#!/usr/bin/env python3
"""Manual research checks only: not a production C++20/API validation.
Usage: python3 flowchartcp-ioi2017-probe.py [optional-new-output.json]
Reads retained permanent snapshots and their raw manifest; borrows only a local compiler matching its frozen SHA. Never changes shared files or saved audit outputs.
"""
from pathlib import Path
from collections import deque
from functools import lru_cache
import hashlib,heapq,itertools,json,math,random,sys,time,subprocess,tempfile,gzip,shutil,base64,os
SITE=Path(__file__).resolve().parents[2]
MANIFEST=json.loads((SITE/'research/snapshots/ioi-2017-manifest.json').read_text())
BASE=None
RETAINED_COUNT=0
result={'scope':'fixed IOI2017 six competition tasks; limited independent research checks, not completed article/API tests','productionImplementationValidated':False}
rng=random.Random(2017073020170801)

def nowruz():
    boards=attempts=transitions=nonoptimal=0;witness=None;connected_witness=None
    for h in range(1,4):
      for w in range(1,4):
        n=h*w;adj=[sum(1<<(rr*w+cc) for rr,cc in [(r-1,c),(r+1,c),(r,c-1),(r,c+1)] if 0<=rr<h and 0<=cc<w) for r in range(h) for c in range(w)]
        def validate(mask):
            if not mask:return False,0
            seen=mask&-mask;queue=[seen.bit_length()-1]
            for v in queue:
                new=adj[v]&mask&~seen;seen|=new
                while new:b=new&-new;new-=b;queue.append(b.bit_length()-1)
            edges=sum((adj[v]&mask).bit_count() for v in range(n) if mask>>v&1)//2
            leaves=sum((adj[v]&mask).bit_count()==1 for v in range(n) if mask>>v&1)
            return seen==mask and edges==mask.bit_count()-1,leaves
        trees=[(mask,validate(mask)[1]) for mask in range(1,1<<n) if validate(mask)[0]]
        for free in range(1,1<<n):
            boards+=1;best=max(leaves for mask,leaves in trees if mask&free==mask)
            # Valid growth, deliberately NO optimality/full-score claim.
            marked=free&-free;attempts+=1
            while True:
                candidates=[v for v in range(n) if free>>v&1 and not marked>>v&1 and (adj[v]&marked).bit_count()==1]
                if not candidates:break
                v=candidates[0];before=validate(marked)[1];parent=(adj[v]&marked).bit_length()-1;d=(adj[parent]&marked).bit_count();marked|=1<<v
                valid,after=validate(marked);assert valid and after-before==1+(d==0)-(d==1);transitions+=1
            valid,leaves=validate(marked);assert valid and marked&free==marked and leaves<=best
            if (h,w,free)==(2,3,63):
                assert (marked,leaves,best)==(47,2,3);connected_witness={"h":h,"w":w,"freeMask":free,"greedyMask":marked,"greedyLeaves":leaves,"optimalLeaves":best}
            if leaves<best:
                nonoptimal+=1
                if witness is None:witness={'h':h,'w':w,'freeMask':free,'greedyMask':marked,'greedyLeaves':leaves,'optimalLeaves':best}
    result['nowruz']={'allNonemptyFreeBoardsH_W1to3':boards,'growthRuns':attempts,'exactlyOneNeighborInsertionsChecked':transitions,'nonOptimalFixedOrderRuns':nonoptimal,'counterexample':witness,'connectedFullGridCounterexample':connected_witness,'verified':'Adding a free cell with exactly one existing marked neighbor preserves induced connected acyclicity; leaf delta checked literally including singleton->2vertices. Exact all-subset tree oracle bounds quality.','unconfirmed':'Official ten output files were not retrieved/solved. This growth method has no full-score guarantee; no invented optimum or 100-point claim.'}

