#!/usr/bin/env python3
"""Recheck retained IOI2018 snapshots and research oracles; no live-product reads.

The 607-file raw rehash was performed at the original review. Only flow and
aggregate metadata bytes are permanently stored; other original bytes are not
claimed available. Their SHA ledger and original manifest bytes are retained.
No argument writes files. An optional output path stores this rerun report.
"""
import ast,base64,gzip,hashlib,heapq,itertools,json,math,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
AUDIT=ROOT/'data/corpus-audits/ioi-2018.json'
MANIFEST=ROOT/'research/snapshots/ioi-2018-manifest.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
compact=lambda x:json.dumps(x,ensure_ascii=False,separators=(',',':')).encode()
audit_bytes=AUDIT.read_bytes();a=json.loads(audit_bytes)
initial_records=[{k:v for k,v in r.items() if k not in ('resolution','subsequentSolutionReviews','subsequentSourceVerifications')} for r in a['records']]
manifest_bytes=MANIFEST.read_bytes();m=json.loads(manifest_bytes)
assert sha(manifest_bytes)=='5f4e3a6d77568ffdd1fbd25f6632c6520bc06b09ec5713b5fcf82385c8cca104'
original_manifest_bytes=base64.b64decode(m['originalManifestRawBase64'],validate=True)
assert sha(original_manifest_bytes)=='bc97c90a87d59f384a931ca5e315799372169b8ac5a78fbb4b3bced5d9a600bf'
source=json.loads(original_manifest_bytes)
assert source['files']==m['files'] and len(m['files'])==607
assert sha(compact(m['files']))=='ccdb633a48e808042bd11343f074010512219d5406b5e3d47f872e55e6648111'
assert sha(compact(initial_records))=='ee06a9394e994d941e27a5b820bdd7f6eafbe0d54561f1b3216d2a7a950a0523'
assert sha(compact(a['status']))=='8004bbe3f1d6107d67f6b75a76ae60175a1c7b7ee6e86277bc8d864b027f7ff3'
assert sha(compact(a['selection']))=='1a1ad95f82fcff524f555c339050ba4c05c86b9d7309e80023486479570da71b'
snapshots={}
for kind in ('flow','technique'):
 raw=gzip.decompress((ROOT/a['snapshot'][kind+'SnapshotFile']).read_bytes())
 assert sha(raw)==a['snapshot'][kind+'Sha256']
 snapshots[kind]=json.loads(raw)
assert len(snapshots['flow'])==449 and len(snapshots['technique'])==482
assert sum(t.get('kind')=='technique' for t in snapshots['technique'])==404
assert m['walkCount']==503
assert not m['preservation']['allHistoricalMdxPermanentlyStored']
assert not m['preservation']['allHistoricalRawFilesPermanentlyStored']
assert m['preservation']['permanentRawSnapshotCount']==2
tasks=['combo','seats','werewolf','doll','highway','meetings']
assert [r['problemId'] for r in a['records']]==['ioi2018_'+t for t in tasks]
assert [r['contest']['date'] for r in a['records']]==['2018-09-03']*3+['2018-09-05']*3
graphs={g['id']:g for g in snapshots['flow']}
ledger={f['path']:f for f in m['files']}
ids={r['id'] for r in snapshots['technique']}
def raw_walk(entry,choices):
 gid=entry;nid=graphs[gid]['root'];used=0;steps=[];seen=set()
 assert graphs[gid].get('entry')
 while True:
  key=(gid,nid,used);assert key not in seen;seen.add(key)
  node=next(n for n in graphs[gid]['nodes'] if n['id']==nid)
  if node['type']=='route':
   gid=node['graph'];nid=graphs[gid]['root'];continue
  options=node.get('options',[{'id':i,'label':{'yes':'はい','no':'いいえ','unknown':'わからない'}.get(i,i)} for i in node.get('answers',{})])
  if node['type']!='question' or used==len(choices):
   assert used==len(choices)
   return steps,dict(graphId=gid,nodeId=nid,type=node['type'],title=node['title'],options=options,techniques=node.get('techniques',[]))
  answer=choices[used];used+=1
  label=next(o['label'] for o in options if o['id']==answer)
  steps.append(dict(graphId=gid,nodeId=nid,question=node['title'],answer=answer,answerLabel=label))
  nid=node['answers'][answer]
routes=[]
for r in initial_records:
 steps,current=raw_walk(r['entryGraphId'],r['choices'])
 assert steps==r['steps'] and current==r['canonicalRouteEnd']
 assert current['options']==r['gap']['currentOptions']
 assert current['title']==r['gap']['currentQuestion']
 assert [current['graphId'],current['nodeId']]==[r['gap']['firstMissingGraphId'],r['gap']['firstMissingNodeId']]
 assert r['actualReachedTechniqueIds']==current['techniques'] and not r['expectedTechniqueIds']
 assert r['classification']=='missing-technique'
 assert all(i not in ids for i in r['gap']['neededTechniqueIds'])
 assert all(i in ids for i in r['gap']['existingRelatedTechniqueIds'])
 assert r['technicalFindings']['verification']=='independent-analysis'
 assert not r['technicalFindings']['unconfirmedDetails']
 assert r['technicalFindings']['fullImplementationValidated'] is False
 assert r['technicalFindings']['remainingImplementationValidation']
 for related in r['relatedArticleReview']:
  assert ledger[related['file']]['sha256']==related['sha256']
  assert related['scopeMismatch']
 routes.append({'problemId':r['problemId'],'stop':[current['graphId'],current['nodeId']],'choices':r['choices']})
