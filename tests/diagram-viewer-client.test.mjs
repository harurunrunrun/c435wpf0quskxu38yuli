import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
import { compileLocalModules } from '../scripts/local-modules.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
class Element {
  constructor(tag = 'div', dataset = {}) {
    this.tag = tag; this.className = ''; this.dataset = dataset; this.children = []; this.attributes = {}; this.handlers = {}; this.hidden = false;
    this.classes = new Set(); this.classList = { add: value => this.classes.add(value), remove: value => this.classes.delete(value), toggle: (value, on) => on ? this.classes.add(value) : this.classes.delete(value) };
  }
  append(...elements) { for (const element of elements) { this.children.push(element); element.parent = this; } }
  replaceChildren(...elements) { this.children = []; this.append(...elements); }
  setAttribute(key, value) { this.attributes[key] = String(value); }
  getAttribute(key) { return this.attributes[key] ?? null; }
  removeAttribute(key) { delete this.attributes[key]; }
  addEventListener(type, handler, options) { (this.handlers[type] ??= []).push({ handler, options }); }
  emit(type, fields = {}) { const event = { target: this, button: 0, preventDefault() { this.prevented = true; }, stopPropagation() { this.stopped = true; }, ...fields }; for (const { handler } of this.handlers[type] ?? []) handler(event); return event; }
  matches(selector) {
    if (selector.startsWith('.')) return this.className.split(' ').includes(selector.slice(1));
    if (selector.includes(',')) return selector.split(',').some(part => this.matches(part.trim()));
    const attribute = selector.match(/^\[data-([a-z0-9-]+)(?:="([^"]*)")?\]$/);
    if (attribute) { const key = attribute[1].replace(/-([a-z])/g, (_, char) => char.toUpperCase()); return key in this.dataset && (attribute[2] === undefined || this.dataset[key] === attribute[2]); }
    return this.tag === selector;
  }
  closest(selector) { return this.matches(selector) ? this : this.parent?.closest(selector) ?? null; }
  querySelectorAll(selector) { return this.children.flatMap(child => [...(child.matches(selector) ? [child] : []), ...child.querySelectorAll(selector)]); }
  querySelector(selector) { return this.querySelectorAll(selector)[0] ?? null; }
  focus() { this.focused = true; }
  setPointerCapture(id) { this.captured = id; }
}
class Point { constructor(x, y) { this.x = x; this.y = y; } matrixTransform(matrix) { return { x: matrix.a * this.x + matrix.e, y: matrix.d * this.y + matrix.f }; } }
function fixture(flow, viewer, graph, state, camera) {
  const root = new Element('main', { diagramViewer: '', graph: graph.id, base: '/flowchartcp/' });
  const viewport = new Element('div', { diagramViewport: '' }); viewport.clientWidth = 1000; viewport.clientHeight = 600;
  const svg = new Element('svg');
  const markup = flow.renderFlowSvg(graph);
  const original = markup.match(/viewBox="([^"]+)"/)[1].split(' ').map(Number); svg.setAttribute('viewBox', original.join(' '));
  const rectangles = new Map([...markup.matchAll(/data-node="([^"]+)"[^>]*><rect ([^>]+)/g)].map(match => [match[1], Object.fromEntries([...match[2].matchAll(/(x|y|width|height)="([^"]+)"/g)].map(attribute => [attribute[1], attribute[2]]))]));
  svg.getScreenCTM = () => {
    const [x, y, width, height] = svg.getAttribute('viewBox').split(' ').map(Number);
    const scale = Math.min(viewport.clientWidth / width, viewport.clientHeight / height);
    const e = 10 + (viewport.clientWidth - width * scale) / 2 - x * scale, f = 20 + (viewport.clientHeight - height * scale) / 2 - y * scale;
    return { a: scale, d: scale, e, f, inverse: () => ({ a: 1 / scale, d: 1 / scale, e: -e / scale, f: -f / scale }) };
  };
  for (const node of graph.nodes) {
    const group = new Element('g', { node: node.id }), rect = new Element('rect');
    for (const [key, value] of Object.entries(rectangles.get(node.id) ?? {})) rect.setAttribute(key, value);
    group.append(rect); svg.append(group);
    if (node.type === 'route') svg.append(new Element('a', { route: node.graph }));
    for (const [answer, target] of Object.entries(node.answers ?? {})) svg.append(new Element('g', { edge: `${node.id}:${answer}:${target}` }));
  }
  viewport.append(svg); root.append(viewport);
  const back = new Element('a', { diagramBack: '' }), zoom = new Element('output', { diagramZoom: '' }); root.append(back, zoom);
  const buttons = ['in', 'out', 'fit'].map(action => new Element('button', { diagramAction: action })); root.append(...buttons);
  const url = new URL(viewer.diagramViewerUrl(graph.id, '/flowchartcp/', state, camera), 'https://flowchartcp.invalid');
  let timerId = 0;
  const timers = new Map();
  const window = { location: { hash: url.hash, search: url.search, pathname: url.pathname, href: url.href }, handlers: {}, addEventListener(type, handler) { this.handlers[type] = handler; }, history: { replaceState(_state, _unused, next) { const parsed = new URL(next, url); window.location.hash = parsed.hash; window.location.search = parsed.search; window.location.pathname = parsed.pathname; window.location.href = parsed.href; } } };
  window.replacements = []; window.location.replace = next => window.replacements.push(next);
  window.setTimeout = callback => { timers.set(++timerId, callback); return timerId; };
  window.clearTimeout = id => timers.delete(id);
  window.flushTimers = () => { const pending = [...timers.values()]; timers.clear(); pending.forEach(callback => callback()); };
  const document = { readyState: 'complete', querySelector: () => root, addEventListener() {} };
  return { root, viewport, svg, back, zoom, buttons, window, document, original, box: () => svg.getAttribute('viewBox').split(' ').map(Number) };
}
function mainFixture(flow, viewer, graph, state, camera, startDiagram = true) {
  const f = fixture(flow, viewer, graph, state);
  const root = new Element('div', { flowchart: '', base: '/flowchartcp/' });
  const fields = ['graphSelect', 'questionPanel', 'currentNode', 'diagrams', 'flowStatus', 'flowHistory', 'historyCount', 'flowBack', 'shareBox', 'shareUrl', 'flowReset', 'flowShare'];
  const controls = Object.fromEntries(fields.map(field => [field, new Element('div', { [field]: '' })]));
  root.append(...Object.values(controls));
  const staticNav = new Element(); staticNav.className = 'flow-static-nav'; root.append(staticNav);
  const panel = new Element('section', { graphPanel: graph.id });
  const opener = new Element('a', { diagramOpen: graph.id }), label = new Element('span', { zoomValue: '' });
  delete f.viewport.dataset.diagramViewport; f.viewport.dataset.svgViewport = '';
  panel.append(f.viewport, opener, label); root.append(panel);
  const views = ['questions', 'diagram'].map(view => new Element('button', { view })); root.append(...views);
  const fit = new Element('button', { camera: 'fit' }), current = new Element('button', { camera: 'current' }); panel.append(fit, current);
  f.window.location.pathname = '/flowchartcp/flowcharts/';
  f.window.location.search = `${startDiagram ? `?diagram=${graph.id}` : ''}${camera ? `&camera=${camera.join(',')}` : ''}`;
  const document = { readyState: 'complete', querySelectorAll: () => [root], createElement: tag => new Element(tag), addEventListener() {} };
  return { ...f, root, controls, panel, opener, label, views, fit, current, document };
}
function approximately(actual, expected, message) { assert(Math.abs(actual - expected) < 1e-6, `${message ?? ''}: ${actual} != ${expected}`); }

