/** Deterministic layered layout. Labels have their own space, just like nodes. */
export type LayoutBox = { x: number; y: number; width: number; height: number };
export type LayoutNode = { id: string; width: number; height: number };
export type LayoutEdge = { id: string; from: string; to: string; labelWidth: number; labelHeight: number };
export type LayoutEdgeDrawing = { before: string; after: string; label: LayoutBox };
export type LayeredLayout = { width: number; height: number; nodes: Map<string, LayoutBox>; edges: Map<string, LayoutEdgeDrawing> };
type Item = LayoutNode & { rank: number; kind: 'node' | 'label' | 'dummy'; parents: Item[]; children: Item[]; x: number; y: number };
type Connection = { from: Item; to: Item; edge: string; start: number; end: number };

export function layoutLayeredGraph(nodes: LayoutNode[], edges: LayoutEdge[], root: string): LayeredLayout {
  const nodeById = new Map(nodes.map(node => [node.id, node]));
  const outgoing = new Map(nodes.map(node => [node.id, [] as LayoutEdge[]]));
  const indegree = new Map(nodes.map(node => [node.id, 0]));
  for (const edge of edges) {
    outgoing.get(edge.from)!.push(edge);
    indegree.set(edge.to, indegree.get(edge.to)! + 1);
  }
  const queue = nodes.filter(node => indegree.get(node.id) === 0).map(node => node.id);
  const depth = new Map(nodes.map(node => [node.id, 0]));
  const order: string[] = [];
  for (let i = 0; i < queue.length; ++i) {
    const id = queue[i]!; order.push(id);
    for (const edge of outgoing.get(id)!) {
      depth.set(edge.to, Math.max(depth.get(edge.to)!, depth.get(id)! + 1));
      const remaining = indegree.get(edge.to)! - 1;
      indegree.set(edge.to, remaining);
      if (remaining === 0) queue.push(edge.to);
    }
  }
  if (order.length !== nodes.length || !nodeById.has(root)) throw new Error('A flow diagram must be an acyclic graph with a valid root.');
  const layers: Item[][] = [];
  const real = new Map<string, Item>();
  function item(id: string, rank: number, width: number, height: number, kind: Item['kind']): Item {
    const value: Item = { id, rank, width, height, kind, parents: [], children: [], x: 0, y: 0 };
    (layers[rank] ??= []).push(value);
    return value;
  }
  for (const id of order) {
    const node = nodeById.get(id)!;
    real.set(id, item(`node:${id}`, depth.get(id)! * 2, node.width, node.height, 'node'));
  }
  const connections: Connection[] = [];
  const chains = new Map<string, Item[]>();
  for (const edge of edges) {
    const from = real.get(edge.from)!, to = real.get(edge.to)!;
    const chain = [from, item(`label:${edge.id}`, from.rank + 1, edge.labelWidth, edge.labelHeight, 'label')];
    for (let rank = from.rank + 2; rank < to.rank; ++rank) chain.push(item(`pass:${edge.id}:${rank}`, rank, 12, 0, 'dummy'));
    chain.push(to); chains.set(edge.id, chain);
    for (let i = 1; i < chain.length; ++i) {
      const a = chain[i - 1]!, b = chain[i]!;
      a.children.push(b); b.parents.push(a);
      connections.push({ from: a, to: b, edge: edge.id, start: 0, end: 0 });
    }
  }
  const indexes = (): Map<Item, number> => new Map(layers.flatMap(layer => layer.map((value, index) => [value, index] as const)));
  function quality(): number {
    const index = indexes(); let crossings = 0;
    for (let rank = 0; rank + 1 < layers.length; ++rank) {
      const between = connections.filter(connection => connection.from.rank === rank);
      for (let i = 0; i < between.length; ++i) for (let j = 0; j < i; ++j) {
        const a = between[i]!, b = between[j]!;
        if ((index.get(a.from)! - index.get(b.from)!) * (index.get(a.to)! - index.get(b.to)!) < 0) ++crossings;
      }
    }
    return crossings;
  }
  // Long connections use small, invisible pass-through items. Include those in
  // the ordering, so a distant fallback does not cut across intermediate cards.
  let best = layers.map(layer => [...layer]), bestQuality = quality();
  for (let sweep = 0; sweep < 16; ++sweep) {
    const down = sweep % 2 === 0;
    const ranks = layers.map((_, rank) => rank);
    if (!down) ranks.reverse();
    for (const rank of ranks) {
      const index = indexes();
      const previous = new Map(layers[rank]!.map((value, i) => [value, i]));
      const average = (value: Item): number => {
        const neighbors = down ? value.parents : value.children;
        return neighbors.length ? neighbors.reduce((sum, neighbor) => sum + index.get(neighbor)!, 0) / neighbors.length : previous.get(value)!;
      };
      layers[rank]!.sort((a, b) => average(a) - average(b) || previous.get(a)! - previous.get(b)!);
    }
    const score = quality();
    if (score < bestQuality) { best = layers.map(layer => [...layer]); bestQuality = score; }
  }
  for (let rank = 0; rank < layers.length; ++rank) layers[rank] = best[rank]!;
  const gap = 44, margin = 32;
  const rowWidth = (layer: Item[]): number => layer.reduce((sum, value) => sum + value.width, 0) + Math.max(0, layer.length - 1) * gap;
  const width = Math.max(...layers.map(rowWidth)) + margin * 2;
  for (const layer of layers) {
    let x = (width - rowWidth(layer)) / 2;
    for (const value of layer) { value.x = x; x += value.width + gap; }
  }
  // Pull each card towards its neighbors while keeping a fixed, nonoverlapping
  // order. Wide label rows remain readable; narrow rows need not zigzag.
  for (let sweep = 0; sweep < 8; ++sweep) {
    const down = sweep % 2 === 0;
    const ranks = layers.map((_, rank) => rank); if (!down) ranks.reverse();
    for (const rank of ranks) {
      const layer = layers[rank]!;
      for (const value of layer) {
        const neighbors = down ? value.parents : value.children;
        if (neighbors.length) value.x = neighbors.reduce((sum, neighbor) => sum + neighbor.x + neighbor.width / 2, 0) / neighbors.length - value.width / 2;
      }
      for (let i = 0; i < layer.length; ++i) layer[i]!.x = Math.max(layer[i]!.x, i ? layer[i - 1]!.x + layer[i - 1]!.width + gap : margin);
      if (layer.length && layer.at(-1)!.x + layer.at(-1)!.width > width - margin) {
        layer.at(-1)!.x = width - margin - layer.at(-1)!.width;
        for (let i = layer.length - 2; i >= 0; --i) layer[i]!.x = Math.min(layer[i]!.x, layer[i + 1]!.x - gap - layer[i]!.width);
      }
    }
  }
  const rowBottom: number[] = [];
  let y = margin;
  for (let rank = 0; rank < layers.length; ++rank) {
    const layer = layers[rank]!, height = Math.max(0, ...layer.map(value => value.height));
    for (const value of layer) value.y = y;
    rowBottom[rank] = y + height;
    y += height + 88;
  }
  const height = y - 88 + margin;
  // Every distinct connection has its own port. Sort ports by the next row so
  // branches fan out without overlapping one another at their source/target.
  const incoming = new Map<Item, Connection[]>(), exiting = new Map<Item, Connection[]>();
  for (const connection of connections) {
    if (!exiting.has(connection.from)) exiting.set(connection.from, []);
    if (!incoming.has(connection.to)) incoming.set(connection.to, []);
    exiting.get(connection.from)!.push(connection); incoming.get(connection.to)!.push(connection);
  }
  for (const [value, list] of exiting) {
    list.sort((a, b) => a.to.x + a.to.width / 2 - b.to.x - b.to.width / 2);
    list.forEach((connection, index) => { connection.start = value.x + value.width * (index + 1) / (list.length + 1); });
  }
  for (const [value, list] of incoming) {
    list.sort((a, b) => a.from.x + a.from.width / 2 - b.from.x - b.from.width / 2);
    list.forEach((connection, index) => { connection.end = value.x + value.width * (index + 1) / (list.length + 1); });
  }
  const number = (n: number): string => String(Math.round(n * 1000) / 1000);
  function segment(connection: Connection): string {
    const { from, to, start, end } = connection;
    const leave = rowBottom[from.rank]! + 12;
    const arrive = to.y - 12;
    const middle = (leave + arrive) / 2;
    return `V${number(leave)} C${number(start)} ${number(middle)} ${number(end)} ${number(middle)} ${number(end)} ${number(arrive)} V${number(to.y)}`;
  }
  const drawings = new Map<string, LayoutEdgeDrawing>();
  for (const edge of edges) {
    const chain = chains.get(edge.id)!;
    const parts = connections.filter(connection => connection.edge === edge.id);
    const from = chain[0]!, label = chain[1]!;
    const first = parts[0]!;
    const before = `M${number(first.start)} ${number(from.y + from.height)} ${segment(first)}`;
    const second = parts[1]!;
    let after = `M${number(second.start)} ${number(label.y + label.height)}`;
    for (const connection of parts.slice(1)) after += ` ${segment(connection)}`;
    drawings.set(edge.id, { before, after, label: { x: label.x, y: label.y, width: label.width, height: label.height } });
  }
  return { width, height, nodes: new Map([...real].map(([id, value]) => [id, { x: value.x, y: value.y, width: value.width, height: value.height }])), edges: drawings };
}
