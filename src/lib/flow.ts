import rawGraphs from '../../data/flows.json' with { type: 'json' };
import { layoutLayeredGraph } from './flow-layout.ts';

export type FlowAnswer = string;
export type FlowOption = { id: string; label: string };
export type FlowNode = {
  id: string;
  type: 'question' | 'result' | 'route';
  title: string;
  explanation?: string;
  answers?: Record<FlowAnswer, string>;
  options?: FlowOption[];
  techniques?: string[];
  conditions?: string[];
  graph?: string;
  continuation?: boolean;
};
export type FlowLegacyEntry = { answer: string; graph: string };
export type FlowGraph = { id: string; title: string; description: string; root: string; nodes: FlowNode[]; entry?: boolean; legacyEntryChoices?: Record<string, FlowLegacyEntry> };
export type FlowContext = { graph: string; answers: FlowAnswer[] };
export type FlowState = FlowContext & { trail?: FlowContext[] };
export type FlowEvaluation = {
  graph: FlowGraph;
  current: FlowNode;
  path: FlowNode[];
  edges: { from: string; answer: FlowAnswer; to: string }[];
  answers: FlowAnswer[];
};
export const graphs = rawGraphs as FlowGraph[];
export const answerLabels: Record<FlowAnswer, string> = { yes: 'はい', no: 'いいえ', unknown: 'わからない' };
export function getNodeOptions(node: FlowNode): FlowOption[] {
  return node.options ?? Object.keys(node.answers ?? {}).map((id) => ({ id, label: answerLabels[id] ?? id }));
}
export function getAnswerLabel(node: FlowNode, id: string): string {
  return getNodeOptions(node).find((option) => option.id === id)?.label ?? answerLabels[id] ?? id;
}
const graphMap = new Map(graphs.map((graph) => [graph.id, graph]));
export const entryGraphs = graphs.filter((graph) => graph.entry === true);
const fallbackGraph = entryGraphs[0] ?? graphs.find((graph) => graph.id === 'ranges') ?? graphs[0]!;

export const flowGroups = entryGraphs.map((entry) => ({ entry, graphs: [] as FlowGraph[] }));
const graphDomain = new Map(entryGraphs.map((graph) => [graph.id, graph.id]));
for (const { entry } of flowGroups) {
  const visited = new Set<string>();
  const queue = [entry.id];
  for (let i = 0; i < queue.length; i++) {
    const id = queue[i]!;
    if (visited.has(id) || (graphDomain.has(id) && graphDomain.get(id) !== entry.id)) continue;
    visited.add(id);
    if (!graphDomain.has(id)) graphDomain.set(id, entry.id);
    for (const node of graphMap.get(id)?.nodes ?? []) if (node.type === 'route' && node.graph) queue.push(node.graph);
  }
}
for (const graph of graphs) flowGroups.find((group) => group.entry.id === graphDomain.get(graph.id))?.graphs.push(graph);

export function getFlowDomainId(state: FlowState): string {
  const first = state.trail?.[0]?.graph ?? state.graph;
  return graphDomain.get(first) ?? graphDomain.get(state.graph) ?? fallbackGraph.id;
}

export function getGraph(id: string): FlowGraph {
  return graphMap.get(id) ?? fallbackGraph;
}
export function getNode(graph: FlowGraph, id: string): FlowNode {
  const node = graph.nodes.find((item) => item.id === id);
  if (!node) throw new Error(`Unknown flow node: ${graph.id}/${id}`);
  return node;
}
export function initialState(graph = fallbackGraph.id): FlowState {
  return { graph: getGraph(graph).id, answers: [] };
}

