#!/usr/bin/env python3
"""Manual IOI2016 research checks; not production article/API validation.
Reads the immutable baseline and writes only an optional /tmp output path.
"""
from pathlib import Path
from collections import defaultdict
from functools import lru_cache
import bisect,hashlib,itertools,json,random,sys,time
from ioi_2016_snapshot import snapshot_baseline
_snapshot_holder,BASE=snapshot_baseline()
rng=random.Random(2016081420160816)
result={'scope':'IOI2016 fixed six competition tasks; independent research prototypes only','productionImplementationValidated':False}

def molecules():
    arrays=cases=subsets=0
    for n in range(1,9):
      for w in itertools.combinations_with_replacement(range(1,7),n):
        arrays+=1;sums={0}
        for v in w:sums|={x+v for x in sums}
        subsets+=1<<n
        for low in range(1,sum(w)+3):
          for width in sorted({w[-1]-w[0],w[-1]-w[0]+1,7}):
            high=low+width;left=total=0;answer=None
            for right,v in enumerate(w):
                total+=v
                while left<=right and total>high:total-=w[left];left+=1
                if low<=total<=high:answer=(left,right+1);break
            exact=any(low<=x<=high for x in sums)
            assert (answer is not None)==exact
            if answer:assert low<=sum(w[answer[0]:answer[1]])<=high
            cases+=1
    w=(2,3,7);low=high=9
    assert any(sum(w[i] for i in range(3) if mask>>i&1)==9 for mask in range(8))
    assert all(sum(w[a:b])!=9 for a in range(3) for b in range(a+1,4))
    result['molecules']={'allSortedWeightArraysN1to8Weights1to6':arrays,'allSubsetAssignmentsRepresented':subsets,'validRangeCases':cases,'missingGapGuardCounterexample':{'w':w,'l':low,'u':high,'arbitrarySubset':[0,2],'sortedContiguousWindowExists':False},'verified':'Positive sorted window search equals independent exact all-subset sum-set DP existence for all tested valid-width ranges. Cardinality window sums are monotone and jump by at most max−min<=u−l. Sorting retains original indices in future API.','unconfirmed':'Complete reusable C++20/API/invalid/overflow/full-scale checker not created.'}

class DSU:
    def __init__(self,n):self.p=list(range(n));self.size=[1]*n
    def root(self,v):
        while self.p[v]!=v:self.p[v]=self.p[self.p[v]];v=self.p[v]
        return v
    def join(self,a,b):
        a,b=self.root(a),self.root(b)
        if a==b:return False
        if self.size[a]<self.size[b]:a,b=b,a
        self.p[b]=a;self.size[a]+=self.size[b];return True

def railroad_fast(sections):
    sections=list(sections)+[(max(max(s,t) for s,t in sections),1)]
    x=sorted({v for edge in sections for v in edge});index={v:i for i,v in enumerate(x)};dsu=DSU(len(x));delta=[0]*len(x)
    for s,t in sections:a,b=index[s],index[t];delta[a]+=1;delta[b]-=1;dsu.join(a,b)
    balance=answer=0;optional=[]
    for i in range(len(x)-1):
        balance+=delta[i];gap=x[i+1]-x[i]
        answer+=max(0,balance)*gap
        if balance:dsu.join(i,i+1)
        else:optional.append((gap,i))
    for gap,i in sorted(optional):
        if dsu.join(i,i+1):answer+=gap
    assert len({dsu.root(i) for i in range(len(x))})==1
    return answer

def railroad():
    cases=orders=0
    def exact(edges):
        nonlocal orders
        best=10**30
        for order in itertools.permutations(range(len(edges))):
            cost=sum(max(0,edges[a][1]-edges[b][0]) for a,b in zip(order,order[1:]));best=min(best,cost);orders+=1
        return best
    for n in range(2,5):
      for edges in itertools.product(tuple(itertools.product(range(1,4),repeat=2)),repeat=n):
        assert railroad_fast(edges)==exact(edges);cases+=1
    randoms=0
    for it in range(160):
        n=rng.randrange(2,9);edges=[(rng.randrange(1,20),rng.randrange(1,20)) for _ in range(n)]
        assert railroad_fast(edges)==exact(edges);randoms+=1
    assert railroad_fast([(1,7),(4,3),(5,8),(6,6)])==3
    result['railroad']={'allSectionArraysN2to4Speeds1to3':cases,'randomN2to8':randoms,'literalSectionPermutations':orders,'verified':'Auxiliary maxspeed→1 edge, per-coordinate-cut balance correction and component MST equal ALL literal section orderings. Repeated endpoints/self-sections are included.','unconfirmed':'No production Euler/sweep/DSU C++ API, source-scale resource/overflow/exception/sanitizer validation yet.'}

