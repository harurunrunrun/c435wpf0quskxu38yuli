from pathlib import Path
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
checks={
'subset-sum-inverse-update':r'''
 auto brute=[](const vector<int>& a,int k){vector<int> answer(k+1);for(unsigned mask=0;mask<(1U<<a.size());++mask){int sum=0;for(int i=0;i<int(a.size());++i)if(mask>>i&1)sum+=a[i];if(sum<=k)++answer[sum];}return answer;};
 for(int trial=0;trial<700;++trial){int k=rng()%22;SubsetSumUpdates model(k);vector<int>a;for(int step=0;step<45;++step){if(a.empty()||(a.size()<12&&rng()%2)){int x=1+rng()%30;a.push_back(x);model.add(x);}else{int i=rng()%a.size();int x=a[i];a.erase(a.begin()+i);model.erase(x);}auto expected=brute(a,k);for(int s=0;s<=k;++s)assert(model.count(s)==expected[s]);}}
 SubsetSumUpdates empty(0);empty.add(5);empty.erase(5);assert(empty.count(0)==1);
 bool rejected=false;try{empty.erase(5);}catch(const invalid_argument&){rejected=true;}assert(rejected&&empty.count(0)==1);
 rejected=false;try{empty.add(0);}catch(const invalid_argument&){rejected=true;}assert(rejected);
 SubsetSumUpdates large(5000);for(int i=0;i<5000;++i)large.add(1);assert(large.count(5000)==1);for(int i=0;i<5000;++i)large.erase(1);for(int s=0;s<=5000;++s)assert(large.count(s)==(s==0));
''',
'all-segment-subset-sum':r'''
 auto brute=[](const vector<int>&a,int target){long long answer=0;for(int l=0;l<int(a.size());++l)for(int r=l;r<int(a.size());++r){for(int mask=0;mask<(1<<(r-l+1));++mask){int sum=0;for(int i=l;i<=r;++i)if(mask>>(i-l)&1)sum+=a[i];answer+=sum==target;}}return int(answer%998244353);};
 for(int n=0;n<=7;++n){int total=1;for(int i=0;i<n;++i)total*=3;for(int encoded=0;encoded<total;++encoded){vector<int>a(n);int v=encoded;for(int&i:a){i=1+v%3;v/=3;}for(int target=1;target<=10;++target)assert(all_segment_subset_sum_count(a,target)==brute(a,target));}}
 assert(all_segment_subset_sum_count({2,2,4},4)==5);assert(all_segment_subset_sum_count({3,1,4,1,5,9,2,6,5,3},10)==152);
 long long all_single=3000LL*3001*3002/6%998244353;
 assert(all_segment_subset_sum_count(vector<int>(3000,1),1)==all_single);
 assert(all_segment_subset_sum_count(vector<int>(3000,3000),3000)==all_single);
 assert(all_segment_subset_sum_count(vector<int>(3000,1),3000)==1);
 bool rejected=false;try{all_segment_subset_sum_count({0},1);}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'knapsack-first-color-bonus':r'''
 auto brute=[](const vector<ColorBonusItem>&a,int budget,long long bonus){long long answer=0;for(unsigned mask=0;mask<(1U<<a.size());++mask){int cost=0;long long value=0;set<int> colors;for(int i=0;i<int(a.size());++i)if(mask>>i&1){cost+=a[i].price;value+=a[i].utility;colors.insert(a[i].color);}if(cost<=budget)answer=max(answer,value+bonus*static_cast<long long>(colors.size()));}return answer;};
 for(int trial=0;trial<2200;++trial){vector<ColorBonusItem>a(rng()%12);for(auto&x:a)x={1+int(rng()%9),int(rng()%31)-15,int(rng()%5)-2};int budget=rng()%40;long long bonus=int(rng()%31)-15;assert(maximum_color_bonus_value(a,budget,bonus)==brute(a,budget,bonus));}
 assert(maximum_color_bonus_value({{1,3,1},{7,4,2},{4,5,1}},10,5)==17);
 assert(maximum_color_bonus_value({{1,3,7},{1,4,7}},2,5)==12);
 vector<ColorBonusItem> maximum;for(int i=0;i<500;++i)maximum.push_back({100,1000000000LL,i});
 assert(maximum_color_bonus_value(maximum,50000,1000000000)==1000000000000LL);
 assert(maximum_color_bonus_value({{50000,-1000000000,1}},0,-1000000000)==0);
 bool rejected=false;try{maximum_color_bonus_value({{0,1,1}},1,1);}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'interval-hit-last-selected':r'''
 auto brute=[](int n,const vector<tuple<int,int,long long>>&intervals){long long answer=0;for(int mask=0;mask<(1<<n);++mask){long long score=0;for(auto[l,r,w]:intervals){bool hit=false;for(int i=l-1;i<r;++i)hit=hit||bool(mask>>i&1);if(hit)score+=w;}answer=max(answer,score);}return answer;};
 for(int trial=0;trial<2600;++trial){int n=1+rng()%10;vector<tuple<int,int,long long>> intervals;for(int i=0,m=rng()%25;i<m;++i){int l=1+rng()%n,r=1+rng()%n;if(l>r)swap(l,r);intervals.push_back({l,r,int(rng()%25)-12});}assert(maximum_interval_hit_reward(n,intervals)==brute(n,intervals));}
 assert(maximum_interval_hit_reward(5,{{1,3,10},{2,4,-10},{3,5,10}})==20);
 assert(maximum_interval_hit_reward(1,{{1,1,-10}})==0);
 assert(maximum_interval_hit_reward(1,vector<tuple<int,int,long long>>(200000,{1,1,1000000000}))==200000000000000LL);
 vector<tuple<int,int,long long>> maximum;for(int i=1;i<=200000;++i)maximum.push_back({i,i,i%2?1000000000LL:-1000000000LL});
 assert(maximum_interval_hit_reward(200000,maximum)==100000000000000LL);
 assert(maximum_interval_hit_reward(1,{})==0);
''',
'partition-distinct-range-add':r'''
 auto brute=[](const vector<long long>&a,int groups){long long answer=-1;int n=a.size();for(int cuts=0;cuts<(1<<(n-1));++cuts)if(popcount(static_cast<unsigned>(cuts))==groups-1){long long score=0;set<long long> values;for(int i=0;i<n;++i){values.insert(a[i]);if(i==n-1||(cuts>>i&1)){score+=values.size();values.clear();}}answer=max(answer,score);}return answer;};
 for(int n=1;n<=7;++n){int total=1;for(int i=0;i<n;++i)total*=3;for(int encoded=0;encoded<total;++encoded){int v=encoded;vector<long long>a(n);for(auto&x:a){x=v%3-1;v/=3;}for(int k=1;k<=n;++k)assert(maximum_partition_distinct_sum(a,k)==brute(a,k));}}
 for(int trial=0;trial<400;++trial){int n=1+rng()%12;vector<long long>a(n);for(auto&x:a)x=rng()%2?LLONG_MIN:LLONG_MAX;int k=1+rng()%n;assert(maximum_partition_distinct_sum(a,k)==brute(a,k));}
 vector<long long> all(35000);iota(all.begin(),all.end(),-17000LL);assert(maximum_partition_distinct_sum(all,50)==35000);
 assert(maximum_partition_distinct_sum(vector<long long>(35000,1),50)==50);
 assert(maximum_partition_distinct_sum({1,2,1,2},1)==2);assert(maximum_partition_distinct_sum({1,2,1,2},4)==4);
''',
'partition-equal-pairs-moving-window':r'''
 auto brute=[](const vector<long long>&a,int groups){long long answer=LLONG_MAX;int n=a.size();for(int cuts=0;cuts<(1<<(n-1));++cuts)if(popcount(static_cast<unsigned>(cuts))==groups-1){long long score=0;int left=0;for(int right=0;right<n;++right)if(right==n-1||(cuts>>right&1)){for(int i=left;i<=right;++i)for(int j=i+1;j<=right;++j)score+=a[i]==a[j];left=right+1;}answer=min(answer,score);}return answer;};
 for(int n=1;n<=7;++n){int total=1;for(int i=0;i<n;++i)total*=3;for(int encoded=0;encoded<total;++encoded){int v=encoded;vector<long long>a(n);for(auto&x:a){x=v%3-1;v/=3;}for(int k=1;k<=n;++k)assert(minimum_equal_pair_partition(a,k)==brute(a,k));}}
 for(int trial=0;trial<700;++trial){int n=1+rng()%12;vector<long long>a(n);for(auto&x:a)x=rng()%6==0?LLONG_MIN:int(rng()%5);int k=1+rng()%n;assert(minimum_equal_pair_partition(a,k)==brute(a,k));}
 assert(minimum_equal_pair_partition({1,1,3,3,3,2,1},3)==1);
 assert(minimum_equal_pair_partition({1,2,1,2,1,2,1,2,1,2},2)==8);
 assert(minimum_equal_pair_partition(vector<long long>(100000,1),20)==249950000LL);
 vector<long long> unique(100000);iota(unique.begin(),unique.end(),0LL);assert(minimum_equal_pair_partition(unique,20)==0);
 assert(minimum_equal_pair_partition(vector<long long>(100000,1),1)==4999950000LL);
''',
'palindrome-erasure-boundary':r'''
 map<vector<int>,int> memo;
 function<int(const vector<int>&)> brute=[&](const vector<int>&a){if(a.empty())return 0;if(memo.contains(a))return memo[a];int answer=a.size();for(int l=0;l<int(a.size());++l)for(int r=l;r<int(a.size());++r){bool palindrome=true;for(int i=l,j=r;i<j;++i,--j)if(a[i]!=a[j])palindrome=false;if(palindrome){auto next=a;next.erase(next.begin()+l,next.begin()+r+1);answer=min(answer,1+brute(next));}}return memo[a]=answer;};
 for(int n=0;n<=8;++n){int total=1;for(int i=0;i<n;++i)total*=3;for(int encoded=0;encoded<total;++encoded){int v=encoded;vector<int>a(n);for(int&x:a){x=v%3;v/=3;}assert(minimum_palindrome_erasure(a)==brute(a));}}
 assert(minimum_palindrome_erasure({1,4,4,2,3,2,1})==2);assert(minimum_palindrome_erasure({1,5,3,5,4,3,4,1})==2);
 assert(minimum_palindrome_erasure({1,1})==1);assert(minimum_palindrome_erasure({1,2})==2);
 assert(minimum_palindrome_erasure(vector<int>(500,1))==1);
 vector<int> unique(500);iota(unique.begin(),unique.end(),0);assert(minimum_palindrome_erasure(unique)==500);
''',
'optional-booster-subset-speed':r'''
 using Point=pair<long double,long double>;
 auto brute=[](const vector<Point>&mandatory,const vector<Point>&boosters){auto p=mandatory;p.insert(p.end(),boosters.begin(),boosters.end());int n=mandatory.size(),all=p.size(),required=(1<<n)-1;long double answer=numeric_limits<long double>::infinity();function<void(int,Point,long double,long double)> visit=[&](int seen,Point at,long double time,long double speed){if((seen&required)==required)answer=min(answer,time+hypotl(at.first,at.second)/speed);for(int i=0;i<all;++i)if(!(seen>>i&1)){long double added=hypotl(at.first-p[i].first,at.second-p[i].second)/speed;visit(seen|(1<<i),p[i],time+added,speed*(i>=n?2:1));}};visit(0,{0,0},0,1);return answer;};
 for(int trial=0;trial<500;++trial){int n=1+rng()%4,m=rng()%4;vector<Point>a(n),b(m);set<pair<int,int>> occupied{{0,0}};for(auto* group:{&a,&b})for(auto&point:*group){pair<int,int> p;do{p={int(rng()%21)-10,int(rng()%21)-10};}while(occupied.contains(p));occupied.insert(p);point={p.first,p.second};}long double answer=minimum_boosted_tour(a,b),expected=brute(a,b);assert(abs(answer-expected)<=1e-11L*max(1.0L,expected));}
 assert(abs(minimum_boosted_tour({{3,4}},{})-10)<1e-15L);
 assert(abs(minimum_boosted_tour({{4,0}},{{1,0}})-4.5L)<1e-15L);
 assert(abs(minimum_boosted_tour({{4,0}},{{1000,0}})-8)<1e-15L);
 vector<Point>a,b;for(int i=1;i<=12;++i)a.push_back({i,0});for(int i=13;i<=17;++i)b.push_back({i,0});long double maximum=minimum_boosted_tour(a,b);assert(isfinite(maximum)&&maximum>0&&maximum<=24);
 assert(abs(minimum_boosted_tour({{1e9L,1e9L}},{{-1e9L,-1e9L}})-2*hypotl(1e9L,1e9L))<1e-5L);
'''
}

with tempfile.TemporaryDirectory(prefix='flowchartcp-dp-patterns-') as tmp:
    for id,body in checks.items():
        article=(ROOT/'src/content/docs/techniques'/f'{id}.mdx').read_text()
        code=re.findall(r'```cpp\n(.*?)\n```',article,re.S)[0]
        source=Path(tmp)/(id+'.cpp');binary=Path(tmp)/id
        source.write_text('#include <bits/stdc++.h>\nusing namespace std;\n'+code+'\nint main(){mt19937 rng(1732050807);\n'+body+'\n}\n')
        result=subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'vendor/ac-library'),str(source),'-o',str(binary)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stderr)
        subprocess.run([str(binary)],check=True,timeout=55)
        print(id+' PASS',flush=True)
