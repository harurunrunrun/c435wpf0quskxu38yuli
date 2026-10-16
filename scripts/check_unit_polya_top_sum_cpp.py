#!/usr/bin/env python3
"""Compile the article C++20 API and compare with independent exact oracles."""
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
#include <boost/multiprecision/cpp_dec_float.hpp>
#include <boost/multiprecision/cpp_int.hpp>
#include <chrono>
#include <climits>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <map>
#include <random>
#include <string>
#include <sys/resource.h>
using boost::multiprecision::cpp_int;
using Decimal = boost::multiprecision::cpp_dec_float_100;
std::uint64_t checks=0,api_calls=0,checksum=0,composition_states=0,composition_parameters=0;
std::uint64_t owner_histories=0,history_states=0,history_parameters=0,exact_tail_terms=0,exact_calls=0;
std::uint64_t random_rank_queries=0,metamorphic=0,boundary_calls=0,invalid_calls=0;
long double max_absolute_error=0;
void require(bool ok,const char*message){++checks;if(!ok)throw std::runtime_error(message);}
void record(std::uint64_t value){checksum=checksum*1000003ULL+value;}
double api(int n,int d,int r){++api_calls;double answer=unit_polya::expected_top_r_unit_polya(n,d,r);
    require(std::isfinite(answer),"answer finite");require(answer>=r&&answer<=n+d,"answer in physical bounds");
    record(static_cast<std::uint64_t>(std::llround(answer*1000000)));return answer;}
void close(double actual,long double expected,long double tolerance=0.00000006L){
    const long double error=std::fabs(static_cast<long double>(actual)-expected);max_absolute_error=std::max(max_absolute_error,error);
    require(error<tolerance,"independent exact expectation differs beyond rounding bound");}
std::vector<cpp_int> exact_binomial;
const cpp_int& choose(int n,int k){static const cpp_int zero=0;if(n<0||k<0||k>n)return zero;return exact_binomial[n*501+k];}
void prepare_exact(){exact_binomial.resize(1000*501);for(int a=0;a<1000;++a){exact_binomial[a*501]=1;
    for(int b=1;b<=std::min(a,500);++b)exact_binomial[a*501+b]=choose(a-1,b-1)+choose(a-1,b);}}
long double ratio(const cpp_int&num,const cpp_int&den){return (Decimal(num.convert_to<std::string>())/Decimal(den.convert_to<std::string>())).convert_to<long double>();}
// Independent full-range exact oracle, used ONLY in verification. For each
// increment threshold t, U_j=C(n,j)*C(n+d-j*t-1,d-j*t) counts marked j-subsets
// whose entries are >=t. Binomial inversion counts exact marked-set sizes, and
// summing the indicators [size>=k],1<=k<=r gives coefficients a_1=1,
// a_j=0 for2<=j<=r, a_j=(-1)^(j-r)C(j-2,r-1) for j>r.
// All alternating arithmetic is arbitrary-precision integer, never floating.
std::pair<cpp_int,cpp_int> exact_tail(int n,int d,int r){++exact_calls;
    const cpp_int denominator=choose(n+d-1,d);if(r==0)return {0,denominator};cpp_int numerator=r*denominator;
    for(int threshold=1;threshold<=d;++threshold){const int maximum=std::min(n,d/threshold);
        for(int j=1;j<=maximum;++j){if(j>=2&&j<=r)continue;++exact_tail_terms;
            const int remaining=d-j*threshold;cpp_int term=choose(n,j)*choose(n+remaining-1,remaining);
            if(j>r){term*=choose(j-2,r-1);if((j-r)&1)numerator-=term;else numerator+=term;}
            else numerator+=term;}}
    require(numerator>=r*denominator&&numerator<=(n+d)*denominator,"exact-tail physical integer bounds");return {numerator,denominator};}