def shortcut_bounds(x,d,c,k,fast):
    n=len(x)
    # Any two different branch endpoints remain at distance at least di+dj.
    # This guard makes every eligible distinct pair in the sweep satisfy i<j.
    if sum(sorted(d)[-2:])>k:return None
    low_sum=low_diff=-10**30;high_sum=high_diff=10**30
    a=[x[i]-d[i] for i in range(n)];b=[x[i]+d[i] for i in range(n)]
    extrema=[]
    if fast:
        order_a=sorted(range(n),key=lambda i:a[i]);order_b=sorted(range(n),key=lambda i:b[i]);at=0;min_a=[];max_b=[]
        for j in order_b:
            while at<n and a[order_a[at]]<b[j]-k:
                i=order_a[at];at+=1
                min_a=sorted(min_a+[(a[i],i)])[:2];max_b=sorted(max_b+[(b[i],i)],reverse=True)[:2]
            use_a=[v for v,i in min_a if i!=j];use_b=[v for v,i in max_b if i!=j]
            if use_a:
                aa,bb=use_a[0],use_b[0];extrema.append((a[j]+aa,b[j]+bb,a[j]-bb,b[j]-aa))
    else:
        for i in range(n):
          for j in range(i+1,n):
            if d[i]+d[j]+x[j]-x[i]>k:extrema.append((a[i]+a[j],b[i]+b[j],a[j]-b[i],b[j]-a[i]))
    for sa,sb,da,db in extrema:
        high_sum=min(high_sum,k-c+sa);low_sum=max(low_sum,c-k+sb)
        high_diff=min(high_diff,k-c+da);low_diff=max(low_diff,c-k+db)
    return low_sum,high_sum,low_diff,high_diff

def shortcut_feasible(x,bounds):
    if bounds is None:return False
    sl,sh,dl,dh=bounds;dl=max(dl,1)
    if sl>sh or dl>dh:return False
    # z >= max(sl-y,y+dl): V-shaped in sorted y. Its lower_bound pointer
    # has at most a decreasing and an increasing phase, for O(N) steps.
    j=bisect.bisect_left(x,max(sl-x[0],x[0]+dl))
    for i,y in enumerate(x):
        lower=max(sl-y,y+dl)
        while j>i+1 and x[j-1]>=lower:j-=1
        while j<len(x) and x[j]<lower:j+=1
        j=max(j,i+1)
        if j<len(x) and x[j]<=min(sh-y,y+dh):return True
    return False

def shortcut_literal(x,d,c):
    n=len(x);best=10**30
    for a in range(n):
      for b in range(a+1,n):
        # Literal augmented railway: main stations and actual branch leaves.
        m=n+sum(v>0 for v in d);dist=[[10**20]*m for _ in range(m)]
        for i in range(m):dist[i][i]=0
        for i in range(n-1):dist[i][i+1]=dist[i+1][i]=x[i+1]-x[i]
        dist[a][b]=dist[b][a]=min(dist[a][b],c);at=n
        for i,weight in enumerate(d):
            if weight:dist[i][at]=dist[at][i]=weight;at+=1
        for v in range(m):
          for i in range(m):
            for j in range(m):dist[i][j]=min(dist[i][j],dist[i][v]+dist[v][j])
        best=min(best,max(max(row) for row in dist))
    return best