def wiring_linear(x,colors):
    n=len(x);starts=[0]+[i for i in range(1,n) if colors[i]!=colors[i-1]]+[n]
    inf=10**30;dp=[inf]*(n+1);dp[0]=0
    for block in range(1,len(starts)-1):
        p,q,r=starts[block-1:block+2];a=q-p
        first,last=x[q],x[q-1];u=[inf]*(a+2);v=[inf]*(a+1);sum_a=0
        for k in range(1,a+1):
            sum_a+=x[q-k];previous=min(dp[q-k],dp[q-k+1])
            u[k]=previous+k*first-sum_a
            v[k]=min(v[k-1],previous+k*last-sum_a)
        for k in range(a-1,0,-1):u[k]=min(u[k],u[k+1])
        sum_b=0
        for j in range(1,r-q+1):
            sum_b+=x[q+j-1];best=v[min(j,a)]-j*last
            if j<=a:best=min(best,u[j]-j*first)
            dp[q+j]=sum_b+best
    return dp[-1]

def wiring():
    cases=assignments=0
    for n in range(2,8):
      for colors in itertools.product(range(2),repeat=n):
        if min(colors)==max(colors):continue
        for profile in range(2):
            x=[];cur=0
            for i in range(n):cur+=1 if profile==0 else 1+(i*i+3*i)%5;x.append(cur)
            red=[x[i] for i in range(n) if colors[i]==0];blue=[x[i] for i in range(n) if colors[i]==1]
            inf=10**9;dp=[[inf]*(len(blue)+1) for _ in range(len(red)+1)];dp[0][0]=0
            for i in range(1,len(red)+1):
              for j in range(1,len(blue)+1):dp[i][j]=min(dp[i-1][j],dp[i][j-1],dp[i-1][j-1])+abs(red[i-1]-blue[j-1])
            block=[0]*n
            for i in range(1,n):block[i]=block[i-1]+(colors[i]!=colors[i-1])
            edges=[(i,j,abs(x[i]-x[j]),abs(block[i]-block[j])==1) for i in range(n) for j in range(i+1,n) if colors[i]!=colors[j]]
            best=adjacent=inf
            for mask in range(1<<len(edges)):
                covered=cost=0;allowed=True
                for k,(i,j,weight,near) in enumerate(edges):
                    if mask>>k&1:covered|=1<<i|1<<j;cost+=weight;allowed&=near
                assignments+=1
                if covered==(1<<n)-1:
                    best=min(best,cost)
                    if allowed:adjacent=min(adjacent,cost)
            assert dp[-1][-1]==best==adjacent==wiring_linear(x,colors);cases+=1
    random_cases=0
    for _ in range(1000):
        n=rng.randrange(2,50);colors=[rng.randrange(2) for _ in range(n)];colors[0]=0;colors[-1]=1;x=[];cur=0
        for _ in range(n):cur+=rng.randrange(1,100);x.append(cur)
        red=[x[i] for i in range(n) if colors[i]==0];blue=[x[i] for i in range(n) if colors[i]==1];dp=[[10**20]*(len(blue)+1) for _ in range(len(red)+1)];dp[0][0]=0
        for i in range(1,len(red)+1):
            for j in range(1,len(blue)+1):dp[i][j]=min(dp[i-1][j],dp[i][j-1],dp[i-1][j-1])+abs(red[i-1]-blue[j-1])
        assert wiring_linear(x,colors)==dp[-1][-1];random_cases+=1
    assert wiring_linear(list(range(200000)),[0]*100000+[1]*100000)==10**10
    assert wiring_linear(list(range(200000)),[i%2 for i in range(200000)])==100000
    x=list(range(100000))+list(range(999900001,1000000001))
    assert wiring_linear(x,[0]*100000+[1]*100000)==99990000100000
    result['wiring']={'allTwoColorSequencesLength2to7TwoCoordinateProfiles':cases,'allBipartiteEdgeSubsets':assignments,'randomLinearVsQuadraticN2to49':random_cases,'maximumCombinedN200000Cases':3,'verified':'Independent literal all-edge-set minimum equals quadratic prefix DP AND new fully-derived linear monochromatic-block prefix/suffix minima DP. Adjacent-block exclusion and one-overlap split prove recurrence; separated-group edge-cover closed form is attained by stars. Three maximum-size exact closed-form families checked.','unconfirmed':'Production reusable C++20/API/overflow/exception/sanitizer validation has not been performed. The official editorial supplies only the high-level linear DP; explicit recurrence/proof here is an independent supplement.'}

