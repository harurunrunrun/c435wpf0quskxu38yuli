import { readFile, writeFile, readdir, mkdir, cp, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { renderMarkdown } from '../vendor/markdown.mjs';
import { compileLocalModules } from './local-modules.mjs';
import { renderHome, renderTechniqueList, renderProblemReferences, sections, siteTitle } from '../src/lib/presentation.mjs';

const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const output=path.join(site,'dist-local');
const base='/flowchartcp/';
const esc=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const url=route=>base+route.replace(/^\//,'');
async function readData(prefix){return (await Promise.all((await readdir(path.join(site,'data'))).filter(name=>name.startsWith(prefix)&&name.endsWith('.json')).map(async name=>JSON.parse(await readFile(path.join(site,'data',name),'utf8')).map(item => prefix === 'techniques-' ? { ...item, kind: name.includes('-specific-') ? 'technique' : 'foundation' } : item)))).flat();}
const techniques=await readData('techniques-');
const references=await readData('references-');
const titles=Object.fromEntries(techniques.map(item=>[item.id,item.title]));
await rm(output,{recursive:true,force:true});
await mkdir(path.join(output,'assets'),{recursive:true});
await compileLocalModules(site,path.join(output,'assets'));
const flow=await import(pathToFileURL(path.join(output,'assets/flow.js')).href);
const viewer=await import(pathToFileURL(path.join(output,'assets/diagram-viewer.js')).href);
const nav=sections;
const homeHtml=()=>renderHome(techniques,base);
const gridHtml=(entry,heading,kind='technique')=>renderTechniqueList(techniques,{entry,heading,kind,base});
const referencesHtml=id=>renderProblemReferences(references,id,techniques.find(item=>item.id===id)?.aliases ?? []);
const sources=JSON.parse(await readFile(path.join(site,'data/sources.json'),'utf8'));
const ledger=JSON.parse(await readFile(path.join(site,'data/research-ledger.json'),'utf8'));
function researchHtml(){const statuses={'bootstrap-reviewed':'使用例の一部を確認','manual-pending':'手動調査待ち','not-started':'未着手','partial':'一部取得','failed':'取得失敗','complete':'対象索引の取得完了','metadata-complete':'対象索引の取得完了','corpus-partial':'固定群の一部を確認'};return `<p>把握した問題には、索引の情報だけを取得したものも含みます。解法確認は、掲載使用例と先に固定した問題群の重複を除いた件数です。</p><div class="research-scroll"><table><thead><tr><th>収集元</th><th>状態</th><th>総数</th><th>把握した問題</th><th>解法確認</th><th>技巧との対応</th></tr></thead><tbody>${sources.map(source=>{const p=ledger.sources.find(item=>item.source===source.id);return `<tr><td><a href="${esc(source.archive)}">${esc(source.name)}</a><small>${esc(source.language)}</small></td><td>${esc(statuses[p?.status]||p?.status||'未着手')}</td><td>${p?.totalKnown??'未確認'}</td><td>${p?.allProblemsObserved??p?.fetched??0}</td><td>${p?.allSolutionsReviewed??p?.solutionReviewed??0}</td><td>${p?.techniquesExtracted??0}</td></tr>`;}).join('')}</tbody></table></div><h2>収集元ごとの対象範囲</h2><div class="source-notes">${sources.map(source=>{const p=ledger.sources.find(item=>item.source===source.id);return `<details><summary>${esc(source.name)}</summary><p>${esc(p?.scope||source.notes)}</p><p>${esc(p?.notes)}</p><a href="${esc(source.archive)}">出典の一覧を見る ↗</a></details>`;}).join('')}</div>`;}
function pageShell(title,body,route){return `<!doctype html><html lang="ja" data-theme="light"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(title)} | ${siteTitle}</title><link rel="icon" href="${url('favicon.svg')}"><link rel="stylesheet" href="${url('assets/local.css')}"><link rel="stylesheet" href="${url('assets/katex/katex.min.css')}"><script type="module" src="${url('assets/local-ui.js')}"></script>${route==='flowcharts/'?`<script type="module" src="${url('assets/flow-client.js')}"></script>`:''}</head><body><a href="#main" class="skip-link">本文へ</a><header class="local-header"><a class="local-brand" href="${base}">${siteTitle}</a><button type="button" data-search-open>検索</button><button class="mobile-menu-button" type="button" data-menu-toggle aria-expanded="false" aria-controls="local-sidebar">目次</button></header><div class="local-layout"><aside class="local-sidebar" id="local-sidebar"><a class="sidebar-home" href="${base}">目次</a>${nav.map(item=>`<a href="${url(item.href)}" ${route===item.href?'aria-current="page"':''}>${item.title}</a>`).join('')}</aside><main id="main" class="sl-markdown-content">${route?`<h1>${esc(title)}</h1>`:''}${body}</main></div><dialog id="search-dialog" aria-labelledby="search-title"><div class="search-heading"><h2 id="search-title">検索</h2><button type="button" data-search-close aria-label="検索を閉じる">閉じる</button></div><label>検索語<input type="search" id="search-input" autocomplete="off"></label><p id="search-status" aria-live="polite">検索語を入力してください。</p><div id="search-results"></div></dialog></body></html>`;}
const searchEntries=[];
async function emitPage(route,title,source){
  let body=source.replace(/^---\n[\s\S]*?\n---\n/,'').replace(/^import .+;\s*$/gm,'');
  const componentBlocks=[];
  const marker=html=>{const id=componentBlocks.length;componentBlocks.push(html);return `\n\nFLOWCHARTCPCOMPONENT${id}END\n\n`;};
  body=body.replace(/<Home\s*\/>/g,()=>marker(homeHtml()));
  body=body.replace(/<TechniqueReferences\s+techniqueId="([^"]+)"\s*\/>/g,(_,id)=>marker(referencesHtml(id)));
  body=body.replace(/<TechniqueGrid\b([^>]*)\/>/g,(_,attrs)=>marker(gridHtml(attrs.match(/entry="([^"]+)"/)?.[1],attrs.match(/heading="([^"]+)"/)?.[1],attrs.match(/kind="([^"]+)"/)?.[1]||'technique')));
  body=body.replace(/<ResearchTables\s*\/>/g,()=>marker(researchHtml()));
  body=body.replace(/<Flowchart\b[^>]*\/>/g,()=>marker(flow.renderFlowHtml(base,titles)));
  const searchText=body.replace(/FLOWCHARTCPCOMPONENT\d+END/g,'').replace(/```[\s\S]*?```/g,' ').replace(/[#$*`<>]/g,' ');
  let html=renderMarkdown(body);
  html=html.replace(/(?:<p>)?FLOWCHARTCPCOMPONENT(\d+)END(?:<\/p>)?/g,(_,index)=>componentBlocks[Number(index)]);
  const destination=path.join(output,route);
  await mkdir(destination,{recursive:true});
  await writeFile(path.join(destination,'index.html'),pageShell(title,html,route));
  if(route.startsWith('techniques/')){
    const item=techniques.find(item=>route===`techniques/${item.id}/`);
    searchEntries.push({title,url:url(route),summary:item.summary,aliases:item.aliases,kind:item.kind,text:searchText});
  }
}
const docs=path.join(site,'src/content/docs');
for(const name of (await readdir(docs)).filter(name=>name.endsWith('.mdx'))){const source=await readFile(path.join(docs,name),'utf8');const title=(source.match(/^title:\s*(.+)$/m)?.[1]||name).replace(/^"|"$/g,'');await emitPage(name==='index.mdx'?'':name.replace('.mdx','/'),title,source);}
for(const item of techniques)await emitPage(`techniques/${item.id}/`,item.title,await readFile(path.join(docs,'techniques',item.id+'.mdx'),'utf8'));
await mkdir(path.join(output,'diagrams'),{recursive:true});
for(const graph of flow.graphs){
  await writeFile(path.join(output,'diagrams',graph.id+'.svg'),flow.renderFlowSvg(graph,base,titles));
  const destination=path.join(output,'diagrams',graph.id);
  await mkdir(destination,{recursive:true});
  await writeFile(path.join(destination,'index.html'),`<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(graph.title)}の図</title><link rel="icon" href="${url('favicon.svg')}"><link rel="stylesheet" href="${url('assets/diagram-viewer.css')}"><script type="module" src="${url('assets/diagram-viewer-client.js')}"></script></head><body>${viewer.renderDiagramViewerHtml(graph,base,titles)}</body></html>`);
}
await cp(path.join(site,'src/styles/diagram-viewer.css'),path.join(output,'assets/diagram-viewer.css'));
await writeFile(path.join(output,'assets/search.json'),JSON.stringify(searchEntries));
await cp(path.join(site,'public/favicon.svg'),path.join(output,'favicon.svg'));
await cp(path.join(site,'vendor/katex'),path.join(output,'assets/katex'),{recursive:true});
let styles=await readFile(path.join(site,'src/styles/local.css'),'utf8');
styles+='\n'+await readFile(path.join(site,'src/styles/custom.css'),'utf8');
for(const name of await readdir(path.join(site,'src/components'))){if(!name.endsWith('.astro'))continue;const component=await readFile(path.join(site,'src/components',name),'utf8');for(const match of component.matchAll(/<style(?:\s[^>]*)?>([\s\S]*?)<\/style>/g))styles+='\n'+match[1];}
await writeFile(path.join(output,'assets/local.css'),styles);
await cp(path.join(site,'src/lib/local-ui.js'),path.join(output,'assets/local-ui.js'));
await writeFile(path.join(output,'build-info.json'),JSON.stringify({mode:'local-preview',cutoff:'2026-10-14',techniques:techniques.length,references:references.length,graphs:flow.graphs.length},null,2)+'\n');
console.log(`Local build complete: ${techniques.length} technique articles, ${references.length} mappings, ${flow.graphs.length} SVG graphs.\nOutput: dist-local/\nPreview: npm run preview:local\nThis offline preview uses the shared content/flow source; the production build remains Astro/Starlight/Pagefind.`);
