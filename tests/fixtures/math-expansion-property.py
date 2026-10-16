"""Compare the actual 13 published C++ snippets with small independent models."""
from pathlib import Path
import concurrent.futures
import json
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
COMMON = r'''
int main() {
    using namespace tested;
    mt19937_64 rng(195193);
    auto absolute=[](__int128 x){return x<0 ? -x : x;};
    (void)absolute;
'''
CASES = {
'digit-sum-residue-dp': r'''
    for(int trial=0;trial<800;++trial) {
        int upper=rng()%15000,d=1+rng()%35;long long mod=1+rng()%100000;
        long long expected=0;
        for(int x=1;x<=upper;++x){int sum=0;for(int n=x;n;n/=10)sum+=n%10;expected+=sum%d==0;}
        string limit=(rng()%2 ? "000" : "")+to_string(upper);
        assert(count_digit_sum_mod(limit,d,mod)==expected%mod);
    }
    assert(count_digit_sum_mod("0",1)==0);
    assert(count_digit_sum_mod("9999",40)==0);
    for(int mod:{1,2,6,97})assert(count_digit_sum_mod("987654321",1,mod)==987654321LL%mod);
''',
'subset-coprime-small-primes': r'''
    for(int trial=0;trial<450;++trial) {
        long long a=1+rng()%200;int width=rng()%12,n=width+1;
        unsigned long long expected=0;
        for(unsigned mask=0;mask<(1u<<n);++mask){bool valid=true;for(int i=0;i<n;++i)if(mask>>i&1)for(int j=0;j<i;++j)if((mask>>j&1) && gcd(a+i,a+j)!=1)valid=false;expected+=valid;}
        assert(count_pairwise_coprime_interval(a,a+width)==expected);
    }
    assert(count_pairwise_coprime_interval(1,1)==2);
    assert(count_pairwise_coprime_interval(1000000000000000000LL,1000000000000000000LL)==2);
    assert(count_pairwise_coprime_interval(999999999999999999LL,1000000000000000000LL)==4);
''',
'linear-congruence-gcd': r'''
    for(long long m=1;m<=40;++m)for(long long a=-40;a<=40;++a)for(long long b=-30;b<=30;++b) {
        optional<long long> expected;
        for(long long x=0;x<m;++x)if(((a*x-b)%m+m)%m==0){expected=x;break;}
        auto actual=least_congruence_solution(a,b,m);
        assert(actual==expected);
        if(actual)assert(((__int128)a*(*actual)-b)%m==0);
    }
    assert(least_congruence_solution(0,0,1)==0);
    assert(least_congruence_solution(0,1,12)==nullopt);
    assert(least_congruence_solution(LLONG_MAX-1,LLONG_MAX-2,LLONG_MAX)==2);
''',
'crt-noncoprime': r'''
    for(long long m=1;m<=24;++m)for(long long n=1;n<=24;++n)for(int trial=0;trial<20;++trial) {
        long long a=int(rng()%100)-50,b=int(rng()%100)-50,period=lcm(m,n);
        optional<long long> expected;
        for(long long t=0;t<period;++t)if(((t-a)%m+m)%m==0 && ((t-b)%n+n)%n==0){expected=t;break;}
        auto actual=combine_two_congruences(a,m,b,n);
        assert(actual.has_value()==expected.has_value());
        if(actual){assert(actual->residue==*expected && actual->modulus==period);assert((actual->residue-a)%m==0 && (actual->residue-b)%n==0);}
    }
    auto large=combine_two_congruences(7,4000000007LL,7,4000000009LL);
    assert(large && large->residue==7 && large->modulus==(__int128)4000000007LL*4000000009LL);
    assert(!combine_two_congruences(0,6,1,10));
''',
'lattice-pick-area': r'''
    auto classify=[](const vector<pair<long long,long long>>& poly,long long x,long long y){
        int winding=0;
        for(int i=0;i<int(poly.size());++i){auto [ax,ay]=poly[i];auto [bx,by]=poly[(i+1)%poly.size()];long long cross=(bx-ax)*(y-ay)-(by-ay)*(x-ax);
            if(cross==0 && min(ax,bx)<=x && x<=max(ax,bx) && min(ay,by)<=y && y<=max(ay,by))return 1;
            if(ay<=y && by>y && cross>0)++winding;
            if(ay>y && by<=y && cross<0)--winding;
        }
        return winding==0 ? 0 : 2;
    };
    auto check=[&](vector<pair<long long,long long>> poly){
        for(int orientation=0;orientation<2;++orientation){long long inside=0,boundary=0,xlo=poly[0].first,xhi=xlo,ylo=poly[0].second,yhi=ylo;
            for(auto [x,y]:poly){xlo=min(xlo,x);xhi=max(xhi,x);ylo=min(ylo,y);yhi=max(yhi,y);}
            for(long long x=xlo;x<=xhi;++x)for(long long y=ylo;y<=yhi;++y){int position=classify(poly,x,y);inside+=position==2;boundary+=position==1;}
            auto actual=polygon_lattice_counts(poly);assert(actual.first==inside && actual.second==boundary);
            reverse(poly.begin(),poly.end());
        }
    };
    check({{0,0},{4,0},{2,1},{4,4},{0,4}});
    check({{-3,-2},{2,-1},{-1,4}});
    for(int trial=0;trial<400;++trial){long long a=2+rng()%7,d=2+rng()%7,c=1+rng()%(a-1),b=1+rng()%(d-1),tx=int(rng()%9)-4,ty=int(rng()%9)-4;
        vector<pair<long long,long long>> poly{{0,0},{a,0},{a,b},{c,b},{c,d},{0,d}};
        for(auto& p:poly){p.first+=tx;p.second+=ty;}check(poly);
    }
    auto big=polygon_lattice_counts({{-1000000000LL,-1000000000LL},{1000000000LL,-1000000000LL},{1000000000LL,1000000000LL},{-1000000000LL,1000000000LL}});
    assert(big.first==(__int128)1999999999LL*1999999999LL && big.second==8000000000LL);
''',
'rectangle-union-sweep': r'''
    for(int trial=0;trial<900;++trial){int n=rng()%15;vector<array<long long,4>> rectangles;set<pair<int,int>> covered;
        for(int i=0;i<n;++i){int x1=int(rng()%11)-5,x2=int(rng()%11)-5,y1=int(rng()%11)-5,y2=int(rng()%11)-5;if(x1>x2)swap(x1,x2);if(y1>y2)swap(y1,y2);
            rectangles.push_back({x1,y1,x2,y2});if(rng()%4==0)rectangles.push_back(rectangles.back());
            for(int x=x1;x<x2;++x)for(int y=y1;y<y2;++y)covered.insert({x,y});
        }
        assert(rectangle_union_area(rectangles)==static_cast<long long>(covered.size()));
        reverse(rectangles.begin(),rectangles.end());assert(rectangle_union_area(rectangles)==static_cast<long long>(covered.size()));
    }
    assert(rectangle_union_area({{0,0,1,1},{1,0,2,1}})==2);
    assert(rectangle_union_area({{-1000000000000LL,-1000000000000LL,1000000000000LL,1000000000000LL}})==(__int128)2000000000000LL*2000000000000LL);
''',
'manhattan-transform': r'''
    for(int trial=0;trial<1500;++trial){int n=rng()%40;vector<pair<long long,long long>> p;for(int i=0;i<n;++i)p.push_back({int(rng()%101)-50,int(rng()%101)-50});if(!p.empty() && rng()%2)p.push_back(p.front());
        __int128 expected=0;for(auto [x,y]:p)for(auto [u,v]:p)expected=max(expected,absolute((__int128)x-u)+absolute((__int128)y-v));
        assert(maximum_manhattan_distance(p)==expected);
    }
    vector<pair<long long,long long>> p{{LLONG_MIN,LLONG_MIN},{LLONG_MAX,LLONG_MAX}};
    assert(maximum_manhattan_distance(p)==2*((__int128)LLONG_MAX-LLONG_MIN));
''',
'circle-square-distance': r'''
    for(int trial=0;trial<6000;++trial){IntegerCircle a{int(rng()%21)-10,int(rng()%21)-10,int(rng()%11)},b{int(rng()%21)-10,int(rng()%21)-10,int(rng()%11)};
        long double distance=hypotl(a.x-b.x,a.y-b.y);
        bool expected=distance+min(a.r,b.r)>=max(a.r,b.r) && distance<=a.r+b.r;
        assert(circumference_intersects(a,b)==expected);
        assert(circumference_intersects(b,a)==expected);
        int x=int(rng()%21)-10,y=int(rng()%21)-10;
        assert(point_on_circumference(a,x,y)==(hypotl(a.x-x,a.y-y)==a.r));
    }
    assert(circumference_intersects({0,0,3},{6,0,3}));
    assert(circumference_intersects({0,0,5},{3,0,2}));
    assert(circumference_intersects({0,0,5},{0,0,5}));
    assert(!circumference_intersects({0,0,5},{0,0,4}));
    assert(!circumference_intersects({0,0,5},{2,0,2}));
    assert(circumference_intersects({0,0,0},{0,0,0}));
    assert(circumference_intersects({-1000000000LL,0,1000000000LL},{1000000000LL,0,1000000000LL}));
    assert(point_on_circumference({1000000000LL,1000000000LL,1000000000LL},0,1000000000LL));
''',
'knapsack-bitset-shift': r'''
    auto check=[&](const vector<int>& a,int limit){vector<bool> expected(limit+1);for(unsigned mask=0;mask<(1u<<a.size());++mask){int sum=0;for(int i=0;i<int(a.size());++i)if(mask>>i&1)sum+=a[i];if(sum<=limit)expected[sum]=true;}
        auto actual=subset_sum_bits(a,limit);assert(actual.size()==size_t(limit/64+1));
        for(int s=0;s<=limit;++s)assert(bool(actual[s/64]>>(s%64)&1)==expected[s]);
        for(int s=limit+1;s<int(actual.size()*64);++s)assert(!(actual[s/64]>>(s%64)&1));
    };
    for(int trial=0;trial<700;++trial){vector<int> a(rng()%12);for(int& x:a)x=rng()%131;check(a,rng()%350);}
    for(int limit:{0,1,62,63,64,65,66,127,128,129,256})check({0,1,63,64,65,128},limit);
    check({},0);check({0,0,0},0);
''',
'subset-sum-repeated-binary': r'''
    auto check=[&](const vector<pair<int,long long>>& items,int limit){vector<bool> expected(limit+1);
        auto enumerate=[&](auto&& self,int i,long long sum)->void{if(i==int(items.size())){if(sum<=limit)expected[sum]=true;return;}auto [w,c]=items[i];for(long long take=0;take<=c;++take){if(sum+take*w>limit)break;self(self,i+1,sum+take*w);}};
        enumerate(enumerate,0,0);auto actual=bounded_subset_sum_bits(items,limit);
        for(int s=0;s<=limit;++s)assert(bool(actual[s/64]>>(s%64)&1)==expected[s]);
        for(int s=limit+1;s<int(actual.size()*64);++s)assert(!(actual[s/64]>>(s%64)&1));
    };
    for(int trial=0;trial<900;++trial){vector<pair<int,long long>> items(rng()%7);for(auto& [w,c]:items){w=rng()%75;c=rng()%5;}check(items,rng()%260);}
    for(int limit:{0,63,64,65,127,128,129})check({{0,3},{1,0},{63,3},{64,2},{65,3}},limit);
    auto actual=bounded_subset_sum_bits({{0,LLONG_MAX},{3,LLONG_MAX},{64,LLONG_MAX}},400);
    for(int s=0;s<=400;++s){bool expected=false;for(int k=0;k*64<=s;++k)if((s-k*64)%3==0)expected=true;assert(bool(actual[s/64]>>(s%64)&1)==expected);}
''',
'matrix-walk-sum-block': r'''
    auto independent_multiply=[](const Matrix& a,const Matrix& b,long long mod){int d=a.size();Matrix c(d,vector<long long>(d));for(int row=0;row<d;++row)for(int col=0;col<d;++col){__int128 sum=0;for(int k=0;k<d;++k)sum=(sum+(__int128)a[row][k]*b[k][col])%mod;c[row][col]=sum;}return c;};
    for(int trial=0;trial<700;++trial){int d=rng()%5,n=rng()%40;long long mod=vector<long long>{1,2,6,12,97,1000,LLONG_MAX}[rng()%7];Matrix a(d,vector<long long>(d));for(auto& row:a)for(auto& x:row)x=int(rng()%101)-50;
        Matrix normalized=a;for(auto& row:normalized)for(auto& x:row){x%=mod;if(x<0)x+=mod;}
        Matrix power(d,vector<long long>(d)),sum(d,vector<long long>(d));for(int i=0;i<d;++i)power[i][i]=1%mod;
        for(int step=0;step<n;++step){for(int i=0;i<d;++i)for(int j=0;j<d;++j)sum[i][j]=((__int128)sum[i][j]+power[i][j])%mod;power=independent_multiply(power,normalized,mod);}
        auto actual=matrix_power_and_sum(a,n,mod);assert(actual.first==power && actual.second==sum);
    }
    Matrix a{{1,1},{0,1}},b{{1,0},{1,1}};assert(independent_multiply(a,b,12)!=independent_multiply(b,a,12));
    for(long long mod:{1LL,6LL,1000LL,LLONG_MAX}){unsigned long long n=1000000000000ULL;auto result=matrix_power_and_sum(a,n,mod);assert(result.first==Matrix({{1%mod,(long long)(n%mod)},{0,1%mod}}));assert(result.second==Matrix({{(long long)(n%mod),(long long)((__int128)n*(n-1)/2%mod)},{0,(long long)(n%mod)}}));}
    auto full=matrix_power_and_sum({{1}},ULLONG_MAX,97);assert(full.first[0][0]==1 && full.second[0][0]==ULLONG_MAX%97);
''',
'cyclic-dp-first-state': r'''
    for(int trial=0;trial<1600;++trial){int n=rng()%13;vector<long long> cost(n);for(auto& x:cost)x=rng()%20;long long expected=LLONG_MAX;
        for(unsigned mask=0;mask<(1u<<n);++mask){bool valid=true;long long total=0;for(int i=0;i<n;++i){if(mask>>i&1)total+=cost[i];if(!(mask>>i&1) && !(mask>>((i+1)%n)&1))valid=false;}if(valid)expected=min(expected,total);}
        assert(minimum_cycle_cover_cost(cost)==expected);
    }
    assert(minimum_cycle_cover_cost({})==0);
    assert(minimum_cycle_cover_cost({7})==7);
    assert(minimum_cycle_cover_cost({9,4})==4);
    assert(minimum_cycle_cover_cost({0,0,0})==0);
    assert(minimum_cycle_cover_cost({(1LL<<60)-1,(1LL<<60)-1})==(1LL<<60)-1);
''',
'rectangle-split-dp': r'''
    auto enumerate=[&](const vector<vector<long long>>& weights){
        auto all_trees=[&](auto&& self,int top,int bottom,int left,int right)->vector<long long>{if(bottom-top==1 && right-left==1)return {0};long long mass=0;for(int y=top;y<bottom;++y)for(int x=left;x<right;++x)mass+=weights[y][x];vector<long long> plans;
            for(int cut=top+1;cut<bottom;++cut){auto first=self(self,top,cut,left,right),second=self(self,cut,bottom,left,right);for(auto x:first)for(auto y:second)plans.push_back(mass+x+y);}
            for(int cut=left+1;cut<right;++cut){auto first=self(self,top,bottom,left,cut),second=self(self,top,bottom,cut,right);for(auto x:first)for(auto y:second)plans.push_back(mass+x+y);}
            return plans;};
        auto plans=all_trees(all_trees,0,weights.size(),0,weights[0].size());return *min_element(plans.begin(),plans.end());
    };
    assert(minimum_rectangle_split_cost({})==0);assert(minimum_rectangle_split_cost({{}})==0);
    for(int h=1;h<=3;++h)for(int w=1;w<=3;++w)for(int trial=0;trial<200;++trial){vector<vector<long long>> weights(h,vector<long long>(w));for(auto& row:weights)for(auto& x:row)x=rng()%8;assert(minimum_rectangle_split_cost(weights)==enumerate(weights));}
    assert(minimum_rectangle_split_cost({{123456789}})==0);
    assert(minimum_rectangle_split_cost({{1000000000000LL,2000000000000LL}})==3000000000000LL);
'''
}