def train_solution(out,owner,charge):
    n=len(out);active=set(range(n));rounds=0
    def attract(target,player):
        reached=set(target)
        while True:
            new={v for v in active-reached if (any(w in reached for w in out[v] if w in active) if owner[v]==player else all(w in reached for w in out[v] if w in active))}
            if not new:return reached
            reached|=new
    while active:
        rounds+=1;reached=attract({v for v in active if charge[v]},1)
        if reached==active:break
        lost=attract(active-reached,0);assert lost
        active-=lost
        assert all(any(w in active for w in out[v]) for v in active)
    return tuple(v in active for v in range(n)),rounds

def train_literal(out,owner,charge,start):
    # Literal first-visit play. The first repeated station fixes the eventual
    # cycle, because all previously chosen switches are permanent.
    def play(path,v):
        if v in path:return any(charge[x] for x in path[path.index(v):])
        outcomes=[play(path+(v,),w) for w in out[v]]
        return any(outcomes) if owner[v] else all(outcomes)
    return play((),start)

def train():
    graphs=cases=starts=maxrounds=0
    for n in range(1,4):
      for rows in itertools.product(range(1,1<<n),repeat=n):
        out=[tuple(v for v in range(n) if mask>>v&1) for mask in rows];graphs+=1
        for own in range(1<<n):
          owner=[own>>v&1 for v in range(n)]
          for r in range(1,1<<n):
            charge=[r>>v&1 for v in range(n)];got,rounds=train_solution(out,owner,charge);maxrounds=max(maxrounds,rounds)
            for s in range(n):assert got[s]==train_literal(out,owner,charge,s);starts+=1
            cases+=1
    randomcases=0
    for _ in range(400):
        n=rng.randrange(4,9);out=[tuple(rng.sample(range(n),rng.randrange(1,min(n,3)+1))) for _ in range(n)];owner=[rng.randrange(2) for _ in range(n)];charge=[rng.randrange(2) for _ in range(n)];charge[rng.randrange(n)]=1
        got,rounds=train_solution(out,owner,charge);maxrounds=max(maxrounds,rounds)
        for s in range(n):assert got[s]==train_literal(out,owner,charge,s);starts+=1
        randomcases+=1
    result['train']={'allTotalDirectedGraphsN1to3LoopsAllowed':graphs,'allOwnerAndNonemptyChargerAssignments':cases,'randomGraphsN4to8':randomcases,'literalInitialPositions':starts,'maximumObservedDeletionRounds':maxrounds,'verified':'Alternating reachability-attractor deletion equals literal extensive first-visit minimax including permanent switches and repeated vertices. Queue/counter implementation would be O(NM), not implemented as a production API here.'}

def prize():
    cases=pairs=0
    arrays=[]
    for n in range(3,11):
        for diamond in range(n):a=[2]*n;a[diamond]=1;arrays.append(a)
        if n>=8:
            for diamond in range(n):
              for twos in itertools.combinations([i for i in range(n) if i!=diamond],2):
                a=[3]*n;a[diamond]=1
                for i in twos:a[i]=2
                arrays.append(a)
    for a in arrays:
        left=[sum(x<a[i] for x in a[:i]) for i in range(len(a))];right=[sum(x<a[i] for x in a[i+1:]) for i in range(len(a))]
        for i in range(len(a)):
          for j in range(i+1,len(a)):
            assert ((left[i]+right[i])==(left[j]+right[j]))==(a[i]==a[j]);pairs+=1
            if a[i]==a[j]:
                assert left[j]-left[i]==sum(x<a[i] for x in a[i+1:j])
                if left[j]==left[i]:assert 1 not in a[i+1:j]
        cases+=1
    bound=0;witness=None;chains=0
    def extend(prefix):
        nonlocal bound,witness,chains
        total=sum(prefix);least_cheap=prefix[-1]**2+1
        if total+least_cheap>200000:return
        chains+=1
        if total>bound:bound=total;witness=prefix+[least_cheap]
        for k in range(least_cheap,math.isqrt(200000-total-1)+1):
            if total+k+k*k+1<=200000:extend(prefix+[k])
    extend([1]);assert bound==472
    result['prize']={'allLegalPrizeSequencesLength3to10':cases,'allPositionPairsCompared':pairs,'allFeasibleMoreExpensiveCountChains':chains,'maximumNonCheapestPrizesForN200000':bound,'countWitness':witness,'verified':'Response sum identifies prize level. Equal-level boundary left-count difference is exact number of strictly better prizes in between; zero remaining count safely prunes for every transcript-consistent fixed completion. Count growth is checked with exact integer recursion.','unconfirmed':'No implementation or independent worst-case proof of the official efficient 4759/required5000-query strategy. Fixed-sequence gap tests do not establish adaptive-grader full-score correctness/budget.'}

