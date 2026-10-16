#!/usr/bin/env python3
"""Extract the published C++20 fence; compare local permutations AND literal trails."""
from pathlib import Path
import hashlib,json,math,os,re,subprocess,sys,tempfile
args=[x for x in sys.argv[1:] if x!='--sanitize']
article=Path(args[0]) if args else (Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/almost-dag-edge-routing-pairing-frontier-cycle-count.mdx')
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('exactly one complete always-visible C++20 fence')
moduli=[1,2,6,97,1000000007,2147483647]
# Exact integers from independent combinatorial families, never the frontier DP.
maximum=[math.factorial(49),math.factorial(32)**2,1,1,math.factorial(48),
         3*math.factorial(47),math.factorial(46),6*math.factorial(47),
         32*math.factorial(32),31*32*math.factorial(31),31*32*math.factorial(31),
         math.factorial(5)**50,0,0]
fixture='const std::vector<int> moduli{'+','.join(map(str,moduli))+'};\nconst std::vector<std::vector<int>> maximum_expected{'+','.join('{'+','.join(str(x%m) for m in moduli)+'}' for x in maximum)+'};\n'
TESTS=r'''
#include <bit>
#include <chrono>
#include <climits>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <numeric>
#include <random>
#include <utility>
using U=std::uint64_t;using E=std::pair<int,int>;
U checks=0,calls=0,graphs=0,balanced_cases=0,positive_cases=0,zero_cases=0,pairings=0,valid_pairings=0,trail_calls=0,trail_schemes=0,random_cases=0,maximum_calls=0,invalid_calls=0,batch_calls=0,unbalanced_role_calls=0,checksum=0;
struct Instance{std::vector<std::string> a;std::string roles;};
void require(bool ok,const char* why){++checks;if(!ok){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
Instance make(int n,std::string roles,const std::vector<E>& edges){Instance x{std::vector<std::string>(n,std::string(n,'0')),std::move(roles)};for(auto [u,v]:edges)x.a[u][v]='1';return x;}
int call(const Instance& x,int modulus=1000000007){auto old=x;const int result=count_almost_dag_edge_routings(x.a,x.roles,modulus);require(result>=0&&result<modulus,"canonical residue");require(old.a==x.a&&old.roles==x.roles,"input remains unchanged");++calls;checksum=checksum*1000003+U(result+1);return result;}
std::string forced_roles(const std::vector<std::string>& a){int n=int(a.size()),senders=0;std::string roles(n,'.');for(int v=0;v<n;++v){int delta=0;for(int w=0;w<n;++w)delta+=(a[v][w]=='1')-(a[w][v]=='1');if(delta>1||delta< -1)return {};if(delta==1){roles[v]='S';++senders;}if(delta== -1)roles[v]='R';}return senders?roles:std::string{};}
U factorial_small(int n){U result=1;for(int x=2;x<=n;++x)result*=unsigned(x);return result;}
U literal_pairings(const Instance& x){
 // Every incoming port is paired with an independently permuted outgoing port.
 // Only after ALL pairings are fixed do we trace sources and require every edge.
 // There is no vertex sweep, backward-edge state, or cycle formula here.
 const int n=int(x.a.size());std::vector<E> edges;for(int u=0;u<n;++u)for(int v=0;v<n;++v)if(x.a[u][v]=='1')edges.push_back({u,v});const int m=int(edges.size());
 std::vector<std::vector<int>> in(n),out(n);for(int e=0;e<m;++e){out[edges[e].first].push_back(e);in[edges[e].second].push_back(e);}
 int s=0;for(char r:x.roles)s+=(r=='S');int send=0,receive=0;for(int v=0;v<n;++v){if(x.roles[v]=='S')in[v].push_back(m+send++);if(x.roles[v]=='R')out[v].push_back(m+s+receive++);if(in[v].size()!=out[v].size())return 0;}
 std::vector<int> next(m+s,-1);U count=0;
 std::function<void(int)> enumerate=[&](int v){
  if(v==n){++pairings;std::vector<bool> seen(m);for(int z=0;z<s;++z){int port=m+z;for(;;){int following=next[port];if(following>=m+s)break;if(seen[following])return;seen[following]=true;port=following;}}
   if(std::find(seen.begin(),seen.end(),false)==seen.end()){++count;++valid_pairings;}return;}
  auto choices=out[v];std::sort(choices.begin(),choices.end());do{for(std::size_t k=0;k<choices.size();++k)next[in[v][k]]=choices[k];enumerate(v+1);}while(std::next_permutation(choices.begin(),choices.end()));
 };enumerate(0);return count;
}
U literal_trails(const Instance& x){
 // Directly build sender-labelled trails one edge at a time. A receiver may be
 // passed through; stopping consumes that receiver. Repeated vertices allowed.
 const int n=int(x.a.size());std::vector<std::vector<E>> out(n);std::vector<int> senders;int m=0;for(int u=0;u<n;++u){if(x.roles[u]=='S')senders.push_back(u);for(int v=0;v<n;++v)if(x.a[u][v]=='1')out[u].push_back({v,m++});}
 require(m<63,"literal trail oracle edge-mask domain");const U all=(U(1)<<m)-1;U count=0;
 std::function<void(int,int,U,U)> walk=[&](int path,int vertex,U used,U receivers){++trail_calls;
  if(x.roles[vertex]=='R'&&!(receivers>>vertex&1)){const U next_receivers=receivers|(U(1)<<vertex);if(path+1==int(senders.size())){if(used==all){++count;++trail_schemes;}}else walk(path+1,senders[path+1],used,next_receivers);}
  for(auto [v,id]:out[vertex])if(!(used>>id&1))walk(path,v,used|(U(1)<<id),receivers);
 };walk(0,senders[0],0,0);return count;
}
void verify_small(const Instance& x){const U by_pairing=literal_pairings(x),by_trails=literal_trails(x);require(by_pairing==by_trails,"independent full port permutation AND literal trail decomposition agree");require(call(x)==int(by_trails%1000000007),"published fence equals BOTH literal all-scheme oracles");for(int modulus:moduli)require(call(x,modulus)==int(by_trails%unsigned(modulus)),"all small well-balanced role assignments and six prime/composite/boundary moduli");if(by_trails)++positive_cases;else ++zero_cases;}
void exhaustive(){for(int n=2;n<=5;++n){
 std::vector<std::string> legal_roles;int total=1;for(int v=0;v<n;++v)total*=3;
 for(int code=0;code<total;++code){int copy=code,s=0,r=0;std::string roles(n,'.');for(int v=0;v<n;++v){int c=copy%3;copy/=3;if(c==1){roles[v]='S';++s;}if(c==2){roles[v]='R';++r;}}if(s>0&&s==r)legal_roles.push_back(roles);}
 std::vector<E> forward,backward;for(int u=0;u<n;++u)for(int v=u+1;v<n;++v){forward.push_back({u,v});backward.push_back({v,u});}std::vector<unsigned> back_masks{0};for(unsigned i=0;i<backward.size();++i){back_masks.push_back(1U<<i);for(unsigned j=0;j<i;++j)back_masks.push_back((1U<<i)|(1U<<j));}
 for(unsigned f=0;f<(1U<<forward.size());++f)for(unsigned b:back_masks){std::vector<E> edges;for(unsigned j=0;j<forward.size();++j){if(f>>j&1)edges.push_back(forward[j]);if(b>>j&1)edges.push_back(backward[j]);}Instance x=make(n,std::string(n,'.'),edges);x.roles=forced_roles(x.a);++graphs;
  const auto balanced_roles=x.roles;
  if(!balanced_roles.empty()){++balanced_cases;verify_small(x);}
  // Every OTHER structurally admissible S/R/. assignment has a violated local
  // conservation equation. Check all, not one representative zero assignment.
  for(const auto& roles:legal_roles)if(roles!=balanced_roles){x.roles=roles;require(call(x)==0,"ALL other legal small role assignments violate conservation and have zero schemes");++unbalanced_role_calls;}
 }
}}
void random_small(){std::mt19937 rng(151052603);for(int attempt=0;attempt<500000&&random_cases<1000;++attempt){int n=6+int(rng()%4);Instance x=make(n,std::string(n,'.'),{});for(int u=0;u<n;++u)for(int v=u+1;v<n;++v)if(rng()%100<22)x.a[u][v]='1';int k=int(rng()%3);while(k){int u=int(rng()%n),v=int(rng()%n);if(u>v&&x.a[u][v]=='0'){x.a[u][v]='1';--k;}}x.roles=forced_roles(x.a);if(x.roles.empty())continue;U product=1;int m=0;for(int v=0;v<n;++v){int d=x.roles[v]=='S';for(int u=0;u<n;++u)d+=(x.a[u][v]=='1');product*=factorial_small(d);for(char c:x.a[v])m+=(c=='1');}if(product>100000||m>20)continue;verify_small(x);++random_cases;}require(random_cases==1000,"1000 accepted random full-oracle cases N6..9");}
Instance star(int p){const int n=2*p+1;std::string roles(n,'.');std::vector<E> edges;for(int i=0;i<p;++i){roles[i]='S';roles[p+1+i]='R';edges.push_back({i,p});edges.push_back({p,p+1+i});}return make(n,roles,edges);}
Instance combine(Instance first,const Instance& second,int total=100){int offset=int(first.a.size());first.roles.resize(total,'.');for(int i=0;i<int(second.a.size());++i)first.roles[offset+i]=second.roles[i];for(auto& row:first.a)row.resize(total,'0');first.a.resize(total,std::string(total,'0'));for(int u=0;u<int(second.a.size());++u)for(int v=0;v<int(second.a.size());++v)first.a[offset+u][offset+v]=second.a[u][v];return first;}
Instance wide(int p,int feedback){int hub=p,branch=p+1,tails=branch+p+feedback,receivers=tails+feedback,n=receivers+p;std::string roles(n,'.');std::vector<E> e;for(int i=0;i<p;++i){roles[i]='S';roles[receivers+i]='R';e.push_back({i,hub});}for(int i=0;i<p+feedback;++i){e.push_back({hub,branch+i});if(i<feedback){e.push_back({branch+i,tails+i});e.push_back({tails+i,hub});}else e.push_back({branch+i,receivers+i-feedback});}return make(n,roles,e);}
Instance reverse_instance(const Instance& x){int n=int(x.a.size());std::string roles(n,'.');std::vector<E> edges;for(int u=0;u<n;++u){char r=x.roles[u];roles[n-1-u]=r=='S'?'R':r=='R'?'S':'.';for(int v=0;v<n;++v)if(x.a[u][v]=='1')edges.push_back({n-1-v,n-1-u});}return make(n,roles,edges);}
void maximums(){
 auto gadget1=make(3,"S.R",{{0,1},{1,0},{0,2}});
 auto gadget3=make(5,"SS.RR",{{0,2},{0,4},{1,2},{2,0},{2,3}});
 auto gadget2=make(6,"S....R",{{0,2},{1,3},{2,1},{2,5},{3,4},{4,2}});
 auto gadget6=make(5,".SSRR",{{0,1},{1,0},{1,2},{1,4},{2,1},{2,3}});
 verify_small(gadget1);verify_small(gadget3);verify_small(gadget2);verify_small(gadget6);
 for(int p=1;p<=4;++p)for(int feedback=1;feedback<=2;++feedback){auto x=wide(p,feedback);U f=factorial_small(p)*unsigned(p)*(feedback==2?unsigned(p+1):1);require(literal_pairings(x)==f,"wide feedback-excursion family independently agrees with full permutations");require(literal_trails(x)==f,"wide family also agrees with direct trails");require(call(x)==int(f),"wide-family expected closed form");auto reversed=reverse_instance(x);require(call(reversed)==int(f),"path reversal swaps shared back heads into shared back tails");}
 std::vector<Instance> cases;cases.push_back(combine(star(49),make(1,".",{})));
 {std::vector<E> e;std::string roles(100,'.');for(int i=0;i<32;++i){roles[i]='S';roles[66+i]='R';e.push_back({i,32});e.push_back({32,33+i});e.push_back({33+i,65});e.push_back({65,66+i});}cases.push_back(make(100,roles,e));}
 {std::vector<E> e;for(int i=0;i<99;++i)e.push_back({i,i+1});cases.push_back(make(100,"S"+std::string(98,'.')+"R",e));}
 cases.push_back(make(100,"R"+std::string(98,'.')+"S",{{99,0}}));
 cases.push_back(combine(gadget1,star(48)));cases.push_back(combine(gadget3,star(47)));cases.push_back(combine(gadget2,star(46)));cases.push_back(combine(gadget6,star(47)));
 cases.push_back(combine(wide(32,1),make(1,".",{})));auto broad=combine(wide(31,2),make(2,"..",{}));cases.push_back(broad);cases.push_back(reverse_instance(broad));
 {std::string roles(100,'.');std::vector<E> e;for(int i=0;i<25;++i){roles[i]='S';roles[75+i]='R';e.push_back({i,25+i/5});e.push_back({70+i/5,75+i});}for(int layer=0;layer<9;++layer)for(int i=0;i<5;++i)for(int j=0;j<5;++j)e.push_back({25+5*layer+i,30+5*layer+j});cases.push_back(make(100,roles,e));}
 {std::vector<E> e;for(int i=0;i<100;++i)for(int j=i+1;j<100;++j)e.push_back({i,j});e.push_back({99,0});e.push_back({98,1});cases.push_back(make(100,std::string(50,'S')+std::string(50,'R'),e));}
 cases.push_back(make(100,"SR"+std::string(98,'.'),{{0,1},{2,3},{3,2}}));
 require(cases.size()==maximum_expected.size(),"all exact maximum family fixtures");
 for(std::size_t j=0;j<cases.size();++j)for(std::size_t k=0;k<moduli.size();++k){require(cases[j].a.size()==100,"maximum N100");require(call(cases[j],moduli[k])==maximum_expected[j][k],"N100 exact combinatorial family expectation, all six moduli");++maximum_calls;}
 // Original aggregate boundaries: twenty N2 cases, or two N100 cases.
 for(int i=0;i<20;++i){require(call(make(2,"SR",{{0,1}}))==1,"original T20 independent calls");++batch_calls;}
 for(int i:{8,9}){require(call(cases[i])==maximum_expected[i][4],"original sum N^2=20000 for two N100 cases");++batch_calls;}
}
void samples(){const std::vector<Instance> cases{
 { {"00100000","00100000","00011000","00000100","00000100","00000011","00000000","00000000"},"SS....RR"},
 { {"0001000000000","0001000000000","0001000000000","0000111000000","0000000000000","0000000000000","0000000000000","0000000001000","0000000001000","0000000000110","0000000000000","0000000000000","0000000000000"},"SSS.RRRSS.RR."},
 { {"00101","00100","10010","00000","00000"},"SS.RR"},
 { {"001000","000100","010001","000010","001000","000000"},"S....R"},
 { {"010","101","100"},"RS."},
 { {"0100","0010","1000","0100"},".R.S"},
 { {"0000","0011","0100","0010"},".SR."},
 { {"01000","10101","01010","00000","00000"},".SSRR"},
 { {"001010","000010","000010","000010","100101","000000"},"SS..RR"}};
 const int expected[]{4,12,3,1,2,1,2,6,24};for(std::size_t i=0;i<cases.size();++i){require(call(cases[i])==expected[i],"all nine original samples");verify_small(cases[i]);}
}
void invalids(){const auto base=make(2,"SR",{{0,1}});auto reject=[&](const Instance& x,int modulus=1000000007){bool caught=false;try{(void)count_almost_dag_edge_routings(x.a,x.roles,modulus);}catch(const std::invalid_argument&){caught=true;}require(caught,"invalid API rejects");++invalid_calls;};
 reject({{},""});reject({{"0"},"S"});reject(make(101,"SR"+std::string(99,'.'),{}));reject({{"01","0"},"SR"});reject({{"01",""},"SR"});reject({{"01","00"},"S"});reject({{"01","00"},"SX"});reject({{"01","00"},"SS"});reject({{"01","00"},".."});reject({{"01","00"},"S."});reject({{"02","00"},"SR"});reject({{"11","00"},"SR"});reject(make(3,"SR.",{{1,0},{2,0},{2,1}}));reject(base,0);reject(base,-1);reject(base,INT_MIN);
 // An early degree mismatch must not suppress a later structural violation.
 reject({{"00","0x"},"SR"});reject({{"00","01"},"SR"});
 require(call(make(2,"SR",{}))==0,"structurally valid degree-imbalanced graph returns zero");
 auto onlycycle=make(4,"SR..",{{0,1},{2,3},{3,2}});require(call(onlycycle)==0,"balanced but isolated closed component returns zero");
 require(call(star(2),2)==0,"zero residue for valid nonempty family is not an error");for(int j=0;j<50;++j){require(call(base,1)==0,"modulus one");require(call(base,INT_MAX)==1,"state independent after zero residue and invalid calls");}
}
int main(){auto start=std::chrono::steady_clock::now();exhaustive();random_small();samples();maximums();invalids();double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<calls<<",\"allSmallGraphs\":"<<graphs<<",\"balancedSmallCases\":"<<balanced_cases<<",\"positiveOracleCases\":"<<positive_cases<<",\"zeroOracleCases\":"<<zero_cases<<",\"literalLocalPairings\":"<<pairings<<",\"validLiteralPairings\":"<<valid_pairings<<",\"literalTrailRecursions\":"<<trail_calls<<",\"literalTrailSchemes\":"<<trail_schemes<<",\"randomCases\":"<<random_cases<<",\"maximumCalls\":"<<maximum_calls<<",\"unbalancedRoleCalls\":"<<unbalanced_role_calls<<",\"originalBatchCalls\":"<<batch_calls<<",\"invalidCalls\":"<<invalid_calls<<",\"checksum\":\""<<checksum<<"\""<<",\"seconds\":"<<seconds<<"}\n";}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-routing-') as temp:
    cpp=Path(temp)/'check.cpp';binary=Path(temp)/'check';timefile=Path(temp)/'time'
    cpp.write_text(blocks[0]+'\n'+fixture+TESTS)
    flags=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'] if '--sanitize' in sys.argv else ['-O2']
    subprocess.run(['g++','-std=c++20',*flags,'-Wall','-Wextra','-Werror',str(cpp),'-o',str(binary)],check=True)
    env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    result=subprocess.run(['/usr/bin/time','-f','%M','-o',str(timefile),str(binary)],capture_output=True,text=True,env=env,timeout=300)
    if result.returncode:sys.stderr.write(result.stdout+result.stderr);raise SystemExit(result.returncode)
    data=json.loads(result.stdout);data['cppSha256']=hashlib.sha256(blocks[0].encode()).hexdigest();data['maxRssKiB']=int(timefile.read_text().strip());data['sanitizers']='address,undefined' if '--sanitize' in sys.argv else None
    print(json.dumps(data,ensure_ascii=False,indent=2))
