#!/usr/bin/env python3
"""Audit probes only: literal small-domain oracles, not published technique implementations."""
import itertools,collections,heapq,json,time,random,math,sys
from pathlib import Path
out={};started=time.monotonic()

def combo(secret):
 n=len(secret);count=0;longest=0
 def press(p):
  nonlocal count,longest
  count+=1;longest=max(longest,len(p));assert len(p)<=4*n
  return max(k for k in range(n+1) if secret[:k] in p)
 first=('A' if press('A') else 'B') if press('AB') else ('X' if press('X') else 'Y')
 s=first;chars=[c for c in 'ABXY' if c!=first]
 while len(s)<n-1:
  a,b,c=chars;p=s+a+a+s+a+b+s+a+c+s+b;q=press(p)
  s+=a if q>=len(s)+2 else b if q==len(s)+1 else c
 if len(s)<n:
  s+=chars[0] if press(s+chars[0])==n else chars[1] if press(s+chars[1])==n else chars[2]
 assert s==secret and count<=n+2
 return count,longest
count=0;maxq=0
for n in range(1,9):
 for first in 'ABXY':
  for tail in itertools.product([c for c in 'ABXY' if c!=first],repeat=n-1):
   q,_=combo(first+''.join(tail));maxq=max(maxq,q);count+=1
out['combo']={'allLegalStringsLength1to8':count,'largestQueries':maxq,'oracle':'literal longest secret prefix that occurs as substring'}
print('combo',out['combo'],flush=True)

def corner_counts(h,w,mask):
 c1=c3=0
 for r in range(h+1):
  for c in range(w+1):
   k=sum(0<=rr<h and 0<=cc<w and bool(mask>>(rr*w+cc)&1) for rr in (r-1,r) for cc in (c-1,c))
   c1+=k==1;c3+=k==3
 return c1,c3
