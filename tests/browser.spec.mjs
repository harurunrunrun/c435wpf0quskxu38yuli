import { test as base, expect } from '@playwright/test';
import { readFileSync, readdirSync } from 'node:fs';
import { readFile, stat } from 'node:fs/promises';
import { join, resolve, sep, extname, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { sections, siteTitle } from '../src/lib/presentation.mjs';

const site = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const graphs = JSON.parse(readFileSync(join(site, 'data/flows.json'), 'utf8'));
const entries = graphs.filter(graph => graph.entry);
const metadata = readdirSync(join(site, 'data')).filter(name => /^techniques-.+\.json$/.test(name))
  .flatMap(name => JSON.parse(readFileSync(join(site, 'data', name), 'utf8')).map(item => ({ ...item,
    kind: name.startsWith('techniques-specific-') ? 'technique' : 'foundation' })));
const primary = metadata.filter(item => item.kind === 'technique');
const foundations = metadata.filter(item => item.kind === 'foundation');
const techniqueById = new Map(metadata.map(item => [item.id, item]));
const graphById = new Map(graphs.map(graph => [graph.id, graph]));
const labels = { yes: 'はい', no: 'いいえ', unknown: 'わからない' };
const nodeOf = (graph, id) => graph.nodes.find(node => node.id === id);
const rootOf = graph => nodeOf(graph, graph.root);
const optionsOf = node => node.options ?? Object.keys(node.answers ?? {}).map(id => ({ id, label: labels[id] ?? id }));
const articleUrl = id => `/flowchartcp/techniques/${id}/`;

function formerFlowDestination(id, answers) {
  let graph = graphById.get(id), current = rootOf(graph), consumed = 0, historyCount = 0;
  for (let limit = 0; limit < 128; limit++) {
    const entry = current.id === graph.root ? graph.legacyEntryChoices?.[answers[consumed]] : undefined;
    if (entry) {
      graph = graphById.get(entry.graph); current = rootOf(graph); historyCount++;
      continue;
    }
    if (current.type === 'route' && current.continuation === true) {
      graph = graphById.get(current.graph); current = rootOf(graph);
      continue;
    }
    if (consumed === answers.length) return { graph, current, historyCount };
    if (current.type !== 'question' || !current.answers[answers[consumed]]) throw new Error(`Invalid old browser fixture at ${graph.id}/${current.id}`);
    current = nodeOf(graph, current.answers[answers[consumed++]]); historyCount++;
  }
  throw new Error('The old browser fixture contains a route cycle.');
}

// Paths and labels follow the real data; adding a field never requires a new fixed count.
function findPath(graph, predicate) {
  const queue = [{ current: rootOf(graph), answers: [], nodes: [rootOf(graph)], edges: [] }];
  const seen = new Set();
  for (const path of queue) {
    if (seen.has(path.current.id)) continue;
    seen.add(path.current.id);
    if (predicate(path)) return { graph, ...path };
    if (path.current.type !== 'question') continue;
    for (const option of optionsOf(path.current).filter(option => option.id !== 'unknown')) {
      const next = nodeOf(graph, path.current.answers[option.id]);
      queue.push({ current: next, answers: [...path.answers, option.id], nodes: [...path.nodes, next],
        edges: [...path.edges, `${path.current.id}:${option.id}:${next.id}`] });
    }
  }
}
const multiPath = graphs.filter(graph => optionsOf(rootOf(graph)).length > 3)
  .map(graph => findPath(graph, path => path.answers.length >= 2 && path.current.type === 'result'
    && path.current.techniques?.some(id => techniqueById.get(id)?.kind === 'technique'))).find(Boolean);
const routePath = graphs.map(graph => findPath(graph, path => path.answers.length >= 2 && path.current.type === 'route')).find(Boolean);
const unknownGraph = graphs.find(graph => rootOf(graph).answers?.unknown && rootOf(graph).answers.unknown !== graph.root);
if (!multiPath || !routePath || !unknownGraph) throw new Error('Multi-choice, detailed-route, and unknown paths are required.');
const article = techniqueById.get(multiPath.current.techniques.find(id => techniqueById.get(id)?.kind === 'technique'));
const searchArticle = primary.find(item => item.id === 'two-fenwick-range-add') ?? primary[0];
const englishAlias = searchArticle.aliases.find(alias => /^[A-Za-z][A-Za-z\s-]+$/.test(alias));
if (!englishAlias) throw new Error('A searchable English alias is required.');

const test = base.extend({
  pageErrors: [async ({ page }, use) => {
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await use(errors);
    expect(errors, 'No uncaught browser errors').toEqual([]);
  }, { auto: true }],
});

// Interception also permits QA on hosts where the preview server cannot bind a socket.
const offline = process.env.FLOWCHARTCP_QA_OFFLINE === '1';
const artifactRoot = join(site, 'dist-local');
const mimeTypes = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.woff': 'font/woff', '.ttf': 'font/ttf', '.png': 'image/png' };
async function serveArtifacts(context) {
  if (!offline) return;
  await context.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.origin !== 'http://127.0.0.1:4323' || !url.pathname.startsWith('/flowchartcp/')) {
      await route.abort('blockedbyclient'); return;
    }
    try {
      let target = resolve(artifactRoot, decodeURIComponent(url.pathname.slice('/flowchartcp/'.length)));
      if (target !== artifactRoot && !target.startsWith(artifactRoot + sep)) {
        await route.fulfill({ status: 403, body: 'Forbidden' }); return;
      }
      if ((await stat(target)).isDirectory()) target = join(target, 'index.html');
      await route.fulfill({ status: 200, contentType: mimeTypes[extname(target)] ?? 'application/octet-stream', body: await readFile(target) });
    } catch { await route.fulfill({ status: 404, body: 'Not found' }); }
  });
}
test.beforeEach(async ({ context }) => { await serveArtifacts(context); });

