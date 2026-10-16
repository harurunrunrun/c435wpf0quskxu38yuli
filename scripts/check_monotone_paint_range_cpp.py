#!/usr/bin/env python3
"""Compile the actual visible C++20 and compare to legal brush-action BFS."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,tempfile

TESTS=r'''
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <random>
using I=std::int64_t;using U=std::uint64_t;
U checks=0,bfs_states=0,bfs_actions=0,arrays=0,exhaustive_queries=0,random_cases=0,random_queries=0,maximum_queries=0,checksum=0;
int maximum_n=0,maximum_q=0;double maximum_case_seconds=0;
void require(bool condition,const char* why){++checks;if(!condition){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
void absorb(int value){checksum=checksum*1000003+U(value+2);}
std::vector<std::vector<int>> literal_painting_bfs(){
    std::vector<std::vector<int>> tables(9);tables[0]={0};
    for(int n=1;n<=8;++n){
        const int states=1<<(2*n);auto& distance=tables[n];distance.assign(states,-1);distance[0]=0;
        std::vector<int> queue{0};queue.reserve(states);
        for(std::size_t head=0;head<queue.size();++head){
            const int state=queue[head];
            for(int left=0;left<n;++left){
                int mask=0,ones=0,darkest=0;
                for(int right=left;right<n;++right){
                    mask|=3<<(2*right);ones|=1<<(2*right);darkest=std::max(darkest,state>>(2*right)&3);
                    for(int color=std::max(1,darkest);color<=3;++color){
                        // A true legal contiguous brush action, independent of links/stacks/Fenwick.
                        const int next=(state&~mask)|(color*ones);++bfs_actions;
                        if(distance[next]<0){distance[next]=distance[state]+1;queue.push_back(next);}
                    }
                }
            }
        }
        require(int(queue.size())==states,"every legal cell state reached by literal monotone-color brush actions");bfs_states+=queue.size();
    }
    return tables;
}
int encode(const std::vector<I>& colors,int left,int right){int state=0;for(int i=left;i<right;++i)state|=int(colors[i])<<(2*(i-left));return state;}
void exhaustive(const std::vector<std::vector<int>>& tables){
    for(int n=1;n<=8;++n){
        int count=1;for(int i=0;i<n;++i)count*=3;
        for(int code=0;code<count;++code){
            int digits=code;std::vector<I> colors(n);for(I& color:colors){color=1+digits%3;digits/=3;}
            std::vector<std::pair<int,int>> queries;
            for(int left=0;left<=n;++left)for(int right=left;right<=n;++right)queries.push_back({left,right});
            std::reverse(queries.begin(),queries.end()); // NOT sorted by endpoint; output must stay in input order.
            if(code%2)std::rotate(queries.begin(),queries.begin()+queries.size()/2,queries.end());
            const auto colors_before=colors;const auto queries_before=queries;
            const auto answer=range_monotone_paint_strokes(colors,queries);require(answer.size()==queries.size(),"one answer per query");
            for(std::size_t i=0;i<queries.size();++i){
                const auto [l,r]=queries[i];const int expected=tables[r-l][encode(colors,l,r)];
                require(answer[i]==expected,"ALL small target color arrays and ALL half-open subintervals equal literal painting BFS minimum");
                absorb(answer[i]);++exhaustive_queries;
            }
            require(colors==colors_before&&queries==queries_before,"exhaustive constructor/function does not modify either input");++arrays;
        }
    }
    require(arrays==9840&&bfs_states==87380,"all3-color arrayslength1..8 and every4-state brush configuration enumerated");
}
int minimum_color_decomposition(const std::vector<I>& colors,int left,int right){
    // An independent optimum oracle: paint the minimum color across the range,
    // then recursively paint blocks separated by those final-minimum cells.
    if(left==right)return 0;
    const I smallest=*std::min_element(colors.begin()+left,colors.begin()+right);int answer=1,begin=left;
    for(int i=left;i<right;++i)if(colors[i]==smallest){answer+=minimum_color_decomposition(colors,begin,i);begin=i+1;}
    return answer+minimum_color_decomposition(colors,begin,right);
}
void randomized(){
    std::mt19937 rng(1116);
    for(int test=0;test<1800;++test){
        const int n=int(rng()%201),q=300;std::vector<I> colors(n);
        for(int i=0;i<n;++i){
            const int type=int(rng()%17);
            colors[i]=type==0?std::numeric_limits<I>::min():type==1?std::numeric_limits<I>::max():I(int(rng()%31)-15);
        }
        std::vector<std::pair<int,int>> queries(q),reversed_queries(q);
        for(int i=0;i<q;++i){int l=int(rng()%(n+1)),r=int(rng()%(n+1));if(l>r)std::swap(l,r);queries[i]={l,r};reversed_queries[i]={n-r,n-l};}
        const auto before=colors;const auto queries_before=queries;
        const auto answer=range_monotone_paint_strokes(colors,queries);
        auto reflection=colors;std::reverse(reflection.begin(),reflection.end());const auto reversed=range_monotone_paint_strokes(reflection,reversed_queries);
        auto palette=colors;std::sort(palette.begin(),palette.end());palette.erase(std::unique(palette.begin(),palette.end()),palette.end());
        auto ranks=colors;for(I& x:ranks)x=std::lower_bound(palette.begin(),palette.end(),x)-palette.begin();
        const auto remapped=range_monotone_paint_strokes(ranks,queries);
        for(int i=0;i<q;++i){
            const auto [l,r]=queries[i];const int expected=minimum_color_decomposition(colors,l,r);
            require(answer[i]==expected,"random larger arrays equal independent minimum-color recursive optimum");
            require(reversed[i]==expected&&remapped[i]==expected,"reflection and arbitrary strictly-increasing color remapping preserve answers, including equal/extreme/negative colors");
            absorb(answer[i]);++random_queries;
        }
        require(colors==before&&queries==queries_before,"random inputs preserved");++random_cases;
    }
}
void rejects(const std::vector<I>& colors,const std::vector<std::pair<int,int>>& queries){
    const auto colors_before=colors;const auto queries_before=queries;bool threw=false;
    try{(void)range_monotone_paint_strokes(colors,queries);}catch(const std::invalid_argument&){threw=true;}
    require(threw&&colors==colors_before&&queries==queries_before,"invalid size/query throws invalid_argument without changing either input");
}
void boundaries(){
    const std::vector<I> sample{1,2,2,1,1,2,3,2};const std::vector<std::pair<int,int>> original_queries{{3,6},{2,6},{0,6},{4,8}};
    require(range_monotone_paint_strokes(sample,original_queries)==std::vector<int>({2,3,3,3}),"official1basedinclusive sample correctly adapted to0basedhalfopen");
    require(range_monotone_paint_strokes({2,1,2},{{0,3}})==std::vector<int>{3},"lighter interior forbids joining equal dark endpoints");
    require(range_monotone_paint_strokes({1,2,1},{{0,3},{0,1},{1,2},{1,3}})==std::vector<int>({2,1,1,2}),"darker interior allows outer color, but outside query stays unpainted");
    require(range_monotone_paint_strokes({1,1,1},{{0,3},{1,3}})==std::vector<int>({1,1}),"three equal positions give ONLYconsecutive links, not all equal pairs");
    require(range_monotone_paint_strokes({3,2,3,1,3,2,3},{{0,7},{0,3},{4,7}})==std::vector<int>({7,3,3}),"lower-color barrier splits old same-color candidates");
    require(range_monotone_paint_strokes({},{}).empty(),"empty input/no queries");
    require(range_monotone_paint_strokes({},{{0,0},{0,0}})==std::vector<int>({0,0}),"empty range at empty input is0");
    require(range_monotone_paint_strokes({0,-1,0},{}).empty(),"no questions extension with signed colors");
    require(range_monotone_paint_strokes({std::numeric_limits<I>::min(),std::numeric_limits<I>::max(),std::numeric_limits<I>::min()},{{0,3},{1,2}})==std::vector<int>({2,1}),"int64 extremes compared without subtraction or unpainted0 sentinel");
    for(auto query:std::vector<std::pair<int,int>>{{-1,0},{0,-1},{1,0},{0,4},{4,4},{std::numeric_limits<int>::min(),std::numeric_limits<int>::max()}})rejects({1,2,1},{query});
    rejects({},{{0,1}});rejects(std::vector<I>(200001),{});rejects({},std::vector<std::pair<int,int>>(200001,{0,0}));
    rejects({1,2,1},{{0,3},{0,0},{2,4}}); // A later invalid query cannot be bypassed by earlier valid/empty ones.
    for(int repeat=0;repeat<30;++repeat){
        const auto a=range_monotone_paint_strokes(sample,original_queries);
        require(range_monotone_paint_strokes({1},{{0,1},{0,0}})==std::vector<int>({1,0}),"interleaved differently-sized call");
        require(a==range_monotone_paint_strokes(sample,original_queries),"repeated/interleaved calls have no residual global/bit state");
    }
}
void maximum_case(int pattern){
    constexpr int n=200000,q=200000;std::vector<I> colors(n);std::vector<std::pair<int,int>> queries(q);
    for(int i=0;i<n;++i){
        if(pattern==0)colors[i]=1;
        if(pattern==1)colors[i]=i+1;
        if(pattern==2)colors[i]=n-i;
        if(pattern==3)colors[i]=1+i%2;
        if(pattern==4)colors[i]=1+i/2;
        if(pattern==5)colors[i]=1+i%1000;
    }
    for(int i=0;i<q;++i){
        int l=int(U(i)*100003%n),r=l+1+int((U(i)*91771+37)%(n-l));
        if(i%31==0){l=0;r=n;}
        if(i%31==1)r=l+1;
        queries[i]={l,r};
    }
    const auto begin=std::chrono::steady_clock::now();const auto answer=range_monotone_paint_strokes(colors,queries);
    maximum_case_seconds=std::max(maximum_case_seconds,std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count());
    for(int i=0;i<q;++i){
        const auto [l,r]=queries[i];int expected=0;
        if(pattern==0)expected=1;
        if(pattern==1||pattern==2)expected=r-l;
        if(pattern==3){const int high=r/2-l/2;expected=high+int(r-l-high>0);}
        if(pattern==4)expected=(r-1)/2-l/2+1;
        if(pattern==5){
            // In a repeated1..1000 ramp, each period requires one stroke for every
            // color>1 present; all finalcolor1 cells can share one outer stroke.
            const int low=(r+999)/1000-(l+999)/1000;expected=(r-l)-low+int(low>0);
        }
        require(answer[i]==expected,"maximumoriginalN/Q with independent per-pattern painting formula");absorb(answer[i]);++maximum_queries;
    }
    maximum_n=n;maximum_q=q;
}
int main(){
    const auto begin=std::chrono::steady_clock::now();const auto tables=literal_painting_bfs();boundaries();exhaustive(tables);randomized();
    for(int pattern=0;pattern<6;++pattern)maximum_case(pattern);
    require(maximum_n==200000&&maximum_q==200000&&maximum_queries==1200000,"ALL original maxN/Q executed for SIXpatterns");
    std::cout<<"{\"checks\":"<<checks<<",\"literalPaintingBFSStates\":"<<bfs_states<<",\"literalPaintingBFSActions\":"<<bfs_actions
             <<",\"allThreeColorArrays\":"<<arrays<<",\"allSubintervalsIncludingEmpty\":"<<exhaustive_queries
             <<",\"randomCases\":"<<random_cases<<",\"randomQueries\":"<<random_queries<<",\"maximumQueries\":"<<maximum_queries
             <<",\"maximumN\":"<<maximum_n<<",\"maximumQ\":"<<maximum_q<<",\"maximumCaseSeconds\":"<<maximum_case_seconds
             <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"}\n";
}
'''

args=[arg for arg in sys.argv[1:] if arg!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/monotone-paint-stroke-links-offline-containment.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected one complete visible C++20 fence')
with tempfile.TemporaryDirectory(prefix='flowchartcp-notime-check-') as directory:
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
