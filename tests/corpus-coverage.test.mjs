import test from 'node:test';
import assert from 'node:assert/strict';
import { assessCorpus, auditCoverage } from '../scripts/audit-coverage.mjs';

const record = { source: 'USACO', problemId: 'x', title: 'Fixed problem', reviewStatus: 'verified',
  materialStatus: { statement: 'retrieved-and-reviewed' }, technicalFindings: { verification: 'official-editorial' },
  classification: 'missing-technique', gap: { id: 'gap' } };
const corpus = records => ({ corpusId: 'fixed', cutoff: '2026-10-14', records,
  selection: { fixedBeforeTechniqueSearch: true }, status: { fixedCorpusResearchComplete: true, recordCount: records.length } });
const selection = { id: 'fixed', cutoff: '2026-10-14', expectedProblems: 1,
  fixedProblems: [{ source: 'usaco', problemId: 'x' }] };
const data = { techniques: [{ id: 'specific', status: 'reviewed' }], preflightPassed: true,
  references: [{ source: 'usaco', problemId: 'x', techniqueId: 'specific', verification: 'editorial', url: 'https://example.test/x' }],
  walks: [{ source: 'USACO', problemId: 'x', reviewStatus: 'verified', verificationKind: 'editorial',
    statementUrl: 'https://example.test/x', expectedTechniqueIds: ['specific'] }],
  isWalkValid: () => true };
const resolved = { ...record, resolution: { status: 'verified', techniqueIds: ['specific'] } };
const assess = (audit, context = data, fixed = selection) => assessCorpus(audit, context, fixed);

