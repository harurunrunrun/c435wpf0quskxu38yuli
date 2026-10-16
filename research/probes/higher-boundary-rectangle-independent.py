#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,os,re,subprocess,tempfile
ARTICLE=Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/grid-enclosing-higher-boundary-rectangle-candidates.mdx'
CPP=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',ARTICLE.read_text(),re.M|re.S)[0]
TEST=r'''
#include <chrono>
#include <iostream>
#include <numeric>
#include <random>
#include <set>
using Grid=std::vector<std::vector<int>>;
using Box=std::array<int,4>;
using U=std::uint64_t;
U cases=0,rectangles=0,checks=0,witnesses=0,valid=0,duplicate_candidates=0,spurious_candidates=0,checksum=0;
void check(bool ok,const char* why){++checks;if(!ok){std::cerr<<why<<'\n';std::exit(1);}}
Box scan(const Grid& a,int i,int j){
 int n=int(a.size()),m=int(a[0].size()),t=i-1,b=i+1,l=j-1,r=j+1;
 while(t>=0&&a[t][j]<=a[i][j])--t;
 while(b<n&&a[b][j]<=a[i][j])++b;
 while(l>=0&&a[i][l]<=a[i][j])--l;
 while(r<m&&a[i][r]<=a[i][j])++r;
 if(t<0||b==n||l<0||r==m)return {-1,-1,-1,-1};
 return {t+1,b-1,l+1,r-1};
}
void test(const Grid& a,bool inspect){
 const int n=int(a.size()),m=int(a[0].size());
 // For every pair of literal outside endpoints, running maxima across its
 // interior give a Boolean violation for EACH row/column. Prefix sums across
 // the OTHER axis make rectangle checks O(1). No nearest-stack, candidates,
 // timestamp runs, packing, radix, or product formula enters this optimum.
 std::vector<int> h(std::size_t(m)*m*(n+1)),v(std::size_t(n)*n*(m+1));
 for(int l=0;l<m-2;++l){std::vector<int> mx(n,-1);
  for(int r=l+2;r<m;++r){const auto base=(std::size_t(l)*m+r)*(n+1);
   for(int i=0;i<n;++i){mx[i]=std::max(mx[i],a[i][r-1]);h[base+i+1]=h[base+i]+int(mx[i]>=std::min(a[i][l],a[i][r]));}
  }
 }
 for(int t=0;t<n-2;++t){std::vector<int> mx(m,-1);
  for(int b=t+2;b<n;++b){const auto base=(std::size_t(t)*n+b)*(m+1);
   for(int j=0;j<m;++j){mx[j]=std::max(mx[j],a[b-1][j]);v[base+j+1]=v[base+j]+int(mx[j]>=std::min(a[t][j],a[b][j]));}
  }
 }
 std::set<Box> literal_valid;
 for(int t=0;t<n-2;++t)for(int b=t+2;b<n;++b)for(int l=0;l<m-2;++l)for(int r=l+2;r<m;++r){
  ++rectangles;
  const auto hb=(std::size_t(l)*m+r)*(n+1),vb=(std::size_t(t)*n+b)*(m+1);
  if(h[hb+b]!=h[hb+t+1]||v[vb+r]!=v[vb+l+1])continue;
  literal_valid.insert({t+1,b-1,l+1,r-1});++valid;
  if(inspect){
   int maximum=-1;for(int i=t+1;i<b;++i)for(int j=l+1;j<r;++j)maximum=std::max(maximum,a[i][j]);
   for(int i=t+1;i<b;++i)for(int j=l+1;j<r;++j)if(a[i][j]==maximum){check(scan(a,i,j)==Box{t+1,b-1,l+1,r-1},"EVERY tied maximum must literally produce exact valid boundaries");++witnesses;}
  }
 }
 const auto old=a;
 const long long result=count_strictly_enclosed_rectangles(a);
 check(result==static_cast<long long>(literal_valid.size()),"actual fence versus independent interval-max/violation-prefix ALL rectangle oracle");
 check(old==a,"caller input unchanged");
 check(result<=static_cast<long long>(std::max(0,n-2))*std::max(0,m-2),"max-cell injection count bound");
 if(inspect){
  std::set<Box> possible;int all=0;
  for(int i=1;i<n-1;++i)for(int j=1;j<m-1;++j){auto box=scan(a,i,j);if(box[0]>=0){++all;possible.insert(box);}}
  duplicate_candidates+=all-possible.size();
  for(auto box:literal_valid)check(possible.count(box)==1,"all literal valid rectangles present in separately scanned candidate set");
  for(auto box:possible)spurious_candidates+=!literal_valid.count(box);
 }
 checksum=checksum*1000003+U(result+1);++cases;
}
int main(){
 const auto begin=std::chrono::steady_clock::now();
 std::vector<int> order(9);std::iota(order.begin(),order.end(),0);Grid a(3,std::vector<int>(3));
 do{for(int i=0;i<9;++i)a[i/3][i%3]=order[i];test(a,true);}while(std::next_permutation(order.begin(),order.end()));
 // Exhaustive 3x3 ternary interiors behind an independent full-height frame.
 // All unequal and tied maxima, overlapping candidates, missing runs and
 // different row/column barrier shapes occur, beyond the author's 4x4 binary.
 int configurations=1;for(int i=0;i<9;++i)configurations*=3;
 for(int code=0;code<configurations;++code){Grid g(5,std::vector<int>(5,7000000));int digits=code;
  for(int i=1;i<4;++i)for(int j=1;j<4;++j){g[i][j]=digits%3;digits/=3;}
  // Corners are arbitrary and are deliberately lower than all border cells.
  g[0][0]=g[0][4]=g[4][0]=g[4][4]=0;test(g,true);
 }
 std::mt19937 rng(162019);
 for(int repeat=0;repeat<12000;++repeat){
  int n=3+int(rng()%26),m=3+int(rng()%26);
  if(repeat%101==0){n=3;m=60;}if(repeat%101==1){n=60;m=3;}
  Grid g(n,std::vector<int>(m));
  const int mode=repeat%8;
  for(int i=0;i<n;++i)for(int j=0;j<m;++j){
   int x=0;
   if(mode==0)x=int(rng()%7000001);
   if(mode==1)x=int(rng()%2)*7000000;
   if(mode==2)x=int(rng()%5);
   if(mode==3)x=(i/2+j/2)%5;
   if(mode==4)x=std::abs(2*i-(n-1))+std::abs(2*j-(m-1));
   if(mode==5)x=((i+j)%4==0)?7000000:0;
   if(mode==6)x=((i/3+j/2)%3==0)?int(rng()%3):6;
   if(mode==7)x=(int(rng()%4)==0)?int(rng()%7000001):3500000;
   g[i][j]=x;
  }
  if(repeat%5==0){for(int i=0;i<n;++i)g[i][0]=g[i][m-1]=7000000;for(int j=0;j<m;++j)g[0][j]=g[n-1][j]=7000000;}
  test(g,true);
 }
 check(cases==362880+19683+12000,"all independent cases visited");
 check(duplicate_candidates>0&&spurious_candidates>0&&witnesses>0,"duplicates, invalid candidates and tiedmax witnesses are exercised");
 std::cout<<"{\"checks\":"<<checks<<",\"cases\":"<<cases<<",\"distinct3x3Permutations\":362880,\"ternary5x5FramedInteriors\":19683,\"randomGrids\":12000,\"rectangles\":"<<rectangles<<",\"validRectangles\":"<<valid<<",\"allMaximumWitnesses\":"<<witnesses<<",\"duplicateCandidateEmissions\":"<<duplicate_candidates<<",\"spuriousCandidates\":"<<spurious_candidates<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-rect-independent-') as tmp:
 p=Path(tmp);(p/'test.cpp').write_text(CPP+'\n'+TEST)
 subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 result=subprocess.run(['/usr/bin/time','-f','peak_rss_kib=%M',str(p/'test')],capture_output=True,text=True,check=True)
 output=json.loads(result.stdout);output['peakRSSKiB']=int(re.search(r'peak_rss_kib=(\d+)',result.stderr)[1]);output['cppSha256']=hashlib.sha256(CPP.encode()).hexdigest()
 print(json.dumps(output,indent=2))
