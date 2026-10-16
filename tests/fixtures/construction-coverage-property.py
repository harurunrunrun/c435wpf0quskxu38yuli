"""Check published implementations against independent small models."""
from pathlib import Path
import concurrent.futures
import json
import os
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
COMMON=r'''
int main(){
    using namespace tested;
    mt19937_64 rng(382626);
    constexpr long long prime=998244353;
    auto power=[](long long a,long long e){long long r=1;for(;e;e>>=1,a=a*a%prime)if(e&1)r=r*a%prime;return r;};
    auto close=[](long double a,long double b){assert(fabsl(a-b)<=1e-10L*max(1.0L,fabsl(b)));};
    (void)power;(void)close;
'''
CASES={
'coupon-collector-state-count':r'''
    for(int n=1;n<=10;++n){int full=(1<<n)-1;vector<long double> expected(1<<n);
        for(int mask=full-1;mask>=0;--mask){long double sum=n;int other=0;
            for(int j=0;j<n;++j)if(!(mask>>j&1)){sum+=expected[mask|(1<<j)];++other;}
            expected[mask]=sum/other;
        }
        for(int mask=0;mask<=full;++mask)close(expected_collection_steps(n,__builtin_popcount((unsigned)mask)),expected[mask]);
    }
    close(expected_collection_steps(2),2);close(expected_collection_steps(3),4.5L);
    assert(expected_collection_steps(100000)>1000000);
''',
'independent-avoidance-product':r'''
    for(auto [h,w]:vector<pair<int,int>>{{1,1},{1,2},{1,3},{2,2},{2,3}})for(int steps=0;steps<=3;++steps){
        int n=h*w;if(n>4 && steps>1)continue;vector<vector<int>> g(n);
        for(int y=0;y<h;++y)for(int x=0;x<w;++x)for(auto [dy,dx]:vector<pair<int,int>>{{1,0},{-1,0},{0,1},{0,-1}}){int u=y+dy,v=x+dx;if(u>=0 && u<h && v>=0 && v<w)g[y*w+x].push_back(u*w+v);}
        for(int v=0;v<n;++v)if(g[v].empty())g[v].push_back(v);
        vector<vector<pair<int,long double>>> outcomes(n);
        auto paths=[&](auto&& self,int start,int v,int left,long double p)->void{
            if(left==0){outcomes[start].push_back({v,p});return;}
            for(int u:g[v])self(self,start,u,left-1,p/g[v].size());};
        for(int s=0;s<n;++s)paths(paths,s,s,steps,1);
        long double expected=0;vector<int> occupied(n);
        auto combinations=[&](auto&& self,int s,long double p)->void{
            if(s==n){expected+=p*count(occupied.begin(),occupied.end(),0);return;}
            for(auto [v,q]:outcomes[s]){++occupied[v];self(self,s+1,p*q);--occupied[v];}};
        combinations(combinations,0,1);close(expected_empty_cells(h,w,steps),expected);
    }
    assert(fabsl(expected_empty_cells(8,8,10)-23.120740L)<0.5e-6L);
''',
'random-gain-zero-elimination':r'''
    for(int trial=0;trial<500;++trial){int n=rng()%7,target=rng()%10;vector<int> p(n);for(int& x:p)x=vector<int>{0,1,25,50,99,100}[rng()%6];
        if(target==0){close(expected_trials_for_gain(p,target),0);continue;}
        vector<long double> distribution(n+1);
        for(unsigned mask=0;mask<(1u<<n);++mask){long double probability=1;for(int i=0;i<n;++i)probability*=((mask>>i&1) ? p[i] : 100-p[i])/100.0L;distribution[__builtin_popcount(mask)]+=probability;}
        if(all_of(p.begin(),p.end(),[](int x){return x==0;})){assert(isinf(expected_trials_for_gain(p,target)));continue;}
        vector<vector<long double>> matrix(target,vector<long double>(target+1));
        for(int r=1;r<=target;++r){matrix[r-1][r-1]=1;matrix[r-1][target]=1;
            for(int g=0;g<=n;++g)if(r-g>0)matrix[r-1][r-g-1]-=distribution[g];}
        for(int col=0;col<target;++col){int pivot=col;for(int row=col+1;row<target;++row)if(fabsl(matrix[row][col])>fabsl(matrix[pivot][col]))pivot=row;
            swap(matrix[col],matrix[pivot]);long double divisor=matrix[col][col];assert(divisor!=0);for(int j=col;j<=target;++j)matrix[col][j]/=divisor;
            for(int row=0;row<target;++row)if(row!=col){long double factor=matrix[row][col];for(int j=col;j<=target;++j)matrix[row][j]-=factor*matrix[col][j];}}
        close(expected_trials_for_gain(p,target),matrix[target-1][target]);
    }
    close(expected_trials_for_gain({50,100},2),1.5L);close(expected_trials_for_gain({1},10),1000);
''',
'probability-start-time-window':r'''
    for(int trial=0;trial<500;++trial){int n=1+rng()%3,x=rng()%8;vector<int> length(n);for(int& d:length)d=1+rng()%5;
        long long inv=power(n,prime-2);
        for(int chosen=0;chosen<n;++chosen){long long expected=0;
            auto sequences=[&](auto&& self,int start,long long probability)->void{
                for(int j=0;j<n;++j){long long q=probability*inv%prime;
                    if(start+length[j]>x){if(j==chosen)expected=(expected+q)%prime;}
                    else self(self,start+length[j],q);}};
            sequences(sequences,0,1);assert(playlist_occupancy(length,x,chosen)==expected);
        }
    }
    assert(playlist_occupancy({3,5,6},6)==369720131);
    assert(playlist_occupancy({1},100)==1);
''',
'expectation-order-statistic-tail':r'''
    for(int trial=0;trial<650;++trial){int n=1+rng()%7,m=1+rng()%5,k=1+rng()%n;vector<int> a(n);int unknown=0;
        for(int& x:a){x=rng()%(m+1);unknown+=x==0;}
        if(unknown>6)continue;
        long long sum=0,count_cases=0;vector<int> values=a;
        auto enumerate=[&](auto&& self,int i)->void{
            if(i==n){auto sorted=values;sort(sorted.begin(),sorted.end());sum+=sorted[k-1];++count_cases;return;}
            if(a[i])self(self,i+1);else for(int x=1;x<=m;++x){values[i]=x;self(self,i+1);}};
        enumerate(enumerate,0);assert(expected_kth_uniform(a,m,k)==sum%prime*power(count_cases,prime-2)%prime);
    }
    assert(expected_kth_uniform({2,0,4},5,2)==3);
    assert(expected_kth_uniform({0,0},3,1)==221832080);
    assert(expected_kth_uniform({1,1,1},1,2)==1);
''',
'tree-dp-degree-capacity':r'''
    for(int trial=0;trial<900;++trial){int n=1+rng()%12;vector<tuple<int,int,long long>> edges;vector<int> degree(n),cap(n);
        for(int v=1;v<n;++v){int u=rng()%v;edges.push_back({v,u,int(rng()%31)-15});++degree[v];++degree[u];}
        for(int v=0;v<n;++v)cap[v]=rng()%(degree[v]+1);
        __int128 expected=0;
        for(unsigned mask=0;mask<(1u<<edges.size());++mask){vector<int> used(n);__int128 sum=0;bool valid=true;
            for(int i=0;i<(int)edges.size();++i)if(mask>>i&1){auto [v,u,w]=edges[i];++used[v];++used[u];sum+=w;}
            for(int v=0;v<n;++v)if(used[v]>cap[v])valid=false;
            if(valid)expected=max(expected,sum);}
        assert(maximum_tree_edges(cap,edges)==expected);
    }
    int n=100000;vector<int> cap(n,2);vector<tuple<int,int,long long>> chain;for(int v=1;v<n;++v)chain.push_back({v-1,v,LLONG_MAX});
    assert(maximum_tree_edges(cap,chain)==(__int128)(n-1)*LLONG_MAX);
''',
'dp-open-groups-gap-cost':r'''
    for(int trial=0;trial<650;++trial){int n=rng()%9,limit=rng()%20;vector<long long> a(n);for(auto& x:a)x=int(rng()%15)-7;
        vector<vector<long long>> groups;long long expected=0;
        auto partitions=[&](auto&& self,int i)->void{
            if(i==n){long long cost=0;for(auto& g:groups)cost+=*max_element(g.begin(),g.end())-*min_element(g.begin(),g.end());expected+=cost<=limit;return;}
            int size=groups.size();for(int j=0;j<size;++j){groups[j].push_back(a[i]);self(self,i+1);groups[j].pop_back();}
            groups.push_back({a[i]});self(self,i+1);groups.pop_back();};
        partitions(partitions,0);assert(count_range_cost_partitions(a,limit)==expected);
    }
    assert(count_range_cost_partitions({2,4,5},2)==3);
    assert(count_range_cost_partitions({7,8,9,10},3)==13);
    assert(count_range_cost_partitions({LLONG_MIN,LLONG_MAX},100)==1);
''',
'permutation-cycle-minimum-swaps':r'''
    for(int n=0;n<=6;++n){vector<int> target(n);iota(target.begin(),target.end(),0);map<vector<int>,int> distance;queue<vector<int>> q;distance[target]=0;q.push(target);
        while(!q.empty()){auto p=q.front();q.pop();int d=distance[p];for(int i=0;i<n;++i)for(int j=i+1;j<n;++j){swap(p[i],p[j]);if(!distance.contains(p)){distance[p]=d+1;q.push(p);}swap(p[i],p[j]);}}
        for(const auto& [state,d]:distance){auto p=state;auto operations=sort_permutation_swaps(p);assert((int)operations.size()==d);for(auto [v,u]:operations)swap(p[v],p[u]);assert(p==target);}
    }
    vector<int> long_cycle(100000);iota(long_cycle.begin(),long_cycle.end(),0);rotate(long_cycle.begin(),long_cycle.begin()+1,long_cycle.end());assert(sort_permutation_swaps(long_cycle).size()==99999);
''',
'permutation-tree-leaf-fix':r'''
    for(int trial=0;trial<200;++trial){int n=1+rng()%7;vector<pair<int,int>> edges;
        for(int i=0;i<n;++i)for(int j=i+1;j<n;++j)if(rng()%4==0)edges.push_back({i,j});
        vector<int> target(n);iota(target.begin(),target.end(),0);set<vector<int>> reachable{target};queue<vector<int>> q;q.push(target);
        while(!q.empty()){auto state=q.front();q.pop();for(auto [v,u]:edges){swap(state[v],state[u]);if(reachable.insert(state).second)q.push(state);swap(state[v],state[u]);}}
        for(int repeat=0;repeat<15;++repeat){auto p=target;shuffle(p.begin(),p.end(),rng);auto operations=sort_permutation_on_edges(p,edges);assert(operations.has_value()==reachable.contains(p));
            if(operations){assert(operations->size()<=size_t(n*(n-1)/2));for(int id:*operations){assert(0<=id && id<(int)edges.size());auto [v,u]=edges[id];swap(p[v],p[u]);}assert(p==target);}}
    }
    int n=1000;vector<int> p(n);iota(p.begin(),p.end(),0);reverse(p.begin(),p.end());vector<pair<int,int>> edges;for(int v=1;v<n;++v)edges.push_back({v-1,v});auto result=sort_permutation_on_edges(p,edges);assert(result && result->size()<=499500);
''',
'construct-star-distance-two':r'''
    auto distance_two=[](int n,const vector<pair<int,int>>& edges){vector<vector<int>> d(n,vector<int>(n,n+1));for(int v=0;v<n;++v)d[v][v]=0;set<pair<int,int>> seen;
        for(auto [v,u]:edges){assert(0<=v && v<n && 0<=u && u<n && v!=u);assert(seen.insert(minmax(v,u)).second);d[v][u]=d[u][v]=1;}
        for(int k=0;k<n;++k)for(int v=0;v<n;++v)for(int u=0;u<n;++u)d[v][u]=min(d[v][u],d[v][k]+d[k][u]);
        long long count=0;for(int v=0;v<n;++v)for(int u=v+1;u<n;++u){if(d[v][u]>n)return -1LL;count+=d[v][u]==2;}return count;};
    for(int n=1;n<=6;++n){vector<pair<int,int>> pairs;for(int v=0;v<n;++v)for(int u=v+1;u<n;++u)pairs.push_back({v,u});set<long long> attainable;
        for(unsigned mask=0;mask<(1u<<pairs.size());++mask){vector<pair<int,int>> edges;for(int i=0;i<(int)pairs.size();++i)if(mask>>i&1)edges.push_back(pairs[i]);long long count=distance_two(n,edges);if(count>=0)attainable.insert(count);}
        for(int k=-1;k<=n*(n-1)/2+1;++k){auto result=graph_with_distance_two_pairs(n,k);assert(result.has_value()==attainable.contains(k));if(result)assert(distance_two(n,*result)==k);}
    }
    for(int n=7;n<=35;++n)for(int k:{0,1,(n-1)*(n-2)/4,(n-1)*(n-2)/2}){auto result=graph_with_distance_two_pairs(n,k);assert(result && distance_two(n,*result)==k);}
''',
'forest-trigger-minimum-continuation':r'''
    for(int trial=0;trial<650;++trial){int n=1+rng()%9;vector<int> parent(n),children(n);vector<long long> fun(n);for(int v=0;v<n;++v){parent[v]=int(rng()%(v+1))-1;fun[v]=rng()%50;if(parent[v]>=0)++children[parent[v]];}
        // 頂点番号と親子順を無関係にし、親番号の大小へ依存しないか調べる。
        vector<int> label(n);iota(label.begin(),label.end(),0);shuffle(label.begin(),label.end(),rng);
        vector<int> renamed_parent(n),renamed_children(n);vector<long long> renamed_fun(n);
        for(int v=0;v<n;++v){renamed_parent[label[v]]=parent[v]<0 ? -1 : label[parent[v]];renamed_children[label[v]]=children[v];renamed_fun[label[v]]=fun[v];}
        parent=move(renamed_parent);children=move(renamed_children);fun=move(renamed_fun);
        vector<int> initiators;for(int v=0;v<n;++v)if(children[v]==0)initiators.push_back(v);__int128 expected=0;
        do{vector<bool> active(n);__int128 total=0;for(int v:initiators){long long best=0;while(v!=-1 && !active[v]){active[v]=true;best=max(best,fun[v]);v=parent[v];}total+=best;}expected=max(expected,total);}while(next_permutation(initiators.begin(),initiators.end()));
        assert(maximum_forest_chain_fun(fun,parent)==expected);
    }
    assert(maximum_forest_chain_fun({60,20,40,50},{-1,0,0,1})==110);
    int n=200000;vector<int> parent(n);iota(parent.begin(),parent.end(),-1);vector<long long> fun(n,LLONG_MAX);assert(maximum_forest_chain_fun(fun,parent)==LLONG_MAX);
    fill(parent.begin(),parent.end(),-1);assert(maximum_forest_chain_fun(fun,parent)==(__int128)n*LLONG_MAX);
''',
'append-digits-lexicographic':r'''
    auto smaller=[](const string& a,const string& b){return a.size()!=b.size() ? a.size()<b.size() : a<b;};
    for(int trial=0;trial<650;++trial){int n=1+rng()%5;vector<string> a(n);for(auto& x:a)x=to_string(1+rng()%100);
        auto [cost,result]=append_to_increasing(a);long long expected_cost=0;string previous;
        for(int i=0;i<n;++i){string best;int count=0;bool found=false;
            for(int append=0;append<=5 && !found;++append){long long limit=1;for(int j=0;j<append;++j)limit*=10;
                for(long long suffix=0;suffix<limit;++suffix){string tail=append ? to_string(suffix) : string();if(append)tail=string(append-tail.size(),'0')+tail;string candidate=a[i]+tail;
                    if(smaller(previous,candidate)){best=candidate;count=append;found=true;break;}}}
            assert(found && result[i]==best);expected_cost+=count;previous=best;
        }
        assert(cost==expected_cost);
    }
    // 小さい列は全候補を同時に探索して、前からの選択自体も検証する。
    for(int a=1;a<=4;++a)for(int b=1;b<=4;++b)for(int c=1;c<=4;++c){vector<string> input{to_string(a),to_string(b),to_string(c)};long long best=100;
        auto enumerate=[&](auto&& self,int i,string previous,int cost)->void{if(cost>=best)return;if(i==3){best=cost;return;}for(int appended=0;appended<=2;++appended){int count=appended==0 ? 1 : appended==1 ? 10 : 100;for(int suffix=0;suffix<count;++suffix){string tail=appended ? to_string(suffix) : string();if(appended)tail=string(appended-tail.size(),'0')+tail;string x=input[i]+tail;if(smaller(previous,x))self(self,i+1,x,cost+appended);}}};
        enumerate(enumerate,0,"",0);assert(append_to_increasing(input).first==best);}
    assert(append_to_increasing({"100","7","10"}).first==4);
    for(const auto& [input,expected]:vector<pair<vector<string>,vector<string>>>{
        {{"1299","12"},{"1299","12000"}},{{"1298","12"},{"1298","1299"}},
        {{"1200","12"},{"1200","1201"}},{{"1299","13"},{"1299","1300"}},
        {{"1399","12"},{"1399","12000"}},{{"99","99"},{"99","990"}},
        {{"99","1"},{"99","100"}},{{"100","10"},{"100","101"}}})assert(append_to_increasing(input).second==expected);
    auto empty=append_to_increasing({});assert(empty.first==0 && empty.second.empty());
    auto boundary=append_to_increasing({"1299","12","12","13","1"});for(size_t i=1;i<boundary.second.size();++i)assert(smaller(boundary.second[i-1],boundary.second[i]));
    vector<string> repeated(1000);for(int i=0;i<1000;++i)repeated[i]=i%2 ? "8" : "9";
    auto large=append_to_increasing(repeated);assert(large.second.back().size()>18);
''',
'alternating-linear-weight-prefix':r'''
    for(int trial=0;trial<500;++trial){int n=rng()%55;vector<long long> a(n);for(auto& x:a)x=int(rng()%101)-50;AlternatingWeightedSum data(a);
        for(int operation=0;operation<180;++operation){if(n && rng()%3==0){int p=rng()%n;long long value=int(rng()%201)-100;data.set(p,value);a[p]=value;}
            else {int l=rng()%(n+1),r=rng()%(n+1);if(l>r)swap(l,r);__int128 expected=0;for(int i=l;i<r;++i)expected+=(__int128)((i-l)%2 ? -1 : 1)*(i-l+1)*a[i];assert(data.query(l,r)==expected);}}
    }
    AlternatingWeightedSum extremes({LLONG_MIN,LLONG_MAX});assert(extremes.query(0,2)==(__int128)LLONG_MIN-2*(__int128)LLONG_MAX);extremes.set(0,LLONG_MAX);assert(extremes.query(0,2)==-(__int128)LLONG_MAX);
'''
}

