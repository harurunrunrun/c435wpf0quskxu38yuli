#!/usr/bin/env python3
"""Read-only actual-MDX probe: literal degree allocations plus allocation faults."""
from pathlib import Path
import hashlib,json,os,re,subprocess,tempfile,time
src=(Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/tree-degree-preservation-budget-construction.mdx').read_text()
fences=re.findall(r'```cpp\n(.*?)\n```',src,re.S)
assert len(fences)==1
cpp=fences[0]+'\n'
harness=r"""
#include <cstdlib>
#include <new>
#include <iostream>
#include <limits>
#include <random>
static long long fail_after=-1;
void* operator new(std::size_t n) {
    if(fail_after==0) throw std::bad_alloc();
    if(fail_after>0) --fail_after;
    if(void* p=std::malloc(n?n:1)) return p;
    throw std::bad_alloc();
}
void* operator new[](std::size_t n) { return ::operator new(n); }
void operator delete(void* p) noexcept { std::free(p); }
void operator delete[](void* p) noexcept { std::free(p); }
void operator delete(void* p,std::size_t) noexcept { std::free(p); }
void operator delete[](void* p,std::size_t) noexcept { std::free(p); }
using namespace degree_tree;
std::uint64_t checksum=0;
long long checks=0, allocations=0, compositions=0, cases=0;
void require(bool b) { ++checks; if(!b) throw std::runtime_error("probe mismatch"); }
void valid(const Result& r,const std::vector<std::int64_t>& want,int optimum) {
    int n=static_cast<int>(want.size());
    require(r.changed_vertices==optimum);
    require(r.degree.size()==want.size());
    require(r.edges.size()==want.size()-1);
    std::vector<int> deg(n),seen(n);std::vector<std::vector<int>> adj(n);
    for(auto [a,b]:r.edges) {
        require(a>=0&&a<n&&b>=0&&b<n&&a!=b);
        ++deg[a];++deg[b];adj[a].push_back(b);adj[b].push_back(a);
    }
    std::vector<int> q{0};seen[0]=1;
    for(std::size_t h=0;h<q.size();++h) for(int v:adj[q[h]]) if(!seen[v]) {seen[v]=1;q.push_back(v);}
    require(q.size()==want.size());require(deg==r.degree);
    int changed=0;for(int i=0;i<n;++i) changed+=(deg[i]!=want[i]);require(changed==optimum);
    checksum=checksum*1000003+static_cast<std::uint64_t>(changed+1);
    for(int d:deg) checksum=checksum*1000003+static_cast<unsigned>(d);
}
void enumerate(const std::vector<std::int64_t>& d,int i,int left,int changed,int& best) {
    if(i+1==static_cast<int>(d.size())) {
        ++compositions;best=std::min(best,changed+(d[i]!=left+1));return;
    }
    for(int x=0;x<=left;++x) enumerate(d,i+1,left-x,changed+(d[i]!=x+1),best);
}
int main(){
 std::mt19937_64 rng(0xe6f10b3cULL);
 for(int n=2;n<=10;++n) for(int k=0;k<200;++k) {
    std::vector<std::int64_t> d(n);
    for(auto& x:d) { auto r=rng()%8; x=r<3?static_cast<std::int64_t>(1+rng()%(n+2)):r==3?std::numeric_limits<std::int64_t>::max():r==4?2147483648LL:r==5?2147483647LL:r==6?4294967296LL:static_cast<std::int64_t>(1+rng()%100000); }
    d[rng()%n]=std::numeric_limits<std::int64_t>::max();
    auto saved=d;int best=n;enumerate(d,0,n-2,0,best);
    auto r=closest_tree_degrees(d);valid(r,d,best);require(d==saved);++cases;
 }
 // Every allocation in both APIs is failed once. Inputs must remain unchanged,
 // and a subsequent invocation must produce the same complete result.
 std::vector<Edge> es{{0,1},{0,1},{0,2},{0,2},{0,3}};
 std::vector<std::int64_t> ds{5,2,2,1};
 const auto saved_edges=es;const auto saved_degrees=ds;
 for(int which=0;which<2;++which) {
   bool reached=false;
   for(int failure=0;failure<1000;++failure) {
     fail_after=failure;
     try {auto r=which?rebuild_tree_preserving_degrees(4,es):closest_tree_degrees(ds);fail_after=-1;valid(r,ds,1);reached=true;break;}
     catch(const std::bad_alloc&) {fail_after=-1;++allocations;}
     require(es==saved_edges&&ds==saved_degrees);
     auto r=which?rebuild_tree_preserving_degrees(4,es):closest_tree_degrees(ds);valid(r,ds,1);
   }
   require(reached);
 }
 std::cout<<"{\"checks\":"<<checks<<",\"newDegreeInputs\":"<<cases<<",\"literalPositiveDegreeCompositions\":"<<compositions<<",\"allocationFailures\":"<<allocations<<",\"checksum\":\""<<checksum<<"\"}\n";
}
"""
with tempfile.TemporaryDirectory(prefix='flowchartcp-degree-independent-') as td:
 c=Path(td)/'probe.cpp'; exe=Path(td)/'probe';c.write_text(cpp+harness)
 flags=['-std=c++20','-O1','-Wall','-Wextra','-Werror','-Wno-mismatched-new-delete']
 if '--sanitize' in __import__('sys').argv: flags+=['-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
 subprocess.run(['g++',*flags,str(c),'-o',str(exe)],check=True)
 run_env=os.environ.copy();run_env['ASAN_OPTIONS']='detect_leaks=0'
 start=time.monotonic(); out=subprocess.check_output([str(exe)],text=True,env=run_env);elapsed=time.monotonic()-start
 result=json.loads(out);result.update({'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'articleSha256':hashlib.sha256(src.encode()).hexdigest(),'sanitize':'--sanitize' in __import__('sys').argv,'seconds':elapsed,'leakSanitizerEnabled':False,'method':'Literal enumeration of every positive target-degree composition; no sorting, budget selection, Prüfer oracle, or degree-assignment DP. Global allocation failure injection covers each allocation in both public APIs.'})
 print(json.dumps(result))
