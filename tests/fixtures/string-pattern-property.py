"""Exercise the eight actual published C++ snippets against independent small models."""
from pathlib import Path
import concurrent.futures
import json
import os
import re
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]
HELPERS=r'''
using namespace std;
vector<string> words_up_to(int maximum,int alphabet=2){vector<string> all{""},layer{""};for(int n=1;n<=maximum;++n){vector<string> next;for(const auto& s:layer)for(int c=0;c<alphabet;++c)next.push_back(s+char('a'+c));all.insert(all.end(),next.begin(),next.end());layer=move(next);}return all;}
int direct_prefix_pieces(const string& s,const string& t){vector<int>dp(t.size()+1,1000000);dp[0]=0;for(int i=0;i<int(t.size());++i)for(int length=1;length<=int(s.size()) && i+length<=int(t.size());++length)if(t.substr(i,length)==s.substr(0,length))dp[i+length]=min(dp[i+length],dp[i]+1);return dp.back()==1000000?-1:dp.back();}
int direct_lcp(const string& a,const string& b){int length=0;while(length<int(a.size()) && length<int(b.size()) && a[length]==b[length])++length;return length;}
int direct_edit(const string& s,const string& t){vector<vector<int>>dp(s.size()+1,vector<int>(t.size()+1));for(int i=0;i<=int(s.size());++i)for(int j=0;j<=int(t.size());++j){if(i==0)dp[i][j]=j;else if(j==0)dp[i][j]=i;else dp[i][j]=min({dp[i-1][j]+1,dp[i][j-1]+1,dp[i-1][j-1]+(s[i-1]!=t[j-1])});}return dp.back().back();}
int direct_periodic(const string& base,const string& word){int best=0,n=base.size();for(int start=0;start<n;++start){int count=0;while(count<=n){bool equal=true;for(int j=0;j<int(word.size());++j)if(word[j]!=base[(start+count*word.size()+j)%base.size()]){equal=false;break;}if(!equal)break;++count;}if(count>n)return -1;best=max(best,count);}return best;}
optional<pair<string,int>> direct_reverse(const string& s){int n=s.size()/2;for(int i=0;i<=n;++i){string deleted=s.substr(i,n);reverse(deleted.begin(),deleted.end());string rest=s.substr(0,i)+s.substr(i+n);if(rest==deleted)return pair{rest,i};}return nullopt;}
int brute_slash(const string& s){int best=0,n=s.size();for(unsigned mask=1;mask<(1u<<n);++mask){string t;for(int i=0;i<n;++i)if(mask>>i&1)t+=s[i];if(t.size()%2==0)continue;int middle=t.size()/2;if(t[middle]!='/')continue;bool ok=true;for(int i=0;i<middle;++i)if(t[i]!='1' || t[middle+1+i]!='2')ok=false;if(ok)best=max(best,int(t.size()));}return best;}
int main(){using namespace tested;mt19937_64 rng(257213386135);
'''
CASES={
'prefix-piece-farthest-reach':r'''
    for(const auto& s:words_up_to(5))for(const auto& t:words_up_to(8))assert(minimum_prefix_pieces(s,t)==direct_prefix_pieces(s,t));
    for(int trial=0;trial<1000;++trial){string s(rng()%35,'a'),t(rng()%80,'a');for(auto&c:s)c+='\0'+rng()%3;for(auto&c:t)c+='\0'+rng()%3;assert(minimum_prefix_pieces(s,t)==direct_prefix_pieces(s,t));}
    assert(minimum_prefix_pieces("aba","ababa")==2);assert(minimum_prefix_pieces("aba","ababaab")==3);
    string bytes;bytes+=char(0);bytes+=char(255);assert(minimum_prefix_pieces(bytes,bytes+bytes)==2);
    assert(minimum_prefix_pieces(string(500000,'a'),string(500000,'a'))==1);
    assert(minimum_prefix_pieces("ab",string(500000,'a'))==500000);
''',
'suffix-lcp-pair-sum':r'''
    auto check=[](const string& s){auto got=all_suffix_lcp_sums(s);assert(got.size()==s.size());for(int i=0;i<int(s.size());++i){long long expected=0;for(int j=0;j<int(s.size());++j)expected+=direct_lcp(s.substr(i),s.substr(j));assert(got[i]==expected);}};
    for(const auto& s:words_up_to(10))check(s);
    for(int trial=0;trial<800;++trial){string s(rng()%100,'a');for(auto&c:s)c+='\0'+rng()%5;check(s);}
    check("mississippi");check(string{char(0),char(255),char(0),char(128)});
    int n=1000000;auto got=all_suffix_lcp_sums(string(n,'a'));for(int i=0;i<n;++i){long long length=n-i;assert(got[i]==length*(length+1)/2+1LL*i*length);}
''',
'fixed-length-lexicographic-subsequence':r'''
    auto check=[](const string& s){int n=s.size();vector<string>best(n+1,string(n+1,'z'));for(unsigned mask=0;mask<(1u<<n);++mask){string t;for(int i=0;i<n;++i)if(mask>>i&1)t+=s[i];best[t.size()]=min(best[t.size()],t);}for(int k=0;k<=n;++k)assert(smallest_fixed_length_subsequence(s,k)==best[k]);};
    for(const auto& s:words_up_to(8,3))check(s);
    for(int trial=0;trial<400;++trial){string s(rng()%15,'a');for(auto&c:s)c+='\0'+rng()%5;check(s);}
    assert(smallest_fixed_length_subsequence("atcoder",3)=="acd");assert(smallest_fixed_length_subsequence("kittyonyourlap",5)=="inlap");
    string s(500000,'a');assert(smallest_fixed_length_subsequence(s,0).empty());assert(smallest_fixed_length_subsequence(s,250000)==string(250000,'a'));assert(smallest_fixed_length_subsequence(s,500000)==s);
    s.assign(250000,'z');s+=string(250000,'a');assert(smallest_fixed_length_subsequence(s,250000)==string(250000,'a'));
    bool threw=false;try{smallest_fixed_length_subsequence("a",2);}catch(const invalid_argument&){threw=true;}assert(threw);
''',
'edit-distance-diagonal-band':r'''
    auto all=words_up_to(7);for(const auto& s:all)for(const auto& t:all){int expected=direct_edit(s,t);for(int k=0;k<=8;++k)assert(edit_distance_at_most(s,t,k)==(expected<=k));}
    for(int trial=0;trial<1000;++trial){string s(rng()%60,'a'),t(rng()%60,'a');for(auto&c:s)c+='\0'+rng()%4;for(auto&c:t)c+='\0'+rng()%4;int expected=direct_edit(s,t);for(int k=0;k<=10;++k)assert(edit_distance_at_most(s,t,k)==(expected<=k));}
    string s(500000,'a'),t=s;assert(edit_distance_at_most(s,t,0));assert(edit_distance_at_most(s,t,20));t.replace(t.size()-21,21,string(21,'b'));assert(!edit_distance_at_most(s,t,20));assert(edit_distance_at_most(s,t,21));assert(edit_distance_at_most(s,t,INT_MAX));
    assert(edit_distance_at_most("",string(500000,'a'),500000));assert(!edit_distance_at_most("",string(500000,'a'),499999));
    bool threw=false;try{edit_distance_at_most("a","a",-1);}catch(const invalid_argument&){threw=true;}assert(threw);
''',
'periodic-match-residue-chains':r'''
    auto bases=words_up_to(5),words=words_up_to(6);for(const auto& base:bases)if(!base.empty())for(const auto& word:words)if(!word.empty())assert(maximum_periodic_word_repetitions(base,word)==direct_periodic(base,word));
    for(int trial=0;trial<1000;++trial){string base(1+rng()%50,'a'),word(1+rng()%80,'a');for(auto&c:base)c+='\0'+rng()%3;for(auto&c:word)c+='\0'+rng()%3;assert(maximum_periodic_word_repetitions(base,word)==direct_periodic(base,word));}
    assert(maximum_periodic_word_repetitions("abcabab","ab")==3);assert(maximum_periodic_word_repetitions("aa","aaaaaaa")==-1);assert(maximum_periodic_word_repetitions("aba","baaab")==0);
    string base(500000,'a');base.back()='b';assert(maximum_periodic_word_repetitions(base,"a")==499999);
    assert(maximum_periodic_word_repetitions("a",string(500000,'a'))==-1);string word(500000,'a');word.back()='b';assert(maximum_periodic_word_repetitions("a",word)==0);
''',
'sorted-adjacent-max-lcp':r'''
    auto check=[](const vector<string>& words){auto got=maximum_other_lcp(words);assert(got.size()==words.size());for(int i=0;i<int(words.size());++i){int expected=0;for(int j=0;j<int(words.size());++j)if(i!=j)expected=max(expected,direct_lcp(words[i],words[j]));assert(got[i]==expected);}};
    auto pool=words_up_to(2);pool.push_back("aaa");for(int n=0,power=1;n<=5;++n,power*=8)for(int code=0;code<power;++code){int x=code;vector<string> words(n);for(auto& s:words){s=pool[x%8];x/=8;}check(words);}
    for(int trial=0;trial<1000;++trial){vector<string>words(rng()%100);for(auto&s:words){s.assign(rng()%50,'a');for(auto&c:s)c+='\0'+rng()%5;}check(words);}
    check({string{char(0),char(255)},string{char(0),char(128)},"","a","a"});
    auto got=maximum_other_lcp(vector<string>(500000,"a"));for(int x:got)assert(x==1);
    assert(maximum_other_lcp({string(250000,'a'),string(250000,'a')})==vector<int>({250000,250000}));
''',
'reverse-deletion-two-z':r'''
    auto check=[](const string& s){auto got=find_reverse_deletion(s),expected=direct_reverse(s);assert(bool(got)==bool(expected));if(got){auto [rest,i]=*got;int n=s.size()/2;assert(i>=0 && i<=n && rest==s.substr(0,i)+s.substr(i+n));string removed=s.substr(i,n);reverse(removed.begin(),removed.end());assert(rest==removed);}};
    check("");for(int n=1;n<=8;++n)for(unsigned mask=0;mask<(1u<<(2*n));++mask){string s(2*n,'a');for(int i=0;i<2*n;++i)if(mask>>i&1)s[i]='b';check(s);}
    for(int trial=0;trial<1000;++trial){int n=1+rng()%60;string s(2*n,'a');for(auto&c:s)c+='\0'+rng()%4;check(s);string original(n,'a');for(auto&c:original)c+='\0'+rng()%4;int i=rng()%(n+1);string reverse=original;std::reverse(reverse.begin(),reverse.end());check(original.substr(0,i)+reverse+original.substr(i));}
    check("abcbac");check("abababab");check("agccga");check("atcodeer");check(string{char(0),char(255),char(255),char(0)});
    string s(2000000,'a');auto got=find_reverse_deletion(s);assert(got && got->first==string(1000000,'a'));s.back()='b';assert(!find_reverse_deletion(s));
    bool threw=false;try{find_reverse_deletion("a");}catch(const invalid_argument&){threw=true;}assert(threw);
''',
'slash-subsequence-crossing':r'''
    const string alphabet="12/";for(int n=0,power=1;n<=7;++n,power*=3)for(int code=0;code<power;++code){int x=code;string s(n,'1');for(auto&c:s){c=alphabet[x%3];x/=3;}BalancedSlashQueries solver(s);for(int l=0;l<=n;++l)for(int r=l;r<=n;++r)assert(solver.longest(l,r)==brute_slash(s.substr(l,r-l)));}
    for(int trial=0;trial<1000;++trial){int n=1+rng()%80;string s(n,'1');for(auto&c:s)c=alphabet[rng()%3];BalancedSlashQueries solver(s);for(int q=0;q<200;++q){int l=rng()%(n+1),r=rng()%(n+1);if(l>r)swap(l,r);int best=0;for(int p=l;p<r;++p)if(s[p]=='/'){int ones=0,twos=0;for(int i=l;i<p;++i)ones+=s[i]=='1';for(int i=p+1;i<r;++i)twos+=s[i]=='2';best=max(best,2*min(ones,twos)+1);}assert(solver.longest(l,r)==best);}}
    string s(49999,'1');s+='/';s+=string(49999,'2');BalancedSlashQueries solver(s);for(int q=0;q<100000;++q)assert(solver.longest(0,s.size())==99999);
    BalancedSlashQueries only(string(100000,'/'));assert(only.longest(0,100000)==1);BalancedSlashQueries none(string(100000,'1'));assert(none.longest(0,100000)==0);
'''
}
def run(item):
    slug,body=item
    article=(ROOT/'src/content/docs/techniques'/f'{slug}.mdx').read_text()
    snippets=re.findall(r'```cpp\n(.*?)```',article,re.S)
    if len(snippets)!=1:return slug,False,'Expected one published C++ implementation'
    includes=[];code=[]
    for line in snippets[0].splitlines():
        (includes if line.startswith('#include ') else code).append(line)
    source='#include <bits/stdc++.h>\n'+'\n'.join(includes)+'\nnamespace tested {\n'+'\n'.join(code)+'\n}\n'+HELPERS+body+'\n}\n'
    with tempfile.TemporaryDirectory(prefix='string-pattern-property-') as directory:
        cpp=Path(directory)/'test.cpp';exe=Path(directory)/'test';cpp.write_text(source)
        compiled=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror','-I',str(ROOT/'vendor/ac-library'),str(cpp),'-o',str(exe)],capture_output=True,text=True,timeout=60)
        if compiled.returncode:return slug,False,compiled.stderr
        executed=subprocess.run([str(exe)],capture_output=True,text=True,timeout=60)
        return slug,executed.returncode==0,executed.stderr
if __name__=='__main__':
    features=json.loads((ROOT/'data/string-pattern-problem-features.json').read_text())
    assert {id for row in features for id in row['techniqueIds']}==set(CASES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES.items()))
    for slug,passed,details in results:
        print(slug,'PASS' if passed else 'FAIL',flush=True)
        if details:print(details,flush=True)
    raise SystemExit(0 if all(passed for _,passed,_ in results) else 1)
