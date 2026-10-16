#!/usr/bin/env python3
"""Research-only lemma probes and independent replay of the frozen corpus.
No production C++ API/article is claimed by this audit.
"""
import collections,hashlib,itertools,json,math,random,time
from pathlib import Path
from usaco_spring_snapshot import open_snapshot
import argparse,sys
SITE=Path(__file__).resolve().parents[2]
result={};begin=time.monotonic()

def no_time():
 tables={};states=0
 for n in range(1,7):
  first=(0,)*n;distance={first:0};q=collections.deque([first])
  while q:
   a=q.popleft()
   for l in range(n):
    for r in range(l,n):
     minimum=max(a[l:r+1])
     for c in range(max(1,minimum),4):
      b=a[:l]+(c,)*(r-l+1)+a[r+1:]
      if b not in distance:distance[b]=distance[a]+1;q.append(b)
  tables[n]=distance;states+=len(distance)
 arrays=queries=0
 for n in range(1,7):
  for a in itertools.product(range(1,4),repeat=n):
   stack=[];pairs=[]
   for r,x in enumerate(a):
    while stack and a[stack[-1]]>x:stack.pop()
    if stack and a[stack[-1]]==x:pairs.append((stack.pop(),r))
    stack.append(r)
   for l in range(n):
    for r in range(l,n):
     predicted=r-l+1-sum(l<=x and y<=r for x,y in pairs)
     assert predicted==tables[r-l+1][a[l:r+1]],('paint',a,l,r,pairs)
     queries+=1
   arrays+=1
 result['1116']={'arrays':arrays,'allSubintervals':queries,'literalPaintingBFSStates':states,'oracle':'BFS from all-zero fence, enumerate EVERY legal contiguous brush stroke of colors1..3 (never decrease any cell), then compare minimum action counts. No monotone-stack oracle.'}

INF=999

def profile(n,adj):
 d=[[INF,INF] for _ in range(n)];d[0][0]=0;q=collections.deque([(0,0)])
 while q:
  x,p=q.popleft()
  for y in adj[x]:
   if d[y][1-p]==INF:d[y][1-p]=d[x][p]+1;q.append((y,1-p))
 return tuple(tuple(sorted(x)) for x in d)

def exact_infinite_walk_word(n,neighbors):
 # Deterministic evolution of the literal set reachable in EXACTLYt moves.
 # Detect repeated bitsets to represent the COMPLETE infinite language, not a cutoff.
 seen={};word=[];mask=1
 while mask not in seen:
  seen[mask]=len(word);word.append(mask);nxt=0
  for x in range(n):
   if mask>>x&1:nxt|=neighbors[x]
  mask=nxt
 pre=word[:seen[mask]];cycle=word[seen[mask]:]
 for period in range(1,len(cycle)+1):
  if len(cycle)%period==0 and all(cycle[i]==cycle[i%period] for i in range(len(cycle))):cycle=cycle[:period];break
 while pre and pre[-1]==cycle[-1]:cycle=[pre.pop()]+cycle[:-1]
 return tuple(pre),tuple(cycle)

