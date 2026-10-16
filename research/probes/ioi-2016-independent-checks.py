#!/usr/bin/env python3
"""Read-only IOI2016 audit review. Research checks, never production API checks."""
from pathlib import Path
import hashlib, importlib.util, itertools, json, random, re, time

from ioi_2016_snapshot import snapshot_baseline
_snapshot_holder,BASE=snapshot_baseline()
PREFIX=str(BASE/'.research-originals'/'flowchartcp-ioi2016-')
def frozen_path(value):
    value=str(value);oldbase='/tmp/flowchartcp-ioi2016-baseline/'
    if value.startswith(oldbase):return BASE/value[len(oldbase):]
    oldprefix='/tmp/flowchartcp-ioi2016-'
    assert value.startswith(oldprefix),value
    return Path(PREFIX+value[len(oldprefix):])
def read(name): return json.loads(Path(name).read_text())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def canonical(x): return hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def preservation():
    side = read(PREFIX+'sidecar.json')
    artifact_count = 0
    for item in side['artifacts'].values():
        assert sha(frozen_path(item['path'])) == item['sha256'], item['path']
        artifact_count += 1
    m = read(BASE/'manifest.json')
    before, after = read(BASE/'hashes-before.json'), read(BASE/'hashes-after.json')
    assert before == after == m['fullRawHashes']
    for file, digest in before.items():
        assert not any(part.startswith('.env') for part in Path(file).parts)
        assert sha(BASE/file) == digest, file
    all_ledger = {line.split('  ',1)[1]:line.split('  ',1)[0] for line in (BASE/'SHA256SUMS').read_text().splitlines()}
    core_ledger = {line.split('  ',1)[1]:line.split('  ',1)[0] for line in (BASE/'CORE_SHA256SUMS').read_text().splitlines()}
    assert all_ledger == before and len(before) == 1431
    assert core_ledger == {k:v for k,v in before.items() if not k.startswith('public/')}
    assert len(core_ledger) == 959 and sum(k.startswith('public/') for k in before) == 472
    vendor = read(BASE/'vendor-hashes-before.json')
    assert vendor == read(BASE/'vendor-hashes-after.json') and len(vendor) == 105
    assert not any(k in before for k in vendor)
    for file,digest in vendor.items(): assert sha(BASE/file) == digest
    selection = read(PREFIX+'selection.json')
    assert sha(PREFIX+'selection.json') == '3505ba77043d0ff594b6b66fe763cf9e7b1cd97082a79ff4dc30cbca809c3350'
    assert selection['fixedBeforeTechniqueSearch'] and selection['solutionsAndCoverageNotYetAssessedAtSelection']
    names = ['molecules','railroad','shortcut','paint','messy','aliens']
    assert [p['officialTaskId'] for p in selection['problems']] == names
    for i,p in enumerate(selection['problems']):
        assert p['day'] == (1 if i<3 else 2)
        assert p['date'] == ('2016-08-14' if i<3 else '2016-08-16')
    metadata = [r for file in sorted((BASE/'data').glob('techniques*.json')) for r in read(file)]
    refs = [r for file in sorted((BASE/'data').glob('references*.json')) for r in read(file)]
    assert len(metadata) == 504 and len(refs) == 525
    assert sum(k.startswith('src/content/docs/techniques/') and k.endswith('.mdx') for k in before) == 504
    assert len(list((BASE/'data/corpus-audits').glob('*.json'))) == 9
    audit = read(PREFIX+'audit.json')
    assert audit['status']['solutionReviewedCount'] == 6
    assert audit['status']['coveredCount'] == audit['status']['fullImplementationValidatedCount'] == 0
    nearest = {}
    for row in audit['records']:
        assert row['completedApiCoverage'] is False and row['expectedTechniqueIds'] == []
        assert row['technicalFindings']['fullImplementationValidated'] is False
        assert row['technicalFindings']['unconfirmedDetails'] == []
        assert row['difficulty'] is None and row['datePrecision'] == 'day'
        for entry in row['relatedArticleReview']:
            assert sha(BASE/entry['file']) == entry['sha256']
            cpp = re.findall(r'^```cpp\s*\n(.*?)^```\s*$',(BASE/entry['file']).read_text(),re.M|re.S)
            assert len(cpp) == 1 and hashlib.sha256(cpp[0].encode()).hexdigest() == entry['cppFenceSha256']
            for source in entry['metadataSourceFiles']: assert sha(BASE/source['file']) == source['sha256']
            nearest[entry['techniqueId']] = entry['sha256']
    assert len(nearest) == 19
    return {'allArtifactHashes':artifact_count,'rawFiles':1431,'coreFiles':959,'publicSameEpoch':472,'vendorLaterEpoch':105,'oldAudits':9,'nearestMdxAndCpp':19,'initialMetadata':504,'initialWalks':525,'initialGraphs':471,'initialResearch':6,'initialProductionApi':0,'initialCoverage':0,'rawLedgerSha256':sha(BASE/'SHA256SUMS'),'initialRecordsProjectionSha256':canonical(audit['records']),'initialStatusSha256':canonical(audit['status']),'initialSelectionSha256':canonical(audit['selection']),'initialSnapshotSha256':canonical(audit['snapshot'])}

