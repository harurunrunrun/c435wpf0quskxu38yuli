#!/usr/bin/env node
import { readFile, readdir, writeFile, mkdtemp, rm } from 'node:fs/promises';
import path from 'node:path';
import { tmpdir } from 'node:os';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { validateSite } from './validate.mjs';
import { compileLocalModules } from './local-modules.mjs';
import { isCorpusSolutionReviewed } from './lib/corpus-progress.mjs';

const site = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const json = async file => JSON.parse(await readFile(file, 'utf8'));
const normalize = value => String(value).toLowerCase().replace(/[^a-z0-9]/g, '');
const key = row => `${normalize(row.source)}:${row.problemId}`;
const confirmed = new Set(['editorial', 'reference-solution', 'independent-analysis']);
const safeFile = file => /^data\/corpus-audits\/[a-z0-9-]+\.json$/.test(file);
const sameSet = (a, b) => a.size === b.size && [...a].every(item => b.has(item));

function coveredTechnique(id, data, problem) {
  if (!data.preflightPassed || !data.techniques.some(row => row.id === id && row.status === 'reviewed')) return false;
  return data.references.some(ref => ref.techniqueId === id && confirmed.has(ref.verification)
    && (!problem || key(ref) === key(problem))
    && data.walks.some(walk => key(walk) === key(ref) && walk.statementUrl === ref.url
      && walk.verificationKind === ref.verification && walk.reviewStatus === 'verified'
      && walk.expectedTechniqueIds.includes(id) && data.isWalkValid(walk, id)));
}

// A fixed denominator and fixed identities are both required. Article counts,
// successful research, metadata acquisition and tags cannot establish coverage.
export function assessCorpus(audit, data, selection) {
  const errors = [];
  const expected = selection?.expectedProblems;
  if (!Number.isSafeInteger(expected) || expected < 1) errors.push('fixed problem count is unknown');
  if (audit.corpusId !== selection?.id || audit.cutoff !== selection?.cutoff) errors.push('corpus identity/cutoff mismatch');
  if (audit.records.length !== expected) errors.push('fixed corpus size mismatch');
  const actualKeys = audit.records.map(key);
  const fixedKeys = selection?.fixedProblems?.map(key) ?? [];
  if (new Set(actualKeys).size !== actualKeys.length) errors.push('duplicate canonical problem identities');
  if (fixedKeys.length !== expected || new Set(fixedKeys).size !== fixedKeys.length
    || !sameSet(new Set(actualKeys), new Set(fixedKeys))) errors.push('fixed problem identities mismatch');
  const records = audit.records.map(record => {
    const resolution = record.resolution;
    const resolved = Boolean(errors.length === 0 && isCorpusSolutionReviewed(record)
      && resolution?.status === 'verified' && Array.isArray(resolution.techniqueIds)
      && resolution.techniqueIds.length > 0
      && resolution.techniqueIds.every(id => coveredTechnique(id, data, record)));
    return { source: record.source, problemId: record.problemId, title: record.title,
      originalClassification: record.classification,
      currentClassification: resolved ? 'covered' : record.classification === 'covered' ? 'unconfirmed' : record.classification,
      resolved, techniqueIds: resolved ? resolution.techniqueIds : [], gapId: record.gap?.id ?? null };
  });
  // The first-pass status is historical. Later explicit proof reviews may
  // complete the research while that initial false value remains unchanged.
  const firstPassComplete = audit.status?.firstPassAuditComplete === undefined
    ? audit.status?.fixedCorpusResearchComplete === true
    : audit.status.firstPassAuditComplete === true;
  const researchComplete = errors.length === 0 && audit.selection?.fixedBeforeTechniqueSearch === true
    && firstPassComplete && audit.status.recordCount === records.length
    && audit.records.every(isCorpusSolutionReviewed);
  return { corpusId: audit.corpusId, researchComplete,
    coverageComplete: researchComplete && records.length > 0 && records.every(row => row.resolved),
    reviewedProblems: audit.records.filter(isCorpusSolutionReviewed).length,
    coveredProblems: records.filter(row => row.resolved).length, totalProblems: records.length, records, errors };
}

