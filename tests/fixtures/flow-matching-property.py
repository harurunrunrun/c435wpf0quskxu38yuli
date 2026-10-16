"""Compile actual article snippets and compare to exhaustive, independent models."""
from pathlib import Path
import concurrent.futures,json,os,re,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
COMMON='using namespace std;\nusing namespace tested;\nmt19937_64 rng(20261014);\n'
CASES={
'mandatory-matching-lower-bounds':r'''
bool brute(int l,int r,const vector<pair<int,int>>& e,const vector<bool>& nl,const vector<bool>& nr){
 vector<vector<int>> g(l);for(auto[a,b]:e)g[a].push_back(b);
 function<bool(int,unsigned)> dfs=[&](int a,unsigned used){if(a==l){for(int b=0;b<r;++b)if(nr[b]&&!(used>>b&1))return false;return true;}
 if(!nl[a]&&dfs(a+1,used))return true;
 for(int b:g[a])if(!(used>>b&1)&&dfs(a+1,used|(1u<<b)))return true;
 return false;};
 return dfs(0,0);
}
int main(){
 for(int l=0;l<=5;++l)for(int r=0;r<=5;++r)for(int trial=0;trial<90;++trial){
 vector<pair<int,int>> e;for(int a=0;a<l;++a)for(int b=0;b<r;++b)if(rng()%2)e.push_back({a,b});
 vector<bool> nl(l),nr(r);for(int a=0;a<l;++a)nl[a]=rng()%2;for(int b=0;b<r;++b)nr[b]=rng()%2;
 auto result=mandatory_matching(l,r,e,nl,nr);assert(bool(result)==brute(l,r,e,nl,nr));
 if(result){vector<int> sl(l),sr(r);for(auto[a,b]:*result){assert(find(e.begin(),e.end(),pair{a,b})!=e.end());assert(++sl[a]==1&&++sr[b]==1);}
 for(int a=0;a<l;++a)assert(!nl[a]||sl[a]);
 for(int b=0;b<r;++b)assert(!nr[b]||sr[b]);}}
 for(int trial=0;trial<1200;++trial){
 int n=1+rng()%4,m=rng()%6;vector<BoundedEdge> e;for(int k=0;k<m;++k){long long lo=rng()%3;e.push_back({int(rng()%n),int(rng()%n),lo,lo+int(rng()%3)});}
 vector<long long> balance(n);bool exists=false;
 function<void(int)> dfs=[&](int k){if(k==m){if(all_of(balance.begin(),balance.end(),[](long long x){return x==0;}))exists=true;return;}
 auto edge=e[k];for(long long f=edge.lower;f<=edge.upper;++f){balance[edge.from]-=f;balance[edge.to]+=f;dfs(k+1);balance[edge.from]+=f;balance[edge.to]-=f;}};
 dfs(0);auto result=feasible_circulation(n,e);assert(bool(result)==exists);
 if(result){fill(balance.begin(),balance.end(),0);for(int k=0;k<m;++k){assert(e[k].lower<=(*result)[k]&&(*result)[k]<=e[k].upper);balance[e[k].from]-=(*result)[k];balance[e[k].to]+=(*result)[k];}assert(all_of(balance.begin(),balance.end(),[](long long x){return x==0;}));}}
 assert(!feasible_circulation(2,{{0,1,1,1}}));
 assert(feasible_circulation(2,{{0,1,1000000000000LL,1000000000000LL},{1,0,1000000000000LL,1000000000000LL}}));
 assert(!feasible_circulation(1,{{0,0,2,1}}));
}
''',
'matrix-margin-lower-offset':r'''
bool brute(vector<long long> rows,vector<long long> cols,const vector<vector<long long>>& lo,const vector<vector<long long>>& hi){
 int r=rows.size(),c=cols.size();function<bool(int)> dfs=[&](int at){if(at==r*c)return all_of(rows.begin(),rows.end(),[](long long x){return x==0;})&&all_of(cols.begin(),cols.end(),[](long long x){return x==0;});
 int i=at/c,j=at%c;for(long long x=lo[i][j];x<=hi[i][j]&&x<=rows[i]&&x<=cols[j];++x){rows[i]-=x;cols[j]-=x;bool good=dfs(at+1);rows[i]+=x;cols[j]+=x;if(good)return true;}return false;};return dfs(0);
}
int main(){for(int trial=0;trial<1200;++trial){
 int r=1+rng()%3,c=1+rng()%3;vector<vector<long long>> lo(r,vector<long long>(c)),hi=lo;vector<long long> rows(r),cols(c);
 for(int i=0;i<r;++i)for(int j=0;j<c;++j){lo[i][j]=rng()%2;hi[i][j]=lo[i][j]+rng()%3;long long x=lo[i][j]+rng()%(hi[i][j]-lo[i][j]+1);rows[i]+=x;cols[j]+=x;}
 if(rng()%2){for(auto& x:rows)x=rng()%8;for(auto& x:cols)x=rng()%8;}
 auto result=bounded_matrix(rows,cols,lo,hi);assert(bool(result)==brute(rows,cols,lo,hi));
 if(result){vector<long long> gr(r),gc(c);for(int i=0;i<r;++i)for(int j=0;j<c;++j){auto x=(*result)[i][j];assert(lo[i][j]<=x&&x<=hi[i][j]);gr[i]+=x;gc[j]+=x;}assert(gr==rows&&gc==cols);}}
 assert(bounded_matrix(vector<long long>(20,400),vector<long long>(20,400),vector<vector<long long>>(20,vector<long long>(20,1)),vector<vector<long long>>(20,vector<long long>(20,20))));
 assert(!bounded_matrix({0},{0},{{1}},{{20}}));assert(!bounded_matrix({1},{2},{{0}},{{3}}));assert(!bounded_matrix({1},{1},{{2}},{{1}}));assert(!bounded_matrix({0},{0},{{-1}},{{1}}));
 auto big=bounded_matrix({2000000000000LL},{1000000000000LL,1000000000000LL},{{1000000000000LL,1000000000000LL}},{{1000000000000LL,1000000000000LL}});assert(big);
}
''',
'vertex-disjoint-through-pivot':r'''
bool brute(int n,const vector<pair<int,int>>& e,int a,int b,int c){
 vector<vector<int>> g(n);for(auto[u,v]:e){g[u].push_back(v);g[v].push_back(u);}
 function<bool(int,unsigned,bool)> dfs=[&](int v,unsigned mask,bool through){through|=v==b;if(v==c)return through;for(int u:g[v])if(!(mask>>u&1)&&dfs(u,mask|(1u<<u),through))return true;return false;};return dfs(a,1u<<a,false);
}
int main(){for(int n=3;n<=9;++n)for(int trial=0;trial<280;++trial){
 vector<pair<int,int>> e;for(int a=0;a<n;++a)for(int b=a+1;b<n;++b)if(rng()%4==0)e.push_back({a,b});
 vector<int> p(n);iota(p.begin(),p.end(),0);shuffle(p.begin(),p.end(),rng);assert(path_through_pivot(n,e,p[0],p[1],p[2])==brute(n,e,p[0],p[1],p[2]));}
 assert(!path_through_pivot(4,{{0,1},{1,2},{1,3}},0,2,3));
 int n=200000;vector<pair<int,int>> chain;for(int i=1;i<n;++i)chain.push_back({i-1,i});assert(path_through_pivot(n,chain,0,n/2,n-1));assert(!path_through_pivot(n,chain,0,n-1,1));
}
''',
'matching-profit-each-cardinality':r'''
vector<long long> brute(int l,int r,const vector<tuple<int,int,long long>>& e){
 vector<vector<pair<int,long long>>> g(l);for(auto[a,b,w]:e)g[a].push_back({b,w});vector<long long> answer(min(l,r)+1,LLONG_MIN);answer[0]=0;
 function<void(int,unsigned,int,long long)> dfs=[&](int a,unsigned mask,int k,long long value){if(a==l){answer[k]=max(answer[k],value);return;}dfs(a+1,mask,k,value);for(auto[b,w]:g[a])if(!(mask>>b&1))dfs(a+1,mask|(1u<<b),k+1,value+w);};
 dfs(0,0,0,0);while(answer.back()==LLONG_MIN)answer.pop_back();return answer;
}
int main(){for(int l=0;l<=6;++l)for(int r=0;r<=5;++r)for(int trial=0;trial<55;++trial){
 vector<tuple<int,int,long long>> e;for(int a=0;a<l;++a)for(int b=0;b<r;++b)if(rng()%2){e.push_back({a,b,int(rng()%31)-15});if(rng()%5==0)e.push_back({a,b,int(rng()%31)-15});}
 assert(matching_profit_by_size(l,r,e)==brute(l,r,e));}
 assert((matching_profit_by_size(2,2,{{0,0,100},{0,1,10},{1,0,1}})==vector<long long>{0,100,11}));
 assert((matching_profit_by_size(2,2,{{0,0,-100},{0,1,-1},{1,0,-1}})==vector<long long>{0,-1,-2}));
 assert((matching_profit_by_size(2,2,{{0,0,1000000000},{1,1,1000000000}})==vector<long long>{0,1000000000,2000000000}));
}
''',
'dag-path-cover-vertex-disjoint':r'''
int brute(int n,const vector<pair<int,int>>& e){
 vector<vector<int>> g(n);for(auto[a,b]:e)g[a].push_back(b);vector<bool> path(1<<n);path[0]=true;
 function<void(int,unsigned)> dfs=[&](int v,unsigned mask){path[mask]=true;for(int u:g[v])if(!(mask>>u&1))dfs(u,mask|(1u<<u));};
 for(int v=0;v<n;++v)dfs(v,1u<<v);
 vector<int> dp(1<<n,n+1);dp[0]=0;
 for(int mask=1;mask<(1<<n);++mask)for(int part=mask;part;part=(part-1)&mask)if(path[part])dp[mask]=min(dp[mask],dp[mask^part]+1);
 return dp.back();
}
int main(){for(int n=0;n<=8;++n)for(int trial=0;trial<85;++trial){
 vector<pair<int,int>> e;for(int a=0;a<n;++a)for(int b=a+1;b<n;++b)if(rng()%3==0)e.push_back({a,b});
 auto result=minimum_path_partition(n,e);assert(int(result.size())==brute(n,e));vector<int> seen(n);
 for(const auto& p:result){assert(!p.empty());for(int v:p)assert(++seen[v]==1);for(int k=1;k<int(p.size());++k)assert(find(e.begin(),e.end(),pair{p[k-1],p[k]})!=e.end());}assert(all_of(seen.begin(),seen.end(),[](int x){return x==1;}));}
 assert(minimum_path_partition(5,{{0,2},{1,2},{2,3},{2,4}}).size()==3);
 assert(minimum_path_partition(5,{{0,2},{1,2},{2,3},{2,4},{0,3},{0,4},{1,3},{1,4}}).size()==2);
 bool rejected=false;try{minimum_path_partition(2,{{0,1},{1,0}});}catch(const invalid_argument&){rejected=true;}assert(rejected);
 vector<tuple<int,int,long long>> roads{{0,1,10},{1,2,10}};assert(delivery_chains(3,roads,{{0,0},{1,10},{2,0}}).size()==2);assert(delivery_chains(3,roads,{{0,0},{1,10},{2,20},{0,40}}).size()==1);
 assert(delivery_chains(2,{},{{0,0},{1,20}}).size()==2);assert(delivery_chains(1,{},{{0,0},{0,100}}).size()==1);
}
''',
'rectangle-rook-flow':r'''
int brute(const vector<AllowedRectangle>& e){
 function<int(int,unsigned,unsigned)> dfs=[&](int i,unsigned rows,unsigned cols){if(i==int(e.size()))return 0;int best=dfs(i+1,rows,cols);
 for(int r=e[i].top;r<e[i].bottom;++r)if(!(rows>>r&1))for(int c=e[i].left;c<e[i].right;++c)if(!(cols>>c&1))best=max(best,1+dfs(i+1,rows|(1u<<r),cols|(1u<<c)));
 return best;};return dfs(0,0,0);
}
int main(){for(int trial=0;trial<850;++trial){
 int h=1+rng()%4,w=1+rng()%4,n=rng()%7;vector<AllowedRectangle> e;for(int i=0;i<n;++i){int a=rng()%h,c=rng()%h,b=rng()%w,d=rng()%w;if(a>c)swap(a,c);if(b>d)swap(b,d);e.push_back({a,c+1,b,d+1});}
 auto result=place_rectangle_rooks(h,w,e);assert(int(result.size())==brute(e));vector<bool> rows(h),cols(w),used(n);
 for(auto p:result){auto q=e[p.piece];assert(!used[p.piece]&&!rows[p.row]&&!cols[p.column]);used[p.piece]=rows[p.row]=cols[p.column]=true;assert(q.top<=p.row&&p.row<q.bottom&&q.left<=p.column&&p.column<q.right);}}
 assert(place_rectangle_rooks(2,3,{{0,2,0,2},{0,2,1,3},{0,1,0,3}}).size()==2);
 assert(place_rectangle_rooks(1,1,{{0,0,0,1}}).empty());assert(place_rectangle_rooks(1,1,{{0,1,0,0}}).empty());
}
''',
'translated-point-matching':r'''
bool permitted(Coordinate a,Coordinate b,long long t){long long x=b.first-a.first,y=b.second-a.second;return(x!=0||y!=0)&&(x==0||llabs(x)==t)&&(y==0||llabs(y)==t);}
bool brute(const vector<Coordinate>& a,const vector<Coordinate>& b,long long t){vector<int> p(a.size());iota(p.begin(),p.end(),0);do{bool good=true;for(int i=0;i<int(a.size());++i)good&=permitted(a[i],b[p[i]],t);if(good)return true;}while(next_permutation(p.begin(),p.end()));return false;}
int main(){
 const array<Coordinate,8> dir{{{1,0},{1,1},{0,1},{-1,1},{-1,0},{-1,-1},{0,-1},{1,-1}}};
 for(int trial=0;trial<1600;++trial){int n=rng()%8;long long t=1+rng()%3;vector<Coordinate>a,b;set<Coordinate>sa,sb;
 while(int(a.size())<n){Coordinate p{int(rng()%7)-3,int(rng()%7)-3};if(sa.insert(p).second)a.push_back(p);}
 while(int(b.size())<n){Coordinate p{int(rng()%7)-3,int(rng()%7)-3};if(sb.insert(p).second)b.push_back(p);}
 auto result=match_translated_points(a,b,t);assert(bool(result)==brute(a,b,t));
 if(result){vector<bool> seen(n);for(int i=0;i<n;++i){auto p=(*result)[i];assert(1<=p.direction&&p.direction<=8&&!seen[p.destination]);seen[p.destination]=true;auto[dx,dy]=dir[p.direction-1];assert((b[p.destination]==Coordinate{a[i].first+t*dx,a[i].second+t*dy}));}}}
 vector<Coordinate>a,b;for(int i=0;i<20000;++i){a.push_back({5LL*i,0});b.push_back({5LL*i+1,0});}
 auto result=match_translated_points(a,b,1);assert(result&&result->size()==20000);for(int i=0;i<20000;++i)assert((*result)[i].destination==i&&(*result)[i].direction==1);
 assert(match_translated_points({{-1000000000000LL,1000000000000LL}},{{0,0}},1000000000000LL));
}
''',
'perfect-matching-forced-scc':r'''
void check(int n,const vector<pair<int,int>>& e){
 vector<vector<bool>> edge(n,vector<bool>(n));for(auto[a,b]:e)edge[a][b]=true;vector<int> p(n);iota(p.begin(),p.end(),0);vector<vector<int>> all;
 do{bool good=true;for(int a=0;a<n;++a)good&=edge[a][p[a]];if(good)all.push_back(p);}while(next_permutation(p.begin(),p.end()));
 auto result=classify_perfect_edges(n,e);assert(bool(result)==!all.empty());if(!result)return;
 vector<bool> seen(n);for(int a=0;a<n;++a){int b=result->partner[a];assert(edge[a][b]&&!seen[b]);seen[b]=true;}
 for(int k=0;k<int(e.size());++k){auto[a,b]=e[k];bool any=false,every=true;for(const auto& m:all){any|=m[a]==b;every&=m[a]==b;}assert(result->allowed[k]==any&&result->forced[k]==every);}
}
int main(){for(int n=0;n<=3;++n)for(unsigned mask=0;mask<(1u<<(n*n));++mask){vector<pair<int,int>>e;for(int a=0;a<n;++a)for(int b=0;b<n;++b)if(mask>>(a*n+b)&1)e.push_back({a,b});check(n,e);}
 for(int n=4;n<=7;++n)for(int trial=0;trial<180;++trial){vector<pair<int,int>>e;for(int a=0;a<n;++a)for(int b=0;b<n;++b)if(rng()%3)e.push_back({a,b});check(n,e);}
 bool rejected=false;try{classify_perfect_edges(1,{{0,0},{0,0}});}catch(const invalid_argument&){rejected=true;}assert(rejected);
 int n=20000;vector<pair<int,int>>e;for(int i=0;i<n;++i){e.push_back({i,i});if(i+1<n)e.push_back({i,i+1});}auto result=classify_perfect_edges(n,e);assert(result);for(int k=0;k<int(e.size());++k)assert(result->forced[k]==(e[k].first==e[k].second));
}
''',
'maximum-profit-closure':r'''
int main(){for(int n=0;n<=11;++n)for(int trial=0;trial<90;++trial){
 vector<long long>w(n);for(auto& x:w)x=int(rng()%31)-15;vector<pair<int,int>>e;if(n)for(int k=0;k<25;++k)if(rng()%2)e.push_back({rng()%n,rng()%n});
 long long expected=0;for(unsigned mask=0;mask<(1u<<n);++mask){bool good=true;for(auto[u,v]:e)if((mask>>u&1)&&!(mask>>v&1))good=false;if(good){long long sum=0;for(int v=0;v<n;++v)if(mask>>v&1)sum+=w[v];expected=max(expected,sum);}}
 auto result=maximum_closed_profit(w,e);assert(result.profit==expected);vector<bool>seen(n);long long sum=0;for(int v:result.selected){assert(!seen[v]);seen[v]=true;sum+=w[v];}assert(sum==expected);for(auto[u,v]:e)assert(!seen[u]||seen[v]);}
 assert(maximum_closed_profit({-1000,100000},{{1,0}}).profit==99000);
 assert(maximum_closed_profit({-1000000000000LL,1000000000000LL},{{1,0}}).profit==0);
 assert(maximum_closed_profit({10,-9},{{0,1},{1,0}}).profit==1);assert(maximum_closed_profit({0,0},{{0,1}}).profit==0);
}
''',
'grid-corridor-cover-matching':r'''
unsigned coverage(const vector<string>&b,int r,int c,int dy,int dx){
 int h=b.size(),w=b[0].size();unsigned mask=0;while(0<=r&&r<h&&0<=c&&c<w&&b[r][c]=='.'){mask|=1u<<(r*w+c);r+=dy;c+=dx;}return mask;
}
int brute(const vector<string>&b){
 int h=b.size(),w=b[0].size();unsigned full=0;vector<unsigned>options;
 for(int r=0;r<h;++r)for(int c=0;c<w;++c)if(b[r][c]=='.'){full|=1u<<(r*w+c);for(auto[dy,dx]:vector<pair<int,int>>{{1,0},{-1,0},{0,1},{0,-1}})options.push_back(coverage(b,r,c,dy,dx));}
 vector<int>dp(1<<(h*w),h*w+1);dp[0]=0;for(unsigned mask=0;mask<=full;++mask)if((mask&~full)==0)for(unsigned extra:options)dp[mask|extra]=min(dp[mask|extra],dp[mask]+1);return dp[full];
}
int main(){
 for(int h=1;h<=3;++h)for(int w=1;w<=3;++w)for(unsigned mask=0;mask<(1u<<(h*w));++mask){
 vector<string>b(h,string(w,'#'));for(int r=0;r<h;++r)for(int c=0;c<w;++c)if(mask>>(r*w+c)&1)b[r][c]='.';
 auto result=cover_grid_corridors(b);assert(int(result.size())==brute(b));unsigned got=0;for(auto p:result){assert(0<=p.row&&p.row<h&&0<=p.column&&p.column<w&&b[p.row][p.column]=='.');got|=coverage(b,p.row,p.column,p.dy,p.dx);}assert(got==mask);}
 assert(cover_grid_corridors({"...",".#.","..."}).size()==4);assert(cover_grid_corridors({"...##",".#...","...#."}).size()==5);assert(cover_grid_corridors({}).empty());
 assert(cover_grid_corridors(vector<string>(300,string(300,'.'))).size()==300);
}
'''
}
def run(item):
    slug,body=item
    article=(ROOT/'src/content/docs/techniques'/f'{slug}.mdx').read_text()
    fence=chr(96)*3
    snippets=re.findall('^'+fence+r'cpp\n(.*?)^'+fence,article,re.M|re.S)
    if len(snippets)!=1:return slug,False,'Expected one published implementation'
    includes=[];code=[]
    for line in snippets[0].splitlines():
        (includes if line.startswith('#include ') else code).append(line)
    source='#include <bits/stdc++.h>\n'+'\n'.join(includes)+'\nnamespace tested {\n'+'\n'.join(code)+'\n}\n'+COMMON+body
    with tempfile.TemporaryDirectory(prefix='flow-matching-property-') as directory:
        cpp=Path(directory)/'test.cpp';exe=Path(directory)/'test';cpp.write_text(source)
        result=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],capture_output=True,text=True,timeout=60)
        if result.returncode:return slug,False,result.stderr
        result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=60)
        return slug,result.returncode==0,result.stderr
if __name__=='__main__':
    rows=json.loads((ROOT/'data/flow-matching-problem-features.json').read_text())
    assert {id for row in rows for id in row['techniqueIds']}==set(CASES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES.items()))
    for slug,passed,output in results:print(slug,'PASS' if passed else 'FAIL',output)
    if any(not passed for _,passed,_ in results):raise SystemExit(1)
    print('flow matching properties verified: 10 published implementations')
