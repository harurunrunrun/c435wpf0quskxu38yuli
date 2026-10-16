#!/usr/bin/env python3
"""Audit-only independent small checks; this is not a reusable article implementation."""
import itertools,json,time

def connected_masks(adj):
 n=len(adj); ok=[False]*(1<<n)
 for mask in range(1,1<<n):
  seen=0; todo=mask&-mask
  while todo:
   b=todo&-todo;todo-=b
   if seen&b:continue
   seen|=b;todo|=adj[b.bit_length()-1]&mask&~seen
  ok[mask]=seen==mask
 return ok

def split_method(adj,a,b,c):
 n=len(adj);tin=[-1]*n;low=[0]*n;parent=[-1]*n;sub=[0]*n;children=[[] for _ in adj];clock=0
 def dfs(v):
  nonlocal clock
  tin[v]=low[v]=clock;clock+=1;sub[v]=1<<v
  bits=adj[v]
  while bits:
   z=bits&-bits;bits-=z;u=z.bit_length()-1
   if u==parent[v]:continue
   if tin[u]<0:
    parent[u]=v;children[v].append(u);dfs(u);sub[v]|=sub[u];low[v]=min(low[v],low[u])
   else:low[v]=min(low[v],tin[u])
 dfs(0)
 v=0
 while True:
  nxt=next((u for u in children[v] if sub[u].bit_count()>=a),None)
  if nxt is None:break
  v=nxt
 p=sub[v];q=((1<<n)-1)^p
 for u in children[v]:
  if q.bit_count()>=a:break
  if low[u]<tin[v] and p.bit_count()-sub[u].bit_count()>=a:
   p^=sub[u];q|=sub[u]
 if min(p.bit_count(),q.bit_count())<a:return None
 if p.bit_count()>q.bit_count():p,q=q,p
 def grow(mask,count):
  seen=0;todo=mask&-mask
  while seen.bit_count()<count:
   z=todo&-todo;todo-=z
   if seen&z:continue
   seen|=z;todo|=adj[z.bit_length()-1]&mask&~seen
  return seen
 aa,bb=grow(p,a),grow(q,b)
 return aa,bb,((1<<n)-1)^(aa|bb)

start=time.time(); graphs=0;cases=0
for n in range(3,7):
 pairs=list(itertools.combinations(range(n),2));allmask=(1<<n)-1
 for code in range(1<<len(pairs)):
  adj=[0]*n
  for j,(u,v) in enumerate(pairs):
   if code>>j&1:adj[u]|=1<<v;adj[v]|=1<<u
  ok=connected_masks(adj)
  if not ok[allmask]:continue
  graphs+=1
  for a in range(1,n):
   for b in range(a,n):
    c=n-a-b
    if c<b:continue
    # Literal three-way assignments and at-least-two connected sets.
    expected=False
    for aa in range(1,allmask):
     if aa.bit_count()!=a:continue
     remaining=allmask^aa;bb=remaining
     while bb:
      if bb.bit_count()==b and sum((ok[aa],ok[bb],ok[remaining^bb]))>=2:expected=True;break
      bb=(bb-1)&remaining
     if expected:break
    result=split_method(adj,a,b,c);cases+=1
    assert (result is not None)==expected,(n,code,a,b,c)
    if result:
     aa,bb,cc=result
     assert (aa.bit_count(),bb.bit_count(),cc.bit_count())==(a,b,c)
     assert aa&bb==0 and aa|bb|cc==allmask and sum((ok[aa],ok[bb],ok[cc]))>=2
vision=0
for h in range(1,7):
 for w in range(1,7):
  cells=list(itertools.product(range(h),range(w)));d=h+w-1
  for x,y in itertools.combinations(cells,2):
   arrays=[]
   for family in [0,1]:
    occ=[False]*d
    for r,c in [x,y]:occ[r+c if family==0 else r-c+w-1]=True
    pref=[]
    for z in occ:pref.append(z or (pref[-1] if pref else False))
    arrays.append((occ,pref))
   def too_far(bound):
    return any(occ[i] and pref[i-bound-1] for occ,pref in arrays for i in range(bound+1,d))
   for k in range(1,h+w+2):
    actual=too_far(k-1) and not too_far(k)
    expected=abs(x[0]-y[0])+abs(x[1]-y[1])==k
    assert actual==expected,(h,w,x,y,k)
    vision+=1
print(json.dumps({'splitConnectedGraphs':graphs,'splitSortedSizeCases':cases,'visionAllPixelPairAndKCases':vision,'seconds':time.time()-start}))
