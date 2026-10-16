from pathlib import Path
import re, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
checks={
'restart-board-trial-expectation':r'''
 auto gaussian=[](int n,int m,const vector<int>&resets)->optional<long double>{
   vector<bool>bad(n);for(int x:resets)bad[x]=true;
   vector<vector<long double>>a(n,vector<long double>(n+1));
   for(int i=0;i<n;++i){a[i][i]=1;if(bad[i])a[i][0]-=1;else{a[i][n]=1;for(int step=1;step<=m;++step)if(i+step<n)a[i][i+step]-=1.0L/m;}}
   for(int j=0;j<n;++j){int pivot=j;for(int i=j+1;i<n;++i)if(fabsl(a[i][j])>fabsl(a[pivot][j]))pivot=i;if(fabsl(a[pivot][j])<1e-15L)return nullopt;swap(a[j],a[pivot]);long double divisor=a[j][j];for(int k=j;k<=n;++k)a[j][k]/=divisor;for(int i=0;i<n;++i)if(i!=j){long double coefficient=a[i][j];for(int k=j;k<=n;++k)a[i][k]-=coefficient*a[j][k];}}
   return a[0][n];
 };
 for(int n=1;n<=8;++n)for(int m=1;m<=4;++m)for(int mask=0;mask<(1<<(n-1));++mask){vector<int>reset;for(int i=1;i<n;++i)if((mask>>(i-1))&1)reset.push_back(i);auto expected=gaussian(n,m,reset),got=restart_board_expectation(n,m,reset);if(got.has_value()!=expected.has_value()){cerr<<"board n="<<n<<" m="<<m<<" reset-mask="<<mask<<" actual="<<got.has_value()<<" gaussian="<<expected.has_value()<<"\n";}assert(got.has_value()==expected.has_value());if(got)assert(close_enough(*got,*expected,1e-11L));}
 auto affine=[](int n,int m,const vector<int>&reset){vector<bool>bad(n);for(int x:reset)bad[x]=true;vector<long double>a(n+m),b(n+m);for(int i=n-1;i>=0;--i){if(bad[i])a[i]=1;else{b[i]=1;for(int s=1;s<=m;++s){a[i]+=a[i+s]/m;b[i]+=b[i+s]/m;}}}return b[0]/(1-a[0]);};
 assert(close_enough(*restart_board_expectation(2,2,{}),1.5L));
 assert(close_enough(*restart_board_expectation(2,2,{1}),2.0L));
 assert(!restart_board_expectation(100,6,{11,12,13,14,15,16,17,18,19,20}));
 assert(close_enough(*restart_board_expectation(100000,2,{2997,92458}),201932.2222222222L,1e-10L));
 assert(close_enough(*restart_board_expectation(100000,1,{}),100000.0L));
 assert(close_enough(*restart_board_expectation(100000,100000,{}),powl(1.00001L,99999),1e-11L));
 vector<int>isolated;for(int i=1;i<=10;++i)isolated.push_back(5000*i);assert(close_enough(*restart_board_expectation(100000,2,isolated),affine(100000,2,isolated),1e-9L));
 vector<int>block;for(int i=1;i<=10;++i)block.push_back(i);assert(close_enough(*restart_board_expectation(11,11,block),11.0L));
 assert(close_enough(*restart_board_expectation(100000,11,block),affine(100000,11,block),1e-9L));
 assert(!restart_board_expectation(100000,10,block));
 bool rejected=false;try{restart_board_expectation(10,6,{2,2});}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'sushi-count-state-rolling':r'''
 for(int n=0;n<=7;++n){int states=1<<(2*n);vector<long double>memo(states,-1);memo[0]=0;function<long double(int)>labeled=[&](int code)->long double{if(memo[code]>=0)return memo[code];long double total=n;int positive=0;for(int i=0;i<n;++i)if((code>>(2*i))&3){++positive;total+=labeled(code-(1<<(2*i)));}return memo[code]=total/positive;};for(int code=0;code<states;++code){vector<int>plates(n);for(int i=0;i<n;++i)plates[i]=(code>>(2*i))&3;auto expected=labeled(code),got=sushi_count_expectation(plates);assert(close_enough(got,expected,1e-11L));}}
 assert(close_enough(sushi_count_expectation({1,1,1}),5.5L));
 assert(close_enough(sushi_count_expectation({3}),3.0L));
 assert(close_enough(sushi_count_expectation({0,0,1}),3.0L));
 long double harmonic=0;for(int i=1;i<=300;++i)harmonic+=1.0L/i;
 auto one=sushi_count_expectation(vector<int>(300,1));assert(close_enough(one,300*harmonic,1e-11L));
 auto two=sushi_count_expectation(vector<int>(300,2)),three=sushi_count_expectation(vector<int>(300,3));assert(isfinite(two)&&isfinite(three));assert(one<two&&two<three&&three<=900*harmonic);
 assert(sushi_count_expectation(vector<int>(300,0))==0);
 bool rejected=false;try{sushi_count_expectation({4});}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'increasing-record-reward-probability':r'''
 auto backward=[](const vector<long long>&a){int n=a.size();long long inverse=mod_power(n,P-2);vector<long long>future(n+1);for(int current=n-1;current>=0;--current){long long total=0;for(int next=current+1;next<=n;++next){long long reward=(a[next-1]%P+P)%P;total=(total+reward+future[next])%P;}future[current]=total*inverse%P;}return int(future[0]);};
 for(int n=1;n<=6;++n){int states=1;for(int i=0;i<n;++i)states*=5;for(int code=0;code<states;++code){vector<long long>a(n);int value=code;for(auto&x:a){x=value%5-2;value/=5;}assert(increasing_record_reward(a)==backward(a));}}
 for(int trial=0;trial<1000;++trial){vector<long long>a(1+rng()%40);for(auto&x:a)x=static_cast<long long>((uint64_t(rng())<<32)|rng());assert(increasing_record_reward(a)==backward(a));}
 assert(increasing_record_reward({LLONG_MIN,0,LLONG_MAX})==backward({LLONG_MIN,0,LLONG_MAX}));
 assert(increasing_record_reward({3,2,6})==776412280);
 assert(increasing_record_reward({998244352})==998244352);
 assert(increasing_record_reward({3,14,159,2653,58979,323846,2643383,27950288,419716939})==545252774);
 assert(increasing_record_reward(vector<long long>(300000,0))==0);
 long long ratio=300001*mod_power(300000,P-2)%P;
 assert(increasing_record_reward(vector<long long>(300000,1))==(mod_power(ratio,300000)+P-1)%P);
''',
'random-swap-symmetry-two-state':r'''
 for(int n=1;n<=6;++n){vector<vector<int>>permutations;vector<int>start(n);iota(start.begin(),start.end(),0);do{permutations.push_back(start);}while(next_permutation(start.begin(),start.end()));map<vector<int>,int>number;for(int i=0;i<int(permutations.size());++i)number[permutations[i]]=i;vector<long long>distribution(permutations.size());distribution[0]=1;long long inverse_pairs=mod_power(n*n,P-2);for(int steps=0;steps<=9;++steps){long long answer=0;for(int i=0;i<int(permutations.size());++i){int position=find(permutations[i].begin(),permutations[i].end(),0)-permutations[i].begin()+1;answer=(answer+distribution[i]*position)%P;}assert(random_swap_expected_position(n,steps)==answer);vector<long long>next(distribution.size());for(int i=0;i<int(permutations.size());++i)if(distribution[i])for(int a=0;a<n;++a)for(int b=0;b<n;++b){auto target=permutations[i];swap(target[a],target[b]);int j=number[target];next[j]=(next[j]+distribution[i]*inverse_pairs)%P;}distribution=next;}}
 using Matrix=array<array<long long,2>,2>;
 auto multiply=[](Matrix a,Matrix b){Matrix c{};for(int i=0;i<2;++i)for(int j=0;j<2;++j)for(int k=0;k<2;++k)c[i][j]=(c[i][j]+a[i][k]*b[k][j])%P;return c;};
 auto matrix_answer=[&](long long n,uint64_t steps){if(n==1)return 1LL;long long inverse_pairs=mod_power(n*n%P,P-2),leave=2*(n-1)%P*inverse_pairs%P,enter=2*inverse_pairs%P;Matrix transition={{{(1-leave+P)%P,enter},{leave,(1-enter+P)%P}}},product={{{1,0},{0,1}}};for(;steps;steps>>=1,transition=multiply(transition,transition))if(steps&1)product=multiply(product,transition);return (product[0][0]+product[1][0]*((n+2)%P)%P*((P+1)/2))%P;};
 for(long long n:{1LL,2LL,3LL,1000000LL,P-1})for(uint64_t steps:array<uint64_t,5>{0,1,2,1000000000000000000ULL,UINT64_MAX})assert(random_swap_expected_position(n,steps)==matrix_answer(n,steps));
 assert(random_swap_expected_position(P-1,0)==1);
 assert(random_swap_expected_position(P-1,UINT64_MAX)==mod_power(3,UINT64_MAX));
 bool rejected=false;try{random_swap_expected_position(P,10);}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'dice-product-prime-exponents':r'''
 auto direct=[](uint64_t target){map<uint64_t,long long>memo;long long inv_six=mod_power(6,P-2),self_factor=mod_power((1-inv_six+P)%P,P-2);function<long long(uint64_t)>probability=[&](uint64_t product)->long long{if(product==target)return 1;if(product>target||target%product)return 0;if(memo.contains(product))return memo[product];long long total=0;for(int face=2;face<=6;++face)if(product<=target/face)total=(total+inv_six*probability(product*face))%P;return memo[product]=total*self_factor%P;};return probability(1);};
 for(uint64_t target=1;target<=6000;++target)assert(dice_product_exact_probability(target)==direct(target));
 for(uint64_t target:{1000000000000000000ULL,979552051200000000ULL,576460752303423488ULL,450283905890997363ULL,298023223876953125ULL})assert(dice_product_exact_probability(target)==direct(target));
 assert(dice_product_exact_probability(6)==239578645);
 assert(dice_product_exact_probability(7)==0);
 assert(dice_product_exact_probability(300)==183676961);
 assert(dice_product_exact_probability(979552051200000000ULL)==812376310);
 assert(dice_product_exact_probability(1)==1);
 bool rejected=false;try{dice_product_exact_probability(0);}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'dag-edge-removal-expectation':r'''
 auto brute=[](int n,const vector<pair<int,int>>&edges){vector<vector<int>>out(n);for(int i=0;i<int(edges.size());++i)out[edges[i].first].push_back(i);auto solve=[&](int skip){vector<long double>memo(n,-1);function<long double(int)>expected=[&](int v)->long double{if(v==n-1)return 0;if(memo[v]>=0)return memo[v];long double sum=0;int degree=0;for(int edge:out[v])if(edge!=skip){++degree;sum+=expected(edges[edge].second);}assert(degree>0);return memo[v]=1+sum/degree;};return expected(0);};long double best=solve(-1);for(int i=0;i<int(edges.size());++i)if(out[edges[i].first].size()>1)best=min(best,solve(i));return best;};
 for(int trial=0;trial<3500;++trial){int n=1+rng()%11;vector<int>order(n);iota(order.begin(),order.end(),0);shuffle(order.begin(),order.end()-1,rng);vector<pair<int,int>>edges;for(int i=0;i<n-1;++i){edges.push_back({order[i],order[i+1+rng()%(n-i-1)]});for(int j=i+1;j<n;++j)if(rng()%4==0)edges.push_back({order[i],order[j]});}shuffle(edges.begin(),edges.end(),rng);assert(close_enough(minimum_dag_expectation_after_removal(n,edges),brute(n,edges),1e-11L));}
 assert(close_enough(minimum_dag_expectation_after_removal(4,{{0,1},{0,2},{1,2},{2,3}}),2.0L));
 assert(minimum_dag_expectation_after_removal(1,{})==0);
 vector<pair<int,int>>chain;for(int i=0;i<199999;++i)chain.push_back({i,i+1});assert(close_enough(minimum_dag_expectation_after_removal(200000,chain),199999.0L));
 vector<int>order={0};for(int i=199998;i>=1;--i)order.push_back(i);order.push_back(199999);chain.clear();for(int i=0;i<199999;++i)chain.push_back({order[i],order[i+1]});assert(close_enough(minimum_dag_expectation_after_removal(200000,chain),199999.0L));
 bool rejected=false;try{minimum_dag_expectation_after_removal(3,{{0,1},{1,0},{1,2}});}catch(const invalid_argument&){rejected=true;}assert(rejected);
 rejected=false;try{minimum_dag_expectation_after_removal(3,{{0,2}});}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'roulette-choice-zero-outcomes':r'''
 auto enumerate_policies=[](int target,const vector<RouletteChoice>&wheels)->optional<long double>{if(target==0)return 0;if(wheels.empty())return nullopt;int count=1;for(int r=1;r<=target;++r)count*=wheels.size();long double best=numeric_limits<long double>::infinity();for(int code=0;code<count;++code){int rest=code;vector<long double>expected(target+1);for(int r=1;r<=target;++r){int chosen=rest%wheels.size();rest/=wheels.size();auto wheel=wheels[chosen];int zero=0;long double total=wheel.cost;for(int score:wheel.outcomes){if(score==0)++zero;else total+=expected[max(0,r-score)]/wheel.outcomes.size();}expected[r]=zero==int(wheel.outcomes.size())?numeric_limits<long double>::infinity():total/(1.0L-static_cast<long double>(zero)/wheel.outcomes.size());}best=min(best,expected[target]);}if(!isfinite(best))return nullopt;return best;};
 for(int trial=0;trial<1800;++trial){int target=rng()%6,n=rng()%4;vector<RouletteChoice>wheels;for(int i=0;i<n;++i){RouletteChoice wheel{static_cast<long double>(1+rng()%10),{}};for(int j=0,k=1+rng()%5;j<k;++j)wheel.outcomes.push_back(rng()%6);wheels.push_back(wheel);}auto expected=enumerate_policies(target,wheels),got=minimum_roulette_cost(target,wheels);assert(got.has_value()==expected.has_value());if(got)assert(close_enough(*got,*expected,1e-11L));}
 assert(close_enough(*minimum_roulette_cost(3,{{1,{1}},{1.5L,{2}}}),2.5L));
 assert(close_enough(*minimum_roulette_cost(4,{{2,{0,0,3}}}),12.0L));
 assert(close_enough(*minimum_roulette_cost(1,{{7,{INT_MAX}}}),7.0L));
 assert(!minimum_roulette_cost(1,{{1,{0,0}},{2,{0}}}));
 assert(minimum_roulette_cost(0,{})==optional<long double>(0));
 vector<RouletteChoice>wheels(100,{1,vector<int>(100,0)});for(auto&wheel:wheels)wheel.outcomes.back()=1;assert(close_enough(*minimum_roulette_cost(100,wheels),10000.0L));
 bool rejected=false;try{minimum_roulette_cost(10,{{1,{0,-1}}});}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'random-subtree-removal-ancestor-priority':r'''
 auto markov=[](int n,const vector<pair<int,int>>&edges,int root){vector<vector<int>>g(n);for(auto[v,u]:edges){g[v].push_back(u);g[u].push_back(v);}vector<int>subtree(n);function<int(int,int)>build=[&](int v,int parent){int mask=1<<v;for(int u:g[v])if(u!=parent)mask|=build(u,v);return subtree[v]=mask;};build(root,-1);vector<long double>memo(1<<n,-1);memo[0]=0;function<long double(int)>expected=[&](int mask)->long double{if(memo[mask]>=0)return memo[mask];long double sum=0;for(int v=0;v<n;++v)if((mask>>v)&1)sum+=expected(mask&~subtree[v]);return memo[mask]=1+sum/popcount(static_cast<unsigned>(mask));};return expected((1<<n)-1);};
 for(int n=1;n<=6;++n){vector<pair<int,int>>edges;function<void(int)>generate=[&](int v){if(v==n){for(int root=0;root<n;++root)assert(close_enough(expected_subtree_removals(n,edges,root),markov(n,edges,root),1e-11L));return;}for(int parent=0;parent<v;++parent){edges.push_back({parent,v});generate(v+1);edges.pop_back();}};generate(1);}
 for(int trial=0;trial<2500;++trial){int n=1+rng()%10;vector<pair<int,int>>edges;for(int v=1;v<n;++v)edges.push_back({v,int(rng()%v)});int root=rng()%n;assert(close_enough(expected_subtree_removals(n,edges,root),markov(n,edges,root),1e-11L));}
 vector<pair<int,int>>chain,star;for(int v=1;v<200000;++v){chain.push_back({v-1,v});star.push_back({0,v});}
 long double harmonic=0;for(int v=1;v<=200000;++v)harmonic+=1.0L/v;
 assert(close_enough(expected_subtree_removals(200000,chain),harmonic,1e-11L));
 assert(close_enough(expected_subtree_removals(200000,star),1.0L+199999/2.0L,1e-11L));
 assert(close_enough(expected_subtree_removals(200000,star,199999),1.5L+199998/3.0L,1e-11L));
 bool rejected=false;try{expected_subtree_removals(3,{{0,1},{0,1}});}catch(const invalid_argument&){rejected=true;}assert(rejected);
'''
}
prelude=r'''
#include <bits/stdc++.h>
using namespace std;
constexpr long long P=998244353;
long long mod_power(long long value,uint64_t exponent){long long result=1;for(;exponent;exponent>>=1,value=value*value%P)if(exponent&1)result=result*value%P;return result;}
bool close_enough(long double a,long double b,long double tolerance=1e-12L){return isfinite(a)&&isfinite(b)&&fabsl(a-b)<=tolerance*max({1.0L,fabsl(a),fabsl(b)});}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-probability-patterns-') as tmp:
    for id,body in checks.items():
        article=(ROOT/'src/content/docs/techniques'/f'{id}.mdx').read_text()
        snippets=re.findall(r'```cpp\n(.*?)\n```',article,re.S)
        assert len(snippets)==1,(id,len(snippets))
        source=Path(tmp)/(id+'.cpp');binary=Path(tmp)/id
        source.write_text(prelude+snippets[0]+'\nint main(){mt19937 rng(870624813);\n'+body+'\n}\n')
        result=subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(id+'\n'+result.stderr)
        subprocess.run([str(binary)],check=True,timeout=50)
        print(id+' PASS',flush=True)