def greedy_minimum(h):
 n=len(h)
 if h[0][1]==INF:return n-1
 freq=collections.Counter(h);incoming={};answer=0
 for (a,b),f in sorted(freq.items()):
  previous=incoming.get((a-1,b+1),0);has_A=(a-1,b-1) in freq
  if b==a+1:
   if a==0:answer+=(f+1)//2
   elif has_A:answer+=max(f-previous+(previous+1)//2,(f+1)//2)
   else:answer+=max(f-previous,0)+(f+1)//2
  else:
   answer+=f
   if a==0:incoming[a,b]=f
   elif has_A:incoming[a,b]=min(f,previous)
   else:answer+=max(f-previous,0);incoming[a,b]=f
 return answer

def C(n,k):return math.comb(n,k) if 0<=k<=n else 0

def count_graphs(h):
 n=len(h)
 if h[0][1]==INF:
  f=collections.Counter(a for a,b in h);answer=1
  for d,number in f.items():
   if d:answer*=((1<<f[d-1])-1)**number
  return answer
 s=collections.Counter(h);answer=1
 for layer in range(1,max(a+b for a,b in h)+1,2):
  dp=[0]*(s[0,layer]+1);dp[-1]=1
  for a in range(1,layer//2+1):
   b=layer-a;number=s[a,b];previous=s[a-1,b+1];lower=s[a-1,b-1]
   intermediate=[0]*(number+1)
   for x in range(number+1):
    for y,value in enumerate(dp):
     transition=sum((-1)**k*C(y,k)*((1<<(previous-k))-1)**(number-x) for k in range(y+1))
     intermediate[x]+=C(number,x)*value*transition
   dp=[sum(value*C(number-y,x)*((1<<lower)-1)**(number-x) for y,value in enumerate(intermediate)) for x in range(number+1)]
  number=s[layer//2,layer//2+1]
  # Official explanation leaves this C-edge/loop terminal formula as an exercise.
  # Independent PIE: exclude k of y required vertices from all internal edges/loops.
  answer*=sum(value*sum((-1)**k*C(y,k)*(1<<((number-k)*(number-k+1)//2)) for k in range(y+1)) for y,value in enumerate(dp))
 return answer

def graph_languages():
 total=groups_total=profile_checks=0
 for n in range(2,6):
  edges=[(i,j) for i in range(n) for j in range(i,n)];groups={};h_to_word={}
  for mask in range(1<<len(edges)):
   adj=[[] for _ in range(n)];neighbors=[0]*n
   for k,(u,v) in enumerate(edges):
    if mask>>k&1:
     adj[u].append(v);neighbors[u]|=1<<v
     if u!=v:adj[v].append(u);neighbors[v]|=1<<u
   seen=1;q=[0]
   for x in q:
    for y in adj[x]:
     if not(seen>>y&1):seen|=1<<y;q.append(y)
   if seen!=(1<<n)-1:continue
   key=exact_infinite_walk_word(n,neighbors);h=profile(n,adj)
   if h in h_to_word:assert h_to_word[h]==key
   h_to_word[h]=key
   if key in groups:
    entry=groups[key];assert entry['profile']==h
    entry['count']+=1;entry['minimum']=min(entry['minimum'],mask.bit_count())
   else:groups[key]={'profile':h,'count':1,'minimum':mask.bit_count()}
   # Independently check parity minimum formula on the full eventual cycle plus prefix.
   current=1
   for length in range(4*n+5):
    # h reconstructs actual parity by the integer parity of each finite distance.
    reconstructed=0
    for x,(a,b) in enumerate(h):
     threshold=a if a%2==length%2 else b
     if threshold<INF and length>=threshold:reconstructed|=1<<x
    assert reconstructed==current;profile_checks+=1
    nxt=0
    for x in range(n):
     if current>>x&1:nxt|=neighbors[x]
    current=nxt
   total+=1
  for entry in groups.values():
   h=entry['profile'];assert greedy_minimum(h)==entry['minimum'],('min',n,h,greedy_minimum(h),entry)
   assert count_graphs(h)==entry['count'],('count',n,h,count_graphs(h),entry)
  groups_total+=len(groups)
 result['1117']={'allConnectedUndirectedGraphsWithOptionalLoopsN2to5':total,'completeInfiniteWalkLanguageGroups':groups_total,'literalParityFeasibilityComparisons':profile_checks,'oracle':'Enumerate EVERY labeled graph including loops/no parallel; group by the COMPLETE eventually-periodic sequence of literal exact-length reachable vertex bitsets (cycle detection, not an arbitrary length cutoff). Min edge count over the entire group is independent oracle for greedy.'}
 result['1118']={'allConnectedUndirectedGraphsWithOptionalLoopsN2to5':total,'completeInfiniteWalkLanguageGroups':groups_total,'oracle':'Group size in the same exhaustive infinite-language partition is independent graph-count oracle; compare bipartite formula, layered two-stage PIE, root exemption and independently derived terminal C-edge/loop PIE. Exact integers, not modulo coincidences.'}

def cows():
 arrays=triples=0
 for n in range(1,9):
  for a in itertools.product(range(1,min(3,n)+1),repeat=n):
   expected=0
   for l,m,r in itertools.combinations(range(n),3):
    frequencies=collections.Counter(a[l:r+1]);expected+=all(frequencies[a[x]]==1 for x in (l,m,r));triples+=1
   last={};second={};active=[0]*n;weight=[0]*n;actual=0
   for r,color in enumerate(a):
    previous=last.get(color,-1);before_previous=second.get(color,-1)
    actual+=sum(active[l]*weight[l] for l in range(previous+1,r))
    if previous>=0:active[previous]=0
    for l in range(max(previous,0),r):weight[l]+=1
    for l in range(max(before_previous,0),previous):weight[l]-=1
    active[r]=1
    for l in range(r+1):
     assert active[l]==(a[l:r+1].count(a[l])==1)
     assert weight[l]==sum(v==1 for v in collections.Counter(a[l+1:r+1]).values())
    second[color]=previous;last[color]=r
   assert actual==expected,('cows',a,actual,expected);arrays+=1
 result['1140']={'allArraysLength1to8AlphabetAtMost3':arrays,'allLeaderTriplesTested':triples,'oracle':'Enumerate ALL ordered-by-position leader triples l<m<r; directly count each leader breed in ENTIREdelegation l..r. Compare literal active/singleton interval-update equations (not a production lazy API), also check every intermediate active/weight invariant.'}

def frontier_count(n,edges,roles):
 adjacency=[[] for _ in range(n)];inside=[0]*n;back=[]
 for u,v in edges:
  adjacency[u].append(v);inside[v]+=1
  if u>v:back.append((u,v))
 starts=[u for u,v in back]+[-1]*(2-len(back));ends=[v for u,v in back]+[-1]*(2-len(back));identity={e:i for i,e in enumerate(back)}
 dp={tuple(ends):1}
 for i in range(n):
  degree=inside[i]+(roles[i]=='S');nxt=collections.Counter()
  for (j,k),value in dp.items():
   hits=[p for p,x in enumerate((j,k)) if x==i];ad=value*math.factorial(degree-len(hits))
   def put(x,y):
    if starts[0]<=i or x<=i:x=-1
    if starts[1]<=i or y<=i:y=-1
    nxt[x,y]+=ad
   if not hits:put(j,k);continue
   outgoing=adjacency[i]+([-1] if roles[i]=='R' else [])
   if hits==[0]:
    for x in outgoing:
     kind=identity.get((i,x),-1)
     if kind==0:continue
     if kind==1:put(k,-1)
     else:put(x,k)
   elif hits==[1]:
    for y in outgoing:
     kind=identity.get((i,y),-1)
     if kind==1:continue
     if kind==0:put(-1,j)
     else:put(j,y)
   else:
    for x in outgoing:
     for y in outgoing:
      if x==y:continue
      first=identity.get((i,x),-1);second=identity.get((i,y),-1)
      if first==0 or second==1:continue
      if first==1:
       if second==0:continue
       put(y,-1)
      elif second==0:put(-1,x)
      else:put(x,y)
  dp=nxt
 return dp.get((-1,-1),0)

def literal_trails(n,edges,roles):
 sources=[i for i,c in enumerate(roles) if c=='S'];receivers={i for i,c in enumerate(roles) if c=='R'}
 adjacency=[[] for _ in range(n)]
 for k,(u,v) in enumerate(edges):adjacency[u].append((v,k))
 full=(1<<len(edges))-1
 def next_sender(at,used,ended):
  if at==len(sources):return int(used==full and len(ended)==len(receivers))
  def walk(x,mask):
   answer=0
   if x in receivers and x not in ended:answer+=next_sender(at+1,mask,ended|{x})
   for y,edge in adjacency[x]:
    if not(mask>>edge&1):answer+=walk(y,mask|1<<edge)
   return answer
  return walk(sources[at],used)
 return next_sender(0,0,frozenset())

def routing():
 graphs=balanced=valid=cycle_only=schemes=0
 for n in range(2,5):
  all_edges=[(i,j) for i in range(n) for j in range(n) if i!=j]
  for mask in range(1<<len(all_edges)):
   edges=[e for i,e in enumerate(all_edges) if mask>>i&1]
   if sum(u>v for u,v in edges)>2:continue
   graphs+=1;diff=[0]*n
   for u,v in edges:diff[u]+=1;diff[v]-=1
   if any(abs(d)>1 for d in diff) or not any(d==1 for d in diff):continue
   roles=''.join('S' if d==1 else 'R' if d==-1 else '.' for d in diff);balanced+=1
   expected=literal_trails(n,edges,roles);actual=frontier_count(n,edges,roles)
   assert actual==expected,('routing',n,edges,roles,actual,expected)
   schemes+=expected;valid+=expected>0;cycle_only+=expected==0
 result['1141']={'allDirectedSimpleGraphsN2to4WithAtMostTwoBackwardEdges':graphs,'allDegreeBalancedRoleConfigurationsWithSender':balanced,'validInstances':valid,'balancedButNoValidScheme':cycle_only,'allLiteralTrailSchemes':schemes,'oracle':'For EVERY eligible graph, local degree balance uniquely determines S/R/. roles. Enumerate actual sender-to-unusedreceiver edge-disjoint directed TRAILS in fixed sender order, permitting repeated vertices, stopping at receivers optionally, accepting iff EVERY edge used once. Compare two-backedge frontier DP including single-path cycle closure, cross merger, double cross closure, receiver termination and deg-minus-tracked factorial.'}

def literal_shape(h,w,mask):
 if not mask:return False
 cells=[(i//w,i%w) for i in range(h*w) if mask>>i&1]
 for r in range(h):
  columns=[c for x,c in cells if x==r]
  if columns and max(columns)-min(columns)+1!=len(columns):return False
 for c in range(w):
  rows=[r for r,y in cells if y==c]
  if rows and max(rows)-min(rows)+1!=len(rows):return False
 seen={cells[0]};q=list(seen);present=set(cells)
 for r,c in q:
  for p in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
   if p in present and p not in seen:seen.add(p);q.append(p)
 return len(seen)==len(cells)

def endpoints_shape(h,w,mask):
 if not mask:return False
 intervals=[]
 for r in range(h):
  columns=[c for c in range(w) if mask>>(r*w+c)&1]
  if columns:
   if max(columns)-min(columns)+1!=len(columns):return False
   intervals.append((r,min(columns),max(columns)))
 left_inward=right_inward=False
 for (r,l,rr),(s,L,R) in zip(intervals,intervals[1:]):
  if s!=r+1 or L>rr or R<l:return False
  if left_inward and L<l:return False
  if right_inward and R>rr:return False
  left_inward|=L>l;right_inward|=R<rr
 return True

def subset_dp(n,grass):
 previous={};answer=0
 for row in range(n):
  current=collections.Counter()
  for L in range(n):
   for R in range(L,n):
    if any(not(grass>>(row*n+c)&1) for c in range(L,R+1)):continue
    current[L,R,0,0]+=1
    for (l,r,a,b),ways in previous.items():
     if L>r or R<l or (a and L<l) or (b and R>r):continue
     current[L,R,int(a or L>l),int(b or R<r)]+=ways
  answer+=sum(current.values());previous=current
 return answer

def balanced_subsets():
 shapes=0;tables={}
 for h in range(1,5):
  for w in range(1,5):
   for mask in range(1,1<<(h*w)):
    assert endpoints_shape(h,w,mask)==literal_shape(h,w,mask),('shape',h,w,mask);shapes+=1
 rng=random.Random(1142);cases=0
 for n in range(1,5):
  counts=[int(literal_shape(n,n,mask)) for mask in range(1<<(n*n))]
  for bit in range(n*n):
   for mask in range(1<<(n*n)):
    if mask>>bit&1:counts[mask]+=counts[mask^(1<<bit)]
  chosen=range(1<<(n*n)) if n<=3 else [0,(1<<(n*n))-1]+[rng.randrange(1<<(n*n)) for _ in range(1024)]
  for grass in chosen:assert subset_dp(n,grass)==counts[grass],('subsetdp',n,grass);cases+=1
 result['1142']={'everyNonemptyBitmapEveryH_W1to4':shapes,'allGrassBoardsN1to3AndRandom4':cases,'oracle':'Enumerate actual cell subsets and test literal occupied-row contiguity, occupied-column contiguity,4-neighbor BFS connectivity. Compare endpoint/unimodality characterization for EVERYsmallshape. Zeta sum over allvalidsubsets gives exact answer for eachgrassboard, independently checked against interval/two-strict-phase-flags DP. No prefix-sum optimization/API implemented in this research probe.'}

def raw_replay(entry,choices):
 graphs=json.loads((SNAPSHOT/'data/flows.json').read_text());by={g['id']:g for g in graphs}
 graph=by[entry];node=next(n for n in graph['nodes'] if n['id']==graph['root']);steps=[];routes=[];used=0
 for _ in range(256):
  if node['type']=='route':
   routes.append({'fromGraphId':graph['id'],'fromNodeId':node['id'],'toGraphId':node['graph']});graph=by[node['graph']];node=next(n for n in graph['nodes'] if n['id']==graph['root']);continue
  if used==len(choices):break
  assert node['type']=='question';answer=choices[used]
  options=node.get('options',[{'id':a,'label':{'yes':'はい','no':'いいえ','unknown':'わからない'}.get(a,a)} for a in node.get('answers',{})])
  option=next(x for x in options if x['id']==answer);steps.append({'graphId':graph['id'],'nodeId':node['id'],'question':node['title'],'answer':answer,'answerLabel':option['label']})
  next_id=node['answers'][answer];node=next(n for n in graph['nodes'] if n['id']==next_id);used+=1
 else:raise AssertionError('route cycle or excessive depth')
 assert used==len(choices)
 end={'graphId':graph['id'],'nodeId':node['id'],'type':node['type'],'title':node['title'],'options':node.get('options',[{'id':a,'label':{'yes':'はい','no':'いいえ','unknown':'わからない'}.get(a,a)} for a in node.get('answers',{})]),'techniques':node.get('techniques',[])}
 return steps,routes,end

def verify_frozen_audit():
 path=SITE/'data/corpus-audits/usaco-2021-february-us-open-platinum.json'
 assert path.exists()
 audit=json.loads(path.read_text());records=audit['records'];assert len(records)==6
 for r in records:
  steps,routes,end=raw_replay(r['entryGraphId'],r['choices']);assert steps==r['steps'];assert end==r['initialReached']==r['canonicalRouteEnd']
  gap=r['gap'];assert gap['firstMissingGraphId']==end['graphId'] and gap['firstMissingNodeId']==end['nodeId']
  assert gap['currentQuestion']==end['title'] and gap['currentOptions']==end['options']
  assert r['navigationReplay']['stepsSha256']==hashlib.sha256(json.dumps(steps,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
  assert routes==r['navigationReplay']['routeTransitions']
 ledger=json.loads((SNAPSHOT/'hashes-before.json').read_text());assert ledger==json.loads((SNAPSHOT/'hashes-after.json').read_text())
 for rel,sha in ledger.items():assert hashlib.sha256((SNAPSHOT/rel).read_bytes()).hexdigest()==sha
 assert audit['snapshot']['articleCount']==488 and audit['snapshot']['flowGraphCount']==455 and audit['snapshot']['walkCount']==509
 result['navigation']={'recordsReplayed':len(records),'questionsAndAnswerLabelsVerified':sum(len(r['steps']) for r in records),'frozenFilesShaRechecked':len(ledger),'allInitialReachedAndGapFieldsEqualFrozenNodes':True,'interpreter':'independent raw JSON graph/node/options/answers/route interpreter, no live data/runtime dependency'}

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
 with open_snapshot() as SNAPSHOT:
  for name,task in [('1116',no_time),('1117+1118',graph_languages),('1140',cows),('1141',routing),('1142',balanced_subsets)]:
   start=time.monotonic();task();print(name,'passed',round(time.monotonic()-start,6),flush=True,file=sys.stderr)
  verify_frozen_audit()
  result['seconds']=time.monotonic()-begin
  if args.output:args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
  print(json.dumps(result,ensure_ascii=False,indent=2))
