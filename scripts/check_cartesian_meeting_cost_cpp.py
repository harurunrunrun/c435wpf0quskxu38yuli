#!/usr/bin/env python3
"""Extract actual public C++20; literal every-site/participant/max oracle."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile
args=[x for x in sys.argv[1:] if x!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/cartesian-prefix-meeting-cost-single-cross-envelope.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected one visible complete C++20 fence')
TESTS=r'''
#include <bit>
#include <chrono>
#include <climits>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <random>
using LL=long long;using U=std::uint64_t;using Interval=std::pair<int,int>;
U checks=0,checksum=0,small_arrays=0,small_queries=0,oriented_queries=0,random_arrays=0,random_queries=0;
U maximum_cases=0,maximum_queries=0,invalid_calls=0;LL maximum_cost=0;
void need(bool x,const char* why){++checks;if(!x){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
void absorb(LL x){checksum=checksum*1000003+U(x)+1;maximum_cost=std::max(maximum_cost,x);}
// Three explicit loops: try EVERY site, EVERY participant, EVERY intervening
// height. This oracle uses no Cartesian split, DP, envelope or minimum shortcut.
LL literal(const std::vector<int>& h,int l,int r){
    LL answer=std::numeric_limits<LL>::max();
    for(int site=l;site<=r;++site){LL total=0;
        for(int person=l;person<=r;++person){int tallest=0;
            for(int pos=std::min(site,person);pos<=std::max(site,person);++pos)tallest=std::max(tallest,h[pos]);
            total+=tallest;
        }answer=std::min(answer,total);
    }return answer;
}
// Still enumerate every site/participant, reusing only the literal running max
// while expanding away from that site. Crosschecked with the slower oracle.
LL enumerate_sites(const std::vector<int>& h,int l,int r){
    if(l>r)return 0;
    LL answer=std::numeric_limits<LL>::max();
    for(int site=l;site<=r;++site){LL total=h[site];int tallest=h[site];
        for(int person=site-1;person>=l;--person){tallest=std::max(tallest,h[person]);total+=tallest;}
        tallest=h[site];for(int person=site+1;person<=r;++person){tallest=std::max(tallest,h[person]);total+=tallest;}
        answer=std::min(answer,total);
    }return answer;
}
std::vector<Interval> all_intervals(int n){std::vector<Interval> out;for(int l=0;l<n;++l)for(int r=l;r<n;++r)out.emplace_back(l,r);return out;}
void verify_small(const std::vector<int>& h){
    const int n=int(h.size());const auto queries=all_intervals(n);std::vector<LL> truth(n*n);
    for(auto [l,r]:queries){truth[l*n+r]=literal(h,l,r);need(truth[l*n+r]==enumerate_sites(h,l,r),"independent site expansion oracle equals literal every max");}
    const auto unchanged=h;auto actual=minimum_interval_meeting_costs(h,queries);
    need(actual.size()==queries.size()&&h==unchanged,"output size and unchanged height input");
    for(std::size_t i=0;i<queries.size();++i){auto [l,r]=queries[i];need(actual[i]==truth[l*n+r],"all-small answer equals all sites/participants/maxima");absorb(actual[i]);++small_queries;}
    // Check each direction separately, so a correct minimum cannot mask one bad DP.
    if(n<=7){
        std::vector<int> peak(queries.size());
        for(std::size_t i=0;i<queries.size();++i){auto [l,r]=queries[i];int v=l;
            for(int p=l+1;p<=r;++p)if(h[p]>=h[v])v=p;
            peak[i]=v;
        }
        for(bool reversed:{false,true}){
            std::vector<LL> candidate(queries.size(),std::numeric_limits<LL>::max());
            meeting_envelope_detail::direction(h,queries,peak,reversed,candidate);
            for(std::size_t i=0;i<queries.size();++i){auto [l,r]=queries[i];int v=peak[i];
                LL want=reversed?LL(r-v+1)*h[v]+(v==l?0:truth[l*n+v-1]):LL(v-l+1)*h[v]+(v==r?0:truth[(v+1)*n+r]);
                need(candidate[i]==want,"each oriented candidate independently equals direct suffix/prefix optimum");++oriented_queries;
            }
        }
    }
    ++small_arrays;
}
void exhaustive(){
    for(int alphabet=0;alphabet<2;++alphabet){
        const std::vector<int> values=alphabet==0?std::vector<int>{1,2,3}:std::vector<int>{1,2,7,1000000000};
        for(int n=1;n<=(alphabet==0?9:7);++n){std::vector<int> h(n);
            auto all=[&](auto&& self,int at)->void{if(at==n){verify_small(h);return;}for(int x:values){h[at]=x;self(self,at+1);}};all(all,0);
        }
    }
    need(small_arrays==51367,"all ternary arrays N1..9 and four-value arrays N1..7");
}
void random_and_properties(){
    std::mt19937 random(20180905);
    for(int test=0;test<500;++test){
        int n=1+int(random()%150);std::vector<int> h(n);for(int& x:h)x=test%3==0?1+int(random()%4):1+int(random()%1000000000);
        std::vector<Interval> queries;for(int q=0;q<200;++q){int l=int(random()%n),r=int(random()%n);if(l>r)std::swap(l,r);queries.emplace_back(l,r);}
        auto actual=minimum_interval_meeting_costs(h,queries);
        for(std::size_t i=0;i<queries.size();++i){auto [l,r]=queries[i];need(actual[i]==enumerate_sites(h,l,r),"random answer equals enumeration of every meeting site and participant");absorb(actual[i]);++random_queries;}
        auto reversed=h;std::reverse(reversed.begin(),reversed.end());auto mirror=queries;
        for(auto& [l,r]:mirror){int nl=n-1-r;r=n-1-l;l=nl;}
        need(actual==minimum_interval_meeting_costs(reversed,mirror),"reflection preserves optimal costs even with ties");
        ++random_arrays;
    }
    need(minimum_interval_meeting_costs({2,1,2},{{0,2}})==std::vector<LL>{5},"fixed original tie witness5, not6");
    need(minimum_interval_meeting_costs({2,4,3,5},{{0,2},{1,3}})==std::vector<LL>({10,12}),"original example");
    need(minimum_interval_meeting_costs({1000000000},{{0,0},{0,0}})==std::vector<LL>({1000000000,1000000000}),"singleton and duplicate-query extension");
    need(minimum_interval_meeting_costs({1},{}).empty(),"empty batch extension");
    for(int repeat=0;repeat<100;++repeat){
        need(minimum_interval_meeting_costs({3,1,3},{{0,2}})==std::vector<LL>{7},"fresh call after other tree states");
        need(minimum_interval_meeting_costs({1,5,2},{{0,1},{0,2},{1,2}})==std::vector<LL>({6,11,7}),"interleaved calls retain no map/offset/query state");
    }
}
struct Runs{int length=0,left=0,right=0,best=0;};
Runs join(Runs a,Runs b){return {a.length+b.length,a.left==a.length?a.length+b.left:a.left,b.right==b.length?b.length+a.right:b.right,std::max({a.best,b.best,a.right+b.left})};}
std::vector<LL> binary_truth(const std::vector<int>& h,const std::vector<Interval>& queries){
    int base=1;while(base<int(h.size()))base*=2;std::vector<Runs> tree(2*base);
    for(int i=0;i<int(h.size());++i)tree[base+i]={1,h[i]==1,h[i]==1,h[i]==1};
    for(int i=base-1;i>0;--i)tree[i]=join(tree[2*i],tree[2*i+1]);
    std::vector<LL> out;out.reserve(queries.size());
    for(auto [l,r]:queries){Runs a,b;for(l+=base,r+=base+1;l<r;l/=2,r/=2){if(l&1)a=join(a,tree[l++]);if(r&1)b=join(tree[--r],b);}auto result=join(a,b);
        out.push_back(1000000000LL*result.length-999999999LL*result.best);
    }return out;
}
void maximum(){
    constexpr int n=750000;std::mt19937 random(1843);
    for(int kind=0;kind<7;++kind){
        std::vector<int> h(n);std::vector<Interval> queries;queries.reserve(n);
        for(int i=0;i<n;++i){
            h[i]=kind==0?1000000000:kind==1?i+1:kind==2?1000000000-i:kind==3?(i%2?1000000000:1):kind==4?1+int(std::countr_zero(static_cast<unsigned>(i+1))):kind==5?1+int(random()%1000000000):(random()%3?1000000000:1);
            int l=i/2;
            if(kind==0)l=0;
            else if(kind==4||kind==5)l=std::max(0,i-int(random()%16));
            else if(kind==6)l=int(random()%(i+1));
            else if(i%8==0)l=i;
            else if(i%8==1)l=0;
            queries.emplace_back(l,i); // R unique: all original query pairs distinct
        }
        std::vector<LL> expected;
        if(kind==6)expected=binary_truth(h,queries); // this oracle freed before library run
        else if(kind==4||kind==5){expected.reserve(n);for(auto [l,r]:queries)expected.push_back(enumerate_sites(h,l,r));}
        else {std::vector<LL> sum(n+1);for(int i=0;i<n;++i)sum[i+1]=sum[i]+h[i];
            for(auto [l,r]:queries){int length=r-l+1;
                expected.push_back(kind==0?1000000000LL*length:kind==1||kind==2?sum[r+1]-sum[l]:1000000000LL*length-((length>1||l%2==0)?999999999LL:0));
            }
        }
        auto actual=minimum_interval_meeting_costs(h,queries);
        need(actual.size()==n,"maximum original Q executed");
        for(int i=0;i<n;++i){need(actual[i]==expected[i],"maximum N/Q answer equals independent closed form/site enumeration/binary run oracle");absorb(actual[i]);++maximum_queries;}
        ++maximum_cases;
    }
    need(maximum_cost==750000000000000LL,"original maximum possible64bit answer attained");
}
void reject(const std::vector<int>& heights,const std::vector<Interval>& queries){
    bool caught=false;try{(void)minimum_interval_meeting_costs(heights,queries);}catch(const std::invalid_argument&){caught=true;}
    need(caught,"invalid public API argument rejected");++invalid_calls;
}
void invalid(){
    reject({},{});reject(std::vector<int>(750001,1),{});reject({1},std::vector<Interval>(750001,{0,0}));
    for(int h:{INT_MIN,-1,0,1000000001,INT_MAX})reject({h},{}); // validate even if Q0
    for(auto interval:std::vector<Interval>{{-1,0},{0,3},{2,1},{INT_MIN,0},{0,INT_MAX},{-1,-1},{3,3}})reject({1,2,3},{interval});
    need(minimum_interval_meeting_costs({2,1,2},{{0,2}})==std::vector<LL>{5},"valid state after every exception");
}
int main(){
    const auto start=std::chrono::steady_clock::now();exhaustive();random_and_properties();invalid();maximum();
    std::cout<<"{\"checks\":"<<checks<<",\"smallArrays\":"<<small_arrays<<",\"smallQueries\":"<<small_queries
      <<",\"orientedQueries\":"<<oriented_queries<<",\"randomArrays\":"<<random_arrays<<",\"randomQueries\":"<<random_queries
      <<",\"maximumCases\":"<<maximum_cases<<",\"maximumQueries\":"<<maximum_queries<<",\"maximumCost\":"<<maximum_cost
      <<",\"invalidCalls\":"<<invalid_calls<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"
      <<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-meetings-build-') as tmp:
    source=Path(tmp)/'check.cpp';binary=Path(tmp)/'check';source.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];env=dict(os.environ)
    if '--sanitize' in sys.argv:
        flags=['-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
        env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True,timeout=120)
    command=[str(binary)]
    if Path('/usr/bin/time').exists():command=['/usr/bin/time','-f','peak_rss_kib=%M',*command]
    result=subprocess.run(command,text=True,capture_output=True,env=env,timeout=300)
    if result.returncode:
        print(result.stdout,end='',file=sys.stderr);print(result.stderr,end='',file=sys.stderr);result.check_returncode()
    report=json.loads(result.stdout);match=re.search(r'^peak_rss_kib=(\d+)$',result.stderr,re.M)
    if match:report['peakRSSKiB']=int(match[1])
    report.update(cppSha256=hashlib.sha256(blocks[0].encode()).hexdigest(),sanitized='--sanitize' in sys.argv)
    print(json.dumps(report,ensure_ascii=False))
