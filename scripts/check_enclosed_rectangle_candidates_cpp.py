#!/usr/bin/env python3
"""Extract the actual visible C++20 and compare to literal four-boundary inequalities."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile
args=[x for x in sys.argv[1:] if x!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/grid-enclosing-higher-boundary-rectangle-candidates.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('one complete always-visible C++20 fence required')
TESTS=r'''
#include <chrono>
#include <climits>
#include <cstdlib>
#include <iostream>
#include <random>
#include <utility>
using Grid=std::vector<std::vector<int>>;using U=std::uint64_t;
U checks=0,checksum=0,binary_grids=0,ternary_grids=0,literal_rectangles=0,random_grids=0,maximum_cases=0,invalid_calls=0;
void need(bool p,const char* why){++checks;if(!p){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
void take(U x){checksum=checksum*1000003+x+1;}
long long literal(const Grid& a){
 int n=int(a.size()),m=int(a[0].size());long long answer=0;
 for(int t=1;t<n-1;++t)for(int b=t;b<n-1;++b)for(int l=1;l<m-1;++l)for(int r=l;r<m-1;++r){
  ++literal_rectangles;bool good=true;
  for(int i=t;i<=b&&good;++i)for(int j=l;j<=r;++j)
   if(a[i][j]>=a[i][l-1]||a[i][j]>=a[i][r+1]||a[i][j]>=a[t-1][j]||a[i][j]>=a[b+1][j]){good=false;break;}
  answer+=good;
 }
 return answer;
}
void small(const Grid& a){
 const auto old=a;const long long got=count_strictly_enclosed_rectangles(a),want=literal(a);
 need(got==want,"every small grid equals literal every internal rectangle and four strict inequalities");
 need(old==a,"input unchanged");take(got);
}
void exhaustive(){
 for(int n=1;n<=4;++n)for(int m=1;m<=4;++m){Grid a(n,std::vector<int>(m));
  for(unsigned mask=0;mask<(1U<<(n*m));++mask){for(int k=0;k<n*m;++k)a[k/m][k%m]=(mask>>k&1)?7000000:0;small(a);++binary_grids;}
 }
 for(auto [n,m]:std::vector<std::pair<int,int>>{{3,3},{3,4},{4,3}}){Grid a(n,std::vector<int>(m));
  auto generate=[&](auto&& self,int k)->void{if(k==n*m){small(a);++ternary_grids;return;}for(int v:{0,1,7000000}){a[k/m][k%m]=v;self(self,k+1);}};generate(generate,0);
 }
}
void primitives(){
 using namespace enclosing_rectangle_detail;std::vector<std::uint16_t> left,right;std::vector<int> stack;
 for(int length=1;length<=9;++length){std::vector<int> a(length);
  auto all=[&](auto&& self,int k)->void{if(k==length){
   neighbors(length,[&](int i){return a[i];},left,right,stack);
   for(int i=0;i<length;++i){int l=i-1,r=i+1;while(l>=0&&a[l]<=a[i])--l;while(r<length&&a[r]<=a[i])++r;
    need(left[i]==(l<0?absent:std::uint16_t(l)),"strict previous higher including all ties");need(right[i]==(r==length?absent:std::uint16_t(r)),"strict next higher including all ties");}
   return;}for(int v:{0,1,2}){a[k]=v;self(self,k+1);}};all(all,0);
 }
 for(unsigned mask=0;mask<1024;++mask){std::vector<std::uint32_t> runs(pair_slots(3));
  for(int at=0;at<10;++at){if(mask>>at&1){note(runs,0,2,at+1);auto first=runs;note(runs,0,2,at+1);need(first==runs,"same pair repeated in one line is one occurrence");}
   for(int start=0;start<=at;++start){bool all=true;for(int j=start;j<=at;++j)all=all&&bool(mask>>j&1);need(covers(runs,0,2,start+1,at+1)==all,"run timestamps equal literal occurrence bitmap");}
  }
 }
 std::mt19937 random(947321);
 for(int repeat=0;repeat<300;++repeat){std::vector<Key> a;
  const unsigned length=1000+random()%1000;
  for(unsigned j=0;j<length;++j)a.push_back(pack(int(random()%2500),int(random()%2500),int(random()%2500),int(random()%2500)));
  const std::vector<Key> duplicates(a.begin(),a.begin()+3);a.insert(a.end(),duplicates.begin(),duplicates.end());auto expected=a;std::sort(expected.begin(),expected.end());radix_sort(a);need(a==expected,"full48bit stable radix versus comparison sort");
 }
}
Grid transpose(const Grid& a){Grid b(a[0].size(),std::vector<int>(a.size()));for(std::size_t i=0;i<a.size();++i)for(std::size_t j=0;j<a[0].size();++j)b[j][i]=a[i][j];return b;}
void randomized(){
 std::mt19937 random(20190806);
 for(int test=0;test<1000;++test){int n=3+int(random()%13),m=3+int(random()%13);Grid a(n,std::vector<int>(m));
  for(auto& row:a)for(int& x:row)x=test%3?int(random()%3):int(random()%7000001);
  if(test%7==0){for(int i=0;i<n;++i)a[i][0]=a[i][m-1]=7000000;for(int j=0;j<m;++j)a[0][j]=a[n-1][j]=7000000;}
  small(a);const long long got=count_strictly_enclosed_rectangles(a);
  need(got==count_strictly_enclosed_rectangles(transpose(a)),"transpose invariant");auto mirror=a;std::reverse(mirror.begin(),mirror.end());need(got==count_strictly_enclosed_rectangles(mirror),"vertical reflection invariant");
  for(auto& row:mirror){std::reverse(row.begin(),row.end());}
  need(got==count_strictly_enclosed_rectangles(mirror),"both reflections invariant");
  std::vector<int> values;for(const auto& row:a)values.insert(values.end(),row.begin(),row.end());std::sort(values.begin(),values.end());values.erase(std::unique(values.begin(),values.end()),values.end());
  auto rank=a;for(auto& row:rank)for(int& x:row)x=int(std::lower_bound(values.begin(),values.end(),x)-values.begin());need(got==count_strictly_enclosed_rectangles(rank),"strictly increasing rank relabeling invariant");++random_grids;
 }
 Grid example{{4,8,7,5,6},{7,4,10,3,5},{9,7,20,14,2},{9,14,7,3,6},{5,7,5,2,7},{4,5,13,5,6}};
 need(count_rectangles(example)==6,"original grader adapter and published example");
 Grid corners{{0,2,0},{2,1,2},{0,2,0}};need(count_rectangles(corners)==1,"outer corners are irrelevant");
 corners[1][0]=1;need(count_rectangles(corners)==0,"one equal boundary invalidates strictness");
 for(int i=0;i<100;++i){need(count_rectangles({{1,1,1},{1,0,1},{1,1,1}})==1,"fresh state after unrelated runs");need(count_rectangles({{0,0,0},{0,0,0},{0,0,0}})==0,"uniform equals never enclose");}
}
long long good_intervals(const std::vector<int>& a){ // independent quadratic running maximum, no nearest-neighbor stack
 long long answer=0;
 for(int l=0;l<int(a.size())-2;++l){int top=0;for(int r=l+2;r<int(a.size());++r){top=std::max(top,a[r-1]);answer+=top<std::min(a[l],a[r]);}}
 return answer;
}
long long binary_components(const Grid& a){ // all-zero4-components; literal bbox filledness, no candidate/runs
 const int n=int(a.size()),m=int(a[0].size());std::vector<unsigned char> seen(std::size_t(n)*m);std::vector<int> queue;long long result=0;
 for(int i=0;i<n;++i)for(int j=0;j<m;++j)if(a[i][j]==0&&!seen[i*m+j]){
  queue.clear();queue.push_back(i*m+j);seen[i*m+j]=1;int lo=i,hi=i,left=j,right=j;bool internal=true;
  for(std::size_t at=0;at<queue.size();++at){int r=queue[at]/m,c=queue[at]%m;lo=std::min(lo,r);hi=std::max(hi,r);left=std::min(left,c);right=std::max(right,c);internal=internal&&r>0&&r<n-1&&c>0&&c<m-1;
   for(auto [dr,dc]:std::array<std::pair<int,int>,4>{{{-1,0},{1,0},{0,-1},{0,1}}}){int rr=r+dr,cc=c+dc;if(rr>=0&&rr<n&&cc>=0&&cc<m&&a[rr][cc]==0&&!seen[rr*m+cc]){seen[rr*m+cc]=1;queue.push_back(rr*m+cc);}}
  }
  result+=internal&&queue.size()==std::size_t(hi-lo+1)*(right-left+1);
 }
 return result;
}
void maximum(){
 const int n=2500,m=2500;std::mt19937 random(987123);
 for(int kind=0;kind<7;++kind){Grid a(n,std::vector<int>(m));long long expected=0;
  if(kind==0){} // equal-zero board
  if(kind==1){for(int i=0;i<n;++i)a[i][0]=a[i][m-1]=7000000;for(int j=0;j<m;++j)a[0][j]=a[n-1][j]=7000000;expected=1;}
  if(kind==2){for(int i=0;i<n;++i)for(int j=0;j<m;++j){a[i][j]=((i+j)&1)?7000000:0;if(i>0&&i<n-1&&j>0&&j<m-1&&!a[i][j])++expected;}}
  if(kind==3){for(int i=0;i<n;++i)for(int j=0;j<m;++j)a[i][j]=i*m+j;}
  if(kind==4||kind==5){std::vector<int> row(n),column(m);for(int& x:row)x=kind==4?int(random()%3500001):0;for(int& x:column)x=kind==4?int(random()%3500001):0;
   if(kind==5){for(int i=0;i<n;++i)row[i]=std::abs(2*i-(n-1));for(int j=0;j<m;++j)column[j]=std::abs(2*j-(m-1));}
   for(int i=0;i<n;++i){for(int j=0;j<m;++j)a[i][j]=row[i]+column[j];}
   expected=good_intervals(row)*good_intervals(column);
  }
  if(kind==6){for(auto& row:a)for(int& x:row)x=random()%3?7000000:0;expected=binary_components(a);}
  U before=0;for(const auto& row:a)for(int x:row)before=before*1000003+U(x);
  const long long got=kind==1?count_rectangles(a):count_strictly_enclosed_rectangles(a);
  need(got==expected,"full2500x2500 original bound vs independent closed form/quadratic1D/BFS oracle");
  U after=0;for(const auto& row:a)for(int x:row)after=after*1000003+U(x);need(before==after,"large input unchanged");take(got);++maximum_cases;
 }
 need(count_strictly_enclosed_rectangles(Grid(1,std::vector<int>(2500,7000000)))==0,"maximum-width single row");
 need(count_strictly_enclosed_rectangles(Grid(2500,std::vector<int>(1,7000000)))==0,"maximum-height single column");
}
void reject(const Grid& a){bool caught=false;try{(void)count_strictly_enclosed_rectangles(a);}catch(const std::invalid_argument&){caught=true;}need(caught,"invalid API argument rejected");++invalid_calls;}
void invalid(){
 reject({});reject({{}});reject(Grid(2501,std::vector<int>(1)));reject(Grid(1,std::vector<int>(2501)));reject({{0},{0,1}});reject({{0},{}});
 for(int x:{INT_MIN,-1,7000001,INT_MAX})reject({{x}});
 reject({{0,0,0},{0,7000001,0},{0,0,0}});
 need(count_rectangles({{1,1,1},{1,0,1},{1,1,1}})==1,"valid call after exceptions");
}
int main(){auto begin=std::chrono::steady_clock::now();primitives();exhaustive();randomized();invalid();maximum();
 std::cout<<"{\"checks\":"<<checks<<",\"binaryGrids\":"<<binary_grids<<",\"ternaryGrids\":"<<ternary_grids<<",\"literalRectangles\":"<<literal_rectangles<<",\"randomGrids\":"<<random_grids<<",\"maximumCases\":"<<maximum_cases<<",\"maximumRows\":2500,\"maximumColumns\":2500,\"maximumHeight\":7000000,\"invalidCalls\":"<<invalid_calls<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-rect-build-') as tmp:
    src=Path(tmp)/'check.cpp';binary=Path(tmp)/'check';src.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];env=dict(os.environ)
    if '--sanitize' in sys.argv:
        flags=['-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'];env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    subprocess.run(['g++',*flags,str(src),'-o',str(binary)],check=True,timeout=120)
    result=subprocess.run(['/usr/bin/time','-f','peak_rss_kib=%M',str(binary)],capture_output=True,text=True,env=env,timeout=300)
    if result.returncode:print(result.stdout,end='',file=sys.stderr);print(result.stderr,end='',file=sys.stderr);result.check_returncode()
    out=json.loads(result.stdout);out['peakRSSKiB']=int(re.search(r'peak_rss_kib=(\d+)',result.stderr)[1]);out['cppSha256']=hashlib.sha256(blocks[0].encode()).hexdigest();out['sanitized']='--sanitize' in sys.argv;print(json.dumps(out))