/** Validate one chart without following a route or trusting URL node IDs. */
function sanitizeContext(value: unknown): FlowContext {
  const input = value && typeof value === 'object' ? value as { graph?: unknown; answers?: unknown } : {};
  const graph = typeof input.graph === 'string' ? getGraph(input.graph) : fallbackGraph;
  let current = getNode(graph, graph.root);
  const answers: FlowAnswer[] = [];
  if (Array.isArray(input.answers)) {
    for (const answer of input.answers.slice(0, 128)) {
      if (current.type !== 'question' || typeof answer !== 'string' || !getNodeOptions(current).some(option => option.id === answer) || !current.answers) break;
      const next = current.answers[answer];
      if (!graph.nodes.some(node => node.id === next)) break;
      answers.push(answer); current = getNode(graph, next);
    }
  }
  return { graph: graph.id, answers };
}
function contextEnd(context: FlowContext): FlowNode {
  const graph = getGraph(context.graph);
  let node = getNode(graph, graph.root);
  for (const answer of context.answers) node = getNode(graph, node.answers![answer]);
  return node;
}
function legacyEntry(graph: FlowGraph, answer: unknown): FlowLegacyEntry | undefined {
  if (typeof answer !== 'string' || !graph.legacyEntryChoices || !Object.hasOwn(graph.legacyEntryChoices, answer)) return undefined;
  const entry = graph.legacyEntryChoices[answer];
  if (!entry || typeof entry.answer !== 'string' || typeof entry.graph !== 'string' || !graphMap.has(entry.graph)) return undefined;
  const root = getNode(graph, graph.root);
  const route = root.answers?.[entry.answer];
  const target = graph.nodes.find(node => node.id === route);
  return target?.type === 'route' && target.graph === entry.graph ? entry : undefined;
}
/** Replay former answers across chart boundaries without entering ordinary routes. */
function migrateContext(value: unknown, followContinuationAtEnd = true): FlowContext[] {
  const input = value && typeof value === 'object' ? value as { graph?: unknown; answers?: unknown } : {};
  let graph = typeof input.graph === 'string' ? getGraph(input.graph) : fallbackGraph;
  let current = getNode(graph, graph.root);
  const supplied = Array.isArray(input.answers) ? input.answers.slice(0, 128) : [];
  const contexts: FlowContext[] = [];
  const transitions = new Set<string>();
  let answers: FlowAnswer[] = [];
  let consumed = 0;
  function enter(target: FlowGraph, prefix: FlowAnswer[]): boolean {
    const key = `${graph.id}/${current.id}`;
    if (transitions.has(key) || contexts.length >= 128) return false;
    transitions.add(key);
    contexts.push({ graph: graph.id, answers: prefix });
    graph = target;
    current = getNode(graph, graph.root);
    answers = [];
    return true;
  }
  while (true) {
    const entry = current.id === graph.root && !answers.length ? legacyEntry(graph, supplied[consumed]) : undefined;
    if (entry) {
      // The former choice is still the first choice in the new category chart.
      if (!enter(getGraph(entry.graph), [entry.answer])) return [sanitizeContext(input)];
      continue;
    }
    if (current.type === 'route' && current.continuation === true && (consumed < supplied.length || followContinuationAtEnd)) {
      const target = graphMap.get(current.graph ?? '');
      // Only same-node continuations can preserve an old answer sequence.
      if (!target || target.root !== current.id) break;
      if (!enter(target, answers)) return [sanitizeContext(input)];
      continue;
    }
    if (current.type !== 'question' || consumed === supplied.length) break;
    const answer = supplied[consumed];
    if (typeof answer !== 'string' || !getNodeOptions(current).some(option => option.id === answer) || !current.answers) break;
    const next = graph.nodes.find(node => node.id === current.answers![answer]);
    if (!next) break;
    answers.push(answer);
    current = next;
    consumed++;
  }
  return [...contexts, { graph: graph.id, answers }];
}
function validTrail(trail: FlowContext[], current: FlowContext): boolean {
  return trail.every((context, index) => {
    const end = contextEnd(context);
    return end.type === 'route' && end.graph === (trail[index + 1] ?? current).graph;
  });
}

/** Replay only valid answers from the canonical roots, including old shared URLs. */
export function sanitizeState(value: unknown): FlowState {
  if (!value || typeof value !== 'object') return initialState();
  const input = value as { graph?: unknown; answers?: unknown; trail?: unknown };
  const local = migrateContext(input);
  const current = local.at(-1)!;
  // A history item already records its route boundary. Entering that final
  // continuation again would duplicate the following canonical context.
  const previous = Array.isArray(input.trail) ? input.trail.slice(0, 32).flatMap(context => migrateContext(context, false)) : [];
  let trail = [...previous, ...local.slice(0, -1)];
  // A malformed external history cannot suppress a valid local URL migration.
  if (!validTrail(trail, current)) trail = local.slice(0, -1);
  return { ...current, ...(trail.length ? { trail } : {}) };
}

