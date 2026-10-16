"""Exercise the actual C++ code published in every string-coverage article.

Each snippet is extracted from MDX and placed in its own namespace and translation
unit. Expected values come from direct enumeration, not another optimized method.
"""
from pathlib import Path
import concurrent.futures
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
COMMON = r'''
int main() {
    using namespace tested;
    mt19937 rng(432835);
    auto random_string=[&](int n,int sigma) {string s;while(n--)s+=char('a'+rng()%sigma);return s;};
    (void)random_string;
'''
CASES = {
'prefix-border-occurrences': r'''
    for(int n=0;n<=10;++n) for(int mask=0;mask<(1<<n);++mask) {
        string s;for(int i=0;i<n;++i)s+=char('a'+(mask>>i&1));
        vector<pair<int,long long>> expected;
        for(int length=1;length<=n;++length) if(s.substr(0,length)==s.substr(n-length)) {
            long long count=0;for(int at=0;at+length<=n;++at)count+=s.substr(at,length)==s.substr(0,length);
            expected.push_back({length,count});
        }
        assert(border_occurrences(s)==expected);
    }
''',
'period-from-border': r'''
    assert(period_lengths("abcab")==vector<int>({3,5}));
    assert(exact_repeat_period("abcab")==5);
    for(int n=0;n<=11;++n) for(int mask=0;mask<(1<<n);++mask) {
        string s;for(int i=0;i<n;++i)s+=char('a'+(mask>>i&1));
        vector<int> periods;int exact=n;
        for(int p=1;p<=n;++p) {
            bool valid=true;for(int i=p;i<n;++i)if(s[i]!=s[i-p])valid=false;
            if(valid){periods.push_back(p);if(n%p==0)exact=min(exact,p);}
        }
        assert(period_lengths(s)==periods);
        assert(exact_repeat_period(s)==exact);
    }
''',
'z-concatenate-boundary': r'''
    for(int trial=0;trial<2000;++trial) {
        int n=rng()%15,m=rng()%12;string text,pattern;
        for(int i=0;i<n;++i)text+=char(vector<int>{0,35,97,128,255}[rng()%5]);
        for(int i=0;i<m;++i)pattern+=char(vector<int>{0,35,97,128,255}[rng()%5]);
        vector<int> expected;
        for(int at=0;at+m<=n;++at)if(text.substr(at,m)==pattern)expected.push_back(at);
        assert(exact_match_positions(text,pattern)==expected);
    }
    assert(exact_match_positions("aaaaa","aaa")==vector<int>({0,1,2}));
''',
'lcp-distinct-substrings': r'''
    for(int n=0;n<=10;++n) for(int mask=0;mask<(1<<n);++mask) {
        string s;for(int i=0;i<n;++i)s+=char('a'+(mask>>i&1));
        set<string> all;
        for(int l=0;l<n;++l)for(int r=l+1;r<=n;++r)all.insert(s.substr(l,r-l));
        assert(count_distinct_substrings(s)==static_cast<long long>(all.size()));
    }
    assert(count_distinct_substrings(string(100000,'a'))==100000);
''',
'lcp-repeated-substring': r'''
    for(int trial=0;trial<1200;++trial) {
        string s=random_string(rng()%14,3);int n=s.size();
        map<string,int> count;
        for(int l=0;l<n;++l)for(int r=l+1;r<=n;++r)++count[s.substr(l,r-l)];
        for(int k=1;k<=n+2;++k) {
            int best=0;for(auto [word,c]:count)if(c>=k)best=max(best,int(word.size()));
            auto answer=longest_k_repeated_substring(s,k);
            assert(int(answer.size())==best);
            assert(answer.empty() || count[answer]>=k);
        }
    }
    assert(longest_k_repeated_substring("aaaa",2)=="aaa");
''',
'palindrome-radius-range': r'''
    for(int n=0;n<=11;++n) for(int mask=0;mask<(1<<n);++mask) {
        string s;for(int i=0;i<n;++i)s+=char('a'+(mask>>i&1));
        PalindromeRanges index(s);
        for(int l=0;l<=n;++l)for(int r=l;r<=n;++r) {
            string part=s.substr(l,r-l),reversed=part;reverse(reversed.begin(),reversed.end());
            assert(index.is_palindrome(l,r)==(part==reversed));
        }
        for(int c=0;c<n;++c) {
            int odd=0,even=0;
            for(int d=1;c-d+1>=0 && c+d<=n;++d){string p=s.substr(c-d+1,2*d-1),r=p;reverse(r.begin(),r.end());if(p==r)odd=d;}
            for(int d=1;c-d>=0 && c+d<=n;++d){string p=s.substr(c-d,2*d),r=p;reverse(r.begin(),r.end());if(p==r)even=d;}
            assert(index.odd[c]==odd && index.even[c]==even);
        }
    }
''',
'palindrome-center-contribution': r'''
    for(int n=0;n<=11;++n) for(int mask=0;mask<(1<<n);++mask) {
        string s;for(int i=0;i<n;++i)s+=char('a'+(mask>>i&1));
        vector<long long> expected(n+1);
        for(int l=0;l<n;++l)for(int r=l+1;r<=n;++r) {
            string part=s.substr(l,r-l),rev=part;reverse(rev.begin(),rev.end());if(part==rev)++expected[r-l];
        }
        auto answer=palindrome_counts_by_length(s);
        assert(answer==expected);
        PalindromeCountRadii p(s);
        long long by_radius=accumulate(p.odd.begin(),p.odd.end(),0LL)+accumulate(p.even.begin(),p.even.end(),0LL);
        assert(accumulate(answer.begin(),answer.end(),0LL)==by_radius);
    }
    string s(100000,'a');auto answer=palindrome_counts_by_length(s);
    assert(accumulate(answer.begin(),answer.end(),0LL)==100000LL*100001/2);
''',
'automaton-forbidden-dp': r'''
    assert(count_avoiding_word(0,"ab","")==0);
    assert(count_avoiding_word(4,"ab","z")==16);
    for(int trial=0;trial<1500;++trial) {
        int n=rng()%9,m=rng()%6;string pattern=random_string(m,3);int expected=0;
        for(int mask=0;mask<(1<<n);++mask){string word;for(int i=0;i<n;++i)word+=char('a'+(mask>>i&1));expected+=word.find(pattern)==string::npos;}
        assert(count_avoiding_word(n,"ab",pattern)==expected);
    }
    assert(count_avoiding_word(1000,"ab","a")==1);
''',
'aho-failure-aggregation': r'''
    for(int trial=0;trial<1200;++trial) {
        string text=random_string(rng()%30,3);int k=rng()%14;vector<string> patterns;
        for(int i=0;i<k;++i)patterns.push_back(random_string(rng()%8,3));
        if(!patterns.empty())patterns.push_back(patterns.front());
        vector<long long> expected;
        for(auto p:patterns) {long long count=0;for(int at=0;at+int(p.size())<=int(text.size());++at)count+=text.substr(at,p.size())==p;expected.push_back(count);}
        assert(pattern_occurrences(text,patterns)==expected);
    }
    vector<string> many;for(int n=1;n<=100;++n)many.push_back(string(n,'a'));
    auto counts=pattern_occurrences(string(10000,'a'),many);
    for(int n=1;n<=100;++n)assert(counts[n-1]==10001-n);
''',
'wildcard-convolution': r'''
    for(int mod:{998244353,469762049}) {
        for(int d=2;1LL*d*d<=mod;++d)assert(mod%d!=0);
        assert(wildcard_ntt::power(3,mod-1,mod)==1);
        for(int factor:{2,7,17})if((mod-1)%factor==0)assert(wildcard_ntt::power(3,(mod-1)/factor,mod)!=1);
    }
    auto direct=[](const string& text,const string& pattern){vector<int> result;for(int at=0;at+int(pattern.size())<=int(text.size());++at){bool valid=true;for(int j=0;j<int(pattern.size());++j)if(text[at+j]!='*' && pattern[j]!='*' && text[at+j]!=pattern[j])valid=false;if(valid)result.push_back(at);}return result;};
    for(int trial=0;trial<700;++trial) {
        int n=rng()%45,m=rng()%35;string text,pattern;
        for(int i=0;i<n;++i)text+="azb*"[rng()%4];
        for(int i=0;i<m;++i)pattern+="azb*"[rng()%4];
        assert(wildcard_match_positions(text,pattern)==direct(text,pattern));
    }
    for(int n=0;n<=5;++n)for(int mask=0;mask<int(pow(3,n));++mask){int v=mask;string text;for(int i=0;i<n;++i){text+="ab*"[v%3];v/=3;}for(int m=0;m<=3;++m)for(int p=0;p<int(pow(3,m));++p){v=p;string pattern;for(int j=0;j<m;++j){pattern+="ab*"[v%3];v/=3;}assert(wildcard_match_positions(text,pattern)==direct(text,pattern));}}
    assert(wildcard_match_positions(string(4096,'*'),string(2048,'z')).size()==2049);
    assert(wildcard_match_positions(string(4096,'a'),string(2048,'z')).empty());
''',
'rotation-minimum': r'''
    for(int n=0;n<=12;++n) for(int mask=0;mask<(1<<n);++mask) {
        string s;for(int i=0;i<n;++i)s+=char('a'+(mask>>i&1));
        string expected=s;for(int at=0;at<n;++at)expected=min(expected,s.substr(at)+s.substr(0,at));
        assert(minimum_rotation(s)==expected);
        int at=minimum_rotation_start(s);assert(n==0 ? at==0 : (0<=at && at<n));
    }
    for(int trial=0;trial<2000;++trial){string s=random_string(rng()%60,5),expected=s;for(int at=0;at<int(s.size());++at)expected=min(expected,s.substr(at)+s.substr(0,at));assert(minimum_rotation(s)==expected);}
    assert(minimum_rotation(string(100000,'a')+"b")==string(100000,'a')+"b");
''',
'palindrome-recursive-degree': r'''
    auto defined_degree=[](const string& word){
        auto follows_definition=[&](auto&& self,const string& w,int k)->bool {
            if(w.empty())return false;
            if(k==1){string reversed=w;reverse(reversed.begin(),reversed.end());return w==reversed;}
            int half=w.size()/2;
            if(half==0)return false;
            string left=w.substr(0,half),right=w.substr(w.size()-half);
            return left==right && self(self,left,k-1) && self(self,right,k-1);
        };
        int degree=0;for(int k=1;k<=int(word.size());++k)if(follows_definition(follows_definition,word,k))degree=k;
        return degree;
    };
    for(int n=0;n<=11;++n)for(int mask=0;mask<(1<<n);++mask){string s;for(int i=0;i<n;++i)s+=char('a'+(mask>>i&1));vector<long long> expected(n+1);
        for(int l=0;l<n;++l)for(int r=l+1;r<=n;++r){int d=defined_degree(s.substr(l,r-l));for(int k=1;k<=d;++k)++expected[k];}
        assert(palindrome_degree_counts(s)==expected);
    }
    assert(palindrome_degree_counts("abba")==vector<long long>({0,6,1,0,0}));
    assert(palindrome_degree_counts("abacaba")==vector<long long>({0,12,4,1,0,0,0,0}));
    assert(palindrome_degree_counts("aba")==vector<long long>({0,4,1,0}));
    auto all_equal=palindrome_degree_counts(string(5000,'a'));
    assert(all_equal[1]==5000LL*5001/2 && all_equal[13]==905LL*906/2 && all_equal[14]==0);
''',
'substring-subsequence-next': r'''
    for(int trial=0;trial<1200;++trial) {
        string s=random_string(rng()%15,3);int n=s.size();NextSubsequence index(s);
        for(int query=0;query<15;++query) {
            int l=rng()%(n+1),r=l+rng()%(n-l+1);string pattern=random_string(rng()%8,4);
            int matched=0,end=l;
            for(int i=l;i<r && matched<int(pattern.size());++i)if(s[i]==pattern[matched]){++matched;end=i+1;}
            optional<int> expected;if(matched==int(pattern.size()))expected=end;
            assert(index.earliest_end(l,r,pattern)==expected);
        }
        string pattern=random_string(rng()%12,4),expanded;
        for(int t=0;t<int(pattern.size())+1;++t)expanded+=s;
        int matched=0;optional<long long> expected;if(pattern.empty())expected=0;
        for(int i=0;i<int(expanded.size()) && matched<int(pattern.size());++i)if(expanded[i]==pattern[matched]){++matched;if(matched==int(pattern.size()))expected=i+1;}
        assert(repeated_subsequence_length(s,pattern)==expected);
    }
    assert(repeated_subsequence_length("contest","son")==10);
    assert(repeated_subsequence_length("contest","programming")==nullopt);
    assert(repeated_subsequence_length("contest","sentence")==33);
    assert(repeated_subsequence_length(string(99999,'a')+"b",string(100000,'b'))==10000000000LL);
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
    with tempfile.TemporaryDirectory(prefix='string-coverage-') as directory:
        cpp = Path(directory) / 'test.cpp'
        executable = Path(directory) / 'test'
        cpp.write_text(source)
        compiled = subprocess.run([os.environ.get('CXX', 'g++'), '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', '-I', str(ROOT / 'vendor/ac-library'), str(cpp), '-o', str(executable)], capture_output=True, text=True, timeout=60)
        if compiled.returncode:
            return slug, False, compiled.stderr
        executed = subprocess.run([str(executable)], capture_output=True, text=True, timeout=30)
        return slug, executed.returncode == 0, executed.stderr


if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, CASES.items()))
    for slug, passed, output in results:
        print(slug, 'PASS' if passed else 'FAIL', output)
    if any(not passed for _, passed, _ in results):
        raise SystemExit(1)
