import { readFile, readdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { atomicWrite } from './collection.mjs';
import { readCorpusProgress, canonicalProblemKey, sourceIdFor } from './corpus-progress.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
async function json(file, fallback) {
  try { return JSON.parse(await readFile(file, 'utf8')); }
  catch (error) { if (error.code === 'ENOENT') return fallback; throw error; }
}

/** Explicitly publish acquisition counts without promoting metadata/tags to reviewed solutions. */
export async function syncLedger({ root = site, rawDirectory = path.join(root, 'research/raw') } = {}) {
  const sources = await json(path.join(root, 'data/sources.json'), []);
  const existing = await json(path.join(root, 'data/research-ledger.json'), { cutoff: '2026-10-14' });
  const files = (await readdir(path.join(root, 'data'))).filter(name => /^references-.*\.json$/.test(name));
  const references = (await Promise.all(files.map(name => json(path.join(root, 'data', name), [])))).flat().filter(row => ['editorial', 'reference-solution', 'official-tag', 'independent-analysis'].includes(row.verification));
  const corpusRecords = await readCorpusProgress(root, sources);
  const rows = [];
  for (const source of sources) {
    const sourceReferences = references.filter(row => sourceIdFor(row.source, sources) === source.id);
    const bootstrap = new Set(sourceReferences.map(row => `${source.id}:${row.problemId}`));
    const reviewed = new Set(sourceReferences.filter(row => row.verification !== 'official-tag').map(row => row.problemId));
    const corpusStatements = new Set(corpusRecords.filter(row => row.source === source.id && row.statementVerified).map(row => row.problemId));
    const corpusSolutions = new Set(corpusRecords.filter(row => row.source === source.id && row.solutionVerified).map(row => row.problemId));
    const checkpoint = await json(path.join(rawDirectory, `${source.id}.checkpoint.json`), null);
    const acquired = new Set();
    try {
      const content = await readFile(path.join(rawDirectory, `${source.id}.jsonl`), 'utf8');
      for (const line of content.split('\n').filter(Boolean)) acquired.add(JSON.parse(line).id);
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
    const union = new Set([...bootstrap, ...acquired]);
    const status = checkpoint?.status === 'complete' ? 'metadata-complete' : checkpoint?.status ?? (bootstrap.size ? 'bootstrap-reviewed' : corpusStatements.size ? 'corpus-partial' : source.method === 'manual' ? 'manual-pending' : 'not-started');
    rows.push({ source: source.id, status, totalKnown: null, discovered: Math.max(checkpoint?.discovered ?? 0, union.size), fetched: union.size, metadataCollected: acquired.size, bootstrapProblems: bootstrap.size, solutionReviewed: reviewed.size,
      corpusStatementsReviewed: corpusStatements.size, corpusSolutionsReviewed: corpusSolutions.size,
      allSolutionsReviewed: new Set([...reviewed, ...corpusSolutions]).size,
      allProblemsObserved: new Set([...union, ...[...corpusStatements].map(id => `${source.id}:${id}`)]).size,
      techniquesExtracted: sourceReferences.length, acquisitionCutoff: checkpoint?.until ?? null, scope: checkpoint?.scope ?? source.notes, notes: source.notes, ...(checkpoint?.error ? { error: checkpoint.error } : {}) });
  }
  const allReviewed = new Set(references.filter(row => row.verification !== 'official-tag').map(row => canonicalProblemKey(row, sources)));
  for (const row of corpusRecords.filter(row => row.solutionVerified)) allReviewed.add(row.key);
  const ledger = { ...existing, updatedAt: new Date().toISOString(), sources: rows, verifiedMappings: references.length, reviewedProblems: new Set(references.filter(row => row.verification !== 'official-tag').map(row => canonicalProblemKey(row, sources))).size, formatVerifiedProblems: new Set(references.filter(row => row.verification === 'official-tag').map(row => canonicalProblemKey(row, sources))).size,
    corpusStatementsReviewed: corpusRecords.filter(row => row.statementVerified).length,
    corpusSolutionsReviewed: corpusRecords.filter(row => row.solutionVerified).length,
    allSolutionsReviewed: allReviewed.size,
    progressDefinitions: { solutionReviewed: '掲載使用例から解法を確認した問題数。形式のみの確認は除く。', corpusStatementsReviewed: '先に固定した問題群で原典を確認した問題数。複数群の同じ問題は一件。', corpusSolutionsReviewed: '固定問題群で解法を確認した問題数。記事・分岐が未完成の問題も含む。', allSolutionsReviewed: '掲載使用例と固定問題群で解法確認した問題の和集合。両者の件数を単純に加えない。', techniquesExtracted: '掲載した問題と技巧の対応数。固定群の解法を読んだだけでは増やさない。' } };
  await atomicWrite(path.join(root, 'data/research-ledger.json'), `${JSON.stringify(ledger, null, 2)}\n`);
  return ledger;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const ledger = await syncLedger();
  console.log(`Ledger updated: ${ledger.verifiedMappings} mappings; ${ledger.reviewedProblems} reviewed problems in examples; ${ledger.corpusSolutionsReviewed} fixed-corpus reviews; ${ledger.allSolutionsReviewed} distinct reviewed problems in their union. Metadata acquisition remains separate.`);
}