class DSU:
    def __init__(self,n):self.p=list(range(n))
    def find(self,x):
        while self.p[x]!=x:self.p[x]=self.p[self.p[x]];x=self.p[x]
        return x
    def join(self,a,b):
        a,b=self.find(a),self.find(b)
        if a==b:return False
        self.p[a]=b;return True

def simurgh_recover(n,edges,hidden):
    m=len(edges);d=DSU(n);tree=[];adj=[[] for _ in range(n)]
    for e,(u,v) in enumerate(edges):
        if d.join(u,v):tree.append(e);adj[u].append((v,e));adj[v].append((u,e))
    assert len(tree)==n-1;treeset=set(tree);queries=0
    def ask(es):
        nonlocal queries
        queries+=1;assert len(es)==n-1 and len(set(es))==n-1
        d=DSU(n)
        for e in es:assert 0<=e<m and d.join(*edges[e])
        return sum(e in hidden for e in es)
    baseline=ask(tree);known={}
    for back,(u,v) in enumerate(edges):
        if back in treeset:continue
        queue=[u];parent={u:(-1,-1)}
        for w in queue:
            if w==v:break
            for z,e in adj[w]:
                if z not in parent:parent[z]=(w,e);queue.append(z)
        path=[];w=v
        while w!=u:w0,e=parent[w];path.append(e);w=w0
        unknown=[e for e in path if e not in known]
        if not unknown:continue
        anchor=next((e for e in path if e in known),None)
        def delta(e):return ask([x for x in tree if x!=e]+[back])-baseline
        if anchor is not None:
            wb=known[anchor]+delta(anchor);assert wb in (0,1)
            for e in unknown:known[e]=wb-delta(e);assert known[e] in (0,1)
        else:
            values=[delta(e) for e in unknown]
            wb=next((1 if v==1 else 0 for v in values if v),0)
            for e,vv in zip(unknown,values):known[e]=wb-vv;assert known[e] in (0,1)
    for e in tree:known.setdefault(e,1) # Reference edges on no fundamental cycle are bridges.
    assert all(known[e]==int(e in hidden) for e in tree)
    learning_queries=queries;assert queries<=1+2*(n-1)
    def forest_count(es):
        if not es:return 0
        d=DSU(n);complete=list(es)
        for e in es:assert d.join(*edges[e])
        added=0
        for e in tree:
            if d.join(*edges[e]):complete.append(e);added+=known[e]
        return ask(complete)-added
    incident=[[] for _ in range(n)]
    for e,(u,v) in enumerate(edges):incident[u].append(e);incident[v].append(e)
    degree=[forest_count(es) for es in incident];active=[True]*n;queue=deque(v for v in range(n) if degree[v]==1);found=[]
    while queue:
        v=queue.popleft()
        if not active[v] or degree[v]!=1:continue
        candidates=[e for e in incident[v] if active[edges[e][0]] and active[edges[e][1]]]
        assert candidates
        while len(candidates)>1:
            mid=len(candidates)//2
            if forest_count(candidates[:mid]):candidates=candidates[:mid]
            else:candidates=candidates[mid:]
        e=candidates[0];assert e in hidden;found.append(e);u,w=edges[e];other=w if u==v else u;active[v]=False;degree[v]=0;degree[other]-=1
        if degree[other]==1:queue.append(other)
    assert set(found)==hidden and len(found)==n-1
    upper=1+2*(n-1)+n+(n-1)*(n-2).bit_length()
    assert queries<=upper
    return queries,learning_queries