def routes():
    graphs = read(BASE/'data/flows.json'); by={g['id']:g for g in graphs}
    assert len(graphs) == 471
    entries = [g['id'] for g in graphs if g.get('entry')]
    assert len(entries) == 15
    def options(n):
        if 'options' in n:return n['options']
        return [{'id':a,'label':{'yes':'はい','no':'いいえ','unknown':'わからない'}.get(a,a)} for a in n.get('answers',{})]
    def walk(entry,choices):
        g=by[entry];n=next(n for n in g['nodes'] if n['id']==g['root']);steps=[];position=0
        for _ in range(10000):
            if n['type']=='route':
                g=by[n['graph']];n=next(n for n in g['nodes'] if n['id']==g['root']);continue
            if n['type']!='question' or position==len(choices):break
            a=choices[position];target=n['answers'][a]
            label=next(o['label'] for o in options(n) if o['id']==a)
            steps.append({'graphId':g['id'],'nodeId':n['id'],'question':n['title'],'answer':a,'answerLabel':label,'target':target})
            position+=1;n=next(n for n in g['nodes'] if n['id']==target)
        assert position==len(choices)
        return steps,{'graphId':g['id'],'nodeId':n['id'],'type':n['type'],'title':n['title'],'options':options(n),'techniques':n.get('techniques',[]),'conditions':n.get('conditions',[])}
    reference = read(PREFIX+'routes.json');audit=read(PREFIX+'audit.json');total=0
    for row in audit['records']:
        steps,end=walk(row['entryGraphId'],row['choices'])
        expected=reference[row['officialTaskId']]
        assert steps==expected['steps']==row['steps']
        assert end==expected['reached']==row['initialReached']
        assert end['graphId']==row['gap']['firstMissingGraphId'] and end['nodeId']==row['gap']['firstMissingNodeId']
        assert end['title']==row['gap']['currentQuestion'] and end['options']==row['gap']['currentOptions']
        assert end['techniques']==row['actualReachedTechniqueIds']
        assert canonical(steps)==row['navigationReplay']['stepsSha256']
        assert entries==row['navigationReplay']['all15EntryDomainsConsidered']
        total+=len(steps)
    existing=read(BASE/'data/problem-walks.json');oldsteps=0
    for row in existing:
        steps,end=walk(row['entryGraphId'],row['choices'])
        assert len(steps)==len(row['steps'])
        for a,b in zip(steps,row['steps']):
            assert (a['graphId'],a['nodeId'],a['answer'])==(b['graph'],b['node'],b['answer'])
        assert set(row['expectedTechniqueIds']) <= set(end['techniques'])
        oldsteps+=len(steps)
    return {'entryRoots':entries,'canonicalRoutes':6,'fullQuestionAndAnswerLabels':total,'existingWalks':len(existing),'existingWalkSteps':oldsteps,'genericInteractiveReachedButUncovered':True}