def shortcut():
    cases=thresholds=0
    for n in range(2,5):
      for gaps in itertools.product((1,2),repeat=n-1):
       x=[0]
       for v in gaps:x.append(x[-1]+v)
       for d in itertools.product(range(3),repeat=n):
        for c in (1,3):
            exact=shortcut_literal(x,d,c);upper=max(d[i]+d[j]+x[j]-x[i] for i in range(n) for j in range(i+1,n))
            for k in range(upper+2):
                fast=shortcut_bounds(x,d,c,k,True);slow=shortcut_bounds(x,d,c,k,False)
                assert fast==slow,(x,d,c,k,fast,slow)
                assert shortcut_feasible(x,fast)==(exact<=k),(x,d,c,k,exact)
                thresholds+=1
            cases+=1
    randoms=0
    for it in range(1800):
        n=rng.randrange(2,11);x=[0]
        for _ in range(n-1):x.append(x[-1]+rng.randrange(1,20))
        d=[rng.randrange(60) for _ in range(n)];c=rng.randrange(1,60)
        exact=shortcut_literal(x,d,c)
        for k in {0,exact-1,exact,exact+1,rng.randrange(200)}:
            f=shortcut_bounds(x,d,c,k,True);s=shortcut_bounds(x,d,c,k,False)
            assert f==s;assert shortcut_feasible(x,f)==(exact<=k);thresholds+=1
        randoms+=1
    # A single long branch must not generate the nonexistent pair i=i.
    assert shortcut_literal([0,1],[100,0],1)==101
    result['shortcut']={'allSmallNetworksN2to4':cases,'randomN2to10':randoms,'decisionThresholdsCompared':thresholds,'verified':'All actual augmented-graph Floyd diameters over EVERY legal express endpoint pair equal rotated-square constraints AND independent O(N) decision sweep. GuardK>=topTwoBranchLengths implies eligible distinct i automatically i<j; exclude self with two extrema by different indices. Keep c in all four bounds. Discrete distinct endpoints use V-shaped lower-bound pointer. Sort x−d/x+d once, then binary answer in O(NlogN+NlogDiameter).','unconfirmed':'Research prototype sorts sweep order per invocation; production must cache sorting once. No full N1million implementation, exception/64bit/sanitizer/API validation yet.'}

def paint_prefix(s,c):
    n=len(s);k=len(c);white=[0]
    for ch in s:white.append(white[-1]+(ch=='_'))
    f=[[False]*(n+1) for _ in range(k+1)];f[0][0]=True
    for j in range(1,n+1):f[0][j]=f[0][j-1] and s[j-1]!='X'
    for i in range(1,k+1):
      for j in range(1,n+1):
        f[i][j]=s[j-1]!='X' and f[i][j-1];a=j-c[i-1]
        if a>=0 and white[j]==white[a] and (a==0 or s[a-1]!='X') and f[i-1][max(0,a-1)]:f[i][j]=True
    return f,white

def paint_dp(s,c):
    n=len(s);k=len(c);f,white=paint_prefix(s,c);back,_=paint_prefix(s[::-1],c[::-1]);assert f[k][n]
    can_white=[s[i]!='X' and any(f[t][i] and back[k-t][n-i-1] for t in range(k+1)) for i in range(n)]
    delta=[0]*(n+1)
    for t,length in enumerate(c):
      for a in range(n-length+1):
        b=a+length
        if white[a]!=white[b] or (a and s[a-1]=='X') or (b<n and s[b]=='X'):continue
        if f[t][max(0,a-1)] and back[k-t-1][max(0,n-b-1)]:delta[a]+=1;delta[b]-=1
    active=0;out=[]
    for i in range(n):
        active+=delta[i];black=active>0;assert black or can_white[i];out.append('?' if black and can_white[i] else 'X' if black else '_')
    return ''.join(out)

def clues(mask,n):
    a=[];run=0
    for i in range(n+1):
        if i<n and mask>>i&1:run+=1
        elif run:a.append(run);run=0
    return tuple(a)

def paint():
    cases=physical=0
    for n in range(1,9):
        observations={};full=(1<<n)-1
        for mask in range(1,1<<n):
            c=clues(mask,n)
            for known in range(1<<n):
                key=(c,mask&known,(full^mask)&known);old=observations.get(key,(0,0));observations[key]=(old[0]|mask,old[1]|(full^mask));physical+=1
        for (c,black,white),(canblack,canwhite) in observations.items():
            s=''.join('X' if black>>i&1 else '_' if white>>i&1 else '.' for i in range(n));exact=''.join('?' if (canblack>>i&1) and (canwhite>>i&1) else 'X' if canblack>>i&1 else '_' for i in range(n))
            assert paint_dp(s,c)==exact;cases+=1
    assert paint_dp('...._..._....',(3,1,1,3))=='?XX?_X_X_?XX?'
    result['paint']={'allConsistentCluesAndPartialRowsN1to8':cases,'literalFullSolutionRevealPairs':physical,'verified':'Prefix/suffix feasibility and per-block range marking equal color intersection/union across every literal full binary solution consistent with each observation, including mandatory black/white separation sentinels. O(NK), full K100/N200000 state bound identified.','unconfirmed':'No production reusable memory-bounded C++20/API, inconsistent-input policy, maximum/sanitizer validation yet.'}