const encodeSteps = answers => answers.map(answer => ({ yes: 'y', no: 'n', unknown: 'u' })[answer] ?? `c:${encodeURIComponent(answer)}`).join(',');
async function openFlow(page, graph = multiPath.graph, answers = []) {
  await page.goto(`flowcharts/#flow=${encodeURIComponent(graph.id)}&steps=${encodeSteps(answers)}`);
  await expect(page.locator('[data-flowchart]')).toHaveAttribute('data-enhanced', 'true');
  await expect(page.locator('[data-graph-select]')).toHaveValue(graph.id);
}
async function answerPath(page, path) {
  for (let i = 0; i < path.answers.length; i++) {
    await expect(page.locator('[data-current-node] h3')).toHaveText(path.nodes[i].title);
    const option = optionsOf(path.nodes[i]).find(option => option.id === path.answers[i]);
    await page.locator('[data-current-node]').getByRole('button', { name: option.label, exact: true }).click();
  }
  await expect(page.locator('[data-current-node] h3')).toHaveText(path.current.title);
}
async function noHorizontalOverflow(page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), 'Page stays within viewport width').toBe(true);
}
async function viewBox(svg) { return (await svg.getAttribute('viewBox')).split(/\s+/).map(Number); }
async function cardIds(page) {
  return page.locator('[data-technique-card]').evaluateAll(links => links.map(link => new URL(link.href).pathname.split('/').filter(Boolean).at(-1)).sort());
}

