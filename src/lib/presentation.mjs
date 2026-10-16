export const siteTitle = '競技プログラミング知識大全集';
export const sections = [
  { title: '解法フローチャート', href: 'flowcharts/' },
  { title: '計算量を減らすテクニック', href: 'complexity/' },
  { title: '高度なテクニック', href: 'advanced/' },
  { title: '考察のテクニック', href: 'reasoning/' },
  { title: 'テクニック一覧', href: 'catalog/' },
  { title: '基本アルゴリズム・データ構造', href: 'basics/' },
  { title: '出典', href: 'research/' },
];
export function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}
function link(base, route) { return `${base.replace(/\/$/, '')}/${route.replace(/^\//, '')}`; }
export function renderHome(techniques, base = '/flowchartcp/', { showTitle = true } = {}) {
  return `<div class="simple-home not-content">${showTitle ? `<h1>${siteTitle}</h1>` : ''}<h2>目次</h2><ul class="section-list">${sections.map(section => `<li><a data-section-link href="${link(base, section.href)}">${section.title}</a></li>`).join('')}</ul><h2>テクニックを探す</h2>${renderTechniqueList(techniques, { base })}</div>`;
}
export function renderTechniqueList(techniques, { entry, ids, heading, kind = 'technique', base = '/flowchartcp/' } = {}) {
  const items = techniques.filter(item => (kind === 'all' || item.kind === kind) && (!entry || item.entryPoints.includes(entry)) && (!ids || ids.includes(item.id)));
  const families = [...new Set(items.map(item => item.family))];
  return `<div class="technique-browser not-content" data-technique-browser>${heading ? `<h2>${escapeHtml(heading)}</h2>` : ''}<label class="filter-label">絞り込み<input type="search" data-technique-filter placeholder="名前・扱う条件" autocomplete="off"></label><p class="filter-status" data-filter-status aria-live="polite">${items.length}件</p>${families.map(family => `<section class="technique-family" data-technique-family><h3>${escapeHtml(family)}</h3><div class="technique-list">${items.filter(item => item.family === family).map(item => `<a class="technique-card" href="${link(base, `techniques/${item.id}/`)}" data-technique-card data-search="${escapeHtml([item.title, ...item.aliases, item.family, item.summary].join(' ').normalize('NFKC').toLowerCase())}"><span class="technique-name">${escapeHtml(item.title)}</span><span class="technique-summary">${escapeHtml(item.summary)}</span></a>`).join('')}</div></section>`).join('')}</div>`;
}
export function renderProblemReferences(references, techniqueId, aliases = []) {
  const rows = references.filter(item => item.techniqueId === techniqueId);
  const names = `<span class="search-aliases" aria-hidden="true">${escapeHtml(aliases.join(' '))}</span>`;
  const table = rows.length ? `<div class="reference-scroll"><table><thead><tr><th>問題</th><th>出典</th><th>解説・解答</th></tr></thead><tbody>${rows.map(item => `<tr><td><a href="${escapeHtml(item.url)}">${escapeHtml(item.title)}</a></td><td>${escapeHtml(item.source)}${item.difficulty ? `<br><small>${escapeHtml(item.difficulty)}</small>` : ''}</td><td>${item.editorialUrl ? `<a href="${escapeHtml(item.editorialUrl)}">${item.verification === 'independent-analysis' ? '問題文' : item.verification === 'editorial' ? '解説' : item.verification === 'official-tag' ? '問題形式' : '参照解答'}</a>` : ''}<details><summary>使用箇所</summary><p>${escapeHtml(item.evidence)}</p></details></td></tr>`).join('')}</tbody></table></div>` : '<p>使用例は調査中です。</p>';
  return `${names}<section class="technique-references" data-pagefind-ignore aria-labelledby="examples-${escapeHtml(techniqueId)}"><h2 id="examples-${escapeHtml(techniqueId)}">この手法を使う問題</h2>${table}</section>`;
}
