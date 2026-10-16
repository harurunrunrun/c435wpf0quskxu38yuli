import test from 'node:test';
import assert from 'node:assert/strict';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const execute=promisify(execFile);
test('10 published string tricks match enumeration, updates and overlap boundaries', {timeout:240000}, async()=>{
  const result=await execute('python3',[path.join(site,'tests/fixtures/string-extension-property.py')],{cwd:site,timeout:230000,maxBuffer:1024*1024});
  assert.equal((result.stdout.match(/ PASS/g)||[]).length,10,result.stdout);
  assert(!result.stdout.includes('FAIL'),result.stdout);
});