# Load only the two pure functions under review, without author probe top-level
# loops or output writes. Every further oracle below is independently authored.
tree = ast.parse((ROOT / 'research/probes/ioi-2018-research-checks.py').read_text())
functions = ast.Module(body=[n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('meetings_tables', 'doll')], type_ignores=[])
namespace = {'math': math}
exec(compile(functions, '<reviewed-functions>', 'exec'), namespace)
h = [2, 1, 2]

def oriented_cost(values, priorities):
    nodes, prefixes = namespace['meetings_tables'](values, priorities)
    v = max(range(len(values)), key=lambda i: (values[i], priorities[i]))
    answer = (v + 1) * values[v]
    if nodes[v][3] is not None:
        answer += prefixes[nodes[v][3]][-1]
    return answer

correct = min(oriented_cost(h, [0, 1, 2]), oriented_cost(h[::-1], [2, 1, 0]))
wrong = min(oriented_cost(h, [0, 1, 2]), oriented_cost(h[::-1], [0, 1, 2]))
literal = min(sum(max(h[min(v, i):max(v, i) + 1]) for i in range(3)) for v in range(3))
assert correct == literal == 5 and wrong == 6

doll_formula_cases = 0
for n in range(1, 200001):
    height = n.bit_length()
    switches = sum((n + (1 << j)) >> j for j in range(1, height + 1))
    assert switches == n - n.bit_count() + height
    assert switches <= n + n.bit_length() - 1
    assert ((1 << height) * height) <= 4718592
    doll_formula_cases += 1
doll_boundary_cases = 0
boundaries = set(range(1, 65)) | {200000}
for j in range(1, 18):
    boundaries.update([2 ** j - 1, 2 ** j, 2 ** j + 1])
for n in sorted(boundaries):
    namespace['doll']([1] * n, 1)
    doll_boundary_cases += 1

# For every connected graph up to four vertices, enumerate EVERY legal A/B
# edge-weight vector. Literal simple-path enumeration answers the same fixed
# hidden pair as Dijkstra, independently of the endpoint-search construction.
weighted_vectors = weighted_pair_comparisons = connected_graphs = 0
for n in range(2, 5):
    possible = list(itertools.combinations(range(n), 2))
    for bits in range(1 << len(possible)):
        edges = [e for j, e in enumerate(possible) if bits >> j & 1]
        adj = [[] for _ in range(n)]
        for j, (u, v) in enumerate(edges):
            adj[u].append((v, j)); adj[v].append((u, j))
        reached = {0}; queue = [0]
        for u in queue:
            for v, _ in adj[u]:
                if v not in reached: reached.add(v); queue.append(v)
        if len(reached) != n: continue
        connected_graphs += 1
        for low, high in [(1, 2), (3, 4), (1, 10 ** 9)]:
            for mask in range(1 << len(edges)):
                weights = [high if mask >> j & 1 else low for j in range(len(edges))]
                weighted_vectors += 1
                for s in range(n):
                    dist = [10 ** 30] * n; dist[s] = 0; heap = [(0, s)]
                    while heap:
                        d, u = heapq.heappop(heap)
                        if dist[u] != d: continue
                        for v, j in adj[u]:
                            nd = d + weights[j]
                            if nd < dist[v]: dist[v] = nd; heapq.heappush(heap, (nd, v))
                    direct = [10 ** 30] * n
                    stack = [(s, 1 << s, 0)]
                    while stack:
                        u, seen, d = stack.pop()
                        direct[u] = min(direct[u], d)
                        for v, j in adj[u]:
                            if not (seen >> v & 1): stack.append((v, seen | (1 << v), d + weights[j]))
                    for t in range(s + 1, n):
                        assert dist[t] == direct[t]
                        weighted_pair_comparisons += 1

original_probe=json.loads((ROOT/'research/probes/ioi-2018-research-checks-results.json').read_bytes())
with tempfile.TemporaryDirectory(prefix='ioi2018-research-review-') as directory:
 rerun=Path(directory)/'results.json'
 subprocess.run([sys.executable,str(ROOT/'research/probes/ioi-2018-research-checks.py'),str(rerun)],check=True,stdout=subprocess.PIPE,text=True)
 rerun_probe=json.loads(rerun.read_bytes())