def simurgh():
    graphs=trees=queries=maxqueries=0
    for n in range(2,6):
        possible=list(itertools.combinations(range(n),2))
        for mask in range(1<<len(possible)):
            edges=[e for k,e in enumerate(possible) if mask>>k&1]
            if len(edges)<n-1:continue
            d=DSU(n)
            for e in edges:d.join(*e)
            if len({d.find(v) for v in range(n)})>1:continue
            graphs+=1
            for choice in itertools.combinations(range(len(edges)),n-1):
                d=DSU(n)
                if not all(d.join(*edges[e]) for e in choice):continue
                q,_=simurgh_recover(n,edges,set(choice));trees+=1;queries+=q;maxqueries=max(maxqueries,q)
    maximum=[]
    n=500
    for kind in ['path','complete-star','complete-path','complete-random']:
        edges=list(itertools.combinations(range(n),2)) if kind!='path' else [(i,i+1) for i in range(n-1)];ids={e:k for k,e in enumerate(edges)}
        if kind=='complete-star':target=[(0,i) for i in range(1,n)]
        elif kind=='complete-random':target=[tuple(sorted((v,rng.randrange(v)))) for v in range(1,n)]
        else:target=[(i,i+1) for i in range(n-1)]
        q,learn=simurgh_recover(n,edges,{ids[e] for e in target});maximum.append({'kind':kind,'N':n,'M':len(edges),'queries':q,'referenceQueries':learn})
    assert 1+2*499+500+499*499 .bit_length()==5990
    result['simurgh']={'allConnectedSimpleGraphsN2to5':graphs,'everyHiddenSpanningTreeForEveryGraph':trees,'literalValidSpanningTreeQueries':queries,'maximumObservedSmallQueries':maxqueries,'N500Cases':maximum,'allN500UpperBound':5990,'verified':'Independent reference-tree fundamental-cycle differences classify every reference edge in <=1+2(N-1) queries. A forest can be completed with known reference edges; subtract known contribution to get exact forest count. Star counts give hidden degrees; leaf-star subset bisection recovers the hidden tree. EVERY oracle question explicitly DSU-validated as a spanning tree.','productionApiValidated':False,'officialEarDecompositionProofClaimed':False}

def books_values(p,s):
    n=len(p);cycle=[-1]*n;left=[];right=[]
    for v in range(n):
        if cycle[v]>=0:continue
        c=len(left);nodes=[];w=v
        while cycle[w]<0:cycle[w]=c;nodes.append(w);w=p[w]
        left.append(min(nodes));right.append(max(nodes))
    tl=min([s]+[v for v in range(n) if p[v]!=v]);tr=max([s]+[v for v in range(n) if p[v]!=v])
    @lru_cache(None)
    def close(l,r):
        while True:
            nl=min([l]+[left[cycle[v]] for v in range(l,r+1)]);nr=max([r]+[right[cycle[v]] for v in range(l,r+1)])
            if (nl,nr)==(l,r):return l,r
            l,r=nl,nr
    @lru_cache(None)
    def dp(l,r):
        a,b=close(l,r)
        if (a,b)!=(l,r):return dp(a,b)
        if a<=tl and b>=tr:return 0
        return 2+min(([dp(a-1,b)] if a>tl else [])+([dp(a,b+1)] if b<tr else []))
    l=r=s;cost=0
    while True:
        l,r=close(l,r)
        if l<=tl and r>=tr:break
        ll,rl=l,r;cl=0;first_left=False
        while ll>tl:
            ll-=1;cl+=2;ll,rl=close(ll,rl)
            if rl>r:first_left=True;break
        lr,rr=l,r;cr=0;first_right=False
        while rr<tr:
            rr+=1;cr+=2;lr,rr=close(lr,rr)
            if lr<l:first_right=True;break
        assert first_left==first_right
        cost+=min(cl,cr) if first_left else cl+cr
        l,r=min(ll,lr),max(rl,rr)
    base=sum(abs(v-p[v]) for v in range(n));return base+dp(s,s),base+cost

