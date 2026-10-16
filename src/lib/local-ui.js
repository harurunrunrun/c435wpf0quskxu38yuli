import './technique-filter.js';
const normalize=value=>String(value??'').normalize('NFKC').toLowerCase();
const toggle=document.querySelector('[data-menu-toggle]');
toggle?.addEventListener('click',()=>{const open=toggle.getAttribute('aria-expanded')!=='true';toggle.setAttribute('aria-expanded',String(open));document.querySelector('#local-sidebar').classList.toggle('menu-open',open);});
const dialog=document.querySelector('#search-dialog');
const input=document.querySelector('#search-input');
const resultList=document.querySelector('#search-results');
const status=document.querySelector('#search-status');
let indexPromise;
let queryVersion=0;
function openSearch(){dialog.showModal();input.focus();}
document.querySelector('[data-search-open]')?.addEventListener('click',openSearch);
document.querySelector('[data-search-close]')?.addEventListener('click',()=>dialog.close());
document.addEventListener('keydown',event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();if(!dialog.open)openSearch();}});
dialog?.addEventListener('click',event=>{if(event.target===dialog){const box=dialog.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)dialog.close();}});
input?.addEventListener('input',async()=>{
  const version=++queryVersion;
  const terms=normalize(input.value).trim().split(/\s+/).filter(Boolean);
  resultList.replaceChildren();
  if(!terms.length){status.textContent='検索語を入力してください。';return;}
  status.textContent='検索しています…';
  try{
    indexPromise??=fetch(new URL('./search.json',import.meta.url)).then(response=>{if(!response.ok)throw new Error('検索データを取得できません');return response.json();});
    const index=await indexPromise;if(version!==queryVersion)return;
    const results=index.map(item=>{const headline=normalize([item.title,...item.aliases].join(' '));const text=normalize(headline+' '+item.summary+' '+item.text);return {...item,score:terms.reduce((score,term)=>score+(headline.includes(term)?10:1),0),match:terms.every(term=>text.includes(term))};}).filter(item=>item.match).sort((a,b)=>b.score-a.score);
    status.textContent=results.length?`${results.length} 件`:'該当する項目はありません。';
    for(const item of results.slice(0,50)){const link=document.createElement('a');link.href=item.url;const title=document.createElement('strong');title.textContent=item.title;const summary=document.createElement('span');summary.textContent=item.summary;const aliases=document.createElement('small');aliases.textContent=item.aliases.join(' / ');link.append(title,summary,aliases);resultList.append(link);}
  }catch(error){if(version===queryVersion){indexPromise=undefined;status.textContent=error.message+'。もう一度入力してください。';}}
});