async function splitDiagramModules(temp) {
  await compileLocalModules(site, temp);
  const question = (id, answers) => ({ id, type: 'question', title: `質問 ${id}`, answers });
  const result = id => ({ id, type: 'result', title: '候補', techniques: ['binary-search'], conditions: ['適用条件を確認する'] });
  const route = (id, graph, continuation = false) => ({ id, type: 'route', title: '続きの質問へ', graph, ...(continuation ? { continuation: true } : {}) });
  const graphs = [
    { id: 'former-field', title: '分野', description: '分野の入口', root: 'root', entry: true,
      legacyEntryChoices: { former: { answer: 'category', graph: 'category' } },
      nodes: [question('root', { category: 'category-route', unknown: 'uncertain' }), route('category-route', 'category'), result('uncertain')] },
    { id: 'category', title: '分類', description: '分類の入口', root: 'root', nodes: [
      question('root', { former: 'condition', unknown: 'uncertain' }), question('condition', { yes: 'detail-route', no: 'uncertain', unknown: 'uncertain' }),
      route('detail-route', 'detail-a', true), result('uncertain')] },
    { id: 'detail-a', title: '詳しい条件', description: '詳しい条件', root: 'detail-route', nodes: [
      question('detail-route', { yes: 'next-route', no: 'uncertain', unknown: 'uncertain' }), route('next-route', 'detail-b', true), result('uncertain')] },
    { id: 'detail-b', title: '最後の条件', description: '最後の条件', root: 'next-route', nodes: [
      question('next-route', { yes: 'candidate', no: 'uncertain', unknown: 'uncertain' }), result('candidate'), result('uncertain')] },
  ];
  const modulePath = path.join(temp, 'flow.js'), source = await readFile(modulePath, 'utf8');
  const updated = source.replace(/^const rawGraphs = .+;$/m, `const rawGraphs = ${JSON.stringify(graphs)};`);
  assert.notEqual(updated, source, 'the compiled fixture uses isolated diagram data');
  await writeFile(modulePath, updated);
  const flow = await import(pathToFileURL(modulePath).href);
  const viewer = await import(pathToFileURL(path.join(temp, 'diagram-viewer.js')).href);
  const standalone = (await readFile(path.join(temp, 'diagram-viewer-client.js'), 'utf8')).replace(/^import .+;\s*$/gm, '');
  const main = (await readFile(path.join(temp, 'flow-client.js'), 'utf8')).replace(/^import .+;\s*$/gm, '');
  return { flow, viewer, standalone, main };
}

