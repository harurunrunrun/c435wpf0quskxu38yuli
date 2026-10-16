#!/usr/bin/env python3
"""Extract the published C++20; literal three-leader and intermediate-state oracles."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile
args=[x for x in sys.argv[1:] if x!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/interval-unique-endpoints-singleton-middle-active-lazy.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('one always-visible complete C++20 fence required')
TESTS=r'''
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
using I=std::int64_t;using U=std::uint64_t;
U checks=0,arrays=0,literal_triples=0,invariant_arrays=0,invariant_snapshots=0,invariant_points=0,random_cases=0,medium_cases=0,primitive_steps=0,maximum_cases=0,maximum_elements=0,checksum=0;
void require(bool p,const char* why){++checks;if(!p){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
void absorb(I x){checksum=checksum*1000003+U(x+2);}
I choose2(I n){return n*(n-1)/2;}
I choose3(I n){return n<3?0:n*(n-1)*(n-2)/6;}
std::vector<I> literal_by_right(const std::vector<I>& a){
 const int n=int(a.size());std::vector<I> result(n);
 for(int left=0;left<n;++left)for(int middle=left+1;middle<n;++middle)for(int right=middle+1;right<n;++right){
  int x=0,y=0,z=0;
  for(int i=left;i<=right;++i){x+=a[i]==a[left];y+=a[i]==a[middle];z+=a[i]==a[right];}
  result[right]+=x==1&&y==1&&z==1;++literal_triples;
 }
 return result;
}
I total(const std::vector<I>& a){return std::accumulate(a.begin(),a.end(),I(0));}
void snapshot(unique_leader_detail::ActiveWeights& tree,const std::vector<I>& a,int end){
 const int n=int(a.size());int count_sum=0;I weighted_sum=0;
 // Literal per-left frequency lists, independent of prev-two occurrences,
 // permanent removals, range updates, lazy tags, and compression ordering.
 for(int left=end-1;left>=0;--left){
  std::vector<std::pair<I,int>> frequency;
  for(int i=left+1;i<end;++i){
   auto it=std::find_if(frequency.begin(),frequency.end(),[&](const auto& p){return p.first==a[i];});
   if(it==frequency.end())frequency.push_back({a[i],1});else ++it->second;
  }
  bool active=true;int singletons=0;
  for(const auto& p:frequency){active=active&&p.first!=a[left];singletons+=p.second==1;}
  const auto point=tree.fold(left,left+1);
  require(point.count==int(active)&&point.sum==(active?singletons:0),"EVERY position has literal endpoint-unique activity and literal inner-singleton weight after EACH prefix event");
  ++invariant_points;count_sum+=active;weighted_sum+=active?singletons:0;
  const auto suffix=tree.fold(left,end);
  require(suffix.count==count_sum&&suffix.sum==weighted_sum,"EVERY suffix aggregate matches count and sum of literal active weights");
 }
 const auto all=tree.fold(0,end),future=tree.fold(end,n);
 require(all.count==count_sum&&all.sum==weighted_sum,"root/prefix aggregate invariant");
 require(future.count==0&&future.sum==0,"positions not processed yet remain inactive and contribute0");++invariant_snapshots;
}
void event_invariants(const std::vector<I>& a,const std::vector<I>& contributions){
 const int n=int(a.size());if(n==0)return;
 unique_leader_detail::ActiveWeights tree(n);snapshot(tree,a,0);I accumulated=0;
 for(int right=0;right<n;++right){
  int p=-1,q=-1;for(int i=0;i<right;++i)if(a[i]==a[right]){q=p;p=i;}
  const auto got=tree.fold(p+1,right).sum;
  require(got==contributions[right],"query BEFORE inserting right matches ALL literal triples with this exact right endpoint");
  accumulated+=got;
  if(p>=0)tree.replace(p,false);
  tree.add(std::max(0,p),right,1);
  if(p>=0)tree.add(std::max(0,q),p,-1);
  tree.replace(right,true);
  snapshot(tree,a,right+1);
 }
 require(accumulated==total(contributions),"traced exact published tree operations equal literal triple total");++invariant_arrays;
}
void small_case(const std::vector<I>& a,bool inspect){
 const auto old=a;const auto want=literal_by_right(a);const I got=count_interval_unique_leader_triples(a);
 require(got==total(want),"actual FULL published function equals ALL literal l<m<r with EACH leader breed counted in ENTIRE interval");
 require(a==old,"caller input unchanged");absorb(got);++arrays;if(inspect)event_invariants(a,want);
}
void exhaustive(){
 const std::vector<I> labels{std::numeric_limits<I>::min(),-1,0,std::numeric_limits<I>::max()};
 for(int n=0;n<=9;++n){U possibilities=U(1)<<(2*n);
  for(U code=0;code<possibilities;++code){U digits=code;std::vector<I> a(n);for(I& x:a){x=labels[digits&3];digits>>=2;}small_case(a,n<=8);}
 }
 require(arrays==349525&&invariant_arrays==87380,"ALLfourlabel arrays0..9 and EACH event0..8 observed");
}
I quadratic_interval_oracle(const std::vector<I>& a){
 // Independently enumerate intervals and use their actual frequency map.
 // Only unique endpoints accepted; every other singleton is a middle choice.
 I answer=0;const int n=int(a.size());
 for(int left=0;left<n;++left){std::map<I,int> frequency;int unique=0;
  for(int right=left;right<n;++right){int& f=frequency[a[right]];if(f==0)++unique;else if(f==1)--unique;++f;
   if(right-left>=2&&frequency[a[left]]==1&&frequency[a[right]]==1)answer+=unique-2;
  }
 }
 return answer;
}
void randomized(){
 std::mt19937 rng(1140);
 for(int test=0;test<3000;++test){
  const bool medium=test>=2500;const int n=medium?30+int(rng()%151):int(rng()%46);std::vector<I> a(n);
  for(I& x:a){int mode=int(rng()%17);x=mode==0?std::numeric_limits<I>::min():mode==1?std::numeric_limits<I>::max():I(int(rng()%19)-9);}
  const auto old=a;const I want=medium?quadratic_interval_oracle(a):total(literal_by_right(a));
  const I got=count_interval_unique_leader_triples(a);require(got==want,"random small literal triples / medium direct-interval frequency oracle");
  auto reversed=a;std::reverse(reversed.begin(),reversed.end());require(count_interval_unique_leader_triples(reversed)==want,"reflection preserves interval and three leader count");
  auto palette=a;std::sort(palette.begin(),palette.end());palette.erase(std::unique(palette.begin(),palette.end()),palette.end());
  auto renamed=a;for(I& x:renamed)x=-1000*I(std::lower_bound(palette.begin(),palette.end(),x)-palette.begin());
  require(count_interval_unique_leader_triples(renamed)==want,"bijection reversing label order preserves equality; original numeric order is irrelevant");
  require(a==old,"random input unchanged");absorb(got);if(medium)++medium_cases;else ++random_cases;
 }
}
void primitive_tests(){
 using unique_leader_detail::ActiveWeights;
 ActiveWeights tree(8);tree.add(0,8,7);tree.replace(3,true);require(tree.fold(0,8).sum==0,"new activation discards a historical whole-node lazy tag");
 tree.add(0,8,5);tree.replace(0,true);require(tree.fold(0,8).sum==5,"new point gets0 while old active point keeps5");
 tree.replace(3,false);tree.add(0,8,-2);require(tree.fold(0,8).sum==-2,"generic internal tree uses signed weights and excludes deactivatedpoint");
 tree.replace(0,false);tree.replace(3,true);require(tree.fold(0,8).sum==0,"reactivation resets previous value even after negative pending lazy");
 std::mt19937 rng(73140);
 for(int n:{1,2,3,17,64,129}){ActiveWeights t(n);std::vector<int> active(n);std::vector<I> weight(n);
  for(int step=0;step<8000;++step){
   if(rng()%3==0){const int p=int(rng()%n),on=int(rng()%2);t.replace(p,on);active[p]=on;weight[p]=0;}
   else{int l=int(rng()%(n+1)),r=int(rng()%(n+1));if(l>r)std::swap(l,r);const int delta=int(rng()%7)-3;t.add(l,r,delta);for(int i=l;i<r;++i)if(active[i])weight[i]+=delta;}
   int l=int(rng()%(n+1)),r=int(rng()%(n+1));if(l>r)std::swap(l,r);int count=0;I sum=0;for(int i=l;i<r;++i){count+=active[i];sum+=active[i]?weight[i]:0;}
   const auto result=t.fold(l,r);require(result.count==count&&result.sum==sum,"actual active-count times signed-lazy tree versus literal point model after arbitrary range updates and membership replacements");++primitive_steps;
  }
 }
}
I cycle_formula(int n,int period){const I k=std::min(n,period)-2;return k<=0?0:I(n-1)*k*(k+1)/2-k*(k+1)*(2*k+1)/6;}
I one_duplicate_formula(int n,int u,int v){
 const I containing_u=choose2(n-u-1)-choose2(v-u-1)+I(u)*(n-v);
 const I containing_v=choose2(v)-choose2(v-u-1)+I(u+1)*(n-v-1);
 return choose3(n)-containing_u-containing_v+(n-2);
}
void boundaries(){
 require(count_interval_unique_leader_triples({1,2,3,4,3,2,5})==9,"original PLATINUM sample, not same-title GOLD task");
 require(count_interval_unique_leader_triples({1,2,1,3})==1,"pairwise distinct selected leader values are insufficient when another nonleader repeats one of them");
 require(count_interval_unique_leader_triples({1,2,2,3})==0,"unique endpoints but no singleton middle");
 require(count_interval_unique_leader_triples({1,2,1})==0,"repeated endpoint invalid");
 require(count_interval_unique_leader_triples({std::numeric_limits<I>::max(),std::numeric_limits<I>::min(),0})==1,"three distinct full64bit labels including0 are valid");
 require(count_interval_unique_leader_triples({})==0&&count_interval_unique_leader_triples({0})==0&&count_interval_unique_leader_triples({0,1})==0,"empty and too-short inputs");
 const auto too_large=std::vector<I>(200001,std::numeric_limits<I>::min());const auto old=too_large;bool threw=false;
 try{(void)count_interval_unique_leader_triples(too_large);}catch(const std::invalid_argument&){threw=true;}
 require(threw&&too_large==old,"oversized public API rejects before narrowing and never modifies input");
 for(int n=3;n<=16;++n){
  for(int period=1;period<=n;++period){std::vector<I> a(n);for(int i=0;i<n;++i)a[i]=1+i%period;require(total(literal_by_right(a))==cycle_formula(n,period),"maximum-cycle closed formula independently checked on ALL small periods");}
  for(int u=0;u<n;++u)for(int v=u+1;v<n;++v){std::vector<I> a(n);std::iota(a.begin(),a.end(),I(1));a[v]=a[u];require(total(literal_by_right(a))==one_duplicate_formula(n,u,v),"one-duplicate inclusion-exclusion closed formula independently checked for every small position pair");}
 }
 for(int repeat=0;repeat<100;++repeat){require(count_interval_unique_leader_triples({1,2,3,4,3,2,5})==9,"valid repeated call after invalid / differently sized call");require(count_interval_unique_leader_triples({-1,-1,-1,-1})==0,"interleaved equality pattern cannot retain old palette/last/tree state");}
}
void maximum(){
 constexpr int n=200000;require(choose3(n)==I(1333313333400000LL),"exact source maximum result fits signed64 but exceeds32bit");
 for(int pattern=0;pattern<7;++pattern){std::vector<I> a(n);I want=0;
  if(pattern==0)std::fill(a.begin(),a.end(),1);
  if(pattern==1){std::iota(a.begin(),a.end(),I(1));want=choose3(n);}
  if(pattern==2)for(int i=0;i<n;++i)a[i]=1+i%2;
  if(pattern==3){for(int i=0;i<n;++i)a[i]=1+i%3;want=n-2;}
  if(pattern==4){for(int i=0;i<n;++i)a[i]=1+i%997;want=cycle_formula(n,997);}
  if(pattern==5){for(int i=0;i<n;++i)a[i]=1+i%(n/2);want=cycle_formula(n,n/2);}
  if(pattern==6){std::iota(a.begin(),a.end(),I(1));const int u=n/3,v=2*n/3;a[v]=a[u];want=one_duplicate_formula(n,u,v);}
  const auto old=a;const I got=count_interval_unique_leader_triples(a);
  require(got==want,"full original N200000 versus independent singleton/all-distinct/periodic/one-duplicate combinatorial formula");
  require(a==old,"full source bound input unchanged");absorb(got);++maximum_cases;maximum_elements+=n;
 }
 std::vector<I> pairs(n);for(int i=0;i<n;++i)pairs[i]=1+i/2;
 require(count_interval_unique_leader_triples(pairs)==0,"full source adjacent equal pairs: all internal complete pair values repeat, so no middle leader");++maximum_cases;maximum_elements+=n;
}
int main(){const auto begin=std::chrono::steady_clock::now();primitive_tests();boundaries();exhaustive();randomized();maximum();
 std::cout<<"{\"checks\":"<<checks<<",\"allFourLabelArrays\":"<<arrays<<",\"literalLeaderTriples\":"<<literal_triples
 <<",\"invariantArrays\":"<<invariant_arrays<<",\"invariantSnapshots\":"<<invariant_snapshots<<",\"invariantPoints\":"<<invariant_points
 <<",\"randomCases\":"<<random_cases<<",\"mediumCases\":"<<medium_cases<<",\"primitiveSteps\":"<<primitive_steps
 <<",\"maximumCases\":"<<maximum_cases<<",\"maximumElements\":"<<maximum_elements<<",\"maximumN\":200000,\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-unitedcows-check-') as directory:
    source=Path(directory)/'check.cpp';binary=Path(directory)/'check';source.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];environment=dict(os.environ)
    if '--sanitize' in sys.argv:
        flags=['-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
        environment['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';environment['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True,timeout=120)
    result=subprocess.run(['/usr/bin/time','-f','peak_rss_kib=%M',str(binary)],capture_output=True,text=True,env=environment,timeout=300)
    if result.returncode:
        print(result.stdout,end='',file=sys.stderr);print(result.stderr,end='',file=sys.stderr);result.check_returncode()
    output=json.loads(result.stdout);output['peakRSSKiB']=int(re.search(r'peak_rss_kib=(\d+)',result.stderr)[1]);output['sanitized']='--sanitize' in sys.argv;output['cppSha256']=hashlib.sha256(blocks[0].encode()).hexdigest()
    print(json.dumps(output,ensure_ascii=False,indent=2))