export function evaluateState(value: FlowState): FlowEvaluation {
  const state = sanitizeState(value);
  const graph = getGraph(state.graph);
  let current = getNode(graph, graph.root);
  const path = [current];
  const edges: FlowEvaluation['edges'] = [];
  for (const answer of state.answers) {
    const next = current.answers![answer];
    edges.push({ from: current.id, answer, to: next });
    current = getNode(graph, next);
    path.push(current);
  }
  return { graph, current, path, edges, answers: state.answers };
}

export function answerState(value: FlowState, answer: FlowAnswer): FlowState {
  const state = sanitizeState(value);
  if (evaluateState(state).current.type !== 'question') return state;
  return sanitizeState({ ...state, answers: [...state.answers, answer] });
}

export function enterFlowRoute(value: FlowState): FlowState {
  const state = sanitizeState(value);
  const current = evaluateState(state).current;
  if (current.type !== 'route') return state;
  return sanitizeState({ graph: current.graph, answers: [], trail: [...(state.trail ?? []), { graph: state.graph, answers: state.answers }] });
}
export function backFlowState(value: FlowState): FlowState {
  const state = sanitizeState(value);
  if (state.answers.length) return sanitizeState({ ...state, answers: state.answers.slice(0, -1) });
  if (!state.trail?.length) return state;
  const previous = state.trail.at(-1)!;
  return sanitizeState({ ...previous, answers: previous.answers.slice(0, -1), trail: state.trail.slice(0, -1) });
}

export function serializeFlowHash(value: FlowState): string {
  const state = sanitizeState(value);
  const letters: Record<FlowAnswer, string> = { yes: 'y', no: 'n', unknown: 'u' };
  return `#flow=${encodeURIComponent(state.graph)}&steps=${state.answers.map((answer) => letters[answer] ?? `c:${encodeURIComponent(answer)}`).join(',')}${state.trail?.length ? `&trail=${encodeURIComponent(JSON.stringify(state.trail))}` : ''}`;
}