test('standalone diagrams share the SVG source, keep routes and support a custom base without the site layout', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'flowchartcp-viewer-html-'));
  try {
    await compileLocalModules(site, temp);
    const flow = await import(pathToFileURL(path.join(temp, 'flow.js')).href);
    const viewer = await import(pathToFileURL(path.join(temp, 'diagram-viewer.js')).href);
    for (const graph of [flow.graphs[0], flow.graphs.find(graph => graph.nodes.some(node => node.type === 'route')), flow.graphs.at(-1)]) {
      const html = viewer.renderDiagramViewerHtml(graph, '/other-base/');
      assert.equal((html.match(/<svg\b/g) ?? []).length, 1);
      assert(!/<(?:header|aside|dialog)\b/.test(html));
      assert(html.includes(`data-flow-svg="${graph.id}"`));
      assert(html.includes('/other-base/flowcharts/#diagram-'));
      for (const node of graph.nodes.filter(node => node.type === 'route')) assert(html.includes(`href="/other-base/diagrams/${node.graph}/"`));
      for (const node of graph.nodes.filter(node => node.type === 'result')) for (const technique of node.techniques) assert(html.includes(`/other-base/techniques/${technique}/`));
    }
    const main = flow.renderFlowHtml();
    assert.equal((main.match(/data-diagram-open=/g) ?? []).length, flow.graphs.length);
    assert(!main.includes('data-flow-fullscreen'));
    assert.equal(viewer.normalizeDiagramBase('/'), '/');
    const original = [0, 0, 1000, 800];
    for (const invalid of ['NaN,0,100,100', '0,0,-100,100', '0,0,0,100', '0,0,1e300,100', 'Infinity,0,100,100', '1000000000,0,100,100']) assert.equal(viewer.parseDiagramCamera(invalid, original), undefined);
    assert.equal(viewer.diagramState('strings', flow.serializeFlowHash(flow.initialState('ranges'))).graph, 'strings');
    const fractional = [0, 0, 5341, 3000], limit = viewer.diagramZoomLimits(fractional).min;
    const limited = [2.5, 8.25, limit, limit * .6];
    const roundtrip = new URL(viewer.diagramViewerUrl('ranges', '/', undefined, limited), 'https://flowchartcp.invalid');
    assert.deepEqual(viewer.parseDiagramCamera(roundtrip.searchParams.get('camera'), fractional), limited);
  } finally { await rm(temp, { recursive: true, force: true }); }
});

test('actual viewer handlers zoom under the wheel pointer, clamp, drag, pinch and restore the answer path', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'flowchartcp-viewer-client-'));
  try {
    await compileLocalModules(site, temp);
    const flow = await import(pathToFileURL(path.join(temp, 'flow.js')).href);
    const viewer = await import(pathToFileURL(path.join(temp, 'diagram-viewer.js')).href);
    const source = (await readFile(path.join(temp, 'diagram-viewer-client.js'), 'utf8')).replace(/^import .+;\s*$/gm, '');
    const graph = flow.getGraph('ranges'), answer = flow.getNodeOptions(flow.getNode(graph, graph.root))[0].id;
    const state = flow.answerState(flow.initialState(graph.id), answer);
    const f = fixture(flow, viewer, graph, state);
    runInNewContext(source, { ...flow, ...viewer, window: f.window, document: f.document, Element, DOMPoint: Point, URLSearchParams });
    assert(f.buttons.every(button => !button.hidden));
    assert.equal(f.viewport.handlers.wheel[0].options.passive, false);
    const evaluation = flow.evaluateState(state), current = f.svg.querySelectorAll('[data-node]').find(node => node.dataset.node === evaluation.current.id);
    assert.equal(current.getAttribute('aria-current'), 'step');
    assert(current.classes.has('is-current'));
    assert.deepEqual(flow.parseFlowHash(new URL(f.back.href, 'https://flowchartcp.invalid').hash), state);
    if (evaluation.current.type === 'route') {
      const link = f.svg.querySelectorAll('[data-route]').find(link => link.dataset.route === evaluation.current.graph);
      const next = flow.parseFlowHash(new URL(link.getAttribute('href'), 'https://flowchartcp.invalid').hash);
      assert.equal(next.graph, evaluation.current.graph); assert.equal(next.trail[0].graph, graph.id);
    }
    const before = f.box(), screen = { x: 470, y: 260 };
    const point = new Point(screen.x, screen.y).matrixTransform(f.svg.getScreenCTM().inverse());
    const event = f.viewport.emit('wheel', { clientX: screen.x, clientY: screen.y, deltaY: -120, deltaMode: 0 });
    assert(event.prevented); assert(f.box()[2] < before[2]);
    const afterScreen = new Point(point.x, point.y).matrixTransform(f.svg.getScreenCTM());
    approximately(afterScreen.x, screen.x, 'wheel x anchor'); approximately(afterScreen.y, screen.y, 'wheel y anchor');
    const zoomed = f.box()[2]; f.viewport.emit('wheel', { clientX: screen.x, clientY: screen.y, deltaY: 3, deltaMode: 1 }); assert(f.box()[2] > zoomed);
    for (let i = 0; i < 12; i++) f.viewport.emit('wheel', { clientX: 450, clientY: 250, deltaY: -999999, deltaMode: 0, ctrlKey: true });
    approximately(f.box()[2], viewer.diagramZoomLimits(f.original).min, 'maximum zoom');
    for (let i = 0; i < 12; i++) f.viewport.emit('wheel', { clientX: 450, clientY: 250, deltaY: 999999, deltaMode: 2 });
    approximately(f.box()[2], viewer.diagramZoomLimits(f.original).max, 'minimum zoom');
    f.buttons[2].emit('click'); assert.deepEqual(f.box(), f.original);
    f.viewport.emit('keydown', { key: '+' }); assert(f.box()[2] < f.original[2]);
    f.viewport.emit('keydown', { key: '0' }); assert.deepEqual(f.box(), f.original);
    const start = f.box();
    f.viewport.emit('pointerdown', { pointerId: 1, clientX: 420, clientY: 220 });
    f.viewport.emit('pointermove', { pointerId: 1, clientX: 470, clientY: 250 });
    assert(f.box()[0] < start[0]); assert(f.box()[1] < start[1]); assert.equal(f.box()[2], start[2]);
    f.viewport.emit('pointerup', { pointerId: 1 }); assert(!f.viewport.classes.has('is-dragging'));
    const click = f.viewport.emit('click'); assert(click.prevented);
    f.buttons[2].emit('click');
    f.viewport.emit('pointerdown', { pointerId: 1, clientX: 400, clientY: 250 });
    f.viewport.emit('pointerdown', { pointerId: 2, clientX: 600, clientY: 250 });
    f.viewport.emit('pointermove', { pointerId: 1, clientX: 350, clientY: 250 });
    f.viewport.emit('pointermove', { pointerId: 2, clientX: 650, clientY: 250 });
    approximately(f.box()[2], f.original[2] * 2 / 3, 'pinch zoom');
    f.viewport.emit('pointercancel', { pointerId: 2 }); f.viewport.emit('lostpointercapture', { pointerId: 1 });
    let historyWrites = 0;
    const replaceState = f.window.history.replaceState;
    f.window.history.replaceState = (...args) => { ++historyWrites; replaceState(...args); };
    for (let i = 0; i < 1000; ++i) f.viewport.emit('wheel', { clientX: 450, clientY: 250, deltaY: i % 2 ? 1 : -1, deltaMode: 0 });
    assert.equal(historyWrites, 0, 'continuous wheel input does not flood the History API');
    f.window.flushTimers();
    assert.equal(historyWrites, 1);
    const persisted = new URL(f.window.location.href);
    assert.equal(persisted.pathname, `/flowchartcp/diagrams/${graph.id}/`);
    for (let i = 0; i < 4; ++i) assert(Math.abs(Number(persisted.searchParams.get('camera').split(',')[i]) - f.box()[i]) < .001);
    const final = f.box(), returned = new URL(f.back.href, 'https://flowchartcp.invalid');
    assert.equal(returned.searchParams.get('diagram'), graph.id);
    const restored = viewer.parseDiagramCamera(returned.searchParams.get('camera'), f.original);
    for (let i = 0; i < 4; i++) assert(Math.abs(restored[i] - final[i]) < 0.001);
    assert.deepEqual(flow.parseFlowHash(returned.hash), state);
    // A direct shared viewer URL restores the camera and path after reload.
    const second = fixture(flow, viewer, graph, state, final);
    runInNewContext(source, { ...flow, ...viewer, window: second.window, document: second.document, Element, DOMPoint: Point, URLSearchParams });
    for (let i = 0; i < 4; i++) assert(Math.abs(second.box()[i] - final[i]) < 0.001);
    assert.equal(second.svg.querySelectorAll('[data-node]').find(node => node.dataset.node === evaluation.current.id).getAttribute('aria-current'), 'step');
  } finally { await rm(temp, { recursive: true, force: true }); }
});

