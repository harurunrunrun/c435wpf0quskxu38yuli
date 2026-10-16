#!/usr/bin/env python3
"""Column lifetime automaton, independent of endpoint phases/prefix sums."""
from pathlib import Path
import hashlib,json,re,subprocess,tempfile

HARNESS=r'''
#include <chrono>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
using Grid=std::vector<std::string>;
constexpr int mod=1000000007;
std::uint64_t checks=0,checksum=0,boards=0,automaton_steps=0,separator_checks=0;
void require(bool b,const char*why){++checks;if(!b)throw std::runtime_error(why);}
void record(int x){checksum=checksum*1000003ULL+std::uint64_t(x);}
struct Automaton {
 int width,size;
 std::vector<unsigned> interval,active,closed;
 std::vector<std::vector<int>> next;
 std::vector<int> start;
 explicit Automaton(int w):width(w),size(1) {
  for(int i=0;i<w;++i)size*=3;
  for(int l=0;l<w;++l)for(int r=l;r<w;++r)interval.push_back(((1U<<(r-l+1))-1)<<l);
  active.resize(size);closed.resize(size);next.assign(size,std::vector<int>(interval.size(),-1));
  for(int s=0;s<size;++s){int digits=s;for(int c=0;c<w;++c){int value=digits%3;digits/=3;if(value==1)active[s]|=1U<<c;if(value==2)closed[s]|=1U<<c;}}
  auto encode=[&](unsigned a,unsigned c){int value=0,power=1;for(int i=0;i<w;++i){value+=power*((a>>i&1)?1:(c>>i&1)?2:0);power*=3;}return value;};
  for(unsigned now:interval)start.push_back(encode(now,0));
  for(int s=0;s<size;++s)for(std::size_t k=0;k<interval.size();++k) {
   unsigned now=interval[k];if(!(active[s]&now)||(closed[s]&now))continue;
   next[s][k]=encode(now,closed[s]|(active[s]&~now));
  }
 }
 int count(const Grid&grid)const {
  std::vector<int> dp(size),out(size);int answer=0;
  for(const auto&row:grid) {
   std::fill(out.begin(),out.end(),0);unsigned grass=0;for(int c=0;c<width;++c)if(row[c]=='G')grass|=1U<<c;
   for(std::size_t k=0;k<interval.size();++k)if((interval[k]&grass)==interval[k]) {
    ++out[start[k]];
    for(int s=0;s<size;++s)if(dp[s]&&next[s][k]>=0) {
     ++automaton_steps;int&dest=out[next[s][k]];dest=int((std::int64_t(dest)+dp[s])%mod);
    }
   }
   for(int count:out)answer=int((std::int64_t(answer)+count)%mod);
   dp.swap(out);
  }
  return answer;
 }
};
Grid transposed(const Grid&a){Grid b(a[0].size(),std::string(a.size(),'.'));for(std::size_t i=0;i<a.size();++i)for(std::size_t j=0;j<a[0].size();++j)b[j][i]=a[i][j];return b;}
void verify(const Grid&a,const Automaton&oracle) {
 ++boards;int want=oracle.count(a);
 int got=count_row_column_convex_subsets(a);record(got);require(got==want,"explicit column lifetime automaton");
 got=count_row_column_convex_subsets(transposed(a));record(got);require(got==want,"lifetime oracle after input transpose");
}
// Verify the history automaton itself on all actual cell subsets, using only
// literal occupied cells and BFS, without endpoint phases.
bool actual_shape(int h,int w,unsigned mask) {
 if(!mask)return false;
 for(int axis=0;axis<2;++axis)for(int i=0;i<(axis?w:h);++i) {
  bool ended=false,started=false;
  for(int j=0;j<(axis?h:w);++j) {
   bool on=mask>>(axis?j*w+i:i*w+j)&1;
   if(on){if(ended)return false;started=true;}else if(started)ended=true;
  }
 }
 unsigned seen=mask&(~mask+1),before=0;
 while(seen!=before) {
  before=seen;for(int r=0;r<h;++r)for(int c=0;c<w;++c)if(seen>>(r*w+c)&1)
   for(auto[dr,dc]:std::array<std::pair<int,int>,4>{{{1,0},{-1,0},{0,1},{0,-1}}}) {
    int rr=r+dr,cc=c+dc;if(rr>=0&&rr<h&&cc>=0&&cc<w&&((mask>>(rr*w+cc))&1))seen|=1U<<(rr*w+cc);
   }
 }
 return seen==mask;
}
int main() {
 auto begin=std::chrono::steady_clock::now();Automaton width3(3);
 std::vector<int> literal(1<<15);
 for(unsigned mask=1;mask<(1U<<15);++mask)literal[mask]=actual_shape(5,3,mask);
 for(int bit=0;bit<15;++bit)for(int mask=0;mask<(1<<15);++mask)if(mask>>bit&1)literal[mask]+=literal[mask^(1<<bit)];
 for(unsigned mask=0;mask<(1U<<15);++mask) {
  Grid a(5,std::string(3,'.'));for(int i=0;i<15;++i)if(mask>>i&1)a[i/3][i%3]='G';
  require(width3.count(a)==literal[mask],"lifetime automaton versus literal5x3 cells");verify(a,width3);
 }
 std::mt19937 rng(729251U);
 for(int w=1;w<=7;++w) {
  Automaton oracle(w);
  for(int pattern=0;pattern<6;++pattern) {
   Grid a(150,std::string(w,'G'));
   for(int r=0;r<150;++r)for(int c=0;c<w;++c) {
    if(pattern==1&&r%2)a[r][c]='.';
    if(pattern==2&&c%2)a[r][c]='.';
    if(pattern==3&&(r+c)%2)a[r][c]='.';
    if(pattern==4&&r%7==0&&c!=int(rng()%unsigned(w)))a[r][c]='.';
    if(pattern==5&&r<148&&c>0&&c+1<w)a[r][c]='.';
   }
   verify(a,oracle);
  }
  for(int trial=0;trial<60;++trial) {
   int h=1+int(rng()%150);Grid a(h,std::string(w,'.'));
   for(auto&row:a)for(char&cell:row)if(rng()%100<unsigned(20+trial%8*10))cell='G';
   verify(a,oracle);
  }
 }
 // A blocked separator prevents any4-connected subset from crossing it.
 // This large-grid identity is independent of either DP's state design.
 for(int trial=0;trial<20;++trial) {
  Grid top(74,std::string(150,'.')),bottom(75,std::string(150,'.'));
  for(auto*grid:{&top,&bottom})for(auto&row:*grid)for(char&cell:row)if(rng()%5)cell='G';
  const int expected=int((std::int64_t(count_row_column_convex_subsets(top))+count_row_column_convex_subsets(bottom))%mod);
  Grid combined=top;combined.push_back(std::string(150,'.'));combined.insert(combined.end(),bottom.begin(),bottom.end());
  int got=count_row_column_convex_subsets(combined);record(got);require(got==expected,"blocked separator additive identity on150x150");++separator_checks;
 }
 std::cout<<"{\"checks\":"<<checks<<",\"boards\":"<<boards<<",\"lifetimeTransitionUpdates\":"<<automaton_steps
  <<",\"all5x3Boards\":32768,\"literal5x3Shapes\":32767,\"maximumTallPatterns\":42,\"randomNarrowBoards\":420"
  <<",\"maximumSeparatorChecks\":"<<separator_checks<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"}\n";
}
'''
article=(Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/orthogonally-convex-row-interval-phase-prefix-dp.mdx').read_text()
fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S);assert len(fences)==1
with tempfile.TemporaryDirectory(prefix='flowchartcp-balanced-independent-') as tmp:
    src=Path(tmp)/'check.cpp';binary=Path(tmp)/'check';src.write_text(fences[0]+'\n'+HARNESS)
    subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(src),'-o',str(binary)],check=True)
    output=json.loads(subprocess.check_output([str(binary)],text=True))
output['cppSha256']=hashlib.sha256(fences[0].encode()).hexdigest()
output['oracle']='Per-column unseen/active/closed lifetimes and explicit row-overlap transitions, without endpoint phases or cumulative sums.'
print(json.dumps(output,ensure_ascii=False))
