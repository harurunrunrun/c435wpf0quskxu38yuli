import core from '../../data/techniques-core.json';
import advanced from '../../data/techniques-advanced.json';
import reasoning from '../../data/techniques-reasoning.json';
import coreReferences from '../../data/references-core.json';
import advancedReferences from '../../data/references-advanced.json';
import reasoningReferences from '../../data/references-reasoning.json';
import specificCore from '../../data/techniques-specific-core.json';
import specificDP from '../../data/techniques-specific-dp.json';
import specificMath from '../../data/techniques-specific-math.json';
import specificStrings from '../../data/techniques-specific-strings.json';
import specificGraphs from '../../data/techniques-specific-graphs.json';
import specificAlgebra from '../../data/techniques-specific-algebra.json';
import specificOffline from '../../data/techniques-specific-offline.json';
import specificConstruction from '../../data/techniques-specific-construction.json';
import specificGeometry from '../../data/techniques-specific-geometry.json';
import specificGames from '../../data/techniques-specific-games.json';
import specificHeuristic from '../../data/techniques-specific-heuristic.json';
import specificDPExtensions from '../../data/techniques-specific-dp-extensions.json';
import specificStringExtensions from '../../data/techniques-specific-string-extensions.json';
import specificFlowMatching from '../../data/techniques-specific-flow-matching.json';
import specificTreePaths from '../../data/techniques-specific-tree-paths.json';
import specificCombinatorics from '../../data/techniques-specific-combinatorics.json';
import specificOlympiadPatterns from '../../data/techniques-specific-olympiad-patterns.json';
import specificSelectionPatterns from '../../data/techniques-specific-selection-patterns.json';
import specificGraphExtensions from '../../data/techniques-specific-graph-extensions.json';
import specificDPStructures from '../../data/techniques-specific-dp-structures.json';
import specificIntegerPatterns from '../../data/techniques-specific-integer-patterns.json';
import specificRangePatterns from '../../data/techniques-specific-range-patterns.json';
import specificOperationPatterns from '../../data/techniques-specific-operation-patterns.json';
import specificDPPatterns from '../../data/techniques-specific-dp-patterns.json';
import specificStringPatterns from '../../data/techniques-specific-string-patterns.json';
import specificTreePatterns from '../../data/techniques-specific-tree-patterns.json';
import specificBitPatterns from '../../data/techniques-specific-bit-patterns.json';
import specificPlanarPatterns from '../../data/techniques-specific-planar-patterns.json';
import specificProbabilityPatterns from '../../data/techniques-specific-probability-patterns.json';
import specificCoreReferences from '../../data/references-specific-core.json';
import specificDPReferences from '../../data/references-specific-dp.json';
import specificMathReferences from '../../data/references-specific-math.json';
import specificStringReferences from '../../data/references-specific-strings.json';
import specificGraphReferences from '../../data/references-specific-graphs.json';
import specificAlgebraReferences from '../../data/references-specific-algebra.json';
import specificOfflineReferences from '../../data/references-specific-offline.json';
import specificConstructionReferences from '../../data/references-specific-construction.json';
import specificGeometryReferences from '../../data/references-specific-geometry.json';
import specificGameReferences from '../../data/references-specific-games.json';
import specificHeuristicReferences from '../../data/references-specific-heuristic.json';
import specificDPExtensionReferences from '../../data/references-specific-dp-extensions.json';
import specificStringExtensionReferences from '../../data/references-specific-string-extensions.json';
import specificFlowMatchingReferences from '../../data/references-specific-flow-matching.json';
import specificTreePathReferences from '../../data/references-specific-tree-paths.json';
import specificCombinatoricsReferences from '../../data/references-specific-combinatorics.json';
import specificOlympiadPatternReferences from '../../data/references-specific-olympiad-patterns.json';
import coverageRound3References from '../../data/references-specific-coverage-round3.json';
import specificSelectionPatternReferences from '../../data/references-specific-selection-patterns.json';
import specificGraphExtensionReferences from '../../data/references-specific-graph-extensions.json';
import specificDPStructureReferences from '../../data/references-specific-dp-structures.json';
import specificIntegerPatternReferences from '../../data/references-specific-integer-patterns.json';
import specificRangePatternReferences from '../../data/references-specific-range-patterns.json';
import specificOperationPatternReferences from '../../data/references-specific-operation-patterns.json';
import specificDPPatternReferences from '../../data/references-specific-dp-patterns.json';
import specificStringPatternReferences from '../../data/references-specific-string-patterns.json';
import specificTreePatternReferences from '../../data/references-specific-tree-patterns.json';
import specificBitPatternReferences from '../../data/references-specific-bit-patterns.json';
import specificPlanarPatternReferences from '../../data/references-specific-planar-patterns.json';
import specificProbabilityPatternReferences from '../../data/references-specific-probability-patterns.json';

