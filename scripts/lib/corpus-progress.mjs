import { readFile } from 'node:fs/promises';
import path from 'node:path';

const folded = value => String(value).trim().toLowerCase();
const normalized = value => folded(value).replace(/[^a-z0-9]/g, '');
export function sourceIdFor(name, sources) {
  const exact = sources.find(source => [source.id, source.name].some(value => folded(value) === folded(name)));
  if (exact) return exact.id;
  const key = normalized(name);
  return key ? sources.find(source => [source.id, source.name].some(value => normalized(value) === key))?.id : undefined;
}
export function canonicalProblemKey(record, sources) {
  if (typeof record.problemId !== 'string' || !record.problemId.trim()) throw new Error('Missing corpus problem identity');
  const id = sourceIdFor(record.source, sources);
  if (!id) throw new Error(`Unknown corpus source: ${record.source}`);
  return `${id}:${record.problemId}`;
}

const confirmedSolutionKinds = new Set([
  'editorial', 'official-editorial', 'public-editorial-sketch',
  'reference-solution', 'independent-analysis',
]);
const reviewedCollections = new Set([
  'statement-and-official-editorial-verified',
  'statement-and-official-editorial-reviewed',
  'statement-and-public-sketch-reviewed',
  'statement-and-reference-solution-verified',
  'statement-and-independent-analysis-verified',
]);
export function isCorpusStatementReviewed(row) {
  const status = row.materialStatus?.statement;
  if (status !== undefined) return ['retrieved-and-reviewed',
    'official-english-retrieved-and-reviewed-japanese-unavailable'].includes(status);
  return row.collectionStatus === 'statement-and-official-editorial-verified';
}
function isDirectSolutionReviewed(row) {
  const kinds = [row.verification, row.technicalFindings?.verification].filter(value => value !== undefined);
  return isCorpusStatementReviewed(row) && row.reviewStatus === 'verified'
    && kinds.length > 0 && kinds.every(kind => confirmedSolutionKinds.has(kind))
    && (row.collectionStatus === undefined || reviewedCollections.has(row.collectionStatus))
    && (row.materialStatus?.solution === undefined || row.materialStatus.solution === 'retrieved-and-reviewed')
    && (!kinds.includes('official-editorial') || row.materialStatus?.officialEditorialVerified !== false);
}
export function isCorpusSolutionReviewed(row) {
  if (isDirectSolutionReviewed(row)) return true;
  if (!isCorpusStatementReviewed(row) || !Array.isArray(row.subsequentSolutionReviews)) return false;
  // Preserve the initial unconfirmed record. A later explicit review can
  // establish the missing proof without rewriting what was known at first.
  return row.subsequentSolutionReviews.some(review => review.statementUrl === row.statementUrl
    && /^\d{4}-\d{2}-\d{2}$/.test(review.reviewedAt ?? '')
    && typeof review.notes === 'string' && review.notes.trim().length > 0
    && Array.isArray(review.evidenceUrls) && review.evidenceUrls.includes(row.statementUrl)
    && review.evidenceUrls.every(url => typeof url === 'string' && /^https?:\/\//.test(url))
    && isDirectSolutionReviewed({ ...review,
      materialStatus: { ...review.materialStatus, statement: 'retrieved-and-reviewed' } }));
}

// Reading a statement, verifying a solution and publishing a technique mapping
// are separate stages. A researched but not yet implemented gap is not discarded.
export async function readCorpusProgress(root, sources) {
  let plan;
  try { plan = JSON.parse(await readFile(path.join(root, 'data/coverage-plan.json'), 'utf8')); }
  catch (error) { if (error.code === 'ENOENT') return []; throw error; }
  const records = new Map();
  for (const selection of plan.corpora) {
    if (!/^data\/corpus-audits\/[a-z0-9-]+\.json$/.test(selection.auditFile)) throw new Error('Unsafe corpus audit path');
    let audit;
    try { audit = JSON.parse(await readFile(path.join(root, selection.auditFile), 'utf8')); }
    catch (error) { if (error.code === 'ENOENT') continue; throw error; }
    if (audit.corpusId !== selection.id || audit.cutoff !== plan.cutoff) throw new Error(`${selection.id}: corpus identity/cutoff mismatch`);
    const fixed = new Set((selection.fixedProblems ?? []).map(row => canonicalProblemKey(row, sources)));
    if (!selection.expectedProblems || selection.fixedProblems?.length !== selection.expectedProblems
      || fixed.size !== selection.expectedProblems || audit.records.length !== selection.expectedProblems)
      throw new Error(`${selection.id}: fixed corpus is not fully enumerated`);
    const seen = new Set();
    for (const row of audit.records) {
      const key = canonicalProblemKey(row, sources);
      if (!fixed.has(key) || seen.has(key)) throw new Error(`${selection.id}: corpus problem replaced or duplicated`);
      seen.add(key);
      const statementVerified = isCorpusStatementReviewed(row);
      const solutionVerified = isCorpusSolutionReviewed(row);
      const previous = records.get(key);
      records.set(key, { key, source: sourceIdFor(row.source, sources), problemId: row.problemId,
        statementVerified: Boolean(statementVerified || previous?.statementVerified),
        solutionVerified: Boolean(solutionVerified || previous?.solutionVerified) });
    }
  }
  return [...records.values()];
}
