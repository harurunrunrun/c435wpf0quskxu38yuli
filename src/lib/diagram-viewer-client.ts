import { enterFlowRoute, evaluateState, initialState, serializeFlowHash } from './flow.ts';
import { diagramNodeBox, diagramState, diagramViewerUrl, diagramZoomPercent, parseDiagramCamera, readableDiagramBox, zoomDiagramBox, type DiagramBox } from './diagram-viewer.ts';

function initializeDiagramViewer(): void {
  const root = document.querySelector<HTMLElement>('[data-diagram-viewer]');
  if (!root || root.dataset.enhanced === 'true') return;
  const viewport = root.querySelector<HTMLElement>('[data-diagram-viewport]');
  const svg = viewport?.querySelector<SVGSVGElement>('svg');
  const back = root.querySelector<HTMLAnchorElement>('[data-diagram-back]');
  const zoom = root.querySelector<HTMLOutputElement>('[data-diagram-zoom]');
  if (!viewport || !svg || !back || !zoom) return;
  const graph = root.dataset.graph!;
  const base = root.dataset.base!;
  let persistTimer: number | undefined;
  function redirectSplit(next: ReturnType<typeof diagramState>): boolean {
    if (next.graph === graph) return false;
    if (persistTimer !== undefined) window.clearTimeout(persistTimer);
    // The split diagram has different coordinates. Its readable view replaces the old camera.
    window.location.replace(diagramViewerUrl(next.graph, base, next));
    return true;
  }
  let state = diagramState(graph, window.location.hash);
  if (redirectSplit(state)) return;
  root.dataset.enhanced = 'true';
  const original = svg.getAttribute('viewBox')!.split(/\s+/).map(Number) as DiagramBox;
  const restoredCamera = parseDiagramCamera(new URLSearchParams(window.location.search).get('camera'), original);
  let box = restoredCamera ?? [...original] as DiagramBox;
  let mode: 'auto' | 'manual' | 'fit' = restoredCamera ? 'manual' : 'auto';
  root.querySelectorAll<HTMLElement>('[data-diagram-action], [data-diagram-zoom]').forEach(control => { control.hidden = false; });

  function update(): void {
    svg!.setAttribute('viewBox', box.join(' '));
    zoom!.textContent = `${diagramZoomPercent(box, viewport!.clientWidth, viewport!.clientHeight)}%`;
    const query = `?diagram=${encodeURIComponent(graph)}&camera=${box.join(',')}`;
    back!.href = `${base}flowcharts/${query}${serializeFlowHash(state)}`;
    // Trackpad events arrive in bursts. Persist after they stop so browsers'
    // History API rate limits cannot interrupt dragging or zooming.
    if (persistTimer !== undefined) window.clearTimeout(persistTimer);
    persistTimer = window.setTimeout(() => {
      window.history.replaceState(null, '', diagramViewerUrl(graph, base, state, box));
      persistTimer = undefined;
    }, 200);
  }
  function highlight(): void {
    const evaluation = evaluateState(state);
    const nodes = new Set(evaluation.path.map(node => node.id));
    const edges = new Set(evaluation.edges.map(edge => `${edge.from}:${edge.answer}:${edge.to}`));
    svg!.querySelectorAll<SVGGElement>('[data-node]').forEach(node => {
      node.classList.toggle('is-path', nodes.has(node.dataset.node!));
      node.classList.toggle('is-current', node.dataset.node === evaluation.current.id);
      if (node.dataset.node === evaluation.current.id) node.setAttribute('aria-current', 'step'); else node.removeAttribute('aria-current');
    });
    svg!.querySelectorAll<SVGGElement>('[data-edge]').forEach(edge => edge.classList.toggle('is-path', edges.has(edge.dataset.edge!)));
    svg!.querySelectorAll<SVGAElement>('[data-route]').forEach(link => {
      const target = link.dataset.route!;
      const next = evaluation.current.type === 'route' && evaluation.current.graph === target ? enterFlowRoute(state) : initialState(target);
      link.setAttribute('href', diagramViewerUrl(target, base, next));
    });
  }
  function focusCurrent(): void {
    const node = diagramNodeBox(svg!, evaluateState(state).current.id);
    if (!node) return;
    const next = readableDiagramBox(original, node, viewport!.clientWidth, viewport!.clientHeight);
    if (next) box = next;
  }
  function center(): { x: number; y: number } { return { x: box[0] + box[2] / 2, y: box[1] + box[3] / 2 }; }
  function control(action: string): void {
    mode = action === 'fit' ? 'fit' : 'manual';
    if (action === 'fit') box = [...original];
    else if (action === 'in' || action === 'out') box = zoomDiagramBox(box, original, action === 'in' ? 0.8 : 1.25, center());
    else {
      const dx = action === 'left' ? -0.15 : action === 'right' ? 0.15 : 0;
      const dy = action === 'up' ? -0.15 : action === 'down' ? 0.15 : 0;
      box = [box[0] + box[2] * dx, box[1] + box[3] * dy, box[2], box[3]];
    }
    update();
  }
  root.querySelectorAll<HTMLButtonElement>('[data-diagram-action]').forEach(button => button.addEventListener('click', () => control(button.dataset.diagramAction!)));
  viewport.addEventListener('keydown', event => {
    if (event.target !== viewport) return;
    const actions: Record<string, string> = { '+': 'in', '=': 'in', '-': 'out', '0': 'fit', ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'up', ArrowDown: 'down' };
    const action = actions[event.key];
    if (action) { event.preventDefault(); control(action); }
  });
  viewport.addEventListener('wheel', event => {
    event.preventDefault();
    const matrix = svg.getScreenCTM();
    if (!matrix) return;
    const anchor = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
    mode = 'manual';
    const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? viewport.clientHeight : 1);
    box = zoomDiagramBox(box, original, Math.exp(Math.max(-1200, Math.min(1200, delta)) * 0.0015), anchor);
    update();
  }, { passive: false });

  type Pointer = { x: number; y: number };
  type Gesture = { box: DiagramBox; inverse: DOMMatrix; anchor: Pointer; distance: number; screen: Pointer };
  const pointers = new Map<number, Pointer>();
  let gesture: Gesture | undefined;
  let moved = false;
  function middle(): Pointer {
    const points = [...pointers.values()];
    return points.length > 1 ? { x: (points[0]!.x + points[1]!.x) / 2, y: (points[0]!.y + points[1]!.y) / 2 } : points[0]!;
  }
  function distance(): number {
    const points = [...pointers.values()];
    return points.length > 1 ? Math.hypot(points[0]!.x - points[1]!.x, points[0]!.y - points[1]!.y) : 0;
  }
  function beginGesture(): void {
    const matrix = svg!.getScreenCTM();
    if (!pointers.size || !matrix) { gesture = undefined; return; }
    const inverse = matrix.inverse();
    const screen = middle();
    const anchor = new DOMPoint(screen.x, screen.y).matrixTransform(inverse);
    gesture = { box: [...box], inverse, anchor, distance: distance(), screen };
  }
  viewport.addEventListener('pointerdown', event => {
    if (event.button !== 0 || !(event.target instanceof Element) || event.target.closest('a')) return;
    event.preventDefault();
    mode = 'manual';
    if (!pointers.size) moved = false;
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    viewport.setPointerCapture(event.pointerId);
    viewport.classList.add('is-dragging');
    viewport.focus({ preventScroll: true });
    beginGesture();
  });
  viewport.addEventListener('pointermove', event => {
    if (!pointers.has(event.pointerId) || !gesture) return;
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    const screen = middle();
    if (Math.hypot(screen.x - gesture.screen.x, screen.y - gesture.screen.y) > 3 || (pointers.size > 1 && Math.abs(distance() - gesture.distance) > 3)) moved = true;
    const point = new DOMPoint(screen.x, screen.y).matrixTransform(gesture.inverse);
    const factor = pointers.size > 1 && gesture.distance > 0 ? gesture.distance / Math.max(1, distance()) : 1;
    const next = zoomDiagramBox(gesture.box, original, factor, gesture.anchor);
    const scale = next[2] / gesture.box[2];
    box = [next[0] + (gesture.anchor.x - point.x) * scale, next[1] + (gesture.anchor.y - point.y) * scale, next[2], next[3]];
    update();
  });
  const endPointer = (event: PointerEvent): void => {
    if (!pointers.delete(event.pointerId)) return;
    if (!pointers.size) viewport.classList.remove('is-dragging');
    beginGesture();
  };
  viewport.addEventListener('pointerup', endPointer);
  viewport.addEventListener('pointercancel', endPointer);
  viewport.addEventListener('lostpointercapture', endPointer);
  viewport.addEventListener('click', event => { if (moved) { event.preventDefault(); event.stopPropagation(); moved = false; } }, true);
  window.addEventListener('hashchange', () => {
    const next = diagramState(graph, window.location.hash);
    if (redirectSplit(next)) return;
    state = next;
    highlight(); if (mode === 'auto') focusCurrent(); update();
  });
  window.addEventListener('resize', () => { if (mode === 'auto') focusCurrent(); update(); });
  highlight();
  if (mode === 'auto') focusCurrent();
  update();
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeDiagramViewer, { once: true });
else initializeDiagramViewer();
