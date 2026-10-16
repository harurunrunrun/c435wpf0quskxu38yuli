import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { runInNewContext } from 'node:vm';

// Exercise the actual search event handler even when this host cannot launch Chromium.
const source = (await readFile(new URL('../src/lib/local-ui.js', import.meta.url), 'utf8'))
  .replace(/^import .+;\s*$/gm, '')
  .replaceAll('import.meta.url', '"https://flowchartcp.invalid/assets/local-ui.js"');
function element() {
  return { value: '', textContent: '', children: [], handlers: {},
    addEventListener(type, handler) { this.handlers[type] = handler; },
    append(...children) { this.children.push(...children); },
    replaceChildren() { this.children = []; },
  };
}

test('local search normalizes Japanese/full-width and English names, then clears stale results', async () => {
  const input = element(), results = element(), status = element(), dialog = element();
  const selectors = { '#search-input': input, '#search-results': results, '#search-status': status, '#search-dialog': dialog };
  let requests = 0;
  const index = [
    { title: '単調キューで遷移の最小値を求める', url: '/flowchartcp/techniques/dp-sliding-min/', summary: '動く区間の遷移をまとめる', aliases: ['monotone queue DP'], text: 'DP の式' },
    { title: 'ダイクストラ法', url: '/flowchartcp/techniques/dijkstra/', summary: '重みが非負の最短路', aliases: ['Dijkstra', 'shortest path'], text: '負辺には使えない' },
  ];
  runInNewContext(source, { URL,
    document: { querySelector: selector => selectors[selector], addEventListener() {}, createElement: element },
    fetch: async () => { requests++; return { ok: true, json: async () => index }; },
  });
  for (const [query, id] of [['動く 区間', 'dp-sliding-min'], ['ＤＰ', 'dp-sliding-min'], ['SHORTEST PATH', 'dijkstra']]) {
    input.value = query;
    await input.handlers.input();
    assert.equal(results.children.length, 1);
    assert.equal(results.children[0].href, `/flowchartcp/techniques/${id}/`);
    assert.match(status.textContent, /1 件/);
  }
  assert.equal(requests, 1, 'search index is reused');
  input.value = 'unknown-example-3718';
  await input.handlers.input();
  assert.equal(results.children.length, 0);
  assert.match(status.textContent, /該当する項目はありません/);
  input.value = '';
  await input.handlers.input();
  assert.match(status.textContent, /検索語を入力/);
});

test('failed search fetch can be retried on the next input', async () => {
  const input = element(), results = element(), status = element(), dialog = element();
  const selectors = { '#search-input': input, '#search-results': results, '#search-status': status, '#search-dialog': dialog };
  let requests = 0;
  runInNewContext(source, { URL,
    document: { querySelector: selector => selectors[selector], addEventListener() {}, createElement: element },
    fetch: async () => ({ ok: ++requests > 1, json: async () => [] }),
  });
  input.value = 'DP';
  await input.handlers.input();
  assert.match(status.textContent, /もう一度入力/);
  await input.handlers.input();
  assert.equal(requests, 2);
  assert.match(status.textContent, /該当する項目/);
});