test('actual main-page handlers restore the viewer camera and create a wheel-updated diagram link', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'flowchartcp-main-camera-'));
  try {
    await compileLocalModules(site, temp);
    const flow = await import(pathToFileURL(path.join(temp, 'flow.js')).href);
    const viewer = await import(pathToFileURL(path.join(temp, 'diagram-viewer.js')).href);
    const source = (await readFile(path.join(temp, 'flow-client.js'), 'utf8')).replace(/^import .+;\s*$/gm, '');
    const graph = flow.getGraph('ranges'), state = flow.answerState(flow.initialState(graph.id), flow.getNodeOptions(flow.getNode(graph, graph.root))[0].id);
    const original = flow.renderFlowSvg(graph).match(/viewBox="([^"]+)"/)[1].split(' ').map(Number);
    const camera = [original[0] + 55, original[1] - 30, original[2] * .8, original[3] * .8];
    const f = mainFixture(flow, viewer, graph, state, camera);
    const { controls, opener } = f;
    runInNewContext(source, { ...flow, ...viewer, window: f.window, document: f.document, Element, DOMPoint: Point, URLSearchParams });
    assert.deepEqual(f.box(), camera); assert.equal(controls.questionPanel.hidden, true);
    let opened = new URL(opener.href, 'https://flowchartcp.invalid');
    assert.equal(opened.pathname, `/flowchartcp/diagrams/${graph.id}/`);
    assert.deepEqual(flow.parseFlowHash(opened.hash), state);
    const handed = viewer.parseDiagramCamera(opened.searchParams.get('camera'), f.original);
    for (let i=0;i<4;i++) assert(Math.abs(handed[i] - camera[i]) < .001);
    const screen = { x: 480, y: 280 }, point = new Point(screen.x, screen.y).matrixTransform(f.svg.getScreenCTM().inverse());
    const event = f.viewport.emit('wheel', { clientX: screen.x, clientY: screen.y, deltaY: -100, deltaMode: 0 });
    assert(event.prevented); assert.equal(f.viewport.handlers.wheel[0].options.passive, false);
    const anchored = new Point(point.x, point.y).matrixTransform(f.svg.getScreenCTM());
    approximately(anchored.x, screen.x, 'main wheel x'); approximately(anchored.y, screen.y, 'main wheel y');
    assert(f.box()[2] < camera[2]);
    opened = new URL(opener.href, 'https://flowchartcp.invalid');
    const passed = viewer.parseDiagramCamera(opened.searchParams.get('camera'), f.original);
    for (let i=0;i<4;i++) assert(Math.abs(passed[i] - f.box()[i]) < .001);
    assert.deepEqual(flow.parseFlowHash(opened.hash), state);
  } finally { await rm(temp, { recursive: true, force: true }); }
});

