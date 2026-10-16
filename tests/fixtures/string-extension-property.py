"""Compare all ten published string implementations with independent small models."""
from pathlib import Path
import concurrent.futures
import json
import os
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
COMMON=r'''
int main(){
    using namespace tested;
    mt19937_64 rng(202610152);
    auto is_subsequence=[](const string& text,const string& word){size_t j=0;for(char c:text)if(j<word.size() && word[j]==c)++j;return j==word.size();};
    auto binary=[](int n,int mask){string result(n,'a');for(int i=0;i<n;++i)result[i]+=bool(mask&(1<<i));return result;};
    (void)is_subsequence;(void)binary;
'''
CASES={
'shortest-absent-subsequence':r'''
    auto brute=[&](const string& text,int sigma){
        for(int length=1;;++length){string candidate(length,'a');while(true){if(!is_subsequence(text,candidate))return candidate;int p=length-1;while(p>=0 && candidate[p]==char('a'+sigma-1)){candidate[p]='a';--p;}if(p<0)break;++candidate[p];}}
    };
    for(int n=0;n<=10;++n)for(int mask=0;mask<(1<<n);++mask){string s=binary(n,mask);assert(shortest_absent_subsequence(s,2)==brute(s,2));}
    for(int trial=0;trial<1200;++trial){string s(rng()%12,'a');for(char& c:s)c+=rng()%3;assert(shortest_absent_subsequence(s,3)==brute(s,3));}
    for(int repetition=0;repetition<15;++repetition){string s;for(int i=0;i<repetition;++i)s+="abcdefghijklmnopqrstuvwxyz";assert(shortest_absent_subsequence(s)==string(repetition+1,'a'));}
    assert(shortest_absent_subsequence(string(200000,'a'),1)==string(200001,'a'));
''',
'forbidden-abc-segment-summary':r'''
    auto naive=[](const string& text){array<int,3> dp{0,1000000,1000000};for(char c:text){array<int,3> next;next.fill(1000000);for(int state=0;state<3;++state)for(char replacement='a';replacement<='c';++replacement){int to=state+(replacement==char('a'+state));if(to<3)next[to]=min(next[to],dp[state]+(replacement!=c));}dp=next;}return *min_element(dp.begin(),dp.end());};
    auto deletions=[&](const string& text){int answer=text.size(),n=text.size();for(int mask=0;mask<(1<<n);++mask){string kept;for(int i=0;i<n;++i)if(mask&(1<<i))kept+=text[i];if(!is_subsequence(kept,"abc"))answer=min(answer,n-__builtin_popcount(unsigned(mask)));}return answer;};
    for(int n=0;n<=7;++n){int total=1;for(int i=0;i<n;++i)total*=3;for(int code=0;code<total;++code){string s(n,'a');int value=code;for(char& c:s){c+=value%3;value/=3;}AvoidAbc tree(s);assert(tree.minimum_replacements()==naive(s));if(n<=6)assert(tree.minimum_replacements()==deletions(s));}}
    for(int trial=0;trial<800;++trial){string s(1+rng()%70,'a');for(char& c:s)c+=rng()%3;AvoidAbc tree(s);for(int operation=0;operation<80;++operation){int i=rng()%s.size();s[i]='a'+rng()%3;tree.change(i,s[i]);assert(tree.minimum_replacements()==naive(s));}}
    for(int trial=0;trial<2000;++trial){string a(rng()%10,'a'),b(rng()%10,'a'),c(rng()%10,'a');for(auto* s:{&a,&b,&c})for(char& ch:*s)ch+=rng()%3;auto summarize=[](const string& s){AbcSummary result;for(char ch:s)result=merge_abc(result,abc_leaf(ch));return result;};auto left=merge_abc(merge_abc(summarize(a),summarize(b)),summarize(c)),right=merge_abc(summarize(a),merge_abc(summarize(b),summarize(c)));assert(tie(left.a,left.b,left.c,left.ab,left.bc,left.abc)==tie(right.a,right.b,right.c,right.ab,right.bc,right.abc));}
''',
'aho-active-failure-subtree':r'''
    for(int trial=0;trial<650;++trial){int n=rng()%25;vector<string> words(n);for(auto& word:words){word.resize(1+rng()%8,'a');for(char& c:word)c+=rng()%3;}bool initially=rng()%2;ActiveDictionary dictionary(words,initially);vector<bool> active(n,initially);
        for(int operation=0;operation<100;++operation){if(n && rng()%2){int id=rng()%n;bool enabled=rng()%2;dictionary.set_active(id,enabled);active[id]=enabled;dictionary.set_active(id,enabled);}
            string text(rng()%60,'a');for(char& c:text)c+=rng()%4;long long expected=0;for(int id=0;id<n;++id)if(active[id])for(size_t i=0;i+words[id].size()<=text.size();++i)expected+=text.compare(i,words[id].size(),words[id])==0;assert(dictionary.count(text)==expected);
        }
    }
    ActiveDictionary duplicate({"a","a","aa"});assert(duplicate.count("aaa")==8);duplicate.set_active(0,false);assert(duplicate.count("aaa")==5);duplicate.set_active(1,false);assert(duplicate.count("aaa")==2);duplicate.set_active(2,false);assert(duplicate.count("aaa")==0);
    ActiveDictionary deep({string(30000,'a'),"a"});assert(deep.count(string(30000,'a'))==30001);deep.set_active(0,false);assert(deep.count(string(30000,'a'))==30000);
''',
'sam-kth-distinct-substring':r'''
    auto check=[](const string& text){set<string> unique;for(size_t i=0;i<text.size();++i)for(size_t j=i+1;j<=text.size();++j)unique.insert(text.substr(i,j-i));long long k=0;for(const auto& value:unique){auto answer=kth_substring(text,++k,false);assert(answer && *answer==value);}assert(!kth_substring(text,0,false));assert(!kth_substring(text,k+1,false));};
    for(int n=0;n<=9;++n)for(int mask=0;mask<(1<<n);++mask)check(binary(n,mask));
    for(int trial=0;trial<120;++trial){string s(rng()%24,'a');for(char& c:s)c+=rng()%5;check(s);}
    string repeated(100000,'a');assert(kth_substring(repeated,100000,false)==optional<string>{repeated});assert(!kth_substring(repeated,100001,false));
''',
'sam-kth-occurrence-substring':r'''
    auto check=[](const string& text){vector<string> all;for(size_t i=0;i<text.size();++i)for(size_t j=i+1;j<=text.size();++j)all.push_back(text.substr(i,j-i));sort(all.begin(),all.end());for(size_t k=0;k<all.size();++k){auto answer=kth_substring(text,k+1,true);assert(answer && *answer==all[k]);}assert(!kth_substring(text,0,true));assert(!kth_substring(text,all.size()+1,true));};
    for(int n=0;n<=9;++n)for(int mask=0;mask<(1<<n);++mask)check(binary(n,mask));
    for(int trial=0;trial<120;++trial){string s(rng()%24,'a');for(char& c:s)c+=rng()%5;check(s);}
    string repeated(100000,'a');assert(kth_substring(repeated,100000,true)==optional<string>{"a"});assert(kth_substring(repeated,100001,true)==optional<string>{"aa"});assert(kth_substring(repeated,5000050000LL,true)==optional<string>{repeated});assert(!kth_substring(repeated,5000050001LL,true));
''',
'sam-length-distribution':r'''
    auto check=[](const string& text){vector<set<string>> buckets(text.size()+1);for(size_t i=0;i<text.size();++i)for(size_t j=i+1;j<=text.size();++j)buckets[j-i].insert(text.substr(i,j-i));auto answer=distinct_substring_counts_by_length(text);assert(answer.size()==text.size()+1 && answer[0]==0);for(size_t i=1;i<answer.size();++i)assert(answer[i]==(long long)buckets[i].size());};
    for(int n=0;n<=10;++n)for(int mask=0;mask<(1<<n);++mask)check(binary(n,mask));
    for(int trial=0;trial<450;++trial){string s(rng()%70,'a');for(char& c:s)c+=rng()%26;check(s);}
    auto repeated=distinct_substring_counts_by_length(string(100000,'a'));for(int i=1;i<=100000;++i)assert(repeated[i]==1);
''',
'palindrome-update-hash-monoid':r'''
    auto actual_palindrome=[](const string& text,int l,int r){for(--r;l<r;++l,--r)if(text[l]!=text[r])return false;return true;};
    for(int trial=0;trial<500;++trial){string s(rng()%80,'a');for(char& c:s)c+=rng()%26;PalindromeHash first(s),second(s,972663749);for(int operation=0;operation<140;++operation){if(!s.empty() && rng()%2){int i=rng()%s.size();s[i]='a'+rng()%26;first.change(i,s[i]);second.change(i,s[i]);}int l=rng()%(s.size()+1),r=rng()%(s.size()+1);if(l>r)swap(l,r);bool expected=actual_palindrome(s,l,r);assert(first.possibly_palindrome(l,r)==expected);assert(second.possibly_palindrome(l,r)==expected);}}
    for(int n=0;n<=8;++n)for(int mask=0;mask<(1<<n);++mask){string s=binary(n,mask);PalindromeHash hash(s);for(int l=0;l<=n;++l)for(int r=l;r<=n;++r)assert(hash.possibly_palindrome(l,r)==actual_palindrome(s,l,r));}
    PalindromeHash collision("caha",2);assert(collision.possibly_palindrome(0,4));assert(!actual_palindrome("caha",0,4));
    PalindromeHash long_text(string(200000,'a'));assert(long_text.possibly_palindrome(0,200000));long_text.change(1,'b');assert(!long_text.possibly_palindrome(0,200000));long_text.change(199998,'b');assert(long_text.possibly_palindrome(0,200000));
''',
'subsequence-nonadjacent-last-range':r'''
    auto brute=[](const string& text){set<string> values;int n=text.size();for(int mask=1;mask<(1<<n);++mask){if(mask&(mask<<1))continue;string value;for(int i=0;i<n;++i)if(mask&(1<<i))value+=text[i];values.insert(value);}return (long long)values.size();};
    for(int n=0;n<=10;++n)for(int mask=0;mask<(1<<n);++mask){string s=binary(n,mask);assert(nonadjacent_distinct_subsequence_count(s)==brute(s));}
    for(int trial=0;trial<500;++trial){string s(rng()%14,'a');for(char& c:s)c+=rng()%5;assert(nonadjacent_distinct_subsequence_count(s)==brute(s));}
    assert(nonadjacent_distinct_subsequence_count("abc")==4);assert(nonadjacent_distinct_subsequence_count("aa")==1);assert(nonadjacent_distinct_subsequence_count("acba")==6);assert(nonadjacent_distinct_subsequence_count("chokudai")==54);
    assert(nonadjacent_distinct_subsequence_count(string(200000,'a'))==100000);
''',
'subsequence-waiting-buckets':r'''
    for(int trial=0;trial<1200;++trial){string text(rng()%70,'a');for(char& c:text)c+=rng()%5;vector<string> words(rng()%160);for(auto& word:words){word.resize(rng()%15,'a');for(char& c:word)c+=rng()%5;}int expected=0;for(const auto& word:words)expected+=is_subsequence(text,word);assert(count_matching_subsequences(text,words)==expected);}
    assert(count_matching_subsequences("a",{"aa","a","","a","aaa"})==3);
    assert(count_matching_subsequences("abcde",{"a","bb","acd","ace"})==3);
    vector<string> words(5000,string(50,'a'));assert(count_matching_subsequences(string(50000,'a'),words)==5000);
    assert(count_matching_subsequences(string(49,'a'),words)==0);
''',
'subsequence-delete-gap':r'''
    auto check=[&](const string& text,const string& target){int best=-1,n=text.size();for(int l=0;l<=n;++l)for(int r=l;r<=n;++r)if(is_subsequence(text.substr(0,l)+text.substr(r),target))best=max(best,r-l);auto result=longest_deletable_interval(text,target);assert(result.has_value()==(best>=0));if(result){auto [l,r]=*result;assert(0<=l && l<=r && r<=n && r-l==best);assert(is_subsequence(text.substr(0,l)+text.substr(r),target));}};
    for(int n=0;n<=7;++n)for(int code=0;code<(1<<n);++code){string text=binary(n,code);set<string> targets;for(int mask=0;mask<(1<<n);++mask){string target;for(int i=0;i<n;++i)if(mask&(1<<i))target+=text[i];targets.insert(target);}for(const auto& target:targets)check(text,target);check(text,"z");}
    for(int trial=0;trial<500;++trial){string text(rng()%30,'a'),target;for(char& c:text){c+=rng()%6;if(rng()%2)target+=c;}check(text,target);}
    string text(200000,'a');auto result=longest_deletable_interval(text,string(100000,'a'));assert(result && result->second-result->first==100000);
'''
}