test('researching every problem does not imply coverage', () => {
  const result = assess(corpus([record]));
  assert.equal(result.researchComplete, true);
  assert.equal(result.coverageComplete, false);
  assert.equal(result.coveredProblems, 0);
  assert.equal(result.records[0].resolved, false);
});
test('later explicit proofs complete current research without rewriting the first-pass history', () => {
  const statementUrl = 'https://example.test/x';
  const initial = { ...record, statementUrl, reviewStatus: 'unconfirmed',
    technicalFindings: { verification: 'public-editorial-sketch-with-unconfirmed-proof' } };
  const proof = { statementUrl, reviewedAt: '2026-10-15', reviewStatus: 'verified',
    verification: 'independent-analysis', collectionStatus: 'statement-and-independent-analysis-verified',
    materialStatus: { solution: 'retrieved-and-reviewed' }, evidenceUrls: [statementUrl],
    notes: 'An independent proof establishes the previously missing lemma.' };
  const audit = corpus([initial]);
  audit.status = { firstPassAuditComplete: true, fixedCorpusResearchComplete: false, recordCount: 1 };
  const historical = structuredClone(audit);
  assert.equal(assess(audit).researchComplete, false);
  audit.records[0] = { ...initial, subsequentSolutionReviews: [proof] };
  const researched = assess(audit);
  assert.equal(researched.researchComplete, true);
  assert.equal(researched.coverageComplete, false, 'a proof alone does not publish an article or valid flow');
  audit.records[0].resolution = resolved.resolution;
  assert.equal(assess(audit).coverageComplete, true);
  assert.deepEqual(audit.status, historical.status);
  assert.equal(audit.records[0].reviewStatus, 'unconfirmed');
  for (const change of [{ notes: '' }, { evidenceUrls: [] }, { reviewedAt: undefined },
    { materialStatus: { solution: 'unconfirmed' } }]) {
    const invalid = structuredClone(audit);
    invalid.records[0].subsequentSolutionReviews = [{ ...proof, ...change }];
    assert.equal(assess(invalid).researchComplete, false);
    assert.equal(assess(invalid).coverageComplete, false);
  }
  const unfinished = structuredClone(audit);
  unfinished.status.firstPassAuditComplete = false;
  assert.equal(assess(unfinished).researchComplete, false, 'the complete fixed first pass is still required');
  unfinished.status.fixedCorpusResearchComplete = true;
  assert.equal(assess(unfinished).researchComplete, false, 'a stale research flag cannot override an explicit incomplete first pass');
});
test('resolution requires a validated article and a matching confirmed reference and valid root walk', () => {
  assert.equal(assess(corpus([resolved])).coverageComplete, true);
  for (const key of ['techniques', 'references', 'walks'])
    assert.equal(assess(corpus([resolved]), { ...data, [key]: [] }).coverageComplete, false);
  for (const verification of ['official-tag', 'unconfirmed', undefined])
    assert.equal(assess(corpus([resolved]), { ...data, references: [{ ...data.references[0], verification }] }).coverageComplete, false);
  for (const change of [{ problemId: 'other' }, { source: 'other' }, { statementUrl: 'https://example.test/y' },
    { verificationKind: 'independent-analysis' }, { reviewStatus: 'pending' }])
    assert.equal(assess(corpus([resolved]), { ...data, walks: [{ ...data.walks[0], ...change }] }).coverageComplete, false);
  assert.equal(assess(corpus([resolved]), { ...data, preflightPassed: false }).coverageComplete, false);
  assert.equal(assess(corpus([resolved]), { ...data, isWalkValid: () => false }).coverageComplete, false);
  assert.equal(assess(corpus([{ ...resolved, reviewStatus: 'pending' }])).coverageComplete, false);
  assert.equal(assess(corpus([{ ...resolved, resolution: { status: 'verified', techniqueIds: [] } }])).coverageComplete, false);
});
test('unknown count, missing fixed identities, replacement problem, size or cutoff mismatch prevents completion', () => {
  for (const fixed of [{ ...selection, expectedProblems: null }, { ...selection, expectedProblems: 2 },
    { ...selection, fixedProblems: [] }, { ...selection, fixedProblems: [{ source: 'usaco', problemId: 'other' }] },
    { ...selection, cutoff: '2026-10-13' }, { ...selection, id: 'other' }]) {
    const result = assess(corpus([resolved]), data, fixed);
    assert.equal(result.researchComplete, false);
    assert.equal(result.coverageComplete, false);
    assert.equal(result.coveredProblems, 0);
    assert(result.errors.length);
  }
});
test('source spelling differences cannot make a duplicate problem look like two problems', () => {
  const result = assess(corpus([resolved, { ...resolved, source: 'usaco' }]), data,
    { ...selection, expectedProblems: 2, fixedProblems: [selection.fixedProblems[0], { source: 'USACO', problemId: 'y' }] });
  assert(result.errors.includes('duplicate canonical problem identities'));
  assert.equal(result.coverageComplete, false);
});
test('one unresolved problem prevents a fixed corpus from being covered', () => {
  const result = assess(corpus([resolved, { ...record, problemId: 'y' }]), data,
    { ...selection, expectedProblems: 2, fixedProblems: [selection.fixedProblems[0], { source: 'usaco', problemId: 'y' }] });
  assert.equal(result.coveredProblems, 1);
  assert.equal(result.coverageComplete, false);
});
test('stale verified labels cannot promote tag-only or proof-unconfirmed research', () => {
  for (const change of [{ verification: 'official-tag' }, { collectionStatus: 'statement-only' },
    { technicalFindings: { verification: 'official-editorial-partial-main-lemma-unconfirmed' } },
    { materialStatus: { statement: 'unavailable' }, collectionStatus: 'statement-and-official-editorial-verified' },
    { materialStatus: { statement: 'retrieved-and-reviewed', officialEditorialVerified: false } }]) {
    const result = assess(corpus([{ ...resolved, ...change }]));
    assert.equal(result.reviewedProblems, 0);
    assert.equal(result.coveredProblems, 0);
    assert.equal(result.researchComplete, false);
    assert.equal(result.coverageComplete, false);
  }
});
test('actual articles, references, root walks, fixed identities and known gaps are internally consistent', async () => {
  const result = await auditCoverage();
  assert.deepEqual(result.errors, []);
  assert.equal(result.globalCoverageComplete, false);
  assert.equal(result.globalProblemCount, null);
  const usaco = result.corpora.find(row => row.corpusId === 'usaco-2020-dec-2021-jan-platinum');
  assert.equal(usaco.totalProblems, 6);
  assert.equal(usaco.researchComplete, true);
  assert(usaco.coveredProblems >= 2);
});