test('a direct viewer initially frames the current node at readable size on desktop and mobile; fit remains explicit', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'flowchartcp-viewer-readable-'));
  try {
    await compileLocalModules(site, temp);
    const flow = await import(pathToFileURL(path.join(temp, 'flow.js')).href);
    const viewer = await import(pathToFileURL(path.join(temp, 'diagram-viewer.js')).href);
    const source = (await readFile(path.join(temp, 'diagram-viewer-client.js'), 'utf8')).replace(/^import .+;\s*$/gm, '');
    const graph = flow.getGraph('dp');
    for (const [width, height] of [[1000, 600], [390, 844]]) {
      const state = flow.initialState(graph.id), f = fixture(flow, viewer, graph, state);
      f.viewport.clientWidth = width; f.viewport.clientHeight = height;
      runInNewContext(source, { ...flow, ...viewer, window: f.window, document: f.document, Element, DOMPoint: Point, URLSearchParams });
      const node = viewer.diagramNodeBox(f.svg, graph.root), camera = f.box();
      assert(node); assert.notDeepEqual(camera, f.original);
      approximately(camera[2] / camera[3], width / height, 'initial viewport aspect');
      assert(f.svg.getScreenCTM().a * 16 >= 12, 'initial question text remains readable');
      assert(node[0] >= camera[0] && node[0] + node[2] <= camera[0] + camera[2]);
      assert(node[1] >= camera[1] && node[1] + node[3] <= camera[1] + camera[3]);
      assert.equal(f.zoom.textContent, `${viewer.diagramZoomPercent(camera, width, height)}%`);
      const passed = new URL(f.back.href, 'https://flowchartcp.invalid');
      assert(viewer.parseDiagramCamera(passed.searchParams.get('camera'), f.original), 'readable camera survives sharing');
      // A natural-aspect viewport and the original graph aspect are deliberately different.
      const point = new Point(width * .43, height * .42).matrixTransform(f.svg.getScreenCTM().inverse());
      const screen = new Point(point.x, point.y).matrixTransform(f.svg.getScreenCTM());
      f.viewport.emit('wheel', { clientX: screen.x, clientY: screen.y, deltaY: -100, deltaMode: 0 });
      const anchored = new Point(point.x, point.y).matrixTransform(f.svg.getScreenCTM());
      approximately(anchored.x, screen.x); approximately(anchored.y, screen.y);
      f.buttons[2].emit('click'); assert.deepEqual(f.box(), f.original);
      assert.equal(f.zoom.textContent, `${Math.round(Math.min(width / f.original[2], height / f.original[3]) * 100)}%`);
    }
    // Very wide graphs still permit a natural-size view and keep that camera after URL parsing.
    const huge = [0, 0, 100000, 2000], node = [50000, 100, 320, 180];
    const natural = viewer.readableDiagramBox(huge, node, 390, 844);
    assert(natural[2] < huge[2] / 64);
    assert(viewer.parseDiagramCamera(natural.join(','), huge));
    approximately(viewer.diagramZoomPercent([0, 0, 1000, 10000], 1000, 600), 6, 'tall camera uses height scale');
    assert.equal(viewer.readableDiagramBox(huge, node, 0, 0), undefined);
  } finally { await rm(temp, { recursive: true, force: true }); }
});

test('switching from questions frames the root readably; an explicit fit and manual camera survive later view changes', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'flowchartcp-main-readable-'));
  try {
    await compileLocalModules(site, temp);
    const flow = await import(pathToFileURL(path.join(temp, 'flow.js')).href);
    const viewer = await import(pathToFileURL(path.join(temp, 'diagram-viewer.js')).href);
    const source = (await readFile(path.join(temp, 'flow-client.js'), 'utf8')).replace(/^import .+;\s*$/gm, '');
    const graph = flow.getGraph('dp'), state = flow.initialState(graph.id);
    const f = mainFixture(flow, viewer, graph, state, undefined, false);
    f.viewport.clientWidth = 390; f.viewport.clientHeight = 680;
    runInNewContext(source, { ...flow, ...viewer, window: f.window, document: f.document, Element, DOMPoint: Point, URLSearchParams });
    assert.equal(f.controls.diagrams.hidden, true); assert.deepEqual(f.box(), f.original);
    f.views[1].emit('click');
    assert.equal(f.controls.diagrams.hidden, false);
    assert(f.svg.getScreenCTM().a * 16 >= 12);
    approximately(f.box()[2] / f.box()[3], 390 / 680);
    f.viewport.clientWidth = 900; f.viewport.clientHeight = 600; f.window.handlers.resize();
    approximately(f.box()[2] / f.box()[3], 900 / 600, 'automatic frame follows viewport resize');
    f.root.emit('click', { target: f.fit }); assert.deepEqual(f.box(), f.original);
    f.views[0].emit('click'); f.views[1].emit('click'); assert.deepEqual(f.box(), f.original);
    f.root.emit('click', { target: f.current }); assert.notDeepEqual(f.box(), f.original);
    f.viewport.emit('wheel', { clientX: 480, clientY: 280, deltaY: -120, deltaMode: 0 });
    const moved = f.box(); f.views[0].emit('click'); f.views[1].emit('click'); assert.deepEqual(f.box(), moved);
    assert.equal(f.label.textContent, `${viewer.diagramZoomPercent(moved, 900, 600)}%`);
  } finally { await rm(temp, { recursive: true, force: true }); }
});