def books():
    comparisons=states=0
    for n in range(1,7):
      for s in range(n):
        # Reversible literal operations: swap held item with current table at
        # cost0 (blank models pickup/putdown), move one adjacent table at cost1.
        start=(tuple(range(n+1)),s);distance={start:0};queue=deque([start])
        while queue:
            items,pos=queue.popleft();d=distance[(items,pos)]
            changed=list(items);changed[pos],changed[n]=changed[n],changed[pos];state=(tuple(changed),pos)
            if d<distance.get(state,10**9):distance[state]=d;queue.appendleft(state)
            for v in [pos-1,pos+1]:
                if 0<=v<n:
                    state=(items,v)
                    if d+1<distance.get(state,10**9):distance[state]=d+1;queue.append(state)
        states+=len(distance)
        for p in itertools.permutations(range(n)):
            expected=distance[(p+(n,),s)];bydp,bygreedy=books_values(p,s);assert expected==bydp==bygreedy,(p,s,expected,bydp,bygreedy);comparisons+=1
    result['books']={'allPermutationsN1to6AllStarts':comparisons,'literalPickupSwapPutdownAdjacentMoveStates':states,'verified':'Full reversible 0-1 state shortest paths equal interval-cycle closure DP and author greedy comparing first cross-boundary cycle reach costs. Probe uses explicit small closures, not a linear-time production implementation.','productionApiValidated':False,'numericBoundsSource':'Final contest KOR statement n<=1000000, NOT old Library editorial draft subtask table/API.'}

