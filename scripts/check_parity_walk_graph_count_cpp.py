#!/usr/bin/env python3
"""Actual-fence graph counting versus complete infinite-language group sizes."""
from pathlib import Path
import hashlib,json,math,os,re,subprocess,sys,tempfile
args=[x for x in sys.argv[1:] if x!='--sanitize']
article=Path(args[0]) if args else (Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/parity-walk-profile-layer-inclusion-exclusion-count.mdx')
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('one complete always-visible C++20 fence required')
MODULI=[1,2,4,6,97,1000000007,2147483647]
# Independent exact integer oracles: classify by the set of NON-isolated
# vertices instead of alternating PIE. No production DP participates here.
nonisolated=[1]
for n in range(1,100):
    nonisolated.append((1<<(n*(n+1)//2))-sum(math.comb(n,k)*nonisolated[k] for k in range(n)))
def nonempty_matrix(p,m):
    row_surjective=[]
    for rows in range(p+1):
        row_surjective.append(((1<<rows)-1)**m-sum(math.comb(rows,k)*row_surjective[k] for k in range(rows)))
    return row_surjective[p]
k,p,m=3,48,48
first=((1<<k)-1)*(1<<p);second=(1<<p)-1
mixed=nonisolated[k]*sum(math.comb(m,d)*nonisolated[d]*first**(m-d)*(first+second)**d for d in range(m+1))
expected=[1,1,((1<<50)-1)**49,1<<4950,1<<4950,nonisolated[99],1<<99,1,1<<99,5*7**48,(1<<98)-1,3**97,
          nonempty_matrix(49,50)*nonisolated[50],nonempty_matrix(49,50)*nonisolated[50],nonempty_matrix(50,49)*nonisolated[49],
          ((1<<49)-1)**50*(1<<2500),mixed]
fixture='const std::vector<int> moduli{'+','.join(map(str,MODULI))+'};\nconst std::vector<std::vector<int>> expected_max{'+','.join('{'+','.join(str(x%mod) for mod in MODULI)+'}' for x in expected)+'};\n'
TESTS=r'''
#include <bit>
#include <chrono>
#include <climits>
#include <cstdlib>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
#include <string>
#include <unordered_map>
using E=std::pair<int,int>;using U=std::uint64_t;
U checks=0,small_graphs=0,small_groups=0,n6_graphs=0,n6_groups=0,api_calls=0,root_cases=0,matrix_masks=0,clique_masks=0,primitive_checks=0,maximum_calls=0,batch_calls=0,invalid_calls=0,checksum=0;
void require(bool b,const char* why){++checks;if(!b){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
int call(int n,const std::vector<E>& edges,int root=0,int modulus=1000000007){
 const auto old=edges;const int got=count_graphs_preserving_root_walk_lengths(n,edges,root,modulus);
 require(got>=0&&got<modulus,"canonical modular residue including0 andmodulus1");require(old==edges,"const edge input unchanged");
 checksum=checksum*1000003+U(got+1);++api_calls;return got;
}
std::pair<std::string,bool> complete_word(int n,const std::vector<unsigned>& adjacent){
 // Literal deterministic reachable-set outputs, until first repeated set.
 // No parity-distance, A/B/C, DP, or guessed finite horizon in this oracle.
 std::vector<int> seen(1U<<n,-1);std::string key;unsigned set=1,ever=0;
 while(seen[set]<0){seen[set]=int(key.size());key.push_back(char(set));ever|=set;unsigned next=0;
  for(int v=0;v<n;++v)if(set>>v&1)next|=adjacent[v];
  set=next;
 }
 key.insert(key.begin(),char(seen[set]));return {key,ever==(1U<<n)-1};
}
std::vector<E> decode(unsigned mask,const std::vector<E>& possible){std::vector<E> edges;for(unsigned j=0;j<possible.size();++j)if(mask>>j&1)edges.push_back(possible[j]);return edges;}
void all_graphs(int n){
 std::vector<E> possible;for(int u=0;u<n;++u)for(int v=u;v<n;++v)possible.push_back({u,v});
 struct Group{unsigned count=0,representative=0;};std::unordered_map<std::string,Group> groups;
 struct Record{unsigned mask;std::string key;};std::vector<Record> records;
 for(unsigned mask=0;mask<(1U<<possible.size());++mask){
  std::vector<unsigned> adjacent(n);for(unsigned j=0;j<possible.size();++j)if(mask>>j&1){auto [u,v]=possible[j];adjacent[u]|=1U<<v;adjacent[v]|=1U<<u;}
  auto [key,connected]=complete_word(n,adjacent);if(!connected)continue;
  auto& g=groups[key];++g.count;g.representative=mask;
  if(n<=5){records.push_back({mask,key});++small_graphs;}else ++n6_graphs;
 }
 if(n<=5){small_groups+=groups.size();
  for(const auto& record:records){const auto& g=groups.at(record.key);auto edges=decode(record.mask,possible);
   require(call(n,edges)==int(g.count),"ALL labeled small loop graphs actual fence equals exact size of its COMPLETE infinite-language group");
   const int root=int(record.mask%unsigned(n));auto changed=edges;
   for(auto& [u,v]:changed){u=(u+root)%n;v=(v+root)%n;std::swap(u,v);}std::reverse(changed.begin(),changed.end());
   require(call(n,changed,root)==int(g.count),"arbitrary supplied root through label bijection and reversed endpoints/list order");++root_cases;
  }
 }else n6_groups=groups.size();
 // One full API representative of EVERY language group for EVERY modulus;
 // N6 group counts are derived from ALL 2^21 graphs, not a sample estimate.
 for(const auto& [key,g]:groups){(void)key;auto edges=decode(g.representative,possible);
  for(int modulus:moduli)require(call(n,edges,0,modulus)==int(g.count%unsigned(modulus)),"every language group size reduced by prime/composite/1/INT_MAX modulus");
 }
}
void primitives(){
 struct MatrixCase{int previous,current;std::vector<std::vector<U>> both,mandatory_a;};std::vector<MatrixCase> cases;
 for(int p=0;p<=4;++p)for(int m=0;m<=4;++m){MatrixCase item{p,m,std::vector<std::vector<U>>(p+1,std::vector<U>(m+1)),std::vector<std::vector<U>>(p+1,std::vector<U>(p+1))};
  for(unsigned mask=0;mask<(1U<<(p*m));++mask){unsigned rows=0,columns=0;
   for(int i=0;i<p;++i)for(int j=0;j<m;++j)if(mask>>(i*m+j)&1){rows|=1U<<i;columns|=1U<<j;}
   const int empty=m-std::popcount(columns),empty_rows=p-std::popcount(rows);
   for(int y=0;y<=p;++y){const unsigned must=(1U<<y)-1;if((rows&must)==must)++item.both[y][empty];}
   for(int z=0;z<=p;++z){const unsigned must=(1U<<z)-1;if((rows&must)==must)++item.mandatory_a[z][empty_rows];}
   ++matrix_masks;
  }
  cases.push_back(std::move(item));
 }
 std::vector<std::vector<U>> c_hist(7);
 for(int m=0;m<=6;++m){std::vector<E> possible;for(int u=0;u<m;++u)for(int v=u;v<m;++v)possible.push_back({u,v});c_hist[m].assign(m+1,0);
  for(unsigned mask=0;mask<(1U<<possible.size());++mask){unsigned covered=0;for(unsigned k=0;k<possible.size();++k)if(mask>>k&1){covered|=1U<<possible[k].first;covered|=1U<<possible[k].second;}
   for(int y=0;y<=m;++y){const unsigned must=(1U<<y)-1;if((covered&must)==must)++c_hist[m][y];}++clique_masks;
  }
 }
 for(int modulus:moduli){walk_profile_count_detail::Tables table(6,modulus);const auto& ring=table.ring;
  for(const auto& item:cases){const int p=item.previous,m=item.current;
   for(int y=0;y<=p;++y)for(int x=0;x<=m;++x){require(table.between(p,m,y,x)==int(item.both[y][x]%unsigned(modulus)),"B PIE equals ALL literal matrices with required rows nonempty and exactlyx empty columns, including empty axes and0^0");++primitive_checks;}
   // Treat p as the CURRENT size, m as lower-neighbor count for A edges.
   for(int z=0;z<=p;++z)for(int x=0;x+z<=p;++x){const int got=ring.mul(table.choose[p-z][x],table.power[m][p-x]);require(got==int(item.mandatory_a[z][x]%unsigned(modulus)),"A transition equals ALL literal matrices, required B-empty vertices getnonemptyA, exact newunfulfilledset");++primitive_checks;}
  }
  for(int m=0;m<=6;++m)for(int y=0;y<=m;++y){require(table.finish(m,y)==int(c_hist[m][y]%unsigned(modulus)),"terminal PIE equals EVERY loop-allowed graph with specifiedfirsty vertices nonisolated");++primitive_checks;}
  require(table.power[0][0]==ring.one()&&table.power[0][1]==0,"empty selection means0^0=1modm, no inverse or field required");
 }
}
void maximum(){
 constexpr int n=100;
 for(int pattern=0;pattern<int(expected_max.size());++pattern){std::vector<E> edges;int root=0;
  auto path=[&]{for(int v=1;v<n;++v)edges.push_back({v-1,v});};
  auto star=[&]{for(int v=1;v<n;++v)edges.push_back({0,v});};
  if(pattern==0)path();
  if(pattern==1)star();
  if(pattern==2)for(int u=0;u<50;++u)for(int v=50;v<n;++v)edges.push_back({u,v});
  if(pattern==3)for(int u=0;u<n;++u)for(int v=u;v<n;++v)edges.push_back({u,v});
  if(pattern==4){star();edges.push_back({0,0});}
  if(pattern==5){star();for(int v=1;v<n;++v)edges.push_back({v,v});}
  if(pattern==6){path();edges.push_back({0,0});}
  if(pattern==7||pattern==8){path();edges.push_back({n-1,n-1});if(pattern==8)root=n-1;}
  if(pattern==9){for(int v=1;v<n-1;++v)edges.push_back({v-1,v});edges.push_back({n-2,0});edges.push_back({0,n-1});}
  if(pattern==10||pattern==11){for(int u=0;u<2;++u)for(int v=2;v<n;++v)edges.push_back({u,v});if(pattern==11)root=2;}
  if(pattern==12||pattern==13||pattern==14){const int p=pattern==14?50:49,begin=p+1,m=n-begin;
   for(int u=1;u<=p;++u)edges.push_back({0,u});
   if(pattern==13){for(int j=0;j<m;++j)edges.push_back({1+j%p,begin+j});}
   else for(int u=1;u<=p;++u)for(int v=begin;v<n;++v)edges.push_back({u,v});
   for(int v=begin;v<n;++v)edges.push_back({v,v});
  }
  if(pattern==15){edges.push_back({0,0});for(int u=1;u<=49;++u){edges.push_back({0,u});for(int v=50;v<n;++v)edges.push_back({u,v});}}
  if(pattern==16){for(int u=1;u<=51;++u)edges.push_back({0,u});for(int u=1;u<=3;++u)edges.push_back({u,u});
   for(int v=52;v<n;++v)for(int u=1;u<=51;++u)edges.push_back({u,v});}
  for(std::size_t k=0;k<moduli.size();++k){require(call(n,edges,root,moduli[k])==expected_max[pattern][k],"MAX N100 pureB/pureA/mixedA-B-C/root/loop/denseM5050 versus independently generated EXACT integer formulas");++maximum_calls;}
 }
 for(int i=0;i<25000;++i){const std::vector<E> edges=(i&1)?std::vector<E>{{0,1}}:std::vector<E>{{0,0},{0,1}};require(call(2,edges)==((i&1)?1:2),"original T25000 and sumN²100000, interleaved fresh tables/graphs");++batch_calls;}
}
void boundaries(){
 require(call(5,{{0,1},{1,2},{0,3},{2,4}})==3,"original first sample exact count");
 require(call(5,{{0,1},{1,2},{2,3},{3,4},{0,4}})==35,"original fivecycle sample");
 require(call(10,{{0,0},{0,1},{0,2},{0,3},{0,4},{0,5},{0,6},{0,7},{0,8},{0,9}})==371842544,"original rootloop sample2^45mod1e9+7");
 auto reject=[](int n,const std::vector<E>& edges,int root=0,int modulus=1000000007){const auto old=edges;bool caught=false;try{(void)count_graphs_preserving_root_walk_lengths(n,edges,root,modulus);}catch(const std::invalid_argument&){caught=true;}require(caught&&edges==old,"invalid API rejects and preserves input");++invalid_calls;};
 reject(INT_MIN,{});reject(0,{});reject(1,{{0,0}});reject(101,{});reject(INT_MAX,{});
 reject(2,{{0,1}},-1);reject(2,{{0,1}},2);reject(2,{{0,1}},INT_MAX);
 reject(2,{{0,1}},0,0);reject(2,{{0,1}},0,-1);reject(2,{{0,1}},0,INT_MIN);
 reject(2,{{INT_MIN,1}});reject(2,{{0,INT_MAX}});reject(2,{{0,2}});
 reject(2,{{0,1},{1,0}});reject(2,{{0,1},{0,0},{0,0}});reject(2,{});reject(3,{{0,1},{2,2}});
 reject(2,std::vector<E>(4,{0,0}));reject(100,std::vector<E>(5051,{0,0}));
 require(call(2,{{0,0},{0,1}},0,2)==0,"valid graph count can have residue0; not an infeasible profile");
 require(call(2,{{0,0},{0,1}},0,1)==0,"modulus1 valid andevery count0");
 require(call(2,{{0,1}})==1,"fresh default modulus after invalid and modulus1 calls");
}
int main(){auto begin=std::chrono::steady_clock::now();primitives();boundaries();for(int n=2;n<=6;++n)all_graphs(n);maximum();
 require(small_graphs==23940&&small_groups==932&&n6_graphs==1709056&&n6_groups==10263,"exact enumeration scope separatefrominitialPythonresearchprobe");
 std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"allConnectedLoopGraphsN2to5\":"<<small_graphs<<",\"languageGroupsN2to5\":"<<small_groups<<",\"allConnectedLoopGraphsN6\":"<<n6_graphs<<",\"languageGroupsN6\":"<<n6_groups<<",\"nonzeroRootRelabelCases\":"<<root_cases<<",\"literalBipartiteMatrices\":"<<matrix_masks<<",\"literalTerminalLoopGraphs\":"<<clique_masks<<",\"primitiveChecks\":"<<primitive_checks<<",\"maximumN100Calls\":"<<maximum_calls<<",\"maximumBatchCalls\":"<<batch_calls<<",\"invalidCalls\":"<<invalid_calls<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-countgraphs-check-') as tmp:
    src=Path(tmp)/'check.cpp';binary=Path(tmp)/'check';src.write_text(blocks[0]+'\n'+fixture+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];env=dict(os.environ)
    if '--sanitize' in sys.argv:
        flags=['-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'];env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    subprocess.run(['g++',*flags,str(src),'-o',str(binary)],check=True,timeout=120)
    result=subprocess.run(['/usr/bin/time','-f','peak_rss_kib=%M',str(binary)],capture_output=True,text=True,env=env,timeout=300)
    if result.returncode:print(result.stdout,end='',file=sys.stderr);print(result.stderr,end='',file=sys.stderr);result.check_returncode()
    output=json.loads(result.stdout);output['peakRSSKiB']=int(re.search(r'peak_rss_kib=(\d+)',result.stderr)[1]);output['cppSha256']=hashlib.sha256(blocks[0].encode()).hexdigest();output['sanitized']='--sanitize' in sys.argv
    print(json.dumps(output,ensure_ascii=False,indent=2))
