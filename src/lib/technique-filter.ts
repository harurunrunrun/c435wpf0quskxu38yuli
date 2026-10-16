export function initializeTechniqueFilters() {
  document.querySelectorAll<HTMLElement>('[data-technique-browser]').forEach(browser => {
    if (browser.dataset.filterReady) return;
    browser.dataset.filterReady = 'true';
    const input = browser.querySelector<HTMLInputElement>('[data-technique-filter]');
    input?.addEventListener('input', () => {
      const terms = input.value.normalize('NFKC').toLowerCase().trim().split(/\s+/).filter(Boolean);
      let count = 0;
      browser.querySelectorAll<HTMLElement>('[data-technique-card]').forEach(item => {
        item.hidden = !terms.every(term => item.dataset.search?.includes(term));
        if (!item.hidden) count++;
      });
      browser.querySelectorAll<HTMLElement>('[data-technique-family]').forEach(family => {
        family.hidden = !family.querySelector('[data-technique-card]:not([hidden])');
      });
      const status = browser.querySelector<HTMLElement>('[data-filter-status]');
      if (status) status.textContent = count ? `${count}件` : '該当する項目はありません。';
    });
  });
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', initializeTechniqueFilters, { once: true });
else initializeTechniqueFilters();
document.addEventListener('astro:page-load', initializeTechniqueFilters);
