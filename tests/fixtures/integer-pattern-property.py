from pathlib import Path
import re, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
checks={
'decimal-substring-divisibility':r'''
 auto brute=[](const string&s,int mod){long long answer=0;for(int l=0;l<int(s.size());++l){int value=0;for(int r=l;r<int(s.size());++r){value=(value*10+s[r]-'0')%mod;if(value==0)++answer;}}return answer;};
 assert(count_divisible_decimal_substrings("3543",3)==6);assert(count_divisible_decimal_substrings("2020",2)==10);
 assert(count_divisible_decimal_substrings("33883322005544116655",11)==68);
 for(int trial=0;trial<2000;++trial){string s(rng()%35,'0');for(auto&c:s)c='0'+rng()%10;for(int mod=1;mod<=40;++mod)if(gcd(mod,10)==1||mod==2||mod==5)assert(count_divisible_decimal_substrings(s,mod)==brute(s,mod));}
 bool rejected=false;try{count_divisible_decimal_substrings("20",4);}catch(const invalid_argument&){rejected=true;}assert(rejected);
 assert(count_divisible_decimal_substrings(string(200000,'0'),9973)==200000LL*200001/2);
''',
'lcm-removal-unique-maximum':r'''
 auto brute=[](const vector<vector<pair<int,int>>>&f){set<vector<pair<int,int>>>outputs;for(int skip=0;skip<int(f.size());++skip){map<int,int>exponents;for(int i=0;i<int(f.size());++i)if(i!=skip)for(auto[p,e]:f[i])exponents[p]=max(exponents[p],e);vector<pair<int,int>>out(exponents.begin(),exponents.end());outputs.insert(out);}return int(outputs.size());};
 assert(distinct_lcms_after_removing_one({{{7,2}},{{2,2},{5,1}},{{5,1}},{{2,1},{7,1}}})==3);
 assert(distinct_lcms_after_removing_one({{{998244353,1000000000}}})==1);
 for(int trial=0;trial<2500;++trial){int n=1+rng()%14;vector<vector<pair<int,int>>>f(n);for(auto&row:f)for(int p:{2,3,5,7,11}){int e=rng()%5;if(e)row.push_back({p,e});}assert(distinct_lcms_after_removing_one(f)==brute(f));}
 assert(distinct_lcms_after_removing_one(vector<vector<pair<int,int>>>(200000,{{2,1000000000}}))==1);
''',
'squarefree-product-pairs':r'''
 auto brute=[](const vector<int>&a){long long answer=0;for(int i=0;i<int(a.size());++i)for(int j=i+1;j<int(a.size());++j){long long p=1LL*a[i]*a[j],r=sqrtl(p);while((r+1)*(r+1)<=p)++r;while(r*r>p)--r;if(r*r==p)++answer;}return answer;};
 assert(count_square_product_pairs({0,3,2,8,12})==6);assert(count_square_product_pairs({2,2,4,6,3,100,100,25})==7);
 for(int trial=0;trial<3000;++trial){vector<int>a(rng()%40);for(auto&x:a)x=rng()%500;assert(count_square_product_pairs(a)==brute(a));}
 assert(count_square_product_pairs(vector<int>(200000,0))==200000LL*199999/2);
 assert(count_square_product_pairs(vector<int>(200000,200000))==200000LL*199999/2);
 assert(count_square_product_pairs({1,4,9,16})==6);
''',
'gcd-pairs-exclude-divides':r'''
 auto brute=[](int l,int r){long long result=0;for(int x=l;x<=r;++x)for(int y=l;y<=r;++y){int g=gcd(x,y);if(g>1&&x/g>1&&y/g>1)++result;}return result;};
 for(int r=1;r<=160;++r)for(int l=1;l<=r;++l)assert(count_nondividing_gcd_pairs(l,r)==brute(l,r));
 assert(count_nondividing_gcd_pairs(3,7)==2);assert(count_nondividing_gcd_pairs(4,10)==12);
 assert(count_nondividing_gcd_pairs(1,1000000)==392047955148LL);
 assert(count_nondividing_gcd_pairs(999999,1000000)==0);
''',
'prime-mod-power-tower':r'''
 auto direct=[](unsigned n,unsigned k,unsigned long long m){unsigned long long exponent=1;for(unsigned i=0;i<n;++i)exponent*=k;unsigned long long answer=1;for(unsigned long long i=0;i<exponent;++i)answer=answer*(m%998244353)%998244353;return answer;};
 for(unsigned n=0;n<=5;++n)for(unsigned k=0;k<=7;++k)for(unsigned long long m:{0ULL,1ULL,2ULL,5ULL,998244353ULL,1996488706ULL,998244354ULL})assert(prime_mod_power_tower(n,k,m)==direct(n,k,m));
 assert(prime_mod_power_tower(2,2,2)==16);assert(prime_mod_power_tower(3,14,15926535)==109718301);
 assert(prime_mod_power_tower(1,998244352,998244353)==0);
 assert(prime_mod_power_tower(1000000000000000000ULL,1000000000000000000ULL,0)==0);
 assert(prime_mod_power_tower(1,0,0)==1);assert(prime_mod_power_tower(0,0,0)==0);
 assert(integer_power_mod(ULLONG_MAX,2,ULLONG_MAX-1)==1);
 bool rejected=false;try{integer_power_mod(2,3,0);}catch(const invalid_argument&){rejected=true;}assert(rejected);
''',
'half-multiple-two-adic':r'''
 auto brute=[](const vector<long long>&a,long long upper){long long result=0;for(long long x=1;x<=upper;++x){bool good=true;for(auto value:a){long long half=value/2;if(x%half||x/half%2==0)good=false;}result+=good;}return result;};
 assert(count_half_odd_multiples({6,10},50)==2);assert(count_half_odd_multiples({14,22,40},100)==0);
 assert(count_half_odd_multiples({6,6,2,6,2},1000000000)==166666667);
 for(int trial=0;trial<4000;++trial){vector<long long>a(1+rng()%10);for(auto&x:a)x=2*(1+rng()%30);long long upper=rng()%250;assert(count_half_odd_multiples(a,upper)==brute(a,upper));}
 assert(count_half_odd_multiples(vector<long long>(100000,2),1000000000000000000LL)==500000000000000000LL);
 assert(count_half_odd_multiples({999999998,999999994},1000000000)==0);
''',
'factorial-divisibility-threshold':r'''
 auto brute=[](long long k){long long value=1;for(long long n=1;;++n){value=value*n%k;if(value==0)return n;}};
 for(int k=1;k<=12000;++k)assert(minimum_positive_factorial_multiple(k)==brute(k));
 assert(minimum_positive_factorial_multiple(30)==5);assert(minimum_positive_factorial_multiple(280)==7);
 assert(minimum_positive_factorial_multiple(123456789011LL)==123456789011LL);
 assert(minimum_positive_factorial_multiple(1000000000000LL)==50);
 assert(minimum_positive_factorial_multiple(549755813888LL)==42);
''',
'decimal-length-rank-sum':r'''
 long long prefix=0;unsigned long long power=1;
 for(unsigned long long n=0;n<=100000;++n){if(n>=power*10)power*=10;if(n)prefix+=n-power+1;for(long long mod:{1LL,2LL,7LL,1000LL,998244353LL})assert(decimal_length_rank_sum(n,mod)==prefix%mod);}
 assert(decimal_length_rank_sum(16)==73);
 auto block_value=[](unsigned long long n,long long mod){__int128 sum=0;for(unsigned long long left=1;left<=n;){unsigned long long right=min(n,left*10-1),count=right-left+1;sum+=(__int128)count*(count+1)/2;if(left>n/10)break;left*=10;}return static_cast<long long>(sum%mod);};
 for(unsigned long long n:{9ULL,10ULL,99ULL,100ULL,999ULL,1000ULL,999999999999999999ULL,1000000000000000000ULL})for(long long mod:{2LL,8LL,998244353LL,1000000000LL})assert(decimal_length_rank_sum(n,mod)==block_value(n,mod));
'''
}
with tempfile.TemporaryDirectory(prefix='flowchartcp-integer-patterns-') as tmp:
    for id,body in checks.items():
        article=(ROOT/'src/content/docs/techniques'/f'{id}.mdx').read_text()
        code=re.findall(r'```cpp\n(.*?)\n```',article,re.S)[0]
        source=Path(tmp)/(id+'.cpp');binary=Path(tmp)/id
        source.write_text('#include <bits/stdc++.h>\nusing namespace std;\n'+code+'\nint main(){mt19937 rng(1029384756);\n'+body+'\n}\n')
        result=subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stderr)
        subprocess.run([str(binary)],check=True,timeout=45)
        print(id+' PASS',flush=True)