test('old standalone field URLs redirect only their own legacy answers and discard the obsolete camera', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'flowchartcp-viewer-legacy-'));
  try {
    await compileLocalModules(site, temp);
    const flow = await import(pathToFileURL(path.join(temp, 'flow.js')).href);
    const viewer = await import(pathToFileURL(path.join(temp, 'diagram-viewer.js')).href);
    const source = (await readFile(path.join(temp, 'diagram-viewer-client.js'), 'utf8')).replace(/^import .+;\s*$/gm, '');
    const cases = [['math', 'xor,y'], ['geometry', 'far'], ['dp', 'small-set'], ['graphs', 'distance']];
    for (const [id, steps] of cases) {
      const graph = flow.getGraph(id), hash = `#flow=${id}&steps=c:${steps}`, expected = flow.parseFlowHash(hash);
      assert.notEqual(expected.graph, id);
      assert.deepEqual(viewer.diagramState(id, hash), expected);
      const f = fixture(flow, viewer, graph, flow.initialState(id), [20, 30, 1000, 600]);
      f.window.location.hash = hash;
      runInNewContext(source, { ...flow, ...viewer, window: f.window, document: f.document, Element, DOMPoint: Point, URLSearchParams });
      assert.equal(f.window.replacements.length, 1);
      const redirect = new URL(f.window.replacements[0], 'https://flowchartcp.invalid');
      assert.equal(redirect.pathname, `/flowchartcp/diagrams/${expected.graph}/`);
      assert.equal(redirect.search, '', 'coordinates from the old large chart are discarded');
      assert.deepEqual(flow.parseFlowHash(redirect.hash), expected);
      assert.equal(f.root.dataset.enhanced, undefined, 'the mismatched old chart is not initialized');
      const target = fixture(flow, viewer, flow.getGraph(expected.graph), expected);
      runInNewContext(source, { ...flow, ...viewer, window: target.window, document: target.document, Element, DOMPoint: Point, URLSearchParams });
      assert.equal(target.window.replacements.length, 0);
      const current = flow.evaluateState(expected).current;
      assert.equal(target.svg.querySelector(`[data-node="${current.id}"]`).getAttribute('aria-current'), 'step');
      assert(target.svg.getScreenCTM().a * 16 >= 12);
    }
    const math = flow.getGraph('math'), legacyHash = '#flow=math&steps=c:xor,y';
    for (const unrelated of ['#flow=strings&steps=', flow.serializeFlowHash(flow.parseFlowHash(legacyHash)), '#flow=math&steps=c:unrecognized']) {
      assert.deepEqual(viewer.diagramState('math', unrelated), flow.initialState('math'));
      const f = fixture(flow, viewer, math, flow.initialState('math')); f.window.location.hash = unrelated;
      runInNewContext(source, { ...flow, ...viewer, window: f.window, document: f.document, Element, DOMPoint: Point, URLSearchParams });
      assert.equal(f.window.replacements.length, 0);
      assert.equal(f.svg.querySelector(`[data-node="${math.root}"]`).getAttribute('aria-current'), 'step');
    }
    // Pasting an old fragment after initialization follows the same safe redirect path.
    const pasted = fixture(flow, viewer, math, flow.initialState('math'));
    runInNewContext(source, { ...flow, ...viewer, window: pasted.window, document: pasted.document, Element, DOMPoint: Point, URLSearchParams });
    pasted.window.location.hash = legacyHash; pasted.window.handlers.hashchange();
    assert.equal(pasted.window.replacements.length, 1);
    pasted.window.flushTimers();
    assert.equal(pasted.window.location.hash, legacyHash, 'a pending old camera write cannot overwrite the redirect');
  } finally { await rm(temp, { recursive: true, force: true }); }
});

test('old main-page diagram intent and answers migrate to the split diagram without using its old camera', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'flowchartcp-main-legacy-'));
  try {
    await compileLocalModules(site, temp);
    const flow = await import(pathToFileURL(path.join(temp, 'flow.js')).href);
    const viewer = await import(pathToFileURL(path.join(temp, 'diagram-viewer.js')).href);
    const source = (await readFile(path.join(temp, 'flow-client.js'), 'utf8')).replace(/^import .+;\s*$/gm, '');
    for (const [id, steps] of [['math', 'xor,y'], ['geometry', 'far'], ['dp', 'small-set'], ['graphs', 'distance']]) {
      const hash = `#flow=${id}&steps=c:${steps}`, expected = flow.parseFlowHash(hash);
      const graph = flow.getGraph(expected.graph), oldCamera = [20, 30, 1000, 600];
      const f = mainFixture(flow, viewer, graph, expected, undefined);
      f.window.location.hash = hash;
      f.window.location.search = `?diagram=${id}&camera=${oldCamera.join(',')}`;
      assert(viewer.parseDiagramCamera(oldCamera.join(','), f.original), 'the obsolete camera would otherwise be accepted');
      runInNewContext(source, { ...flow, ...viewer, window: f.window, document: f.document, Element, DOMPoint: Point, URLSearchParams });
      assert.equal(f.controls.questionPanel.hidden, true);
      assert.equal(f.controls.diagrams.hidden, false);
      assert.equal(f.controls.graphSelect.value, expected.graph);
      const node = viewer.diagramNodeBox(f.svg, flow.evaluateState(expected).current.id);
      assert.deepEqual(f.box(), viewer.readableDiagramBox(f.original, node, 1000, 600));
      assert.notDeepEqual(f.box(), oldCamera);
      assert(f.svg.getScreenCTM().a * 16 >= 12);
      assert.equal(new URLSearchParams(f.window.location.search).get('diagram'), expected.graph);
      assert.equal(new URLSearchParams(f.window.location.search).get('camera'), null);
      assert.deepEqual(flow.parseFlowHash(f.window.location.hash), expected);
      // Reloading the normalized URL preserves diagram mode and the migrated answer trail.
      const reloaded = mainFixture(flow, viewer, graph, expected, undefined);
      reloaded.window.location.hash = f.window.location.hash; reloaded.window.location.search = f.window.location.search;
      runInNewContext(source, { ...flow, ...viewer, window: reloaded.window, document: reloaded.document, Element, DOMPoint: Point, URLSearchParams });
      assert.equal(reloaded.controls.questionPanel.hidden, true);
      assert.deepEqual(flow.parseFlowHash(reloaded.window.location.hash), expected);
    }
  } finally { await rm(temp, { recursive: true, force: true }); }
});

