import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import path from 'node:path';

export function cutoffEnd(day) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(day)) throw new Error('--until must be YYYY-MM-DD');
  const date = new Date(`${day}T23:59:59.999+09:00`);
  if (!Number.isFinite(+date) || new Date(`${day}T00:00:00Z`).toISOString().slice(0, 10) !== day) throw new Error('Invalid cutoff date');
  return date;
}

export class HttpClient {
  constructor({ fetchImpl = fetch, sleep = ms => new Promise(resolve => setTimeout(resolve, ms)), retries = 3, interval = 2100, now = Date.now } = {}) {
    Object.assign(this, { fetchImpl, sleep, retries, interval, now });
    this.lastRequest = null;
  }
  async get(url, format = 'text') {
    for (let attempt = 0; ; attempt++) {
      if (this.lastRequest !== null) await this.sleep(Math.max(0, this.interval - (this.now() - this.lastRequest)));
      this.lastRequest = this.now();
      try {
        const response = await this.fetchImpl(url, { headers: { 'User-Agent': 'flowchartcp-research/1.0 (metadata only)', Accept: 'application/json,text/html,text/plain' }, signal: AbortSignal.timeout(30000) });
        if (!response.ok) {
          const error = new Error(`HTTP ${response.status}: ${url}`);
          error.retryable = response.status === 429 || response.status >= 500;
          const value = response.headers?.get('retry-after');
          error.delay = value && /^\d+$/.test(value) ? Number(value) * 1000 : value ? Math.max(0, Date.parse(value) - this.now()) : null;
          throw error;
        }
        return await (format === 'json' ? response.json() : response.text());
      } catch (error) {
        if (attempt >= this.retries || error.retryable === false) throw error;
        await this.sleep(error.delay ?? 1000 * 2 ** attempt);
      }
    }
  }
}

export async function atomicWrite(file, content) {
  await mkdir(path.dirname(file), { recursive: true });
  const temporary = `${file}.${process.pid}.tmp`;
  await writeFile(temporary, content);
  await rename(temporary, file);
}

async function readJson(file, fallback) {
  try { return JSON.parse(await readFile(file, 'utf8')); }
  catch (error) { if (error.code === 'ENOENT') return fallback; throw error; }
}

/** Metadata acquisition never increments editorial-review or technique-extraction counters. */
export async function collect({ source, adapter, directory, until, resume = false, limit = Infinity, onProgress = () => {} }) {
  const file = path.join(directory, `${source}.jsonl`);
  const checkpointFile = path.join(directory, `${source}.checkpoint.json`);
  const previous = await readJson(checkpointFile, null);
  if (resume && previous && previous.until !== until) throw new Error('Cutoff differs from checkpoint; use a separate output directory or start without --resume');
  let state = resume && previous ? previous : { source, until, cursor: null, status: 'collecting', discovered: 0, fetched: 0, solutionReviewed: 0, techniquesExtracted: 0, batches: 0, scope: null, excludedUnknownDate: 0 };
  const records = new Map();
  try {
    const content = await readFile(file, 'utf8');
    // A failed fresh attempt must not destroy the last successful snapshot.
    if (resume && previous) for (const line of content.split('\n').filter(Boolean)) { const row = JSON.parse(line); records.set(row.id, row); }
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
    if (resume && previous?.fetched > 0) throw new Error('Checkpoint references a missing snapshot; restore it or restart collection');
  }
  if (state.status === 'complete') return state;
  let committed = false;
  try {
    for (let count = 0; count < limit; count++) {
      const batch = await adapter.next(state.cursor);
      for (const row of batch.records) records.set(row.id, row);
      state = { ...state, cursor: batch.cursor, status: batch.done ? 'complete' : 'partial', batches: state.batches + 1, discovered: Math.max(state.discovered, batch.discovered ?? records.size), fetched: records.size, scope: batch.scope ?? state.scope, excludedUnknownDate: batch.excludedUnknownDate ?? state.excludedUnknownDate, updatedAt: new Date().toISOString() };
      const data = [...records.values()].sort((a, b) => a.id.localeCompare(b.id)).map(row => JSON.stringify(row)).join('\n');
      await atomicWrite(file, data ? `${data}\n` : '');
      await atomicWrite(checkpointFile, `${JSON.stringify(state, null, 2)}\n`);
      committed = true;
      onProgress(state);
      if (batch.done) break;
    }
  } catch (error) {
    state = { ...state, status: 'failed', error: error.message, updatedAt: new Date().toISOString() };
    // A fresh run failing before its first batch must keep the old snapshot's cursor.
    const failureFile = !resume && previous && !committed ? path.join(directory, `${source}.attempt.json`) : checkpointFile;
    await atomicWrite(failureFile, `${JSON.stringify(state, null, 2)}\n`);
    throw error;
  }
  return state;
}
