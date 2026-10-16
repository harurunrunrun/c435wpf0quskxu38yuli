import { getGraph, initialState, migratedFlowHash, parseFlowHash, renderFlowSvg, serializeFlowHash, type FlowGraph, type FlowState } from './flow.ts';

const escapeHtml = (value: string): string => value.replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]!);

export type DiagramBox = [number, number, number, number];
export function diagramZoomLimits(original: readonly number[]): { min: number; max: number } {
  // Even a wide field diagram must allow its nodes to be read at their natural size.
  return { min: Math.min(160, original[2]! / 64), max: Math.max(160, original[2]! * 4) };
}
export function diagramZoomPercent(box: readonly number[], viewportWidth: number, viewportHeight: number): number {
  return Math.round(Math.min(viewportWidth / box[2]!, viewportHeight / box[3]!) * 100);
}
export function diagramNodeBox(svg: SVGSVGElement, nodeId: string): DiagramBox | undefined {
  const rect = svg.querySelector<SVGGElement>(`[data-node="${nodeId}"]`)?.querySelector('rect');
  if (!rect) return undefined;
  const box = ['x', 'y', 'width', 'height'].map(attribute => Number(rect.getAttribute(attribute)));
  return box.every(Number.isFinite) && box[2]! > 0 && box[3]! > 0 ? box as DiagramBox : undefined;
}
/** Natural-size text around the current question, using the actual viewport aspect ratio. */
export function readableDiagramBox(original: readonly number[], node: readonly number[], viewportWidth: number, viewportHeight: number): DiagramBox | undefined {
  if (viewportWidth <= 0 || viewportHeight <= 0) return undefined;
  const ratio = viewportWidth / viewportHeight;
  const limits = diagramZoomLimits(original);
  const width = Math.max(limits.min, Math.min(limits.max, Math.max(viewportWidth, node[2]! + 96, (node[3]! + 96) * ratio)));
  const height = width / ratio;
  const position = (start: number, extent: number, nodeStart: number, nodeExtent: number, viewExtent: number): number =>
    viewExtent >= extent ? start + (extent - viewExtent) / 2 : Math.max(start, Math.min(start + extent - viewExtent, nodeStart + nodeExtent / 2 - viewExtent / 2));
  return [position(original[0]!, original[2]!, node[0]!, node[2]!, width), position(original[1]!, original[3]!, node[1]!, node[3]!, height), width, height];
}
export function normalizeDiagramBase(base: string): string { return `/${base.split('/').filter(Boolean).join('/')}${base.split('/').filter(Boolean).length ? '/' : ''}`; }
export function diagramViewerUrl(graph: string, base = '/flowchartcp/', state?: FlowState, camera?: readonly number[]): string {
  // Lossless numbers keep a camera exactly on a zoom limit valid after a reload.
  const query = camera ? `?camera=${camera.join(',')}` : '';
  return `${normalizeDiagramBase(base)}diagrams/${encodeURIComponent(getGraph(graph).id)}/${query}${state ? serializeFlowHash(state) : ''}`;
}
export function parseDiagramCamera(value: string | null, original: readonly number[]): DiagramBox | undefined {
  if (!value || value.length > 180) return undefined;
  const box = value.split(',').map(Number);
  if (box.length !== 4 || !box.every(Number.isFinite) || box[2]! <= 0 || box[3]! <= 0) return undefined;
  if (Math.abs(box[0]!) > original[2]! * 1000 || Math.abs(box[1]!) > original[3]! * 1000) return undefined;
  // A camera saved before a field was split may point entirely outside its new diagram.
  // Partial overlap remains valid, including deliberate panning beyond the canvas edge.
  if (box[0]! + box[2]! <= original[0]! || box[0]! >= original[0]! + original[2]! || box[1]! + box[3]! <= original[1]! || box[1]! >= original[1]! + original[3]!) return undefined;
  const limits = diagramZoomLimits(original);
  if (box[2]! < limits.min || box[2]! > limits.max || box[3]! < original[3]! / 1000 || box[3]! > original[3]! * 1000) return undefined;
  return box as DiagramBox;
}
/** Keep the diagram point under the pointer fixed, including at both zoom limits. */
export function zoomDiagramBox(box: readonly number[], original: readonly number[], factor: number, anchor: { x: number; y: number }): DiagramBox {
  const limits = diagramZoomLimits(original);
  const width = Math.max(limits.min, Math.min(limits.max, box[2]! * factor));
  const scale = width / box[2]!;
  return [anchor.x + (box[0]! - anchor.x) * scale, anchor.y + (box[1]! - anchor.y) * scale, width, box[3]! * scale];
}
export function diagramState(graph: string, hash: string): FlowState {
  const state = parseFlowHash(hash);
  return state.graph === graph ? state : legacyDiagramState(graph, hash) ?? initialState(graph);
}
/** Preserve the viewer API while accepting verified migrations through any number of split diagrams. */
export function legacyDiagramState(graph: string, hash: string): FlowState | undefined {
  return migratedFlowHash(graph, hash);
}
/** Used unchanged by the Astro page and the offline builder. */
export function renderDiagramViewerHtml(graph: FlowGraph, base = '/flowchartcp/', titles: Record<string, string> = {}): string {
  const normalized = normalizeDiagramBase(base);
  const svg = renderFlowSvg(graph, normalized, titles).replace('候補の適用条件は図の後の一覧でも読めます。', '候補の記事で適用条件を確認できます。').replace(/href="[^"]*" data-route="([a-z0-9-]+)"/g,
    (_match, id: string) => `href="${escapeHtml(diagramViewerUrl(id, normalized))}" data-route="${escapeHtml(id)}"`);
  return `<main class="diagram-viewer" data-diagram-viewer data-graph="${escapeHtml(graph.id)}" data-base="${escapeHtml(normalized)}"><div class="diagram-viewer-controls" aria-label="図の操作"><a data-diagram-back href="${escapeHtml(`${normalized}flowcharts/#diagram-${graph.id}`)}">戻る</a><button type="button" data-diagram-action="in" aria-label="拡大" hidden>＋</button><button type="button" data-diagram-action="out" aria-label="縮小" hidden>−</button><button type="button" data-diagram-action="fit" hidden>全体</button><output data-diagram-zoom aria-label="拡大率" hidden>100%</output></div><div class="diagram-viewer-viewport" data-diagram-viewport tabindex="0" aria-label="${escapeHtml(graph.title)}。ホイールで拡大縮小、ドラッグで移動。プラス・マイナス、矢印キー、0キーでも操作できます。">${svg}</div></main>`;
}
