#!/usr/bin/env python3
from pathlib import Path
import re, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
checks={
'knuth-adjacent-merges':r'''
    auto brute=[](const vector<long long>& a) {
        int n=int(a.size());if(!n)return __int128(0);
        vector<__int128> p(n+1);for(int i=0;i<n;++i)p[i+1]=p[i]+a[i];
        vector<vector<__int128>> d(n+1,vector<__int128>(n+1));
        for(int z=2;z<=n;++z)for(int l=0;l+z<=n;++l){int r=l+z;d[l][r]=__int128(1)<<120;for(int k=l+1;k<r;++k)d[l][r]=min(d[l][r],d[l][k]+d[k][r]+p[r]-p[l]);}
        return d[0][n];
    };
    assert(minimum_adjacent_merge({})==0);assert(minimum_adjacent_merge({7})==0);
    assert(minimum_adjacent_merge({10,20,30,40})==190);
    for(int z=0;z<1000;++z){vector<long long>a(rng()%18);for(auto&x:a)x=(z%10==0?1000000000000LL:rng()%8);assert(minimum_adjacent_merge(a)==brute(a));}
    bool rejected=false;try{minimum_adjacent_merge({2,-1});}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'subset-bin-lexicographic':r'''
    auto brute=[](const vector<long long>& w,long long cap){
        if(w.empty()) return 0;
        int answer=int(w.size());vector<long long>loads;
        auto dfs=[&](auto&&self,int i)->void{if(i==int(w.size())){answer=min(answer,int(loads.size()));return;}if(int(loads.size())>answer)return;for(int j=0;j<int(loads.size());++j)if(w[i]<=cap-loads[j]){loads[j]+=w[i];self(self,i+1);loads[j]-=w[i];}loads.push_back(w[i]);self(self,i+1);loads.pop_back();};dfs(dfs,0);return answer;
    };
    assert(minimum_bins({},10)==make_pair(0,0LL));assert(minimum_bins({4,8,6,1},10).first==2);
    assert(minimum_bins({0,0,0},1).first==1);
    for(int z=0;z<400;++z){long long cap=1+rng()%12;vector<long long>w(rng()%9);for(auto&x:w)x=rng()%(cap+1);auto [b,l]=minimum_bins(w,cap);assert(b==brute(w,cap));assert(l>=0&&l<=cap);}
    assert(minimum_bins({LLONG_MAX,LLONG_MAX},LLONG_MAX).first==2);
''',
'domino-column-transition':r'''
    auto brute=[](int h,int w){
        unsigned long long full=(1ULL<<(h*w))-1;
        auto dfs=[&](auto&&self,unsigned long long used)->long long{if(used==full)return 1;int p=0;while(used>>p&1)++p;long long ans=0;int r=p/w,c=p%w;if(c+1<w&&!(used>>(p+1)&1))ans+=self(self,used|(1ULL<<p)|(1ULL<<(p+1)));if(r+1<h&&!(used>>(p+w)&1))ans+=self(self,used|(1ULL<<p)|(1ULL<<(p+w)));return ans;};return dfs(dfs,0);
    };
    assert(count_domino_tilings(0,5)==1);assert(count_domino_tilings(4,7)==781);
    for(int h=1;h<=4;++h)for(int w=1;w<=5;++w){assert(count_domino_tilings(h,w)==brute(h,w));assert(count_domino_tilings(w,h)==brute(h,w));}
    assert(count_domino_tilings(1,1000)==1);assert(count_domino_tilings(1,999)==0);
''',
'interval-pair-removal-interleavings':r'''
    auto brute=[](const vector<vector<bool>>& allowed){
        int n=int(allowed.size());vector<long long>memo(1<<n,-1);
        auto dfs=[&](auto&&self,int mask)->long long{if(!mask)return 1;auto&ans=memo[mask];if(ans!=-1)return ans;ans=0;int last=-1;for(int i=0;i<n;++i)if(mask>>i&1){if(last!=-1&&allowed[last][i])ans+=self(self,mask^(1<<last)^(1<<i));last=i;}return ans;};return dfs(dfs,(1<<n)-1);
    };
    assert(count_pair_removal_orders({})==1);
    for(int z=0;z<500;++z){int n=2*(rng()%6);vector<vector<bool>>a(n,vector<bool>(n));for(int i=0;i<n;++i)for(int j=i+1;j<n;++j)a[i][j]=a[j][i]=rng()%2;assert(count_pair_removal_orders(a)==brute(a));}
    vector<vector<bool>>all(8,vector<bool>(8,true));assert(count_pair_removal_orders(all)==105);
    vector<vector<bool>>cross(4,vector<bool>(4));cross[0][2]=cross[2][0]=true;cross[1][3]=cross[3][1]=true;assert(count_pair_removal_orders(cross)==0);
''',
'grid-xor-antidiagonal':r'''
    auto brute=[](const vector<vector<unsigned long long>>&a,unsigned long long target){
        int n=int(a.size());auto dfs=[&](auto&&self,int r,int c,unsigned long long x)->long long{x^=a[r][c];if(r==n-1&&c==n-1)return x==target;long long count=0;if(r+1<n)count+=self(self,r+1,c,x);if(c+1<n)count+=self(self,r,c+1,x);return count;};return dfs(dfs,0,0,0);
    };
    assert(count_grid_xor_paths({{1,5,2},{7,0,5},{4,2,3}},0)==2);
    assert(count_grid_xor_paths({{7}},7)==1);assert(count_grid_xor_paths({{7}},0)==0);
    for(int z=0;z<700;++z){int n=1+rng()%7;vector<vector<unsigned long long>>a(n,vector<unsigned long long>(n));for(auto&row:a)for(auto&x:row)x=rng()%8;unsigned long long k=rng()%8;assert(count_grid_xor_paths(a,k)==brute(a,k));}
''',
'digit-required-count-sum':r'''
    auto brute=[](int bound,const vector<int>&required){long long ans=0;for(int x=1;x<=bound;++x){string s=to_string(x);bool ok=true;for(int d:required)if(s.find(char('0'+d))==string::npos)ok=false;if(ok)ans+=x;}return int(ans%998244353);};
    assert(sum_with_required_digits("104",{0,1})==520);assert(sum_with_required_digits("0",{})==0);
    for(int z=0;z<600;++z){int b=rng()%2500;vector<int>r;for(int d=0;d<10;++d)if(rng()%4==0)r.push_back(d);if(!r.empty())r.push_back(r.back());assert(sum_with_required_digits(to_string(b),r)==brute(b,r));}
    constexpr long long mod=998244353;long long value=0;for(int i=0;i<10000;++i)value=(value*10+9)%mod;
    assert(sum_with_required_digits(string(10000,'9'),{})==value*(value+1)%mod*((mod+1)/2)%mod);
''',
'lis-tail-three-count':r'''
    auto brute=[](int n,int m){long long answer=0;vector<int>a(n);auto dfs=[&](auto&&self,int pos)->void{if(pos<n){for(int x=1;x<=m;++x){a[pos]=x;self(self,pos+1);}return;}vector<int>d(n,1);int best=0;for(int i=0;i<n;++i){for(int j=0;j<i;++j)if(a[j]<a[i])d[i]=max(d[i],d[j]+1);best=max(best,d[i]);}answer+=best==3;};dfs(dfs,0);return answer;};
    for(int n=0;n<=7;++n)for(int m=1;m<=4;++m)assert(count_lis_exactly_three(n,m)==brute(n,m));
    assert(count_lis_exactly_three(4,5)==135);assert(count_lis_exactly_three(111,3)==144980434);
''',
 'tree-one-mark-components':r'''
    auto brute=[](const vector<int>&mark,const vector<pair<int,int>>&edges){int n=int(mark.size());if(!n)return 0;int answer=0;for(int mask=0;mask<(1<<int(edges.size()));++mask){vector<int>parent(n);iota(parent.begin(),parent.end(),0);auto find=[&](auto&&self,int v)->int{return parent[v]==v?v:parent[v]=self(self,parent[v]);};for(int i=0;i<int(edges.size());++i)if(!(mask>>i&1)){auto[u,v]=edges[i];parent[find(find,u)]=find(find,v);}vector<int>counts(n);for(int i=0;i<n;++i)counts[find(find,i)]+=mark[i];bool ok=true;for(int i=0;i<n;++i)if(find(find,i)==i&&counts[i]!=1)ok=false;answer+=ok;}return answer;};
    for(int z=0;z<800;++z){int n=1+rng()%10;vector<int>marks(n);for(auto&x:marks)x=rng()%2;vector<pair<int,int>>e;for(int i=1;i<n;++i)e.emplace_back(i,rng()%i);assert(count_one_mark_components(marks,e)==brute(marks,e));}
    vector<int>marks(100000,1);vector<pair<int,int>>edges;for(int i=1;i<100000;++i)edges.emplace_back(i-1,i);assert(count_one_mark_components(marks,edges)==1);fill(marks.begin(),marks.end(),0);marks[50000]=1;assert(count_one_mark_components(marks,edges)==1);
''',
'sparse-grid-blocked-points':r'''
    auto brute=[](int h,int w,const vector<pair<int,int>>&blocked){vector<vector<long long>>d(h+1,vector<long long>(w+1));set<pair<int,int>>b(blocked.begin(),blocked.end());for(int r=1;r<=h;++r)for(int c=1;c<=w;++c){if(b.count({r,c}))continue;if(r==1&&c==1)d[r][c]=1;else d[r][c]=(d[r-1][c]+d[r][c-1])%1000000007;}return d[h][w];};
    for(int mask=0;mask<512;++mask){vector<pair<int,int>>b;for(int i=0;i<9;++i)if(mask>>i&1)b.emplace_back(i/3+1,i%3+1);assert(count_sparse_grid_paths(3,3,b)==brute(3,3,b));}
    for(int z=0;z<500;++z){int h=1+rng()%8,w=1+rng()%8;vector<pair<int,int>>b;for(int r=1;r<=h;++r)for(int c=1;c<=w;++c)if(rng()%4==0)b.emplace_back(r,c);if(!b.empty())b.push_back(b.back());shuffle(b.begin(),b.end(),rng);assert(count_sparse_grid_paths(h,w,b)==brute(h,w,b));}
    assert(count_sparse_grid_paths(100000,1,{})==1);
''',
'independent-race-first-hit':r'''
    auto power=[](long long a,long long e){long long r=1;for(;e;e>>=1,a=a*a%998244353)if(e&1)r=r*a%998244353;return r;};
    auto brute=[&](int n,int a,int b,int p,int q){constexpr long long mod=998244353;long long inverse=power(p,mod-2)*power(q,mod-2)%mod;vector<vector<long long>>memo(n,vector<long long>(n,-1));auto dfs=[&](auto&&self,int x,int y)->long long{auto&ans=memo[x][y];if(ans!=-1)return ans;ans=0;for(int i=1;i<=p;++i)for(int j=1;j<=q;++j){if(x+i>=n)ans=(ans+1)%mod;else if(y+j<n)ans=(ans+self(self,x+i,y+j))%mod;}return ans=ans*inverse%mod;};return dfs(dfs,a,b);};
    for(int n=2;n<=9;++n)for(int a=1;a<n;++a)for(int b=1;b<n;++b)for(int p=1;p<=4;++p)for(int q=1;q<=4;++q)assert(first_player_race_probability(n,a,b,p,q)==brute(n,a,b,p,q));
    assert(first_player_race_probability(4,2,3,3,2)==665496236);
    assert(first_player_race_probability(100,1,1,10,10)==264077814);
    assert(first_player_race_probability(8,3,3,1,1)==1);
'''
}
with tempfile.TemporaryDirectory(prefix='flowchartcp-dp-extension-') as tmp:
    for id,body in checks.items():
        text=(ROOT/'src/content/docs/techniques'/f'{id}.mdx').read_text()
        code=re.findall(r'```cpp\n(.*?)\n```',text,re.S)[0]
        source=Path(tmp)/(id+'.cpp');binary=Path(tmp)/id
        source.write_text(code+'\nint main(){\nstd::mt19937 rng(8231701);\n'+body+'\n}\n')
        compiled=subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
        if compiled.returncode:
            raise RuntimeError(compiled.stderr)
        subprocess.run([str(binary)],check=True,timeout=30)
        print(id+' PASS',flush=True)