test('simple contents opens specific technique articles', async ({ page }) => {
  await page.goto('./');
  await expect(page.locator('.simple-home h1')).toHaveText(siteTitle);
  await expect(page.locator('.simple-home').getByRole('heading', { name: '目次', exact: true })).toBeVisible();
  const destinations = await page.locator('.simple-home [data-section-link]').evaluateAll(links => links.map(link => new URL(link.href).pathname));
  expect(destinations).toEqual(sections.map(section => `/flowchartcp/${section.href}`));
  expect(await cardIds(page)).toEqual(primary.map(item => item.id).sort());
  await expect(page.locator('main')).not.toContainText('問題の条件から、');
  await noHorizontalOverflow(page);
  await page.locator('.simple-home [data-section-link][href$="/catalog/"]').click();
  await page.locator(`[data-technique-card][href="${articleUrl(article.id)}"]`).click();
  await expect(page.locator('main h1')).toHaveText(article.title);
  for (const heading of ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', 'この手法を使う問題'])
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
  await expect(page.locator('pre code').first()).toBeVisible();
  await expect(page.locator('.technique-references tbody a').first()).toHaveAttribute('href', /^https:\/\//);
});

test('primary techniques and basic algorithms have separate catalogs', async ({ page }) => {
  await page.goto('catalog/');
  expect(await cardIds(page)).toEqual(primary.map(item => item.id).sort());
  await page.goto('basics/');
  expect(await cardIds(page)).toEqual(foundations.map(item => item.id).sort());
  const foundation = foundations.find(item => item.id === 'dijkstra') ?? foundations[0];
  await page.locator(`[data-technique-card][href="${articleUrl(foundation.id)}"]`).click();
  await expect(page.locator('main h1')).toHaveText(foundation.title);
});

for (const query of [searchArticle.title, englishAlias]) {
  test(`full-text search supports Japanese and English: ${query}`, async ({ page }) => {
    await page.goto('./');
    await page.locator('[data-search-open]').click();
    await expect(page.locator('#search-dialog')).toBeVisible();
    await page.locator('#search-input').fill(query);
    const result = page.locator(`#search-results a[href="${articleUrl(searchArticle.id)}"]`);
    await expect(result).toBeVisible(); await result.click();
    await expect(page).toHaveURL(new RegExp(`/techniques/${searchArticle.id}/$`));
    await expect(page.locator('main h1')).toHaveText(searchArticle.title);
  });
}

test('alias filtering and no-result searches remain usable', async ({ page }) => {
  await page.goto('catalog/');
  await page.locator('[data-technique-filter]').fill(englishAlias);
  await expect(page.locator(`[data-technique-card][href="${articleUrl(searchArticle.id)}"]`)).toBeVisible();
  await page.locator('[data-technique-filter]').fill('no-such-technique-872649');
  await expect(page.locator('[data-technique-card]:visible')).toHaveCount(0);
  await expect(page.locator('[data-filter-status]')).toContainText('該当する項目はありません');
  await page.locator('[data-search-open]').click();
  await page.locator('#search-input').fill('no-such-technique-872649');
  await expect(page.locator('#search-status')).toContainText('該当する項目はありません');
  await page.keyboard.press('Escape');
  await expect(page.locator('#search-dialog')).not.toBeVisible();
});

test('multiple choices and highlighted paths survive question/diagram switching', async ({ page }) => {
  await openFlow(page);
  expect(await page.locator('[data-current-node] [data-answer]').allTextContents()).toEqual(optionsOf(rootOf(multiPath.graph)).map(option => option.label));
  await answerPath(page, multiPath);
  const hash = new URL(page.url()).hash;
  await expect(page.locator('[data-history-count]')).toHaveText(String(multiPath.answers.length));
  await page.locator('[data-view="diagram"]').click();
  const panel = page.locator(`[data-graph-panel="${multiPath.graph.id}"]`);
  await expect(panel).toBeVisible();
  const svg = panel.locator('svg');
  await expect(svg.locator('.flow-node.is-current')).toHaveAttribute('data-node', multiPath.current.id);
  await expect(svg.locator('.flow-node.is-path')).toHaveCount(multiPath.nodes.length);
  expect(await svg.locator('.flow-edge.is-path').evaluateAll(edges => edges.map(edge => edge.dataset.edge).sort())).toEqual([...multiPath.edges].sort());
  expect(new URL(page.url()).hash).toBe(hash);
  await page.locator('[data-view="questions"]').click();
  await expect(page.locator('[data-current-node] h3')).toHaveText(multiPath.current.title);
  await expect(page.locator('[data-current-node] .flow-candidate-list a').first()).toBeVisible();
  await page.locator('[data-flow-history-wrap] summary').click();
  await expect(page.locator('[data-flow-history] button')).toHaveCount(multiPath.answers.length);
  await expect(page.locator('[data-flow-history] button').first()).toContainText(optionsOf(multiPath.nodes[0]).find(option => option.id === multiPath.answers[0]).label);
  await page.locator('[data-flow-history] button').first().click();
  await expect(page.locator('[data-current-node] h3')).toHaveText(rootOf(multiPath.graph).title);
  await expect(page.locator('[data-history-count]')).toHaveText('0');
});

test('switching fields retains each field’s answers', async ({ page }) => {
  await openFlow(page); await answerPath(page, multiPath);
  const other = graphs.find(graph => graph.id !== multiPath.graph.id && optionsOf(rootOf(graph)).some(option => option.id !== 'unknown' && nodeOf(graph, rootOf(graph).answers[option.id]).type !== 'route'));
  const option = optionsOf(rootOf(other)).find(option => option.id !== 'unknown' && nodeOf(other, rootOf(other).answers[option.id]).type !== 'route');
  await page.locator('[data-graph-select]').selectOption(other.id);
  await page.locator('[data-current-node]').getByRole('button', { name: option.label, exact: true }).click();
  await expect(page.locator('[data-history-count]')).toHaveText('1');
  await page.locator('[data-graph-select]').selectOption(multiPath.graph.id);
  await expect(page.locator('[data-current-node] h3')).toHaveText(multiPath.current.title);
  await expect(page.locator('[data-history-count]')).toHaveText(String(multiPath.answers.length));
});

test('field links open field roots and restore a detailed answer path', async ({ page }) => {
  await page.goto('flowcharts/');
  await expect(page.locator('[data-domain-graph]')).toHaveCount(entries.length);
  await expect(page.locator('[data-domain-graph="overview"]')).toHaveCount(0);
  await expect(page.locator('[data-graph-panel="overview"]')).toHaveCount(0);
  await page.locator('[data-domain-graph="ranges"]').click();
  await expect(page.locator('[data-graph-select]')).toHaveValue('ranges');
  const field=graphById.get('ranges'), first=rootOf(field);
  const option=optionsOf(first).find(option=>nodeOf(field,first.answers[option.id]).type==='route');
  await page.locator('[data-current-node]').getByRole('button',{name:option.label,exact:true}).click();
  const route=nodeOf(field,first.answers[option.id]);
  await page.locator('[data-current-node] .flow-route-button').click();
  const detail=graphById.get(route.graph), answer=optionsOf(rootOf(detail)).find(option=>option.id!=='unknown');
  await page.locator('[data-current-node]').getByRole('button',{name:answer.label,exact:true}).click();
  const title=nodeOf(detail,rootOf(detail).answers[answer.id]).title;
  await page.locator('[data-domain-graph="strings"]').click();
  await expect(page.locator('[data-graph-select]')).toHaveValue('strings');
  await page.locator('[data-domain-graph="ranges"]').click();
  await expect(page.locator('[data-graph-select]')).toHaveValue(detail.id);
  await expect(page.locator('[data-current-node] h3')).toHaveText(title);
  await expect(page.locator('[data-history-count]')).toHaveText('2');
});

test('unknown, back, reset and share URLs preserve valid answers', async ({ page }) => {
  await openFlow(page, unknownGraph);
  const root = rootOf(unknownGraph), unknown = nodeOf(unknownGraph, root.answers.unknown);
  await page.locator('[data-current-node] [data-answer="unknown"]').click();
  await expect(page.locator('[data-current-node] h3')).toHaveText(unknown.title);
  await expect(page.locator('[data-current-node]')).toContainText(unknown.explanation);
  await expect(page.locator('[data-history-count]')).toHaveText('1');
  await page.locator('[data-flow-back]').click();
  await expect(page.locator('[data-current-node] h3')).toHaveText(root.title);
  await expect(page.locator('[data-flow-back]')).toBeDisabled();
  await openFlow(page); await answerPath(page, multiPath);
  await page.locator('[data-flow-share]').click();
  await expect(page.locator('[data-share-url]')).toBeVisible();
  const shared = await page.locator('[data-share-url]').inputValue();
  expect(shared).toBe(page.url()); await page.goto(shared);
  await expect(page.locator('[data-current-node] h3')).toHaveText(multiPath.current.title);
  await expect(page.locator('[data-history-count]')).toHaveText(String(multiPath.answers.length));
  await page.locator('[data-flow-reset]').click();
  await expect(page.locator('[data-current-node] h3')).toHaveText(rootOf(multiPath.graph).title);
  await expect(page.locator('[data-history-count]')).toHaveText('0');
  expect(new URLSearchParams(new URL(page.url()).hash.slice(1)).get('steps')).toBe('');
});

test('detailed flows preserve previous choices through share/reload and back', async ({ page }) => {
  await openFlow(page, routePath.graph); await answerPath(page, routePath);
  await page.locator('[data-current-node] .flow-route-button').click();
  const destination = graphById.get(routePath.current.graph), root = rootOf(destination);
  await expect(page.locator('[data-graph-select]')).toHaveValue(destination.id);
  await expect(page.locator('[data-current-node] h3')).toHaveText(root.title);
  await expect(page.locator('[data-history-count]')).toHaveText(String(routePath.answers.length));
  const option = optionsOf(root).find(option => option.id !== 'unknown');
  await page.locator('[data-current-node]').getByRole('button', { name: option.label, exact: true }).click();
  await page.locator('[data-flow-share]').click();
  await page.goto(await page.locator('[data-share-url]').inputValue());
  await expect(page.locator('[data-current-node] h3')).toHaveText(nodeOf(destination, root.answers[option.id]).title);
  await expect(page.locator('[data-history-count]')).toHaveText(String(routePath.answers.length + 1));
  await page.locator('[data-flow-back]').click();
  await expect(page.locator('[data-current-node] h3')).toHaveText(root.title);
  await page.locator('[data-flow-back]').click();
  await expect(page.locator('[data-graph-select]')).toHaveValue(routePath.graph.id);
  await expect(page.locator('[data-current-node] h3')).toHaveText(routePath.nodes.at(-2).title);
  await expect(page.locator('[data-history-count]')).toHaveText(String(routePath.answers.length - 1));
});

test('invalid shared answers are truncated at the last valid choice', async ({ page }) => {
  const valid = multiPath.answers[0];
  await page.goto(`flowcharts/#flow=${multiPath.graph.id}&steps=${encodeSteps([valid])},c:invalid-answer,${encodeSteps(multiPath.answers.slice(1))}`);
  await expect(page.locator('[data-flowchart]')).toHaveAttribute('data-enhanced', 'true');
  await expect(page.locator('[data-current-node] h3')).toHaveText(multiPath.nodes[1].title);
  await expect(page.locator('[data-history-count]')).toHaveText('1');
  expect(new URLSearchParams(new URL(page.url()).hash.slice(1)).get('steps')).toBe(encodeSteps([valid]));
  await page.goto('flowcharts/#flow=no-such-field&steps=c:invalid-answer');
  await expect(page.locator('[data-graph-select]')).toHaveValue(graphs[0].id);
  await expect(page.locator('[data-current-node] h3')).toHaveText(rootOf(graphs[0]).title);
  await expect(page.locator('[data-history-count]')).toHaveText('0');
});

test('camera handles zoom, fit, keyboard, drag and current-position focus', async ({ page }) => {
  await openFlow(page, multiPath.graph, [multiPath.answers[0]]);
  await page.locator('[data-view="diagram"]').click();
  const panel = page.locator(`[data-graph-panel="${multiPath.graph.id}"]`), svg = panel.locator('svg'), viewport = panel.locator('[data-svg-viewport]');
  await panel.locator('[data-camera="fit"]').click(); const original = await viewBox(svg);
  await panel.locator('[data-camera="in"]').click(); expect((await viewBox(svg))[2]).toBeLessThan(original[2]);
  await panel.locator('[data-camera="out"]').click(); expect((await viewBox(svg))[2]).toBeCloseTo(original[2]);
  await panel.locator('[data-camera="left"]').click(); expect((await viewBox(svg))[0]).toBeLessThan(original[0]);
  await viewport.focus(); await page.keyboard.press('ArrowRight'); expect((await viewBox(svg))[0]).toBeCloseTo(original[0]);
  const box = await viewport.boundingBox(); expect(box).not.toBeNull(); const before = await viewBox(svg);
  await page.mouse.move(box.x + 12, box.y + 12); await page.mouse.down();
  await page.mouse.move(box.x + 90, box.y + 60, { steps: 5 }); await page.mouse.up();
  expect(await viewBox(svg)).not.toEqual(before);
  await panel.locator('[data-camera="current"]').click();
  await expect(svg.locator(`[data-node="${multiPath.nodes[1].id}"]`)).toHaveAttribute('aria-current', 'step');
  expect((await viewBox(svg))[2]).toBeLessThan(original[2]);
  await panel.locator('[data-camera="fit"]').click(); expect(await viewBox(svg)).toEqual(original);
});

for (const dimensions of [{ width: 1280, height: 900 }, { width: 390, height: 844 }]) {
  test(`the initial root is readable in both diagram views at ${dimensions.width}px`, async ({ page }) => {
    const graph = graphById.get('dp');
    await page.setViewportSize(dimensions);
    await openFlow(page, graph); await page.locator('[data-view="diagram"]').click();
    const panel = page.locator(`[data-graph-panel="${graph.id}"]`), svg = panel.locator('svg');
    const fontPixels = element => {
      const text = element.querySelector('.node-title'), matrix = text.getScreenCTM();
      return parseFloat(getComputedStyle(text).fontSize) * Math.hypot(matrix.a, matrix.b);
    };
    expect(await svg.locator(`[data-node="${graph.root}"]`).evaluate(fontPixels)).toBeGreaterThanOrEqual(12);
    await page.goto(`diagrams/${graph.id}/`);
    const standalone = page.locator('[data-diagram-viewport] svg');
    await expect(page.locator('[data-diagram-viewer]')).toHaveAttribute('data-enhanced', 'true');
    expect(await standalone.locator(`[data-node="${graph.root}"]`).evaluate(fontPixels)).toBeGreaterThanOrEqual(12);
    const initial = await viewBox(standalone);
    const rectangle = await page.locator('[data-diagram-viewport]').boundingBox();
    expect(initial[2] / initial[3]).toBeCloseTo(rectangle.width / rectangle.height, 3);
    await page.locator('[data-diagram-action="fit"]').click();
    expect((await viewBox(standalone))[2]).toBeGreaterThan(initial[2]);
  });
}

test('a separate diagram page keeps the answer path and supports pointer-centered wheel zoom', async ({ page }) => {
  await openFlow(page, multiPath.graph, multiPath.answers);
  await page.locator('[data-view="diagram"]').click();
  const panel = page.locator(`[data-graph-panel="${multiPath.graph.id}"]`);
  await panel.locator('[data-camera="in"]').click();
  const camera = await viewBox(panel.locator('svg'));
  await panel.locator('[data-diagram-open]').click();
  await expect(page).toHaveURL(new RegExp(`/diagrams/${multiPath.graph.id}/`));
  await expect(page.locator('header, aside, dialog')).toHaveCount(0);
  const viewport = page.locator('[data-diagram-viewport]'), svg = viewport.locator('svg');
  await expect(svg).toHaveCount(1);
  const openedCamera = await viewBox(svg);
  for (let i=0;i<4;i++) expect(openedCamera[i]).toBeCloseTo(camera[i], 2);
  await expect(svg.locator(`[data-node="${multiPath.current.id}"]`)).toHaveAttribute('aria-current', 'step');
  const point = await svg.evaluate(element => {
    const screen = new DOMPoint(innerWidth * .45, innerHeight * .55);
    const diagram = screen.matrixTransform(element.getScreenCTM().inverse());
    return { x: screen.x, y: screen.y, diagramX: diagram.x, diagramY: diagram.y };
  });
  await page.mouse.move(point.x, point.y); await page.mouse.wheel(0, -200);
  await expect.poll(async () => (await viewBox(svg))[2]).toBeLessThan(camera[2]);
  const anchored = await svg.evaluate((element, point) => new DOMPoint(point.diagramX, point.diagramY).matrixTransform(element.getScreenCTM()).toJSON(), point);
  expect(anchored.x).toBeCloseTo(point.x, 4); expect(anchored.y).toBeCloseTo(point.y, 4);
  const zoomed = await viewBox(svg); await page.mouse.wheel(0, 200);
  await expect.poll(async () => (await viewBox(svg))[2]).toBeGreaterThan(zoomed[2]);
  await viewport.focus(); await page.keyboard.press('+'); const returnedCamera = await viewBox(svg);
  await page.locator('[data-diagram-back]').click();
  await expect(page).toHaveURL(new RegExp('/flowcharts/'));
  await expect(panel).toBeVisible();
  const restored = await viewBox(panel.locator('svg'));
  for (let i=0;i<4;i++) expect(restored[i]).toBeCloseTo(returnedCamera[i], 2);
  await expect(panel.locator(`svg [data-node="${multiPath.current.id}"]`)).toHaveAttribute('aria-current', 'step');
});

test('an old dedicated field URL opens its split diagram with the old answers and a readable camera', async ({ page }) => {
  const { graph, current } = formerFlowDestination('math', ['xor', 'yes']);
  const target = graph.id;
  await page.goto('diagrams/math/?camera=20,30,1000,600#flow=math&steps=c:xor,y');
  await expect(page).toHaveURL(new RegExp(`/diagrams/${target}/`));
  const svg = page.locator('[data-diagram-viewport] svg');
  await expect(svg).toHaveAttribute('data-flow-svg', target);
  await expect(svg.locator(`[data-node="${current.id}"]`)).toHaveAttribute('aria-current', 'step');
  const fontPixels = await svg.locator(`[data-node="${current.id}"] .node-title`).first().evaluate(text => parseFloat(getComputedStyle(text).fontSize) * text.getScreenCTM().a);
  expect(fontPixels).toBeGreaterThanOrEqual(12);
  expect(new URL(page.url()).searchParams.get('camera')).not.toBe('20,30,1000,600');
  // A fragment for an unrelated diagram keeps this page at its own root.
  await page.goto('diagrams/math/#flow=strings&steps=');
  await expect(page.locator('[data-diagram-viewport] svg')).toHaveAttribute('data-flow-svg', 'math');
  await expect(page.locator(`[data-node="${rootOf(graphById.get('math')).id}"]`)).toHaveAttribute('aria-current', 'step');
});

test('an old main-page diagram URL keeps diagram mode after category migration and reload', async ({ page }) => {
  const { graph, historyCount } = formerFlowDestination('math', ['xor', 'yes']);
  const target = graph.id;
  await page.goto('flowcharts/?diagram=math&camera=20,30,1000,600#flow=math&steps=c:xor,y');
  await expect(page.locator('[data-graph-select]')).toHaveValue(target);
  await expect(page.locator(`[data-graph-panel="${target}"]`)).toBeVisible();
  await expect(page.locator('[data-question-panel]')).not.toBeVisible();
  await expect(page.locator('[data-history-count]')).toHaveText(String(historyCount));
  expect(new URL(page.url()).searchParams.get('diagram')).toBe(target);
  expect(new URL(page.url()).searchParams.get('camera')).toBeNull();
  await page.reload();
  await expect(page.locator('[data-graph-select]')).toHaveValue(target);
  await expect(page.locator(`[data-graph-panel="${target}"]`)).toBeVisible();
  await expect(page.locator('[data-history-count]')).toHaveText(String(historyCount));
});

test('an old detailed-diagram URL opens the continued question without its previous camera', async ({ page }) => {
  const split = graphs.map(graph => findPath(graph, path => path.current.type === 'route' && path.current.continuation === true)).find(Boolean);
  expect(split, 'A detailed diagram must have a separated continuation').toBeTruthy();
  const target = graphById.get(split.current.graph);
  const hash = `#flow=${encodeURIComponent(split.graph.id)}&steps=${encodeSteps(split.answers)}`;
  await page.goto(`diagrams/${split.graph.id}/?camera=20,30,1000,600${hash}`);
  await expect(page).toHaveURL(new RegExp(`/diagrams/${target.id}/`));
  const svg = page.locator('[data-diagram-viewport] svg');
  await expect(svg).toHaveAttribute('data-flow-svg', target.id);
  await expect(svg.locator(`[data-node="${target.root}"]`)).toHaveAttribute('aria-current', 'step');
  const fontPixels = await svg.locator(`[data-node="${target.root}"] .node-title`).first().evaluate(text => parseFloat(getComputedStyle(text).fontSize) * text.getScreenCTM().a);
  expect(fontPixels).toBeGreaterThanOrEqual(12);
  expect(new URL(page.url()).searchParams.get('camera')).not.toBe('20,30,1000,600');
  await page.reload();
  await expect(svg.locator(`[data-node="${target.root}"]`)).toHaveAttribute('aria-current', 'step');
});

test('a main-page detailed-diagram URL preserves diagram mode after continuation migration and reload', async ({ page }) => {
  const split = graphs.map(graph => findPath(graph, path => path.current.type === 'route' && path.current.continuation === true)).find(Boolean);
  expect(split, 'A detailed diagram must have a separated continuation').toBeTruthy();
  const target = graphById.get(split.current.graph);
  const hash = `#flow=${encodeURIComponent(split.graph.id)}&steps=${encodeSteps(split.answers)}`;
  await page.goto(`flowcharts/?diagram=${split.graph.id}&camera=20,30,1000,600${hash}`);
  await expect(page.locator('[data-graph-select]')).toHaveValue(target.id);
  await expect(page.locator(`[data-graph-panel="${target.id}"]`)).toBeVisible();
  await expect(page.locator('[data-question-panel]')).not.toBeVisible();
  await expect(page.locator('[data-history-count]')).toHaveText(String(split.answers.length));
  expect(new URL(page.url()).searchParams.get('diagram')).toBe(target.id);
  expect(new URL(page.url()).searchParams.get('camera')).toBeNull();
  await page.reload();
  await expect(page.locator('[data-graph-select]')).toHaveValue(target.id);
  await expect(page.locator('[data-question-panel]')).not.toBeVisible();
});

test('hovering or focusing one diagram answer makes its own route clear and dims the other routes', async ({ page }) => {
  await page.goto('diagrams/restart-board-trial-expectation/');
  await expect(page.locator('[data-diagram-viewer]')).toHaveAttribute('data-enhanced', 'true');
  await page.locator('[data-diagram-action="fit"]').click();
  const svg = page.locator('[data-diagram-viewport] svg');
  const label = svg.locator('[data-edge-label]').first();
  const edgeId = await label.getAttribute('data-edge-label');
  const edge = svg.locator(`[data-edge="${edgeId}"]`), other = svg.locator('[data-edge]').nth(1);
  const path = edge.locator(':scope > path').first();
  await expect(edge).toHaveCSS('opacity', '1'); await expect(other).toHaveCSS('opacity', '1');
  await expect(path).toHaveCSS('stroke-width', '1.8px');
  await label.hover();
  await expect(edge).toHaveCSS('opacity', '1'); await expect(other).toHaveCSS('opacity', '0.16');
  await expect(path).toHaveCSS('stroke-width', '4px');
  await page.mouse.move(0, 0);
  await expect(other).toHaveCSS('opacity', '1'); await expect(path).toHaveCSS('stroke-width', '1.8px');
  await label.focus(); await expect(label).toBeFocused();
  await expect(edge).toHaveCSS('opacity', '1'); await expect(other).toHaveCSS('opacity', '0.16');
  await expect(path).toHaveCSS('stroke-width', '4px');
  await page.locator('[data-diagram-viewport]').focus();
  await expect(edge).toHaveCSS('opacity', '1'); await expect(other).toHaveCSS('opacity', '1');
  await expect(path).toHaveCSS('stroke-width', '1.8px');
});

test('diagram-only route links open the next diagram page and preserve route history', async ({ page }) => {
  await openFlow(page, routePath.graph, routePath.answers); await page.locator('[data-view="diagram"]').click();
  const source = page.locator(`[data-graph-panel="${routePath.graph.id}"]`), destination = routePath.current.graph;
  await source.locator('[data-diagram-open]').click();
  await page.locator(`[data-node="${routePath.current.id}"] a[data-route="${destination}"]`).locator('text').click();
  await expect(page.locator('[data-diagram-viewport] svg')).toHaveAttribute('data-flow-svg', destination);
  await page.locator('[data-diagram-back]').click();
  await expect(page.locator('[data-graph-select]')).toHaveValue(destination);
  await expect(page.locator('[data-history-count]')).toHaveText(String(routePath.answers.length));
});

test('SVG download includes the authored path and opens specific article links', async ({ page }) => {
  await openFlow(page, multiPath.graph, multiPath.answers); await page.locator('[data-view="diagram"]').click();
  const panel = page.locator(`[data-graph-panel="${multiPath.graph.id}"]`), download = panel.locator('a[download]');
  await expect(download).toHaveAttribute('href', `/flowchartcp/diagrams/${multiPath.graph.id}.svg`);
  const response = await page.evaluate(async url => {
    const result = await fetch(url); return { ok: result.ok, contentType: result.headers.get('content-type'), body: await result.text() };
  }, await download.getAttribute('href'));
  expect(response.ok).toBe(true); expect(response.contentType).toContain('image/svg+xml');
  for (const edge of multiPath.edges) expect(response.body).toContain(`data-edge="${edge}"`);
  const link = panel.locator(`svg [data-node="${multiPath.current.id}"] a[href="${articleUrl(article.id)}"]`);
  await link.locator('text').first().click();
  await expect(page).toHaveURL(new RegExp(`/techniques/${article.id}/$`));
  await expect(page.locator('main h1')).toHaveText(article.title);
});

test('mobile contents, questions, diagrams and articles stay within the viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('./'); await expect(page.locator('.simple-home [data-section-link]')).toHaveCount(sections.length);
  await noHorizontalOverflow(page); await openFlow(page); await answerPath(page, multiPath); await noHorizontalOverflow(page);
  await page.locator('[data-view="diagram"]').click(); await noHorizontalOverflow(page);
  await expect(page.locator(`[data-graph-panel="${multiPath.graph.id}"] [data-camera="current"]`)).toBeVisible();
  await page.locator(`[data-graph-panel="${multiPath.graph.id}"] [data-diagram-open]`).click();
  const diagramBox = await page.locator('[data-diagram-viewport]').boundingBox();
  expect(diagramBox.width).toBeCloseTo(390, 0); expect(diagramBox.height).toBeCloseTo(844, 0);
  await noHorizontalOverflow(page); await page.locator('[data-diagram-back]').click();
  await page.goto(`techniques/${article.id}/`); await noHorizontalOverflow(page);
  await expect(page.locator('.reference-scroll')).toBeVisible();
});

test('JavaScript-disabled readers can follow every graph and text alternative', async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false, viewport: { width: 1280, height: 900 } });
  await serveArtifacts(context); const page = await context.newPage();
  try {
    await page.goto('http://127.0.0.1:4323/flowchartcp/flowcharts/');
    await expect(page.locator('svg[data-flow-svg]')).toHaveCount(graphs.length);
    await expect(page.locator('.flow-static-nav a')).toHaveCount(graphs.length);
    await expect(page.locator('[data-domain-graph]')).toHaveCount(entries.length);
    await expect(page.locator('[data-graph-panel="overview"]')).toHaveCount(0);
    expect(await page.locator('svg[data-flow-svg]').evaluateAll(elements => elements.map(svg => svg.dataset.flowSvg).sort())).toEqual(graphs.map(graph => graph.id).sort());
    await expect(page.locator('[data-graph-select]')).not.toBeVisible();
    const panel = page.locator(`[data-graph-panel="${multiPath.graph.id}"]`); await panel.locator('.flow-node-list summary').click();
    const root = rootOf(multiPath.graph), textRoot = panel.locator(`[id="flow-text-${multiPath.graph.id}-${root.id}"]`);
    for (const option of optionsOf(root)) {
      const target = nodeOf(multiPath.graph, root.answers[option.id]);
      await expect(textRoot.getByRole('link', { name: target.title, exact: true }).first()).toBeVisible();
      await expect(textRoot).toContainText(option.label);
    }
    const result = panel.locator(`[id="flow-text-${multiPath.graph.id}-${multiPath.current.id}"]`);
    await expect(result).toContainText(multiPath.current.conditions[0]);
    await expect(result.locator(`a[href="${articleUrl(article.id)}"]`)).toBeVisible();
    await expect(page.locator('noscript')).toContainText('すべての図と文章版');
    await panel.locator('[data-diagram-open]').click();
    await expect(page.locator('[data-diagram-viewport] svg')).toHaveCount(1);
    await expect(page.locator('header, aside, dialog')).toHaveCount(0);
    await expect(page.locator('[data-diagram-back]')).toBeVisible();
    await result.locator(`a[href="${articleUrl(article.id)}"]`).click();
    await expect(page.getByRole('heading', { name: 'この手法を使う問題', exact: true })).toBeVisible();
    await expect(page.locator('.technique-references tbody a').first()).toHaveAttribute('href', /^https:\/\//);
    await expect(page.locator('pre code').first()).toBeVisible();
  } finally { await context.close(); }
});
