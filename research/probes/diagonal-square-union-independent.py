#!/usr/bin/env python3
"""Independent constructive path exchange and cell-dilation checks.

Unlike the author checker, this checks the actual q-1/q+1 -> q/q exchange
for every pair of partitions of every strict interval chain on grids <= 9.
Partition costs are literal bitsets of cells, not the overlap recurrence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument('--sanitize', action='store_true')
parser.add_argument('--output', type=Path)
args = parser.parse_args()
article = Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/diagonal-square-union-cover-monge-penalty-cht.mdx'
cpp = re.findall(r'^```cpp\s*\n(.*?)^```\s*$', article.read_text(), re.M | re.S)
assert len(cpp) == 1
expected = '97748db7491b31d9799fc9cdd1e672e4de97aef0221cc6c36a9bded5a874d42c'
assert hashlib.sha256(cpp[0].encode()).hexdigest() == expected
tests = r'''
#include <array>
#include <bit>
#include <chrono>
#include <iostream>
#include <random>
#include <string>
using ll=std::int64_t;
using U=std::uint64_t;
using Bits=__uint128_t;
using Points=std::vector<std::pair<int,int>>;
U checks=0,chains=0,partitions=0,exchanges=0,common=0,nested=0,api=0,dilations=0,checksum=0;
void need(bool ok,const char* name){++checks;if(!ok){std::cerr<<"FAIL "<<name<<'\n';std::exit(1);}}
void mix(U x){checksum=checksum*1000003+x;}
std::vector<int> path(int mask,int n){
    std::vector<int> p{0};
    for(int j=1;j<n;++j)if(mask>>(j-1)&1)p.push_back(j);
    p.push_back(n);return p;
}
int mask_of(const std::vector<int>& p,int n){
    need(p.front()==0&&p.back()==n,"path endpoints");int mask=0;
    for(std::size_t i=1;i<p.size();++i){need(p[i-1]<p[i],"exchanged path strictly increasing");if(p[i]<n)mask|=1<<(p[i]-1);}
    return mask;
}
int literal(const Points& a,int m,int mask){
    Bits cells=0;int at=0;
    for(int i=0;i<int(a.size());++i)if(i+1==int(a.size())||(mask>>i&1)){
        for(int r=a[at].first;r<=a[i].second;++r)
            for(int c=a[at].first;c<=a[i].second;++c)cells|=Bits(1)<<(r*m+c);
        at=i+1;
    }
    return std::popcount(U(cells))+std::popcount(U(cells>>64));
}
void chain(const Points& a,int m){
    const int n=int(a.size()),total=1<<(n-1);++chains;
    std::vector<int> cost(total),best(n+1,1000000);
    std::vector<std::vector<int>> by(n+1);
    for(int mask=0;mask<total;++mask){
        int q=1+std::popcount(unsigned(mask));cost[mask]=literal(a,m,mask);
        by[q].push_back(mask);best[q]=std::min(best[q],cost[mask]);++partitions;
        int formula=0,t=0;
        for(int i=0;i<n;++i)if(i+1==n||(mask>>i&1)){
            int side=a[i].second-a[t].first+1;
            int overlap=t?std::max(0,a[t-1].second-a[t].first+1):0;
            formula+=side*side-overlap*overlap;t=i+1;
        }
        need(formula==cost[mask],"every partition's neighbor correction equals literal cell union");
    }
    for(int k=1;k<=n;++k){
        ll got=minimum_diagonal_square_union(a,m,k);++api;
        need(got==best[k],"API equals exhaustive literal partition union");mix(U(got));
    }
    for(int q=2;q<n;++q)for(int pm:by[q-1])for(int qm:by[q+1]){
        auto p=path(pm,n),r=path(qm,n);std::vector<int> s,t;
        bool done=false;
        // A shared cut only balances counts when Q has one extra prefix edge.
        for(int i=1;i<int(p.size())-1&&!done;++i)for(int j=1;j<int(r.size())-1;++j)
            if(p[i]==r[j]&&j==i+1){
                s.assign(p.begin(),p.begin()+i+1);s.insert(s.end(),r.begin()+j+1,r.end());
                t.assign(r.begin(),r.begin()+j+1);t.insert(t.end(),p.begin()+i+1,p.end());
                ++common;done=true;break;
            }
        if(!done){
            int pi=0,ri=0;
            for(int d=1;d<n&&!done;++d){
                bool pc=pi+1<int(p.size())-1&&p[pi+1]==d;
                bool rc=ri+1<int(r.size())-1&&r[ri+1]==d;
                if(pc)++pi;
                if(rc)++ri;
                if(ri-pi==2){
                    need(rc&&!pc,"first excess two is Q-only cut");
                    const int a0=p[pi],b=r[ri-1],c=p[pi+1];
                    need(a0<=b&&b<d&&d<c,"nested exchange coordinates");
                    need(ri-1==pi+1,"nested prefix edge count gap one");
                    s.assign(p.begin(),p.begin()+pi+1);s.insert(s.end(),r.begin()+ri,r.end());
                    t.assign(r.begin(),r.begin()+ri);t.insert(t.end(),p.begin()+pi+1,p.end());
                    ++nested;done=true;
                }
            }
        }
        need(done,"every q-1/q+1 pair admits a prescribed exchange");
        need(int(s.size())==q+1&&int(t.size())==q+1,"both exchanged paths have q edges");
        int sm=mask_of(s,n),tm=mask_of(t,n);
        need(cost[sm]+cost[tm]<=cost[pm]+cost[qm],"constructive exchange does not increase literal union sum");
        mix(U(cost[sm]+cost[tm]));++exchanges;
    }
}
void enumerate(Points& a,int m,int last_l,int last_r){
    for(int l=last_l+1;l<m;++l)for(int r=std::max(l,last_r+1);r<m;++r){
        a.emplace_back(l,r);chain(a,m);enumerate(a,m,l,r);a.pop_back();
    }
}
void dilation(){
    std::mt19937 rng(2016081602);
    for(int trial=0;trial<3000;++trial){
        const int m=1+int(rng()%40),n=1+int(rng()%40),k=1+int(rng()%n);
        Points a;for(int i=0;i<n;++i)a.emplace_back(int(rng()%m),int(rng()%m));
        const ll base=minimum_diagonal_square_union(a,m,k);++api;
        const int d=1+int(rng()%(1000000/m));
        const int shift=int(rng()%unsigned(1000000-d*m+1));
        Points scaled;
        for(auto [r,c]:a){
            int lo=std::min(r,c),hi=std::max(r,c);
            scaled.emplace_back(d*lo+shift,d*(hi+1)+shift-1);
        }
        ll got=minimum_diagonal_square_union(scaled,d*m+shift,k);++api;
        need(got==ll(d)*d*base,"cell dilation scales each covered square and its union by d squared");
        // Add a reflected duplicate of each requirement, plus contained cells.
        Points redundant=scaled;
        for(auto [lo,hi]:scaled){redundant.emplace_back(hi,lo);redundant.emplace_back(lo,lo);}
        std::shuffle(redundant.begin(),redundant.end(),rng);
        need(minimum_diagonal_square_union(redundant,d*m+shift,k)==got,"dilation then reflected duplicates and contained demands");++api;
        mix(U(got));++dilations;
    }
}
int main(){
    auto start=std::chrono::steady_clock::now();
    for(int m=1;m<=9;++m){Points a;enumerate(a,m,-1,-1);}
    dilation();
    need(common>0&&nested>0,"both common-cut and strict nested exchange branches exercised");
    std::cout<<"{\"checks\":"<<checks<<",\"strictIntervalChainsGrid1to9\":"<<chains
             <<",\"literalCellUnionPartitions\":"<<partitions<<",\"constructiveTwoPathExchanges\":"<<exchanges
             <<",\"commonCutExchanges\":"<<common<<",\"nestedEdgeExchanges\":"<<nested
             <<",\"apiCalls\":"<<api<<",\"cellDilationCases\":"<<dilations
             <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"
             <<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-aliens-independent-') as tmp:
    source = Path(tmp) / 'probe.cpp'
    binary = Path(tmp) / 'probe'
    source.write_text(cpp[0] + '\n' + tests)
    flags = ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror']
    env = dict(os.environ)
    if args.sanitize:
        flags = ['-std=c++20', '-O1', '-g', '-Wall', '-Wextra', '-Werror',
                 '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
        env['ASAN_OPTIONS'] = 'detect_leaks=0:halt_on_error=1'
        env['UBSAN_OPTIONS'] = 'halt_on_error=1:print_stacktrace=1'
    subprocess.run(['g++', *flags, str(source), '-o', str(binary)], check=True, timeout=120)
    run = subprocess.run(['/usr/bin/time', '-f', 'peak_rss_kib=%M', str(binary)],
                         capture_output=True, text=True, env=env, timeout=300)
    if run.returncode:
        print(run.stdout, end='')
        print(run.stderr, end='')
        run.check_returncode()
    result = json.loads(run.stdout)
    result.update(cppSha256=expected, sanitized=args.sanitize,
                  peakRSSKiB=int(re.search(r'peak_rss_kib=(\d+)', run.stderr)[1]))
    output = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.output:
        args.output.write_text(output)
    print(output, end='')
