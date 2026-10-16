"""Compare published algebra snippets with direct definitions on small inputs.

The implementation under test is extracted from the article on every run. No
optimized implementation is copied into this fixture.
"""
from pathlib import Path
import concurrent.futures
import math
import os
import re
import shlex
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
COMMON = r'''
int main() {
    using namespace tested;
    mt19937_64 rng(381223);
    constexpr int oracle_mod = 998244353;
    auto oracle_power=[](long long a,unsigned long long exponent,int modulus=998244353) {
        long long result=1%modulus;
        a%=modulus;if(a<0)a+=modulus;
        while(exponent){if(exponent&1)result=result*a%modulus;a=a*a%modulus;exponent>>=1;}
        return int(result);
    };
    (void)rng;(void)oracle_mod;(void)oracle_power;
'''
CASES = {
'fps-inverse-newton': r'''
    auto check=[&](const vector<int>& f,int n) {
        auto inverse=fps_inverse(f,n);
        assert(inverse.size()==size_t(n));
        for(int degree=0;degree<n;++degree){long long coefficient=0;
            for(int i=0;i<=degree && i<int(f.size());++i)coefficient=(coefficient+1LL*f[i]*inverse[degree-i])%oracle_mod;
            assert(coefficient==(degree==0));
        }
    };
    for(int n:{0,1,2,3,4,5,7,8,9,15,16,17,31,32,33,63,64,65,127,128,129}) {
        check({1},n);check({oracle_mod-1},n);check({1,oracle_mod-1},n);
        for(int trial=0;trial<18;++trial){vector<int> f(1+rng()%150);for(auto& x:f)x=rng()%oracle_mod;f[0]=1+rng()%(oracle_mod-1);check(f,n);}
    }
    assert(fps_inverse({1,oracle_mod-1},10)==vector<int>(10,1));
''',
'fps-log-derivative': r'''
    auto direct=[&](const vector<int>& f,int n) {
        vector<int> inverse(n),expected(n);
        if(n==0)return expected;
        inverse[0]=1;
        for(int k=1;k<n;++k){long long sum=0;for(int i=1;i<=k && i<int(f.size());++i)sum=(sum+1LL*f[i]*inverse[k-i])%oracle_mod;inverse[k]=(oracle_mod-sum)%oracle_mod;}
        for(int k=1;k<n;++k){long long derivative=0;for(int i=1;i<=k && i<int(f.size());++i)derivative=(derivative+1LL*i*f[i]%oracle_mod*inverse[k-i])%oracle_mod;expected[k]=derivative*oracle_power(k,oracle_mod-2)%oracle_mod;}
        return expected;
    };
    for(int n:{0,1,2,3,7,8,9,15,16,17,31,32,33,63,64,65,127,128,129}) {
        assert(fps_logarithm({1},n)==vector<int>(n));
        for(int trial=0;trial<16;++trial){vector<int> f(1+rng()%150);for(auto& x:f)x=rng()%oracle_mod;f[0]=1;assert(fps_logarithm(f,n)==direct(f,n));}
    }
    auto actual=fps_logarithm({1,1},65);
    for(int k=1;k<65;++k){int value=oracle_power(k,oracle_mod-2);if(k%2==0)value=oracle_mod-value;assert(actual[k]==value);}
''',
'fps-exp-newton': r'''
    auto direct=[&](const vector<int>& f,int n) {
        vector<int> expected(n);if(!n)return expected;expected[0]=1;
        for(int k=1;k<n;++k){long long sum=0;for(int i=1;i<=k && i<int(f.size());++i)sum=(sum+1LL*i*f[i]%oracle_mod*expected[k-i])%oracle_mod;expected[k]=sum*oracle_power(k,oracle_mod-2)%oracle_mod;}
        return expected;
    };
    for(int n:{0,1,2,3,4,5,7,8,9,15,16,17,31,32,33,63,64,65,127,128,129}) {
        vector<int> constant(n);if(n)constant[0]=1;assert(fps_exponential({0},n)==constant);assert(fps_exponential({},n)==constant);
        for(int trial=0;trial<16;++trial){vector<int> f(1+rng()%150);for(auto& x:f)x=rng()%oracle_mod;f[0]=0;assert(fps_exponential(f,n)==direct(f,n));}
    }
    auto exponential=fps_exponential({0,1},129);long long factorial=1;
    for(int k=0;k<129;++k){if(k)factorial=factorial*k%oracle_mod;assert(exponential[k]==oracle_power(factorial,oracle_mod-2));}
''',
'linear-recurrence-bostan-mori': r'''
    for(int trial=0;trial<1200;++trial){int d=1+rng()%12,k=rng()%180;vector<int> initial(d),coefficient(d),sequence;
        for(auto& x:initial){x=rng()%oracle_mod;}for(auto& x:coefficient){x=rng()%oracle_mod;}sequence=initial;
        for(int index=d;index<=k;++index){long long next=0;for(int j=1;j<=d;++j)next=(next+1LL*coefficient[j-1]*sequence[index-j])%oracle_mod;sequence.push_back(next);}
        assert(recurrence_term(initial,coefficient,k)==sequence[k]);
        for(int i=0;i<d;++i)assert(recurrence_term(initial,coefficient,i)==initial[i]);
    }
    for(unsigned long long k:{0ULL,1ULL,2ULL,127ULL,128ULL,129ULL,1000000000000000000ULL,ULLONG_MAX}){
        assert(recurrence_term({37},{19},k)==1LL*37*oracle_power(19,k)%oracle_mod);
        assert(recurrence_term({37},{0},k)==(k==0 ? 37 : 0));
        assert(recurrence_term({1,1},{1,0},k)==1);
    }
''',
'subset-convolution-ranked': r'''
    for(int bits=0;bits<=8;++bits)for(int trial=0;trial<40;++trial){int size=1<<bits;vector<int> a(size),b(size),expected(size);
        for(auto& x:a){x=rng()%oracle_mod;}for(auto& x:b){x=rng()%oracle_mod;}
        for(int s=0;s<size;++s){long long value=0;for(int t=s;;t=(t-1)&s){value=(value+1LL*a[t]*b[s^t])%oracle_mod;if(t==0)break;}expected[s]=value;}
        assert(subset_convolution(a,b)==expected);
        assert(subset_convolution(b,a)==expected);
    }
    for(int bits=0;bits<=9;++bits){int size=1<<bits;vector<int> a(size,1),zero(size),delta(size);delta[0]=1;
        assert(subset_convolution(a,zero)==zero);assert(subset_convolution(a,delta)==a);
        auto actual=subset_convolution(a,a);for(int s=0;s<size;++s)assert(actual[s]==(1<<__builtin_popcount(unsigned(s))));
    }
''',
'xor-convolution-transform': r'''
    for(int bits=0;bits<=8;++bits)for(int trial=0;trial<35;++trial){int size=1<<bits;vector<int> a(size),b(size),expected(size);
        for(auto& x:a){x=rng()%oracle_mod;}for(auto& x:b){x=rng()%oracle_mod;}
        for(int i=0;i<size;++i)for(int j=0;j<size;++j)expected[i^j]=(expected[i^j]+1LL*a[i]*b[j])%oracle_mod;
        assert(xor_convolution(a,b)==expected);assert(xor_convolution(b,a)==expected);
    }
    for(int bits=0;bits<=10;++bits){int size=1<<bits;vector<int> a(size),zero(size),delta(size);for(auto& x:a)x=rng()%oracle_mod;delta[0]=1;
        assert(xor_convolution(a,zero)==zero);assert(xor_convolution(a,delta)==a);
        assert(xor_convolution(vector<int>(size,1),vector<int>(size,1))==vector<int>(size,size));
    }
''',
'binomial-convolution-factorials': r'''
    vector<vector<int>> binomial(260,vector<int>(260));binomial[0][0]=1;
    for(int n=1;n<260;++n){binomial[n][0]=1;for(int k=1;k<=n;++k)binomial[n][k]=(binomial[n-1][k-1]+binomial[n-1][k])%oracle_mod;}
    for(int trial=0;trial<800;++trial){vector<int> a(rng()%70),b(rng()%70);for(auto& x:a)x=rng()%oracle_mod;for(auto& x:b)x=rng()%oracle_mod;
        vector<int> expected(a.empty() || b.empty() ? 0 : a.size()+b.size()-1);
        for(int i=0;i<int(a.size());++i)for(int j=0;j<int(b.size());++j)expected[i+j]=(expected[i+j]+1LL*binomial[i+j][i]*a[i]%oracle_mod*b[j])%oracle_mod;
        assert(binomial_convolution(a,b)==expected);
    }
    vector<int> previous{1};
    for(int n=0;n<=129;++n){assert(stirling_second_row(n)==previous);vector<int> next(n+2);for(int k=1;k<=n+1;++k)next[k]=(previous[k-1]+(k<int(previous.size()) ? 1LL*k*previous[k] : 0))%oracle_mod;previous=next;}
''',
'multipoint-product-tree': r'''
    auto check=[&](const vector<int>& f,const vector<int>& points){vector<int> expected;
        for(int x:points){long long value=0;for(int i=int(f.size())-1;i>=0;--i)value=(value*x+f[i])%oracle_mod;expected.push_back(value);}
        assert(multipoint_evaluate(f,points)==expected);
    };
    check({},{});check({},vector<int>(16,0));check({1},{0,0,1,1,oracle_mod-1});
    for(int count:{0,1,2,3,7,8,9,15,16,17,31,32,33,63,64,65,127,128,129}){
        for(int trial=0;trial<12;++trial){vector<int> f(rng()%150),points(count);for(auto& x:f)x=rng()%oracle_mod;for(auto& x:points)x=(rng()%2 ? rng()%7 : rng()%oracle_mod);check(f,points);}
    }
    vector<int> f(130,oracle_mod-1);for(int count:{1,2,31,32,33,128,129}){check(f,vector<int>(count,0));check(f,vector<int>(count,1));}

    // The published remainder helper also supports nonmonic divisors.
    for(int trial=0;trial<1200;++trial) {
        vector<int> f(rng()%160),divisor(1+rng()%75);
        for(auto& x:f)x=rng()%oracle_mod;
        for(auto& x:divisor)x=rng()%oracle_mod;
        divisor.back()=1+rng()%(oracle_mod-1);
        auto expected=f;
        while(!expected.empty()&&expected.back()==0)expected.pop_back();
        int inverse=oracle_power(divisor.back(),oracle_mod-2);
        while(expected.size()>=divisor.size()) {
            int shift=expected.size()-divisor.size();long long coefficient=1LL*expected.back()*inverse%oracle_mod;
            for(int j=0;j<int(divisor.size());++j)expected[shift+j]=(expected[shift+j]-coefficient*divisor[j]%oracle_mod+oracle_mod)%oracle_mod;
            while(!expected.empty()&&expected.back()==0)expected.pop_back();
        }
        assert(polynomial_remainder(f,divisor)==expected);
    }

''',
'polynomial-taylor-shift': r'''
    vector<vector<int>> binomial(180,vector<int>(180));binomial[0][0]=1;
    for(int n=1;n<180;++n){binomial[n][0]=1;for(int k=1;k<=n;++k)binomial[n][k]=(binomial[n-1][k-1]+binomial[n-1][k])%oracle_mod;}
    auto check=[&](const vector<int>& a,int c){vector<int> expected(a.size());
        for(int i=0;i<int(a.size());++i)for(int k=0;k<=i;++k)expected[k]=(expected[k]+1LL*a[i]*binomial[i][k]%oracle_mod*oracle_power(c,i-k))%oracle_mod;
        assert(taylor_shift(a,c)==expected);assert(taylor_shift(a,0)==a);
    };
    for(int n:{0,1,2,3,7,8,9,15,16,17,31,32,33,63,64,65,127,128,129}){
        check(vector<int>(n,oracle_mod-1),oracle_mod-1);
        for(int trial=0;trial<12;++trial){vector<int> a(n);for(auto& x:a)x=rng()%oracle_mod;check(a,rng()%oracle_mod);}
    }
    for(int c:{INT_MIN,-1000000000,-998244353,-1,0,INT_MAX}) check({1,3,0,7,oracle_mod-1},c);
    assert(taylor_shift({1,0,1},3)==vector<int>({10,6,1}));
''',
'primitive-root-discrete-log': r'''
    auto direct=[](long long a,long long b,long long modulus)->optional<long long>{
        a%=modulus;if(a<0)a+=modulus;b%=modulus;if(b<0)b+=modulus;
        set<long long> visited;long long value=1%modulus,exponent=0;
        while(!visited.count(value)){if(value==b)return exponent;visited.insert(value);value=value*a%modulus;++exponent;}
        return nullopt;
    };
    for(long long modulus=1;modulus<=85;++modulus)for(long long a=0;a<modulus;++a)for(long long b=0;b<modulus;++b)assert(discrete_log(a,b,modulus)==direct(a,b,modulus));
    for(int trial=0;trial<8000;++trial){long long modulus=1+rng()%500,a=int(rng()%2001)-1000,b=int(rng()%2001)-1000;assert(discrete_log(a,b,modulus)==direct(a,b,modulus));}
    for(long long modulus=1;modulus<=100;++modulus)for(long long a:{LLONG_MIN,-1LL,0LL,1LL,LLONG_MAX})for(long long b:{LLONG_MIN,-1LL,0LL,1LL,LLONG_MAX})assert(discrete_log(a,b,modulus)==direct(a,b,modulus));
    assert(discrete_log(0,1,7)==0);assert(discrete_log(0,0,7)==1);assert(!discrete_log(0,2,7));
    assert(discrete_log(6,0,12)==2);assert(!discrete_log(2,3,8));assert(discrete_log(8,4,12)==2);
    for(long long modulus:{100000000LL,999999937LL})for(long long a:{2LL,7LL,99991LL})for(unsigned long long exponent:{0ULL,1ULL,127ULL,2000ULL}){
        long long b=oracle_power(a,exponent,int(modulus));optional<long long> expected;long long value=1%modulus;for(unsigned long long k=0;k<=exponent;++k){if(value==b){expected=k;break;}value=value*a%modulus;}
        assert(discrete_log(a,b,modulus)==expected);
    }
''',
'binomial-composite-prime-power': r'''
    for(int modulus:{1,2,4,8,9,12,16,25,27,32,36,49,64,72,100,125,243,729,1000,65536,999983,1000000}){
        BinomialComposite combination(modulus);vector<int> previous{1%modulus};
        for(unsigned long long n=0;n<=100;++n){for(unsigned long long k=0;k<=n+2;++k)assert(combination.choose(n,k)==(k<=n ? previous[k] : 0));vector<int> next(n+2);next[0]=1%modulus;for(unsigned long long k=1;k<=n+1;++k)next[k]=(previous[k-1]+(k<previous.size() ? previous[k] : 0))%modulus;previous=next;}
        for(const auto& row:vector<array<unsigned long long,4>>{ /* BIG_EXPECTATIONS */ })if(row[0]==unsigned(modulus)) {
            auto n=row[1],k=row[2];int expected=row[3];
            assert(combination.choose(n,k)==expected);assert(combination.choose(n,n-k)==expected);
        }
        assert(combination.choose(0,ULLONG_MAX)==0);
    }
''',
'floor-sum-euclidean': r'''
    auto floor_quotient=[](__int128 value,long long divisor){__int128 quotient=value/divisor;if(value%divisor<0)--quotient;return quotient;};
    auto check=[&](long long n,long long m,long long a,long long b){__int128 expected=0;for(long long i=0;i<n;++i)expected+=floor_quotient((__int128)a*i+b,m);assert(floor_sum_exact(n,m,a,b)==expected);};
    for(long long n=0;n<=12;++n)for(long long m=1;m<=12;++m)for(long long a=-12;a<=12;++a)for(long long b=-12;b<=12;++b)check(n,m,a,b);
    for(int trial=0;trial<15000;++trial){long long n=rng()%250,m=1+rng()%1000000000,a=static_cast<long long>(rng()),b=static_cast<long long>(rng());check(n,m,a,b);}
    for(long long a:{LLONG_MIN,LLONG_MIN+1,-1LL,0LL,1LL,LLONG_MAX})for(long long b:{LLONG_MIN,LLONG_MIN+1,-1LL,0LL,1LL,LLONG_MAX})for(long long m:{1LL,2LL,3LL,999999937LL,1000000000LL})check(200,m,a,b);
    constexpr long long large=1000000000LL;
    for(long long a:{LLONG_MIN,LLONG_MAX})for(long long b:{LLONG_MIN,LLONG_MAX})assert(floor_sum_exact(large,1,a,b)==(__int128)a*large*(large-1)/2+(__int128)b*large);
    assert(floor_sum_exact(large,large,large,-1)==(__int128)large*(large-1)/2-large);
    assert(floor_sum_exact(large,large,-large,1)==-(__int128)large*(large-1)/2);
    assert(floor_sum_exact(large,large,1,0)==0);assert(floor_sum_exact(large,large,1,1)==1);
    assert(floor_sum_exact(0,large,LLONG_MIN,LLONG_MAX)==0);
''',
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
    if slug == 'binomial-composite-prime-power':
        # Python's unbounded exact integer binomial coefficients are an oracle
        # independent of prime-power factorials and need no C++ dependency.
        expected = []
        for modulus in [1,2,4,8,9,12,16,25,27,32,36,49,64,72,100,125,243,729,1000,65536,999983,1000000]:
            for n in [2**16-1,2**16,2**16+1,2**18-1,2**18+17,10**9,10**18-1,10**18]:
                for k in [0,1,2,3,5,17,29,31,64,127,128,129,257,1023]:
                    expected.append(f'{{{modulus}ULL,{n}ULL,{k}ULL,{math.comb(n,k) % modulus}ULL}}')
        body = body.replace('/* BIG_EXPECTATIONS */', ','.join(expected))
    source = '\n'.join(includes) + '\nusing namespace std;\nnamespace tested {\n' + '\n'.join(code) + '\n}\n' + COMMON + body + '\n}\n'
    try:
        with tempfile.TemporaryDirectory(prefix='algebra-coverage-') as directory:
            cpp = Path(directory) / 'test.cpp'
            executable = Path(directory) / 'test'
            cpp.write_text(source)
            command = shlex.split(os.environ.get('CXX', 'g++')) + [
                '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror',
                '-I', str(ROOT / 'vendor/ac-library'), str(cpp), '-o', str(executable),
            ]
            compiled = subprocess.run(command, capture_output=True, text=True, timeout=60)
            if compiled.returncode:
                return slug, False, compiled.stderr
            executed = subprocess.run([str(executable)], capture_output=True, text=True, timeout=30)
            return slug, executed.returncode == 0, executed.stderr
    except (OSError, subprocess.TimeoutExpired) as error:
        return slug, False, str(error)


if __name__ == '__main__':
    assert len(CASES) == 12, 'Every one of the 12 published articles needs its own property test'
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, CASES.items()))
    for slug, passed, output in results:
        print(slug, 'PASS' if passed else 'FAIL', output)
    if any(not passed for _, passed, _ in results):
        raise SystemExit(1)
