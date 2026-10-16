import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { pathToFileURL, fileURLToPath } from 'node:url';
import { runInNewContext } from 'node:vm';
import { compileLocalModules } from '../scripts/local-modules.mjs';

const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
class Element {
  constructor(tag='div') { this.tag=tag;this.dataset={};this.children=[];this.handlers={};this.attributes={};this.textContent='';this.className='';this.hidden=false; }
  addEventListener(type,handler) { this.handlers[type]=handler; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children=[...items]; }
  setAttribute(name,value) { this.attributes[name]=String(value); }
  removeAttribute(name) { delete this.attributes[name]; }
  focus() {}
  matches(selector) {
    if(selector.startsWith('.')) return this.className.split(' ').includes(selector.slice(1));
    if(selector==='[data-answer]') return this.dataset.answer!==undefined;
    if(selector==='[data-domain-graph]') return this.dataset.domainGraph!==undefined;
    return this.tag===selector;
  }
  closest(selector) { return this.matches(selector)?this:null; }
  querySelectorAll(selector) { return this.children.flatMap(child=>[...(child.matches(selector)?[child]:[]),...child.querySelectorAll(selector)]); }
  querySelector(selector) { return this.querySelectorAll(selector)[0]??null; }
}

test('actual field-link handlers restore detailed answers, sharing and display mode', async()=>{
  const temp=await mkdtemp(path.join(tmpdir(),'flowchartcp-field-client-'));
  try {
    await compileLocalModules(site,temp);
    const flow=await import(pathToFileURL(path.join(temp,'flow.js')).href);
    const source=(await readFile(path.join(temp,'flow-client.js'),'utf8')).replace(/^import .+;\s*$/gm,'');
    const controls=new Map();
    for(const selector of ['[data-graph-select]','[data-question-panel]','[data-current-node]','[data-diagrams]',
      '[data-flow-status]','[data-flow-history]','[data-history-count]','[data-flow-back]','[data-share-box]',
      '[data-share-url]','[data-flow-reset]','[data-flow-share]','.flow-static-nav']) controls.set(selector,new Element());
    const links=flow.entryGraphs.map(graph=>{const e=new Element('a');e.dataset.domainGraph=graph.id;return e;});
    const views=['questions','diagram'].map(view=>{const e=new Element('button');e.dataset.view=view;return e;});
    const root=new Element();root.dataset.base='/flowchartcp/';
    root.querySelector=selector=>controls.get(selector)??null;
    root.querySelectorAll=selector=>selector==='[data-domain-graph]'?links:selector==='[data-view]'?views:[];
    const window={location:{hash:'',pathname:'/flowchartcp/flowcharts/',search:'',href:'https://flowchartcp.invalid/flowchartcp/flowcharts/'},addEventListener(){},history:{replaceState(_state,_unused,url){const value=new URL(url,'https://flowchartcp.invalid');window.location.hash=value.hash;window.location.href=value.href;}}};
    runInNewContext(source,{...flow,Element,URL,URLSearchParams,window,navigator:{clipboard:{writeText:async()=>{}}},
      document:{readyState:'complete',querySelectorAll:()=>[root],createElement:tag=>new Element(tag),addEventListener(){}}});
    const panel=controls.get('[data-current-node]');
    const title=()=>panel.querySelector('h3').textContent;
    const clickDomain=id=>root.handlers.click({target:links.find(link=>link.dataset.domainGraph===id),preventDefault(){}});
    const clickAnswer=id=>panel.querySelectorAll('[data-answer]').find(button=>button.dataset.answer===id).handlers.click();
    const range=flow.getGraph('ranges'), question=flow.evaluateState(flow.initialState('ranges')).current;
    const choice=flow.getNodeOptions(question).find(option=>range.nodes.find(node=>node.id===question.answers[option.id]).type==='route');
    assert(choice);
    clickDomain('ranges');assert.equal(title(),question.title);
    clickAnswer(choice.id);
    const route=flow.evaluateState(flow.answerState(flow.initialState('ranges'),choice.id)).current;
    panel.querySelector('.flow-route-button').handlers.click();
    const detail=flow.getGraph(route.graph), detailRoot=flow.evaluateState(flow.initialState(detail.id)).current;
    const answer=flow.getNodeOptions(detailRoot).find(option=>option.id!=='unknown');
    clickAnswer(answer.id);
    const detailTitle=detail.nodes.find(node=>node.id===detailRoot.answers[answer.id]).title;
    assert.equal(title(),detailTitle);
    const before=window.location.hash;
    views[1].handlers.click();assert.equal(window.location.hash,before);
    assert.equal(controls.get('[data-question-panel]').hidden,true);
    clickDomain('strings');assert.equal(controls.get('[data-graph-select]').value,'strings');
    clickDomain('ranges');assert.equal(controls.get('[data-graph-select]').value,detail.id);
    assert.equal(title(),detailTitle);assert.equal(controls.get('[data-history-count]').textContent,'2');
    assert.equal(controls.get('[data-question-panel]').hidden,true);
    assert.equal(links.find(link=>link.dataset.domainGraph==='ranges').attributes['aria-current'],'true');
    views[0].handlers.click();assert.equal(controls.get('[data-question-panel]').hidden,false);
    await controls.get('[data-flow-share]').handlers.click();
    const shared=flow.parseFlowHash(new URL(controls.get('[data-share-url]').value).hash);
    assert.equal(flow.getFlowDomainId(shared),'ranges');
    assert.equal(flow.evaluateState(shared).current.title,detailTitle);
    controls.get('[data-flow-back]').handlers.click();assert.equal(title(),detailRoot.title);
  } finally { await rm(temp,{recursive:true,force:true}); }
});
