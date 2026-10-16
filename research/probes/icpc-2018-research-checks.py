from collections import defaultdict
from functools import lru_cache
from fractions import Fraction
from itertools import product
from math import comb
import json, random
out={}

def compositions(n,d):
    if n==1:
        yield (d+1,)
    else:
        for e in range(d+1):
            for tail in compositions(n-1,d-e): yield (e+1,)+tail

checks=states=0
for n in range(1,7):
 for r in range(1,n+1):
  @lru_cache(None)
  def S(k,d):
   if d<0:return 0
   if k==0:return 0
   count=comb(k+d-1,d)
   if k<=r:return (k+d)*count
   return r*count+sum(comb(k,g)*S(k-g,d-k+g) for g in range(k+1))
  for d in range(9):
   cs=list(compositions(n,d)); brute=sum(sum(sorted(c,reverse=True)[:r]) for c in cs)
   assert brute==S(n,d),(n,d,r,brute,S(n,d))
   checks+=1
 for d in range(9):
  dist={(1,)*n:Fraction(1)}
  for step in range(d):
   nxt=defaultdict(Fraction)
   for a,p in dist.items():
    for k in range(n):
     b=list(a);b[k]+=1;nxt[tuple(b)]+=p*Fraction(a[k],n+step)
   dist=nxt
  assert len(dist)==comb(n+d-1,d)
  assert set(dist.values())=={Fraction(1,len(dist))}
  states+=len(dist)
out['D']={'correctedRecurrenceComparisons':checks,'exactUrnStates':states,'normalizationCounterexample':{'n':2,'d':1,'r':2,'compositions':[[1,2],[2,1]],'sumOverAllCompositions':6,'sketchPrintedBase':3},'note':'小規模の独立検査。大制約の浮動小数安定性や完成実装を検証したものではない。'}

# K: every positive degree target in a small bounded cube; all tree degree
# sequences are exactly positive compositions of 2n-2 (Pruefer multiplicities).
kchecks=0
for n in range(2,7):
 legal=list(compositions(n,n-2))
 for d in product(range(1,5),repeat=n):
  if sum(d)<2*n-2:continue
  budget=n-2;order=sorted(range(n),key=lambda i:d[i]);ans=[1]*n;kept=0
  for i in order:
   if d[i]-1>budget:break
   ans[i]=d[i];budget-=d[i]-1;kept+=1
  if budget:
   ans[order[kept]]+=budget
  optimum=max(sum(a==b for a,b in zip(d,t)) for t in legal)
  assert sum(ans)==2*n-2 and sum(a==b for a,b in zip(ans,d))==optimum
  kchecks+=1
out['K']={'degreeTargetVectorsCompared':kchecks,'maxN':6,'targetDegreeValues':'1..4','note':'目標次数の総和が2N-2以上の小規模ベクトルと、全ての木次数列を比較。完成木の出力実装は未作成。'}

# I: derivation D(j)>=x-j iff j+D(j)>=x, inclusive expiry.
rng=random.Random(20180419);ichecks=0
for _ in range(1000):
 w=rng.randrange(1,60);D=[rng.randrange(0,w+1) for _ in range(w)]
 for x in range(w):
  s=rng.randrange(x+1)
  brute=sum(D[x-i]>=i for i in range(1,s+1))
  active=sum(j+D[j]>=x for j in range(x-s,x))
  assert brute==active;ichecks+=1
out['I']={'activeIntervalComparisons':ichecks,'correctCondition':'j + D(j,y) >= x','inclusiveExpiry':'x=j+D(j,y) is still active','note':'任意run長の等式を検査。ASCII読取や全三角形列挙の完成コード検証ではない。'}

# H: two pointers on a circular matching versus every gap pair; include
# restrictions that cut endpoints can be chosen on different rectangle sides.
def matchings(seq):
 if not seq:yield [];return
 a=seq[0]
 for p in range(1,len(seq)):
  b=seq[p]
  for tail in matchings(seq[1:p]+seq[p+1:]):yield [(a,b)]+tail
hchecks=0
for n in range(1,6):
 m=2*n;sides=[(4*i)//m for i in range(m)]
 # A gap is a boundary interval; a gap spanning a corner allows either side.
 gap=[{sides[(i-1)%m],sides[i]} for i in range(m)]
 def distinct(a,b):return any(x!=y for x in gap[a%m] for y in gap[b%m])
 for pairs in matchings(list(range(m))):
  if any(sides[a]==sides[b] for a,b in pairs):continue
  owner=[0]*m
  for k,(a,b) in enumerate(pairs):owner[a]=owner[b]=k
  brute=False
  for s in range(m):
   for length in range(1,m):
    bits=[0]*n
    for z in range(s,s+length):bits[owner[z%m]]+=1
    if all(b==1 for b in bits) and distinct(s,s+length):brute=True
  count=[0]*n;t=0;found=False
  for s in range(m):
   while t<s+m and count[owner[t%m]]==0:
    count[owner[t%m]]+=1;t+=1
   if t-s==n and distinct(s,t):found=True
   count[owner[s%m]]-=1
  assert brute==found,(n,pairs)
  hchecks+=1
out['H']={'matchingInstancesCompared':hchecks,'maxWires':5,'note':'境界endpointの巡回順とgapの側選択を検査。実数座標出力や1e-6回避の完成コード検証ではない。'}

# A reverse events: read arrivals before same-time departure commits, and
# compute all candidates at one station/time from the same old baseline.
def reverse(n,buses):
 P=[Fraction(i==1) for i in range(n)];q=[Fraction(0)]*len(buses)
 for t in sorted({b[2] for b in buses}|{b[3] for b in buses},reverse=True):
  for i,(u,v,s,e,p) in enumerate(buses):
   if e==t:q[i]=P[v]
  new=P.copy()
  for i,(u,v,s,e,p) in enumerate(buses):
   if s==t:new[u]=max(new[u],p*q[i]+(1-p)*P[u])
  P=new
 return P[0]
def brute(n,buses):
 @lru_cache(None)
 def solve(u,earliest):
  if u==1:return Fraction(1)
  times=sorted({s for a,v,s,e,p in buses if a==u and s>=earliest})
  if not times:return Fraction(0)
  t=times[0];later=solve(u,t+1)
  return max([later]+[p*solve(v,e+1)+(1-p)*later for a,v,s,e,p in buses if a==u and s==t])
 return solve(0,0)
achecks=0
for _ in range(1500):
 n=rng.randrange(2,6);buses=[]
 for j in range(rng.randrange(1,10)):
  s=rng.randrange(0,8);e=rng.randrange(s+1,10)
  buses.append((rng.randrange(n),rng.randrange(n),s,e,Fraction(rng.randrange(5),4)))
 assert reverse(n,buses)==brute(n,buses),(n,buses)
 achecks+=1
out['A']={'reverseEventVsRecursiveDecisionInstances':achecks,'note':'独立な小規模有理数比較。同時刻乗換禁止・同時刻一便選択を含む。最大制約や完成実装は未検証。'}
print(json.dumps(out,ensure_ascii=False,indent=2))