export function parseFlowHash(hash: string): FlowState {
  if (hash.length > 4096) return initialState();
  const values = new URLSearchParams(hash.replace(/^#/, ''));
  const graph = values.get('flow');
  if (!graph || !graphMap.has(graph)) return initialState();
  const letters: Record<string, FlowAnswer> = { y: 'yes', n: 'no', u: 'unknown' };
  const steps = values.get('steps') ?? '';
  const answers = steps ? steps.split(',').map((letter) => {
    if (letters[letter]) return letters[letter];
    if (!letter.startsWith('c:')) return 'invalid';
    try { return decodeURIComponent(letter.slice(2)); } catch { return 'invalid'; }
  }) : [];
  let trail: unknown;
  try { trail = JSON.parse(values.get('trail') ?? 'null'); } catch { trail = undefined; }
  return sanitizeState({ graph, answers, trail });
}

/** A same-viewer old URL may move only through migrations performed above. */
export function migratedFlowHash(graph: string, hash: string): FlowState | undefined {
  if (hash.length > 4096 || !graphMap.has(graph) || new URLSearchParams(hash.replace(/^#/, '')).get('flow') !== graph) return undefined;
  const state = parseFlowHash(hash);
  return state.graph !== graph ? state : undefined;
}

export type RootWalk = { graph: FlowGraph; current: FlowNode; steps: { graph: string; node: string; answer: string; target: string }[]; consumed: number };
export function walkFromRoot(choices: string[], graphId = fallbackGraph.id): RootWalk {
  let graph = getGraph(graphId);
  let current = getNode(graph, graph.root);
  const steps: RootWalk['steps'] = [];
  let consumed = 0;
  const visitedRoutes = new Set<string>();
  while (true) {
    if (current.type === 'route') {
      const key = `${graph.id}/${current.id}`;
      if (visitedRoutes.has(key)) throw new Error(`Cyclic graph route: ${key}`);
      visitedRoutes.add(key);
      graph = getGraph(current.graph!); current = getNode(graph, graph.root);
      continue;
    }
    if (current.type !== 'question' || consumed === choices.length) break;
    const answer = choices[consumed]!;
    const previousEntry = current.id === graph.root ? legacyEntry(graph, answer) : undefined;
    if (previousEntry) {
      const target = current.answers![previousEntry.answer];
      steps.push({ graph: graph.id, node: current.id, answer: previousEntry.answer, target });
      current = getNode(graph, target);
      continue;
    }
    if (!getNodeOptions(current).some((option) => option.id === answer)) throw new Error(`Invalid root choice: ${graph.id}/${current.id}/${answer}`);
    const target = current.answers![answer];
    steps.push({ graph: graph.id, node: current.id, answer, target });
    current = getNode(graph, target); consumed++;
  }
  return { graph, current, steps, consumed };
}

export function validateGraphs(input: FlowGraph[] = graphs): string[] {
  const errors: string[] = [];
  const knownGraphs = new Set(input.map((graph) => graph.id));
  if (knownGraphs.size !== input.length) errors.push('Duplicate graph ids');
  for (const graph of input) {
    const byId = new Map(graph.nodes.map((node) => [node.id, node]));
    if (byId.size !== graph.nodes.length) errors.push(`${graph.id}: duplicate node ids`);
    if (!byId.has(graph.root)) errors.push(`${graph.id}: missing root`);
    const root = byId.get(graph.root);
    for (const [oldAnswer, entry] of Object.entries(graph.legacyEntryChoices ?? {})) {
      const target = input.find(candidate => candidate.id === entry?.graph);
      const routeId = root?.answers?.[entry?.answer];
      const route = routeId ? byId.get(routeId) : undefined;
      const targetRoot = target?.nodes.find(node => node.id === target.root);
      // A category can itself have been split since the URL was shared. Each
      // following entry is checked below, and route validation rejects cycles.
      const targetAcceptsAnswer = targetRoot?.type === 'question' && (getNodeOptions(targetRoot).some(option => option.id === oldAnswer) || Boolean(target?.legacyEntryChoices && Object.hasOwn(target.legacyEntryChoices, oldAnswer)));
      if (!/^[a-z0-9-]+$/.test(oldAnswer) || root?.type !== 'question' || getNodeOptions(root).some(option => option.id === oldAnswer) || route?.type !== 'route' || route.graph !== entry?.graph || !targetAcceptsAnswer) {
        errors.push(`${graph.id}: invalid legacy entry ${oldAnswer}`);
      }
    }
    for (const node of graph.nodes) {
      if (node.type === 'question') {
        const options = getNodeOptions(node);
        if (options.length < 2 || !options.some((option) => option.id === 'unknown') || options.some((option) => !option.label.trim()) || new Set(options.map((option) => option.id)).size !== options.length) errors.push(`${graph.id}/${node.id}: valid choices and unknown choice required`);
        if (options.map((option) => option.id).sort().join(',') !== Object.keys(node.answers ?? {}).sort().join(',')) errors.push(`${graph.id}/${node.id}: choices and answer targets differ`);
        for (const { id: answer } of options) {
          if (!node.answers || !byId.has(node.answers[answer])) errors.push(`${graph.id}/${node.id}: missing ${answer} target`);
        }
      }
      if (node.type === 'result' && (!node.techniques?.length || !node.conditions?.length)) errors.push(`${graph.id}/${node.id}: candidate techniques and conditions required`);
      if (node.type === 'route' && (!node.graph || !knownGraphs.has(node.graph))) errors.push(`${graph.id}/${node.id}: unknown target graph`);
      if (node.continuation !== undefined) {
        const target = input.find(candidate => candidate.id === node.graph);
        if (typeof node.continuation !== 'boolean' || node.type !== 'route' || (node.continuation && target?.root !== node.id)) errors.push(`${graph.id}/${node.id}: continuation must route to the same root id`);
      }
    }
    const visited = new Set<string>();
    const active = new Set<string>();
    function visit(id: string): void {
      if (active.has(id)) { errors.push(`${graph.id}: cycle at ${id}`); return; }
      if (visited.has(id) || !byId.has(id)) return;
      active.add(id);
      const node = byId.get(id)!;
      if (node.type === 'question' && node.answers) for (const next of Object.values(node.answers)) visit(next);
      active.delete(id);
      visited.add(id);
    }
    visit(graph.root);
    for (const node of graph.nodes) if (!visited.has(node.id)) errors.push(`${graph.id}: unreachable ${node.id}`);
  }
  const graphNodes = new Map<string, { graph: FlowGraph; node: FlowNode }>(input.flatMap((graph) => graph.nodes.map((node) => [`${graph.id}/${node.id}`, { graph, node }] as const)));
  const activeRoutes = new Set<string>();
  const completedRoutes = new Set<string>();
  function visitRoutes(key: string): void {
    if (activeRoutes.has(key)) { errors.push(`Graph route cycle at ${key}`); return; }
    if (completedRoutes.has(key)) return;
    const item = graphNodes.get(key); if (!item) return;
    activeRoutes.add(key);
    for (const target of Object.values(item.node.answers ?? {})) visitRoutes(`${item.graph.id}/${target}`);
    if (item.node.type === 'route') { const next = input.find((graph) => graph.id === item.node.graph); if (next) visitRoutes(`${next.id}/${next.root}`); }
    activeRoutes.delete(key); completedRoutes.add(key);
  }
  for (const key of graphNodes.keys()) visitRoutes(key);
  return errors;
}

function escapeHtml(value: string): string {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function normalizeBase(base: string): string {
  return `/${base.split('/').filter(Boolean).join('/')}${base.split('/').filter(Boolean).length ? '/' : ''}`;
}
function techniqueLink(base: string, id: string): string {
  return `${normalizeBase(base)}techniques/${encodeURIComponent(id)}/`;
}
/** Reserve a full character cell, including for fallback fonts and Latin text. */
function wrapText(value: string, width = 18): string[] {
  const opening = '([{（［｛〔〈《「『【〖〘〚‘“«‹';
  const closing = ')]}）］｝〕〉》」』】〗〙〛’”»›、。，．・：；？！!?%,.:;ー々〃ゝゞヽヾぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ…‥';
  const characters = [...value];
  const limit = Number.isFinite(width) ? Math.max(1, Math.floor(width)) : 18;
  const lines: string[] = [];
  const isWord = (character: string | undefined): boolean => character !== undefined && /^[A-Za-z0-9_/-]$/.test(character);
  for (let start = 0; start < characters.length;) {
    const maximum = Math.min(start + limit, characters.length);
    let end = maximum;
    if (end < characters.length) {
      while (end > start && (opening.includes(characters[end - 1]!) || closing.includes(characters[end]!))) end--;
    }
    const punctuationSafe = end;
    if (end > start && end < characters.length && isWord(characters[end - 1]) && isWord(characters[end])) {
      let wordStart = end, wordEnd = end;
      while (wordStart > start && isWord(characters[wordStart - 1])) wordStart--;
      while (wordEnd < characters.length && wordEnd - wordStart <= limit && isWord(characters[wordEnd])) wordEnd++;
      if (wordEnd - wordStart <= limit) {
        // Keep short English names together, including an opening bracket just
        // before the word. Japanese punctuation rules still take precedence.
        end = wordStart;
        while (end > start && (opening.includes(characters[end - 1]!) || closing.includes(characters[end]!))) end--;
        if (end === start) end = punctuationSafe;
      }
    }
    // An overlong run of brackets or punctuation has no legal boundary.
    // Keep every character within its full-em reservation and always advance.
    if (end === start) end = maximum;
    lines.push(characters.slice(start, end).join(''));
    start = end;
  }
  return lines;
}

/** Render at build time, with no browser or graph-library dependency. */
export function renderFlowSvg(graph: FlowGraph, base = '/flowchartcp/', titles: Record<string, string> = {}): string {
  const errors = validateGraphs();
  if (errors.length) throw new Error(errors.join('\n'));
  const nodeWidth = 320;
  type Content = { title: string[]; explanation: string[]; links: { id: string; lines: string[] }[]; height: number };
  const contents = new Map<string, Content>();
  for (const node of graph.nodes) {
    const title = wrapText(node.title, 17);
    const allExplanation = wrapText(node.explanation ?? '', 24);
    const explanation = allExplanation.slice(0, 3);
    if (allExplanation.length > 3) explanation[2] = `${explanation[2]!.slice(0, 23)}…`;
    const links = (node.techniques ?? []).map(id => ({ id, lines: wrapText(titles[id] ?? id, 23) }));
    const height = 48 + title.length * 23 + 4 + explanation.length * 18 + (links.length ? 12 + links.reduce((sum, link) => sum + link.lines.length * 18 + 6, 0) : 0) + (node.type === 'route' ? 30 : 0) + 16;
    contents.set(node.id, { title, explanation, links, height });
  }
  const edges = graph.nodes.flatMap(node => node.type === 'question' ? getNodeOptions(node).map(option => {
    const lines = wrapText(option.label, 17);
    return { id: `${node.id}:${option.id}:${node.answers![option.id]}`, from: node.id, to: node.answers![option.id]!, answer: option.id, label: option.label, lines,
      labelWidth: Math.max(80, 24 + Math.max(...lines.map(line => [...line].length)) * 13), labelHeight: lines.length * 18 + 20 };
  }) : []);
  const layout = layoutLayeredGraph(graph.nodes.map(node => ({ id: node.id, width: nodeWidth, height: contents.get(node.id)!.height })), edges, graph.root);
  const safeGraphId = escapeHtml(graph.id);
  const svg = [`<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="flow-title-${safeGraphId} flow-desc-${safeGraphId}" width="${layout.width}" height="${layout.height}" viewBox="0 0 ${layout.width} ${layout.height}" data-flow-svg="${safeGraphId}">`,
    `<title id="flow-title-${safeGraphId}">${escapeHtml(graph.title)}の解法フローチャート</title><desc id="flow-desc-${safeGraphId}">${escapeHtml(graph.description)} 矢印には選択肢を表示しています。候補の適用条件は図の後の一覧でも読めます。</desc>`,
    `<defs><marker id="arrow-${safeGraphId}" markerWidth="9" markerHeight="9" markerUnits="userSpaceOnUse" refX="8" refY="4.5" orient="auto"><path d="M0 0 L9 4.5 L0 9 Z" fill="context-stroke"/></marker></defs>`,
    `<style>.flow-edge{stroke:#64748b;fill:#475569}.flow-edge>path{fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.flow-edge.yes{stroke:#148575;fill:#148575}.flow-edge.no{stroke:#8d59b6;fill:#8d59b6}.flow-edge.unknown{stroke:#a5681d;fill:#a5681d}.flow-edge-label rect{fill:var(--flow-node-bg,#fff);stroke:currentColor;stroke-width:1;stroke-opacity:.3}.flow-edge-label text{stroke:none;font-size:13px;font-family:system-ui,sans-serif;font-weight:500}.flow-edge.is-path>path{stroke-width:4}.flow-edge.is-path .flow-edge-label rect{stroke:#148575;stroke-width:2;stroke-opacity:1}.flow-edge.is-path .flow-edge-label text{font-weight:700}svg[data-flow-svg]:has(.flow-edge.is-path) .flow-edge:where(:not(.is-path)){opacity:.38}svg[data-flow-svg]:has(.flow-edge:hover,.flow-edge:focus-within) .flow-edge{opacity:.16}svg[data-flow-svg]:has(.flow-edge:hover,.flow-edge:focus-within) .flow-edge:hover,svg[data-flow-svg]:has(.flow-edge:hover,.flow-edge:focus-within) .flow-edge:focus-within{opacity:1}.flow-edge:hover>path,.flow-edge:focus-within>path{stroke-width:4}.flow-edge:focus-within .flow-edge-label rect{stroke:#1754a4;stroke-width:2;stroke-opacity:1}.flow-edge-label:focus{outline:none}.flow-node rect{fill:var(--flow-node-bg,#fff);stroke:var(--flow-node-border,#94a3b8);stroke-width:1.5}.flow-node.result rect{fill:var(--flow-result-bg,#f0f8f5);stroke:#148575}.flow-node.route rect{fill:var(--flow-route-bg,#f3f5fc);stroke:#707dba}.flow-node.is-path rect{stroke:#148575;stroke-width:3}.flow-node.is-current rect{stroke:#e19a35;stroke-width:5}.flow-node text{font-family:system-ui,sans-serif;fill:var(--flow-text,#20324c);stroke:none}.flow-node .node-title{font-size:16px;font-weight:600}.flow-node .node-explanation{font-size:12px;fill:var(--flow-muted,#52637a)}.flow-node a text{font-size:12px;fill:var(--flow-link,#086c65);text-decoration:underline}.flow-node a:focus text{outline:2px solid #e19a35}.flow-node .node-kind{font-size:10px;fill:var(--flow-muted,#52637a);letter-spacing:.06em}</style>`];
  for (const edge of edges) {
    const drawing = layout.edges.get(edge.id)!;
    svg.push(`<g class="flow-edge ${escapeHtml(edge.answer)}" data-edge="${escapeHtml(edge.id)}"><title>${escapeHtml(edge.label)}</title><path d="${drawing.before}"/><path d="${drawing.after}" marker-end="url(#arrow-${safeGraphId})"/><g class="flow-edge-label" data-edge-label="${escapeHtml(edge.id)}" tabindex="0" role="group" aria-label="選択肢：${escapeHtml(edge.label)}"><rect x="${drawing.label.x}" y="${drawing.label.y}" width="${drawing.label.width}" height="${drawing.label.height}" rx="5"/>`);
    edge.lines.forEach((line, i) => svg.push(`<text text-anchor="middle" x="${drawing.label.x + drawing.label.width / 2}" y="${drawing.label.y + 23 + i * 18}">${escapeHtml(line)}</text>`));
    svg.push('</g></g>');
  }
  for (const node of graph.nodes) {
    const { x, y, height: h } = layout.nodes.get(node.id)!;
    const { title, explanation, links } = contents.get(node.id)!;
    svg.push(`<g class="flow-node ${node.type}" data-node="${escapeHtml(node.id)}"><rect x="${x}" y="${y}" width="${nodeWidth}" height="${h}" rx="7"/><text class="node-kind" x="${x + 16}" y="${y + 20}">${node.type === 'question' ? '質問' : node.type === 'route' ? '分野' : '候補'}</text>`);
    let textY = y + 48;
    title.forEach(line => { svg.push(`<text class="node-title" x="${x + 16}" y="${textY}">${escapeHtml(line)}</text>`); textY += 23; });
    textY += 4;
    explanation.forEach(line => { svg.push(`<text class="node-explanation" x="${x + 16}" y="${textY}">${escapeHtml(line)}</text>`); textY += 18; });
    if (links.length) textY += 12;
    for (const link of links) {
      svg.push(`<a href="${escapeHtml(techniqueLink(base, link.id))}"><title>${escapeHtml(titles[link.id] ?? link.id)}の記事へ</title>`);
      link.lines.forEach(line => { svg.push(`<text x="${x + 16}" y="${textY}">${escapeHtml(line)}</text>`); textY += 18; });
      svg.push('</a>'); textY += 6;
    }
    if (node.type === 'route') svg.push(`<a href="${escapeHtml(`${normalizeBase(base)}flowcharts/#diagram-${encodeURIComponent(node.graph!)}`)}" data-route="${escapeHtml(node.graph!)}"><text x="${x + 16}" y="${textY + 10}">詳細の質問・図へ →</text></a>`);
    svg.push('</g>');
  }
  svg.push('</svg>');
  return svg.join('');
}

/** Shared static shell for Astro and the dependency-free local preview. */
export function renderFlowHtml(base = '/flowchartcp/', titles: Record<string, string> = {}): string {
  const safeBase = escapeHtml(normalizeBase(base));
  const data = JSON.stringify(titles).replace(/</g, '\\u003c').replace(/>/g, '\\u003e').replace(/&/g, '\\u0026');
  const html = [`<div class="flowchart" data-flowchart data-base="${safeBase}"><script type="application/json" data-flow-titles>${data}</script>`,
    `<nav class="flow-domain-nav" aria-label="分野">${entryGraphs.map((graph) => `<a href="#diagram-${escapeHtml(graph.id)}" data-domain-graph="${escapeHtml(graph.id)}">${escapeHtml(graph.title)}</a>`).join('')}</nav>`,
    `<nav class="flow-static-nav" aria-label="分野ごとの詳しい図">${flowGroups.map((group) => `<details><summary>${escapeHtml(group.entry.title)}</summary><div>${group.graphs.map((graph) => `<a href="#diagram-${escapeHtml(graph.id)}">${escapeHtml(graph.title)}</a>`).join('')}</div></details>`).join('')}</nav>`,
    '<div class="flow-toolbar" data-enhanced-only hidden><label class="flow-select-label">図を選ぶ<select data-graph-select aria-label="フローチャートの図">',
    ...flowGroups.map((group) => `<optgroup label="${escapeHtml(group.entry.title)}">${group.graphs.map((graph) => `<option value="${escapeHtml(graph.id)}">${escapeHtml(graph.title)}</option>`).join('')}</optgroup>`),
    '</select></label><div class="flow-view-buttons" role="group" aria-label="表示切り替え"><button type="button" data-view="questions" aria-pressed="true">質問でたどる</button><button type="button" data-view="diagram" aria-pressed="false">図で確認する</button></div><div class="flow-action-buttons"><button type="button" data-flow-back>← 戻る</button><button type="button" data-flow-reset>最初から</button><button type="button" data-flow-share>回答を共有</button></div></div>',
    '<p class="flow-live" data-flow-status role="status" aria-live="polite" aria-atomic="true"></p><div data-enhanced-only hidden class="flow-share" data-share-box><label>共有URL<input type="text" readonly data-share-url aria-label="回答履歴の共有URL" /></label></div>',
    '<section class="flow-question-panel" data-question-panel hidden aria-label="現在の質問・候補"><div data-current-node></div><details class="flow-history" data-flow-history-wrap><summary>回答履歴 <span data-history-count>0</span></summary><ol data-flow-history></ol></details></section>',
    '<div class="flow-diagrams" data-diagrams>'];
  for (const graph of graphs) {
    html.push(`<section id="diagram-${escapeHtml(graph.id)}" class="flow-diagram-panel" data-graph-panel="${escapeHtml(graph.id)}"><h2>${escapeHtml(graph.title)}</h2><p>${escapeHtml(graph.description)}</p>`,
      '<div class="flow-camera-controls" data-enhanced-only hidden role="group" aria-label="図の拡大と移動"><button type="button" data-camera="in" aria-label="拡大">＋ 拡大</button><button type="button" data-camera="out" aria-label="縮小">− 縮小</button><button type="button" data-camera="fit">図全体を表示</button><button type="button" data-camera="current">現在位置</button><span class="flow-pan-buttons"><button type="button" data-camera="left" aria-label="図を左へ移動">←</button><button type="button" data-camera="up" aria-label="図を上へ移動">↑</button><button type="button" data-camera="down" aria-label="図を下へ移動">↓</button><button type="button" data-camera="right" aria-label="図を右へ移動">→</button></span><span class="flow-zoom-value" data-zoom-value>100%</span></div>',
      `<div class="flow-svg-viewport" data-svg-viewport tabindex="0" aria-label="${escapeHtml(graph.title)}の図。拡大後は矢印キーまたはドラッグで移動できます。">${renderFlowSvg(graph, base, titles)}</div>`,
      `<p class="flow-diagram-help">矢印のラベルをたどり、候補の記事で適用条件を確認してください。<a href="${safeBase}diagrams/${escapeHtml(graph.id)}/" data-diagram-open="${escapeHtml(graph.id)}">図だけ表示</a><a href="${safeBase}diagrams/${escapeHtml(graph.id)}.svg" download>SVGを保存</a></p>`,
      `<details class="flow-node-list"><summary>図の内容を文章で読む・適用条件を確認する</summary><ol>`);
    for (const node of graph.nodes) {
      html.push(`<li id="flow-text-${escapeHtml(graph.id)}-${escapeHtml(node.id)}"><strong>${escapeHtml(node.title)}</strong><p>${escapeHtml(node.explanation ?? '')}</p>`);
      if (node.type === 'question') html.push(`<ul>${getNodeOptions(node).map(({ id: answer, label }) => `<li>${escapeHtml(label)} → <a href="#flow-text-${escapeHtml(graph.id)}-${escapeHtml(node.answers![answer])}">${escapeHtml(getNode(graph, node.answers![answer]).title)}</a></li>`).join('')}</ul>`);
      if (node.type === 'result') html.push(`<ul>${(node.techniques ?? []).map((technique) => `<li><a href="${escapeHtml(techniqueLink(base, technique))}">${escapeHtml(titles[technique] ?? technique)}</a></li>`).join('')}</ul><p>適用条件</p><ul>${(node.conditions ?? []).map((condition) => `<li>${escapeHtml(condition)}</li>`).join('')}</ul>`);
      if (node.type === 'route') html.push(`<a href="#diagram-${escapeHtml(node.graph!)}">${escapeHtml(getGraph(node.graph!).title)}の図へ</a>`);
      html.push('</li>');
    }
    html.push('</ol></details></section>');
  }
  html.push('</div><noscript><p>JavaScriptが無効でもすべての図と文章版を読めます。質問形式・経路強調・図の拡大移動にはJavaScriptが必要です。</p></noscript></div>');
  return html.join('');
}
