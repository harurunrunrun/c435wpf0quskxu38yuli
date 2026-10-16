from pathlib import Path
import re, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
checks={
'range-and-forced-bits':r'''
 auto meets=[](const vector<uint64_t>&a,const vector<RangeAndRequirement>&q){for(auto c:q){uint64_t value=~uint64_t{0};for(int i=c.left;i<c.right;++i)value&=a[i];if(value!=c.value)return false;}return true;};
 for(int trial=0;trial<1800;++trial){int n=1+rng()%5;vector<RangeAndRequirement>q(rng()%9);for(auto&c:q){c.left=rng()%n;c.right=c.left+1+rng()%(n-c.left);c.value=rng()%4;}auto result=construct_range_and(n,q,2);bool exists=false;vector<uint64_t>smallest(n,3);for(int mask=0;mask<(1<<(2*n));++mask){vector<uint64_t>a(n);for(int i=0;i<n;++i)a[i]=(mask>>(2*i))&3;if(meets(a,q)){exists=true;for(int i=0;i<n;++i)smallest[i]&=a[i];}}assert(result.has_value()==exists);if(result){assert(meets(*result,q));assert(*result==smallest);}}
 uint64_t high=uint64_t{1}<<63;
 assert(construct_range_and(2,{{0,2,high}},64)==optional<vector<uint64_t>>({high,high}));
 assert(!construct_range_and(2,{{0,2,high},{0,1,0}},64));
 assert(construct_range_and(3,{},64)==optional<vector<uint64_t>>({0,0,0}));
 vector<RangeAndRequirement>q(200000,{0,200000,UINT64_MAX});auto a=construct_range_and(200000,q,64);assert(a&&a->front()==UINT64_MAX&&a->back()==UINT64_MAX);
 bool rejected=false;try{construct_range_and(2,{{0,2,8}},3);}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'bitwise-or-constraint-count':r'''
 auto brute=[](int n,const vector<TripleOrRequirement>&q,int bits){long long answer=0;for(int mask=0;mask<(1<<(n*bits));++mask){vector<uint64_t>a(n);for(int i=0;i<n;++i)a[i]=(mask>>(i*bits))&((1<<bits)-1);bool valid=true;for(const auto&c:q)if((a[c.index[0]]|a[c.index[1]]|a[c.index[2]])!=c.value)valid=false;answer+=valid;}return answer;};
 for(int trial=0;trial<1300;++trial){int n=1+rng()%4,bits=1+rng()%3;vector<TripleOrRequirement>q(rng()%6);for(auto&c:q){for(auto&i:c.index)i=rng()%n;c.value=rng()%(1<<bits);}assert(count_triple_or_arrays(n,q,bits)==brute(n,q,bits));}
 assert(count_triple_or_arrays(4,{{{0,1,2},50},{{1,2,3},45}},60)==13);
 auto power=[](long long a,int e){long long r=1;for(int i=0;i<e;++i)r=r*a%1000000007;return r;};
 assert(count_triple_or_arrays(12,{},64)==power(2,12*64));
 assert(count_triple_or_arrays(12,{{{0,0,0},UINT64_MAX}},64)==power(2,11*64));
 assert(count_triple_or_arrays(3,{{{0,1,2},uint64_t{1}<<63}},64)==7);
 assert(count_triple_or_arrays(3,{{{0,1,2},0},{{0,1,2},1}},1)==0);
 bool rejected=false;try{count_triple_or_arrays(3,{{{0,1,2},8}},3);}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'carryfree-sum-xor-bound':r'''
 auto binary=[](int x){string s;do{s.push_back('0'+x%2);x/=2;}while(x);reverse(s.begin(),s.end());return s;};
 vector<long long>count(2001);for(int a=0;a<=2000;++a)for(int b=0;b+a<=2000;++b)if(a+b==(a^b))++count[a+b];
 long long prefix=0;for(int bound=0;bound<=2000;++bound){prefix+=count[bound];assert(count_carryfree_pairs_at_most(binary(bound))==prefix);assert(count_carryfree_pairs_at_most("000"+binary(bound))==prefix);}
 assert(count_carryfree_pairs_at_most("10")==5);assert(count_carryfree_pairs_at_most(string(19,'1'))==162261460);
 long long expected=1;for(int i=0;i<100001;++i)expected=3*expected%1000000007;
 assert(count_carryfree_pairs_at_most(string(100001,'1'))==expected);
 assert(count_carryfree_pairs_at_most(string(100001,'0'))==1);
 bool rejected=false;try{count_carryfree_pairs_at_most("102");}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'xor-popcount-construction':r'''
 for(int bits=1;bits<=8;++bits){set<tuple<int,int,uint64_t>>possible;for(uint64_t x=0;x<(1U<<bits);++x)for(uint64_t y=0;y<(1U<<bits);++y)possible.insert({popcount(x),popcount(y),x^y});for(int a=0;a<=bits;++a)for(int b=0;b<=bits;++b)for(uint64_t c=0;c<(1U<<bits);++c){auto result=construct_xor_popcounts(a,b,c,bits);assert(result.has_value()==possible.contains({a,b,c}));if(result){auto[x,y]=*result;assert(popcount(x)==a&&popcount(y)==b&&(x^y)==c);assert(x<(1U<<bits)&&y<(1U<<bits));}}}
 auto all=construct_xor_popcounts(64,64,0,64);assert(all&&all->first==UINT64_MAX&&all->second==UINT64_MAX);
 auto high=construct_xor_popcounts(1,0,uint64_t{1}<<63,64);assert(high&&high->first==(uint64_t{1}<<63)&&high->second==0);
 assert(!construct_xor_popcounts(64,64,UINT64_MAX,64));
 assert((construct_xor_popcounts(0,0,0,60)==optional<pair<uint64_t,uint64_t>>({0,0})));
 assert(!construct_xor_popcounts(34,56,998244353,60));
 bool rejected=false;try{construct_xor_popcounts(1,1,uint64_t{1}<<63,60);}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'bounded-xor-sum-maximum':r'''
 auto brute=[](const vector<uint64_t>&a,uint64_t k){unsigned __int128 best=0;for(uint64_t x=0;x<=k;++x){unsigned __int128 sum=0;for(auto value:a)sum+=x^value;best=max(best,sum);}return best;};
 for(int trial=0;trial<6000;++trial){vector<uint64_t>a(rng()%10);for(auto&x:a)x=rng()%128;uint64_t k=rng()%128;assert(maximum_bounded_xor_sum(a,k)==brute(a,k));}
 for(int trial=0;trial<1000;++trial){vector<uint64_t>a(1+rng()%10);for(auto&x:a)x=(uint64_t(rng())<<32)|rng();uint64_t k=rng()%50;assert(maximum_bounded_xor_sum(a,k)==brute(a,k));}
 assert(maximum_bounded_xor_sum({0,0,2},2)==5);
 assert(maximum_bounded_xor_sum({1,6,3},7)==14);
 assert(maximum_bounded_xor_sum({7,4,0,3},9)==46);
 assert(maximum_bounded_xor_sum({UINT64_MAX},0)==UINT64_MAX);
 assert(maximum_bounded_xor_sum({0},UINT64_MAX)==UINT64_MAX);
 vector<uint64_t>a(200000,0);assert(maximum_bounded_xor_sum(a,UINT64_MAX)==static_cast<unsigned __int128>(200000)*UINT64_MAX);
 vector<uint64_t>ends={0,UINT64_MAX};assert(maximum_bounded_xor_sum(ends,UINT64_MAX)==UINT64_MAX);
''',
'and-sum-disjoint-remainder':r'''
 for(uint64_t common=0;common<256;++common)for(uint64_t sum=0;sum<512;++sum){bool exists=false;for(uint64_t x=0;x<=sum;++x)if((x&(sum-x))==common){exists=true;break;}auto result=construct_and_sum(common,sum);assert(result.has_value()==exists);if(result){auto[x,y]=*result;assert((x&y)==common);assert(static_cast<unsigned __int128>(x)+y==sum);}}
 for(int trial=0;trial<20000;++trial){uint64_t x=(uint64_t(rng())<<31)|rng(),y=(uint64_t(rng())<<31)|rng();auto result=construct_and_sum(x&y,x+y);assert(result);assert((result->first&result->second)==(x&y));assert(static_cast<unsigned __int128>(result->first)+result->second==static_cast<unsigned __int128>(x)+y);}
 assert((construct_and_sum(0,UINT64_MAX)==optional<pair<uint64_t,uint64_t>>({0,UINT64_MAX})));
 assert(!construct_and_sum(UINT64_MAX,UINT64_MAX));
 uint64_t half=uint64_t{1}<<63;auto result=construct_and_sum(half-1,UINT64_MAX-1);assert(result&&result->first==half-1&&result->second==half-1);
 assert(!construct_and_sum(half,UINT64_MAX));
 assert((construct_and_sum(0,0)==optional<pair<uint64_t,uint64_t>>({0,0})));
''',
'minimum-cost-xor-generators':r'''
 auto closure=[](const vector<PricedXorMask>&a,unsigned subset){set<uint64_t>made{0};for(unsigned i=0;i<a.size();++i)if((subset>>i)&1U){vector<uint64_t>next;for(auto x:made)next.push_back(x^a[i].mask);made.insert(next.begin(),next.end());}return made;};
 for(int trial=0;trial<1600;++trial){int bits=1+rng()%4;vector<PricedXorMask>a(rng()%11);for(auto&x:a)x={rng()%(1U<<bits),rng()%30};optional<uint64_t>best;for(unsigned subset=0;subset<(1U<<a.size());++subset){uint64_t cost=0;for(unsigned i=0;i<a.size();++i)if((subset>>i)&1U)cost+=a[i].cost;if(closure(a,subset).size()==(1U<<bits)&&(!best||cost<*best))best=cost;}auto result=minimum_xor_generators(bits,a);assert(result.has_value()==best.has_value());if(result){assert(result->total_cost==*best);unsigned selected=0;uint64_t sum=0;assert(result->selected.size()==size_t(bits));for(auto i:result->selected){assert(i<a.size());assert(((selected>>i)&1U)==0);selected|=1U<<i;sum+=a[i].cost;}assert(sum==result->total_cost);assert(closure(a,selected).size()==(1U<<bits));}}
 assert(minimum_xor_generators(2,{{1,4},{2,5},{3,3}})->total_cost==7);
 vector<PricedXorMask>all(200000,{0,0});for(int b=0;b<64;++b)all[b]={uint64_t{1}<<b,1000000000000ULL};auto result=minimum_xor_generators(64,all);assert(result&&result->total_cost==64000000000000ULL&&result->selected.size()==64);
 assert(!minimum_xor_generators(64,{{UINT64_MAX,0}}));
 assert(!minimum_xor_generators(1,{}));
 assert(minimum_xor_generators(1,{{1,0},{1,1},{0,0}})->total_cost==0);
 bool rejected=false;try{minimum_xor_generators(63,{{uint64_t{1}<<63,0}});}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'carryfree-subarray-window':r'''
 auto brute=[](const vector<uint64_t>&a){uint64_t answer=0;for(size_t l=0;l<a.size();++l){unsigned __int128 sum=0;uint64_t x=0;for(size_t r=l;r<a.size();++r){sum+=a[r];x^=a[r];answer+=sum==x;}}return answer;};
 for(int n=0;n<=8;++n){int count=1;for(int i=0;i<n;++i)count*=4;for(int mask=0;mask<count;++mask){int rest=mask;vector<uint64_t>a(n);for(auto&x:a){x=rest%4;rest/=4;}assert(count_carryfree_subarrays(a)==brute(a));}}
 for(int trial=0;trial<3000;++trial){vector<uint64_t>a(rng()%40);for(auto&x:a)x=(uint64_t(rng())<<32)|rng();assert(count_carryfree_subarrays(a)==brute(a));}
 assert(count_carryfree_subarrays({2,5,4,6})==5);
 assert(count_carryfree_subarrays({UINT64_MAX,UINT64_MAX})==2);
 assert(count_carryfree_subarrays({uint64_t{1}<<63,1,uint64_t{1}<<63})==5);
 vector<uint64_t>zeros(2000000);assert(count_carryfree_subarrays(zeros)==2000000ULL*2000001/2);
 vector<uint64_t>all(2000000,UINT64_MAX);assert(count_carryfree_subarrays(all)==2000000);
'''
}
with tempfile.TemporaryDirectory(prefix='flowchartcp-bit-patterns-') as tmp:
    for id,body in checks.items():
        article=(ROOT/'src/content/docs/techniques'/f'{id}.mdx').read_text()
        snippets=re.findall(r'```cpp\n(.*?)\n```',article,re.S)
        assert len(snippets)==1,(id,len(snippets))
        source=Path(tmp)/(id+'.cpp');binary=Path(tmp)/id
        source.write_text('#include <bits/stdc++.h>\nusing namespace std;\n'+snippets[0]+'\nint main(){mt19937 rng(192837465);\n'+body+'\n}\n')
        result=subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stderr)
        subprocess.run([str(binary)],check=True,timeout=45)
        print(id+' PASS',flush=True)
