"""Compare eight published DP reductions with independent finite exhaustive models."""
from pathlib import Path
import concurrent.futures
import json
import os
import re
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]
HELPERS=r'''
using namespace std;
long long model_power(long long x,long long e,long long mod){long long r=1;for(;e;e>>=1,x=x*x%mod)if(e&1)r=r*x%mod;return r;}
int main(){mt19937_64 rng(216232263);
'''
CASES={
'subset-sum-max-threshold':r'''
    for(int trial=0;trial<1200;++trial){int n=rng()%13;vector<int>a(n),b(n);for(int i=0;i<n;++i){a[i]=rng()%9;b[i]=rng()%13;}int expected=0;for(unsigned mask=1;mask<(1u<<n);++mask){int maximum=0,sum=0;for(int i=0;i<n;++i)if(mask>>i&1u){maximum=max(maximum,a[i]);sum+=b[i];}expected+=sum<=maximum;}assert(count_sum_bounded_by_selected_maximum(a,b)==expected);}
    assert(count_sum_bounded_by_selected_maximum({3,1},{1,2})==2);
    assert(count_sum_bounded_by_selected_maximum({1,1},{2,2})==0);
    assert(count_sum_bounded_by_selected_maximum(vector<int>(5000,0),vector<int>(5000,0))==(model_power(2,5000,998244353)+998244352)%998244353);
    assert(count_sum_bounded_by_selected_maximum({5000,5000},{1000000000,0})==1);
    bool rejected=false;try{count_sum_bounded_by_selected_maximum({5},{-1});}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'assignment-adjacent-swap-mask':r'''
    auto permutations=[](const vector<long long>&a,const vector<long long>&b,long long x,long long y){int n=a.size();vector<int>p(n);iota(p.begin(),p.end(),0);long long best=LLONG_MAX;do{long long cost=0;for(int i=0;i<n;++i){cost+=x*llabs(a[p[i]]-b[i]);for(int j=0;j<i;++j)if(p[j]>p[i])cost+=y;}best=min(best,cost);}while(next_permutation(p.begin(),p.end()));return best;};
    for(int trial=0;trial<250;++trial){int n=rng()%9;vector<long long>a(n),b(n);for(int i=0;i<n;++i){a[i]=int(rng()%9)-4;b[i]=int(rng()%9)-4;}long long x=rng()%7,y=rng()%13;assert(edit_and_adjacent_swap_cost(a,b,x,y)==permutations(a,b,x,y));}
    auto operations=[](vector<long long> a,vector<long long>b,int x,int y){int n=a.size(),states=1,goal=0,start=0;for(int i=0;i<n;++i){start+=int(a[i])*states;goal+=int(b[i])*states;states*=3;}vector<int>distance(states,INT_MAX);priority_queue<pair<int,int>,vector<pair<int,int>>,greater<pair<int,int>>>q;distance[start]=0;q.push({0,start});while(!q.empty()){auto[cost,state]=q.top();q.pop();if(cost!=distance[state])continue;if(state==goal)return cost;vector<int>v(n),powers(n,1);int rem=state;for(int i=0;i<n;++i){v[i]=rem%3;rem/=3;if(i)powers[i]=powers[i-1]*3;}auto relax=[&](int next,int extra){if(cost+extra<distance[next]){distance[next]=cost+extra;q.push({distance[next],next});}};for(int i=0;i<n;++i){if(v[i]<2)relax(state+powers[i],x);if(v[i]>0)relax(state-powers[i],x);if(i+1<n)relax(state+(v[i+1]-v[i])*powers[i]+(v[i]-v[i+1])*powers[i+1],y);}}return -1;};
    for(int trial=0;trial<180;++trial){int n=1+rng()%4,x=rng()%6,y=rng()%6;vector<long long>a(n),b(n);for(int i=0;i<n;++i){a[i]=rng()%3;b[i]=rng()%3;}assert(edit_and_adjacent_swap_cost(a,b,x,y)==operations(a,b,x,y));}
    assert(edit_and_adjacent_swap_cost({4,2,5,2},{6,4,2,1},3,5)==16);
    assert(edit_and_adjacent_swap_cost(vector<long long>(18,-100000000),vector<long long>(18,100000000),100000000,10000000000000000LL)==360000000000000000LL);
''',
 'two-column-rectangle-tiles':r'''
    auto brute=[](int height){int cells=2*height;unsigned full=(1u<<cells)-1;vector<long long>memo(1u<<cells,-1);function<long long(unsigned)>fill=[&](unsigned covered){if(covered==full)return 1LL;if(memo[covered]!=-1)return memo[covered];int first=0;while(covered>>first&1u)++first;int r=first/2,c=first%2;long long count=0;for(int end_row=r+1;end_row<=height;++end_row)for(int end_col=c+1;end_col<=2;++end_col){unsigned rectangle=0;for(int row=r;row<end_row;++row)for(int col=c;col<end_col;++col)rectangle|=1u<<(2*row+col);if(!(covered&rectangle))count+=fill(covered|rectangle);}return memo[covered]=count;};return fill(0);};
    auto answer=two_column_rectangle_tilings(1000000);assert(answer[0]==1);
    for(int n=1;n<=8;++n)assert(answer[n]==brute(n));
    assert(answer[2]==8 && answer[6]==2864 && answer[1337]==640403945);
    bool rejected=false;try{two_column_rectangle_tilings(-1);}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
 'tournament-opponent-maximum':r'''
    auto brute=[](const vector<vector<long long>>&reward){int people=reward.size();long long answer=LLONG_MIN;for(unsigned outcomes=0;outcomes<(1u<<(people-1));++outcomes){vector<int>current(people),wins(people);iota(current.begin(),current.end(),0);int bit=0;while(current.size()>1){vector<int>next;for(int i=0;i<int(current.size());i+=2){int winner=current[i+((outcomes>>bit)&1u)];++bit;++wins[winner];next.push_back(winner);}current=move(next);}long long score=0;for(int i=0;i<people;++i)if(wins[i])score+=reward[i][wins[i]-1];answer=max(answer,score);}return answer;};
    for(int trial=0;trial<750;++trial){int height=rng()%4,people=1<<height;vector<vector<long long>>reward(people,vector<long long>(height));for(auto&row:reward)for(auto&x:row)x=int(rng()%41)-20;assert(maximum_fixed_tournament_reward(reward)==brute(reward));}
    assert(maximum_fixed_tournament_reward({{2,5},{6,5},{2,1},{7,9}})==15);
    assert(maximum_fixed_tournament_reward(vector<vector<long long>>(8,vector<long long>(3,1)))==4);
    assert(maximum_fixed_tournament_reward(vector<vector<long long>>(65536,vector<long long>(16,-1000000000)))==-32768000000000LL);
    bool rejected=false;try{maximum_fixed_tournament_reward({{}, {}, {}});}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
 'connected-set-minimum-root':r'''
    auto brute=[](const vector<long long>&a,const vector<pair<int,int>>&edges,long long width){int n=a.size();vector<vector<int>>graph(n);for(auto[u,v]:edges){graph[u].push_back(v);graph[v].push_back(u);}int count=0;for(unsigned mask=1;mask<(1u<<n);++mask){long long lo=LLONG_MAX,hi=LLONG_MIN;int root=-1;for(int i=0;i<n;++i)if(mask>>i&1u){root=i;lo=min(lo,a[i]);hi=max(hi,a[i]);}if(hi-lo>width)continue;unsigned seen=1u<<root;vector<int>queue{root};for(size_t at=0;at<queue.size();++at)for(int u:graph[queue[at]])if((mask>>u&1u)&&!(seen>>u&1u)){seen|=1u<<u;queue.push_back(u);}count+=seen==mask;}return count;};
    for(int trial=0;trial<1200;++trial){int n=rng()%13;vector<long long>a(n);for(auto&v:a)v=int(rng()%7)-3;vector<pair<int,int>>edges;for(int v=1;v<n;++v)edges.push_back({v,int(rng()%v)});long long width=rng()%9;assert(count_connected_bounded_value_sets(a,edges,width)==brute(a,edges,width));}
    assert(count_connected_bounded_value_sets({2,1,3,2},{{0,1},{0,2},{2,3}},1)==8);
    vector<pair<int,int>>chain,star;for(int v=1;v<2000;++v){chain.push_back({v-1,v});star.push_back({0,v});}
    assert(count_connected_bounded_value_sets(vector<long long>(2000,7),chain,0)==2001000);
    assert(count_connected_bounded_value_sets(vector<long long>(2000,7),star,0)==(model_power(2,1999,1000000007)+1999)%1000000007);
    assert(count_connected_bounded_value_sets({-1000000000,1000000000},{{0,1}},2000000000LL)==3);
''',
 'grid-waypoint-subset':r'''
    auto brute=[](const vector<string>&a,long long budget){int h=a.size(),w=a[0].size(),cells=h*w,k=0,start=-1,goal=-1;vector<int>bit(cells,-1);for(int r=0;r<h;++r)for(int c=0;c<w;++c){char ch=a[r][c];if(ch=='S')start=r*w+c;if(ch=='G')goal=r*w+c;if(ch=='o')bit[r*w+c]=k++;}vector<int>distance((1u<<k)*cells,-1);queue<int>q;distance[start]=0;q.push(start);int best=-1;while(!q.empty()){int state=q.front();q.pop();int mask=state/cells,v=state%cells,r=v/w,c=v%w;if(v==goal && distance[state]<=budget)best=max(best,popcount(unsigned(mask)));for(auto[dr,dc]:vector<pair<int,int>>{{-1,0},{1,0},{0,-1},{0,1}}){int nr=r+dr,nc=c+dc;if(nr<0||nr>=h||nc<0||nc>=w||a[nr][nc]=='#')continue;int u=nr*w+nc,new_mask=mask;if(bit[u]!=-1)new_mask|=1u<<bit[u];int next=new_mask*cells+u;if(distance[next]==-1){distance[next]=distance[state]+1;q.push(next);}}}return best;};
    for(int trial=0;trial<400;++trial){int h=2+rng()%3,w=2+rng()%3,k=0;vector<string>a(h,string(w,'.'));for(int r=0;r<h;++r)for(int c=0;c<w;++c){int type=rng()%5;if(type==0)a[r][c]='#';if(type==1&&k<7){a[r][c]='o';++k;}}a[0][0]='S';a[h-1][w-1]='G';for(long long budget:{0LL,1LL,5LL,12LL,100LL})assert(maximum_grid_collectibles(a,budget)==brute(a,budget));}
    assert(maximum_grid_collectibles({"SooG"},3)==2);
    assert(maximum_grid_collectibles({"SGo"},3)==1 && maximum_grid_collectibles({"SGo"},1)==0);
    assert(maximum_grid_collectibles({"S.G","o#o",".#."},5)==1);
    assert(maximum_grid_collectibles({"S#G"},100)==-1);
    assert(maximum_grid_collectibles({"S.o..ooo..","..o..o.o..","..o..ooo..","..o..o.o..","..o..ooo.G"},2000000)==18);
''',
 'grid-earning-rate-dominance':r'''
    auto brute=[](const vector<vector<long long>>&income,const vector<vector<long long>>&right,const vector<vector<long long>>&down){int n=income.size();long long highest=0;for(auto&row:right)for(auto v:row)highest=max(highest,v);for(auto&row:down)for(auto v:row)highest=max(highest,v);int cap=2*(n-1)*int(highest),stride=cap+1;vector<int>distance(n*n*stride,-1);queue<int>q;distance[0]=0;q.push(0);while(!q.empty()){int state=q.front();q.pop();int cash=state%stride,place=state/stride,r=place/n,c=place%n;if(r==n-1 && c==n-1)return distance[state];auto visit=[&](int next_place,int next_cash){int next=next_place*stride+next_cash;if(distance[next]==-1){distance[next]=distance[state]+1;q.push(next);}};visit(place,min(cap,cash+int(income[r][c])));if(c+1<n && cash>=right[r][c])visit(place+1,cash-int(right[r][c]));if(r+1<n && cash>=down[r][c])visit(place+n,cash-int(down[r][c]));}return -1;};
    for(int trial=0;trial<1800;++trial){int n=1+rng()%4;vector<vector<long long>>income(n,vector<long long>(n)),right(n,vector<long long>(n-1)),down(n-1,vector<long long>(n));for(auto&row:income)for(auto&v:row)v=1+rng()%6;for(auto&row:right)for(auto&v:row)v=rng()%7;for(auto&row:down)for(auto&v:row)v=rng()%7;assert(minimum_earning_grid_actions(income,right,down)==brute(income,right,down));}
    assert(minimum_earning_grid_actions({{1,2,3},{3,1,2},{2,1,1}},{{1,2},{4,3},{4,2}},{{1,5,7},{5,3,3}})==8);
    assert(minimum_earning_grid_actions(vector<vector<long long>>(3,vector<long long>(3,1)),vector<vector<long long>>(3,vector<long long>(2,1000000000)),vector<vector<long long>>(2,vector<long long>(3,1000000000)))==4000000004LL);
    vector<vector<long long>>income(80,vector<long long>(80));for(int r=0;r<80;++r)for(int c=0;c<80;++c)income[r][c]=1+r*80+c;
    assert(minimum_earning_grid_actions(income,vector<vector<long long>>(80,vector<long long>(79,0)),vector<vector<long long>>(79,vector<long long>(80,0)))==158);
    assert(minimum_earning_grid_actions(vector<vector<long long>>(80,vector<long long>(80,1)),vector<vector<long long>>(80,vector<long long>(79,1000000000)),vector<vector<long long>>(79,vector<long long>(80,1000000000)))==158000000158LL);
''',
 'ratio-knapsack-weight-cap':r'''
    auto brute=[](int minimum,const vector<pair<int,int>>&items){optional<int>best;int n=items.size();for(unsigned mask=1;mask<(1u<<n);++mask){long long weight=0,talent=0;for(int i=0;i<n;++i)if(mask>>i&1u){weight+=items[i].first;talent+=items[i].second;}if(weight>=minimum){int value=int(1000*talent/weight);if(!best || value>*best)best=value;}}return best;};
    for(int trial=0;trial<550;++trial){int n=rng()%15,minimum=1+rng()%160;vector<pair<int,int>>items;for(int i=0;i<n;++i)items.push_back({1+int(rng()%31),int(rng()%31)});assert(maximum_scaled_talent_ratio(minimum,items)==brute(minimum,items));}
    assert(maximum_scaled_talent_ratio(15,{{20,21},{10,11},{30,31}})==1066);
    assert(maximum_scaled_talent_ratio(1,{{1000000,1000}})==1);
    assert(maximum_scaled_talent_ratio(1000,vector<pair<int,int>>(250,{4,1000}))==250000);
    assert(maximum_scaled_talent_ratio(1000,vector<pair<int,int>>(250,{1000000,0}))==0);
    assert(!maximum_scaled_talent_ratio(1000,vector<pair<int,int>>(250,{1,1000})));
    assert(!maximum_scaled_talent_ratio(1,{}));
'''
}

def run(item):
    slug,body=item
    article=(ROOT/'src/content/docs/techniques'/f'{slug}.mdx').read_text()
    snippets=re.findall(r'```cpp\n(.*?)```',article,re.S)
    if len(snippets)!=1:return slug,False,'Expected one published C++ implementation'
    source='#include <bits/stdc++.h>\n'+snippets[0]+'\n'+HELPERS+body+'\n}\n'
    with tempfile.TemporaryDirectory(prefix='dp-structure-coverage-') as directory:
        cpp=Path(directory)/'test.cpp';exe=Path(directory)/'test';cpp.write_text(source)
        compiled=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],capture_output=True,text=True,timeout=70)
        if compiled.returncode:return slug,False,compiled.stderr
        executed=subprocess.run([str(exe)],capture_output=True,text=True,timeout=60)
        return slug,executed.returncode==0,executed.stderr

if __name__=='__main__':
    rows=json.loads((ROOT/'data/dp-structure-problem-features.json').read_text())
    assert {id for row in rows for id in row['techniqueIds']}==set(CASES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES.items()))
    for slug,passed,output in results:print(slug,'PASS' if passed else 'FAIL',output)
    if any(not passed for _,passed,_ in results):raise SystemExit(1)
