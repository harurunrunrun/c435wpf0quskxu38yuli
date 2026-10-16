import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { syncLedger } from '../scripts/lib/ledger.mjs';
import { readCorpusProgress, isCorpusSolutionReviewed } from '../scripts/lib/corpus-progress.mjs';

test('fixed-corpus research is counted separately and deduplicated with published examples', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'flowchartcp-corpus-ledger-'));
  try {
    await mkdir(path.join(root, 'data/corpus-audits'), { recursive: true });
    await mkdir(path.join(root, 'research/raw'), { recursive: true });
    const save = (name, value) => writeFile(path.join(root, name), JSON.stringify(value));
    const sources = [{ id: 'usaco', name: 'USACO', method: 'manual', notes: 'fixed selection' },
      { id: 'icpc', name: 'ICPC', method: 'manual', notes: 'fixed selection' }];
    await save('data/sources.json', sources);
    await save('data/references-test.json', [
      { source: 'USACO', problemId: 'a', techniqueId: 'one', verification: 'editorial' },
      { source: 'USACO', problemId: 'b', techniqueId: 'format', verification: 'official-tag' },
    ]);
    const statement = { materialStatus: { statement: 'retrieved-and-reviewed' }, technicalFindings: { verification: 'official-editorial' } };
    const records = [
      { source: 'USACO', problemId: 'a', reviewStatus: 'verified', ...statement },
      { source: 'usaco', problemId: 'c', reviewStatus: 'verified', ...statement },
      { source: 'ICPC', problemId: 'k', reviewStatus: 'unconfirmed', ...statement,
        technicalFindings: { verification: 'public-editorial-sketch-with-unconfirmed-proof' } },
    ];
    const extra = [{ ...records[1], source: 'USACO' }, { source: 'USACO', problemId: 'd', reviewStatus: 'pending' }];
    const plan = { cutoff: '2026-10-14', corpora: [records, extra].map((rows, i) => ({
      id: `fixed-${i}`, auditFile: `data/corpus-audits/fixed-${i}.json`, expectedProblems: rows.length,
      fixedProblems: rows.map(({ source, problemId }) => ({ source, problemId })),
    })) };
    await save('data/coverage-plan.json', plan);
    for (const [i, rows] of [records, extra].entries())
      await save(`data/corpus-audits/fixed-${i}.json`, { corpusId: `fixed-${i}`, cutoff: plan.cutoff, records: rows });
    await writeFile(path.join(root, 'research/raw/usaco.jsonl'), '{"id":"usaco:d"}\n');
    const ledger = await syncLedger({ root });
    const usaco = ledger.sources.find(row => row.source === 'usaco');
    assert.equal(usaco.bootstrapProblems, 2);
    assert.equal(usaco.metadataCollected, 1);
    assert.equal(usaco.solutionReviewed, 1);
    assert.equal(usaco.corpusStatementsReviewed, 2);
    assert.equal(usaco.corpusSolutionsReviewed, 2);
    assert.equal(usaco.allSolutionsReviewed, 2, 'published a overlaps the fixed corpus');
    assert.equal(usaco.allProblemsObserved, 4);
    assert.equal(usaco.techniquesExtracted, 2, 'research alone cannot publish a mapping');
    const icpc = ledger.sources.find(row => row.source === 'icpc');
    assert.equal(icpc.corpusStatementsReviewed, 1);
    assert.equal(icpc.corpusSolutionsReviewed, 0, 'unconfirmed proof is not a verified solution');
    assert.equal(icpc.allSolutionsReviewed, 0);
    assert.equal(icpc.status, 'corpus-partial');
    assert.equal(ledger.corpusStatementsReviewed, 3);
    assert.equal(ledger.corpusSolutionsReviewed, 2);
    assert.equal(ledger.allSolutionsReviewed, 2);
    assert.equal(ledger.verifiedMappings, 2);
    assert.equal(ledger.formatVerifiedProblems, 1);
    assert.equal(ledger.reviewedProblems, 1);

    await save('data/references-test.json', [
      { source: 'USACO', problemId: 'a', techniqueId: 'one', verification: 'editorial' },
      { source: 'USACO', problemId: 'b', techniqueId: 'format', verification: 'official-tag' },
      { source: 'USACO', problemId: 'c', techniqueId: 'new-article', verification: 'editorial' },
    ]);
    const published = await syncLedger({ root });
    assert.equal(published.reviewedProblems, 2);
    assert.equal(published.verifiedMappings, 3);
    assert.equal(published.corpusSolutionsReviewed, 2);
    assert.equal(published.allSolutionsReviewed, 2, 'publishing an already reviewed gap does not count its solution twice');

    await save('data/references-test.json', [
      { source: 'USACO', problemId: 'a', techniqueId: 'one', verification: 'editorial' },
      { source: 'usaco', problemId: 'a', techniqueId: 'another', verification: 'reference-solution' },
      { source: 'USACO', problemId: 'b', techniqueId: 'format', verification: 'official-tag' },
      { source: 'usaco', problemId: 'b', techniqueId: 'another-format', verification: 'official-tag' },
    ]);
    const aliases = await syncLedger({ root });
    assert.equal(aliases.reviewedProblems, 1, 'source aliases cannot duplicate a reviewed problem');
    assert.equal(aliases.formatVerifiedProblems, 1, 'source aliases cannot duplicate a format-only problem');
    assert.equal(aliases.sources.find(row => row.source === 'usaco').solutionReviewed, aliases.reviewedProblems);
    assert.equal(aliases.allSolutionsReviewed, 2);

    for (const contradiction of [
      { verification: 'official-tag' },
      { collectionStatus: 'statement-only' },
      { technicalFindings: { verification: 'official-tag' } },
      { collectionStatus: 'statement-and-public-sketch-retrieved-proof-unconfirmed' },
      { technicalFindings: { verification: 'public-editorial-sketch-with-unconfirmed-proof' } },
      { technicalFindings: undefined },
      { materialStatus: { statement: 'retrieved-and-reviewed', solution: 'unconfirmed' } },
    ]) {
      const contradicted = { ...records[0], ...contradiction };
      await save('data/corpus-audits/fixed-0.json', { corpusId: 'fixed-0', cutoff: plan.cutoff,
        records: [contradicted, ...records.slice(1)] });
      const progress = await readCorpusProgress(root, sources);
      assert.equal(progress.find(row => row.problemId === 'a').statementVerified, true);
      assert.equal(progress.find(row => row.problemId === 'a').solutionVerified, false,
        `stale verified status cannot override ${JSON.stringify(contradiction)}`);
    }

    const badAudit = { corpusId: 'fixed-0', cutoff: plan.cutoff, records: [records[0], records[0], records[2]] };
    await save('data/corpus-audits/fixed-0.json', badAudit);
    await assert.rejects(readCorpusProgress(root, sources), /replaced or duplicated/);
    await save('data/corpus-audits/fixed-0.json', { ...badAudit, records: [...records.slice(0, 2), { ...records[2], problemId: 'wrong' }] });
    await assert.rejects(readCorpusProgress(root, sources), /replaced or duplicated/);
    await save('data/corpus-audits/fixed-0.json', { ...badAudit, cutoff: '2026-10-13', records });
    await assert.rejects(readCorpusProgress(root, sources), /identity\/cutoff/);
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('Japanese source names remain distinct when canonicalizing published examples', async () => {
  const root = await mkdtemp(path.join(tmpdir(), 'flowchartcp-source-alias-'));
  try {
    await mkdir(path.join(root, 'data'), { recursive: true });
    await mkdir(path.join(root, 'research/raw'), { recursive: true });
    await writeFile(path.join(root, 'data/sources.json'), JSON.stringify([
      { id: 'joi', name: '日本情報オリンピック', method: 'manual', notes: 'one source' },
      { id: 'regional', name: '国内予選', method: 'manual', notes: 'another source' },
    ]));
    await writeFile(path.join(root, 'data/references-test.json'), JSON.stringify([
      { source: '日本情報オリンピック', problemId: 'a', techniqueId: 'one', verification: 'editorial' },
      { source: '国内予選', problemId: 'a', techniqueId: 'two', verification: 'editorial' },
    ]));
    const ledger = await syncLedger({ root });
    assert.equal(ledger.reviewedProblems, 2);
    assert.equal(ledger.allSolutionsReviewed, 2);
    for (const source of ledger.sources) {
      assert.equal(source.bootstrapProblems, 1);
      assert.equal(source.solutionReviewed, 1);
      assert.equal(source.techniquesExtracted, 1);
    }
  } finally { await rm(root, { recursive: true, force: true }); }
});

test('a subsequent explicit independent proof can resolve an initially unconfirmed solution', () => {
  const statementUrl = 'https://example.test/original';
  const original = { source: 'JOI', problemId: 'x', statementUrl, reviewStatus: 'unconfirmed',
    materialStatus: { statement: 'retrieved-and-reviewed', officialEditorialVerified: false },
    technicalFindings: { verification: 'official-editorial-partial-main-lemma-unconfirmed' } };
  const proof = { statementUrl, reviewedAt: '2026-10-15', reviewStatus: 'verified', verification: 'independent-analysis',
    collectionStatus: 'statement-and-independent-analysis-verified', evidenceUrls: [statementUrl], notes: 'The missing interval lemma was proved independently.' };
  assert.equal(isCorpusSolutionReviewed(original), false);
  assert.equal(isCorpusSolutionReviewed({ ...original, subsequentSolutionReviews: [proof] }), true);
  for (const change of [{ statementUrl: 'https://example.test/different' }, { reviewedAt: undefined },
    { reviewStatus: 'unconfirmed' }, { verification: 'official-tag' }, { notes: '' }, { evidenceUrls: [] },
    { materialStatus: { solution: 'unconfirmed' } },
    { verification: 'official-editorial', materialStatus: { solution: 'retrieved-and-reviewed', officialEditorialVerified: false } }])
    assert.equal(isCorpusSolutionReviewed({ ...original, subsequentSolutionReviews: [{ ...proof, ...change }] }), false);
  assert.equal(original.reviewStatus, 'unconfirmed', 'later evidence never mutates the historical review');
});
