#!/usr/bin/env python3
"""Extract the actual sole MDX fence; compare literal square unions and independent DPs."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,tempfile
parser=argparse.ArgumentParser();parser.add_argument('article',nargs='?',type=Path,default=Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/diagonal-square-union-cover-monge-penalty-cht.mdx');parser.add_argument('--sanitize',action='store_true');parser.add_argument('--output',type=Path);args=parser.parse_args()
cpp=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',args.article.read_text(),re.M|re.S)
if len(cpp)!=1:raise RuntimeError('one complete always-visible C++20 fence required')
TESTS=r'''
#include <bits/stdc++.h>
using namespace std;
using ll=int64_t;using U=uint64_t;using Points=vector<pair<int,int>>;
using Interval=diagonal_square_union_detail::Interval;
using Line=diagonal_square_union_detail::Line;
U checks=0,calls=0,adapters=0,literal_sets=0,literal_photos=0,literal_limits=0,penalty_checks=0,convex_checks=0,duplicate_arrays=0,random_cases=0,partition_cases=0,partition_assignments=0,metamorphic=0,maximum_cases=0,batch_cases=0,invalid_cases=0,allocation_failures=0,checksum=0;
long long allocation_budget=-1;
void* operator new(size_t size) {
    if(allocation_budget==0)throw bad_alloc();
    if(allocation_budget>0)--allocation_budget;
    if(void* p=malloc(size?size:1))return p;
    throw bad_alloc();
}
void operator delete(void* p) noexcept {free(p);}
void operator delete(void* p,size_t) noexcept {free(p);}
void* operator new[](size_t size) {return ::operator new(size);}
void operator delete[](void* p) noexcept {free(p);}
void operator delete[](void* p,size_t) noexcept {free(p);}
void require(bool b,const char* message) {
    ++checks;
    if(!b){cerr<<"FAIL "<<message<<'\n';exit(1);}
}
ll square(ll x){return x*x;}
ll call(const Points& points,int m,int k,bool adapter=true) {
    auto original=points;
    ll answer=minimum_diagonal_square_union(points,m,k);++calls;
    require(points==original,"core leaves points unchanged");
    require(1<=answer&&answer<=square(m),"positive nonempty union bounded by whole grid");
    if(adapter) {
        vector<int> r,c;for(auto [x,y]:points){r.push_back(x);c.push_back(y);}
        const auto old_r=r,old_c=c;
        require(take_photos(int(points.size()),m,k,r,c)==answer,"original by-value adapter equals core");++adapters;
        require(r==old_r&&c==old_c,"adapter leaves caller arrays unchanged");
    }
    checksum=checksum*1000003+U(answer);return answer;
}
vector<Interval> brute_filter(const Points& points) {
    // Pairwise containment independently, not the production sorting scan.
    vector<Interval> all,kept;
    for(auto [r,c]:points)all.push_back({min(r,c),max(r,c)});
    for(int i=0;i<int(all.size());++i) {
        bool contained=false;
        for(int j=0;j<int(all.size());++j) {
            if(i==j)continue;
            if(all[j].left<=all[i].left&&all[i].right<=all[j].right&&
               (all[j].left<all[i].left||all[i].right<all[j].right||j<i))contained=true;
        }
        if(!contained)kept.push_back(all[i]);
    }
    sort(kept.begin(),kept.end(),[](Interval a,Interval b){return a.left<b.left;});
    for(int i=1;i<int(kept.size());++i)require(kept[i-1].left<kept[i].left&&kept[i-1].right<kept[i].right,"pairwise containment oracle gives strict endpoints");
    return kept;
}
vector<ll> partition_dp(const vector<Interval>& a) {
    const int n=int(a.size());const ll inf=ll{1}<<60;
    vector<vector<ll>> f(n+1,vector<ll>(n+1,inf));f[0][0]=0;
    for(int q=1;q<=n;++q) {
        for(int i=q;i<=n;++i) {
            for(int t=q-1;t<i;++t) {
                if(f[q-1][t]==inf)continue;
                ll overlap=t?max(0,a[t-1].right-a[t].left+1):0;
                f[q][i]=min(f[q][i],f[q-1][t]+square(ll(a[i-1].right)-a[t].left+1)-square(overlap));
            }
        }
    }
    vector<ll> answer;
    for(int q=1;q<=n;++q)answer.push_back(f[q][n]);
    for(int i=1;i<n;++i){require(answer[i]<=answer[i-1],"F nonincreasing");++convex_checks;}
    for(int i=1;i+1<n;++i){require(2*answer[i]<=answer[i-1]+answer[i+1],"F discrete convex");++convex_checks;}
    return answer;
}
void check_penalty(const vector<Interval>& a,const vector<ll>& f,ll penalty) {
    pair<ll,int> expected{ll{1}<<62,0};
    for(int q=1;q<=int(f.size());++q)expected=min(expected,pair{f[q-1]+penalty*q,q});
    vector<Line> scratch(a.size());
    auto actual=diagonal_square_union_detail::penalized(a,penalty,scratch);
    require(pair{actual.cost,actual.count}==expected,"real published hull DP exact cost AND fewer-photo tie");
    // Repeat using dirty workspace; no previous hull/penalty is inherited.
    auto again=diagonal_square_union_detail::penalized(a,penalty,scratch);
    require(pair{again.cost,again.count}==expected,"penalty workspace reset");++penalty_checks;
}
struct Tiny {
    int m,t;vector<pair<int,int>> types;vector<vector<int>> best;
    explicit Tiny(int size):m(size) {
        for(int a=0;a<m;++a)for(int b=a;b<m;++b)types.emplace_back(a,b);
        t=int(types.size());const int total=1<<t;best.assign(total,vector<int>(t+1,1000000));
        vector<uint32_t> grid(total),cover(total);vector<uint32_t> photo_grid(t),photo_cover(t);
        for(int i=0;i<t;++i) {
            auto [a,b]=types[i];
            for(int r=a;r<=b;++r)for(int c=a;c<=b;++c)photo_grid[i]|=uint32_t{1}<<(r*m+c);
            for(int j=0;j<t;++j)if(a<=types[j].first&&types[j].second<=b)photo_cover[i]|=uint32_t{1}<<j;
        }
        // ALL photo subsets, including empty/redundant/nested/overlapping.
        for(int mask=0;mask<total;++mask) {
            if(mask){int bit=countr_zero(unsigned(mask)),rest=mask&(mask-1);grid[mask]=grid[rest]|photo_grid[bit];cover[mask]=cover[rest]|photo_cover[bit];}
            int q=popcount(unsigned(mask));best[cover[mask]][q]=min(best[cover[mask]][q],int(popcount(grid[mask])));++literal_photos;
        }
        for(auto& row:best)for(int q=1;q<=t;++q)row[q]=min(row[q],row[q-1]);
        // Required cells may be covered along with arbitrary extra cells.
        for(int bit=0;bit<t;++bit)for(int mask=0;mask<total;++mask)if(!(mask>>bit&1))
            for(int q=0;q<=t;++q)best[mask][q]=min(best[mask][q],best[mask|1<<bit][q]);
    }
    int requirement_mask(const Points& p) const {
        int mask=0;
        for(auto [r,c]:p){auto a=pair{min(r,c),max(r,c)};int at=int(find(types.begin(),types.end(),a)-types.begin());mask|=1<<at;}
        return mask;
    }
    ll exact(const Points& p,int k) const {return best[requirement_mask(p)][min(k,t)];}
};
void exhaustive() {
    for(int m=1;m<=5;++m) {
        Tiny literal(m);
        for(int mask=1;mask<(1<<literal.t);++mask) {
            Points p;for(int i=0;i<literal.t;++i)if(mask>>i&1)p.push_back(literal.types[i]);
            auto a=brute_filter(p);auto f=partition_dp(a);
            for(int k=1;k<=int(p.size());++k) {
                ll exact=literal.best[mask][k];
                require(f[min(k,int(f.size()))-1]==exact,"partition DP equals literal square-cell UNION optimum");
                require(call(p,m,k)==exact,"published full API equals literal ALL square-photo-subset optimum");++literal_limits;
            }
            for(ll penalty=0;penalty<=square(m);++penalty)check_penalty(a,f,penalty);
            Points reflected=p;for(auto& [r,c]:reflected)swap(r,c);
            int k=1+mask%int(p.size());
            require(call(reflected,m,k,false)==literal.exact(p,k),"reflect across main diagonal");++metamorphic;
            if(mask%31==0) {
                Points shifted=p;for(auto& [r,c]:shifted){r+=999995;c+=999995;}
                require(call(shifted,999995+m,k,false)==literal.exact(p,k),"translate along diagonal to maximum coordinates");++metamorphic;
                Points duplicate=p;duplicate.insert(duplicate.end(),p.rbegin(),p.rend());
                require(call(duplicate,m,k)==literal.exact(p,k),"duplicate/reverse input cells preserve union answer");
                require(call(duplicate,m,int(duplicate.size()),false)==literal.exact(p,int(p.size())),"K clamped after duplicate/containment removal");metamorphic+=2;
            }
            ++literal_sets;
        }
    }
    // All ordered cell arrays on grids1..3, duplicates/orientation retained.
    for(int m=1;m<=3;++m) {
        Tiny literal(m);Points p;
        auto generate=[&](auto&& self,int n)->void {
            if(int(p.size())==n){for(int k=1;k<=n;++k)require(call(p,m,k)==literal.exact(p,k),"every ordered cell array with duplicate/symmetric coordinates");++duplicate_arrays;return;}
            for(int r=0;r<m;++r)for(int c=0;c<m;++c){p.emplace_back(r,c);self(self,n);p.pop_back();}
        };
        for(int n=1;n<=5;++n)generate(generate,n);
    }
}
ll literal_union(const vector<Interval>& photos) {
    // Generic exact union-area sweep on actual squares. No neighbor-overlap
    // subtraction or partition recurrence is used here.
    vector<int> x;
    for(auto p:photos){x.push_back(p.left);x.push_back(p.right+1);}
    sort(x.begin(),x.end());x.erase(unique(x.begin(),x.end()),x.end());ll area=0;
    for(int i=0;i+1<int(x.size());++i) {
        vector<pair<int,int>> y;
        for(auto p:photos)if(p.left<=x[i]&&x[i]<p.right+1)y.emplace_back(p.left,p.right+1);
        sort(y.begin(),y.end());ll length=0;int left=-1,right=-1;
        for(auto [a,b]:y){if(a>right){length+=right-left;left=a;right=b;}else right=max(right,b);}
        length+=right-left;area+=ll(x[i+1]-x[i])*length;
    }
    return area;
}
void exponential_partitions(const vector<Interval>& a,const vector<ll>& f) {
    const int n=int(a.size());vector<ll> best(n,ll{1}<<60);
    for(unsigned mask=0;mask<(1U<<(n-1));++mask) {
        vector<Interval> photos;int start=0;
        for(int i=0;i<n;++i)if(i+1==n||(mask>>i&1)){photos.push_back({a[start].left,a[i].right});start=i+1;}
        ll area=literal_union(photos);best[photos.size()-1]=min(best[photos.size()-1],area);++partition_assignments;
    }
    require(best==f,"every partition evaluated by independent exact square UNION sweep");++partition_cases;
}
void randoms() {
    mt19937_64 rng(20160816);
    for(int it=0;it<3500;++it) {
        int n=1+int(rng()%30),m=1000000;Points p;
        if(it%3==0) {
            for(int i=0;i<n;++i)p.emplace_back(int(rng()%m),int(rng()%m));
        } else if(it%3==1) {
            int width=int(rng()%700001),at=int(rng()%100);
            for(int i=0;i<n;++i){at+=1+int(rng()%5000);p.emplace_back(at,at+width);}
        } else {
            for(int i=0;i<n;++i){int x=(i*i+3*i)*997;p.emplace_back(x,x);}
            shuffle(p.begin(),p.end(),rng);
            for(int i=1;i<n;i+=3)if(rng()%2)p[i]=p[i-1];
        }
        auto a=brute_filter(p);auto f=partition_dp(a);
        for(int k=1;k<=n;++k)require(call(p,m,k,k==1||k==n)==f[min(k,int(f.size()))-1],"random all K versus independent cubic partition DP");
        for(ll penalty:array<ll,4>{0,1,1000000000000LL,ll(rng()%1000000000001ULL)})check_penalty(a,f,penalty);
        if(it<700&&a.size()<=12)exponential_partitions(a,f);
        Points flipped=p;for(auto& [r,c]:flipped){r=m-1-r;c=m-1-c;}
        int k=1+int(rng()%n);require(call(flipped,m,k,false)==f[min(k,int(f.size()))-1],"reflect both coordinates and reverse interval order");++metamorphic;
        ++random_cases;
    }
    for(int it=0;it<20000;++it) {
        require(call(it%2?Points{{0,3},{4,4},{4,6},{4,5},{4,6}}:Points{{1,4},{4,1}},7,it%2?2:2,false)==(it%2?25:16),"reentrant different shapes/sizes");++batch_cases;
    }
}
ll balanced(int n,int k) {ll q=n/k,r=n%k;return r*square(q+1)+(k-r)*square(q);}
ll diagonal_spaced(int n,int k,int step) {ll q=n/k,r=n%k;return r*square(step*q+1)+(k-r)*square(step*(q-1)+1);}
ll large_union(const Points& p) {
    // Generic rectangle-union line sweep and coverage-count segment tree.
    struct Event{int x,l,r,delta;};vector<Event> events;vector<int> y;
    for(auto [a,b]:p){if(a>b)swap(a,b);events.push_back({a,a,b+1,1});events.push_back({b+1,a,b+1,-1});y.push_back(a);y.push_back(b+1);}
    sort(events.begin(),events.end(),[](auto a,auto b){return a.x<b.x;});sort(y.begin(),y.end());y.erase(unique(y.begin(),y.end()),y.end());
    int count=int(y.size())-1;vector<int> cover(4*count);vector<ll> length(4*count);
    auto add=[&](auto&& self,int v,int l,int r,int a,int b,int delta)->void {
        if(b<=l||r<=a)return;
        if(a<=l&&r<=b)cover[v]+=delta;
        else {int mid=(l+r)/2;self(self,v*2,l,mid,a,b,delta);self(self,v*2+1,mid,r,a,b,delta);}
        length[v]=cover[v]>0?ll(y[r])-y[l]:r-l==1?0:length[v*2]+length[v*2+1];
    };
    ll area=0;int previous=events[0].x;
    for(auto e:events){area+=ll(e.x-previous)*length[1];previous=e.x;int a=int(lower_bound(y.begin(),y.end(),e.l)-y.begin()),b=int(lower_bound(y.begin(),y.end(),e.r)-y.begin());add(add,1,0,count,a,b,e.delta);}
    require(length[1]==0,"generic rectangle sweep ends with no active coverage");return area;
}
void maximum() {
    const int n=100000,m=1000000;Points p(n);
    auto verify=[&](int k,ll expected){require(call(p,m,k)==expected,"original maximum N/M/K against independent exact structural formula");++maximum_cases;};
    fill(p.begin(),p.end(),pair{m-1,m-1});verify(1,1);verify(n,1);
    for(int i=0;i<n;++i)p[i]={i,i};
    for(int k:{1,2,3,49999,n-1,n})verify(k,balanced(n,k));
    for(int i=0;i<n;++i)p[i]={10*i,10*i};
    for(int k:{1,2,23,49999,n})verify(k,diagonal_spaced(n,k,10));
    for(auto& [r,c]:p){r+=9;c+=9;}verify(2,diagonal_spaced(n,2,10));verify(n-1,diagonal_spaced(n,n-1,10));
    for(int i=0;i<n;++i)p[i]={i,i+900000};
    for(int k:{1,2,3,49999,n-1,n})verify(k,square(900000)+2LL*900000*n+balanced(n,k));
    for(int i=0;i<n;++i)p[i]={i%1000,(i%1000)+999000};
    for(int k:{1,2,23,n})verify(k,square(999000)+2LL*999000*1000+balanced(1000,min(k,1000)));
    fill(p.begin(),p.end(),pair{m/2,m/2});p[0]={0,m-1};verify(1,square(m));verify(n,square(m));
    for(int i=0;i<n;++i)p[i]=i%2?pair{0,0}:pair{m-1,m-1};
    verify(1,square(m));verify(n,2);
    mt19937 rng(2016081601);
    for(auto& [r,c]:p){r=int(rng()%m);c=int(rng()%m);}
    verify(n,large_union(p));
    require(call({{1,4},{4,1}},6,2)==16,"fresh call after maximum buffers");
}
void invalids() {
    auto bad=[](const Points& p,int m,int k) {
        const auto original=p;bool caught=false;
        try{(void)minimum_diagonal_square_union(p,m,k);}catch(const invalid_argument&){caught=true;}
        require(caught&&p==original,"invalid core arguments reject without changing input");++invalid_cases;
    };
    bad({},1,1);bad({{0,0}},0,1);bad({{0,0}},-1,1);bad({{0,0}},1000001,1);bad({{0,0}},INT_MIN,1);bad({{0,0}},INT_MAX,1);
    bad({{0,0}},1,0);bad({{0,0}},1,-1);bad({{0,0}},1,2);bad({{0,0}},1,INT_MIN);bad({{0,0}},1,INT_MAX);
    for(auto cell:Points{{-1,0},{0,-1},{1,0},{0,1},{INT_MIN,0},{0,INT_MIN},{INT_MAX,0},{0,INT_MAX}})bad({cell},1,1);
    Points oversized(100001,{0,0});bad(oversized,1,1);
    auto adapter_bad=[](int n,int m,int k,vector<int> r,vector<int> c) {
        const auto old_r=r,old_c=c;bool caught=false;
        try{(void)take_photos(n,m,k,r,c);}catch(const invalid_argument&){caught=true;}
        require(caught&&r==old_r&&c==old_c,"invalid original adapter size/count/coordinate contract");++invalid_cases;
    };
    adapter_bad(0,1,1,{},{});adapter_bad(-1,1,1,{},{});adapter_bad(INT_MAX,1,1,{0},{0});adapter_bad(100001,1,1,vector<int>(100001),vector<int>(100001));
    adapter_bad(1,1,1,{},{});adapter_bad(2,2,1,{0},{0,1});adapter_bad(2,2,1,{0,1},{0});adapter_bad(1,1,1,{0,0},{0,0});
    adapter_bad(1,0,1,{0},{0});adapter_bad(1,1000001,1,{0},{0});adapter_bad(1,1,0,{0},{0});adapter_bad(1,1,2,{0},{0});
    adapter_bad(1,1,1,{-1},{0});adapter_bad(1,1,1,{0},{1});adapter_bad(1,1,1,{INT_MAX},{0});adapter_bad(1,1,1,{0},{INT_MIN});
    require(call({{0,0}},1,1)==1,"valid call after every invalid contract branch");
}
void allocation_tests() {
    for(int test=0;test<2;++test) {
        Points p;int m,k;ll expected;
        if(test==0){p={{0,3},{4,4},{4,6},{4,5},{4,6}};m=7;k=2;expected=25;}
        else{p.resize(100000);for(int i=0;i<100000;++i)p[i]={i,i};m=1000000;k=50000;expected=200000;}
        const auto original=p;
        for(int budget=0;budget<=2;++budget) {
            bool caught=false;ll answer=-1;allocation_budget=budget;
            try{answer=minimum_diagonal_square_union(p,m,k);}catch(const bad_alloc&){caught=true;}
            allocation_budget=-1;
            require(caught==(budget<2),"core allocation failures propagate, exactly two allocations");
            require(p==original,"source preserved after core allocation failure");
            if(caught)++allocation_failures;else require(answer==expected,"core succeeds after exact required allocations");
        }
        vector<int> r,c;for(auto [a,b]:p){r.push_back(a);c.push_back(b);}const auto old_r=r,old_c=c;
        for(int budget=0;budget<=5;++budget) {
            bool caught=false;ll answer=-1;allocation_budget=budget;
            try{answer=take_photos(int(p.size()),m,k,r,c);}catch(const bad_alloc&){caught=true;}
            allocation_budget=-1;
            require(caught==(budget<5),"adapter copies/points/core allocation failures propagate");
            require(r==old_r&&c==old_c,"adapter source arrays preserved after every allocation failure");
            if(caught)++allocation_failures;else require(answer==expected,"adapter succeeds after exact required allocations");
        }
        require(call(p,m,k)==expected,"fresh call following all allocation exceptions");
    }
}
int main() {
    static_assert(is_same_v<decltype(&take_photos),long long(*)(int,int,int,vector<int>,vector<int>)>);
    static_assert(is_same_v<decltype(&minimum_diagonal_square_union),int64_t(*)(const Points&,int,int)>);
    auto start=chrono::steady_clock::now();
    require(call({{0,3},{4,4},{4,6},{4,5},{4,6}},7,2)==25,"official first sample25 with duplicate point");
    require(call({{1,4},{4,1}},6,2)==16,"official symmetric duplicate-interval sample16");
    require(call({{0,2},{1,3}},4,2)==14,"overlap area4 subtracted from18");
    require(call({{0,0},{0,0}},1,2)==1,"one-cell grid and K greater than filtered intervals");
    invalids();exhaustive();randoms();maximum();allocation_tests();
    cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<calls<<",\"originalAdapterCalls\":"<<adapters<<",\"allInterestSubsetsM1to5\":"<<literal_sets<<",\"literalAllPhotoSubsets\":"<<literal_photos<<",\"literalRequestedPhotoLimits\":"<<literal_limits<<",\"penaltyCostAndFewerCountComparisons\":"<<penalty_checks<<",\"convexityAndMonotonicityChecks\":"<<convex_checks<<",\"allOrderedCellArraysM1to3N1to5\":"<<duplicate_arrays<<",\"randomAllKCases\":"<<random_cases<<",\"literalUnionPartitionCases\":"<<partition_cases<<",\"literalUnionPartitionAssignments\":"<<partition_assignments<<",\"metamorphicChecks\":"<<metamorphic<<",\"maximumOriginalCases\":"<<maximum_cases<<",\"reentrantBatchCalls\":"<<batch_cases<<",\"invalidCases\":"<<invalid_cases<<",\"allocationFailuresInjected\":"<<allocation_failures<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<chrono::duration<double>(chrono::steady_clock::now()-start).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-ioi2016-aliens-') as temp:
    source=Path(temp)/'check.cpp';binary=Path(temp)/'check';source.write_text(cpp[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror','-Wno-mismatched-new-delete'];env=dict(os.environ)
    if args.sanitize:
        flags=['-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-Wno-mismatched-new-delete','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'];env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
    subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True,timeout=120)
    run=subprocess.run(['/usr/bin/time','-f','peak_rss_kib=%M',str(binary)],capture_output=True,text=True,env=env,timeout=300)
    if run.returncode:print(run.stdout,end='');print(run.stderr,end='');run.check_returncode()
    result=json.loads(run.stdout);result['peakRSSKiB']=int(re.search(r'peak_rss_kib=(\d+)',run.stderr)[1]);result['cppSha256']=hashlib.sha256(cpp[0].encode()).hexdigest();result['sanitized']=args.sanitize
    output=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:args.output.write_text(output)
    print(output,end='')