def run(item):
    slug,body=item
    article=(ROOT/'src/content/docs/techniques'/f'{slug}.mdx').read_text()
    snippets=re.findall(r'```cpp\n(.*?)```',article,re.S)
    if len(snippets)!=1:return slug,False,'Expected one published implementation'
    includes=['#include <bits/stdc++.h>'];code=[]
    for line in snippets[0].splitlines():(includes if line.startswith('#include ') else code).append(line)
    source='\n'.join(includes)+'\nusing namespace std;\nnamespace tested{\n'+'\n'.join(code)+'\n}\n'+COMMON+body+'\n}\n'
    with tempfile.TemporaryDirectory(prefix='string-extension-') as directory:
        cpp=Path(directory)/'test.cpp';executable=Path(directory)/'test';cpp.write_text(source)
        compiled=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(executable)],capture_output=True,text=True,timeout=60)
        if compiled.returncode:return slug,False,compiled.stderr
        executed=subprocess.run([str(executable)],capture_output=True,text=True,timeout=90)
        return slug,executed.returncode==0,executed.stderr

if __name__=='__main__':
    techniques=json.loads((ROOT/'data/techniques-specific-string-extensions.json').read_text())
    features=json.loads((ROOT/'data/string-extension-problem-features.json').read_text())
    assert {x['id'] for x in techniques}==set(CASES)
    assert {id for x in features for id in x['techniqueIds']}==set(CASES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES.items()))
    for slug,passed,output in results:print(slug,'PASS' if passed else 'FAIL',output)
    if any(not passed for _,passed,_ in results):raise SystemExit(1)