def run(item):
    slug,body=item
    article=(ROOT/'src/content/docs/techniques'/f'{slug}.mdx').read_text()
    snippets=re.findall(r'```cpp\n(.*?)```',article,re.S)
    if len(snippets)!=1:return slug,False,'Expected one published implementation'
    includes=[];code=[]
    for line in snippets[0].splitlines():(includes if line.startswith('#include ') else code).append(line)
    source='\n'.join(includes)+'\nusing namespace std;\nnamespace tested{\n'+'\n'.join(code)+'\n}\n'+COMMON+body+'\n}\n'
    with tempfile.TemporaryDirectory(prefix='construction-coverage-') as directory:
        cpp=Path(directory)/'test.cpp'; executable=Path(directory)/'test';cpp.write_text(source)
        compiled=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(executable)],capture_output=True,text=True,timeout=60)
        if compiled.returncode:return slug,False,compiled.stderr
        executed=subprocess.run([str(executable)],capture_output=True,text=True,timeout=60)
        return slug,executed.returncode==0,executed.stderr

if __name__=='__main__':
    metadata=json.loads((ROOT/'data/construction-problem-features.json').read_text())
    assert {x['techniqueId'] for x in metadata}==set(CASES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES.items()))
    for slug,passed,output in results:print(slug,'PASS' if passed else 'FAIL',output)
    if any(not passed for _,passed,_ in results):raise SystemExit(1)