corner_cases=0
for h in range(1,5):
 for w in range(1,5):
  for mask in range(1,1<<(h*w)):
   ps=[(i//w,i%w) for i in range(h*w) if mask>>i&1]
   area=(max(r for r,c in ps)-min(r for r,c in ps)+1)*(max(c for r,c in ps)-min(c for r,c in ps)+1)
   c1,c3=corner_counts(h,w,mask)
   assert c1>=4 and ((c1+c3==4)==(area==len(ps)))
   corner_cases+=1
seat_swaps=0;perms=0
for h,w in [(1,1),(1,2),(1,3),(2,1),(3,1),(2,2),(2,3),(3,2)]:
 p=h*w
 def local(grid,r,c):
  nums=sorted(grid[rr*w+cc] if 0<=rr<h and 0<=cc<w else p for rr in (r-1,r) for cc in (c-1,c))
  return [(nums[0],nums[1]),(nums[2],nums[3])]
 for perm in itertools.permutations(range(p)):
  grid=list(perm);score=[0]*p
  for r in range(h+1):
   for c in range(w+1):
    for a,b in local(grid,r,c):
     for t in range(a,b):score[t]+=1
  for a,b in itertools.combinations(range(p),2):
   touched={(r,c) for at in (a,b) for r in (at//w,at//w+1) for c in (at%w,at%w+1)}
   fresh=score[:]
   for r,c in touched:
    for lo,hi in local(grid,r,c):
     for t in range(lo,hi):fresh[t]-=1
   grid[a],grid[b]=grid[b],grid[a]
   for r,c in touched:
    for lo,hi in local(grid,r,c):
     for t in range(lo,hi):fresh[t]+=1
   locations=[None]*p
   for at,v in enumerate(grid):locations[v]=(at//w,at%w)
   direct=0
   for t in range(p):
    pts=locations[:t+1];area=(max(r for r,c in pts)-min(r for r,c in pts)+1)*(max(c for r,c in pts)-min(c for r,c in pts)+1)
    direct+=area==t+1
   assert min(fresh)==4 and fresh.count(4)==direct
   grid[a],grid[b]=grid[b],grid[a];seat_swaps+=1
  perms+=1
out['seats']={'allNonemptyBitmapsUpTo4x4':corner_cases,'permutations':perms,'everySwap':seat_swaps,'oracle':'bbox area == cardinality for each label prefix; no corner criterion used by oracle'}
print('seats',out['seats'],flush=True)

def connected(n,edges):
 adj=[[] for _ in range(n)]
 for i,(a,b) in enumerate(edges):adj[a].append((b,i));adj[b].append((a,i))
 seen={0};q=[0]
 for v in q:
  for u,_ in adj[v]:
   if u not in seen:seen.add(u);q.append(u)
 return adj if len(seen)==n else None

def merge_tree(n,adj,ascending):
 parent=list(range(n));root=list(range(n));children=[[] for _ in range(n)];active=[False]*n;component={}
 def find(v):
  while parent[v]!=v:parent[v]=parent[parent[v]];v=parent[v]
  return v
 for threshold in range(n) if ascending else range(n-1,-1,-1):
  v=threshold;active[v]=True
  for u,_ in adj[v]:
   if active[u]:
    a,b=find(v),find(u)
    if a!=b:
     node=len(children);children.append([root[a],root[b]]);parent[b]=a;root[a]=node
  for s in range(n):
   if active[s]:component[threshold,s]=root[find(s)]
 intervals=[None]*len(children);position=[None]*n;counter=0
 def dfs(v):
  nonlocal counter
  lo=counter
  if not children[v]:position[v]=counter;counter+=1
  else:
   for u in children[v]:dfs(u)
  intervals[v]=(lo,counter)
 dfs(root[find(0)])
 return component,intervals,position

def wolf_queries(n,adj):
 low,li,x=merge_tree(n,adj,False);high,hi,y=merge_tree(n,adj,True)
 queries=[];rectangles=[]
 for s in range(n):
  for e in range(n):
   if s==e:continue
   for l in range(s+1):
    for r in range(e,n):
     if l<=r:
      queries.append((s,e,l,r));rectangles.append((*li[low[l,s]],*hi[high[r,e]]))
 events=[]
 for i,(xl,xr,yl,yr) in enumerate(rectangles):events.extend([(xl,i,-1,yl,yr),(xr,i,1,yl,yr)])
 events.sort();points=sorted(zip(x,y));tree=[0]*(n+1);result=[0]*len(queries);at=0
 def pref(end):
  ans=0
  while end:ans+=tree[end];end-=end&-end
  return ans
 for xx,i,sgn,yl,yr in events:
  while at<n and points[at][0]<xx:
   yy=points[at][1]+1
   while yy<=n:tree[yy]+=1;yy+=yy&-yy
   at+=1
  result[i]+=sgn*(pref(yr)-pref(yl))
 for (s,e,l,r),got in zip(queries,result):
  # Literal 2-layer state reachability, with exactly one irreversible transformation.
  seen={(s,0)};q=[(s,0)]
  for v,f in q:
   nxt=[(u,f) for u,_ in adj[v] if u>=l] if f==0 else [(u,f) for u,_ in adj[v] if u<=r]
   if f==0 and v<=r:nxt.append((v,1))
   for z in nxt:
    if z not in seen:seen.add(z);q.append(z)
  assert bool(got)==((e,1) in seen)
 return len(queries)

wolf_graphs=wolf_count=0
for n in range(2,6):
 all_edges=list(itertools.combinations(range(n),2))
 for mask in range(1<<len(all_edges)):
  edges=[e for i,e in enumerate(all_edges) if mask>>i&1];adj=connected(n,edges)
  if adj:
   wolf_count+=wolf_queries(n,adj);wolf_graphs+=1
out['werewolf']={'allConnectedSimpleGraphsN2to5':wolf_graphs,'allValidQueries':wolf_count,'oracle':'direct two-form BFS versus two activation trees + Euler rectangles + independent Fenwick sweep'}
print('werewolf',out['werewolf'],flush=True)

def doll(a,m):
 k=len(a)+1;p=1<<(k-1).bit_length();height=(p-1).bit_length();dead=p-k
 target={};at=0;seq=list(a)+[0]
 for i in range(p):
  leaf=int(f'{i:0{height}b}'[::-1],2)
  if leaf>=dead:target[leaf]=seq[at];at+=1
 x=[];y=[]
 def make(lo,hi):
  if hi<=dead:return -1
  if hi-lo==1:return target[lo]
  node=len(x);x.append(0);y.append(0);mid=(lo+hi)//2
  x[node]=make(lo,mid);y[node]=make(mid,hi)
  return -node-1
 root=make(0,p);assert root==-1
 state=[0]*len(x);vertex=root;seen=[];changes=0
 while vertex!=0:
  if vertex>0:seen.append(vertex);vertex=root
  else:
   i=-vertex-1;vertex=y[i] if state[i] else x[i];state[i]^=1;changes+=1
  assert changes<=p*height
 assert seen==list(a) and not any(state)
 expected=len(a)-len(a).bit_count()+height
 assert len(x)==expected and len(x)<=len(a)+math.log2(len(a)) and changes<=20000000
 return len(x),changes
cases=0
for n in range(1,9):
 for a in itertools.product([1,2],repeat=n):doll(a,2);cases+=1
large_s,large_changes=doll([1+i%100000 for i in range(200000)],100000)
out['doll']={'allTwoTriggerSequencesLength1to8':cases,'maximumN':200000,'maximumM':100000,'switchesAtMaximum':large_s,'changesAtMaximum':large_changes,'oracle':'literal toggle state machine until first origin return; exact trigger sequence and every final switch checked'}
print('doll',out['doll'],flush=True)

def highway(n,edges,adj,s,t,a,b):
 calls=0
 def ask(heavy):
  nonlocal calls
  calls+=1;distance=[10**30]*n;distance[s]=0;heap=[(0,s)]
  while heap:
   d,v=heapq.heappop(heap)
   if d!=distance[v]:continue
   if v==t:return d
   for u,i in adj[v]:
    nd=d+(b if heavy[i] else a)
    if nd<distance[u]:distance[u]=nd;heapq.heappush(heap,(nd,u))
 baseline=ask([False]*len(edges));lo=0;hi=len(edges)-1
 while lo<hi:
  mid=(lo+hi)//2
  if ask([i<=mid for i in range(len(edges))])>baseline:hi=mid
  else:lo=mid+1
 pivot=lo;u,v=edges[pivot]
 def bfs(root):
  d=[-1]*n;d[root]=0;q=[root]
  for x in q:
   for y,_ in adj[x]:
    if d[y]<0:d[y]=d[x]+1;q.append(y)
  return d
 du,dv=bfs(u),bfs(v)
 groups=[[i for i in range(n) if du[i]<dv[i]],[i for i in range(n) if dv[i]<du[i]]]
 trees=[];kept={pivot}
 for root,group in zip((u,v),groups):
  allowed=set(group);order=[root];parentedge={root:None};done={root}
  for z in order:
   for w,i in adj[z]:
    if w in allowed and w not in done:done.add(w);order.append(w);parentedge[w]=i;kept.add(i)
  assert len(order)==len(group);trees.append((order,parentedge))
 answers=[]
 for order,pe in trees:
  lo=0;hi=len(order)-1
  while lo<hi:
   mid=(lo+hi)//2;heavy=[i not in kept for i in range(len(edges))]
   for z in order[mid+1:]:heavy[pe[z]]=True
   if ask(heavy)>baseline:lo=mid+1
   else:hi=mid
  answers.append(order[lo])
 assert set(answers)=={s,t}
 return calls
highway_graphs=highway_cases=highway_maxq=0
for n in range(2,6):
 es=list(itertools.combinations(range(n),2))
 for mask in range(1<<len(es)):
  edges=[e for i,e in enumerate(es) if mask>>i&1];adj=connected(n,edges)
  if not adj:continue
  highway_graphs+=1
  for s,t in itertools.combinations(range(n),2):
   for a,b in [(1,2),(3,4),(1,1000000000)]:
    q=highway(n,edges,adj,s,t,a,b);highway_cases+=1;highway_maxq=max(highway_maxq,q)
max_split=max(((a-1).bit_length()+(90000-a-1).bit_length(),a) for a in range(1,90000))
assert max_split[0]==32 and (130000-1).bit_length()==17
out['highway']={'allConnectedSimpleGraphsN2to5':highway_graphs,'allPairsTimesThreeTollSettings':highway_cases,'maximumQueriesSmall':highway_maxq,'maximumSplitCeilLogsAtN90000':max_split[0],'fullQueryBound':1+17+32,'oracle':'Dijkstra on each actual queried A/B weighting; answer pair checked, no shortest-path-tree assumption in oracle'}
print('highway',out['highway'],flush=True)

def meetings_tables(h,priority=None):
 n=len(h);priority=list(range(n)) if priority is None else priority;nodes={};prefix={}
 def visit(l,r):
  if l==r:return None
  v=max(range(l,r),key=lambda i:(h[i],priority[i]));left=visit(l,v);right=visit(v+1,r)
  old=prefix[left] if left is not None else []
  rv=prefix[right] if right is not None else []
  lc=old[-1] if old else 0;cur=old+[lc+h[v]];delta=[]
  for k,val in enumerate(rv,1):
   f=lc+(k+1)*h[v];g=(v-l+1)*h[v]+val;cur.append(min(f,g));delta.append(f-g)
  assert delta==sorted(delta)
  prefix[v]=cur;nodes[v]=(l,r,left,right)
  return v
 visit(0,n);return nodes,prefix
arrays=queries=prefix_checks=0
for n in range(1,8):
 for tup in itertools.product(range(1,4),repeat=n):
  h=list(tup);nodes,prefs=meetings_tables(h);rn,rp=meetings_tables(h[::-1],list(range(n-1,-1,-1)));arrays+=1
  def direct(l,r):return min(sum(max(h[min(i,x):max(i,x)+1]) for i in range(l,r+1)) for x in range(l,r+1))
  for v,(l,r,le,ri) in nodes.items():
   for k,val in enumerate(prefs[v]):assert val==direct(l,l+k);prefix_checks+=1
  def oriented(vals,nodes,pref,l,r,priority):
   v=max(range(l,r+1),key=lambda i:(vals[i],priority[i]));value=(v-l+1)*vals[v]
   if v<r:value+=pref[nodes[v][3]][r-v-1]
   return value
  for l in range(n):
   for r in range(l,n):
    got=min(oriented(h,nodes,prefs,l,r,list(range(n))),oriented(h[::-1],rn,rp,n-1-r,n-1-l,list(range(n-1,-1,-1))))
    assert got==direct(l,r),(h,l,r,got,direct(l,r),nodes,prefs,rn,rp);queries+=1
out['meetings']={'allHeightArraysN1to7Values1to3':arrays,'allIntervalQueries':queries,'allCartesianPrefixEntries':prefix_checks,'equalHeightsIncluded':True,'oracle':'enumerate every meeting site and every participant, take literal intervening maximum; vector DP and one-cross inequality checked'}
print('meetings',out['meetings'],flush=True)
out['seconds']=time.monotonic()-started
if len(sys.argv)>1:
 Path(sys.argv[1]).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PASS',json.dumps(out),flush=True)
