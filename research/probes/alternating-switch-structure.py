#!/usr/bin/env python3
"""Independent spatial pruning recurrence, without ceiling counts or popcount in its oracle."""
from functools import lru_cache
from pathlib import Path
import hashlib,json,time
started=time.monotonic()
@lru_cache(None)
def structure(span,live):
    # The live leaves occupy a suffix. A retained node is visited span times
    # during the underlying complete-tree period; a dead subtree has no nodes.
    if live==0 or span==1:return (0,0)
    half=span//2
    ls,lt=structure(half,max(0,live-half))
    rs,rt=structure(half,min(half,live))
    return (1+ls+rs,span+lt+rt)
max_s=(0,0);max_t=(0,0);cases=0;checksum=0
for n in range(1,200001):
    p=1
    while p<n+1:p*=2
    s,t=structure(p,n+1)
    h=p.bit_length()-1
    # The independently obtained structural result is compared with every claim.
    expected_s=sum((n+1+b-1)//b for b in (1<<j for j in range(1,h+1)))
    expected_t=sum(b*((n+1+b-1)//b) for b in (1<<j for j in range(1,h+1)))
    assert s==expected_s==n-n.bit_count()+h
    assert t==expected_t
    assert s<=n+n.bit_length()-1<=400000
    assert t<=p*h<=4718592<20000000
    if s>max_s[0]:max_s=(s,n)
    if t>max_t[0]:max_t=(t,n)
    checksum=(checksum*1000003+s*31+t)&((1<<64)-1)
    cases+=1
# Negative control: killing the earliest time slots scatters unused leaves.
# N=4 then needs the unpruned seven nodes and violates the full-score bound six.
def retained(span,live):
    if not live or span==1:return 0
    half=span//2
    return 1+retained(half,{x for x in live if x<half})+retained(half,{x-half for x in live if x>=half})
assert retained(8,set(range(3,8)))==6
assert retained(8,{1,3,5,6,7})==7
article=(Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/alternating-switch-bit-reversal-pruned-router.mdx').read_bytes()
result={'status':'passed','allNSpatialStructureCases':cases,'oracle':'suffix subtree split: S=1+Sleft+Sright,T=span+Tleft+Tright; all-dead child contributes zero','maxS':{'value':max_s[0],'firstN':max_s[1]},'maxT':{'value':max_t[0],'firstN':max_t[1]},'negativeControls':{'wrongTimePrefixPruningN4':{'switches':7,'fullScoreIntegerBound':6,'correctSpatialPruningSwitches':6}},'checksum':str(checksum),'memoStates':structure.cache_info().currsize,'seconds':time.monotonic()-started,'articleSha256':hashlib.sha256(article).hexdigest()}
print(json.dumps(result))