export async function auditCoverage(root = site) {
  const plan = await json(path.join(root, 'data/coverage-plan.json'));
  const names = await readdir(path.join(root, 'data'));
  const collection = async prefix => (await Promise.all(names.filter(name => name.startsWith(prefix)
    && name.endsWith('.json')).map(name => json(path.join(root, 'data', name))))).flat();
  const [techniques, references, walks, ledger, preflight] = await Promise.all([
    collection('techniques-'), collection('references-'), json(path.join(root, 'data/problem-walks.json')),
    json(path.join(root, 'data/research-ledger.json')), validateSite(root),
  ]);
  const errors = preflight.errors.map(error => `content preflight: ${error}`);
  const temporary = await mkdtemp(path.join(tmpdir(), 'flowchartcp-coverage-audit-'));
  let flow;
  try {
    if (!errors.length) {
      await compileLocalModules(root, temporary);
      flow = await import(pathToFileURL(path.join(temporary, 'flow.js')).href);
    }
    const entries = new Set(flow?.entryGraphs.map(graph => graph.id) ?? []);
    const isWalkValid = (walk, id) => {
      if (!flow || !entries.has(walk.entryGraphId) || !Array.isArray(walk.choices)) return false;
      try {
        const actual = flow.walkFromRoot(walk.choices, walk.entryGraphId);
        return actual.consumed === walk.choices.length && actual.current.type === 'result'
          && actual.current.techniques.includes(id)
          && JSON.stringify(actual.steps.map(({ graph, node, answer }) => ({ graph, node, answer }))) === JSON.stringify(walk.steps);
      } catch { return false; }
    };
    const data = { techniques, references, walks, preflightPassed: errors.length === 0, isWalkValid };
    const corpora = [];
    for (const item of plan.corpora) {
      if (!safeFile(item.auditFile)) { errors.push(`${item.id}: unsafe audit path`); continue; }
      let audit;
      try { audit = await json(path.join(root, item.auditFile)); }
      catch (error) { if (error.code !== 'ENOENT') throw error; }
      if (!audit) {
        if (item.state === 'audited') errors.push(`${item.id}: audited corpus has no records`);
        corpora.push({ corpusId: item.id, scope: item.scope, researchComplete: false,
          coverageComplete: false, totalProblems: item.expectedProblems, reviewedProblems: 0, coveredProblems: 0 });
        continue;
      }
      const assessed = assessCorpus(audit, data, { ...item, cutoff: plan.cutoff });
      errors.push(...assessed.errors.map(error => `${item.id}: ${error}`));
      corpora.push({ scope: item.scope, ...assessed });
    }
    const knownGaps = plan.knownGaps.map(gap => {
      const checked = Array.isArray(gap.techniqueIds) && gap.techniqueIds.length > 0
        && gap.techniqueIds.every(id => coveredTechnique(id, data));
      if (gap.state === 'resolved' && !checked) errors.push(`${gap.id}: resolution lacks reviewed article, confirmed example or valid root walk`);
      return { id: gap.id, features: gap.features, state: gap.state,
        resolved: gap.state === 'resolved' && checked, techniqueIds: gap.techniqueIds };
    });
    return { cutoff: plan.cutoff, globalCoverageComplete: false, globalProblemCount: null,
      policy: plan.policy, techniqueArticles: techniques.filter(row => row.kind === 'technique').length,
      totalArticles: techniques.length, mappings: references.length,
      sourcesWithUnknownTotal: ledger.sources.filter(row => row.totalKnown === null).map(row => row.source),
      corpora, knownGaps, unresolvedKnownGaps: knownGaps.filter(row => !row.resolved).length, errors };
  } finally { await rm(temporary, { recursive: true, force: true }); }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  if (args.some(arg => !['--write', '--json'].includes(arg))) throw new Error('Use --write and/or --json');
  const report = await auditCoverage();
  if (args.includes('--write')) await writeFile(path.join(site, 'data/coverage-report.json'), JSON.stringify(report, null, 2) + '\n');
  if (args.includes('--json')) console.log(JSON.stringify(report, null, 2));
  else {
    console.log(`${report.techniqueArticles} specific articles; ${report.unresolvedKnownGaps} unresolved known gaps.`);
    for (const corpus of report.corpora) console.log(`${corpus.corpusId}: research ${corpus.reviewedProblems}/${corpus.totalProblems ?? '?'}; covered ${corpus.coveredProblems}/${corpus.totalProblems ?? '?'}; complete ${corpus.coverageComplete}`);
    console.log('Global coverage remains incomplete; the global denominator is unknown.');
    for (const error of report.errors) console.error(error);
  }
  if (report.errors.length) process.exitCode = 1;
}