assert {k:v for k,v in original_probe.items() if k!='seconds'}=={k:v for k,v in rerun_probe.items() if k!='seconds'}
assert AUDIT.read_bytes()==audit_bytes
report={
 'status':'complete-no-substantive-findings',
 'auditFile':'data/corpus-audits/ioi-2018.json','auditSha256':sha(audit_bytes),
 'auditSha256Scope':'audit bytes at this review; later appended reviews do not rewrite the fixed initial record/status/selection projections',
 'originalRecordsSha256':sha(compact(initial_records)),
 'originalAuditRawSha256':a['preservation']['originalAuditRawSha256'],
 'sharedDataModified':False,'authorArtifactsModified':False,
 'snapshot':{'historicalRawFilesVerifiedAtInitialReview':607,'permanentRawSnapshotsRehashed':2,'articles':482,'specific':404,'graphs':449,'walks':503},
 'preservation':{'allHistoricalRawBytesAvailable':False,'allHistoricalMdxAvailable':False,'originalManifestRawSha256':sha(original_manifest_bytes),'permanentManifestRawSha256':sha(manifest_bytes),'originalManifestEntriesUnchanged':True,'originalRecordsAndStatusUnchanged':True},
 'routesReplayedWithoutProductWalker':routes,
 'officialSelectionAndDatesIndependentlyRetrievedAtInitialReview':True,
 'numericEvidence':'All six organizer-hosted translation search texts independently reproduced at the initial review; no PDF visual inspection claimed.',
 'officialReviewProvenance':'All six Reviews are direct links from organizer and Japan committee task lists. Missing mathematical extraction is explicitly supplemented by author primary HTML and independent analysis, rather than claimed visually read.',
 'researchVsCoverage':{'solutionsReviewed':6,'principalUnconfirmed':0,'missingConcreteTechniques':6,'covered':0,'fullImplementationValidated':0,'globalComplete':False},
 'probes':rerun_probe,
 'additionalChecks':{
  'meetingsEqualMaximum':{'array':h,'sameOriginalMaximumId':correct,'wrongReverseLocalTieRule':wrong,'literalMeetingSiteOracle':literal},
  'dollSwitchAndInversionBoundsForAllN':doll_formula_cases,
  'dollFullSimulationAdditionalBoundaryLengths':doll_boundary_cases,
  'highwayAllPossibleWeightVectors':weighted_vectors,
  'highwayLiteralSimplePathVsDijkstraPairs':weighted_pair_comparisons,
  'highwayConnectedGraphsN2To4':connected_graphs,
 },
 'proofReview':{'combo': 'Unique first symbol restricts every candidate occurrence to one of the four P starts; queried length4|P|+7<=4N-1; middle answer is classified >=|P|+2, not assumed exact. First2+middle(N-2)+last2<=N+2; N=1 separate.', 'seats': 'C1>=4; absence of C3 makes every four-neighbor component a rectangle; triangle-free planar diagonal-contact graph forces C1=4 to have one component. Four labels contribute exactly odd-population intervals[a,b),[c,d); only eight deduplicated vertices change.', 'werewolf': 'Human and wolf feasible vertex components intersect iff a legal one-way transformation exists. Separate activation-tree leaf orders require a two-dimensional point set, not one-dimensional interval overlap; inclusive thresholds and half-open sweep match BFS.', 'doll': 'Pruning only complete dead spatial subtrees skips their internal toggles but preserves retained-switch events in the original bit-reversal cycle. Last spatial leafP-1 is retained and assigned0, so first return occurs only at cycle end; retained switches all toggle evenly. BoundS=N-popcount(N)+bit_length(N)<=N+floorlog2N.', 'highway': 'Threshold pivot lies on some original hop-shortest path. Its two endpoints give disjoint strict-distance Voronoi sets closed under rooted shortest paths. The two BFS trees+pivot alone are A; every other edge B. Any B-containing route exceeds D because its hop count is at least the original optimum and B>A. A path is unique, so suffix-parent-edge response tests identify the maximum vertex order on that path, including a root endpoint. All replies use one fixed hidden pair.', 'meetings': 'Recurrence separates sites left/right of fixed maximum. The F-G difference is monotone since adding one participant raises optimal right-prefix cost by at most Hv. Fixed original-index tie priority preserves the same split in both directions. Global-position map uses O(1) iterator beta updates; charging surviving fragments to birth vertices and choosing smaller original subtree mass proves O(NlogN) offset work despite fragment deletion. Full compressed C++20 and worst-case runtime remain explicitly unvalidated.'},
 'sourceUrls':[a['selection']['countEvidence']['officialIndexUrl'],'https://www2.ioi-jp.org/ioi/2018/tasks/index.html']+[u for r in a['records'] for u in r['constraints']['numericEvidenceUrls']],
}
if len(sys.argv)>1:
 Path(sys.argv[1]).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':report['status'],'permanentRawSnapshotsRehashed':2,'historicalRawFilesAtInitialReview':607,'additionalChecks':report['additionalChecks']},ensure_ascii=False,indent=2))
