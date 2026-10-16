from pathlib import Path
import re,subprocess,tempfile,concurrent.futures,os
root=Path(__file__).resolve().parents[2]
COMMON=r'''
int main() {
    mt19937 rng(1729);
'''
TESTS={
'quotient-blocks':r'''
    assert(floor_sum_by_blocks(0)==0);
    for(int n=1;n<=2000;++n) {
        __int128 expected=0;for(int i=1;i<=n;++i) expected+=n/i;
        assert(floor_sum_by_blocks(n)==expected);
    }
''',
'divisor-multiple-reversal':r'''
    for(int trial=0;trial<250;++trial) {
        int k=rng()%40;vector<long long> a(k+1);
        for(int i=1;i<=k;++i)a[i]=int(rng()%31)-15;
        vector<long long> div(k+1),mul(k+1);
        for(int x=1;x<=k;++x)for(int d=1;d<=k;++d)if(x%d==0){div[x]+=a[d];mul[d]+=a[x];}
        assert(divisor_sums(a)==div);assert(multiple_sums(a)==mul);
    }
''',
'gcd-divisibility-count':r'''
    for(int n=1;n<=5;++n)for(int k=1;k<=6;++k) {
        vector<long long> counts(k+1);
        auto enumerate=[&](auto&& self,int length,int g)->void {
            if(length==n){++counts[g];return;}
            for(int x=1;x<=k;++x)self(self,length+1,gcd(g,x));
        };
        enumerate(enumerate,0,0);
        for(long long mod:{2LL,7LL,97LL,1000000007LL}) {
            auto got=exact_gcd_counts(n,k,mod);
            for(int d=1;d<=k;++d)assert(got[d]==counts[d]%mod);
        }
    }
''',
'factorial-inverses':r'''
    for(long long prime:{2LL,3LL,7LL,97LL,1000000007LL}) {
        int limit=min<long long>(24,prime-1);BinomialTable table(limit,prime);
        vector<vector<long long>> pascal(limit+1,vector<long long>(limit+1));
        pascal[0][0]=1;
        for(int n=1;n<=limit;++n)for(int k=0;k<=n;++k)
            pascal[n][k]=(k?pascal[n-1][k-1]:0)+(k<n?pascal[n-1][k]:0);
        for(int n=0;n<=limit;++n)for(int k=-1;k<=n+1;++k)
            assert(table.choose(n,k)==(k<0||k>n?0:pascal[n][k]%prime));
        assert(table.choose(-1,0)==0);
    }
''',
'stars-and-bars':r'''
    for(int n=1;n<=6;++n)for(int k=0;k<=6;++k) {
        auto count=[&](auto&& self,int left,int smallest)->long long {
            if(left==0)return 1;
            long long answer=0;
            for(int x=smallest;x<n;++x)answer+=self(self,left-1,x);
            return answer;
        };
        long long expected=count(count,k,0);
        for(long long prime:{13LL,97LL,1000000007LL})
            if(n+k-1<prime)assert(nondecreasing_count(n,k,prime)==expected%prime);
    }
''',
'inclusion-exclusion-forbidden':r'''
    for(int alphabet=0;alphabet<=4;++alphabet)
      for(int required=0;required<=alphabet;++required)
       for(int n=0;n<=6;++n) {
        long long expected=0;
        auto enumerate=[&](auto&& self,int length,unsigned used)->void {
            if(length==n){expected+=((used&((1u<<required)-1))==((1u<<required)-1));return;}
            for(int x=0;x<alphabet;++x)self(self,length+1,used|(1u<<x));
        };
        enumerate(enumerate,0,0);
        for(long long mod:{7LL,97LL,1000000007LL})
            assert(include_all_symbols(alphabet,required,n,mod)==expected%mod);
    }
''',
'expectation-indicators':r'''
    for(int trial=0;trial<160;++trial) {
        int n=rng()%7;vector<long long> bounds(n),draw(n);long long total=0,count=0;
        for(auto& x:bounds)x=1+rng()%4;
        auto enumerate=[&](auto&& self,int i)->void {
            if(i==n){++count;for(int j=0;j<n;++j)for(int k=j+1;k<n;++k)total+=draw[j]>draw[k];return;}
            for(int value=1;value<=bounds[i];++value){draw[i]=value;self(self,i+1);}
        };
        enumerate(enumerate,0);
        assert(fabsl(expected_inversions(bounds)-static_cast<long double>(total)/count)<1e-12L);
    }
''',
'expectation-first-step':r'''
    for(int trial=0;trial<180;++trial) {
        int n=1+rng()%9;vector<long double> cost(n);
        vector<vector<pair<int,long double>>> edges(n);
        for(int s=1;s<n;++s) {
            cost[s]=rng()%6;int numerator=rng()%4;
            edges[s].push_back({s-1,numerator/3.0L});
            edges[s].push_back({int(rng()%s),(3-numerator)/3.0L});
        }
        auto got=decreasing_expectations(cost,edges);
        for(int start=0;start<n;++start) {
            long double expected=0;
            auto paths=[&](auto&& self,int s,long double probability,long double paid)->void {
                if(s==0){expected+=probability*paid;return;}
                for(auto [t,p]:edges[s])self(self,t,probability*p,paid+cost[s]);
            };
            paths(paths,start,1,0);
            assert(fabsl(got[start]-expected)<1e-11L);
        }
    }
''',
'expectation-self-loop':r'''
    constexpr long long MOD=998244353;
    auto mod_power=[&](long long x,long long e){long long out=1;for(;e;e>>=1,x=x*x%MOD)if(e&1)out=out*x%MOD;return out;};
    for(int trial=0;trial<250;++trial) {
        int n=1+rng()%11;vector<int> dice(n-1);
        vector<vector<long long>> matrix(n,vector<long long>(n+1));
        for(int i=0;i<n-1;++i) {
            dice[i]=1+rng()%(n-1-i);
            long long probability=mod_power(dice[i]+1,MOD-2);
            matrix[i][i]=1;matrix[i][n]=1;
            for(int step=0;step<=dice[i];++step)
                matrix[i][i+step]=(matrix[i][i+step]-probability+MOD)%MOD;
        }
        matrix[n-1][n-1]=1;
        for(int col=0;col<n;++col) {
            int pivot=col;while(pivot<n && matrix[pivot][col]==0)++pivot;
            assert(pivot<n);swap(matrix[col],matrix[pivot]);
            long long inv=mod_power(matrix[col][col],MOD-2);
            for(int j=col;j<=n;++j)matrix[col][j]=matrix[col][j]*inv%MOD;
            for(int row=0;row<n;++row)if(row!=col) {
                long long factor=matrix[row][col];
                for(int j=col;j<=n;++j)
                    matrix[row][j]=(matrix[row][j]-factor*matrix[col][j]%MOD+MOD)%MOD;
            }
        }
        auto got=forward_dice_expectations(dice);
        for(int i=0;i<n;++i)assert(got[i]==matrix[i][n]);
    }
''',
'bitwise-contribution':r'''
    for(int trial=0;trial<250;++trial) {
        int n=rng()%12;vector<unsigned long long> a(n);
        for(auto& x:a)x=(static_cast<unsigned long long>(rng())<<32)^rng();
        if(n>0)a[0]=0;
        if(n>1)a[1]=1ULL<<63;
        if(n>2)a[2]=ULLONG_MAX;
        for(long long mod:{2LL,97LL,1000000007LL}) {
            long long expected=0;
            for(int i=0;i<n;++i)for(int j=i+1;j<n;++j)
                expected=(expected+(__int128)((a[i]^a[j])%mod))%mod;
            assert(sum_pair_xor(a,mod)==expected);
        }
    }
''',
'xor-prefix-count':r'''
    for(int trial=0;trial<350;++trial) {
        int n=rng()%13;vector<unsigned long long> a(n);for(auto& x:a)x=rng()%8;
        if(trial%7==0)fill(a.begin(),a.end(),0);
        unsigned long long target=rng()%8;long long expected=0;
        for(int l=0;l<n;++l){unsigned long long value=0;for(int r=l;r<n;++r){value^=a[r];expected+=value==target;}}
        assert(count_subarray_xor(a,target)==expected);
    }
    vector<unsigned long long> large{0,1ULL<<63,ULLONG_MAX,1ULL<<63};
    assert(count_subarray_xor(large,1ULL<<63)==3);
''',
'meet-in-middle-four-sums':r'''
    for(int trial=0;trial<350;++trial) {
        int n=rng()%11;vector<long long>a(n);for(auto& x:a)x=int(rng()%17)-8;
        long long target=int(rng()%31)-15;bool possible=false;
        for(int i=0;i<n;++i)for(int j=i+1;j<n;++j)for(int k=j+1;k<n;++k)for(int l=k+1;l<n;++l)
            possible|=(a[i]+a[j]+a[k]+a[l]==target);
        auto answer=four_distinct_sum(a,target);assert(answer.has_value()==possible);
        if(answer){auto ids=*answer;sort(ids.begin(),ids.end());assert(adjacent_find(ids.begin(),ids.end())==ids.end());long long sum=0;for(int id:ids){assert(0<=id && id<n);sum+=a[id];}assert(sum==target);}
    }
    assert(!four_distinct_sum({2,2,2},8));
    assert(four_distinct_sum({0,0,0,0},0));
''',
'sweep-interval-endpoints':r'''
    for(int trial=0;trial<300;++trial) {
        int n=rng()%12;vector<tuple<long long,long long,long long>> intervals;
        for(int i=0;i<n;++i){int s=int(rng()%11)-5,t=int(rng()%11)-5;if(s>t)swap(s,t);intervals.push_back({s,t,rng()%8});}
        long long expected=0;
        for(int time=-6;time<=6;++time){long long load=0;for(auto [s,t,w]:intervals)if(s<=time && time<t)load+=w;expected=max(expected,load);}
        assert(peak_interval_load(intervals)==expected);
    }
    assert(peak_interval_load({{0,1,10},{1,2,20},{1,1,1000}})==20);
''',
 'turn-penalty-state':r'''
    for(int trial=0;trial<180;++trial) {
        int H=1+rng()%4,W=1+rng()%4;vector<string> grid(H,string(W,'.'));
        for(auto& row:grid)for(char& c:row)if(rng()%3==0)c='#';
        int sy=rng()%H,sx=rng()%W,ty=rng()%H,tx=rng()%W;
        grid[sy][sx]=grid[ty][tx]='.';
        int dy[]={-1,0,1,0},dx[]={0,1,0,-1},V=H*W*4,INF=1000000000;
        vector<int> d(V,INF);for(int dir=0;dir<4;++dir)d[(sy*W+sx)*4+dir]=0;
        for(int round=0;round<V;++round){bool changed=false;
            for(int y=0;y<H;++y)for(int x=0;x<W;++x)if(grid[y][x]!='#')for(int dir=0;dir<4;++dir){int v=(y*W+x)*4+dir;if(d[v]==INF)continue;
                for(int nd=0;nd<4;++nd){int ny=y+dy[nd],nx=x+dx[nd];if(ny<0||ny>=H||nx<0||nx>=W||grid[ny][nx]=='#')continue;int u=(ny*W+nx)*4+nd,newcost=d[v]+(dir!=nd);if(newcost<d[u]){d[u]=newcost;changed=true;}}}
            if(!changed)break;
        }
        int expected=INF;for(int dir=0;dir<4;++dir)expected=min(expected,d[(ty*W+tx)*4+dir]);if(expected==INF)expected=-1;
        assert(min_turns(grid,sy,sx,ty,tx)==expected);
    }
    assert(min_turns({".#."},0,0,0,2)==-1);
    assert(min_turns({"."},0,0,0,0)==0);
''',
'multi-source-distance':r'''
    for(int trial=0;trial<300;++trial) {
        int n=rng()%11,INF=1000000000;vector<vector<int>>g(n),d(n,vector<int>(n,INF));
        for(int i=0;i<n;++i){d[i][i]=0;for(int j=0;j<n;++j)if(i!=j && rng()%4==0){g[i].push_back(j);d[i][j]=1;}}
        vector<int> sources;for(int i=0;i<n;++i)if(rng()%3==0){sources.push_back(i);if(rng()%2)sources.push_back(i);}
        for(int k=0;k<n;++k)for(int i=0;i<n;++i)for(int j=0;j<n;++j)d[i][j]=min(d[i][j],d[i][k]+d[k][j]);
        vector<int> expected(n,-1);
        for(int v=0;v<n;++v){int best=INF;for(int s:sources)best=min(best,d[s][v]);if(best<INF)expected[v]=best;}
        assert(nearest_source_distance(g,sources)==expected);
    }
''',
'exchange-crossproduct':r'''
    auto check_order=[&](const vector<pair<long long,long long>>& items) {
        vector<int> perm(items.size());iota(perm.begin(),perm.end(),0);__int128 expected=0;
        do{__int128 score=0,prefix=0;for(int i:perm){score+=prefix*items[i].second;prefix+=items[i].first;}expected=max(expected,score);}while(next_permutation(perm.begin(),perm.end()));
        auto [order,score]=best_cross_order(items);assert(score==expected);
        auto sorted=order;sort(sorted.begin(),sorted.end());for(int i=0;i<int(sorted.size());++i)assert(sorted[i]==i);
        __int128 actual=0,prefix=0;for(int i:order){actual+=prefix*items[i].second;prefix+=items[i].first;}assert(actual==score);
    };
    check_order({{0,0},{1,0},{0,1},{0,0},{2,2},{4,4},{0,5}});
    check_order({{0,0},{0,0},{0,0}});
    for(int trial=0;trial<200;++trial){int n=rng()%8;vector<pair<long long,long long>>items(n);for(auto& [x,y]:items){x=rng()%5;y=rng()%5;}check_order(items);}
''',
'construct-last-operation':r'''
    vector<set<vector<int>>> reachable(8);
    reachable[0].insert(vector<int>{});
    for(int n=1;n<=7;++n)for(const auto& before:reachable[n-1])for(int pos=0;pos<n;++pos){vector<int> after(n);for(int i=0;i<n;++i)after[i]=i<pos?before[i]:i==pos?pos+1:before[i-1];reachable[n].insert(move(after));}
    auto check=[&](const vector<int>& target){auto plan=insertion_plan(target);assert(plan.has_value()==bool(reachable[target.size()].count(target)));if(plan){vector<int> built;for(int position:*plan){assert(1<=position && position<=int(built.size())+1);built.insert(built.begin()+position-1,position);}assert(built==target);}};
    for(int n=0;n<=7;++n)for(const auto& target:reachable[n])check(target);
    for(int trial=0;trial<500;++trial){int n=rng()%8;vector<int>target(n);for(int& x:target)x=1+rng()%(n+2);check(target);}
''',
'prefix-feasibility':r'''
    for(int trial=0;trial<160;++trial) {
        int n=rng()%20;string s(n,'(');for(char& c:s)if(rng()%2)c=')';BracketTree tree(s);
        for(int step=0;step<12;++step){
            if(n){int pos=rng()%n;s[pos]=s[pos]=='('?')':'(';tree.set(pos,s[pos]);}
            for(int l=0;l<=n;++l)for(int r=l;r<=n;++r){int sum=0,minimum=0;for(int i=l;i<r;++i){sum+=s[i]=='('?1:-1;minimum=min(minimum,sum);}auto node=tree.query(l,r);assert(node.sum==sum && node.minimum==minimum);assert(tree.valid(l,r)==(sum==0 && minimum>=0));}
        }
    }
    BracketTree adversary(")()(");assert(!adversary.valid(0,4));assert(adversary.valid(1,3));
'''
,'score-difference-game':r'''
    for(int trial=0;trial<150;++trial) {
        int n=rng()%15;vector<int> allowed{1};
        for(int a=2;a<=7;++a)if(rng()%3==0)allowed.push_back(a);
        auto tree=[&](auto&& self,int remaining,bool first_turn)->int {
            if(remaining==0)return 0;
            int best=first_turn?INT_MIN:INT_MAX;
            for(int take:allowed)if(take<=remaining) {
                int score=self(self,remaining-take,!first_turn)+(first_turn?take:0);
                best=first_turn?max(best,score):min(best,score);
            }
            return best;
        };
        auto differences=stone_score_difference(n,allowed);
        for(int stones=0;stones<=n;++stones) {
            int first=tree(tree,stones,true);
            assert(differences[stones]==2*first-stones);
            assert((stones+differences[stones])%2==0);
            assert((stones+differences[stones])/2==first);
        }
    }
'''

}

def run(pair):
 slug,main=pair
 content=(root/'src/content/docs/techniques'/f'{slug}.mdx').read_text()
 code=re.search(r'```cpp\n(.*?)```',content,re.S).group(1)
 with tempfile.TemporaryDirectory(prefix='specific-property-') as d:
  cpp=Path(d)/'test.cpp';cpp.write_text(code+'\n'+COMMON+main+'\n}\n')
  exe=Path(d)/'test'
  compile=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],capture_output=True,text=True,timeout=60)
  if compile.returncode:return slug,False,compile.stderr
  result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30)
  return slug,result.returncode==0,result.stderr
if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
  results=list(pool.map(run,TESTS.items()))
 for slug,ok,message in results:print(slug,'PASS' if ok else 'FAIL',message)
 if any(not ok for _,ok,_ in results):raise SystemExit(1)

