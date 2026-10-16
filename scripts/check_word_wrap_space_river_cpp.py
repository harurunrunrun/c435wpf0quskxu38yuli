#!/usr/bin/env python3
"""Compile the article fence; compare sparse event search to literal character grids."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile

HARNESS = r'''
#include <array>
#include <chrono>
#include <climits>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <sstream>
#include <string>
#include <sys/resource.h>
using Lengths=std::vector<int>;using Words=std::vector<std::string>;using space_river::Result;
std::uint64_t checks=0,api_calls=0,checksum=0,exhaustive_inputs=0,literal_widths=0,literal_cells=0;
std::uint64_t next_change_checks=0,literal_path_calls=0,random_inputs=0,metamorphic=0,invalid_cases=0;
std::uint64_t full_width_oracle_widths=0,full_width_oracle_spaces=0;
void require(bool ok,const char*message){++checks;if(!ok)throw std::runtime_error(message);}
void record(std::uint64_t v){checksum=checksum*1000003ULL+v;}
int total(const Lengths&v){return std::accumulate(v.begin(),v.end(),int(v.size())-1);}
int minimum(const Lengths&v){return *std::max_element(v.begin(),v.end());}
Words words(const Lengths&v){Words result;for(int length:v)result.emplace_back(length,'a');return result;}
bool same(Result a,Result b){return a.width==b.width&&a.longest==b.longest;}
Result api(const Lengths&v){++api_calls;auto r=space_river::best_space_river(v);require(r.width>=minimum(v)&&r.width<=total(v),"chosen width in finite domain");require(r.longest>=0&&r.longest<int(v.size()),"chosen river length in domain");record(r.width);record(r.longest);return r;}
space_river::WidthEvaluation fixed(const Lengths&v,int width){++api_calls;auto r=space_river::longest_river_at_width(v,width);require(r.line_count>=1&&r.line_count<=int(v.size()),"row count");require(!r.next_width||*r.next_width>width,"next change strictly later");return r;}
struct Literal{Words rows;int river;};
Literal character_grid(const Lengths&v,int width){++literal_widths;const Words input=words(v);Words rows;
    for(const auto&word:input){if(rows.empty()||rows.back().size()+1+word.size()>static_cast<std::size_t>(width)){rows.push_back(word);}else{rows.back()+=' ';rows.back()+=word;}}
    std::vector<int> previous(width,0),current(width,0);int best=0;
    for(const auto&row:rows){std::fill(current.begin(),current.end(),0);for(int c=0;c<width;++c){++literal_cells;
        if(c>=int(row.size())||row[c]!=' '){continue;}int value=previous[c];if(c)value=std::max(value,previous[c-1]);if(c+1<width)value=std::max(value,previous[c+1]);
        current[c]=value+1;best=std::max(best,current[c]);}previous.swap(current);}return {rows,best};}
// Direct path definition, without DP values, independently checks small grids.
int literal_paths(const Words&rows){int best=0;auto walk=[&](auto&&self,int row,int col,int depth)->void{++literal_path_calls;best=std::max(best,depth);
    if(row+1==int(rows.size())){return;}for(int delta=-1;delta<=1;++delta){const int c=col+delta;if(c>=0&&c<int(rows[row+1].size())&&rows[row+1][c]==' ')self(self,row+1,c,depth+1);}};
    for(int row=0;row<int(rows.size());++row){for(int c=0;c<int(rows[row].size());++c){if(rows[row][c]==' ')walk(walk,row,c,1);}}return best;}
void all_widths(const Lengths&v,bool paths){const Lengths before=v;const int low=minimum(v),high=total(v);std::vector<Literal> layouts;
    Result expected{low,0};for(int width=low;width<=high;++width){auto g=character_grid(v,width);if(g.river>expected.longest)expected={width,g.river};
        if(paths){require(g.river==literal_paths(g.rows),"dense grid against every literal space path");}layouts.push_back(std::move(g));}
    for(int width=low;width<=high;++width){const auto&r=layouts[width-low];auto actual=fixed(v,width);
        require(actual.longest==r.river&&actual.line_count==int(r.rows.size()),"literal fixed width grid");int next=width+1;
        while(next<=high&&layouts[next-low].rows==r.rows)++next;
        require(actual.next_width==(next<=high?std::optional<int>(next):std::nullopt),"next-change width by actual future layouts");++next_change_checks;}
    require(same(api(v),expected),"optimal width and minimum-width tie against every integer width");require(v==before,"input not mutated");}
void exhaustive(){for(int n=1;n<=7;++n){Lengths v(n,1);auto enumerate=[&](auto&&self,int i)->void{
    if(i==n){all_widths(v,n<=5);++exhaustive_inputs;return;}for(int length=1;length<=4;++length){v[i]=length;self(self,i+1);}};enumerate(enumerate,0);}}
// A separate full-size oracle uses prefix-sum binary search to wrap each row,
// direct indexed three-column lookups with row timestamps, and EVERY integer
// width. It has no list merge, next-event jump or row-count stopping rule.
Result full_width_oracle(const Lengths&v){const int n=int(v.size()),limit=total(v);Lengths prefix(n+1,0);for(int i=0;i<n;++i)prefix[i+1]=prefix[i]+v[i]+1;
    Lengths stamp(limit+2,-2),value(limit+2,0);int generation=0;Result answer{minimum(v),0};
    for(int width=minimum(v);width<=limit;++width){++full_width_oracle_widths;int row=generation,begin=0,best=0;
        while(begin<n){const int end=int(std::upper_bound(prefix.begin()+begin+1,prefix.end(),prefix[begin]+width+1)-prefix.begin())-1;
            require(end>begin,"prefix binary search always packs a word");for(int j=begin+1;j<end;++j){const int c=prefix[j]-prefix[begin]-1;int longest=1;
                for(int delta=-1;delta<=1;++delta)if(stamp[c+delta]==row-1)longest=std::max(longest,value[c+delta]+1);
                // Consecutive spaces in a row differ by >=2. Overwriting column c
                // cannot destroy a previous-row value needed by any later space.
                value[c]=longest;stamp[c]=row;best=std::max(best,longest);++full_width_oracle_spaces;}
            ++row;begin=end;}generation=row+2;if(best>answer.longest)answer={width,best};}
    return answer;}
void random_tests(){std::mt19937 rng(20180419);
    for(int test=0;test<450;++test){const int n=1+int(rng()%25);Lengths v(n);for(int&x:v)x=1+int(rng()%(test<300?12:80));all_widths(v,false);++random_inputs;
        Words text=words(v);for(auto&word:text)for(char&c:word)c=char((rng()&1?'a':'A')+rng()%26);const auto before=text;const auto a=api(v);++api_calls;
        require(same(space_river::best_space_river_words(text),a)&&text==before,"letters/case do not affect layout");++metamorphic;
        const int width=minimum(v)+int(rng()%(total(v)-minimum(v)+1));Lengths scaled=v;
        if(*std::max_element(v.begin(),v.end())<=39){for(int&x:scaled)x=2*(x+1)-1;
            auto old=fixed(v,width),changed=fixed(scaled,2*(width+1)-1);
            require(changed.line_count==old.line_count&&changed.longest<=old.longest,"affine coordinate scaling preserves wrap and removes diagonal possibilities");++metamorphic;}
        v.push_back(minimum(v));require(api(v).longest>=a.longest,"appending a fitting word cannot remove old rivers");++metamorphic;
        if(test<50)require(same(full_width_oracle(Lengths(v.begin(),v.end()-1)),a),"timestamp oracle versus all small literal widths");}
}
void writer_check(const Words&text,Result expected){std::ostringstream output;output<<std::hex<<std::setprecision(3);output.width(23);output.fill('#');const auto flags=output.flags();
    ++api_calls;space_river::write_best_space_river(output,text);require(flags==output.flags()&&output.precision()==3&&output.width()==23&&output.fill()=='#',"writer preserves all caller format");
    require(output.str()==std::to_string(expected.width)+" "+std::to_string(expected.longest)+"\n","source output format");}
void api_cases(){
    require(same(api({1}),{1,0})&&same(api({80}),{80,0}),"singleton extension");
    require(same(api({1,1}),{3,1})&&same(api({80,80}),{161,1}),"two words");
    require(same(api({1,1,1}),{3,1}),"plateau and final one-row tie");
    require(fixed({1,1,1,1,1,1},3).longest==3&&fixed({1,1,1,1,1,1},5).longest==2,"river can decrease with width");
    require(fixed({1,1,3,1,1},3).longest==1,"one-word middle row breaks river");
    require(fixed({1,1,2,2,1,1},3).longest==1,"trailing padding cannot bridge rows");
    auto reject_lengths=[&](const Lengths&v){bool caught=false;++api_calls;try{(void)space_river::best_space_river(v);}catch(const std::invalid_argument&){caught=true;}require(caught,"invalid lengths accepted");++invalid_cases;
        caught=false;++api_calls;try{(void)space_river::longest_river_at_width(v,1000);}catch(const std::invalid_argument&){caught=true;}require(caught,"fixed API lengths validation");};
    reject_lengths({});reject_lengths(Lengths(2501,1));reject_lengths({0});reject_lengths({-1});reject_lengths({81});reject_lengths({INT_MIN});reject_lengths({INT_MAX});reject_lengths({1,0,2});
    for(int width:std::array<int,4>{INT_MIN,-1,0,79}){bool caught=false;++api_calls;try{(void)space_river::longest_river_at_width(Lengths{80,1},width);}catch(const std::invalid_argument&){caught=true;}require(caught,"invalid line width accepted");++invalid_cases;}
    auto reject_words=[&](const Words&v){const auto before=v;bool caught=false;++api_calls;try{(void)space_river::best_space_river_words(v);}catch(const std::invalid_argument&){caught=true;}require(caught&&v==before,"invalid words accepted or changed");++invalid_cases;
        std::ostringstream out;caught=false;++api_calls;try{space_river::write_best_space_river(out,v);}catch(const std::invalid_argument&){caught=true;}require(caught&&out.str().empty(),"writer invalid before output");};
    reject_words({});reject_words(Words(2501,"a"));reject_words({""});reject_words({std::string(81,'a')});reject_words({"ab1"});reject_words({"a b"});reject_words({"a\tb"});reject_words({"a\nb"});reject_words({"!"});reject_words({std::string("a\0b",3)});reject_words({"é"});
    writer_check({"a","B","c"},{3,1});writer_check({std::string(80,'z')},{80,0});
    std::string word;std::istringstream source1("The Yangtze is the third longest river in Asia and the longest in the world to flow entirely in one country");Words t1;while(source1>>word)t1.push_back(word);
    require(t1.size()==21,"official sample1 word count");++api_calls;require(same(space_river::best_space_river_words(t1),{15,5}),"official sample1");writer_check(t1,{15,5});
    std::istringstream source2("When two or more rivers meet at a confluence other than the sea the resulting merged river takes the name of one of those rivers");Words t2;while(source2>>word)t2.push_back(word);
    require(t2.size()==25,"official sample2 word count");++api_calls;require(same(space_river::best_space_river_words(t2),{21,6}),"official sample2");writer_check(t2,{21,6});
    for(int call=0;call<100;++call){require(same(api({1,1,3,1,1}),api({1,1,3,1,1})),"repeat state");auto a=fixed({80,1,1},INT_MAX);require(a.line_count==1&&a.longest==1&&!a.next_width,"INT_MAX width without allocating columns");}
}
struct MaxRecord{std::string name;Result answer;bool full_oracle;};std::vector<MaxRecord> maximum_cases;
void maximum_case(const std::string&name,const Lengths&v,std::optional<Result>expected,bool full){const auto before=v;const Result answer=api(v);
    if(expected){require(same(answer,*expected),"closed-form maximum family");}if(full)require(same(answer,full_width_oracle(v)),"maximum every-width independent oracle");
    require(v==before,"maximum input unchanged");std::vector<int> widths{minimum(v),minimum(v)+1,answer.width,std::max(minimum(v),answer.width-1),answer.width+1,total(v),total(v)+1};
    for(int w:widths){auto literal=character_grid(v,w);auto actual=fixed(v,w);require(actual.longest==literal.river&&actual.line_count==int(literal.rows.size()),"maximum selected widths literal character grid");}
    auto huge=fixed(v,INT_MAX);require(huge.line_count==1&&huge.longest==1&&!huge.next_width,"maximum huge width");writer_check(words(v),answer);maximum_cases.push_back({name,answer,full});}
void maximum(){const int n=2500;maximum_case("2500 one-letter words",Lengths(n,1),Result{3,1250},false);maximum_case("2500 length80 words,total202499",Lengths(n,80),Result{161,1250},false);
    Lengths v(n);for(int i=0;i<n;++i)v[i]=(i&1)?1:80;maximum_case("alternating80and1",v,Result{82,1250},false);
    std::mt19937 rng(20180419);for(int&x:v)x=1+int(rng()%80);maximum_case("full random1..80",v,std::nullopt,true);
    for(int&x:v){x=41+int(rng()%40);}maximum_case("full random41..80",v,std::nullopt,true);
    for(int i=0;i<n;++i){v[i]=1+i%80;}maximum_case("periodic1..80",v,std::nullopt,false);
    for(int i=0;i<n;++i){v[i]=1+((i*37)^(i/7))%80;}maximum_case("bit-mixed1..80",v,std::nullopt,false);
}
int main(){try{const auto start=std::chrono::steady_clock::now();api_cases();exhaustive();random_tests();maximum();rusage usage{};getrusage(RUSAGE_SELF,&usage);
 std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"exhaustiveLengthInputs\":"<<exhaustive_inputs<<",\"literalIntegerWidths\":"<<literal_widths<<",\"literalGridCells\":"<<literal_cells
 <<",\"nextChangeChecks\":"<<next_change_checks<<",\"literalPathCalls\":"<<literal_path_calls<<",\"randomInputs\":"<<random_inputs<<",\"metamorphicChecks\":"<<metamorphic<<",\"invalidCases\":"<<invalid_cases
 <<",\"fullWidthOracleIntegerWidths\":"<<full_width_oracle_widths<<",\"fullWidthOracleSpaceUpdates\":"<<full_width_oracle_spaces<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<",\"maximumCases\":[";
 bool comma=false;for(const auto&x:maximum_cases){if(comma)std::cout<<',';comma=true;std::cout<<"{\"name\":\""<<x.name<<"\",\"width\":"<<x.answer.width<<",\"longest\":"<<x.answer.longest<<",\"fullWidthOracle\":"<<(x.full_oracle?"true":"false")<<'}';}std::cout<<"]}\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sanitize',action='store_true');parser.add_argument('--article',default=str(Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/word-wrap-sparse-space-river-dp.mdx'));args=parser.parse_args()
    article=Path(args.article).read_text();fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
    assert len(fences)==1 and '<details' not in article
    assert re.findall(r'^## (.+)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料']
    cpp=fences[0];flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-space-river-cpp-') as directory:
        source=Path(directory)/'check.cpp';binary=Path(directory)/'check';source.write_text(cpp+'\n'+HARNESS)
        subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
        env=os.environ.copy()
        if args.sanitize:env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1'
        result=subprocess.run([str(binary)],check=True,text=True,capture_output=True,env=env)
    print(json.dumps({'articleSha256':hashlib.sha256(article.encode()).hexdigest(),'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'sanitize':args.sanitize,'compilerFlags':flags,**json.loads(result.stdout)},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
