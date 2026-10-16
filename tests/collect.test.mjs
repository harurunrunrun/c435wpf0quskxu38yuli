import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { collect, cutoffEnd, HttpClient } from '../scripts/lib/collection.mjs';
import { createAdapter, parseAtCoderArchive, parseAtCoderTasks, parseLibraryCheckerTitle } from '../scripts/lib/adapters.mjs';
import { syncLedger } from '../scripts/lib/ledger.mjs';

const response = (data, status = 200, retry = null) => ({ ok: status < 400, status, headers: { get: () => retry }, json: async () => data, text: async () => data });
const contestRow = (id, date) => `<tr><td><time>${date}</time></td><td><a href="/contests/${id}">${id}</a></td></tr>`;
const taskPage = id => `<table><tr><td><a href="/contests/${id}/tasks/${id}_a">A</a></td><td><a href="/contests/${id}/tasks/${id}_a">Test &amp; title</a></td></tr></table>`;

test('cutoff is end of Japan calendar day and rejects invalid input', () => {
  assert.equal(cutoffEnd('2026-10-14').toISOString(), '2026-10-14T14:59:59.999Z');
  assert.throws(() => cutoffEnd('2026-02-30'));
  assert.throws(() => cutoffEnd('../raw'));
});

test('HTTP retries transient failures with Retry-After and respects request spacing', async () => {
  let calls = 0;
  const sleeps = [];
  let clock = 0;
  const http = new HttpClient({ now: () => clock, sleep: async ms => { sleeps.push(ms); clock += ms; }, fetchImpl: async () => ++calls === 1 ? response('', 429, '3') : response({ ok: true }), retries: 2 });
  assert.deepEqual(await http.get('https://example.test', 'json'), { ok: true });
  await http.get('https://example.test', 'json');
  assert.equal(calls, 3);
  assert(sleeps.includes(3000));
  assert(sleeps.includes(2100));
});

test('HTTP does not retry forbidden metadata access', async () => {
  let calls = 0;
  const http = new HttpClient({ fetchImpl: async () => { calls++; return response('', 403); }, sleep: async () => {} });
  await assert.rejects(http.get('https://example.test'), /403/);
  assert.equal(calls, 1);
});

test('AtCoder parser keeps titles, canonical ids and contest dates without statements', () => {
  const [contest] = parseAtCoderArchive(`<table>${contestRow('abc001', '2012-10-20 21:00:00+0900')}</table>`);
  assert.equal(contest.startedAt, '2012-10-20T12:00:00.000Z');
  const [problem] = parseAtCoderTasks(taskPage('abc001'), contest);
  assert.equal(problem.title, 'Test & title');
  assert.equal(problem.id, 'atcoder:abc001_a');
  assert.equal(problem.verification, 'unreviewed');
  assert.equal('statement' in problem, false);
});

