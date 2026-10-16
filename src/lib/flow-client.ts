import { diagramNodeBox, diagramViewerUrl, diagramZoomPercent, legacyDiagramState, parseDiagramCamera, readableDiagramBox, zoomDiagramBox } from './diagram-viewer.ts';
import { answerLabels, answerState, backFlowState, enterFlowRoute, evaluateState, getGraph, getFlowDomainId, getNodeOptions, getAnswerLabel, graphs, initialState, parseFlowHash, sanitizeState, serializeFlowHash, type FlowAnswer, type FlowState } from './flow.ts';

function initializeFlowcharts(): void {
  document.querySelectorAll<HTMLElement>('[data-flowchart]').forEach((root) => {
    if (root.dataset.enhanced === 'true') return;
    root.dataset.enhanced = 'true';
    const find = <T extends HTMLElement>(selector: string): T => {
      const element = root.querySelector<T>(selector);
      if (!element) throw new Error(`Missing flowchart control: ${selector}`);
      return element;
    };
    let titles: Record<string, string> = {};
    try { titles = JSON.parse(root.querySelector('[data-flow-titles]')?.textContent ?? '{}'); } catch { /* Text labels fall back to ids. */ }
    const base = root.dataset.base ?? '/flowchartcp/';
    const select = find<HTMLSelectElement>('[data-graph-select]');
    const questionPanel = find('[data-question-panel]');
    const currentPanel = find('[data-current-node]');
    const diagrams = find('[data-diagrams]');
    const status = find('[data-flow-status]');
    const historyList = find<HTMLOListElement>('[data-flow-history]');
    const historyCount = find('[data-history-count]');
    const back = find<HTMLButtonElement>('[data-flow-back]');
    const shareBox = find('[data-share-box]');
    const shareUrl = find<HTMLInputElement>('[data-share-url]');
    let state: FlowState = parseFlowHash(window.location.hash);
    if (window.location.hash.startsWith('#diagram-')) state = initialState(window.location.hash.slice('#diagram-'.length));
    const initialQuery = new URLSearchParams(window.location.search);
    const hashGraph = new URLSearchParams(window.location.hash.replace(/^#/, '')).get('flow');
    const migrated = hashGraph ? legacyDiagramState(hashGraph, window.location.hash) : undefined;
    const diagramRequested = initialQuery.get('diagram') === state.graph || (migrated && initialQuery.get('diagram') === hashGraph);
    if (migrated) {
      initialQuery.delete('camera');
      if (diagramRequested) initialQuery.set('diagram', state.graph);
    }
    let normalizedSearch = migrated ? `${initialQuery.size ? '?' : ''}${initialQuery}` : undefined;
    let view: 'questions' | 'diagram' = diagramRequested ? 'diagram' : 'questions';
    const savedStates = new Map<string, FlowState>([[state.graph, state]]);
    const savedDomains = new Map<string, FlowState>([[getFlowDomainId(state), state]]);
    root.querySelectorAll<HTMLElement>('[data-enhanced-only]').forEach((element) => { element.hidden = false; });
    shareBox.hidden = true;
    find('.flow-static-nav').hidden = true;

    type Camera = { svg: SVGSVGElement; viewport: HTMLElement; panel: HTMLElement; original: number[]; box: number[]; mode: 'auto' | 'manual' | 'fit' };
    const cameras = new Map<string, Camera>();
    root.querySelectorAll<HTMLElement>('[data-graph-panel]').forEach((panel) => {
      const svg = panel.querySelector<SVGSVGElement>('svg');
      const viewport = panel.querySelector<HTMLElement>('[data-svg-viewport]');
      if (!svg || !viewport) return;
      const original = (svg.getAttribute('viewBox') ?? '0 0 100 100').split(' ').map(Number);
      cameras.set(panel.dataset.graphPanel!, { svg, viewport, panel, original, box: [...original], mode: 'auto' });
    });
    const restoredCamera = cameras.get(state.graph);
    if (restoredCamera) {
      const box = parseDiagramCamera(initialQuery.get('camera'), restoredCamera.original);
      if (box) { restoredCamera.box = box; restoredCamera.mode = 'manual'; }
      updateCamera(restoredCamera);
    }

    function element<K extends keyof HTMLElementTagNameMap>(tag: K, text?: string, className?: string): HTMLElementTagNameMap[K] {
      const value = document.createElement(tag);
      if (text !== undefined) value.textContent = text;
      if (className) value.className = className;
      return value;
    }
    function link(id: string): HTMLAnchorElement {
      const anchor = element('a', titles[id] ?? id);
      anchor.href = `${base}techniques/${encodeURIComponent(id)}/`;
      return anchor;
    }
    function announce(text: string): void { status.textContent = text; }
    function focusNode(): void {
      (currentPanel.querySelector<HTMLButtonElement>('button') ?? currentPanel.querySelector<HTMLElement>('h3'))?.focus();
    }
    function updateUrl(): void {
      const hash = serializeFlowHash(state);
      window.history.replaceState(null, '', `${window.location.pathname}${normalizedSearch ?? window.location.search}${hash}`);
      normalizedSearch = undefined;
      shareUrl.value = window.location.href;
    }
    function updateCamera(camera: Camera): void {
      camera.svg.setAttribute('viewBox', camera.box.join(' '));
      const percentage = diagramZoomPercent(camera.box, camera.viewport.clientWidth, camera.viewport.clientHeight);
      const label = camera.panel.querySelector('[data-zoom-value]');
      if (label) label.textContent = `${percentage}%`;
      const opener = camera.panel.querySelector<HTMLAnchorElement>('[data-diagram-open]');
      if (opener) opener.href = diagramViewerUrl(camera.panel.dataset.graphPanel!, base, camera.panel.dataset.graphPanel === state.graph ? state : initialState(camera.panel.dataset.graphPanel), camera.box);
    }
    function focusCurrent(camera: Camera): void {
      const node = diagramNodeBox(camera.svg, evaluateState(state).current.id);
      if (!node) return;
      const box = readableDiagramBox(camera.original, node, camera.viewport.clientWidth, camera.viewport.clientHeight);
      if (!box) return;
      camera.box = box;
      camera.mode = 'auto';
      updateCamera(camera);
    }
    function controlCamera(camera: Camera, action: string): void {
      const [x, y, width, height] = camera.box as [number, number, number, number];
      if (action === 'fit') { camera.box = [...camera.original]; camera.mode = 'fit'; }
      else if (action === 'current') { focusCurrent(camera); return; }
      else if (action === 'in' || action === 'out') {
        camera.box = zoomDiagramBox(camera.box, camera.original, action === 'in' ? 0.75 : 1 / 0.75, { x: x + width / 2, y: y + height / 2 });
        camera.mode = 'manual';
      } else {
        const dx = action === 'left' ? -width * 0.15 : action === 'right' ? width * 0.15 : 0;
        const dy = action === 'up' ? -height * 0.15 : action === 'down' ? height * 0.15 : 0;
        camera.box = [x + dx, y + dy, width, height];
        camera.mode = 'manual';
      }
      updateCamera(camera);
    }
    function chooseGraph(id: string): void {
      savedStates.set(state.graph, state);
      savedDomains.set(getFlowDomainId(state), state);
      const graph = getGraph(id);
      const current = evaluateState(state).current;
      state = current.type === 'route' && current.graph === graph.id ? enterFlowRoute(state) : savedStates.get(graph.id) ?? initialState(graph.id);
      render();
      if (view === 'questions') focusNode();
      announce(`${graph.title}。図を切り替えました。`);
    }
    function chooseDomain(id: string): void {
      savedStates.set(state.graph, state);
      savedDomains.set(getFlowDomainId(state), state);
      state = savedDomains.get(id) ?? initialState(id);
      render();
      if (view === 'questions') focusNode();
      announce(`${getGraph(id).title}。分野を切り替えました。`);
    }
    function render(): void {
      state = sanitizeState(state);
      savedStates.set(state.graph, state);
      const domain = getFlowDomainId(state);
      savedDomains.set(domain, state);
      root.querySelectorAll<HTMLAnchorElement>('[data-domain-graph]').forEach((anchor) => {
        if (anchor.dataset.domainGraph === domain) anchor.setAttribute('aria-current', 'true');
        else anchor.removeAttribute('aria-current');
      });
      const evaluation = evaluateState(state);
      select.value = state.graph;
      questionPanel.hidden = view !== 'questions';
      diagrams.hidden = view !== 'diagram';
      root.querySelectorAll<HTMLButtonElement>('[data-view]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.view === view)));
      root.querySelectorAll<HTMLElement>('[data-graph-panel]').forEach((panel) => { panel.hidden = panel.dataset.graphPanel !== state.graph; });
      const current = evaluation.current;
      currentPanel.replaceChildren();
      const kicker = element('p', current.type === 'question' ? `質問 ${evaluation.answers.length + 1}` : current.type === 'route' ? '詳しい分岐へ' : '条件に合う技巧の候補', 'flow-kicker');
      const heading = element('h3', current.title);
      heading.id = 'flow-current-title';
      heading.tabIndex = -1;
      currentPanel.append(kicker, heading, element('p', current.explanation ?? ''));
      if (current.type === 'question') {
        const answers = element('div', undefined, 'flow-answer-buttons');
        getNodeOptions(current).forEach(({ id: answer, label }) => {
          const button = element('button', label, `flow-answer flow-answer-${answer}`);
          button.type = 'button';
          button.dataset.answer = answer;
          button.addEventListener('click', () => {
            state = answerState(state, answer);
            render();
            announce(`${label}。${evaluateState(state).current.title}`);
            focusNode();
          });
          answers.append(button);
        });
        currentPanel.append(answers, element('p', '「わからない」は、確認すべき条件と考察の候補へ進みます。', 'flow-note'));
      } else if (current.type === 'route') {
        const button = element('button', `${getGraph(current.graph!).title}へ進む →`, 'flow-route-button');
        button.type = 'button';
        button.addEventListener('click', () => chooseGraph(current.graph!));
        currentPanel.append(button);
      } else {
        currentPanel.append(element('p', '候補の記事で適用条件と正当性を確認し、必要な技巧を組み合わせてください。', 'flow-note'));
        const techniques = element('ul', undefined, 'flow-candidate-list');
        for (const id of current.techniques ?? []) { const item = element('li'); item.append(link(id)); techniques.append(item); }
        currentPanel.append(techniques, element('h4', '確認する適用条件'));
        const conditions = element('ul');
        for (const condition of current.conditions ?? []) conditions.append(element('li', condition));
        currentPanel.append(conditions);
      }
      historyList.replaceChildren();
      const contexts = [...(state.trail ?? []), { graph: state.graph, answers: state.answers }];
      contexts.forEach((context, contextIndex) => {
        const history = evaluateState(context);
        history.answers.forEach((answer, index) => {
          const item = element('li');
          const button = element('button', `${history.path[index]!.title} → ${getAnswerLabel(history.path[index]!, answer)}`);
          button.type = 'button';
          button.addEventListener('click', () => {
            state = sanitizeState({ graph: context.graph, answers: context.answers.slice(0, index), trail: contexts.slice(0, contextIndex) });
            render(); focusNode(); announce('選んだ質問に戻りました。');
          });
          item.append(button); historyList.append(item);
        });
      });
      historyCount.textContent = String(contexts.reduce((sum, context) => sum + context.answers.length, 0));
      back.disabled = !evaluation.answers.length && !state.trail?.length;
      for (const [id, camera] of cameras) {
        const activePath = id === state.graph ? new Set(evaluation.path.map((node) => node.id)) : new Set<string>();
        const activeEdges = id === state.graph ? new Set(evaluation.edges.map((edge) => `${edge.from}:${edge.answer}:${edge.to}`)) : new Set<string>();
        camera.svg.querySelectorAll<SVGGElement>('[data-node]').forEach((node) => {
          node.classList.toggle('is-path', activePath.has(node.dataset.node!));
          const isCurrent = id === state.graph && node.dataset.node === current.id;
          node.classList.toggle('is-current', isCurrent);
          if (isCurrent) node.setAttribute('aria-current', 'step'); else node.removeAttribute('aria-current');
        });
        camera.svg.querySelectorAll<SVGGElement>('[data-edge]').forEach((edge) => edge.classList.toggle('is-path', activeEdges.has(edge.dataset.edge!)));
      }
      const currentCamera = cameras.get(state.graph);
      if (currentCamera) {
        if (view === 'diagram' && currentCamera.mode === 'auto') focusCurrent(currentCamera);
        updateCamera(currentCamera);
      }
      updateUrl();
    }

    select.addEventListener('change', () => chooseGraph(select.value));
    back.addEventListener('click', () => { state = backFlowState(state); render(); announce('一つ前の質問に戻りました。'); });
    find<HTMLButtonElement>('[data-flow-reset]').addEventListener('click', () => {
      state = sanitizeState({ ...state, answers: [] });
      const camera = cameras.get(state.graph);
      if (camera) camera.mode = 'auto';
      render();
      announce('この図の最初の質問に戻りました。');
    });
    root.querySelectorAll<HTMLButtonElement>('[data-view]').forEach((button) => button.addEventListener('click', () => {
      view = button.dataset.view === 'diagram' ? 'diagram' : 'questions';
      render();
      announce(view === 'diagram' ? '図表示に切り替えました。緑は回答経路、橙は現在位置です。' : '質問表示に切り替えました。回答履歴を保持しています。');
    }));
    find<HTMLButtonElement>('[data-flow-share]').addEventListener('click', async () => {
      shareBox.hidden = false;
      shareUrl.value = window.location.href;
      try {
        await navigator.clipboard.writeText(shareUrl.value);
        announce('回答履歴を復元できるURLをコピーしました。');
      } catch {
        shareUrl.focus();
        shareUrl.select();
        announce('共有URLを選択しました。コピーしてください。');
      }
    });
    root.addEventListener('click', (event) => {
      if (!(event.target instanceof Element)) return;
      const domain = event.target.closest<HTMLAnchorElement>('[data-domain-graph]');
      if (domain?.dataset.domainGraph) { event.preventDefault(); chooseDomain(domain.dataset.domainGraph); return; }
      const route = event.target.closest<SVGElement>('[data-route]');
      if (route?.dataset.route) { event.preventDefault(); chooseGraph(route.dataset.route); }
      const control = event.target.closest<HTMLButtonElement>('[data-camera]');
      const graphId = control?.closest<HTMLElement>('[data-graph-panel]')?.dataset.graphPanel;
      const camera = graphId ? cameras.get(graphId) : undefined;
      if (control?.dataset.camera && camera) controlCamera(camera, control.dataset.camera);
    });
    for (const camera of cameras.values()) {
      camera.viewport.addEventListener('keydown', (event) => {
        if (event.target !== camera.viewport) return;
        const actions: Record<string, string> = { ArrowLeft: 'left', ArrowUp: 'up', ArrowDown: 'down', ArrowRight: 'right', '+': 'in', '=': 'in', '-': 'out', '0': 'fit' };
        const action = actions[event.key];
        if (action) { event.preventDefault(); controlCamera(camera, action); }
      });
      camera.viewport.addEventListener('wheel', (event) => {
        event.preventDefault();
        const matrix = camera.svg.getScreenCTM();
        if (!matrix) return;
        const anchor = new DOMPoint(event.clientX, event.clientY).matrixTransform(matrix.inverse());
        const delta = event.deltaY * (event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? camera.viewport.clientHeight : 1);
        camera.box = zoomDiagramBox(camera.box, camera.original, Math.exp(Math.max(-1200, Math.min(1200, delta)) * 0.0015), anchor);
        camera.mode = 'manual';
        updateCamera(camera);
      }, { passive: false });
      let drag: { id: number; x: number; y: number; original: number[]; inverse: DOMMatrix } | undefined;
      camera.viewport.addEventListener('pointerdown', (event) => {
        if (event.button !== 0 || !(event.target instanceof Element) || event.target.closest('a')) return;
        const matrix = camera.svg.getScreenCTM();
        if (!matrix) return;
        const inverse = matrix.inverse();
        const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(inverse);
        drag = { id: event.pointerId, x: point.x, y: point.y, original: [...camera.box], inverse };
        camera.viewport.setPointerCapture(event.pointerId);
        camera.viewport.classList.add('is-dragging');
      });
      camera.viewport.addEventListener('pointermove', (event) => {
        if (!drag || drag.id !== event.pointerId) return;
        const point = new DOMPoint(event.clientX, event.clientY).matrixTransform(drag.inverse);
        camera.box = [drag.original[0]! + drag.x - point.x, drag.original[1]! + drag.y - point.y, drag.original[2]!, drag.original[3]!];
        camera.mode = 'manual';
        updateCamera(camera);
      });
      const endDrag = (): void => { drag = undefined; camera.viewport.classList.remove('is-dragging'); };
      camera.viewport.addEventListener('pointerup', endDrag);
      camera.viewport.addEventListener('pointercancel', endDrag);
      camera.viewport.addEventListener('lostpointercapture', endDrag);
    }
    window.addEventListener('resize', () => {
      const camera = cameras.get(state.graph);
      if (!camera || view !== 'diagram') return;
      if (camera.mode === 'auto') focusCurrent(camera);
      updateCamera(camera);
    });
    window.addEventListener('hashchange', () => {
      if (window.location.hash.startsWith('#flow=')) {
        state = parseFlowHash(window.location.hash);
        render();
        announce('URLの回答履歴を復元しました。');
      } else if (window.location.hash.startsWith('#diagram-')) {
        chooseGraph(window.location.hash.slice('#diagram-'.length));
        view = 'diagram';
        render();
      }
    });
    render();
    announce(`${getGraph(state.graph).title}。${evaluateState(state).current.title}`);
  });
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeFlowcharts, { once: true });
else initializeFlowcharts();
document.addEventListener('astro:page-load', initializeFlowcharts);
