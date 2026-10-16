"""Compile the published snippets and compare with independent small models."""
from pathlib import Path
import os
import re
import shlex
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
IDS=['mo-frequency-quadratic','mo-with-updates','parallel-binary-search-time','cdq-dominance',
     'offline-kth-divide-values','persistent-prefix-kth','wavelet-range-kth','fenwick-prefix-lower-bound',
     'xor-basis-kth','linear-basis-rollback','sqrt-heavy-light-sets','range-add-count-less']
FIXTURE=r'''
std::mt19937_64 rng(20261014);
std::vector<std::uint64_t> all_xors(const std::vector<std::uint64_t>& a) {
    std::vector<std::uint64_t> values{0};
    for(auto x:a) {int n=int(values.size());for(int i=0;i<n;++i) values.push_back(values[i]^x);}
    std::sort(values.begin(),values.end());values.erase(std::unique(values.begin(),values.end()),values.end());return values;
}
int main() {
    // Frequency-square aggregation: recompute all counts for each original query.
    for(int n=0;n<=24;++n) for(int trial=0;trial<70;++trial) {
        std::vector<long long> a(n);for(auto& x:a) x=static_cast<long long>(rng()%13)-6;
        std::vector<std::pair<int,int>> ranges;std::vector<__int128> want;
        for(int step=0;step<60;++step) {
            int l=rng()%(n+1),r=rng()%(n+1);if(l>r) std::swap(l,r);ranges.push_back({l,r});
            std::map<long long,int> counts;for(int p=l;p<r;++p) ++counts[a[p]];
            __int128 sum=0;for(auto [value,count]:counts) sum+=__int128(value)*count*count;want.push_back(sum);
        }
        assert(t0::weighted_frequency_square(a,ranges)==want);
    }
    {
        std::vector<long long> a(30,std::numeric_limits<long long>::max());
        assert(t0::weighted_frequency_square(a,{{0,30}})[0]==__int128(a[0])*900);
    }
    // Updates and frequency-MEX: execute in input order and reconstruct counts.
    for(int n=1;n<=18;++n) for(int trial=0;trial<80;++trial) {
        std::vector<long long> initial(n);for(auto& x:initial) x=rng()%8;auto a=initial;
        std::vector<t1::FrequencyOperation> operations;std::vector<int> want;
        for(int step=0;step<100;++step) {
            if(rng()%2) {int p=rng()%n;long long v=rng()%14;operations.push_back({1,p,0,v});a[p]=v;}
            else {
                int l=rng()%(n+1),r=rng()%(n+1);if(l>r) std::swap(l,r);operations.push_back({0,l,r,0});
                std::map<long long,int> count;for(int p=l;p<r;++p) ++count[a[p]];
                std::set<int> frequencies;for(auto [x,c]:count) frequencies.insert(c);
                int mex=1;while(frequencies.count(mex)) ++mex;want.push_back(mex);
            }
        }
        assert(t1::frequency_mex_with_updates(initial,operations)==want);
    }
    assert(t1::frequency_mex_with_updates({},{{0,0,0,0}})==std::vector<int>{1});
    // All first target times against explicit cyclic increments, including empty owners.
    for(int m=1;m<=16;++m) for(int trial=0;trial<80;++trial) {
        int groups=1+rng()%10,k=rng()%30;std::vector<int> owner(m);for(int& x:owner) x=rng()%groups;
        std::vector<long long> target(groups);for(auto& x:target) x=static_cast<long long>(rng()%190)-3;
        std::vector<t2::CyclicIncrement> updates;for(int t=0;t<k;++t) updates.push_back({int(rng()%m),int(rng()%m),static_cast<long long>(rng()%9)});
        std::vector<__int128> value(m);std::vector<int> want(groups,-1);
        for(int g=0;g<groups;++g) if(target[g]<=0) want[g]=0;
        for(int t=0;t<k;++t) {
            auto u=updates[t];int p=u.l;while(true) {value[p]+=u.delta;if(p==u.r) break;p=(p+1)%m;}
            std::vector<__int128> total(groups);for(int p=0;p<m;++p) total[owner[p]]+=value[p];
            for(int g=0;g<groups;++g) if(want[g]<0&&total[g]>=target[g]) want[g]=t+1;
        }
        assert(t2::first_target_times(owner,target,updates)==want);
    }
    {
        auto maximum=std::numeric_limits<long long>::max();
        assert(t2::first_target_times({0,0},{maximum},{{0,1,maximum}})==std::vector<int>{1});
    }
    // 3D counts: every ordered pair, with exact duplicates and negative coordinates.
    for(int n=0;n<=45;++n) for(int trial=0;trial<100;++trial) {
        std::vector<std::array<long long,3>> points(n);for(auto& p:points) for(auto& x:p) x=static_cast<long long>(rng()%9)-4;
        std::vector<int> want(n);for(int i=0;i<n;++i) for(int j=0;j<n;++j) if(i!=j)
            want[i]+=points[j][0]<=points[i][0]&&points[j][1]<=points[i][1]&&points[j][2]<=points[i][2];
        assert(t3::dominance_counts(points)==want);
    }
    assert(t3::dominance_counts(std::vector<std::array<long long,3>>(30,{1,2,3}))==std::vector<int>(30,29));
    // Dynamic ranks: sort the literal interval after executing all earlier changes.
    for(int n=1;n<=24;++n) for(int trial=0;trial<80;++trial) {
        std::vector<long long> initial(n);for(auto& x:initial) x=static_cast<long long>(rng()%15)-7;auto a=initial;
        std::vector<t4::RankingOperation> operations;std::vector<long long> want;
        for(int step=0;step<80;++step) {
            if(rng()%2) {int p=rng()%n;long long value=static_cast<long long>(rng()%21)-10;operations.push_back({1,p,0,0,value});a[p]=value;}
            else {int l=rng()%n,r=l+1+rng()%(n-l),k=rng()%(r-l);operations.push_back({0,l,r,k,0});
                std::vector<long long> values(a.begin()+l,a.begin()+r);std::sort(values.begin(),values.end());want.push_back(values[k]);}
        }
        assert(t4::dynamic_range_kth(initial,operations)==want);
    }
    assert(t4::dynamic_range_kth({},{}).empty());
    // Static ranks: every nonempty interval and every rank, with ties and one-valued data.
    for(int n=1;n<=28;++n) for(int trial=0;trial<30;++trial) {
        std::vector<long long> a(n);for(auto& x:a) x=trial%3==0?7:static_cast<long long>(rng()%17)-8;
        t5::PrefixKth persistent(a);t6::WaveletKth wavelet(a);
        for(int l=0;l<n;++l) for(int r=l+1;r<=n;++r) {
            std::vector<long long> sorted(a.begin()+l,a.begin()+r);std::sort(sorted.begin(),sorted.end());
            for(int k=0;k<r-l;++k) {assert(persistent.kth(l,r,k)==sorted[k]);assert(wavelet.kth(l,r,k)==sorted[k]);}
        }
    }
    {t5::PrefixKth a({});t6::WaveletKth b({});assert(a.roots.size()==1&&b.bits==0);}
    // Fenwick inverse-CDF agrees with a linear scan for all possible targets.
    for(int n=1;n<=35;++n) {
        t7::NonnegativeFenwick bit(n);std::vector<int> frequency(n);
        for(int step=0;step<120;++step) {
            int p=rng()%n,d=rng()%6-frequency[p];frequency[p]+=d;bit.add(p,d);
            int total=std::accumulate(frequency.begin(),frequency.end(),0);
            for(int target=1;target<=total+1;++target) {
                int pos=0,sum=0;while(pos<n&&sum+frequency[pos]<target) sum+=frequency[pos++];
                assert(bit.lower_bound(target)==pos);
            }
        }
    }
    for(int n=1;n<=80;++n) for(std::uint64_t skipped:{0ULL,1ULL,2ULL,1000000000ULL,18446744073709551615ULL}) {
        std::vector<int> alive(n),want;std::iota(alive.begin(),alive.end(),0);std::uint64_t rank=0;
        while(!alive.empty()) {rank=(rank+skipped%alive.size())%alive.size();want.push_back(alive[rank]);alive.erase(alive.begin()+rank);}
        assert(t7::josephus_order(n,skipped)==want);
    }
    // Sorted XOR values: enumerate all subsets, deduplicate, and sort.
    for(int n=0;n<=12;++n) for(int trial=0;trial<80;++trial) {
        std::vector<std::uint64_t> a(n);for(auto& x:a) x=rng()%1024;auto want=all_xors(a);t8::SortedXorValues basis(a);
        for(std::uint64_t k=0;k<want.size();++k) assert(basis.kth(k)==std::optional<std::uint64_t>(want[k]));
        assert(!basis.kth(want.size()));
    }
    {
        std::vector<std::uint64_t> powers;for(int b=0;b<64;++b) powers.push_back(std::uint64_t(1)<<b);
        t8::SortedXorValues full(powers);for(std::uint64_t k:{0ULL,1ULL,18446744073709551615ULL,9223372036854775808ULL}) assert(full.kth(k)==std::optional<std::uint64_t>(k));
        powers.pop_back();t8::SortedXorValues partial(powers);assert(!partial.kth(std::uint64_t(1)<<63));
    }
    // Nested rollback versions: all subset XORs of the exact active value list.
    for(int trial=0;trial<300;++trial) {
        t9::RollbackXorBasis basis;std::vector<std::uint64_t> active;
        std::function<void(int)> visit=[&](int depth) {
            auto mark=basis.snapshot();int before=int(active.size());
            int additions=rng()%3;for(int i=0;i<additions;++i) {auto x=rng()%256;active.push_back(x);basis.insert(x);}
            auto possible=all_xors(active);
            for(std::uint64_t x=0;x<256;++x) {
                assert(basis.contains(x)==std::binary_search(possible.begin(),possible.end(),x));
                auto smallest=x;for(auto y:possible) smallest=std::min(smallest,x^y);assert(basis.minimum(x)==smallest);
            }
            if(depth<3) {visit(depth+1);visit(depth+1);}
            basis.rollback(mark);active.resize(before);
            possible=all_xors(active);for(std::uint64_t x=0;x<256;++x) assert(basis.contains(x)==std::binary_search(possible.begin(),possible.end(),x));
        };
        visit(0);assert(basis.snapshot()==0);
    }
    {
        t9::RollbackXorBasis b;b.insert(std::uint64_t(1)<<63);auto snapshot=b.snapshot();assert(!b.insert(std::uint64_t(1)<<63));b.insert(1);
        assert(b.minimum(~std::uint64_t(0))==((std::uint64_t(1)<<63)-2));b.rollback(snapshot);assert(!b.contains(1));
    }
    // Cycle-basis role in CF938G: compare the affine XOR space to all reachable walk states.
    for(int n=1;n<=7;++n) for(int trial=0;trial<100;++trial) {
        std::vector<std::tuple<int,int,int>> edges;
        std::vector<std::vector<std::pair<int,int>>> tree(n),graph(n);
        for(int v=1;v<n;++v) {int p=rng()%v,w=rng()%16;edges.push_back({p,v,w});tree[p].push_back({v,w});tree[v].push_back({p,w});}
        for(int extra=0;extra<12;++extra) edges.push_back({int(rng()%n),int(rng()%n),int(rng()%16)});
        std::vector<int> potential(n,-1),stack{0};potential[0]=0;
        for(int at=0;at<int(stack.size());++at) for(auto [u,w]:tree[stack[at]]) if(potential[u]<0) {potential[u]=potential[stack[at]]^w;stack.push_back(u);}
        t9::RollbackXorBasis basis;
        for(auto [u,v,w]:edges) {graph[u].push_back({v,w});graph[v].push_back({u,w});basis.insert(potential[u]^w^potential[v]);}
        for(int start=0;start<n;++start) {
            std::vector<std::array<int,16>> seen(n);std::vector<std::pair<int,int>> q{{start,0}};seen[start][0]=1;
            for(int at=0;at<int(q.size());++at) {auto [v,x]=q[at];for(auto [u,w]:graph[v]) if(!seen[u][x^w]) {seen[u][x^w]=1;q.push_back({u,x^w});}}
            for(int end=0;end<n;++end) {int want=0;while(!seen[end][want]) ++want;assert(basis.minimum(potential[start]^potential[end])==std::uint64_t(want));}
        }
    }
    // Overlapping fixed sets: update every member literally, including signed updates.
    for(int n=1;n<=24;++n) for(int trial=0;trial<35;++trial) {
        int s=1+rng()%20;std::vector<std::vector<int>> groups(s);
        for(auto& group:groups) for(int p=0;p<n;++p) if(rng()%3==0) group.push_back(p);
        std::vector<long long> a(n);for(auto& x:a) x=static_cast<long long>(rng()%101)-50;
        for(int width:{1,2,5,50}) {
            std::vector<__int128> values(a.begin(),a.end());t10::OverlappingSetSums sets(a,groups,width);
            for(int step=0;step<70;++step) {
                int group=rng()%s;long long delta=static_cast<long long>(rng()%31)-15;sets.add(group,delta);
                for(int p:groups[group]) values[p]+=delta;
                for(int g=0;g<s;++g) {__int128 sum=0;for(int p:groups[g]) sum+=values[p];assert(sets.sum(g)==sum);}
            }
        }
    }
    {
        long long maximum=std::numeric_limits<long long>::max();t10::OverlappingSetSums sets({maximum,maximum},{{0,1}},1);
        sets.add(0,maximum);assert(sets.sum(0)==__int128(maximum)*4);
    }
    // Sorted buckets: explicit updates and both strict/non-strict threshold counts.
    for(int n=0;n<=35;++n) for(int width:{1,2,3,7,80}) {
        std::vector<long long> initial(n);for(auto& x:initial) x=static_cast<long long>(rng()%51)-25;
        std::vector<__int128> a(initial.begin(),initial.end());t11::AddCountBuckets buckets(initial,width);
        for(int step=0;step<200;++step) {
            int l=rng()%(n+1),r=rng()%(n+1);if(l>r) std::swap(l,r);long long delta=static_cast<long long>(rng()%31)-15;
            buckets.add(l,r,delta);for(int p=l;p<r;++p) a[p]+=delta;
            l=rng()%(n+1);r=rng()%(n+1);if(l>r) std::swap(l,r);__int128 threshold=static_cast<long long>(rng()%101)-50;
            int less=0;for(int p=l;p<r;++p) less+=a[p]<threshold;
            assert(buckets.count_less(l,r,threshold)==less);assert(buckets.count_at_least(l,r,threshold)==r-l-less);
        }
    }
    {
        long long maximum=std::numeric_limits<long long>::max();t11::AddCountBuckets b({maximum,maximum,maximum},2);
        b.add(0,3,maximum);b.add(1,2,maximum);assert(b.count_at_least(0,3,__int128(maximum)*2)==3);assert(b.count_less(0,3,__int128(maximum)*3)==2);
    }
    std::cout<<"offline coverage properties verified: 12 published implementations\n";
}
'''

def main():
    includes={'#include <random>','#include <iostream>','#include <map>','#include <set>',
              '#include <numeric>','#include <functional>','#include <limits>','#include <tuple>'}
    snippets=[]
    for index,id in enumerate(IDS):
        content=(ROOT/'src/content/docs/techniques'/f'{id}.mdx').read_text()
        match=re.search(r'^```cpp\s*\n(.*?)^```',content,re.M|re.S)
        assert match, f'{id}: actual C++ block missing'
        code=match.group(1);includes.update(re.findall(r'^#include[^\n]+',code,re.M))
        code=re.sub(r'^#include[^\n]+\n?','',code,flags=re.M)
        snippets.append(f'namespace t{index} {{\n{code}\n}}')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-offline-coverage-') as directory:
        source=Path(directory)/'test.cpp';binary=Path(directory)/'test'
        source.write_text('\n'.join(sorted(includes))+'\n'+'\n'.join(snippets)+'\n'+FIXTURE)
        subprocess.run(shlex.split(os.environ.get('CXX','g++'))+['-std=c++20','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],check=True,timeout=60)
        subprocess.run([str(binary)],check=True,timeout=90)

if __name__=='__main__':main()