test('AtCoder pagination, cutoff and resumed cursor fetch each eligible contest once', async () => {
  const visited = [];
  const pages = new Map([
    ['https://atcoder.jp/contests/archive?lang=en&page=1', `<table>${contestRow('future', '2026-10-15 12:00:00+0900')}${contestRow('old1', '2026-10-14 12:00:00+0900')}</table>`],
    ['https://atcoder.jp/contests/archive?lang=en&page=2', `<table>${contestRow('old2', '2020-10-14 12:00:00+0900')}</table>`],
    ['https://atcoder.jp/contests/archive?lang=en&page=3', '<table></table>'],
    ['https://atcoder.jp/contests/old1/tasks?lang=en', taskPage('old1')],
    ['https://atcoder.jp/contests/old2/tasks?lang=en', taskPage('old2')],
  ]);
  const http = { get: async url => { visited.push(url); assert(pages.has(url), url); return pages.get(url); } };
  const directory = await mkdtemp(path.join(os.tmpdir(), 'flowchartcp-collect-'));
  try {
    const options = { source: 'atcoder', directory, until: '2026-10-14', adapter: createAdapter('atcoder', http, '2026-10-14') };
    const partial = await collect({ ...options, limit: 1 });
    assert.equal(partial.status, 'partial');
    assert.equal(partial.fetched, 1);
    const complete = await collect({ ...options, resume: true });
    assert.equal(complete.status, 'complete');
    assert.equal(complete.fetched, 2);
    assert.equal(complete.solutionReviewed, 0);
    const snapshot = await readFile(path.join(directory, 'atcoder.jsonl'), 'utf8');
    await collect({ ...options, resume: true });
    assert.equal(await readFile(path.join(directory, 'atcoder.jsonl'), 'utf8'), snapshot);
    assert.equal(visited.filter(url => url.includes('/old1/tasks')).length, 1);
    assert(!visited.some(url => url.includes('/future/tasks')));
    await assert.rejects(collect({ ...options, until: '2026-10-13', resume: true }), /Cutoff differs/);
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('canonical deduplication and failures retain last committed batch for resume', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'flowchartcp-collect-'));
  const row = { id: 'test:a', title: 'A' };
  let fail = true;
  const adapter = { next: async cursor => {
    if (!cursor) return { records: [row, row], cursor: 1, done: false };
    if (fail) throw new Error('temporary outage');
    return { records: [row, { id: 'test:b', title: 'B' }], cursor: 2, done: true };
  } };
  try {
    const options = { source: 'test', adapter, directory, until: '2026-10-14' };
    await assert.rejects(collect(options), /outage/);
    assert.equal((await readFile(path.join(directory, 'test.jsonl'), 'utf8')).trim().split('\n').length, 1);
    fail = false;
    assert.equal((await collect({ ...options, resume: true })).fetched, 2);
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('a failing fresh run preserves the previous complete snapshot and checkpoint', async () => {
  const directory = await mkdtemp(path.join(os.tmpdir(), 'flowchartcp-collect-'));
  try {
    const options = { source: 'test', directory, until: '2026-10-14', adapter: { next: async () => ({ records: [{ id: 'test:a' }], cursor: { done: true }, done: true }) } };
    await collect(options);
    const snapshot = await readFile(path.join(directory, 'test.jsonl'), 'utf8');
    const checkpoint = await readFile(path.join(directory, 'test.checkpoint.json'), 'utf8');
    await assert.rejects(collect({ ...options, until: '2026-10-15', adapter: { next: async () => { throw new Error('outage'); } } }), /outage/);
    assert.equal(await readFile(path.join(directory, 'test.jsonl'), 'utf8'), snapshot);
    assert.equal(await readFile(path.join(directory, 'test.checkpoint.json'), 'utf8'), checkpoint);
    assert.equal(JSON.parse(await readFile(path.join(directory, 'test.attempt.json'), 'utf8')).status, 'failed');
  } finally { await rm(directory, { recursive: true, force: true }); }
});

test('Codeforces cutoff joins contest times, excludes unknown dates, preserves tags as unreviewed', async () => {
  const http = { get: async url => url.includes('contest.list') ? { status: 'OK', result: [{ id: 1, startTimeSeconds: Date.parse('2026-10-14T12:00:00Z') / 1000 }, { id: 2, startTimeSeconds: Date.parse('2026-10-15T00:00:00Z') / 1000 }] } : { status: 'OK', result: { problems: [{ contestId: 1, index: 'A', name: 'Past', tags: ['greedy'], rating: 800 }, { contestId: 2, index: 'A', name: 'Future' }, { contestId: 3, index: 'A', name: 'Unknown' }] } } };
  const batch = await createAdapter('codeforces', http, '2026-10-14').next(null);
  assert.equal(batch.records.length, 1);
  assert.equal(batch.records[0].verification, 'unreviewed');
  assert.equal(batch.excludedUnknownDate, 1);
});

test('Library Checker fixes cutoff revision, resumes paths and rejects truncated trees', async () => {
  const calls = [];
  const http = { get: async url => {
    calls.push(url);
    if (url.includes('/commits?')) return [{ sha: 'fixed' }];
    if (url.includes('/git/trees/')) return { truncated: false, tree: [{ type: 'blob', path: 'data_structure/range_sum/info.toml' }, { type: 'blob', path: 'graph/shortest_path/info.toml' }] };
    return 'title = "Official title"';
  } };
  const adapter = createAdapter('library-checker', http, '2026-10-14');
  const first = await adapter.next(null);
  const second = await adapter.next(first.cursor);
  assert.equal(first.records[0].revision, 'fixed');
  assert.equal(second.done, true);
  assert.equal(calls.filter(url => url.includes('/git/trees/')).length, 1);
  await assert.rejects(createAdapter('library-checker', { get: async url => url.includes('/commits?') ? [{ sha: 'x' }] : { truncated: true } }, '2026-10-14').next(null), /truncated/);
});

test('Library Checker metadata parses official TOML literal and escaped basic titles', () => {
  assert.equal(parseLibraryCheckerTitle("title = 'Static Range Sum'\ntimelimit = 5.0"), 'Static Range Sum');
  assert.equal(parseLibraryCheckerTitle('title = "A \\"quoted\\" title"'), 'A "quoted" title');
  assert.throws(() => parseLibraryCheckerTitle('name = "random.cpp"'), /missing/);
});

test('ledger counts metadata, reviewed solutions and format-only confirmations separately', async () => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'flowchartcp-ledger-'));
  try {
    await mkdir(path.join(root, 'data'));
    await mkdir(path.join(root, 'research/raw'), { recursive: true });
    await writeFile(path.join(root, 'data/sources.json'), JSON.stringify([
      { id: 'atcoder', name: 'AtCoder', method: 'automated', notes: 'public scope' },
      { id: 'ioi', name: 'IOI', method: 'manual', notes: 'manual scope' },
    ]));
    await writeFile(path.join(root, 'data/references-test.json'), JSON.stringify([
      { source: 'AtCoder', problemId: 'abc1_a', techniqueId: 'one', verification: 'editorial' },
      { source: 'AtCoder', problemId: 'abc1_a', techniqueId: 'two', verification: 'reference-solution' },
      { source: 'AtCoder', problemId: 'abc1_c', techniqueId: 'guess', verification: 'unreviewed' },
      { source: 'IOI', problemId: '2010-maze', techniqueId: 'output-only', verification: 'official-tag' },
    ]));
    await writeFile(path.join(root, 'research/raw/atcoder.jsonl'), '{"id":"atcoder:abc1_a"}\n{"id":"atcoder:abc1_b"}\n');
    await writeFile(path.join(root, 'research/raw/atcoder.checkpoint.json'), JSON.stringify({ until: '2026-10-14', status: 'partial', discovered: 2, scope: 'one contest' }));
    const ledger = await syncLedger({ root });
    assert.equal(ledger.verifiedMappings, 3);
    const atcoder = ledger.sources.find(row => row.source === 'atcoder');
    assert.equal(atcoder.fetched, 2);
    assert.equal(atcoder.metadataCollected, 2);
    assert.equal(atcoder.solutionReviewed, 1);
    assert.equal(atcoder.techniquesExtracted, 2);
    assert.equal(atcoder.totalKnown, null);
    const ioi = ledger.sources.find(row => row.source === 'ioi');
    assert.equal(ioi.solutionReviewed, 0);
    assert.equal(ioi.techniquesExtracted, 1);
    assert.equal(ledger.formatVerifiedProblems, 1);
  } finally { await rm(root, { recursive: true, force: true }); }
});