def messy_solve(p):
    n=len(p);stored=set();writes=reads=0;compiled=False
    def write(l,r):
        nonlocal writes
        if r-l<=1:return
        mid=(l+r)//2
        for i in range(l,mid):
            s=['1']*n;s[l:r]=['0']*(r-l);s[i]='1';stored.add(''.join(s));writes+=1
        write(l,mid);write(mid,r)
    write(0,n);compiled=True;transformed={''.join(s[p[i]] for i in range(n)) for s in stored};answer=[-1]*n
    def read(l,r,positions):
        nonlocal reads
        if r-l==1:answer[positions[0]]=l;return
        left=[];right=[];s=['1']*n
        for v in positions:s[v]='0'
        for v in positions:
            s[v]='1';query=''.join(s);reads+=1
            (left if query in transformed else right).append(v);s[v]='0'
        mid=(l+r)//2;assert len(left)==mid-l and len(right)==r-mid
        read(l,mid,left);read(mid,r,right)
    assert compiled;read(0,n,list(range(n)));assert answer==list(p)
    return writes,reads,len(stored)

def messy():
    cases=0;maxcounts={}
    for n in (1,2,4,8):
      for p in itertools.permutations(range(n)):
        w,r,distinct=messy_solve(p);assert w==n*(n.bit_length()-1)//2 and r==n*(n.bit_length()-1) and distinct==w;cases+=1
    randoms=0
    for n in (32,128):
      for _ in range(200):
        p=list(range(n));rng.shuffle(p);w,r,distinct=messy_solve(p);assert distinct==w
        assert w<=({32:320,128:896}[n]) and r<=({32:320,128:896}[n]);maxcounts[str(n)]={'writes':w,'reads':r};randoms+=1
    result['messy']={'allPermutationsN1_2_4_8':cases,'randomOriginalN32_128':randoms,'exactCounts':maxcounts,'verified':'Literal compile maps output bit i to original bit p[i]; restored output is p, not inverse. Fixed precompile partition masks use outside ones and one left-half marker. Different levels have different weights, same-level blocks have disjoint zero supports. Exactly one compile after all writes; reads only later; worst448writes/896reads at128 fits strict full limits.','unconfirmed':'No callback-template C++20/state/error/source-scale resource validation yet; character operations O(N²logN), oracle calls O(NlogN).'}

def aliens_segments(points):
    kept=[]
    for a,b in sorted({(min(a,b),max(a,b)) for a,b in points},key=lambda v:(v[0],-v[1])):
        if not kept or b>kept[-1][1]:kept.append((a,b))
    return kept

def aliens_dp(points):
    intervals=aliens_segments(points);n=len(intervals);inf=10**30;f=[[inf]*(n+1) for _ in range(n+1)];f[0][0]=0
    for q in range(1,n+1):
      for i in range(q,n+1):
        for t in range(q-1,i):
            overlap=max(0,intervals[t-1][1]-intervals[t][0]+1) if t else 0
            f[q][i]=min(f[q][i],f[q-1][t]+(intervals[i-1][1]-intervals[t][0]+1)**2-overlap**2)
    return [f[q][n] for q in range(1,n+1)],intervals

def aliens_penalty(intervals,penalty):
    # Exact integer lexicographic (penalized cost, fewer photos) encoded byH.
    n=len(intervals);scale=n+1;z=[0]*(n+1);hull=[];front=0
    for i,(left,right) in enumerate(intervals):
        overlap=max(0,intervals[i-1][1]-left+1) if i else 0
        line=(-2*scale*(left-1),z[i]+scale*((left-1)**2-overlap**2+penalty)+1)
        while len(hull)-front>=2:
            a,b=hull[-2:]
            if (b[1]-a[1])*(b[0]-line[0])<(line[1]-b[1])*(a[0]-b[0]):break
            hull.pop()
        hull.append(line)
        while len(hull)-front>=2 and hull[front][0]*right+hull[front][1]>=hull[front+1][0]*right+hull[front+1][1]:front+=1
        z[i+1]=scale*right*right+hull[front][0]*right+hull[front][1]
    return z[-1]//scale,z[-1]%scale

