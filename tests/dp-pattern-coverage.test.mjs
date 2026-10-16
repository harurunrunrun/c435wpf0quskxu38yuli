import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const execute=promisify(execFile);
test('8 published DP tricks agree with subset enumeration, cut enumeration and direct deletion or tour search', {timeout:180000},async()=>{
  const result=await execute('python3',[path.join(site,'tests/fixtures/dp-pattern-property.py')],{cwd:site,timeout:170000,maxBuffer:1024*1024});
  assert.equal((result.stdout.match(/ PASS/g)||[]).length,8,result.stdout);
  assert(!result.stdout.includes('FAIL'),result.stdout);
});
