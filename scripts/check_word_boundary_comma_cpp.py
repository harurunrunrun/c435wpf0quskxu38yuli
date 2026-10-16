#!/usr/bin/env python3
"""Compile the visible MDX fence; compare literal rules and all closed comma sets."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,tempfile

TESTS=r'''
#include <algorithm>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <random>
#include <regex.h>
using Words=std::vector<std::string>;
using U=std::uint64_t;
U checks=0,valid_cases=0,exhaustive_cases=0,closed_candidates=0,closed_sets=0;
U lexical_cases=0,lexical_valid=0,invalid_cases=0,random_cases=0,checksum=0;
int maximum_rule_passes=0;std::size_t maximum_input=0,maximum_output=0;
double maximum_single_call_seconds=0;
void require(bool good,const char* why){++checks;if(!good){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
void absorb(std::string_view text){for(unsigned char ch:text)checksum=checksum*1000003+ch;checksum=checksum*1000003+257;}
std::string execute(const std::string& text){
    const auto before=std::chrono::steady_clock::now();
    auto result=close_word_boundary_commas(text);
    maximum_single_call_seconds=std::max(maximum_single_call_seconds,
        std::chrono::duration<double>(std::chrono::steady_clock::now()-before).count());
    maximum_input=std::max(maximum_input,text.size());maximum_output=std::max(maximum_output,result.size());
    return result;
}
// Generator representation: gaps[i] is0=space,1=comma,2=period after words[i].
// The final period is implicit. All oracle comparisons use word strings directly.
std::string render(const Words& words,const std::vector<int>& gaps,U commas){
    std::string out;
    for(std::size_t i=0;i<words.size();++i){
        out+=words[i];
        if(i+1==words.size())out+='.';
        else if(gaps[i]==2)out+=". ";
        else out+=(commas>>i&1)?", ":" ";
    }
    return out;
}
U initial_mask(const std::vector<int>& gaps){U mask=0;for(std::size_t i=0;i<gaps.size();++i)if(gaps[i]==1)mask|=U{1}<<i;return mask;}
U literal_rules(const Words& words,const std::vector<int>& gaps){
    U active=initial_mask(gaps);int passes=0;
    for(;;){
        ++passes;const U old=active;
        for(std::size_t target=0;target<gaps.size();++target)if(gaps[target]!=2)
            for(std::size_t source=0;source<gaps.size();++source)if(old>>source&1)
                if(words[source]==words[target]||words[source+1]==words[target+1])
                    active|=U{1}<<target;
        if(active==old)break;
    }
    maximum_rule_passes=std::max(maximum_rule_passes,passes);return active;
}
U enumerate_closed_sets(const Words& words,const std::vector<int>& gaps){
    const U initial=initial_mask(gaps);U eligible=0;
    for(std::size_t i=0;i<gaps.size();++i)if(gaps[i]!=2)eligible|=U{1}<<i;
    const U optional=eligible&~initial;U intersection=eligible,best=0;
    int best_size=100,best_count=0;
    for(U subset=optional;;subset=(subset-1)&optional){
        ++closed_candidates;const U candidate=initial|subset;bool closed=true;
        for(std::size_t source=0;source<gaps.size()&&closed;++source)if(candidate>>source&1)
            for(std::size_t target=0;target<gaps.size();++target)
                if(gaps[target]!=2&&!(candidate>>target&1)&&
                    (words[source]==words[target]||words[source+1]==words[target+1])){closed=false;break;}
        if(closed){
            ++closed_sets;intersection&=candidate;const int size=std::popcount(candidate);
            if(size<best_size){best_size=size;best=candidate;best_count=1;}
            else if(size==best_size)++best_count;
        }
        if(subset==0)break;
    }
    require(best_count==1&&best==intersection,"unique least closed superset equals intersection of ALL closed configurations");
    return best;
}
void check(const Words& words,const std::vector<int>& gaps,bool all_sets){
    require(words.size()==gaps.size()+1&&gaps.size()<63,"small oracle domain");
    const auto text=render(words,gaps,initial_mask(gaps)),unchanged=text;
    const U final=literal_rules(words,gaps);
    if(all_sets)require(enumerate_closed_sets(words,gaps)==final,"literal repeated rules equal all-configurations least closure");
    const auto expected=render(words,gaps,final),actual=execute(text);
    require(actual==expected,"graph output equals literal rules with exact words/periods/spaces preserved");
    require(text==unchanged,"input unchanged");
    require(execute(actual)==actual,"closure idempotent when its output is in the API input range");
    require((final&initial_mask(gaps))==initial_mask(gaps),"original commas retained");
    absorb(actual);++valid_cases;
}
void exhaustive(const Words& vocabulary,int longest){
    for(int count=1;count<=longest;++count){
        Words words(count);std::vector<int> gaps(count-1);
        auto choose_gaps=[&](auto&& self,int at)->void{
            if(at==count-1){check(words,gaps,true);++exhaustive_cases;return;}
            for(int kind=0;kind<3;++kind){gaps[at]=kind;self(self,at+1);}
        };
        auto choose_words=[&](auto&& self,int at)->void{
            if(at==count){choose_gaps(choose_gaps,0);return;}
            for(const auto& word:vocabulary){words[at]=word;self(self,at+1);}
        };choose_words(choose_words,0);
    }
}
void reject(const std::string& text){
    bool threw=false;try{(void)close_word_boundary_commas(text);}catch(const std::invalid_argument&){threw=true;}
    require(threw,"invalid grammar or length rejected");++invalid_cases;
}
void lexical_exhaustive(){
    // Declarative grammar oracle, independently implemented by libc POSIX regex.
    regex_t grammar{},word_regex{};
    require(regcomp(&grammar,R"(^[a-z]+(( |, |\. )[a-z]+)*\.$)",REG_EXTENDED|REG_NOSUB)==0,"compile declarative grammar");
    require(regcomp(&word_regex,"[a-z]+",REG_EXTENDED)==0,"compile independent word regex");
    const std::string alphabet="a ,.";
    for(int length=0;length<=8;++length){
        std::string raw(length,'a');
        auto choose=[&](auto&& self,int at)->void{
            if(at<length){for(char ch:alphabet){raw[at]=ch;self(self,at+1);}return;}
            ++lexical_cases;
            if(raw.size()<2||regexec(&grammar,raw.c_str(),0,nullptr,0)!=0){reject(raw);return;}
            ++lexical_valid;Words words;std::vector<int> gaps;std::size_t previous_end=0;
            std::size_t cursor=0;regmatch_t match{};
            while(regexec(&word_regex,raw.c_str()+cursor,1,&match,0)==0){
                const auto position=cursor+std::size_t(match.rm_so),end=cursor+std::size_t(match.rm_eo);
                if(!words.empty())gaps.push_back(raw[previous_end]=='.'?2:raw[previous_end]==','?1:0);
                words.push_back(raw.substr(position,end-position));previous_end=end;cursor=end;
            }
            check(words,gaps,true);
        };choose(choose,0);
    }
    require(lexical_cases==87381,"all raw strings of length0..8 over letter/space/comma/period");
    regfree(&grammar);regfree(&word_regex);
}
void known_cases(){
    const auto exact=[&](const std::string& input,const std::string& expected){require(execute(input)==expected,"explicit boundary/regression case");absorb(expected);};
    exact("a.","a.");exact("a a a.","a a a.");
    exact("red, blue. blue green.","red, blue. blue green.");
    exact("a, b. a c. d c.","a, b. a, c. d, c.");
    exact("a, a a. a.","a, a, a. a.");
    exact("a, b. b.","a, b. b.");
    exact("a, b. a.","a, b. a.");
    exact("a, ab. aa a. aa ab.","a, ab. aa, a. aa, ab.");
    exact("please sit spot. sit spot, sit. spot here now here.","please, sit spot. sit spot, sit. spot, here now, here.");
    exact("one, two. one tree. four tree. four four. five four. six five.","one, two. one, tree. four, tree. four, four. five, four. six five.");
    for(const std::string& raw:std::vector<std::string>{"a","a,"," a.","a. ","a  b.","a,  b.","a,, b.","a.b.","a,b.","a .", "a , b.","a,.","a..", ".a.","a!", "A.","a B.","a\tb.","a\nb.","a\rb.","a.\n","a? b.","a; b.","a0.","a_.",std::string("a\0.",3),std::string("\xff.",2),"é."})reject(raw);
    reject(std::string(1000000,'a')+'.');
    // Every malformed grammar above is followed by a valid call: no persistent state.
    exact("x, y. x z.","x, y. x, z.");exact("x z.","x z.");
}
void random_checks(){
    std::mt19937 rng(20180419);
    const Words vocabulary={"a","aa","aaa","ab","b","ba","same","some","sameword","sam","z"};
    for(int test=0;test<5000;++test){
        const int count=1+int(rng()%25);Words words;std::vector<int> gaps;
        for(int i=0;i<count;++i){words.push_back(vocabulary[rng()%vocabulary.size()]);if(i+1<count)gaps.push_back(int(rng()%3));}
        check(words,gaps,false);++random_cases;
    }
}
void maximum_scale(){
    {
        const std::string text=std::string(999999,'z')+'.';
        require(execute(text)==text,"original maximum: one huge word");absorb(text);
    }
    {
        std::string text;for(int i=0;i<500000;++i)text+=(i+1==500000?"a.":"a ");
        require(text.size()==1000000,"maximum token-count input length");
        require(execute(text)==text,"500000 repeated words with no source comma");absorb(text);
    }
    {
        constexpr int count=499999;std::string text,expected;
        for(int i=0;i<count;++i){const std::string_view word=i==0?"aa":"a";text+=word;expected+=word;
            if(i+1==count){text+='.';expected+='.';}
            else{ text+=(i==1?", ":" ");expected+=", ";}}
        require(text.size()==1000000&&expected.size()==1499997,"original maximum input, output exceeds input size limit");
        require(execute(text)==expected,"single comma expands to every eligible gap at original maximum");
        absorb(expected);reject(expected); // API input bound is explicit; output is not truncated.
    }
    {
        // An alternating path after(A0)-before(B0)-after(A1)-...-after(A45000).
        // Each graph edge is its own two-word sentence; no sentence-boundary edge.
        auto word=[](int number){std::string out(4,'a');for(char& ch:out){ch=char('a'+number%26);number/=26;}return out;};
        constexpr int links=45000;std::string text,expected;
        for(int i=0;i<links;++i)for(int half=0;half<2;++half){
            std::string a=word(2*(i+half)),b=word(2*i+1);
            if(i==0&&half==0)a+=std::string(10000,'z');
            const bool last=i+1==links&&half==1;
            text+=a;expected+=a;text+=(i==0&&half==0?", ":" ");expected+=", ";
            text+=b;expected+=b;text+=(last?".":". ");expected+=(last?".":". ");
        }
        require(text.size()==1000000&&expected.size()==1089999,"original maximum with90000-edge alternating propagation path");
        require(execute(text)==expected,"long propagation path,90001 distinct words, sentence boundaries and long common prefixes");absorb(expected);
    }
    {
        // A large dictionary with all words distinct: a marked BEFORE of word1
        // must not activate its different AFTER state, even in one long sentence.
        constexpr int count=200000;std::string text;
        for(int i=0;i<count;++i){
            std::string word(4,'a');int code=i;
            for(char& ch:word){ch=char('a'+code%26);code/=26;}
            text+=(i==0?"zzz":word);
            text+=(i+1==count?".":i==0?", ":" ");
        }
        require(text.size()==1000000,"original maximum with200000 distinct words and400000 states");
        require(execute(text)==text,"large exact-string dictionary keeps the two sides independent");absorb(text);
    }
}
int main(){
    const auto start=std::chrono::steady_clock::now();
    exhaustive({"a","b"},7);require(exhaustive_cases==111974,"all two-word vocabulary texts through7 tokens");
    exhaustive({"a","aa","ab"},5);require(exhaustive_cases==134117,"plus every prefix-sharing three-word vocabulary text through5 tokens");
    lexical_exhaustive();known_cases();random_checks();maximum_scale();
    require(maximum_input==1000000&&maximum_output==1499997,"executed original max and larger full output");
    std::cout<<"{\"checks\":"<<checks<<",\"validCases\":"<<valid_cases<<",\"exhaustiveTexts\":"<<exhaustive_cases
             <<",\"closedConfigurationsEnumerated\":"<<closed_candidates<<",\"closedConfigurationsAccepted\":"<<closed_sets
             <<",\"lexicalStrings\":"<<lexical_cases<<",\"lexicalValid\":"<<lexical_valid<<",\"invalidCases\":"<<invalid_cases
             <<",\"randomCases\":"<<random_cases<<",\"maximumRulePasses\":"<<maximum_rule_passes
             <<",\"maximumInputBytes\":"<<maximum_input<<",\"maximumOutputBytes\":"<<maximum_output
             <<",\"maximumSingleCallSeconds\":"<<maximum_single_call_seconds<<",\"checksum\":\""<<checksum
             <<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''

args=[arg for arg in sys.argv[1:] if arg!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/word-boundary-comma-closure.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected exactly one complete visible C++20 fence')
with tempfile.TemporaryDirectory(prefix='flowchartcp-comma-check-') as directory:
    source=Path(directory)/'check.cpp';binary=Path(directory)/'check';source.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];environment=os.environ.copy()
    if '--sanitize' in sys.argv:
        flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
        environment['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';environment['UBSAN_OPTIONS']='halt_on_error=1'
    compiler=environment.get('CXX') or shutil.which('g++') or shutil.which('clang++') or 'c++'
    subprocess.run([compiler,*flags,str(source),'-o',str(binary)],check=True,timeout=120)
    timer=Path('/usr/bin/time');command=[str(binary)]
    if timer.exists() and sys.platform.startswith('linux'):command=[str(timer),'-f','peak_rss_kib=%M',*command]
    result=subprocess.run(command,text=True,capture_output=True,env=environment,timeout=180)
    if result.returncode:
        print(result.stdout,end='',file=sys.stderr);print(result.stderr,end='',file=sys.stderr)
        result.check_returncode()
    report=json.loads(result.stdout);match=re.search(r'^peak_rss_kib=(\d+)$',result.stderr,re.M)
    if match:report['peakRSSKiB']=int(match[1])
    report.update(article=str(article),sanitized='--sanitize' in sys.argv,cppSha256=hashlib.sha256(blocks[0].encode()).hexdigest())
    print(json.dumps(report,ensure_ascii=False,indent=2))
