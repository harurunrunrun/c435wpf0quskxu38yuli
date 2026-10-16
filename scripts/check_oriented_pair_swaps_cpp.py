#!/usr/bin/env python3
"""Compile the actual MDX C++20 fence and compare every small balanced word to adjacent-swap BFS."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,tempfile

HARNESS=r'''
#include <algorithm>
#include <chrono>
#include <climits>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <unordered_map>
using I=std::int64_t;
using U=std::uint64_t;
U checks=0,bfs_states=0,bfs_edges=0,bfs_families=0,checksum=0;
std::size_t maximum_elements=0;
void require(bool condition,const char* message){
    ++checks;if(!condition){std::cerr<<"FAIL: "<<message<<'\n';std::exit(1);}
}
I run(const std::vector<int>& s){
    const auto saved=s;
    const I answer=minimum_oriented_pair_swaps(s);
    require(s==saved,"public API preserves input");
    require(answer>=0 && answer<=I(s.size())*I(s.size()?s.size()-1:0)/2,"answer is an adjacent permutation distance");
    maximum_elements=std::max(maximum_elements,s.size());
    checksum=checksum*1000003+U(answer);
    return answer;
}
U factorial(int n){U out=1;for(int i=2;i<=n;++i)out*=U(i);return out;}

// Oracle states contain only signed values. Every legal final pair order is a
// source at distance zero. Edges are all adjacent swaps of unequal values.
// Neither pairing, greedy deletions nor Fenwick intervals occur in this oracle.
void family(const std::vector<int>& multiplicities){
    ++bfs_families;
    const int kinds=int(multiplicities.size());
    const int pairs=std::accumulate(multiplicities.begin(),multiplicities.end(),0);
    const int length=2*pairs,base=2*kinds;
    U expected=factorial(length);
    for(int c:multiplicities)expected/=factorial(c)*factorial(c);
    std::vector<U> power(length+1,1);
    for(int p=1;p<=length;++p)power[p]=power[p-1]*U(base);
    std::unordered_map<U,int> distance;distance.reserve(std::size_t(expected));
    std::vector<U> queue;queue.reserve(std::size_t(expected));
    std::vector<int> order;
    for(int k=0;k<kinds;++k)for(int c=0;c<multiplicities[k];++c)order.push_back(k);
    do{
        U code=0;
        for(int p=0;p<pairs;++p)code+=U(2*order[p])*power[2*p]+U(2*order[p]+1)*power[2*p+1];
        if(distance.emplace(code,0).second)queue.push_back(code);
    }while(std::next_permutation(order.begin(),order.end()));
    std::vector<int> digit(length),state(length);
    for(std::size_t head=0;head<queue.size();++head){
        const U code=queue[head];const int d=distance.at(code);U rest=code;
        for(int p=0;p<length;++p){digit[p]=int(rest%U(base));rest/=U(base);state[p]=(digit[p]%2?1:-1)*(digit[p]/2+1);}
        require(run(state)==d,"minimum over all valid pair orders equals adjacent-swap BFS");
        ++bfs_states;
        for(int p=0;p+1<length;++p)if(digit[p]!=digit[p+1]){
            const I delta=I(digit[p+1]-digit[p])*(I(power[p])-I(power[p+1]));
            const U next=U(I(code)+delta);++bfs_edges;
            if(distance.emplace(next,d+1).second)queue.push_back(next);
        }
    }
    require(queue.size()==expected,"BFS visits every balanced signed permutation in its multiset family");
}
void all_families(int kinds,int maximum_pairs){
    std::vector<int> counts(kinds);
    for(int n=1;n<=maximum_pairs;++n){
        auto generate=[&](auto&& self,int at,int left)->void{
            if(at==kinds-1){counts[at]=left;family(counts);return;}
            for(int take=0;take<=left;++take){counts[at]=take;self(self,at+1,left-take);}
        };generate(generate,0,n);
    }
}
void reject(const std::vector<int>& s){
    bool threw=false;try{(void)minimum_oriented_pair_swaps(s);}catch(const std::invalid_argument&){threw=true;}
    require(threw,"invalid sequence rejected");
}
void boundaries(){
    require(run({})==0,"empty sequence");
    require(run({-1,1})==0,"already oriented pair");
    require(run({1,-1})==1,"right-left needs one orientation swap");
    require(run({2,1,-1,-2})==4,"official example 1");
    require(run({-2,2,2,-2,-2,2})==1,"official example 2");
    require(run({-1,1,1,-1})==1,"leftmost matching occurrence beats a later equal occurrence");
    require(run({-INT_MAX,INT_MAX,INT_MAX,-INT_MAX})==1,"sparse maximum label and sign safety");
    for(const auto& s:std::vector<std::vector<int>>{{1},{-1},{0,0},{INT_MIN,1},{1,1},{-1,-1},{1,-2},{1,1,-1,-2},{0,-1,-2,2},{1,-1,0,0},{-3,1,1,3}})reject(s);

    constexpr int n=100000;
    std::vector<int> s;s.reserve(2*n);
    for(int i=1;i<=n;++i)s.push_back(i);
    for(int i=n;i>=1;--i)s.push_back(-i);
    require(run(s)==I(n)*n,"maximum source-size nested reversed pairs require n squared swaps");
    s.clear();for(int i=1;i<=n;++i)s.push_back(-i);for(int i=1;i<=n;++i)s.push_back(i);
    require(run(s)==I(n)*(n-1)/2,"all distinct lefts followed by rights");
    s.clear();for(int i=1;i<=n;++i)s.push_back(i);for(int i=1;i<=n;++i)s.push_back(-i);
    require(run(s)==I(n)*(n+1)/2,"all distinct rights followed by lefts");
    s.clear();for(int i=1;i<=n;++i){s.push_back(-i);s.push_back(i);}
    require(run(s)==0,"maximum source-size valid target");
    s.assign(n,-1);s.insert(s.end(),n,1);
    require(run(s)==I(n)*(n-1)/2,"maximum source-size repeated equal left block");
    s.assign(n,1);s.insert(s.end(),n,-1);
    require(run(s)==I(n)*(n+1)/2,"maximum source-size repeated equal right block");
    s.clear();for(int i=0;i<n;++i){s.push_back(1);s.push_back(-1);}
    require(run(s)==n,"every pair needs its own orientation correction");
    // General API also admits lengths beyond the source maximum.
    s.clear();for(int i=1;i<=100001;++i){s.push_back(-i);s.push_back(i);}
    require(run(s)==0,"no artificial original-size cap in reusable API");

    std::mt19937 rng(20190806);
    for(int trial=0;trial<1000;++trial){
        const int pairs=1+int(rng()%100),kinds=1+int(rng()%pairs);
        s.clear();for(int i=0;i<pairs;++i){const int k=1+int(rng()%kinds);s.push_back(-k);s.push_back(k);}
        std::shuffle(s.begin(),s.end(),rng);const I expected=run(s);
        auto reversed=s;std::reverse(reversed.begin(),reversed.end());for(int& x:reversed)x=-x;
        require(run(reversed)==expected,"reverse and sign flip preserves legal targets and swap distance");
        for(int& x:reversed){const int sign=x<0?-1:1;const int magnitude=x<0?-x:x;x=sign*(INT_MAX-magnitude);}
        require(run(reversed)==expected,"bijective relabeling preserves optimum and sparse labels");
    }
}
int main(){
    const auto start=std::chrono::steady_clock::now();
    all_families(2,5);all_families(3,4);family({1,1,1,1});
    boundaries();
    std::cout<<"{\"checks\":"<<checks<<",\"bfsStates\":"<<bfs_states<<",\"bfsDirectedEdges\":"<<bfs_edges
             <<",\"bfsFamilies\":"<<bfs_families<<",\"maximumElements\":"<<maximum_elements
             <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"
             <<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''
args=[a for a in sys.argv[1:] if a!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/oriented-equal-pair-adjacent-swaps-fenwick.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected exactly one complete visible C++ fence')
with tempfile.TemporaryDirectory(prefix='flowchartcp-shoes-check-') as directory:
    source=Path(directory)/'check.cpp';binary=Path(directory)/'check'
    source.write_text(blocks[0]+'\n'+HARNESS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];environment=os.environ.copy()
    if '--sanitize' in sys.argv:
        flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer'];environment['ASAN_OPTIONS']='detect_leaks=0'
    compiler=environment.get('CXX') or shutil.which('g++') or shutil.which('clang++') or 'c++'
    subprocess.run([compiler,*flags,str(source),'-o',str(binary)],check=True,timeout=120)
    timer=Path('/usr/bin/time');command=[str(binary)]
    if timer.exists() and sys.platform.startswith('linux'):command=[str(timer),'-f','peak_rss_kib=%M',*command]
    result=subprocess.run(command,check=True,text=True,capture_output=True,env=environment,timeout=180)
    report=json.loads(result.stdout);match=re.search(r'^peak_rss_kib=(\d+)$',result.stderr,re.M)
    if match:report['peakRSSKiB']=int(match[1])
    report.update(article=str(article),sanitized='--sanitize' in sys.argv,cppSha256=hashlib.sha256(blocks[0].encode()).hexdigest())
    print(json.dumps(report,ensure_ascii=False,indent=2))
