#!/usr/bin/env python3
"""Read-only independent review: frozen hashes, raw routes and separate literal checks."""
import collections, hashlib, importlib.util, itertools, json, math
from pathlib import Path
from usaco_spring_snapshot import open_snapshot
import argparse
SITE=Path(__file__).resolve().parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def review():
 before=json.loads((ROOT/'hashes-before.json').read_text());after=json.loads((ROOT/'hashes-after.json').read_text());assert before==after
 for file,digest in before.items():assert sha(ROOT/file)==digest,file
 metadata=[r for f in (ROOT/'data').glob('techniques-*.json') for r in json.loads(f.read_text())]
 refs=[r for f in (ROOT/'data').glob('references-*.json') for r in json.loads(f.read_text())]
 graphs=json.loads((ROOT/'data/flows.json').read_text());walks=json.loads((ROOT/'data/problem-walks.json').read_text())
 counts={'articles':len(list((ROOT/'src/content/docs/techniques').glob('*.mdx'))),'metadata':len(metadata),'graphs':len(graphs),'walks':len(walks),'references':len(refs),'rawFiles':len(before)}
 assert counts=={'articles':488,'metadata':488,'graphs':455,'walks':509,'references':509,'rawFiles':620}
 assert len({x['id'] for x in metadata})==488
 output={'frozenCounts':counts,'rawLedgerSha256':sha(ROOT/'SHA256SUMS'),'flowRawSha256':sha(ROOT/'data/flows.json'),'allFrozenFilesMatch':True,'beforeEqualsAfter':True}
 audit_path=SITE/'data/corpus-audits/usaco-2021-february-us-open-platinum.json'
 if audit_path.exists():
  audit=json.loads(audit_path.read_text());lookup={g['id']:g for g in graphs};traces=[]
  for record in audit['records']:
   gid=record['entryGraphId'];nid=lookup[gid]['root'];taken=[];transitions=[]
   def resolve(gid,nid):
    for _ in range(256):
     node=next(x for x in lookup[gid]['nodes'] if x['id']==nid)
     if node['type']!='route':return gid,nid,node
     target=node['graph'];transitions.append({'fromGraphId':gid,'fromNodeId':nid,'toGraphId':target});gid=target;nid=lookup[gid]['root']
    raise AssertionError('cycle')
   gid,nid,node=resolve(gid,nid)
   for choice in record['choices']:
    assert node['type']=='question'
    options=node.get('options')
    if options is None:options=[{'id':a,'label':{'yes':'はい','no':'いいえ','unknown':'わからない'}.get(a,a)} for a in node.get('answers',{})]
    selected=next(x for x in options if x['id']==choice)
    taken.append({'graphId':gid,'nodeId':nid,'question':node['title'],'answer':choice,'answerLabel':selected['label']})
    gid,nid,node=resolve(gid,node['answers'][choice])
   options=node.get('options')
   if options is None:options=[{'id':a,'label':{'yes':'はい','no':'いいえ','unknown':'わからない'}.get(a,a)} for a in node.get('answers',{})]
   end={'graphId':gid,'nodeId':nid,'type':node['type'],'title':node['title'],'options':options,'techniques':node.get('techniques',[])}
   assert taken==record['steps'];assert end==record['initialReached']==record['canonicalRouteEnd']
   assert transitions==record['navigationReplay']['routeTransitions']
   gap=record['gap'];assert (gap['firstMissingGraphId'],gap['firstMissingNodeId'],gap['currentQuestion'],gap['currentOptions'])==(gid,nid,node['title'],options)
   traces.append({'problemId':record['problemId'],'entry':record['entryGraphId'],'choices':record['choices'],'questionCount':len(taken),'end':end})
  assert len(traces)==6;output['rawRouteReplays']=traces
 # Every loop-allowed undirected graph, independent terminal-degree predicate.
 total=conditions=0
 for n in range(6):
  edges=list(itertools.combinations_with_replacement(range(n),2));actual=[0]*(n+1)
  for bits in range(1<<len(edges)):
   touched=0
   for i,(u,v) in enumerate(edges):
    if bits>>i&1:touched|=(1<<u)|(1<<v)
   for required in range(n+1):actual[required]+=(touched&((1<<required)-1))==((1<<required)-1)
   total+=1
  for required,value in enumerate(actual):
   formula=sum((-1)**k*math.comb(required,k)*2**((n-k)*(n-k+1)//2) for k in range(required+1))
   assert formula==value;conditions+=1
 output['separateTerminalPIE']={'graphsN0to5':total,'requiredDegreeConditions':conditions}
 # Concrete witnesses separating nearby general methods from the required lemmas.
 def word(n,edges):
  adjacency=[0]*n
  for u,v in edges:adjacency[u]|=1<<v;adjacency[v]|=1<<u
  current=1;values=[]
  for _ in range(2*n+3):
   values.append(current);following=0
   for v in range(n):
    if current>>v&1:following|=adjacency[v]
   current=following
  return values
 assert word(3,[(0,1),(0,2)])!=word(3,[(0,1),(0,2),(1,2)])
 expected_word=word(2,[(0,1),(0,0)]);equivalent=0
 for bits in range(4):
  edges=[(0,1)]+[(i,i) for i in range(2) if bits>>i&1]
  equivalent+=word(2,edges)==expected_word
 assert equivalent==2
 arr=[1,2,1,3];mutually_distinct=legal=0
 for l,m,r in itertools.combinations(range(4),3):
  mutually_distinct+=len({arr[l],arr[m],arr[r]})==3
  freq=collections.Counter(arr[l:r+1]);legal+=all(freq[arr[x]]==1 for x in [l,m,r])
 assert (mutually_distinct,legal)==(2,1)

 output['independentGapWitnesses']={
  '1116':{'array':[2,1,2],'query':[0,2],'naiveConsecutiveEqualPairAnswer':2,'actualPaintAnswer':3,'reason':'The intervening lighter color forbids joining the two 2 strokes.'},
  '1117':{'n':3,'star':[[0,1],[0,2]],'triangle':[[0,1],[0,2],[1,2]],'sameOrdinaryRootDistances':[0,1,1],'minimumEdges':[2,3],'reason':'Ordinary root distances discard odd-walk feasibility.'},
  '1118':{'n':2,'rootLoopGraphs':[[[0,1],[0,0]],[[0,1],[0,0],[1,1]]],'sameRootWalkLanguage':True,'equivalenceClassSize':2,'reason':'Bipartite-level formulas miss allowed loop/internal terminal choices.'},
  '1140':{'array':[1,2,1,3],'leaderTriplesWithDistinctBreeds':2,'actualValidDelegations':1,'reason':'The endpoint leader breed must be unique in the entire delegation.'},
  '1141':{'n':3,'edges':[[0,1],[1,0],[0,2]],'roles':'S.R','degreeFactorialProduct':2,'actualSchemes':1,'validTrail':[0,1,0,2],'reason':'One local pairing leaves an independent cycle; valid paths may revisit vertices.'},
  '1142':{'rows':['GG','.G','GG'],'rowConvexAndConnected':True,'columnConvex':False,'leftEndpoints':[0,1,0],'reason':'A left boundary that turns inward then outward leaves a column gap.'}}
 return output
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
 with open_snapshot() as ROOT:value=review()
 if args.output:args.output.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps(value,ensure_ascii=False,indent=2))