void exact_check(int n,int d,int r){const auto[num,den]=exact_tail(n,d,r);close(api(n,d,r),ratio(num,den));}
void all_compositions(){
    for(int n=1;n<=8;++n)for(int d=0;d<=12;++d){std::vector<int> x(n,0);std::vector<std::uint64_t> sum(n+1,0);std::uint64_t count=0;
        auto enumerate=[&](auto&&self,int position,int remaining)->void{
            if(position+1==n){x[position]=remaining;std::vector<int> descending=x;std::sort(descending.rbegin(),descending.rend());
                int value=0;for(int r=1;r<=n;++r){value+=descending[r-1]+1;sum[r]+=value;}++count;++composition_states;return;}
            for(int value=0;value<=remaining;++value){x[position]=value;self(self,position+1,remaining-value);}};
        enumerate(enumerate,0,d);require(cpp_int(count)==choose(n+d-1,d),"literal all compositions count");
        for(int r=0;r<=n;++r){const long double expected=static_cast<long double>(sum[r])/count;close(api(n,d,r),expected,1e-10L);
            auto[num,den]=exact_tail(n,d,r);require(num*count==cpp_int(sum[r])*den,"tail oracle self-validation against all compositions");}
        ++composition_parameters;}
}
void all_owner_histories(){
    for(int n=1;n<=5;++n)for(int d=0;d<=9;++d){std::vector<int> weight(n,1);std::vector<std::uint64_t> numerator(n+1,0);std::map<std::vector<int>,std::uint64_t> states;
        auto histories=[&](auto&&self,int time,std::uint64_t path_numerator)->void{
            if(time==d){std::vector<int> sorted=weight;std::sort(sorted.rbegin(),sorted.rend());int value=0;
                for(int r=1;r<=n;++r){value+=sorted[r-1];numerator[r]+=path_numerator*value;}states[weight]+=path_numerator;++owner_histories;return;}
            for(int owner=0;owner<n;++owner){const int old=weight[owner]++;self(self,time+1,path_numerator*old);--weight[owner];}};
        histories(histories,0,1);std::uint64_t denominator=1,factorial=1;
        for(int time=0;time<d;++time)denominator*=n+time;
        for(int factor=1;factor<=d;++factor)factorial*=factor;
        std::uint64_t probability_sum=0;for(const auto&[state,mass]:states){(void)state;require(mass==factorial,"each terminal composition has same exact history mass");probability_sum+=mass;++history_states;}
        require(probability_sum==denominator,"exact owner probabilities sum1");
        for(int r=0;r<=n;++r){close(api(n,d,r),static_cast<long double>(numerator[r])/denominator,1e-10L);
            const auto[num,den]=exact_tail(n,d,r);require(num*denominator==cpp_int(numerator[r])*den,"exact tail matches path-probability oracle");}++history_parameters;}
}
void random_and_ranks(){std::mt19937 rng(20180419);
    for(int test=0;test<180;++test){const int n=2+int(rng()%24),d=int(rng()%31);double previous=0;long double previous_delta=1e6;
        for(int r=0;r<=n;++r){const auto[num,den]=exact_tail(n,d,r);const double answer=api(n,d,r);close(answer,ratio(num,den));++random_rank_queries;
            if(r){const long double delta=answer-previous;require(delta<=previous_delta+1e-9L,"expected sorted marginal values nonincreasing");previous_delta=delta;++metamorphic;}
            require(answer>=previous,"top-r sum monotone in r");previous=answer;
            const double later=api(n,d+1,r);require(later>=answer-1e-9&&later<=answer+1+1e-9,"one reinforcement changes top-r by at most1");++metamorphic;}
        require(previous==n+d,"all-r totals sum to conserved total");}
}
void boundary(){
    for(int n=1;n<=500;++n)for(int d=0;d<=500;++d){require(api(n,d,n)==n+d,"r=N exact total");require(api(n,d,0)==0,"r0 exact zero");boundary_calls+=2;}
    for(int n=1;n<=500;++n){for(int r=0;r<=n;++r){require(api(n,0,r)==r,"zero-step top-r exact");++boundary_calls;
        close(api(n,1,r),r==0?0:r+1,1e-9L);++boundary_calls;}}
    for(int d=0;d<=500;++d){std::uint64_t sum=0;for(int x=0;x<=d;++x)sum+=1+std::max(x,d-x);
        close(api(2,d,1),static_cast<long double>(sum)/(d+1));++boundary_calls;}
}
void writer_check(int n,int d,int r){std::ostringstream output;output<<std::scientific<<std::setprecision(3);output.width(17);output.fill('#');const auto flags=output.flags();const auto precision=output.precision();
    unit_polya::write_expected_top_r(output,n,d,r);++api_calls;require(flags==output.flags()&&precision==output.precision()&&output.width()==17&&output.fill()=='#',"writer preserves caller format");
    require(!output.str().empty()&&output.str().back()=='\n',"writer newline");const auto point=output.str().find('.');require(point!=std::string::npos&&output.str().size()-point==14,"writer fixed12 fractional digits");
    std::istringstream input(output.str());long double value=-1;require(bool(input>>value),"writer parse");std::string extra;require(!(input>>extra),"writer exactly one scalar");
    const auto[num,den]=exact_tail(n,d,r);require(std::fabs(value-ratio(num,den))<0.000001L,"writer source absolute tolerance");}