test('a camera outside a resized diagram falls back to its readable root or unknown question in both clients', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'flowchartcp-outside-camera-'));
  try {
    await compileLocalModules(site, temp);
    const flow = await import(pathToFileURL(path.join(temp, 'flow.js')).href);
    const viewer = await import(pathToFileURL(path.join(temp, 'diagram-viewer.js')).href);
    const client = (await readFile(path.join(temp, 'diagram-viewer-client.js'), 'utf8')).replace(/^import .+;\s*$/gm, '');
    const main = (await readFile(path.join(temp, 'flow-client.js'), 'utf8')).replace(/^import .+;\s*$/gm, '');
    const original = [100, 200, 1000, 600];
    for (const outside of [[1100, 200, 400, 300], [-300, 200, 400, 300], [100, 800, 400, 300], [100, -100, 400, 300]]) {
      assert.equal(viewer.parseDiagramCamera(outside.join(','), original), undefined, 'a boundary touch has no visible area');
    }
    for (const partial of [[1050, 200, 400, 300], [-250, 200, 400, 300], [100, 750, 400, 300], [100, -50, 400, 300]]) {
      assert.deepEqual(viewer.parseDiagramCamera(partial.join(','), original), partial, 'partial deliberate panning is preserved');
    }
    for (const id of ['math', 'geometry', 'dp', 'graphs']) {
      const graph = flow.getGraph(id);
      for (const state of [flow.initialState(id), flow.answerState(flow.initialState(id), 'unknown')]) {
        const f = fixture(flow, viewer, graph, state);
        const obsolete = [f.original[0] + f.original[2] + 40, f.original[1], 1000, 600];
        f.window.location.search = `?camera=${obsolete.join(',')}`;
        runInNewContext(client, { ...flow, ...viewer, window: f.window, document: f.document, Element, DOMPoint: Point, URLSearchParams });
        const node = viewer.diagramNodeBox(f.svg, flow.evaluateState(state).current.id);
        assert.deepEqual(f.box(), viewer.readableDiagramBox(f.original, node, 1000, 600));
        assert.notDeepEqual(f.box(), obsolete); assert.equal(f.window.replacements.length, 0);
        assert.equal(f.svg.querySelector(`[data-node="${flow.evaluateState(state).current.id}"]`).getAttribute('aria-current'), 'step');
        const ordinary = mainFixture(flow, viewer, graph, state, obsolete);
        runInNewContext(main, { ...flow, ...viewer, window: ordinary.window, document: ordinary.document, Element, DOMPoint: Point, URLSearchParams });
        const current = viewer.diagramNodeBox(ordinary.svg, flow.evaluateState(state).current.id);
        assert.deepEqual(ordinary.box(), viewer.readableDiagramBox(ordinary.original, current, 1000, 600));
        assert.equal(ordinary.controls.questionPanel.hidden, true);
        assert.deepEqual(flow.parseFlowHash(ordinary.window.location.hash), state);
      }
    }
  } finally { await rm(temp, { recursive: true, force: true }); }
});

test('old answers migrate through a field category and several continuation diagrams in both clients', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'flowchartcp-multisplit-viewers-'));
  try {
    const { flow, viewer, standalone, main } = await splitDiagramModules(temp);
    const cases = [
      ['former-field', '#flow=former-field&steps=c:former,y,y,y', 3],
      ['category', '#flow=category&steps=c:former,y,y,y', 2],
      ['detail-a', '#flow=detail-a&steps=y,y', 1],
    ];
    for (const [id, hash, trailLength] of cases) {
      const expected = flow.parseFlowHash(hash);
      assert.equal(expected.graph, 'detail-b');
      assert.equal(expected.trail.length, trailLength);
      assert.equal(flow.evaluateState(expected).current.id, 'candidate');
      assert.deepEqual(viewer.legacyDiagramState(id, hash), expected);
      assert.deepEqual(viewer.diagramState(id, hash), expected);

      const f = fixture(flow, viewer, flow.getGraph(id), flow.initialState(id), [20, 30, 1000, 600]);
      f.window.location.hash = hash;
      runInNewContext(standalone, { ...flow, ...viewer, window: f.window, document: f.document, Element, DOMPoint: Point, URLSearchParams });
      assert.equal(f.window.replacements.length, 1);
      const redirect = new URL(f.window.replacements[0], 'https://flowchartcp.invalid');
      assert.equal(redirect.pathname, '/flowchartcp/diagrams/detail-b/');
      assert.equal(redirect.search, '', 'each split discards the old coordinate system');
      assert.deepEqual(flow.parseFlowHash(redirect.hash), expected);
      assert.equal(f.root.dataset.enhanced, undefined);

      const targetGraph = flow.getGraph(expected.graph), oldCamera = [20, 30, 600, 400];
      const ordinary = mainFixture(flow, viewer, targetGraph, expected);
      ordinary.window.location.hash = hash;
      ordinary.window.location.search = `?diagram=${id}&camera=${oldCamera.join(',')}`;
      runInNewContext(main, { ...flow, ...viewer, window: ordinary.window, document: ordinary.document, Element, DOMPoint: Point, URLSearchParams });
      assert.equal(ordinary.controls.questionPanel.hidden, true);
      assert.equal(ordinary.controls.graphSelect.value, expected.graph);
      assert.equal(new URLSearchParams(ordinary.window.location.search).get('diagram'), expected.graph);
      assert.equal(new URLSearchParams(ordinary.window.location.search).get('camera'), null);
      assert.deepEqual(flow.parseFlowHash(ordinary.window.location.hash), expected);
      const node = viewer.diagramNodeBox(ordinary.svg, 'candidate');
      assert.deepEqual(ordinary.box(), viewer.readableDiagramBox(ordinary.original, node, 1000, 600));

      // The corrected dedicated URL no longer redirects and restores the same current node.
      const target = fixture(flow, viewer, targetGraph, expected);
      runInNewContext(standalone, { ...flow, ...viewer, window: target.window, document: target.document, Element, DOMPoint: Point, URLSearchParams });
      assert.equal(target.window.replacements.length, 0);
      assert.equal(target.svg.querySelector('[data-node="candidate"]').getAttribute('aria-current'), 'step');
      assert(target.svg.getScreenCTM().a * 16 >= 12);
    }
  } finally { await rm(temp, { recursive: true, force: true }); }
});

