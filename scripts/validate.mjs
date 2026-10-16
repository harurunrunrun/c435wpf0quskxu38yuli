import { readFile, readdir, access } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { readCorpusProgress, canonicalProblemKey, sourceIdFor } from './lib/corpus-progress.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const headings = ['使う場面', '考え方', '適用条件', 'なぜ正しいか', '計算量', '実装', '関連する手法', '参考資料'];
const verifiedKinds = new Set(['editorial', 'reference-solution', 'official-tag', 'independent-analysis']);
const slug = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const text = value => typeof value === 'string' && value.trim().length > 0;
function httpUrl(value) {
  try { const url = new URL(value); return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password; }
  catch { return false; }
}
async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  return (await Promise.all(entries.filter(entry => !entry.name.startsWith('.')).map(entry => entry.isDirectory() ? walk(path.join(directory, entry.name)) : path.join(directory, entry.name)))).flat();
}

/** Read-only: validate authored content and the acquisition ledger without regenerating either. */
export async function validateSite(root = site) {
  const errors = [];
  const require = (condition, message) => { if (!condition) errors.push(message); };
  async function json(relative) {
    try { return JSON.parse(await readFile(path.join(root, relative), 'utf8')); }
    catch (error) { errors.push(`${relative}: ${error.message}`); return null; }
  }
  const files = await readdir(path.join(root, 'data'));
  const techniqueFiles = files.filter(name => /^techniques-.*\.json$/.test(name)).sort();
  const referenceFiles = files.filter(name => /^references-.*\.json$/.test(name)).sort();
  require(techniqueFiles.length > 0 && referenceFiles.length > 0, '技巧と使用例の構造化データが必要です。');
  async function joinArrays(names) {
    const result = [];
    for (const name of names) {
      const rows = await json(`data/${name}`);
      require(Array.isArray(rows), `data/${name}: 配列が必要です。`);
      if (Array.isArray(rows)) result.push(...rows);
    }
    return result;
  }
  const techniques = await joinArrays(techniqueFiles);
  const references = await joinArrays(referenceFiles);
  const techniqueMap = new Map();
  for (const technique of techniques) {
    const label = `技巧 ${technique.id}`;
    require(slug.test(technique.id ?? ''), `${label}: IDの形式が不正です。`);
    require(!techniqueMap.has(technique.id), `${label}: IDが重複しています。`);
    techniqueMap.set(technique.id, technique);
    for (const key of ['title', 'summary', 'family', 'level', 'status']) require(text(technique[key]), `${label}: ${key}が必要です。`);
    for (const key of ['aliases', 'entryPoints', 'prerequisites', 'sources']) require(Array.isArray(technique[key]), `${label}: ${key}は配列です。`);
    require(technique.aliases?.length > 0, `${label}: 検索用別名が必要です。`);
    require(technique.sources?.length > 0, `${label}: 根拠資料が必要です。`);
    for (const url of technique.sources ?? []) require(httpUrl(url), `${label}: 根拠資料URLが不正です: ${url}`);
    for (const point of technique.entryPoints ?? []) require(['complexity', 'advanced', 'reasoning'].includes(point), `${label}: 不明な入口 ${point}`);
  }
  for (const technique of techniques) for (const id of technique.prerequisites ?? []) {
    require(techniqueMap.has(id), `${technique.id}: 前提技巧 ${id} が存在しません。`);
    require(id !== technique.id, `${technique.id}: 自分自身を前提技巧にできません。`);
  }
  const prerequisiteColor = new Map();
  function prerequisiteOrder(id) {
    if (prerequisiteColor.get(id) === 1) { errors.push(`${id}: 前提技巧が循環しています。相互参照は関連技巧へ移してください。`); return; }
    if (prerequisiteColor.get(id) === 2) return;
    prerequisiteColor.set(id, 1);
    for (const prerequisite of techniqueMap.get(id)?.prerequisites ?? []) if (techniqueMap.has(prerequisite)) prerequisiteOrder(prerequisite);
    prerequisiteColor.set(id, 2);
  }
  for (const id of techniqueMap.keys()) prerequisiteOrder(id);
  const sources = await json('data/sources.json');
  const sourceIds = new Set();
  require(Array.isArray(sources), 'data/sources.json: 配列が必要です。');
  for (const source of sources ?? []) {
    require(!sourceIds.has(source.id), `出典 ${source.id}: IDが重複しています。`);
    sourceIds.add(source.id);
    for (const key of ['name', 'language', 'method', 'enumerability', 'access', 'status', 'notes']) require(text(source[key]), `出典 ${source.id}: ${key}が必要です。`);
    for (const key of ['homepage', 'archive']) require(httpUrl(source[key]), `出典 ${source.id}: ${key}のURLが不正です。`);
    require(['automated', 'manual'].includes(source.method), `出典 ${source.id}: 収集方法を明記してください。`);
    require(source.method !== 'automated' || text(source.adapter), `出典 ${source.id}: 自動収集にはadapterが必要です。`);
  }
  const mappingKeys = new Set();
  for (const row of references) {
    const label = `使用例 ${row.techniqueId}/${row.problemId}`;
    require(techniqueMap.has(row.techniqueId), `${label}: 技巧が存在しません。`);
    require(Boolean(sourceIdFor(row.source, sources ?? [])), `${label}: 出典台帳に存在しません。`);
    for (const key of ['problemId', 'title', 'source', 'evidence', 'verification']) require(text(row[key]), `${label}: ${key}が必要です。`);
    require(httpUrl(row.url), `${label}: 原典URLが不正です。`);
    require(httpUrl(row.editorialUrl), `${label}: 確認根拠URLが必要です。`);
    require(verifiedKinds.has(row.verification), `${label}: タグ推測や未確認の対応を使用例として掲載できません。`);
    require(row.difficulty === null || text(row.difficulty), `${label}: 難易度は確認した値またはnullです。`);
    const key = `${row.techniqueId}:${row.url}`;
    require(!mappingKeys.has(key), `${label}: 同じ対応が重複しています。`);
    mappingKeys.add(key);
  }
  const docsDirectory = path.join(root, 'src/content/docs');
  const articleFiles = (await walk(docsDirectory)).filter(file => /\.(md|mdx)$/.test(file));
  const articleIds = new Set();
  const documentPaths = new Set(articleFiles.map(file => path.relative(docsDirectory, file).replace(/\.(md|mdx)$/, '').replace(/(^|\/)index$/, '').replace(/\/$/, '')));
  for (const file of articleFiles) {
    const relative = path.relative(docsDirectory, file);
    require(!/(^|\/)(problems?|tasks?)(\/|\.)/i.test(relative), `${relative}: 個別問題ページは掲載しません。`);
    const content = await readFile(file, 'utf8');
    require(!/[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(content), `${relative}: 不要な制御文字が含まれています。数式のバックスラッシュなどを確認してください。`);
    const frontmatter = content.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/)?.[1];
    require(Boolean(frontmatter), `${relative}: frontmatterが必要です。`);
    function frontmatterText(key) {
      const value = frontmatter?.match(new RegExp(`^${key}:\\s*(.*?)\\s*$`, 'm'))?.[1];
      if (value?.startsWith('"')) { try { return JSON.parse(value); } catch { return null; } }
      if (value?.startsWith("'") && value.endsWith("'")) return value.slice(1, -1).replaceAll("''", "'");
      return value;
    }
    const techniqueId = frontmatter?.match(/^techniqueId:\s*["']?([a-z0-9-]+)["']?\s*$/m)?.[1];
    if (relative.startsWith('techniques/')) {
      const id = path.basename(file).replace(/\.(md|mdx)$/, '');
      articleIds.add(id);
      require(techniqueMap.has(id), `${relative}: 技巧メタデータがありません。`);
      require(techniqueId === id, `${relative}: frontmatterのtechniqueIdは ${id} にしてください。`);
      require(/^title:\s*\S/m.test(frontmatter ?? '') && /^description:\s*\S/m.test(frontmatter ?? ''), `${relative}: titleとdescriptionが必要です。`);
      if (techniqueMap.has(id)) {
        require(frontmatterText('title') === techniqueMap.get(id).title, `${relative}: 記事タイトルとメタデータが一致しません。`);
        require(frontmatterText('description') === techniqueMap.get(id).summary, `${relative}: 記事概要とメタデータが一致しません。`);
      }
      const articleHeadings = [...content.matchAll(/^##\s+(.+?)\s*$/gm)].map(match => match[1]);
      for (const heading of headings) require(articleHeadings.filter(value => value === heading).length === 1, `${relative}: 見出し「${heading}」を一度記載してください。`);
      require(/```(?:cpp|python)\s*\n[\s\S]+?\n```/.test(content), `${relative}: 再利用可能な実装例が必要です。`);
      require(new RegExp(`<TechniqueReferences\\s+techniqueId=["']${id}["']\\s*/>`).test(content), `${relative}: 同じ技巧の使用例一覧が必要です。`);
      require(references.some(row => row.techniqueId === id), `${relative}: 根拠付き使用例が必要です。`);
      for (const source of techniqueMap.get(id)?.sources ?? []) require(content.includes(source), `${relative}: メタデータの根拠資料が本文にありません: ${source}`);
      const reviewed = techniqueMap.get(id)?.status === 'reviewed';
      // Lowercase C++ identifiers such as `todo` are ordinary queue names.
      if (reviewed) require(!/(\bTODO\b|\bTBD\b|近日公開|執筆中|未執筆)/.test(content), `${relative}: 未完成記事をreviewed扱いにできません。`);
    } else require(!techniqueId, `${relative}: 技巧記事はtechniques配下に配置してください。`);
    const withoutCode = content.replace(/```[\s\S]*?```/g, '');
    for (const match of withoutCode.matchAll(/(?:\]\(|(?:href|src)=["'])(\/[^\s"')>]+)/g)) {
      let target;
      try { target = decodeURI(match[1].split(/[?#]/)[0]); } catch { errors.push(`${relative}: 不正な内部URL ${match[1]}`); continue; }
      require(/^\/flowchartcp(?:\/|$)/.test(target), `${relative}: 内部URLを /flowchartcp/ 配下にしてください: ${match[1]}`);
      if (target.startsWith('/flowchartcp')) target = target.slice('/flowchartcp'.length);
      const route = target.replace(/^\/|\/$/g, '');
      if (documentPaths.has(route)) continue;
      try { await access(path.join(root, 'public', route)); }
      catch { errors.push(`${relative}: 内部参照が存在しません: ${match[1]}`); }
    }
  }
  for (const id of techniqueMap.keys()) require(articleIds.has(id), `${id}: 技巧記事が存在しません。`);

  const flowData = await json('data/flows.json');
  const graphs = Array.isArray(flowData) ? flowData : flowData?.graphs;
  require(Array.isArray(graphs) && graphs.length > 0, 'data/flows.json: 分岐図の配列が必要です。');
  const graphMap = new Map();
  const flowEdges = new Map();
  for (const graph of graphs ?? []) {
    require(!graphMap.has(graph.id), `フロー ${graph.id}: IDが重複しています。`);
    graphMap.set(graph.id, graph);
    require(slug.test(graph.id ?? '') && text(graph.title) && text(graph.description), `フロー ${graph.id}: id/title/descriptionが必要です。`);
    require(Array.isArray(graph.nodes) && graph.nodes.length > 0, `フロー ${graph.id}: nodesが必要です。`);
  }
  let nodeCount = 0;
  for (const graph of graphs ?? []) {
    const nodes = new Map();
    for (const node of graph.nodes ?? []) {
      const key = `${graph.id}/${node.id}`;
      ++nodeCount;
      require(!nodes.has(node.id), `${key}: ノードIDが重複しています。`);
      nodes.set(node.id, node);
      require(slug.test(node.id ?? ''), `${key}: 安定したノードIDを指定してください。`);
      require(text(node.title), `${key}: 質問または候補のタイトルが必要です。`);
      require(['question', 'result', 'route'].includes(node.type), `${key}: ノード型が不正です。`);
      flowEdges.set(key, []);
    }
    require(nodes.has(graph.root), `${graph.id}: rootが存在しません。`);
    if (graph.legacyEntryChoices !== undefined) {
      require(graph.legacyEntryChoices && typeof graph.legacyEntryChoices === 'object' && !Array.isArray(graph.legacyEntryChoices), `${graph.id}: 旧回答の対応はオブジェクトで指定してください。`);
      const rootNode = nodes.get(graph.root);
      for (const [oldAnswer, entry] of Object.entries(graph.legacyEntryChoices ?? {})) {
        const destination = graphMap.get(entry?.graph);
        const route = nodes.get(rootNode?.answers?.[entry?.answer]);
        const targetRoot = destination?.nodes?.find(node => node.id === destination.root);
        const currentOptions = rootNode?.options ?? [];
        const targetOptions = targetRoot?.options ?? [];
        // A later split may forward the same former choice once more. Every
        // forwarding entry is validated, and flowEdges rejects route cycles.
        const targetAcceptsAnswer = targetRoot?.type === 'question' && (targetOptions.some(option => option.id === oldAnswer) || Boolean(destination?.legacyEntryChoices && Object.hasOwn(destination.legacyEntryChoices, oldAnswer)));
        require(slug.test(oldAnswer) && rootNode?.type === 'question' && !currentOptions.some(option => option.id === oldAnswer) && route?.type === 'route' && route.graph === entry?.graph && targetAcceptsAnswer, `${graph.id}: 旧回答 ${oldAnswer} のカテゴリ・遷移先が一致しません。`);
      }
    }
    for (const node of graph.nodes ?? []) {
      const key = `${graph.id}/${node.id}`;
      if (node.continuation !== undefined) {
        const destination = graphMap.get(node.graph);
        require(typeof node.continuation === 'boolean' && node.type === 'route' && (!node.continuation || destination?.root === node.id), `${key}: 続きの図へのリンクは同じ質問IDを根に持つ図へ向けてください。`);
      }
      if (node.type === 'question') {
        const options = node.options ?? ['yes', 'no', 'unknown'].map(id => ({ id, label: id }));
        require(options.length >= 2 && options.some(option => option.id === 'unknown'), `${key}: 複数の選択肢と『わからない』が必要です。`);
        require(new Set(options.map(option => option.id)).size === options.length && options.every(option => text(option.id) && text(option.label)), `${key}: 選択肢のIDと表示名が不正です。`);
        require(node.answers && Object.keys(node.answers).sort().join(',') === options.map(option => option.id).sort().join(','), `${key}: 選択肢と分岐先が一致しません。`);
        for (const [label, target] of Object.entries(node.answers ?? {})) {
          require(nodes.has(target), `${key}: ${label}の到達先 ${target} が存在しません。`);
          flowEdges.get(key).push(`${graph.id}/${target}`);
        }
      }
      if (node.type === 'route') {
        const destination = graphMap.get(node.graph);
        require(Boolean(destination), `${key}: 遷移先の分野 ${node.graph} が存在しません。`);
        if (destination) flowEdges.get(key).push(`${destination.id}/${destination.root}`);
      }
      if (node.type === 'result') {
        require(Array.isArray(node.techniques) && node.techniques.length > 0, `${key}: 一つ以上の候補技巧が必要です。`);
        require(Array.isArray(node.conditions) && node.conditions.length > 0 && node.conditions.every(text), `${key}: 到達後の適用条件の確認事項が必要です。`);
      }
      for (const id of node.techniques ?? []) require(techniqueMap.has(id), `${key}: 候補技巧 ${id} が存在しません。`);
    }
    const reached = new Set();
    function visit(id) {
      if (reached.has(id) || !nodes.has(id)) return;
      reached.add(id);
      for (const target of Object.values(nodes.get(id).answers ?? {})) visit(target);
    }
    visit(graph.root);
    for (const id of nodes.keys()) require(reached.has(id), `${graph.id}/${id}: rootから到達できません。`);
  }
  const color = new Map();
  function acyclic(key) {
    if (color.get(key) === 1) { errors.push(`${key}: 分岐または分野間の遷移が循環しています。`); return; }
    if (color.get(key) === 2) return;
    color.set(key, 1);
    for (const target of flowEdges.get(key) ?? []) acyclic(target);
    color.set(key, 2);
  }
  for (const key of flowEdges.keys()) acyclic(key);

  const ledger = await json('data/research-ledger.json');
  let corpusRecords = [];
  try { corpusRecords = await readCorpusProgress(root, sources ?? []); }
  catch (error) { errors.push(`固定問題群の進捗: ${error.message}`); }
  require(ledger?.cutoff === '2026-10-14', '調査台帳: 初回基準日は2026-10-14です。');
  require(text(ledger?.coveragePolicy) && /未|完了していない/.test(ledger.coveragePolicy), '調査台帳: 全件調査が未完了であることを明記してください。');
  require(Array.isArray(ledger?.sources), '調査台帳: 出典別の進捗が必要です。');
  const ledgerIds = new Set();
  for (const row of ledger?.sources ?? []) {
    const label = `調査台帳 ${row.source}`;
    require(sourceIds.has(row.source) && !ledgerIds.has(row.source), `${label}: 出典が不明または重複しています。`);
    ledgerIds.add(row.source);
    for (const key of ['discovered', 'fetched', 'metadataCollected', 'bootstrapProblems', 'solutionReviewed', 'techniquesExtracted']) require(Number.isSafeInteger(row[key]) && row[key] >= 0, `${label}: ${key}は0以上の整数です。`);
    require(row.totalKnown === null || (Number.isSafeInteger(row.totalKnown) && row.totalKnown > 0), `${label}: 未列挙の総数は0ではなくnullです。`);
    require(row.fetched <= row.discovered && row.solutionReviewed <= row.fetched && row.metadataCollected <= row.fetched, `${label}: 取得・確認数が上位の件数を超えています。`);
    require(text(row.status) && text(row.scope) && text(row.notes), `${label}: 状況・対象範囲・注記が必要です。`);
    const source = (sources ?? []).find(value => value.id === row.source);
    const sourceRows = references.filter(ref => source && sourceIdFor(ref.source, sources) === source.id);
    const problems = new Set(sourceRows.map(ref => ref.problemId));
    const reviewed = new Set(sourceRows.filter(ref => ref.verification !== 'official-tag').map(ref => ref.problemId));
    require(row.bootstrapProblems === problems.size && row.solutionReviewed === reviewed.size && row.techniquesExtracted === sourceRows.length, `${label}: 掲載使用例と確認件数が一致しません。node scripts/lib/ledger.mjsで更新してください。`);
    if ('corpusStatementsReviewed' in row || corpusRecords.length) {
      const statements = new Set(corpusRecords.filter(value => value.source === row.source && value.statementVerified).map(value => value.problemId));
      const solutions = new Set(corpusRecords.filter(value => value.source === row.source && value.solutionVerified).map(value => value.problemId));
      for (const name of ['corpusStatementsReviewed', 'corpusSolutionsReviewed', 'allSolutionsReviewed', 'allProblemsObserved'])
        require(Number.isSafeInteger(row[name]) && row[name] >= 0, `${label}: ${name}は0以上の整数です。`);
      require(row.corpusStatementsReviewed === statements.size && row.corpusSolutionsReviewed === solutions.size
        && row.allSolutionsReviewed === new Set([...reviewed, ...solutions]).size, `${label}: 固定問題群の原典・解法確認数が一致しません。`);
      require(row.allProblemsObserved >= Math.max(row.fetched, statements.size, row.allSolutionsReviewed), `${label}: 和集合の観測数が確認数より少なくなっています。`);
    }
  }
  for (const id of sourceIds) require(ledgerIds.has(id), `調査台帳: 出典 ${id} の行がありません。`);
  require(ledger?.verifiedMappings === references.length, '調査台帳: verifiedMappingsと掲載対応件数が一致しません。');
  try {
    require(ledger?.reviewedProblems === new Set(references.filter(row => row.verification !== 'official-tag').map(row => canonicalProblemKey(row, sources ?? []))).size, '調査台帳: 解法確認済み問題数が一致しません。');
    require(ledger?.formatVerifiedProblems === new Set(references.filter(row => row.verification === 'official-tag').map(row => canonicalProblemKey(row, sources ?? []))).size, '調査台帳: 形式確認と解法確認を区別してください。');
  } catch (error) { errors.push(`調査台帳の出典照合: ${error.message}`); }
  if (ledger?.corpusStatementsReviewed !== undefined || corpusRecords.length) {
    require(ledger?.corpusStatementsReviewed === corpusRecords.filter(row => row.statementVerified).length
      && ledger?.corpusSolutionsReviewed === corpusRecords.filter(row => row.solutionVerified).length, '調査台帳: 固定問題群の重複を除いた確認数が一致しません。');
    try {
      const allReviewed = new Set(references.filter(row => row.verification !== 'official-tag').map(row => canonicalProblemKey(row, sources ?? [])));
      for (const row of corpusRecords.filter(row => row.solutionVerified)) allReviewed.add(row.key);
      require(ledger?.allSolutionsReviewed === allReviewed.size, '調査台帳: 掲載使用例と固定問題群の解法確認の和集合が一致しません。');
    } catch (error) { errors.push(`調査台帳の出典照合: ${error.message}`); }
  }
  const vendor = await json('vendor/ac-library/manifest.json');
  require(vendor?.repository === 'https://github.com/atcoder/ac-library' && /^[a-f0-9]{40}$/.test(vendor?.revision ?? '') && vendor?.license === 'CC0-1.0', 'ACL依存: 公式上流・固定リビジョン・ライセンスを記録してください。');
  for (const row of vendor?.files ?? []) {
    const safe = /^(?:LICENSE|atcoder\/[a-z_]+(?:\.hpp)?)$/.test(row.path ?? '');
    require(safe, `ACL依存: 不正なファイルパス ${row.path}`);
    if (!safe) continue;
    try {
      const bytes = await readFile(path.join(root, 'vendor/ac-library', row.path));
      const digest = createHash('sha1').update(`blob ${bytes.length}\0`).update(bytes).digest('hex');
      require(digest === row.blobSha, `ACL依存 ${row.path}: 保存したファイルが上流のGit blob hashと一致しません。`);
    } catch (error) { errors.push(`ACL依存 ${row.path}: ${error.message}`); }
  }
  let workflowFiles = [];
  try { workflowFiles = (await walk(path.join(root, '.github/workflows'))).filter(file => /\.ya?ml$/.test(file)); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  for (const file of workflowFiles) {
    const workflow = await readFile(file, 'utf8');
    require(!/actions\/deploy-pages|peaceiris\/actions-gh-pages|pages:\s*write|github-pages|gh\s+repo\s+edit[^\n]*--visibility\s+public/i.test(workflow), `${path.relative(root, file)}: 今回は公開・デプロイを行いません。`);
  }
  return { errors, counts: { techniques: techniques.length, references: references.length, graphs: graphs?.length ?? 0, nodes: nodeCount, sources: sources?.length ?? 0 } };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const result = await validateSite();
    if (result.errors.length) {
      console.error(result.errors.map(error => `- ${error}`).join('\n'));
      console.error(`Validation failed: ${result.errors.length} issue(s).`);
      process.exitCode = 1;
    } else console.log(`Validated ${result.counts.techniques} techniques, ${result.counts.references} mappings, ${result.counts.graphs} diagrams / ${result.counts.nodes} nodes, ${result.counts.sources} source ledgers. No files changed.`);
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