void invalids_and_state(){
    for(auto [n,d,r]:std::vector<std::array<int,3>>{{0,1,0},{-1,1,1},{501,1,1},{INT_MIN,1,1},{INT_MAX,1,1},{2,-1,1},{2,501,1},{2,INT_MIN,1},{2,INT_MAX,1},{2,1,-1},{2,1,3},{2,1,INT_MIN},{2,1,INT_MAX}}){
        bool rejected=false;try{(void)api(n,d,r);}catch(const std::invalid_argument&){rejected=true;}require(rejected,"invalid parameters accepted");++invalid_calls;
        std::ostringstream out;rejected=false;++api_calls;try{unit_polya::write_expected_top_r(out,n,d,r);}catch(const std::invalid_argument&){rejected=true;}
        require(rejected&&out.str().empty(),"writer emits nothing on invalid input");exact_check(3,4,2);}
    for(int mode:std::array<int,3>{FE_DOWNWARD,FE_UPWARD,FE_TOWARDZERO}){require(std::fesetround(mode)==0,"rounding mode supported");bool rejected=false;
        ++api_calls;try{(void)unit_polya::expected_top_r_unit_polya(3,4,2);}catch(const std::invalid_argument&){rejected=true;}
        require(rejected&&std::fegetround()==mode,"non-nearest rejected without mutating floating environment");
        require(std::fesetround(FE_TONEAREST)==0,"restore nearest rounding");++invalid_calls;exact_check(3,4,2);}
    const double original=api(4,7,2);for(int call=0;call<100;++call){require(api(4,7,2)==original,"no cross-call state");require(api(500,500,500)==1000,"independent size/r parameters");require(api(1,500,1)==501,"one person");}
    writer_check(2,3,1);writer_check(3,3,2);writer_check(5,10,3);writer_check(500,500,0);writer_check(500,500,500);
    close(api(2,3,1),3.5L,1e-12L);close(api(3,3,2),4.9L,1e-12L);close(api(5,10,3),12.256743256743256743L,1e-11L);
}
struct Maximum{int n,d,r;double answer;long double absolute_error;};std::vector<Maximum> maximum_cases;
void maximum(){for(auto[n,d,r]:std::vector<std::array<int,3>>{{500,500,1},{500,500,2},{500,500,3},{500,500,17},{500,500,250},{500,500,499},{500,500,500},{500,499,1},{499,500,17},{250,500,125},{347,431,109},{1,500,1},{500,1,499}}){
    const auto[num,den]=exact_tail(n,d,r);const long double expected=ratio(num,den);const double answer=api(n,d,r);close(answer,expected);
    maximum_cases.push_back({n,d,r,answer,std::fabs(static_cast<long double>(answer)-expected)});writer_check(n,d,r);}}
int main(){try{const auto start=std::chrono::steady_clock::now();require(std::fegetround()==FE_TONEAREST,"initial rounding nearest");prepare_exact();invalids_and_state();all_compositions();all_owner_histories();random_and_ranks();boundary();maximum();
    rusage usage{};getrusage(RUSAGE_SELF,&usage);std::cout<<std::setprecision(18)<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"compositionParameterPairs\":"<<composition_parameters<<",\"allWeakCompositions\":"<<composition_states
      <<",\"historyParameterPairs\":"<<history_parameters<<",\"ownerHistories\":"<<owner_histories<<",\"historyTerminalStates\":"<<history_states<<",\"exactTailOracleCalls\":"<<exact_calls<<",\"exactTailIntegerTerms\":"<<exact_tail_terms
      <<",\"randomRankQueries\":"<<random_rank_queries<<",\"metamorphicChecks\":"<<metamorphic<<",\"boundaryApiCalls\":"<<boundary_calls<<",\"invalidCases\":"<<invalid_calls
      <<",\"maximumAbsoluteError\":"<<max_absolute_error<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<",\"maximumCases\":[";
    bool comma=false;for(const auto&x:maximum_cases){if(comma)std::cout<<',';comma=true;std::cout<<"{\"n\":"<<x.n<<",\"steps\":"<<x.d<<",\"r\":"<<x.r<<",\"answer\":"<<x.answer<<",\"absoluteError\":"<<x.absolute_error<<'}';}std::cout<<"]}\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--sanitize',action='store_true');parser.add_argument('--article',default=str(Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/polya-urn-uniform-composition-top-r-sum.mdx'));args=parser.parse_args()
    article=Path(args.article).read_text();fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
    assert len(fences)==1 and '<details' not in article
    assert re.findall(r'^## (.+)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料']
    cpp=fences[0];flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-polya-top-r-cpp-') as directory:
        source=Path(directory)/'check.cpp';binary=Path(directory)/'check';source.write_text(cpp+'\n'+HARNESS)
        subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
        env=os.environ.copy()
        if args.sanitize:env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1'
        run=subprocess.run([str(binary)],check=True,text=True,capture_output=True,env=env)
    result=json.loads(run.stdout)
    print(json.dumps({'articleSha256':hashlib.sha256(article.encode()).hexdigest(),'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'sanitize':args.sanitize,'compilerFlags':flags,**result},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
