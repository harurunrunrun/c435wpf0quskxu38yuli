#!/usr/bin/env python3
"""Compile the actual MDX C++20 fence; independently check its geometric output.
All inputs here are generated. The ten original output-only data files were not obtained.
"""
import argparse, hashlib, json, os, re, subprocess, tempfile
from pathlib import Path

HARNESS=r'''
#include <chrono>
#include <climits>
#include <iostream>
#include <map>
#include <random>
#include <sstream>
#include <string>
#include <sys/resource.h>
#include <utility>
using namespace orthogonal_cover;
using Points=std::vector<Point>;
std::uint64_t checks=0,checksum=0,permutations=0,small_segments=0,small_point_segment_tests=0;
std::uint64_t random_cases=0,metamorphic=0,invalid_calls=0,interior_covered_points=0;
void require(bool condition,const char*label){++checks;if(!condition)throw std::runtime_error(label);}
void record(std::uint64_t v){checksum=checksum*1000003ULL+v;}
bool on_segment(Point p,Point a,Point b){
    ++small_point_segment_tests;
    if(a.x==b.x)return p.x==a.x&&std::min(a.y,b.y)<=p.y&&p.y<=std::max(a.y,b.y);
    if(a.y==b.y)return p.y==a.y&&std::min(a.x,b.x)<=p.x&&p.x<=std::max(a.x,b.x);
    return false;
}
void basic(const Points&p,const Points&q){
    require(!q.empty()&&q.front()==Point{0,0},"origin must be included exactly as first vertex");
    require(q.size()<=p.size()+4,"N+3 segment guarantee");
    require(p.empty()?q.size()==1:q.size()>=p.size()+2,"each segment covers at most one dot, first covers none");
    for(std::size_t j=0;j<q.size();++j){
        require(q[j].x>=0&&q[j].x<=1000000001LL&&q[j].y>=0&&q[j].y<=1000000001LL,"strong output coordinate bound");
        if(j){require(!(q[j]==q[j-1]),"zero-length segment");
            require(q[j].x==q[j-1].x||q[j].y==q[j-1].y,"segment is horizontal or vertical");}}
    record(q.size()-1);
    for(Point v:q){record(static_cast<std::uint64_t>(v.x));record(static_cast<std::uint64_t>(v.y));}
}
void literal_check(const Points&p,const Points&q){
    basic(p,q);small_segments+=q.size()-1;
    for(Point v:p){bool covered=false,endpoint=false;for(std::size_t j=1;j<q.size();++j)covered|=on_segment(v,q[j-1],q[j]);
        require(covered,"literal point versus every output segment");
        for(Point e:q){endpoint|=e==v;}if(!endpoint)++interior_covered_points;}
}
// A second geometry checker uses interval union per horizontal/vertical supporting line.
// It does not know about chains, peeled boxes, construction order, or final rays.
using Intervals=std::map<std::int64_t,std::vector<std::pair<std::int64_t,std::int64_t>>>;
void merge(Intervals&lines){for(auto&[coordinate,list]:lines){(void)coordinate;std::sort(list.begin(),list.end());std::vector<std::pair<std::int64_t,std::int64_t>> out;
    for(auto interval:list){if(out.empty()||out.back().second<interval.first)out.push_back(interval);else out.back().second=std::max(out.back().second,interval.second);}list.swap(out);}}
bool contains(const Intervals&lines,std::int64_t key,std::int64_t value){auto it=lines.find(key);if(it==lines.end())return false;
    const auto&v=it->second;auto pos=std::upper_bound(v.begin(),v.end(),std::pair<std::int64_t,std::int64_t>{value,INT64_MAX});
    return pos!=v.begin()&&std::prev(pos)->second>=value;}
void union_check(const Points&p,const Points&q){basic(p,q);Intervals horizontal,vertical;
    for(std::size_t j=1;j<q.size();++j){Point a=q[j-1],b=q[j];if(a.x==b.x)vertical[a.x].push_back({std::min(a.y,b.y),std::max(a.y,b.y)});
        else horizontal[a.y].push_back({std::min(a.x,b.x),std::max(a.x,b.x)});}
    merge(horizontal);merge(vertical);
    for(Point v:p)require(contains(horizontal,v.y,v.x)||contains(vertical,v.x,v.y),"merged geometric intervals contain every dot");}
void exhaustive(){
    for(int n=1;n<=9;++n){std::vector<int>a(n);std::iota(a.begin(),a.end(),1);
        do{Points p;for(int i=0;i<n;++i)p.push_back({i+1,a[i]});const Points before=p;auto q=cover_points_orthogonally(p);
            literal_check(p,q);require(p==before,"small input unchanged");++permutations;
        }while(std::next_permutation(a.begin(),a.end()));}
}
void random_tests(){std::mt19937_64 rng(1547192019ULL);
    for(int test=0;test<6000;++test){int n=1+int(rng()%90);std::vector<int>xp(n),yp(n);std::iota(xp.begin(),xp.end(),1);std::iota(yp.begin(),yp.end(),1);
        std::shuffle(xp.begin(),xp.end(),rng);std::shuffle(yp.begin(),yp.end(),rng);Points p;
        for(int i=0;i<n;++i){std::int64_t x=xp[i],y=yp[i];if(test%3==0){x=1+(x-1)*999999999/(n==1?1:n-1);y=1+(y-1)*999999999/(n==1?1:n-1);}
            else if(test%3==1){x=x*x*x+11;y=y*y*y+17;}
            p.push_back({x,y});}
        const Points before=p;auto q=cover_points_orthogonally(p);literal_check(p,q);union_check(p,q);require(p==before,"random input unchanged");++random_cases;
        if(test<1200){std::shuffle(p.begin(),p.end(),rng);require(cover_points_orthogonally(p)==q,"input permutation gives same canonical output");++metamorphic;
            for(Point&v:p){std::swap(v.x,v.y);}literal_check(p,cover_points_orthogonally(p));++metamorphic;
            for(Point&v:p){v.x=1000000001LL-v.x;}literal_check(p,cover_points_orthogonally(p));++metamorphic;
            for(Point&v:p){v.y=1000000001LL-v.y;}literal_check(p,cover_points_orthogonally(p));++metamorphic;
            for(Point&v:p){v.x=1000000001LL-v.x;std::swap(v.x,v.y);}literal_check(p,cover_points_orthogonally(p));++metamorphic;}
    }
}
void api_cases(){
    literal_check({},cover_points_orthogonally({}));
    for(Points p:std::vector<Points>{{{1,1}},{{1000000000,1000000000}},{{1,1000000000},{1000000000,1}},{{2,1},{3,3},{4,4},{5,2}}}){
        auto q=cover_points_orthogonally(p);literal_check(p,q);std::ostringstream output;write_line_output(output,p);std::istringstream in(output.str());
        std::size_t k=0;require(bool(in>>k)&&k==q.size()-1,"writer segment count");
        for(std::size_t j=1;j<q.size();++j){Point v{};require(bool(in>>v.x>>v.y)&&v==q[j],"writer excludes origin, exact vertices");}
        std::string extra;require(!(in>>extra),"writer no trailing token");
        q.back()={-7,-7};require(!(cover_points_orthogonally(p).back()==q.back()),"returned object independent of future calls");
    }
    auto reject=[&](const Points&p){bool caught=false;const Points before=p;try{(void)cover_points_orthogonally(p);}catch(const std::invalid_argument&){caught=true;}
        require(caught,"invalid API input accepted");require(p==before,"invalid input not changed");++invalid_calls;
        std::ostringstream out;caught=false;try{write_line_output(out,p);}catch(const std::invalid_argument&){caught=true;}
        require(caught&&out.str().empty(),"writer validates before emitting output");
        literal_check({{1,1}},cover_points_orthogonally({{1,1}}));};
    reject(Points(100001,{1,1}));reject({{0,1}});reject({{1,0}});reject({{-1,1}});reject({{1,-1}});
    reject({{INT64_MIN,1}});reject({{1,INT64_MIN}});reject({{INT64_MAX,1}});reject({{1,INT64_MAX}});
    reject({{1000000001LL,1}});reject({{1,1000000001LL}});reject({{1,1},{1,2}});reject({{1,1},{2,1}});reject({{1,1},{1,1}});
    for(int i=0;i<50;++i){literal_check({},cover_points_orthogonally({}));literal_check({{2,1},{1,2}},cover_points_orthogonally({{2,1},{1,2}}));}
}
struct MaxResult{std::string name;int n,segments;std::size_t bytes;};std::vector<MaxResult>maximum_results;
void max_case(const std::string&name,const Points&p){const Points before=p;auto q=cover_points_orthogonally(p);union_check(p,q);require(p==before,"maximum input unchanged");
    std::ostringstream out;write_line_output(out,p);const std::string output=out.str();require(output.size()<2300000,"output below15MB and conservative2.3MB bound");
    std::istringstream input(output);int k;require(bool(input>>k)&&k==int(q.size())-1,"maximum writer count");for(int i=1;i<=k;++i){Point v{};require(bool(input>>v.x>>v.y)&&v==q[i],"maximum writer exact point");}
    maximum_results.push_back({name,int(p.size()),k,output.size()});}
Points nested(int n){Points p;for(int i=0;i<n/4;++i){const int l=2*i+1,r=n-2*i;p.push_back({l,l+1});p.push_back({l+1,l});p.push_back({r,r-1});p.push_back({r-1,r});}return p;}
void maximum(){const int n=100000;Points p;for(int i=1;i<=n;++i)p.push_back({i,i});max_case("increasing chain",p);
    for(int i=0;i<n;++i){p[i].y=n-i;}max_case("decreasing chain",p);
    p=nested(n);max_case("25000 strictly nested four-point boxes",p);
    for(Point&v:p){v.x=1+(v.x-1)*999999999/(n-1);v.y=1+(v.y-1)*999999999/(n-1);}max_case("nested boxes at original coordinate extremes",p);
    std::mt19937_64 rng(9144147);std::vector<int>a(n);std::iota(a.begin(),a.end(),1);std::shuffle(a.begin(),a.end(),rng);
    p.clear();for(int i=0;i<n;++i)p.push_back({1+std::int64_t(i)*999999999/(n-1),1+std::int64_t(a[i]-1)*999999999/(n-1)});max_case("random all three parts at1e9",p);
    std::reverse(p.begin(),p.end());max_case("reversed input with same canonical path",p);
    p.clear();for(int i=0;i<n;++i)p.push_back({i+1,i%2==0?i/2+1:n-i/2});max_case("alternating high low ranks",p);
    p=nested(n-4);for(Point&v:p){v.x+=2;v.y+=2;}p.push_back({1,1});p.push_back({2,n});p.push_back({n-1,2});p.push_back({n,n-1});max_case("two chains plus deep spiral",p);
    // The seven table sizes are generated instances, not the ten original contest files.
    for(int size:std::vector<int>{20,600,5000,50000,72018,91891,100000}){
        std::vector<int>v(size);std::iota(v.begin(),v.end(),1);std::shuffle(v.begin(),v.end(),rng);p.clear();for(int i=0;i<size;++i)p.push_back({i+1,v[i]});
        max_case("generated scoring-table size"+std::to_string(size),p);}
}
int main(){try{const auto start=std::chrono::steady_clock::now();api_cases();exhaustive();random_tests();maximum();
    require(interior_covered_points>0,"test suite includes covered dots that are not output vertices");rusage usage{};getrusage(RUSAGE_SELF,&usage);
    std::cout<<"{\"checks\":"<<checks<<",\"rankPermutations\":"<<permutations<<",\"smallOutputSegments\":"<<small_segments
      <<",\"literalPointSegmentTests\":"<<small_point_segment_tests<<",\"interiorCoveredPoints\":"<<interior_covered_points
      <<",\"randomCases\":"<<random_cases<<",\"metamorphicChecks\":"<<metamorphic<<",\"invalidCalls\":"<<invalid_calls
      <<",\"originalContestInputFilesTested\":0,\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()
      <<",\"peakRSSKiB\":"<<usage.ru_maxrss<<",\"maximumCases\":[";bool comma=false;for(const auto&r:maximum_results){if(comma)std::cout<<',';comma=true;
        std::cout<<"{\"name\":\""<<r.name<<"\",\"n\":"<<r.n<<",\"segments\":"<<r.segments<<",\"outputBytes\":"<<r.bytes<<'}';}std::cout<<"]}\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sanitize',action='store_true');parser.add_argument('--article',default=str(Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/orthogonal-point-cover-spiral-two-chains.mdx'));args=parser.parse_args()
    article=Path(args.article).read_text();fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
    assert len(fences)==1
    assert re.findall(r'^## (.+)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料']
    cpp=fences[0];flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-line-cpp-') as directory:
        source=Path(directory)/'check.cpp';binary=Path(directory)/'check';source.write_text(cpp+'\n'+HARNESS)
        subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
        env=os.environ.copy()
        if args.sanitize:env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1'
        run=subprocess.run([str(binary)],capture_output=True,text=True,check=True,env=env)
        result=json.loads(run.stdout);result.update({'sanitized':args.sanitize,'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'article':args.article})
        print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