def replay(entry,choices):
    graphs={g['id']:g for g in json.loads((BASE/'data/flows.json').read_text())};g=graphs[entry];node=next(x for x in g['nodes'] if x['id']==g['root']);steps=[];routes=[];at=0
    for _ in range(256):
        if node['type']=='route':
            routes.append({'fromGraphId':g['id'],'fromNodeId':node['id'],'toGraphId':node['graph']});g=graphs[node['graph']];node=next(x for x in g['nodes'] if x['id']==g['root']);continue
        if at==len(choices):break
        assert node['type']=='question';answer=choices[at];labels=node.get('options') or [{'id':a,'label':{'yes':'はい','no':'いいえ','unknown':'わからない'}.get(a,a)} for a in node['answers']]
        label=next(x['label'] for x in labels if x['id']==answer);steps.append({'graphId':g['id'],'nodeId':node['id'],'question':node['title'],'answer':answer,'answerLabel':label});target=node['answers'][answer];node=next(x for x in g['nodes'] if x['id']==target);at+=1
    else:raise AssertionError('route cycle')
    assert at==len(choices)
    stop={'graphId':g['id'],'nodeId':node['id'],'type':node['type'],'title':node['title'],'options':node.get('options') or ([{'id':a,'label':{'yes':'はい','no':'いいえ','unknown':'わからない'}.get(a,a)} for a in node.get('answers',{})]),'techniques':node.get('techniques',[])}
    return {'entryGraphId':entry,'choices':choices,'steps':steps,'initialReached':stop,'routeTransitions':routes,'stepsSha256':hashlib.sha256(json.dumps(steps,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()}

def product_runtime_crosscheck():
    script=r"""
import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import path from 'node:path';
const [base, output] = process.argv.slice(1);
const {compileLocalModules}=await import(pathToFileURL(path.join(base,'scripts/local-modules.mjs')));
await compileLocalModules(base,output);
const flow=await import(pathToFileURL(path.join(output,'flow.js')));
const input=JSON.parse(readFileSync(0,'utf8'));
const result={};
for(const [task,record] of Object.entries(input)){
 let state=flow.initialState(record.entryGraphId);const steps=[];
 const follow=()=>{for(let i=0;flow.evaluateState(state).current.type==='route';i++){if(i>128)throw Error('routecycle');state=flow.enterFlowRoute(state);}};
 for(const answer of record.choices){follow();const e=flow.evaluateState(state);steps.push({graphId:e.graph.id,nodeId:e.current.id,question:e.current.title,answer,answerLabel:flow.getAnswerLabel(e.current,answer)});state=flow.answerState(state,answer);}
 follow();const e=flow.evaluateState(state);
 result[task]={steps,initialReached:{graphId:e.graph.id,nodeId:e.current.id,type:e.current.type,title:e.current.title,options:flow.getNodeOptions(e.current),techniques:e.current.techniques??[]}};
}
console.log(JSON.stringify(result));
"""
    with tempfile.TemporaryDirectory(prefix='flowchartcp-ioi2017-runtime-') as output:
        process=subprocess.run(['node','--input-type=module','-e',script,str(BASE),output],input=json.dumps(result['routes']),capture_output=True,text=True,check=True)
        observed=json.loads(process.stdout)
    for task,route in result['routes'].items():
        assert observed[task]['steps']==route['steps']
        assert observed[task]['initialReached']==route['initialReached']
    result['productRuntimeCrosscheck']={'allSixRoutesMatchIndependentRawWalker':True,'compiler':'frozen vendor/typescript.cjs through frozen scripts/local-modules.mjs','includesExactQuestionsAnswerLabelsAndTerminal':True}

def existing_api_scope_checks():
    import re
    ids=['matching','retrograde-winning-draw','permutation-cycle-minimum-swaps'];blocks=[];sha={}
    for tid in ids:
        text=(BASE/'src/content/docs/techniques'/f'{tid}.mdx').read_text();fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',text,re.M|re.S);assert len(fences)==1;blocks.append(fences[0]);sha[tid]=hashlib.sha256(fences[0].encode()).hexdigest()
    test=r"""
#include <iostream>
int main(){
 auto matched=bipartite_match({{0},{0}},1);int count=0;for(int v:matched)count+=(v>=0);if(count!=1)return 1;
 auto result=classify_normal_graph_game({{0,1},{0,1}});if(result!=std::vector<int>{0,0})return 2;
 auto swaps=sort_permutation_swaps({2,1,0});if(swaps.size()!=1)return 3;
 std::cout<<"{\"matchingMaximumDisjointPairs\":1,\"normalCyclicGame\":[0,0],\"unrestrictedPermutationSwaps\":1}";
}
"""
    with tempfile.TemporaryDirectory(prefix='flowchartcp-ioi2017-nearby-') as folder:
        cpp=Path(folder)/'scope.cpp';binary=Path(folder)/'scope';cpp.write_text('\n'.join(blocks)+'\n'+test)
        subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(binary)],check=True,capture_output=True,text=True)
        observed=json.loads(subprocess.check_output([str(binary)],text=True))
    assert train_literal([(0,1),(0,1)],[0,1],[1,0],0) and train_literal([(0,1),(0,1)],[0,1],[1,0],1)
    assert books_values((2,1,0),1)==(6,6)
    result['existingApiScopeChecks']={'compiledActualFrozenCppFences':sha,'observed':observed,'originalTargets':{'wiring':'red0,1 andblue2 need TWO incident-cover wires, total3; disjoint matching returns only one pair','train':'a0,1/r1,0 with both selfloops+crossarcs is Arezou-win at both starts; normal-endpoint-game classifier returns draws','books':'p2,1,0 S1 takes6 walk distance even though arbitrary-position swap count1'},'meaning':'These are explicit scope counterexamples, not bugs in the existing APIs or full-range IOI2017 production validations.'}

def retained(kind):
    item=MANIFEST['retainedSnapshots'][kind];data=gzip.decompress((SITE/item['file']).read_bytes())
    assert hashlib.sha256(data).hexdigest()==item['rawSha256'],kind
    assert len(data)==item['rawBytes'];return data

