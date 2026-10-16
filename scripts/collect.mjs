#!/usr/bin/env node
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { collect, HttpClient, cutoffEnd } from './lib/collection.mjs';
import { createAdapter } from './lib/adapters.mjs';

const args = process.argv.slice(2);
const options = { source: 'all', until: '2026-10-14', resume: false, limit: Infinity, directory: path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../research/raw') };
for (let i = 0; i < args.length; i++) {
  const arg = args[i];
  if (arg === '--resume') options.resume = true;
  else if (arg === '--source' || arg === '--until' || arg === '--limit' || arg === '--output') {
    const value = args[++i];
    if (!value) throw new Error(`Missing value for ${arg}`);
    if (arg === '--limit') { options.limit = Number(value); if (!Number.isSafeInteger(options.limit) || options.limit < 1) throw new Error('--limit must be a positive integer'); }
    else if (arg === '--output') options.directory = path.resolve(value);
    else options[arg.slice(2)] = value;
  } else if (arg === '--help') {
    console.log('node scripts/collect.mjs --source codeforces|atcoder|library-checker|cses|all --until YYYY-MM-DD --resume [--limit N] [--output DIRECTORY]\nLimit counts batches: one complete Codeforces/CSES index, one AtCoder contest, one Library Checker problem. Cutoff is end of day in Japan. Acquisition does not verify solutions or classify techniques.');
    process.exit(0);
  } else throw new Error(`Unknown option: ${arg}`);
}
cutoffEnd(options.until);
const supported = ['codeforces', 'atcoder', 'library-checker', 'cses'];
const selected = options.source === 'all' ? supported : [options.source];
if (selected.some(id => !supported.includes(id))) throw new Error(`Supported sources: ${supported.join(', ')}`);
for (const source of selected) {
  try {
    const http = new HttpClient();
    const state = await collect({ ...options, source, adapter: createAdapter(source, http, options.until), onProgress: state => console.log(`${source}: ${state.status}, ${state.fetched} metadata records, ${state.batches} batches; editorial review 0`) });
    console.log(`${source}: ${state.status}; ${state.scope ?? 'No successful metadata request yet'}`);
  } catch (error) { console.error(`${source}: ${error.message}`); process.exitCode = 1; }
}