export interface Technique {
  id: string;
  title: string;
  aliases: string[];
  family: string;
  level: string;
  summary: string;
  entryPoints: string[];
  prerequisites: string[];
  status: string;
  sources: string[];
  kind: 'foundation' | 'technique';
}
export interface ProblemReference {
  techniqueId: string;
  source: string;
  problemId: string;
  title: string;
  url: string;
  editorialUrl: string | null;
  evidence: string;
  verification: string;
  difficulty: string | null;
  verificationNotes?: string;
}
export const techniques: Technique[] = [
  ...[...core, ...advanced, ...reasoning].map(item => ({ ...item, kind: 'foundation' as const })),
  ...[...specificCore, ...specificDP, ...specificMath, ...specificStrings, ...specificGraphs, ...specificAlgebra, ...specificOffline, ...specificConstruction, ...specificGeometry, ...specificGames, ...specificHeuristic, ...specificDPExtensions, ...specificStringExtensions, ...specificFlowMatching, ...specificTreePaths, ...specificCombinatorics, ...specificOlympiadPatterns, ...specificSelectionPatterns, ...specificGraphExtensions, ...specificDPStructures, ...specificIntegerPatterns, ...specificRangePatterns, ...specificOperationPatterns, ...specificDPPatterns, ...specificStringPatterns, ...specificTreePatterns, ...specificBitPatterns, ...specificPlanarPatterns, ...specificProbabilityPatterns].map(item => ({ ...item, kind: 'technique' as const })),
];
export const techniqueById = new Map(techniques.map((item) => [item.id, item]));
export const references = [...coreReferences, ...advancedReferences, ...reasoningReferences, ...specificCoreReferences, ...specificDPReferences, ...specificMathReferences, ...specificStringReferences, ...specificGraphReferences, ...specificAlgebraReferences, ...specificOfflineReferences, ...specificConstructionReferences, ...specificGeometryReferences, ...specificGameReferences, ...specificHeuristicReferences, ...specificDPExtensionReferences, ...specificStringExtensionReferences, ...specificFlowMatchingReferences, ...specificTreePathReferences, ...specificCombinatoricsReferences, ...specificOlympiadPatternReferences, ...coverageRound3References, ...specificSelectionPatternReferences, ...specificGraphExtensionReferences, ...specificDPStructureReferences, ...specificIntegerPatternReferences, ...specificRangePatternReferences, ...specificOperationPatternReferences, ...specificDPPatternReferences, ...specificStringPatternReferences, ...specificTreePatternReferences, ...specificBitPatternReferences, ...specificPlanarPatternReferences, ...specificProbabilityPatternReferences] as ProblemReference[];
export function withBase(path: string) {
  const base = import.meta.env?.BASE_URL ?? '/flowchartcp/';
  return `${base.replace(/\/$/, '')}/${path.replace(/^\//, '')}`;
}
export function techniqueUrl(id: string) { return withBase(`techniques/${id}/`); }