def materialize(folder):
    global BASE,RETAINED_COUNT
    BASE=Path(folder);bundle=json.loads(retained('retained-raw'))
    ledger={f['path']:f['sha256'] for f in MANIFEST['files']}
    for item in bundle['files']:
        file=item['path'];data=base64.b64decode(item['rawBase64']);assert hashlib.sha256(data).hexdigest()==item['sha256']==ledger[file]
        # These are all preserved, but only the two imported flow runtime files
        # need materializing: content.ts imports many intentionally unretained
        # original source JSON chunks; the raw walker never uses live metadata.
        if file.startswith('src/lib/') and file not in ('src/lib/flow.ts','src/lib/flow-layout.ts'):continue
        target=BASE/file;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    for kind,file in [('flow','data/flows.json'),('walk','data/problem-walks.json'),('source','data/sources.json')]:
        target=BASE/file;target.parent.mkdir(parents=True,exist_ok=True);data=retained(kind);assert hashlib.sha256(data).hexdigest()==ledger[file];target.write_bytes(data)
    RETAINED_COUNT=len(bundle['files'])+3
    compiler=Path(os.environ.get('FLOWCHARTCP_COMPILER_FILE',str(SITE/MANIFEST['compilerDependency']['file'])));data=compiler.read_bytes();assert hashlib.sha256(data).hexdigest()==MANIFEST['compilerDependency']['sha256']
    target=BASE/'vendor/typescript.cjs';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)

def frozen_checks():
    core_before=json.loads(base64.b64decode(MANIFEST['originalCoreBeforeRawBase64']));core_after=json.loads(base64.b64decode(MANIFEST['originalCoreAfterRawBase64']))
    before=json.loads(base64.b64decode(MANIFEST['originalExtendedBeforeRawBase64']));after=json.loads(base64.b64decode(MANIFEST['originalExtendedAfterRawBase64']))
    assert core_before==core_after and len(core_before)==921
    assert before==after and len(before)==1492 and all(before[k]==v for k,v in core_before.items())
    assert {f['path']:f['sha256'] for f in MANIFEST['files']}==before
    assert sum(f['epoch']=='initial-core' for f in MANIFEST['files'])==921
    assert sum(f['epoch']=='later-dependency-extension' for f in MANIFEST['files'])==571
    metadata=json.loads(retained('technique'));references=json.loads(retained('reference'))
    assert len(metadata)==498 and len(references)==519 and len({m['id'] for m in metadata})==498
    assert sum(f.startswith('src/content/docs/techniques/') and f.endswith('.mdx') for f in core_before)==498
    graphs=json.loads((BASE/'data/flows.json').read_text());assert len(graphs)==465 and sum(g.get('entry') is True for g in graphs)==15
    assert len(json.loads((BASE/'data/problem-walks.json').read_text()))==519
    result['baseline']={'historicalCoreRawFileCount':921,'laterDependencyExtensionFileCount':571,'historicalRawHashLedgerEntries':1492,'retainedOriginalRawFilesRehashed':RETAINED_COUNT,'allHistoricalRawBytesAvailable':False,'allHistoricalMdxAvailable':False,'retainedFullMdxCount':13,'historicalAllMdx':498,'graphs':465,'walks':519,'entryDomains':[g['id'] for g in graphs if g.get('entry')]}
    result['routes']={task:replay(entry,choices) for task,entry,choices in [('nowruz','fixed-output',[]),('wiring','flow-matching',['quantity-goals','costs','yes']),('train','game-probability',['win','other','no']),('prize','interactive-oracles',['other']),('simurgh','interactive-oracles',['other']),('books','ranges',['sequence-changes','reorder-cost'])]}

if __name__=='__main__':
    started=time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='flowchartcp-ioi2017-retained-') as folder:
        materialize(folder);frozen_checks();product_runtime_crosscheck();existing_api_scope_checks();nowruz();wiring();train();prize();simurgh();books()
    result['elapsedSeconds']=round(time.perf_counter()-started,6)
    rendered=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(rendered)
    print(rendered,end='')