def run(item):
    slug, body = item
    article = (ROOT / 'src/content/docs/techniques' / f'{slug}.mdx').read_text()
    snippets = re.findall(r'```cpp\n(.*?)```', article, re.S)
    if len(snippets) != 1:
        return slug, False, f'Expected exactly one published implementation; got {len(snippets)}'
    includes = []
    code = []
    for line in snippets[0].splitlines():
        (includes if line.startswith('#include ') else code).append(line)
    source = '\n'.join(includes) + '\nusing namespace std;\nnamespace tested {\n' + '\n'.join(code) + '\n}\n' + COMMON + body + '\n}\n'
    with tempfile.TemporaryDirectory(prefix='math-expansion-') as directory:
        cpp = Path(directory) / 'test.cpp'
        executable = Path(directory) / 'test'
        cpp.write_text(source)
        compiled = subprocess.run([os.environ.get('CXX', 'g++'), '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', str(cpp), '-o', str(executable)], capture_output=True, text=True, timeout=60)
        if compiled.returncode:
            return slug, False, compiled.stderr
        executed = subprocess.run([str(executable)], capture_output=True, text=True, timeout=30)
        return slug, executed.returncode == 0, executed.stderr


if __name__ == '__main__':
    metadata = json.loads((ROOT / 'data/math-expansion-problem-features.json').read_text())
    assert {row['techniqueId'] for row in metadata} == set(CASES), 'Every published article must have a test'
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, CASES.items()))
    for slug, passed, output in results:
        print(slug, 'PASS' if passed else 'FAIL', output)
    if any(not passed for _, passed, _ in results):
        raise SystemExit(1)