test('continuation migration rejects another viewer hash and an ordinary route; pasted legacy paths cancel camera writes', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'flowchartcp-multisplit-safety-'));
  try {
    const { flow, viewer, standalone } = await splitDiagramModules(temp);
    const legacy = '#flow=former-field&steps=c:former,y,y,y';
    const canonical = flow.serializeFlowHash(flow.parseFlowHash(legacy));
    for (const hash of [canonical, '#flow=category&steps=c:former,y,y,y', '#flow=former-field&steps=c:category,c:former,y,y,y']) {
      assert.equal(viewer.legacyDiagramState('former-field', hash), undefined);
      const actual = viewer.diagramState('former-field', hash);
      assert.equal(actual.graph, 'former-field');
      const f = fixture(flow, viewer, flow.getGraph('former-field'), flow.initialState('former-field'));
      f.window.location.hash = hash;
      runInNewContext(standalone, { ...flow, ...viewer, window: f.window, document: f.document, Element, DOMPoint: Point, URLSearchParams });
      assert.equal(f.window.replacements.length, 0);
    }
    const pasted = fixture(flow, viewer, flow.getGraph('former-field'), flow.initialState('former-field'));
    runInNewContext(standalone, { ...flow, ...viewer, window: pasted.window, document: pasted.document, Element, DOMPoint: Point, URLSearchParams });
    pasted.window.location.hash = legacy; pasted.window.handlers.hashchange();
    assert.equal(pasted.window.replacements.length, 1);
    pasted.window.flushTimers();
    assert.equal(pasted.window.location.hash, legacy, 'the old viewer cannot overwrite the pending redirect');
  } finally { await rm(temp, { recursive: true, force: true }); }
});

test('every authored continuation opens the right standalone and main diagram from its former answer prefix', async () => {
  const temp = await mkdtemp(path.join(tmpdir(), 'flowchartcp-authored-split-viewers-'));
  try {
    await compileLocalModules(site, temp);
    const flow = await import(pathToFileURL(path.join(temp, 'flow.js')).href);
    const viewer = await import(pathToFileURL(path.join(temp, 'diagram-viewer.js')).href);
    const standalone = (await readFile(path.join(temp, 'diagram-viewer-client.js'), 'utf8')).replace(/^import .+;\s*$/gm, '');
    const main = (await readFile(path.join(temp, 'flow-client.js'), 'utf8')).replace(/^import .+;\s*$/gm, '');
    let checked = 0;
    for (const graph of flow.graphs) {
      const queue = [{ node: flow.getNode(graph, graph.root), answers: [] }], seen = new Set();
      for (const { node, answers } of queue) {
        if (seen.has(node.id)) continue;
        seen.add(node.id);
        if (node.type === 'question') {
          for (const option of flow.getNodeOptions(node)) queue.push({ node: flow.getNode(graph, node.answers[option.id]), answers: [...answers, option.id] });
          continue;
        }
        if (node.type !== 'route' || node.continuation !== true) continue;
        checked++;
        const steps = answers.map(answer => ({ yes: 'y', no: 'n', unknown: 'u' })[answer] ?? `c:${encodeURIComponent(answer)}`).join(',');
        const hash = `#flow=${graph.id}&steps=${steps}`, expected = flow.parseFlowHash(hash);
        assert.equal(expected.graph, node.graph, `${graph.id}/${node.id} enters its separated diagram`);
        const target = flow.getGraph(expected.graph), current = flow.evaluateState(expected).current;
        assert.equal(current.id, target.root);
        const f = fixture(flow, viewer, graph, flow.initialState(graph.id), [20, 30, 1000, 600]);
        f.window.location.hash = hash;
        runInNewContext(standalone, { ...flow, ...viewer, window: f.window, document: f.document, Element, DOMPoint: Point, URLSearchParams });
        assert.equal(f.window.replacements.length, 1);
        const destination = new URL(f.window.replacements[0], 'https://flowchartcp.invalid');
        assert.equal(destination.pathname, `/flowchartcp/diagrams/${target.id}/`);
        assert.equal(destination.search, '');
        assert.deepEqual(flow.parseFlowHash(destination.hash), expected);

        const ordinary = mainFixture(flow, viewer, target, expected);
        ordinary.window.location.hash = hash;
        ordinary.window.location.search = `?diagram=${graph.id}&camera=20,30,1000,600`;
        runInNewContext(main, { ...flow, ...viewer, window: ordinary.window, document: ordinary.document, Element, DOMPoint: Point, URLSearchParams });
        assert.equal(ordinary.controls.questionPanel.hidden, true);
        assert.equal(ordinary.controls.graphSelect.value, target.id);
        assert.equal(new URLSearchParams(ordinary.window.location.search).get('diagram'), target.id);
        assert.equal(new URLSearchParams(ordinary.window.location.search).get('camera'), null);
        assert.deepEqual(flow.parseFlowHash(ordinary.window.location.hash), expected);
        const currentBox = viewer.diagramNodeBox(ordinary.svg, current.id);
        assert.deepEqual(ordinary.box(), viewer.readableDiagramBox(ordinary.original, currentBox, 1000, 600));
      }
    }
    assert(checked > 0, 'authored flow data contains separated detailed questions');
  } finally { await rm(temp, { recursive: true, force: true }); }
});
