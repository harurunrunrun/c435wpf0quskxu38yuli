#!/usr/bin/env python3
"""Compile actual visible C++20; group EVERY small permutation by its observations."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,tempfile

TESTS=r'''
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
using U=std::uint64_t;
U checks=0,permutations=0,observation_groups=0,oracle_queries=0,semantic_vectors=0;
U impossible_vectors=0,random_instances=0,random_queries=0,maximum_queries=0,checksum=0;
int largest_n=0,maximum_levels=0;double maximum_construction_seconds=0,maximum_query_seconds=0;
void require(bool good,const char* why){++checks;if(!good){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
void absorb(int value){checksum=checksum*1000003+U(value+2);}
std::vector<int> observed(int k,const std::vector<int>& heights){
    const int n=int(heights.size());std::vector<int> out(n);
    for(int i=0;i<n;++i)for(int step=1;step<k;++step)
        out[i]+=heights[(i+step)%n]>heights[i];
    return out;
}
U comparisons(const std::vector<int>& heights){
    const int n=int(heights.size());U mask=0;
    for(int i=0;i<n;++i)for(int j=0;j<n;++j)if(heights[i]>heights[j])mask|=U{1}<<(i*n+j);
    return mask;
}
std::vector<U> explicit_closure(int k,const std::vector<int>& heights){
    const int n=int(heights.size());std::vector<U> reach(n);
    for(int i=0;i<n;++i)for(int j=0;j<n;++j)
        if(i!=j&&heights[i]>heights[j]&&((j-i+n)%n<k||(i-j+n)%n<k))reach[i]|=U{1}<<j;
    for(int mid=0;mid<n;++mid)for(int i=0;i<n;++i)if(reach[i]>>mid&1)reach[i]|=reach[mid];
    return reach;
}
struct Group{U mandatory,possible,count;};
void validate_representative(const CyclicWindowOrder& model,int k,const std::vector<int>& counts){
    const auto& rank=model.representative_rank();const int n=int(rank.size());
    auto sorted=rank;std::sort(sorted.begin(),sorted.end());
    for(int i=0;i<n;++i)require(sorted[i]==i,"representative is a permutation of all ranks");
    std::vector<int> heights(n);for(int i=0;i<n;++i)heights[i]=n-1-rank[i];
    require(observed(k,heights)==counts,"representative reproduces every count by literal clockwise comparisons");
}
void exhaustive(){
    for(int n=1;n<=8;++n)for(int k=1;k<=n;++k){
        std::map<std::vector<int>,Group> groups;
        std::vector<int> heights(n);std::iota(heights.begin(),heights.end(),0);
        do{
            const auto counts=observed(k,heights);const U relation=comparisons(heights);
            auto [it,inserted]=groups.try_emplace(counts,Group{relation,relation,0});
            (void)inserted;it->second.mandatory&=relation;it->second.possible|=relation;++it->second.count;++permutations;
        }while(std::next_permutation(heights.begin(),heights.end()));
        for(const auto& [counts,group]:groups){
            const auto unchanged=counts;CyclicWindowOrder model(k,counts);++observation_groups;
            validate_representative(model,k,counts);require(counts==unchanged,"input counts not modified");
            // Mandatory relation is the INTERSECTION over ALL permutations in this
            // exact observation group. No segment tree, graph or greedy oracle.
            for(int x=0;x<n;++x)for(int y=0;y<n;++y){
                const int expected=(group.mandatory>>(x*n+y)&1)?1:(group.mandatory>>(y*n+x)&1)?-1:0;
                const int actual=model.compare(x,y);require(actual==expected,"query equals comparison common to EVERY consistent permutation");
                if(x!=y&&expected==0)require((group.possible>>(x*n+y)&1)&&(group.possible>>(y*n+x)&1),"ambiguous0 has witnesses in both strict directions");
                absorb(actual);++oracle_queries;
            }
            std::vector<int> representative(n);
            for(int x=0;x<n;++x)representative[x]=n-1-model.representative_rank()[x];
            const auto reach=explicit_closure(k,representative);U full=0;
            for(int x=0;x<n;++x)for(int y=0;y<n;++y)if(reach[x]>>y&1)full|=U{1}<<(x*n+y);
            require(full==group.mandatory,"independently check poset/linear-extension lemma against full permutation groups");
        }
        if(n<=6){
            std::vector<int> candidate(n);
            auto enumerate=[&](auto&& self,int at)->void{
                if(at<n){for(int value=0;value<k;++value){candidate[at]=value;self(self,at+1);}return;}
                ++semantic_vectors;const bool exists=groups.contains(candidate);bool accepted=false;
                try{CyclicWindowOrder model(k,candidate);accepted=true;}catch(const std::invalid_argument&){}
                require(accepted==exists,"ALL in-range small count vectors accepted iff some actual permutation generates them");
                impossible_vectors+=!exists;
            };enumerate(enumerate,0);
        }
    }
    require(permutations==362879,"all permutations for every N1..8 and every K1..N");
}
void randomized(){
    std::mt19937 rng(20200916);
    for(int test=0;test<1500;++test){
        const int n=2+int(rng()%59),k=1+int(rng()%n);std::vector<int> heights(n);std::iota(heights.begin(),heights.end(),0);
        std::shuffle(heights.begin(),heights.end(),rng);const auto counts=observed(k,heights);
        const auto reach=explicit_closure(k,heights);CyclicWindowOrder model(k,counts);
        validate_representative(model,k,counts);
        for(int x=0;x<n;++x)for(int y=0;y<n;++y){
            const int expected=(reach[x]>>y&1)?1:(reach[y]>>x&1)?-1:0;
            const int actual=model.compare(x,y);require(actual==expected,"random larger case equals explicit full near-comparison DAG closure");absorb(actual);++random_queries;
        }
        ++random_instances;
    }
}
void rejects(int k,const std::vector<int>& counts){
    bool threw=false;try{CyclicWindowOrder model(k,counts);}catch(const std::invalid_argument&){threw=true;}
    require(threw,"invalid dimensions/range/inconsistent observations rejected");
}
void boundaries(){
    CyclicWindowOrder a(3,{0,1,1,2});require(a.compare(0,2)==1&&a.compare(1,2)==-1,"official example1");
    CyclicWindowOrder b(2,{0,1,0,1});require(b.compare(0,3)==1&&b.compare(1,3)==0,"official example2 and ambiguity not a tie");
    require(b.compare(3,0)==-1&&b.compare(3,1)==0&&b.compare(0,0)==0,"reverse and identical-index API extension");
    CyclicWindowOrder singleton(1,{0});require(singleton.compare(0,0)==0,"single target K1 extension");
    CyclicWindowOrder no_information(1,{0,0,0});require(no_information.compare(0,2)==0,"K1 has no comparison information");
    rejects(1,{});rejects(0,{0});rejects(-1,{0});rejects(2,{0});rejects(200001,std::vector<int>(200001));
    rejects(1,{-1});rejects(1,{1});rejects(2,{0,2});rejects(2,{0,-1});rejects(2,{0,0});rejects(2,{1,1});
    rejects(3,{0,0,0,0}); // A directed cyclic contradiction despite in-range entries.
    for(auto [x,y]:std::vector<std::pair<int,int>>{{-1,0},{0,-1},{4,0},{0,4},{-1,-1},{4,4}}){
        bool threw=false;try{(void)a.compare(x,y);}catch(const std::invalid_argument&){threw=true;}
        require(threw,"query validation precedes same-index shortcut");
    }
    const auto original=a.representative_rank();CyclicWindowOrder copy=a;
    require(copy.compare(0,2)==1&&a.representative_rank()==original,"copy construction preserves independent tables");
    CyclicWindowOrder moved=std::move(copy);bool state=false;
    try{(void)copy.compare(0,1);}catch(const std::invalid_argument&){require(false,"moved state is not a query-range error");}catch(const std::logic_error&){state=true;}
    require(state&&moved.compare(0,2)==1,"move leaves a checked unusable source and valid destination");
    state=false;try{(void)copy.representative_rank();}catch(const std::logic_error&){state=true;}
    require(state,"moved-from rank access throws");
    copy=b;require(copy.compare(1,3)==0&&a.compare(1,2)==-1,"copy assignment and interleaved separate instances");
    copy=copy;require(copy.compare(0,3)==1,"self copy assignment");
    auto* same_object=&copy;copy=std::move(*same_object);require(copy.compare(0,3)==1,"self move assignment preserves data");
    copy=std::move(moved);require(copy.compare(1,2)==-1,"move assignment restores correct tables");
}
void maximum_case(int k,int mode,int queries){
    constexpr int n=200000;std::vector<int> counts(n);
    if(mode==0)for(int i=0;i<n;++i)counts[i]=std::min(k-1,n-1-i); // heights[i]=i
    else if(mode==1)for(int i=0;i<n;++i)counts[i]=i%2; // alternating local maxima/minima,K2
    const auto before=std::chrono::steady_clock::now();CyclicWindowOrder model(k,counts);
    maximum_construction_seconds=std::max(maximum_construction_seconds,
        std::chrono::duration<double>(std::chrono::steady_clock::now()-before).count());
    int levels=1;while((1<<levels)<n)++levels;maximum_levels=std::max(maximum_levels,levels);largest_n=n;
    const auto begin_queries=std::chrono::steady_clock::now();
    for(int q=0;q<queries;++q){
        int x=int(U(q)*100003%n),y=int((U(q)*91771+12345)%n);
        if(mode==1&&q%4==0)y=(x+1)%n;
        if(x==y)y=(y+1)%n;
        if(x>y)std::swap(x,y); // Original x<y range, including wrap adjacency.
        int expected=0;
        if(mode==0)expected=x>y?1:-1;
        else if(mode==1&&(y-x==1||y-x==n-1))expected=x%2?-1:1;
        const int actual=model.compare(x,y);require(actual==expected,"original maximumN/K/Q with independently known forced/ambiguous relations");absorb(actual);++maximum_queries;
    }
    maximum_query_seconds=std::max(maximum_query_seconds,
        std::chrono::duration<double>(std::chrono::steady_clock::now()-begin_queries).count());
}
int main(){
    const auto start=std::chrono::steady_clock::now();exhaustive();randomized();boundaries();
    maximum_case(2,0,200000);maximum_case(2,1,200000);
    maximum_case(100000,0,200000);maximum_case(199999,0,200000);maximum_case(200000,0,200000);
    maximum_case(1,2,200000);
    require(largest_n==200000&&maximum_levels==18,"all source bounds and maximum18 jump levels executed");
    std::cout<<"{\"checks\":"<<checks<<",\"permutations\":"<<permutations<<",\"observationGroups\":"<<observation_groups
             <<",\"oracleQueries\":"<<oracle_queries<<",\"semanticVectors\":"<<semantic_vectors<<",\"impossibleVectors\":"<<impossible_vectors
             <<",\"randomInstances\":"<<random_instances<<",\"randomQueries\":"<<random_queries<<",\"maximumQueries\":"<<maximum_queries
             <<",\"maximumN\":"<<largest_n<<",\"maximumJumpLevels\":"<<maximum_levels
             <<",\"maximumConstructionSeconds\":"<<maximum_construction_seconds<<",\"maximumQueryBatchSeconds\":"<<maximum_query_seconds
             <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''

args=[arg for arg in sys.argv[1:] if arg!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/cyclic-window-height-poset-two-neighbor-doubling.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected one complete visible C++20 fence')
with tempfile.TemporaryDirectory(prefix='flowchartcp-plants-check-') as directory:
    source=Path(directory)/'check.cpp';binary=Path(directory)/'check';source.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];environment=os.environ.copy()
    if '--sanitize' in sys.argv:
        flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
        environment['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';environment['UBSAN_OPTIONS']='halt_on_error=1'
    compiler=environment.get('CXX') or shutil.which('g++') or shutil.which('clang++') or 'c++'
    subprocess.run([compiler,*flags,str(source),'-o',str(binary)],check=True,timeout=120)
    command=[str(binary)];timer=Path('/usr/bin/time')
    if timer.exists() and sys.platform.startswith('linux'):command=[str(timer),'-f','peak_rss_kib=%M',*command]
    result=subprocess.run(command,text=True,capture_output=True,env=environment,timeout=240)
    if result.returncode:
        print(result.stdout,end='',file=sys.stderr);print(result.stderr,end='',file=sys.stderr);result.check_returncode()
    report=json.loads(result.stdout);match=re.search(r'^peak_rss_kib=(\d+)$',result.stderr,re.M)
    if match:report['peakRSSKiB']=int(match[1])
    report.update(article=str(article),sanitized='--sanitize' in sys.argv,cppSha256=hashlib.sha256(blocks[0].encode()).hexdigest())
    print(json.dumps(report,ensure_ascii=False,indent=2))
