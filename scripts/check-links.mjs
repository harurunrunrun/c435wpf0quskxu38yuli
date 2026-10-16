import { readFile, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const base = '/flowchartcp';
const localOrigin = 'https://flowchartcp.invalid';
async function filesIn(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  return (await Promise.all(entries.filter(entry => !entry.name.startsWith('.')).map(entry => entry.isDirectory() ? filesIn(path.join(directory, entry.name)) : path.join(directory, entry.name)))).flat();
}
function unescapeHtml(value) {
  return value.replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").replace(/&#(\d+);/g, (_, number) => String.fromCodePoint(Number(number))).replace(/&#x([0-9a-f]+);/gi, (_, number) => String.fromCodePoint(parseInt(number, 16)));
}
export async function checkBuiltLinks({ directory = path.join(site, 'dist'), external = false, requirePagefind = true } = {}) {
  const errors = [];
  const allFiles = await filesIn(directory);
  const markupFiles = allFiles.filter(file => /\.(html|svg)$/.test(file));
  const contents = new Map();
  const externalUrls = new Set();
  const flowData = JSON.parse(await readFile(path.join(site, 'data/flows.json'), 'utf8'));
  const flowIds = new Set((Array.isArray(flowData) ? flowData : flowData.graphs).map(graph => graph.id));
  let checked = 0;
  let diagrams = 0;
  async function read(file) {
    if (!contents.has(file)) contents.set(file, await readFile(file, 'utf8'));
    return contents.get(file);
  }
  for (const file of markupFiles) {
    const relative = path.relative(directory, file).replaceAll(path.sep, '/');
    if (relative.startsWith('diagrams/') && relative.endsWith('.svg')) ++diagrams;
    const pagePath = `${base}/${relative.endsWith('/index.html') ? relative.slice(0, -10) : relative === 'index.html' ? '' : relative}`;
    const content = await read(file);
    for (const match of content.matchAll(/\b(?:href|src|xlink:href)\s*=\s*["']([^"']*)["']/gi)) {
      const link = unescapeHtml(match[1]);
      if (!link || /^(?:data|mailto|tel|javascript|blob):/i.test(link)) continue;
      let target;
      try { target = new URL(link, `${localOrigin}${pagePath}`); }
      catch { errors.push(`${relative}: invalid URL ${link}`); continue; }
      if (target.origin !== localOrigin) {
        if (/^https?:$/.test(target.protocol)) externalUrls.add(target.href.split('#')[0]);
        continue;
      }
      ++checked;
      if (!(target.pathname === base || target.pathname.startsWith(`${base}/`))) {
        errors.push(`${relative}: internal URL escapes ${base}/: ${link}`);
        continue;
      }
      let route;
      try { route = decodeURIComponent(target.pathname.slice(base.length)).replace(/^\//, ''); }
      catch { errors.push(`${relative}: invalid URL encoding ${link}`); continue; }
      let destination = path.resolve(directory, route || '.');
      if (destination !== path.resolve(directory) && !destination.startsWith(`${path.resolve(directory)}${path.sep}`)) {
        errors.push(`${relative}: internal URL escapes build directory: ${link}`); continue;
      }
      try {
        if ((await stat(destination)).isDirectory()) destination = path.join(destination, 'index.html');
        await stat(destination);
      } catch { errors.push(`${relative}: missing internal resource ${link}`); continue; }
      if (target.hash && /\.(html|svg)$/.test(destination)) {
        let fragment;
        try { fragment = decodeURIComponent(target.hash.slice(1)); }
        catch { errors.push(`${relative}: invalid anchor ${link}`); continue; }
        if (fragment.startsWith(':~:text=')) continue;
        if ((route.replace(/\/$/, '') === 'flowcharts' || /^diagrams\/[a-z0-9-]+\/$/.test(route)) && fragment.startsWith('flow=')) {
          const state = new URLSearchParams(target.hash.slice(1));
          const steps = state.get('steps') ?? '';
          if (!flowIds.has(state.get('flow')) || (steps !== '' && !steps.split(',').every(step => /^[ynu]$|^c:[a-z0-9-]+$/.test(step)))) errors.push(`${relative}: invalid shared flow state ${link}`);
          continue;
        }
        const ids = new Set([...(await read(destination)).matchAll(/\b(?:id|name)\s*=\s*["']([^"']+)["']/g)].map(value => unescapeHtml(value[1])));
        if (!ids.has(fragment)) errors.push(`${relative}: missing anchor ${link}`);
      }
    }
  }
  if (!markupFiles.some(file => path.relative(directory, file) === 'index.html')) errors.push('dist/index.html is missing. Run npm run build first.');
  if (!diagrams) errors.push('No generated SVG diagrams found in dist/diagrams/.');
  if (requirePagefind && !allFiles.some(file => /pagefind\/(?:pagefind\.js|pagefind\.ui\.js)$/.test(file.replaceAll(path.sep, '/')))) errors.push('Pagefind search bundle is missing.');
  if (external) {
    const dataFiles = (await readdir(path.join(site, 'data'))).filter(name => /^(references-|techniques-|sources)/.test(name) && name.endsWith('.json'));
    for (const name of dataFiles) {
      const data = await readFile(path.join(site, 'data', name), 'utf8');
      for (const match of data.matchAll(/"(https?:\/\/[^"\s]+)"/g)) externalUrls.add(match[1].split('#')[0]);
    }
    const queue = [...externalUrls];
    async function worker() {
      while (queue.length) {
        const url = queue.shift();
        try {
          const headers = { 'User-Agent': 'flowchartcp-link-checker/1.0' };
          let response = await fetch(url, { method: 'HEAD', redirect: 'follow', headers, signal: AbortSignal.timeout(12000) });
          if ([403, 405, 501].includes(response.status)) response = await fetch(url, { redirect: 'follow', headers: { ...headers, Range: 'bytes=0-0' }, signal: AbortSignal.timeout(12000) });
          await response.body?.cancel();
          if (!response.ok) errors.push(`External HTTP ${response.status}: ${url}`);
        } catch (error) { errors.push(`External unavailable (${error.message}): ${url}`); }
      }
    }
    await Promise.all(Array.from({ length: 4 }, worker));
  }
  return { errors, checked, pages: markupFiles.length, diagrams, external: external ? externalUrls.size : 0 };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const local = process.argv.includes('--local');
    const result = await checkBuiltLinks({ directory: path.join(site, local ? 'dist-local' : 'dist'), external: process.argv.includes('--external'), requirePagefind: !local });
    if (result.errors.length) {
      console.error(result.errors.map(error => `- ${error}`).join('\n'));
      console.error(`Link check failed: ${result.errors.length} issue(s).`);
      process.exitCode = 1;
    } else console.log(`Checked ${result.checked} local links/assets across ${result.pages} HTML/SVG files; ${result.diagrams} diagrams${result.external ? `; ${result.external} external URLs` : '. External requests disabled (use --external to enable)'}.`);
  } catch (error) { console.error(`${error.message}\nBuild the static site before verifying links.`); process.exitCode = 1; }
}
