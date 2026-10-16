from pathlib import Path
import re, subprocess, tempfile

ROOT=Path(__file__).resolve().parents[2]
checks={
'deadline-duration-remove-longest':r'''
 auto brute=[](vector<DeadlineJob> jobs){sort(jobs.begin(),jobs.end(),[](auto a,auto b){return a.deadline<b.deadline;});int n=jobs.size(),best=0;for(int mask=0;mask<(1<<n);++mask){long long time=0;bool valid=true;for(int i=0;i<n;++i)if(mask>>i&1){time+=jobs[i].duration;if(time>jobs[i].deadline)valid=false;}if(valid)best=max(best,__builtin_popcount(unsigned(mask)));}return best;};
 assert(maximum_on_time_jobs({})==0);
 assert(maximum_on_time_jobs({{100,200},{200,1300},{1000,1250},{2000,3200}})==3);
 assert(maximum_on_time_jobs({{3,2},{4,3}})==0);
 for(int trial=0;trial<1500;++trial){int n=rng()%13;vector<DeadlineJob>jobs;for(int i=0;i<n;++i)jobs.push_back({1+int(rng()%12),int(rng()%40)});assert(maximum_on_time_jobs(jobs)==brute(jobs));}
 assert(maximum_on_time_jobs(vector<DeadlineJob>(200000,{1000000000000LL,1000000000000LL}))==1);
''',
'unit-release-expiry-earliest':r'''
 auto brute=[](const vector<pair<long long,long long>>& jobs){int n=jobs.size();vector<int>possible(1<<n,-1);possible[0]=0;int best=0;for(int t=0;t<=12;++t){auto next=possible;for(int mask=0;mask<(1<<n);++mask)if(possible[mask]>=0)for(int i=0;i<n;++i)if(!(mask>>i&1)&&jobs[i].first<=t&&t<=jobs[i].second)next[mask|(1<<i)]=1;possible=next;}for(int mask=0;mask<(1<<n);++mask)if(possible[mask]>=0)best=max(best,__builtin_popcount(unsigned(mask)));return best;};
 assert(maximum_unit_jobs({})==0);assert(maximum_unit_jobs({{0,0},{0,0},{1,1}})==2);
 assert(maximum_unit_jobs({{1,2},{1,2},{2,3},{1,3},{1,5}})==4);
 for(int trial=0;trial<1200;++trial){int n=rng()%11;vector<pair<long long,long long>>jobs;for(int i=0;i<n;++i){int r=rng()%10;jobs.push_back({r,r+int(rng()%4)});}assert(maximum_unit_jobs(jobs)==brute(jobs));}
 assert(maximum_unit_jobs({{1,2},{1000000000000000000LL,2000000000000000000LL}})==2);
 assert(maximum_unit_jobs(vector<pair<long long,long long>>(200000,{1000000000000000000LL,1000000000000199999LL}))==200000);
''',
'interval-k-resources-predecessor':r'''
 auto brute=[](const vector<pair<long long,long long>>&jobs,int k){int n=jobs.size(),best=0;for(int mask=0;mask<(1<<n);++mask){vector<pair<long long,int>>events;for(int i=0;i<n;++i)if(mask>>i&1){events.push_back({jobs[i].first,1});events.push_back({jobs[i].second,-1});}sort(events.begin(),events.end());int active=0;bool valid=true;for(auto[t,d]:events){(void)t;active+=d;if(active>k)valid=false;}if(valid)best=max(best,__builtin_popcount(unsigned(mask)));}return best;};
 assert(maximum_intervals_k_resources({},1)==0);assert(maximum_intervals_k_resources({{0,1},{1,2},{2,3}},1)==3);
 assert(maximum_intervals_k_resources({{1,5},{8,10},{3,6},{2,5},{6,9}},2)==4);
 for(int trial=0;trial<2000;++trial){int n=rng()%12,k=rng()%5;vector<pair<long long,long long>>jobs;for(int i=0;i<n;++i){int start=int(rng()%13)-6;jobs.push_back({start,start+1+int(rng()%6)});}assert(maximum_intervals_k_resources(jobs,k)==brute(jobs,k));}
 vector<pair<long long,long long>>large;for(int i=0;i<200000;++i)large.push_back({i,i+1});assert(maximum_intervals_k_resources(large,1)==200000);assert(maximum_intervals_k_resources(large,0)==0);
 assert(maximum_intervals_k_resources({{LLONG_MIN,LLONG_MAX}},1)==1);
''',
'threshold-coupon-max-discount':r'''
 auto brute=[](const vector<long long>&p,const vector<ThresholdCoupon>&c){int n=p.size(),m=c.size();vector<vector<long long>>dp(n+1,vector<long long>(1<<m,LLONG_MAX/4));dp[0][0]=0;for(int i=0;i<n;++i)for(int mask=0;mask<(1<<m);++mask)if(dp[i][mask]<LLONG_MAX/4){dp[i+1][mask]=min(dp[i+1][mask],dp[i][mask]+p[i]);for(int j=0;j<m;++j)if(!(mask>>j&1)&&c[j].lower<=p[i])dp[i+1][mask|(1<<j)]=min(dp[i+1][mask|(1<<j)],dp[i][mask]+p[i]-c[j].discount);}return *min_element(dp[n].begin(),dp[n].end());};
 assert(minimum_coupon_cost({4,3,1},{{4,2},{4,3},{2,1}})==4);assert(minimum_coupon_cost({},{{5,4}})==0);
 for(int trial=0;trial<1200;++trial){vector<long long>p(rng()%9);for(auto&x:p)x=rng()%12;vector<ThresholdCoupon>c;for(int i=0,m=rng()%9;i<m;++i){long long lower=rng()%12;c.push_back({lower,static_cast<long long>(rng()%(lower+1))});}assert(minimum_coupon_cost(p,c)==brute(p,c));}
 assert(minimum_coupon_cost(vector<long long>(200000,1000000000),vector<ThresholdCoupon>(200000,{1000000000,1000000000}))==0);
''',
'unordered-split-residual-huffman':r'''
 map<vector<long long>,long long>memo;
 function<long long(vector<long long>)>merge_cost=[&](vector<long long>a){sort(a.begin(),a.end());if(a.size()<2)return 0LL;if(auto it=memo.find(a);it!=memo.end())return it->second;long long best=LLONG_MAX;for(int i=0;i<int(a.size());++i)for(int j=i+1;j<int(a.size());++j){vector<long long>b;for(int z=0;z<int(a.size());++z)if(z!=i&&z!=j)b.push_back(a[z]);b.push_back(a[i]+a[j]);best=min(best,a[i]+a[j]+merge_cost(b));}return memo[a]=best;};
 auto brute=[&](long long total,const vector<long long>&wanted){int rest=total-accumulate(wanted.begin(),wanted.end(),0LL);long long best=LLONG_MAX;function<void(int,int,vector<long long>)>partitions=[&](int remaining,int lo,vector<long long>extra){if(!remaining){auto pieces=wanted;pieces.insert(pieces.end(),extra.begin(),extra.end());best=min(best,merge_cost(pieces));return;}for(int x=lo;x<=remaining;++x){auto next=extra;next.push_back(x);partitions(remaining-x,x,next);}};partitions(rest,1,{});return best;};
 assert(minimum_free_order_split(0,{})==0);assert(minimum_free_order_split(100,{})==0);assert(minimum_free_order_split(7,{1,2,1,2,1})==16);
 for(int trial=0;trial<220;++trial){int n=1+rng()%4;vector<long long>a(n);for(auto&x:a)x=1+rng()%4;long long total=accumulate(a.begin(),a.end(),0LL)+rng()%5;assert(minimum_free_order_split(total,a)==brute(total,a));}
 assert(minimum_free_order_split(1000000000000000LL,{1000000000LL,1000000000LL,1000000000LL})==1000005000000000LL);
 vector<long long>many(200000,1);assert(minimum_free_order_split(1000000000000000LL,many)>1000000000000000LL);
''',
'fixed-size-diversity-exchange':r'''
 auto brute=[](const vector<pair<int,long long>>&a,int k,const vector<long long>&bonus){int n=a.size();long long best=LLONG_MIN;for(int mask=0;mask<(1<<n);++mask)if(__builtin_popcount(unsigned(mask))==k){long long sum=0;set<int>types;for(int i=0;i<n;++i)if(mask>>i&1){sum+=a[i].second;types.insert(a[i].first);}best=max(best,sum+bonus[types.size()]);}return best;};
 assert(maximum_diversity_score({},0,{3})==3);
 for(int trial=0;trial<2200;++trial){int n=rng()%13,k=rng()%(n+1);vector<pair<int,long long>>a;for(int i=0;i<n;++i)a.push_back({int(rng()%6)-2,int(rng()%31)-15});vector<long long>b(k+1);b[0]=-10;for(int x=1;x<=k;++x)b[x]=b[x-1]+rng()%30;assert(maximum_diversity_score(a,k,b)==brute(a,k,b));}
 bool rejected=false;try{maximum_diversity_score({{0,1}},1,{10,0});}catch(const invalid_argument&){rejected=true;}assert(rejected);
 vector<pair<int,long long>>a;for(int i=0;i<200000;++i)a.push_back({i,1000000000});vector<long long>b(200001);for(long long x=0;x<=200000;++x)b[x]=x*x;assert(maximum_diversity_score(a,200000,b)==200040000000000LL);
''',
'cyclic-inversion-delta':r'''
 auto brute=[](vector<int>a){vector<long long>answer;int n=a.size();for(int shift=0;shift<n;++shift){long long inv=0;for(int i=0;i<n;++i)for(int j=i+1;j<n;++j)if(a[i]>a[j])++inv;answer.push_back(inv);rotate(a.begin(),a.begin()+1,a.end());}return answer;};
 assert(cyclic_inversion_counts({}).empty());assert(cyclic_inversion_counts({0})==vector<long long>{0});
 assert(cyclic_inversion_counts({0,1,2,3})==vector<long long>({0,3,4,3}));
 for(int n=1;n<=8;++n){vector<int>a(n);iota(a.begin(),a.end(),0);do{assert(cyclic_inversion_counts(a)==brute(a));}while(next_permutation(a.begin(),a.end()));}
 vector<int>a(300000);iota(a.rbegin(),a.rend(),0);auto output=cyclic_inversion_counts(a);assert(output.front()==300000LL*299999/2);
 bool rejected=false;try{cyclic_inversion_counts({0,0});}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'maximum-product-sign-exchange':r'''
 auto product=[](const vector<long long>&a){__int128 p=1;for(auto x:a)p*=x;return p;};
 auto brute=[&](const vector<long long>&a,int k){__int128 best=-((__int128)1<<120);for(int mask=0;mask<(1<<int(a.size()));++mask)if(__builtin_popcount(unsigned(mask))==k){__int128 p=1;for(int i=0;i<int(a.size());++i)if(mask>>i&1)p*=a[i];best=max(best,p);}return best;};
 assert(maximum_product_mod({1,2,-3,-4},2)==12);assert(maximum_product_mod({-1,-2,-3,-4},3)==1000000001);
 for(int trial=0;trial<3500;++trial){int n=1+rng()%13,k=1+rng()%n;vector<long long>a(n);for(auto&x:a)x=int(rng()%15)-7;auto chosen=maximum_product_selection(a,k);assert(chosen.size()==size_t(k));auto available=a;for(auto x:chosen){auto it=find(available.begin(),available.end(),x);assert(it!=available.end());available.erase(it);}__int128 expected=brute(a,k);assert(product(chosen)==expected);long long mod=expected%1000000007;if(mod<0)mod+=1000000007;assert(maximum_product_mod(a,k)==mod);}
 assert(maximum_product_mod({1000000000,1000000000,-1000000000,-1000000000},2)==49);
 assert(maximum_product_mod({-5,-3,0},1)==0);assert(maximum_product_mod({-5,-3,0},3)==0);
 assert(maximum_product_selection(vector<long long>(200000,-1000000000),199999).size()==199999);
'''
}
with tempfile.TemporaryDirectory(prefix='flowchartcp-selection-patterns-') as tmp:
    for id,body in checks.items():
        article=(ROOT/'src/content/docs/techniques'/f'{id}.mdx').read_text()
        code=re.findall(r'```cpp\n(.*?)\n```',article,re.S)[0]
        source=Path(tmp)/(id+'.cpp');binary=Path(tmp)/id
        source.write_text('#include <bits/stdc++.h>\nusing namespace std;\n'+code+'\nint main(){mt19937 rng(24681357);\n'+body+'\n}\n')
        result=subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stderr)
        subprocess.run([str(binary)],check=True,timeout=45)
        print(id+' PASS',flush=True)
