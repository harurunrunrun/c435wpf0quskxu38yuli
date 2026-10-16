from pathlib import Path
import re,subprocess,tempfile,concurrent.futures,os
root=Path(__file__).resolve().parents[2]
COMMON=r'''
int main() {
    mt19937 rng(1729);
'''
TESTS={
'dp-range-sum':r'''
    for(int trial=0;trial<250;++trial) {
        int n=rng()%7,M=rng()%5; vector<int> lo(n),hi(n);
        for(int i=0;i<n;++i) {lo[i]=rng()%(M+1);hi[i]=lo[i]+rng()%(M-lo[i]+1);}
        auto brute=[&](auto&& self,int i,int last)->int {
            if(i==n) return 1;
            int ans=0;for(int x=max(last,lo[i]);x<=hi[i];++x) ans+=self(self,i+1,x);
            return ans;
        };
        assert(nondecreasing_count(lo,hi,M)==brute(brute,0,0));
    }
''',
'dp-prefix-min':r'''
    for(int trial=0;trial<250;++trial) {
        int n=rng()%10; vector<int> keys(n); vector<long long> start(n),enter(n),leave(n),brute(n);
        for(int i=0;i<n;++i) { keys[i]=rng()%4;start[i]=int(rng()%11)-5;enter[i]=int(rng()%11)-5;leave[i]=int(rng()%11)-5;
            brute[i]=start[i];for(int j=0;j<i;++j) if(keys[j]<keys[i]) brute[i]=min(brute[i],enter[i]+brute[j]+leave[j]);}
        assert(ordered_chain_cost(keys,start,enter,leave)==brute);
    }
''',
'dp-sliding-min':r'''
    for(int trial=0;trial<250;++trial) {
        int n=1+rng()%9,T=1+rng()%7,R=rng()%12;
        vector<vector<long long>> c(T,vector<long long>(n)); vector<long long> dp(n),next(n);
        for(auto& row:c) for(auto& x:row)x=int(rng()%11)-5;
        for(auto row:c) {for(int x=0;x<n;++x) {next[x]=LLONG_MAX;for(int y=0;y<n;++y)if(abs(y-x)<=R)next[x]=min(next[x],dp[y]+row[x]);} dp=next;}
        assert(movement_cost(c,R)==*min_element(dp.begin(),dp.end()));
    }
    assert(movement_cost({},0)==0);
''',
'bounded-knapsack-deque':r'''
    for(int trial=0;trial<300;++trial) {
        int n=rng()%6,W=rng()%15;vector<BoundedItem> a(n);
        for(auto& x:a)x={1+int(rng()%8),int(rng()%5),int(rng()%9)};
        auto brute=[&](auto&& self,int i,int weight)->long long {
            if(i==n)return 0;
            long long ans=0;
            for(int k=0;k<=a[i].count && weight+k*a[i].weight<=W;++k)
                ans=max(ans,k*a[i].value+self(self,i+1,weight+k*a[i].weight));
            return ans;
        };
        assert(bounded_knapsack(a,W)==brute(brute,0,0));
    }
''',
'knapsack-value-axis':r'''
    for(int trial=0;trial<300;++trial) {
        int n=rng()%9,W=rng()%20; vector<long long>w(n);vector<int>v(n);
        for(int i=0;i<n;++i){w[i]=rng()%11;v[i]=rng()%9;}
        int best=0;
        for(int mask=0;mask<(1<<n);++mask){long long weight=0;int value=0;for(int i=0;i<n;++i)if(mask>>i&1){weight+=w[i];value+=v[i];}if(weight<=W)best=max(best,value);}
        assert(value_axis_knapsack(w,v,W)==best);
    }
''',
'dp-dimension-rolling':r'''
    for(int trial=0;trial<200;++trial) {
        string a,b;int n=rng()%8,m=rng()%8;
        for(int i=0;i<n;++i)a+=char('a'+rng()%3);
        for(int i=0;i<m;++i)b+=char('a'+rng()%3);
        set<string> subs;
        for(int mask=0;mask<(1<<m);++mask){string s;for(int i=0;i<m;++i)if(mask>>i&1)s+=b[i];subs.insert(s);}
        int best=0;for(int mask=0;mask<(1<<n);++mask){string s;for(int i=0;i<n;++i)if(mask>>i&1)s+=a[i];if(subs.count(s))best=max(best,int(s.size()));}
        assert(lcs_length(a,b)==best);
    }
''',
'dp-state-dominance':r'''
    for(int trial=0;trial<300;++trial) {
        int n=rng()%10;vector<long long>a(n);for(auto& x:a)x=int(rng()%9)-4;
        int best=0;
        for(int mask=0;mask<(1<<n);++mask){long long last=LLONG_MIN;int length=0;bool valid=true;for(int i=0;i<n;++i)if(mask>>i&1){if(a[i]<=last)valid=false;last=a[i];++length;}if(valid)best=max(best,length);}
        assert(strict_lis_length(a)==best);
    }
''',
'dp-last-occurrence':r'''
    assert(distinct_subsequence_count("aybabtu",1000000007)==103);
    assert(distinct_subsequence_count("aaa",2)==1);
    assert(distinct_subsequence_count("",1)==0);
    for(int trial=0;trial<300;++trial) {
        int n=rng()%11;string s;for(int i=0;i<n;++i)s+=char('a'+rng()%3);
        set<string> subs;for(int mask=1;mask<(1<<n);++mask){string t;for(int i=0;i<n;++i)if(mask>>i&1)t+=s[i];subs.insert(t);}
        assert(distinct_subsequence_count(s)==int(subs.size()));
    }
''',
'dp-polynomial-convolution':r'''
    for(int trial=0;trial<200;++trial) {
        int n=rng()%10;vector<int>a(n);for(auto& x:a)x=rng()%5;
        vector<int> count(n+1);
        for(int mask=0;mask<(1<<n);++mask){long long prod=1;for(int i=0;i<n;++i)if(mask>>i&1)prod=prod*a[i]%ntt998::MOD;count[__builtin_popcount(unsigned(mask))]=(count[__builtin_popcount(unsigned(mask))]+prod)%ntt998::MOD;}
        assert(weighted_subset_counts(a)==count);
    }
''',
'dp-affine-transition':r'''
    for(int trial=0;trial<300;++trial) {
        int n=1+rng()%10;vector<long long>a(n),b(n);a[0]=int(rng()%7)-3;b[0]=10;
        for(int i=1;i<n;++i){a[i]=a[i-1]+rng()%4;b[i]=b[i-1]-1-rng()%4;}
        vector<i128> dp(n);
        for(int i=1;i<n;++i){dp[i]=i128(1)<<100;for(int j=0;j<i;++j)dp[i]=min(dp[i],dp[j]+i128(b[j])*a[i]);}
        assert(affine_transition_dp(a,b)==dp);
    }
''',
'dp-quadratic-transition':r'''
    for(int trial=0;trial<300;++trial) {
        int n=1+rng()%10;vector<long long>h(n);for(int i=1;i<n;++i)h[i]=h[i-1]+1+rng()%6;
        long long C=rng()%20;vector<i128> dp(n);
        for(int i=1;i<n;++i){dp[i]=i128(1)<<100;for(int j=0;j<i;++j)dp[i]=min(dp[i],dp[j]+i128(h[i]-h[j])*(h[i]-h[j])+C);}
        assert(squared_jump_cost(h,C)==dp.back());
    }
''',
'dp-monotone-split':r'''
    for(int trial=0;trial<300;++trial) {
        int n=1+rng()%9,K=1+rng()%n;vector<long long>a(n);for(auto& x:a)x=rng()%6;
        long long best=LLONG_MAX;
        for(int mask=0;mask<(1<<(n-1));++mask)if(__builtin_popcount(unsigned(mask))==K-1){long long cost=0,sum=0;for(int i=0;i<n;++i){sum+=a[i];if(i==n-1 || (mask>>i&1)){cost+=sum*sum;sum=0;}}best=min(best,cost);}
        assert(squared_partition_cost(a,K)==best);
    }
''',
'dp-exact-count-penalty':r'''
    for(int trial=0;trial<500;++trial) {
        int n=1+rng()%12;vector<long long>a(n);for(auto& x:a)x=int(rng()%31)-15;
        for(int K=0;K<=(n+1)/2;++K){long long best=LLONG_MAX;for(unsigned mask=0;mask<(1u<<n);++mask)if(__builtin_popcount(mask)==K && !(mask&(mask<<1))){long long cost=0;for(int i=0;i<n;++i)if(mask>>i&1)cost+=a[i];best=min(best,cost);}assert(nonadjacent_exact_cost(a,K)==best);}
    }
''',
'dp-piecewise-linear-cost':r'''
    for(int trial=0;trial<300;++trial) {
        int n=rng()%10;vector<long long>a(n);for(auto& x:a)x=int(rng()%9)-4;
        vector<long long> dp(9),next(9);
        for(long long x:a){long long best=LLONG_MAX;for(int y=0;y<9;++y){best=min(best,dp[y]);next[y]=best+abs(x-(y-4));}dp=next;}
        assert(isotonic_abs_cost(a)==*min_element(dp.begin(),dp.end()));
    }
''',
'dp-batch-equal-keys':r'''
    for(int trial=0;trial<250;++trial) {
        int H=1+rng()%4,W=1+rng()%4;vector<GridCell> cells;
        for(int r=0;r<H;++r)for(int c=0;c<W;++c)if(rng()%2)cells.push_back({r,c,int(rng()%5)});
        int n=cells.size();vector<int> dp(n,-1);
        auto f=[&](auto&& self,int i)->int{if(dp[i]>=0)return dp[i];dp[i]=0;for(int j=0;j<n;++j)if(cells[j].value>cells[i].value && (cells[j].row==cells[i].row || cells[j].col==cells[i].col))dp[i]=max(dp[i],1+self(self,j));return dp[i];};
        for(int i=0;i<n;++i)f(f,i);
        assert(grid_increasing_moves(H,W,cells)==dp);
    }
''',
 'tree-knapsack-cardinality':r'''
    for(int trial=0;trial<250;++trial){int n=1+rng()%10;vector<vector<int>>g(n);for(int i=1;i<n;++i){int p=rng()%i;g[i].push_back(p);g[p].push_back(i);}int root=rng()%n;vector<long long> count(n+1);
        for(int mask=1;mask<(1<<n);++mask)if(mask>>root&1){vector<int> q{root};int seen=1<<root;for(int p=0;p<int(q.size());++p)for(int u:g[q[p]])if((mask>>u&1) && !(seen>>u&1)){seen|=1<<u;q.push_back(u);}if(seen==mask)++count[__builtin_popcount(unsigned(mask))];}
        assert(root_connected_counts(g,root)==count);
    }
''',
'digit-dp-leading-zero':r'''
    assert(count_no_equal_neighbors(-1)==0);
    for(int trial=0;trial<100;++trial){int B=rng()%10000;long long count=0;for(int x=0;x<=B;++x){auto s=to_string(x);bool valid=true;for(int i=1;i<int(s.size());++i)if(s[i]==s[i-1])valid=false;count+=valid;}assert(count_no_equal_neighbors(B)==count);}
''',
'bitmask-dp-submask':r'''
    for(int trial=0;trial<180;++trial){int n=rng()%9;vector<unsigned>adj(n);for(int i=0;i<n;++i)for(int j=0;j<i;++j)if(rng()%2){adj[i]|=1u<<j;adj[j]|=1u<<i;}int best=n;vector<unsigned> groups;
        auto dfs=[&](auto&& self,int v)->void{if(v==n){best=min(best,int(groups.size()));return;}if(int(groups.size())>=best)return;for(int p=0;p<int(groups.size());++p)if((groups[p]&~adj[v])==0){groups[p]|=1u<<v;self(self,v+1);groups[p]^=1u<<v;}groups.push_back(1u<<v);self(self,v+1);groups.pop_back();};
        dfs(dfs,0);assert(minimum_clique_partition(adj)==best);
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