def additional_math():
    spec=importlib.util.spec_from_file_location('author_research',PREFIX+'probe.py')
    subject=importlib.util.module_from_spec(spec);spec.loader.exec_module(subject)
    rng=random.Random(20160816)
    # Independent subset/last DP: never enumerates a permutation and uses no coordinate balance/DSU/MST.
    def exact_orders(edges):
        n=len(edges);f=[[10**40]*n for _ in range(1<<n)]
        for v in range(n):f[1<<v][v]=0
        for mask in range(1,1<<n):
            remaining=((1<<n)-1)^mask
            for v in range(n):
                if not (mask>>v&1):continue
                z=remaining
                while z:
                    bit=z&-z;u=bit.bit_length()-1;z-=bit
                    value=f[mask][v]+max(0,edges[v][1]-edges[u][0])
                    if value<f[mask|bit][u]:f[mask|bit][u]=value
        return min(f[-1])
    railroad_cases=0;railroad_metas=0
    for case in range(220):
        n=rng.randrange(2,13)
        palette=[1,2,3,10**9-1,10**9] if case<100 else list(range(1,15))
        edges=[(rng.choice(palette),rng.choice(palette)) for _ in range(n)]
        expected=exact_orders(edges)
        assert subject.railroad_fast(edges)==expected
        railroad_cases+=1
        if case>=100:
            scale=17;shift=31
            assert subject.railroad_fast([(scale*s+shift,scale*t+shift) for s,t in edges])==scale*expected
            railroad_metas+=1
    # Test the V-shaped discrete endpoint search on arbitrary bounds, without deriving them from bad pairs.
    pointer_cases=0
    for n in range(2,7):
        for tail in itertools.combinations(range(1,8),n-1):
            x=[0,*tail]
            for sl in range(-2,17,3):
                for sh in range(-2,17,3):
                    for dl in range(-1,10,2):
                        for dh in range(-1,10,2):
                            bounds=(sl,sh,dl,dh)
                            expected=any(sl<=x[a]+x[b]<=sh and dl<=x[b]-x[a]<=dh for a in range(n) for b in range(a+1,n))
                            assert subject.shortcut_feasible(x,bounds)==expected,(x,bounds)
                            pointer_cases+=1
    # Check the constructive balancing exchange for *all* path pairs with counts differing by two.
    # This does not infer convexity from floating-point samples or assume the Monge theorem as an oracle.
    exchange_pairs=0;monge_checks=0;aliens_intervals=0
    for _ in range(260):
        n=rng.randrange(3,10)
        left=sorted(rng.sample(range(30),n));right=sorted(rng.sample(range(30,70),n))
        intervals=list(zip(left,right));aliens_intervals+=1
        def cost(a,b):
            overlap=max(0,intervals[a-1][1]-intervals[a][0]+1) if a else 0
            return (intervals[b-1][1]-intervals[a][0]+1)**2-overlap**2
        for a,b,c,d in itertools.combinations(range(n+1),4):
            assert cost(a,c)+cost(b,d)<=cost(a,d)+cost(b,c)
            monge_checks+=1
        paths=[(0,*cuts,n) for count in range(n) for cuts in itertools.combinations(range(1,n),count)]
        groups={q:[] for q in range(1,n+1)}
        for p in paths:groups[len(p)-1].append(p)
        # Subsample interval instances at n>=8; every path pair of each chosen size is still tested.
        if n>=8 and aliens_intervals%13:continue
        for q in range(2,n):
            for p in groups[q-1]:
                for t in groups[q+1]:
                    common=set(p[1:-1])&set(t[1:-1])
                    swapped=None
                    for v in sorted(common):
                        i,j=p.index(v),t.index(v)
                        if j-i==1:
                            swapped=(p[:i]+t[j:],t[:j]+p[i:]);break
                    if swapped is None:
                        balance=0
                        for v in sorted(set(p[1:-1])|set(t[1:-1])):
                            balance+=(v in t)-(v in p)
                            if balance==2:
                                d=v;j=t.index(d);b=t[j-1]
                                i=max(k for k in range(len(p)) if p[k]<d);a,c=p[i:i+2]
                                assert a<=b<d<=c and j-1-i==1
                                swapped=(p[:i+1]+t[j:],t[:j]+p[i+1:]);break
                    assert swapped is not None
                    a,b=swapped
                    assert len(a)-1==len(b)-1==q
                    assert all(x<y for z in swapped for x,y in zip(z,z[1:]))
                    old=sum(cost(x,y) for z in [p,t] for x,y in zip(z,z[1:]))
                    new=sum(cost(x,y) for z in swapped for x,y in zip(z,z[1:]))
                    assert new<=old
                    exchange_pairs+=1
    return {'railroadHeldKarpCasesN2to12':railroad_cases,'railroadPositiveAffineCases':railroad_metas,'shortcutArbitraryRotatedRectangleEndpointCases':pointer_cases,'aliensAbstractIntervalSets':aliens_intervals,'aliensDirectMongeChecks':monge_checks,'aliensConstructivePathPairExchanges':exchange_pairs,'productionApiValidated':False,'sanitizerRun':False}

def main():
    t=time.monotonic()
    result={'schemaVersion':1,'scope':'independent IOI2016 initial fixed-corpus audit review; no production solver validation','preservation':preservation(),'rawRoutes':routes(),'additionalMath':additional_math(),'sharedFilesModified':False,'authorArtifactsModified':False,'elapsedSeconds':time.monotonic()-t}
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
