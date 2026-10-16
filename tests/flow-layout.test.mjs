import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { compileLocalModules } from '../scripts/local-modules.mjs';

const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const epsilon=0.1;
const decode=value=>value.replace(/&(?:amp|lt|gt|quot|apos|#39|#\d+|#x[\da-f]+);/gi,entity=>{
  const fixed={'&amp;':'&','&lt;':'<','&gt;':'>','&quot;':'"','&apos;':"'",'&#39;':"'"};
  return fixed[entity]??String.fromCodePoint(entity.startsWith('&#x')?parseInt(entity.slice(3,-1),16):Number(entity.slice(2,-1)));
});

// Parse emitted SVG without a browser, without importing the layout's geometry.
function parseSvg(source) {
  const root={tag:'root',attrs:{},children:[],text:'',parent:null};
  const stack=[root];
  for(const token of source.match(/<[^>]+>|[^<]+/g)??[]) {
    if(token.startsWith('</')) {stack.pop();continue;}
    if(token.startsWith('<?')||token.startsWith('<!')) continue;
    if(!token.startsWith('<')) {stack.at(-1).text+=decode(token);continue;}
    const tag=token.match(/^<([\w:-]+)/)?.[1];
    assert(tag,'invalid SVG opening tag');
    const attrs=Object.fromEntries([...token.matchAll(/([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)')/g)].map(m=>[m[1],decode(m[2]??m[3])]));
    const node={tag,attrs,children:[],text:'',parent:stack.at(-1)};
    node.parent.children.push(node);
    if(!token.endsWith('/>')) stack.push(node);
  }
  assert.equal(stack.length,1,'unbalanced SVG');
  return root.children.find(element=>element.tag==='svg');
}
function descendants(element,predicate=()=>true) {
  return element.children.flatMap(child=>[...(predicate(child)?[child]:[]),...descendants(child,predicate)]);
}
function assertSvgMatchesGraph(source,graph,optionsFor,base='/flowchartcp/') {
  const svg=parseSvg(source);assert(svg,`${graph.id}: missing svg`);
  assert.equal(svg.attrs['data-flow-svg'],graph.id,`${graph.id}: SVG identifies its canonical graph`);
  const all=descendants(svg);
  const renderedNodes=all.filter(element=>element.tag==='g'&&'data-node' in element.attrs);
  const renderedEdges=all.filter(element=>element.tag==='g'&&'data-edge' in element.attrs);
  const renderedLabels=all.filter(element=>element.tag==='g'&&'data-edge-label' in element.attrs);
  const canonicalNodes=new Map(graph.nodes.map(node=>[node.id,node]));
  const canonicalEdges=new Map(graph.nodes.flatMap(node=>node.type==='question'?optionsFor(node).map(option=>[
    `${node.id}:${option.id}:${node.answers[option.id]}`,option.label
  ]):[]));
  const assertExactIds=(elements,attribute,expected,kind)=>{
    const ids=elements.map(element=>element.attrs[attribute]);
    assert.equal(new Set(ids).size,ids.length,`${graph.id}: ${kind} identifiers must be unique`);
    assert.deepEqual([...ids].sort(),[...expected].sort(),`${graph.id}: ${kind} match canonical data`);
  };
  assertExactIds(renderedNodes,'data-node',canonicalNodes.keys(),'nodes');
  assertExactIds(renderedEdges,'data-edge',canonicalEdges.keys(),'edges');
  assertExactIds(renderedLabels,'data-edge-label',canonicalEdges.keys(),'answer labels');
  const textContent=element=>element.text+element.children.map(textContent).join('');
  for(const edge of renderedEdges) {
    const id=edge.attrs['data-edge'],label=canonicalEdges.get(id);
    assert.equal(edge.children.filter(element=>element.tag==='title').map(textContent).join(''),label,`${graph.id}: ${id} accessible answer label`);
    const labels=descendants(edge,element=>element.tag==='g'&&'data-edge-label' in element.attrs);
    assert.equal(labels.length,1,`${graph.id}: ${id} owns one answer label`);
    assert.equal(labels[0].attrs['data-edge-label'],id,`${graph.id}: ${id} owns its canonical label`);
    assert.equal(descendants(labels[0],element=>element.tag==='text').map(textContent).join(''),label,`${graph.id}: ${id} wrapped label preserves every character`);
    const paths=descendants(edge,element=>element.tag==='path');
    assert(paths.length>0,`${graph.id}: ${id} has a visible connection`);
    assert.equal(paths.filter(element=>'marker-end' in element.attrs).length,1,`${graph.id}: ${id} has one destination arrow`);
  }
  const routeLinks=all.filter(element=>'data-route' in element.attrs);
  assert.equal(routeLinks.length,graph.nodes.filter(node=>node.type==='route').length,`${graph.id}: one link per canonical route node`);
  const routeOwners=[];
  for(const link of routeLinks) {
    assert.equal(link.tag,'a',`${graph.id}: a route must be a link`);
    let owner=link.parent;
    while(owner&&!('data-node' in owner.attrs)) owner=owner.parent;
    const node=canonicalNodes.get(owner?.attrs['data-node']);
    assert.equal(node?.type,'route',`${graph.id}: a route link belongs to its canonical route node`);
    assert.equal(link.attrs['data-route'],node.graph,`${graph.id}: ${node.id} route target`);
    assert.equal(link.attrs.href,`${base}flowcharts/#diagram-${encodeURIComponent(node.graph)}`,`${graph.id}: ${node.id} route URL respects the site base`);
    routeOwners.push(node.id);
  }
  assert.equal(new Set(routeOwners).size,routeOwners.length,`${graph.id}: route links are unique within their nodes`);
}
function declarations(value) {
  return Object.fromEntries([...value.matchAll(/([\w-]+)\s*:\s*([^;]+)(?:;|$)/g)].map(m=>[m[1],m[2].trim()]));
}
function selectorMatches(element,selector) {
  const parts=selector.trim().split(/\s+/);
  const simple=(node,part)=>{
    const tag=part.match(/^[\w-]+/)?.[0];
    if(tag&&node.tag!==tag) return false;
    for(const m of part.matchAll(/\.([\w-]+)/g)) if(!(node.attrs.class??'').split(/\s+/).includes(m[1])) return false;
    for(const m of part.matchAll(/\[([\w-]+)(?:=['"]?([^\]'"]+)['"]?)?\]/g)) if(!(m[1] in node.attrs)||(m[2]!==undefined&&node.attrs[m[1]]!==m[2])) return false;
    return Boolean(tag||part.startsWith('.')||part.startsWith('['));
  };
  if(!simple(element,parts.pop())) return false;
  let ancestor=element.parent;
  while(parts.length) {
    while(ancestor&&!simple(ancestor,parts.at(-1))) ancestor=ancestor.parent;
    if(!ancestor) return false;
    parts.pop();ancestor=ancestor.parent;
  }
  return true;
}
function styleResolver(svg) {
  const css=descendants(svg,e=>e.tag==='style').map(e=>e.text).join('\n');
  const rules=[...css.matchAll(/([^{}]+)\{([^{}]*)\}/g)].flatMap(m=>m[1].split(',').map(selector=>({selector:selector.trim(),values:declarations(m[2])})));
  const specificity=selector=>(selector.match(/\./g)?.length??0)*10+(selector.match(/\[/g)?.length??0)*10+(selector.match(/(?:^|\s)[a-z][\w-]*/gi)?.length??0);
  const cache=new Map();
  return function resolve(element) {
    if(cache.has(element)) return cache.get(element);
    const inherited=element.parent&&element.parent.tag!=='root'?resolve(element.parent):{};
    const value={stroke:inherited.stroke??'none','font-size':inherited['font-size']??'16px','text-anchor':inherited['text-anchor']??'start','letter-spacing':inherited['letter-spacing']??'0px'};
    for(const name of ['stroke','font-size','text-anchor','letter-spacing']) if(name in element.attrs) value[name]=element.attrs[name];
    for(const rule of rules.filter(rule=>selectorMatches(element,rule.selector)).sort((a,b)=>specificity(a.selector)-specificity(b.selector))) Object.assign(value,rule.values);
    Object.assign(value,declarations(element.attrs.style??''));
    cache.set(element,value);return value;
  };
}
function offset(element) {
  let x=0,y=0;
  for(let node=element;node&&node.tag!=='root';node=node.parent) if(node.attrs.transform) {
    const translation=node.attrs.transform.match(/^translate\(\s*([-\d.e+]+)(?:[ ,]+([-\d.e+]+))?\s*\)$/i);
    assert(translation,`unsupported SVG transform: ${node.attrs.transform}`);
    x+=Number(translation[1]);y+=Number(translation[2]??0);
  }
  return {x,y};
}
function rectBox(rect,id) {
  const origin=offset(rect);
  const x=Number(rect.attrs.x??0)+origin.x,y=Number(rect.attrs.y??0)+origin.y;
  const width=Number(rect.attrs.width),height=Number(rect.attrs.height);
  assert([x,y,width,height].every(Number.isFinite)&&width>0&&height>0,`invalid reserved rectangle ${id}`);
  return {id,x,y,width,height,right:x+width,bottom:y+height};
}
function overlaps(a,b) {
  return Math.min(a.right,b.right)-Math.max(a.x,b.x)>epsilon&&Math.min(a.bottom,b.bottom)-Math.max(a.y,b.y)>epsilon;
}
function segmentEntersBox(a,b,box) {
  const xmin=box.x+epsilon,xmax=box.right-epsilon,ymin=box.y+epsilon,ymax=box.bottom-epsilon;
  if(Math.max(a.x,b.x)<xmin||Math.min(a.x,b.x)>xmax||Math.max(a.y,b.y)<ymin||Math.min(a.y,b.y)>ymax) return false;
  const dx=b.x-a.x,dy=b.y-a.y;
  let low=0,high=1;
  for(const [p,q] of [[-dx,a.x-xmin],[dx,xmax-a.x],[-dy,a.y-ymin],[dy,ymax-a.y]]) {
    if(Math.abs(p)<1e-12) {if(q<0)return false;continue;}
    const t=q/p;
    if(p<0) low=Math.max(low,t);else high=Math.min(high,t);
    if(low>high) return false;
  }
  return high>=low;
}
const midpoint=(a,b)=>({x:(a.x+b.x)/2,y:(a.y+b.y)/2});
function distanceToSegment(p,a,b) {
  const dx=b.x-a.x,dy=b.y-a.y,square=dx*dx+dy*dy;
  const t=square===0?0:Math.max(0,Math.min(1,((p.x-a.x)*dx+(p.y-a.y)*dy)/square));
  return Math.hypot(p.x-a.x-t*dx,p.y-a.y-t*dy);
}
function flattenCubic(points,depth=0) {
  const [a,b,c,d]=points;
  if(depth===18||Math.max(distanceToSegment(b,a,d),distanceToSegment(c,a,d))<0.025) return [[a,d]];
  const ab=midpoint(a,b),bc=midpoint(b,c),cd=midpoint(c,d),abc=midpoint(ab,bc),bcd=midpoint(bc,cd),center=midpoint(abc,bcd);
  return [...flattenCubic([a,ab,abc,center],depth+1),...flattenCubic([center,bcd,cd,d],depth+1)];
}
function pathPieces(element,edge) {
  const tokens=element.attrs.d.match(/[a-zA-Z]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?/g)??[];
  let current={x:0,y:0},command,index=0;
  const origin=offset(element),pieces=[];
  const number=()=>{assert(index<tokens.length&&!/^[A-Za-z]$/.test(tokens[index]),`invalid SVG path ${edge}`);return Number(tokens[index++]);};
  const movePoint=(x,y,relative)=>({x:x+(relative?current.x:0),y:y+(relative?current.y:0)});
  const absolute=p=>({x:p.x+origin.x,y:p.y+origin.y});
  while(index<tokens.length) {
    if(/^[A-Za-z]$/.test(tokens[index])) command=tokens[index++];
    assert(command,`path must start with a command ${edge}`);
    const relative=command===command.toLowerCase(),kind=command.toUpperCase();
    let end;
    if(kind==='M') {current=movePoint(number(),number(),relative);command=relative?'l':'L';continue;}
    if(kind==='C') {
      const b=movePoint(number(),number(),relative),c=movePoint(number(),number(),relative);
      end=movePoint(number(),number(),relative);
      const controls=[current,b,c,end].map(absolute);
      pieces.push({edge,kind:'C',controls,segments:flattenCubic(controls)});
    } else {
      if(kind==='V') end={x:current.x,y:number()+(relative?current.y:0)};
      else if(kind==='H') end={x:number()+(relative?current.x:0),y:current.y};
      else if(kind==='L') end=movePoint(number(),number(),relative);
      else assert.fail(`unsupported edge path command ${command} in ${edge}`);
      const controls=[absolute(current),absolute(end)];
      pieces.push({edge,kind:'L',controls,segments:[controls]});
    }
    current=end;
  }
  return pieces;
}
function containsPoint(box,point,tolerance=0.15) {
  return point.x>=box.x-tolerance&&point.x<=box.right+tolerance&&point.y>=box.y-tolerance&&point.y<=box.bottom+tolerance;
}
function textBox(element,styles) {
  const style=styles(element),font=parseFloat(style['font-size']),position=offset(element);
  assert(Number.isFinite(font)&&font>0,'explicit SVG text size required');
  const text=element.text;
  const spacing=style['letter-spacing'].endsWith('em')?parseFloat(style['letter-spacing'])*font:parseFloat(style['letter-spacing'])||0;
  // A full em per character also reserves room for bold and fallback fonts.
  const width=[...text].length*font+Math.max(0,[...text].length-1)*spacing;
  const anchor=style['text-anchor'];
  const right=Number(element.attrs.x)+position.x;
  const x=right-(anchor==='end'?width:anchor==='middle'?width/2:0);
  const baseline=Number(element.attrs.y)+position.y;
  return {x,y:baseline-font,width,height:font*1.25,right:x+width,bottom:baseline+font*.25,text};
}
function assertSvgGeometry(source,id,expectedLabels) {
  const svg=parseSvg(source);assert(svg,`${id}: missing svg`);
  const [x,y,width,height]=(svg.attrs.viewBox??'').split(/[ ,]+/).map(Number);
  const canvas={x,y,width,height,right:x+width,bottom:y+height};
  assert([x,y,width,height].every(Number.isFinite)&&width>0&&height>0,`${id}: viewBox`);
  const styles=styleResolver(svg),all=descendants(svg);
  const nodes=all.filter(e=>e.tag==='g'&&'data-node' in e.attrs);
  const labels=all.filter(e=>e.tag==='g'&&'data-edge-label' in e.attrs);
  const edges=all.filter(e=>e.tag==='g'&&'data-edge' in e.attrs);
  if(expectedLabels!==undefined) assert.equal(labels.length,expectedLabels,`${id}: one reserved answer label per canonical edge`);
  assert.equal(new Set(labels.map(group=>group.attrs['data-edge-label'])).size,labels.length,`${id}: answer reservations must be unique`);
  for(const label of labels) {
    let owner=label.parent;
    while(owner&&!(owner.attrs&&'data-edge' in owner.attrs)) owner=owner.parent;
    assert.equal(label.attrs['data-edge-label'],owner?.attrs['data-edge'],`${id}: answer reservation belongs to its edge`);
  }
  const regions=[...nodes.map(group=>({group,type:'node',box:rectBox(group.children.find(e=>e.tag==='rect'),`node ${group.attrs['data-node']}`)})),
    ...labels.map(group=>({group,type:'label',box:rectBox(group.children.find(e=>e.tag==='rect'),`label ${group.attrs['data-edge-label']}`)}))];
  // For the frozen old SVG below, infer the formerly unreserved text area.
  // Canonical output must still provide explicit boxes (checked above).
  for(const group of edges) if(!descendants(group,e=>'data-edge-label' in e.attrs).length) {
    const text=group.children.filter(e=>e.tag==='text').map(e=>textBox(e,styles));
    if(text.length) {
      const x=Math.min(...text.map(b=>b.x)),y=Math.min(...text.map(b=>b.y)),right=Math.max(...text.map(b=>b.right)),bottom=Math.max(...text.map(b=>b.bottom));
      regions.push({group,type:'label',box:{id:`label ${group.attrs['data-edge']}`,x,y,right,bottom,width:right-x,height:bottom-y}});
    }
  }
  for(let i=0;i<regions.length;++i) {
    const region=regions[i];
    assert(containsPoint(canvas,{x:region.box.x,y:region.box.y})&&containsPoint(canvas,{x:region.box.right,y:region.box.bottom}),`${id}: ${region.box.id} outside viewBox`);
    for(const other of regions.slice(i+1)) assert(!overlaps(region.box,other.box),`${id}: ${region.box.id} overlaps ${other.box.id}`);
    for(const text of descendants(region.group,e=>e.tag==='text')) {
      const bounds=textBox(text,styles);
      assert(containsPoint(region.box,{x:bounds.x,y:bounds.y})&&containsPoint(region.box,{x:bounds.right,y:bounds.bottom}),`${id}: ${region.box.id} text exceeds its reservation: ${bounds.text}`);
      if(region.type==='label') assert.equal(styles(text).stroke,'none',`${id}: answer text must not inherit an edge stroke`);
    }
  }
  const arrowTips=[];
  const markers=all.filter(element=>element.tag==='marker');
  for(const edge of edges) for(const arrow of descendants(edge,element=>element.tag==='path'&&'marker-end' in element.attrs)) {
    const markerId=arrow.attrs['marker-end'].match(/^url\(#([^)]*)\)$/)?.[1];
    const marker=markers.find(element=>element.attrs.id===markerId);
    assert(marker,`${id}: missing arrowhead`);
    assert.equal(marker.attrs.markerUnits,'userSpaceOnUse',`${id}: arrowheads must stay small when an edge is highlighted`);
    const endpoint=pathPieces(arrow,edge.attrs['data-edge']).at(-1).controls.at(-1);
    arrowTips.push({...endpoint,width:Number(marker.attrs.markerHeight),edge:edge.attrs['data-edge']});
  }
  for(let i=0;i<arrowTips.length;++i) for(const other of arrowTips.slice(i+1)) {
    const arrow=arrowTips[i];
    if(Math.abs(arrow.y-other.y)<epsilon) assert(Math.abs(arrow.x-other.x)+epsilon>=(arrow.width+other.width)/2,`${id}: neighboring arrowheads overlap: ${arrow.edge} / ${other.edge}`);
  }
  const pieces=edges.flatMap(edge=>descendants(edge,e=>e.tag==='path').flatMap(p=>pathPieces(p,edge.attrs['data-edge'])));
  for(const piece of pieces) for(const [a,b] of piece.segments) {
    assert(containsPoint(canvas,a)&&containsPoint(canvas,b),`${id}: ${piece.edge} leaves viewBox`);
    for(const {box} of regions) assert(!segmentEntersBox(a,b,box),`${id}: ${piece.edge} enters ${box.id}`);
  }
  // Shared-target merges can be intentional. Different destinations must not
  // reuse a visible straight run or an identical cubic curve.
  for(let i=0;i<pieces.length;++i) for(const second of pieces.slice(i+1)) {
    const first=pieces[i];
    if(first.edge===second.edge||first.edge.split(':').at(-1)===second.edge.split(':').at(-1)) continue;
    const firstVertical=first.controls.every(p=>Math.abs(p.x-first.controls[0].x)<1e-7);
    const secondVertical=second.controls.every(p=>Math.abs(p.x-second.controls[0].x)<1e-7);
    const firstHorizontal=first.controls.every(p=>Math.abs(p.y-first.controls[0].y)<1e-7);
    const secondHorizontal=second.controls.every(p=>Math.abs(p.y-second.controls[0].y)<1e-7);
    for(const [aligned,axis,position] of [[firstVertical&&secondVertical,'y','x'],[firstHorizontal&&secondHorizontal,'x','y']]) if(aligned&&Math.abs(first.controls[0][position]-second.controls[0][position])<1e-7) {
      const extent=points=>[Math.min(...points.map(p=>p[axis])),Math.max(...points.map(p=>p[axis]))];
      const a=extent(first.controls),b=extent(second.controls);
      assert(Math.min(a[1],b[1])-Math.max(a[0],b[0])<=8,`${id}: different destinations share a long straight run: ${first.edge} / ${second.edge}`);
    }
    if(first.kind==='C'&&second.kind==='C') {
      const equal=(a,b)=>a.every((p,i)=>Math.hypot(p.x-b[i].x,p.y-b[i].y)<1e-7);
      assert(!(equal(first.controls,second.controls)||equal(first.controls,[...second.controls].reverse())),`${id}: different destinations share a cubic: ${first.edge} / ${second.edge}`);
    }
  }
}

const result=(id,title)=>({id,type:'result',title,techniques:['prefix-sum'],conditions:['入力を確認する。']});
const fixtures=[{
  id:'layout-long-answer',title:'長い回答',description:'長い回答の折返し',root:'q',nodes:[
    {id:'q',type:'question',title:'問題の条件は何か',explanation:'当てはまる条件を選ぶ。',options:[{id:'long',label:'同じ条件について長い説明が続くときも、回答を折り返した全ての行と次の回答を読み分けられる必要がある。'},{id:'unknown',label:'わからない'}],answers:{long:'a',unknown:'b'}},result('a','候補一'),result('b','候補二')]
},{
  id:'layout-crossed-branches',title:'同じ階層の分岐',description:'交差する対応と共有の到達先',root:'q',nodes:[
    {id:'q',type:'question',title:'どの量を求めるか',options:[{id:'left',label:'左の条件'},{id:'right',label:'右の条件'},{id:'unknown',label:'わからない'}],answers:{left:'left',right:'right',unknown:'fallback'}},
    {id:'left',type:'question',title:'左側の追加条件を満たすか',answers:{yes:'result-right',no:'fallback',unknown:'fallback'}},
    {id:'right',type:'question',title:'右側の追加条件を満たすか',explanation:'異なる高さのノードも隣に置く。'.repeat(5),answers:{yes:'result-left',no:'fallback',unknown:'fallback'}},
    result('result-left','左の候補'),result('result-right','右の候補'),result('fallback','条件を確認する')]
},{
  id:'layout-escaped-route',title:'記号と分野への接続',description:'折返しやHTML記号で回答を変更しない',root:'q',nodes:[
    {id:'q',type:'question',title:'値と条件を確認する',options:[{id:'compare',label:'A < B & C > D のとき「値」と "個数" を区別する'},{id:'unknown',label:'わからない'}],answers:{compare:'route',unknown:'result'}},
    {id:'route',type:'route',title:'配列の条件を続けて確認する',graph:'ranges'},result('result','条件を確認する')]
}];

test('the canonical SVG checker rejects missing, duplicated or relabeled branches and an incorrect route URL',()=>{
  const graph={id:'canonical-probe',root:'q',nodes:[
    {id:'q',type:'question',options:[{id:'pick',label:'条件を確認する'},{id:'unknown',label:'わからない'}],answers:{pick:'route',unknown:'result'}},
    {id:'route',type:'route',graph:'ranges'},result('result','候補')
  ]};
  const optionsFor=node=>node.options;
  const first='<g data-edge="q:pick:route"><title>条件を確認する</title><path d="M0 0 V10" marker-end="url(#arrow)"/><g data-edge-label="q:pick:route"><text>条件を</text><text>確認する</text></g></g>';
  const second='<g data-edge="q:unknown:result"><title>わからない</title><path d="M1 0 V10" marker-end="url(#arrow)"/><g data-edge-label="q:unknown:result"><text>わからない</text></g></g>';
  const source='<svg data-flow-svg="canonical-probe"><g data-node="q"/><g data-node="route"><a data-route="ranges" href="/flowchartcp/flowcharts/#diagram-ranges"/></g><g data-node="result"/>'+first+second+'</svg>';
  assertSvgMatchesGraph(source,graph,optionsFor);
  assert.throws(()=>assertSvgMatchesGraph(source.replace('<g data-node="result"/>',''),graph,optionsFor),/nodes match canonical data/);
  assert.throws(()=>assertSvgMatchesGraph(source.replace('</svg>','<g data-node="q"/></svg>'),graph,optionsFor),/nodes identifiers must be unique/);
  assert.throws(()=>assertSvgMatchesGraph(source.replace(second,''),graph,optionsFor),/edges match canonical data/);
  assert.throws(()=>assertSvgMatchesGraph(source.replace('</svg>',first+'</svg>'),graph,optionsFor),/edges identifiers must be unique/);
  assert.throws(()=>assertSvgMatchesGraph(source.replace('<text>確認する</text>','<text>変更する</text>'),graph,optionsFor),/wrapped label preserves every character/);
  assert.throws(()=>assertSvgMatchesGraph(source.replace('href="/flowchartcp/flowcharts/#diagram-ranges"','href="/flowcharts/#diagram-ranges"'),graph,optionsFor),/route URL respects the site base/);
});

test('the geometry checker detects the old label-through-line pattern and a cubic crossing a box',()=>{
  const start='<svg viewBox="0 0 200 200"><style>.flow-edge text{font-size:12px;stroke:none}</style>';
  const label='<g data-edge-label="q:unknown:b"><rect x="40" y="70" width="100" height="25"/><text x="45" y="87">わからない</text></g>';
  assert.throws(()=>assertSvgGeometry(start+'<g data-edge="q:unknown:b"><path d="M50 30 V120"/>'+label+'</g></svg>','legacy'),/enters label/);
  // Exact edge/text coordinates from the former adjacent-merge-cost.svg.
  const old='<svg viewBox="0 0 1000 1000"><style>.flow-edge text{font-size:12px;stroke:none}</style><g class="flow-edge unknown" data-edge="adjacent:unknown:check"><title>わからない</title><path d="M467.5 216 V316 H778 V697 H638.5 V710"/><text text-anchor="end" x="525" y="309">わからない</text></g></svg>';
  assert.throws(()=>assertSvgGeometry(old,'old-adjacent-merge-cost'),/enters label/);
  const node='<g data-node="obstacle"><rect x="80" y="80" width="40" height="40"/></g>';
  assert.throws(()=>assertSvgGeometry(start+'<g data-edge="q:yes:a"><path d="M20 100 C70 100 130 100 180 100"/></g>'+node+'</svg>','curve'),/enters node/);
  assert.throws(()=>assertSvgGeometry(start+'<g data-edge="q:yes:a"><path d="M20 20 V150"/></g><g data-edge="q:no:b"><path d="M20 50 V180"/></g></svg>','same-run'),/share a long straight run/);
  assert.throws(()=>assertSvgGeometry(start+'<g data-edge="q:yes:a"><path d="M20 20 C80 20 80 150 150 150"/></g><g data-edge="q:no:b"><path d="M20 20 C80 20 80 150 150 150"/></g></svg>','same-curve'),/share a cubic/);
});

test('all diagrams preserve canonical nodes, choices and routes while keeping text and curves in separate reservations',async()=>{
  const temp=await mkdtemp(path.join(tmpdir(),'flowchartcp-layout-regression-'));
  try {
    await compileLocalModules(site,temp);
    const flow=await import(pathToFileURL(path.join(temp,'flow.js')).href);
    const data=await readdir(path.join(site,'data'));
    const rows=await Promise.all(data.filter(name=>/^techniques-.*\.json$/.test(name)).map(async name=>JSON.parse(await readFile(path.join(site,'data',name),'utf8'))));
    const titles=Object.fromEntries(rows.flat().map(row=>[row.id,row.title]));
    for(const graph of [...flow.graphs,...fixtures]) {
      const expected=graph.nodes.reduce((count,node)=>count+(node.type==='question'?flow.getNodeOptions(node).length:0),0);
      const svg=flow.renderFlowSvg(graph,'/flowchartcp/',titles);
      assertSvgMatchesGraph(svg,graph,flow.getNodeOptions);
      assertSvgGeometry(svg,graph.id,expected);
    }
    for(const base of ['/','/nested/site/']) {
      const graph=fixtures.at(-1);
      assertSvgMatchesGraph(flow.renderFlowSvg(graph,base,titles),graph,flow.getNodeOptions,base);
    }
  } finally {await rm(temp,{recursive:true,force:true});}
});