def aliens_wqs(intervals,k,m):
    k=min(k,len(intervals));low=0;high=m*m
    while low<high:
        mid=(low+high)//2
        if aliens_penalty(intervals,mid)[1]<=k:high=mid
        else:low=mid+1
    return aliens_penalty(intervals,low)[0]-low*k

def aliens():
    grids=photo_sets=queries=convex=penalties=0
    for m in range(1,5):
        cells=[(a,b) for a in range(m) for b in range(a,m)];kinds=len(cells);allmask=(1<<kinds)-1
        photos=[]
        for a,b in cells:
            grid=sum(1<<(r*m+c) for r in range(a,b+1) for c in range(a,b+1));covered=sum(1<<i for i,(u,v) in enumerate(cells) if a<=u<=v<=b);photos.append((grid,covered))
        best=[[10**9]*(m+1) for _ in range(1<<kinds)]
        for subset in range(1<<kinds):
            q=subset.bit_count()
            if q>m:continue
            grid=covered=0
            for i,(g,cov) in enumerate(photos):
                if subset>>i&1:grid|=g;covered|=cov
            best[covered][q]=min(best[covered][q],grid.bit_count());photo_sets+=1
        # Superset min transform: literal photos may cover extra interest cells.
        for bit in range(kinds):
          for mask in range(1<<kinds):
            if not mask>>bit&1:
              for q in range(m+1):best[mask][q]=min(best[mask][q],best[mask|1<<bit][q])
        for mask in range(1,1<<kinds):
            points=[cell for i,cell in enumerate(cells) if mask>>i&1];f,kept=aliens_dp(points);grids+=1
            for i in range(1,len(f)-1):assert f[i-1]-f[i]>=f[i]-f[i+1];convex+=1
            for k in range(1,min(m,len(points))+1):
                literal=min(best[mask][:k+1]);assert f[min(k,len(f))-1]==literal;assert aliens_wqs(kept,k,m)==literal;queries+=1
            for penalty in range(m*m+1):
                exact=min((v+(i+1)*penalty,i+1) for i,v in enumerate(f));assert aliens_penalty(kept,penalty)==exact;penalties+=1
    randoms=0
    for _ in range(1400):
        m=rng.randrange(1,50);points=[(rng.randrange(m),rng.randrange(m)) for _ in range(rng.randrange(1,25))];f,kept=aliens_dp(points)
        for i in range(1,len(f)-1):assert 2*f[i]<=f[i-1]+f[i+1];convex+=1
        for k in range(1,len(f)+1):assert aliens_wqs(kept,k,m)==f[k-1];queries+=1
        for penalty in {0,1,m*m,rng.randrange(m*m+1)}:
            assert aliens_penalty(kept,penalty)==min((v+(i+1)*penalty,i+1) for i,v in enumerate(f));penalties+=1
        randoms+=1
    result['aliens']={'allNonemptyIntervalInterestSubsetsM1to4':grids,'literalSquarePhotoSubsets':photo_sets,'requestedPhotoLimitsCompared':queries,'discreteConvexityChecks':convex,'exactPenaltyAndTieComparisons':penalties,'randomM1to49':randoms,'verified':'Literal UNION of actual square cell bitmaps matches containment-filtered overlap-subtracted partition DP, monotone lower hull penalty DP, and integer penalty search. Pairwise Monge nested-edge exchange proves discrete convexity via rebalancing q−1/q+1 paths toq/q; lex encoded count selects fewer photos; integer slopes justify G(lambda)−lambda*k even count jumps.','unconfirmed':'No production 1e5/N/m1e6 API/128-bit cross arithmetic/tie/maximum/sanitizer validation yet. Research DP quadratic, penalty prototype linear hull, no completed article.'}

def main():
    start=time.perf_counter()
    manifest=json.loads((BASE/'manifest.json').read_text());assert manifest['rawCounts']['allTechniqueMdx']==504
    for p,digest in manifest['fullRawHashes'].items():assert hashlib.sha256((BASE/p).read_bytes()).hexdigest()==digest,p
    result['baseline']={'rawFilesVerified':len(manifest['fullRawHashes']),'coreRawFiles':manifest['coreRawFileCount'],'publicRawFiles':manifest['publicRawFileCount'],'initialCounts':manifest['rawCounts'],'ledgerSha256':manifest['ledgerSha256']}
    for fn in (molecules,railroad,shortcut,paint,messy,aliens):fn()
    result['elapsedSeconds']=time.perf_counter()-start
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
