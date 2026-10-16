#!/usr/bin/env python3
"""Compile the actual visible MDX C++20 fence; independent cuts and finite two-flow oracles."""
from pathlib import Path
import shutil
import os,re,subprocess,sys,tempfile
args=[a for a in sys.argv[1:] if a!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/two-source-concave-flow-mixture-decomposition.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected exactly one complete visible C++ fence')
TESTS=r'''
#include <chrono>
#include <cstdlib>
#include <functional>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>
#include <string>
#include <tuple>
using I=std::int64_t;
using Pipes=std::vector<MixturePipe>;
std::uint64_t checks=0, small_graphs=0, finite_assignments=0, finite_valid=0, constructions=0;
std::uint64_t checksum=0;
void require(bool yes,const char* why) {
    ++checks;if(!yes){std::cerr<<"FAIL: "<<why<<'\n';std::exit(1);}
}
struct Cuts {I a,b,z;};
// Every original vertex subset, with ordinary undirected cut capacities.
// This oracle never augments a path and never uses the Dinic implementation.
Cuts every_cut(int n,const Pipes& pipes,int s1,int s2,int sink) {
    const I inf=std::numeric_limits<I>::max();Cuts out{inf,inf,inf};
    for(int mask=0;mask<(1<<n);++mask) if(!(mask>>sink&1)) {
        I cap=0;for(const auto& e:pipes)if(((mask>>e.u)^(mask>>e.v))&1)cap+=e.capacity;
        if(mask>>s1&1)out.a=std::min(out.a,cap);
        if(mask>>s2&1)out.b=std::min(out.b,cap);
        if((mask>>s1&1)&&(mask>>s2&1))out.z=std::min(out.z,cap);
    }
    return out;
}
// Enumerate BOTH signed species on every edge, same direction, shared capacity.
// Check each species' divergence directly; no cut inequalities or decomposition.
std::vector<std::vector<bool>> every_finite_flow(int n,const Pipes& pipes,int scale) {
    int limit=0;for(const auto& e:pipes)if(e.u==2||e.v==2)limit+=int(e.capacity)*scale;
    std::vector<std::vector<bool>> possible(limit+1,std::vector<bool>(limit+1));
    std::vector<std::vector<std::pair<int,int>>> states;
    for(const auto& e:pipes) {
        const int cap=int(e.capacity)*scale;states.push_back({});
        for(int f=-cap;f<=cap;++f)for(int w=-cap;w<=cap;++w)
            if(std::abs(f)+std::abs(w)<=cap && (f==0||w==0||(f<0)==(w<0)))
                states.back().push_back({f,w});
    }
    std::array<I,8> f{},w{};
    auto visit=[&](auto&& self,std::size_t at)->void {
        if(at==pipes.size()) {
            ++finite_assignments;
            for(int v=0;v<n;++v) {
                if(v!=0&&v!=2&&f[v]!=0)return;
                if(v!=1&&v!=2&&w[v]!=0)return;
            }
            if(f[0]<0||w[1]<0||f[2]!=-f[0]||w[2]!=-w[1])return;
            require(f[0]<=limit&&w[1]<=limit,"finite flow cannot exceed sink incident capacity");
            possible[f[0]][w[1]]=true;++finite_valid;return;
        }
        const auto& e=pipes[at];
        for(const auto& [a,b]:states[at]) {
            f[e.u]+=a;f[e.v]-=a;w[e.u]+=b;w[e.v]-=b;
            self(self,at+1);
            f[e.u]-=a;f[e.v]+=a;w[e.u]-=b;w[e.v]+=b;
        }
    };
    visit(visit,0);return possible;
}
long double objective(long double x,long double y,ExactRatio alpha,ExactRatio viscosity) {
    if(x<=0||y<=0)return 0;
    const long double weight=static_cast<long double>(alpha.num)/alpha.den;
    const long double v=static_cast<long double>(viscosity.num)/viscosity.den;
    return std::pow(x/v,weight)*std::pow(y,1-weight);
}
// Independently search the entire cut-feasible frontier, without alpha*Z/clamp.
long double search_objective(Cuts cut,ExactRatio alpha,ExactRatio viscosity) {
    long double low=0,high=cut.a;
    auto score=[&](long double x){return objective(x,std::min(static_cast<long double>(cut.b),cut.z-x),alpha,viscosity);};
    for(int iteration=0;iteration<200;++iteration) {
        const long double p=low+(high-low)/3,q=high-(high-low)/3;
        if(score(p)<score(q))low=p;else high=q;
    }
    return std::max({score(0),score(cut.a),score((low+high)/2)});
}
void validate(int n,const Pipes& pipes,int s1,int s2,int sink,ExactRatio alpha,ExactRatio viscosity,
              const MixtureResult& result,Cuts expected,bool compare_objective=true) {
    ++constructions;
    require(result.single_first==expected.a&&result.single_second==expected.b&&result.total==expected.z,
            "three maxflows equal independent cut oracle");
    require(result.scale==alpha.den,"exact scale");
    const I q=result.scale,x=result.first_scaled,y=result.second_scaled;
    require(x>=0&&y>=0&&x<=expected.a*q&&y<=expected.b*q&&x+y==expected.z*q,"optimal boundary feasibility");
    require(result.edge_scaled.size()==pipes.size()&&result.edge_rates.size()==pipes.size(),"edge result shape");
    std::vector<std::array<I,2>> balance(n);
    std::vector<std::array<long double,2>> displayed_balance(n);
    const long double v=static_cast<long double>(viscosity.num)/viscosity.den;
    for(std::size_t i=0;i<pipes.size();++i) {
        const auto& e=pipes[i];const auto [f,w]=result.edge_scaled[i];
        require((f>=0&&w>=0)||(f<=0&&w<=0),"species never oppose on one edge");
        require(std::abs(f)+std::abs(w)<=e.capacity*q,"exact shared capacity");
        balance[e.u][0]+=f;balance[e.v][0]-=f;balance[e.u][1]+=w;balance[e.v][1]-=w;
        const auto [ff,ww]=result.edge_rates[i];
        require(std::isfinite(ff)&&std::isfinite(ww),"finite edge rates");
        require(std::fabs(ff*v-static_cast<long double>(f)/q)<1e-9L,"species1 exact-unit conversion");
        require(std::fabs(ww-static_cast<long double>(w)/q)<1e-9L,"species2 exact-unit conversion");
        // Check the values after actual fixed decimal output, not only raw floats.
        std::stringstream line;line<<std::fixed<<std::setprecision(12)<<ff<<' '<<ww;
        long double fd,wd;line>>fd>>wd;
        require(std::fabs(fd)*v+std::fabs(wd)<=e.capacity+1e-8L,"displayed shared capacity");
        require(fd*wd>=-1e-16L,"displayed no reverse directions");
        displayed_balance[e.u][0]+=fd;displayed_balance[e.v][0]-=fd;
        displayed_balance[e.u][1]+=wd;displayed_balance[e.v][1]-=wd;
    }
    for(int u=0;u<n;++u) {
        I a=u==s1?x:u==sink?-x:0,b=u==s2?y:u==sink?-y:0;
        require(balance[u][0]==a&&balance[u][1]==b,"both exact species conservation at every vertex");
        require(std::fabs(displayed_balance[u][0]-static_cast<long double>(a)/q/v)<1e-8L,
                "displayed species1 conservation");
        require(std::fabs(displayed_balance[u][1]-static_cast<long double>(b)/q)<1e-8L,
                "displayed species2 conservation");
    }
    require(std::fabs(result.first_rate-static_cast<long double>(x)/q/v)<1e-9L,"first arrival");
    require(std::fabs(result.second_rate-static_cast<long double>(y)/q)<1e-9L,"second arrival");
    require(std::fabs(result.value-objective(static_cast<long double>(x)/q,static_cast<long double>(y)/q,alpha,viscosity))<1e-9L,
            "reported objective equals arrivals");
    if(compare_objective)require(std::fabs(result.value-search_objective(expected,alpha,viscosity))<1e-8L,
                                 "global continuous optimum / independent ternary search of cut frontier");
    checksum=checksum*1000003+std::uint64_t(x)*97+std::uint64_t(y);
}
I integer_power(I x,int power){I result=1;while(power--)result*=x;return result;}
void exhaustive_graphs() {
    for(int n:{3,4}) {
        std::vector<std::pair<int,int>> pairs;
        for(int u=0;u<n;++u)for(int w=u+1;w<n;++w)pairs.push_back({u,w});
        int count=1;for(std::size_t i=0;i<pairs.size();++i)count*=3;
        for(int code=0;code<count;++code) {
            int remaining=code;Pipes pipes;bool binary=true;
            for(const auto& [u,w]:pairs) {
                int cap=remaining%3;remaining/=3;binary&=cap<=1;
                if(cap) pipes.push_back({u,w,cap});
            }
            ++small_graphs;
            const Cuts cut=every_cut(n,pipes,0,1,2);
            const auto integral=every_finite_flow(n,pipes,1);
            for(int a=0;a<int(integral.size());++a)for(int b=0;b<int(integral.size());++b)
                require(integral[a][b]==(a<=cut.a&&b<=cut.b&&a+b<=cut.z),
                        "complete integer two-species region / literal all edge assignments");
            for(ExactRatio alpha:{ExactRatio{1,100},ExactRatio{1,2},ExactRatio{99,100}}) {
                const ExactRatio viscosity{31415926535LL,10000000000LL};
                const auto result=optimize_two_source_mixture(n,pipes,0,1,2,alpha,viscosity);
                validate(n,pipes,0,1,2,alpha,viscosity,result,cut);
            }
            if(binary) for(int q:{2,3}) {
                const auto finite=every_finite_flow(n,pipes,q);
                for(int p=1;p<q;++p) {
                    I best=0;
                    for(int a=0;a<int(finite.size());++a)for(int b=0;b<int(finite.size());++b)
                        if(finite[a][b])best=std::max(best,integer_power(a,p)*integer_power(b,q-p));
                    const ExactRatio alpha{p,q},viscosity{1,1};
                    const auto result=optimize_two_source_mixture(n,pipes,0,1,2,alpha,viscosity);
                    validate(n,pipes,0,1,2,alpha,viscosity,result,cut);
                    require(integer_power(result.first_scaled,p)*integer_power(result.second_scaled,q-p)==best,
                            "exact optimal objective / every finite two-species assignment at q=2,3");
                }
            }
        }
    }
}
void random_and_boundaries() {
    std::mt19937 random(2017);
    for(int iteration=0;iteration<512;++iteration) {
        int n=3+int(random()%6);Pipes pipes;
        // Generate orientations independently without ever creating a self loop.
        for(int u=0;u<n;++u)for(int v=u+1;v<n;++v)if(random()%3==0) {
            bool swap=random()%2;pipes.push_back({swap?v:u,swap?u:v,I(random()%11)});
        }
        int s1=random()%n,s2=(s1+1+random()%(n-1))%n,t=random()%n;
        while(t==s1||t==s2)t=(t+1)%n;
        const I q=2+random()%9999999999ULL,p=1+random()%(q-1);
        const ExactRatio alpha{p,q},viscosity{99999999999LL,10000000000LL};
        const auto cut=every_cut(n,pipes,s1,s2,t);
        const auto result=optimize_two_source_mixture(n,pipes,s1,s2,t,alpha,viscosity);
        validate(n,pipes,s1,s2,t,alpha,viscosity,result,cut);
        const auto unit=optimize_two_source_mixture(n,pipes,s1,s2,t,alpha,{1,1});
        require(unit.edge_scaled==result.edge_scaled&&unit.first_scaled==result.first_scaled,
                "viscosity does not change exact normalized construction");
        std::reverse(pipes.begin(),pipes.end());for(auto& e:pipes)std::swap(e.u,e.v);
        const auto reversed=optimize_two_source_mixture(n,pipes,s1,s2,t,alpha,viscosity);
        validate(n,pipes,s1,s2,t,alpha,viscosity,reversed,cut);
        require(std::fabs(reversed.value-result.value)<1e-9L,"pipe order/orientation invariance");
    }
    const ExactRatio half{1,2},one{1,1};
    for(const auto& pipes:std::vector<Pipes>{{},{{0,2,0}},{{0,2,3}},{{1,2,4}},{{0,1,10}}}) {
        const auto result=optimize_two_source_mixture(3,pipes,0,1,2,half,one);
        validate(3,pipes,0,1,2,half,one,result,every_cut(3,pipes,0,1,2));
        require(result.value==0,"zero/one unreachable source objective boundary");
    }
    for(auto [pipes,alpha,expected]:std::vector<std::tuple<Pipes,ExactRatio,I>>{
        {{{0,2,1},{1,2,10}},{99,100},100},
        {{{0,2,10},{1,2,1}},{1,100},1000},
        {{{0,3,10},{1,3,10},{3,2,10}},{3,10},30}}) {
        int n=pipes.size()==3?4:3;
        const auto result=optimize_two_source_mixture(n,pipes,0,1,2,alpha,one);
        validate(n,pipes,0,1,2,alpha,one,result,every_cut(n,pipes,0,1,2));
        require(result.first_scaled==expected,"lower clamp / upper clamp / interior optimum");
    }
    // Explicitly reverse an already saturated undirected residual pair.
    mixture_detail::Dinic graph(2);auto handle=graph.add(0,1,10,10);
    require(graph.flow(0,1)==10&&graph.residual(handle)==0,"undirected forward saturation");
    require(graph.flow(1,0)==20&&graph.residual(handle)==20,"reverse residual cancels then reverses original flow");
    Pipes sample1{{1,3,8},{3,5,1},{2,5,1},{3,4,5},{0,4,7},{2,4,3}};
    auto first=optimize_two_source_mixture(6,sample1,0,1,2,{66,100},{3,1});
    validate(6,sample1,0,1,2,{66,100},{3,1},first,every_cut(6,sample1,0,1,2));
    require(std::fabs(first.value-1.02037965897L)<1e-10L,"official sample1 objective");
    Pipes sample2{{0,1,10},{1,2,10},{2,3,10},{3,4,10},{2,4,10}};
    auto second=optimize_two_source_mixture(5,sample2,0,1,2,half,one);
    validate(5,sample2,0,1,2,half,one,second,every_cut(5,sample2,0,1,2));
    require(std::fabs(second.value-5)<1e-12L,"official sample2 objective");
}
void maximum() {
    const int n=200;Pipes dense;
    for(int u=0;u<n;++u)for(int v=u+1;v<n;++v)dense.push_back({u,v,10});
    for(ExactRatio alpha:{parse_decimal_10("0.0100000001"),parse_decimal_10("0.9899999999"),
                          parse_decimal_10("0.9999999999"),ExactRatio{5000000000LL,10000000000LL}}) {
        const ExactRatio viscosity=parse_decimal_10("9.9999999999");
        auto result=optimize_two_source_mixture(n,dense,0,1,2,alpha,viscosity);
        validate(n,dense,0,1,2,alpha,viscosity,result,{1990,1990,1990});
        require(result.first_scaled==alpha.num*1990,"maximum density and exact ten-digit allocation");
        require(result.first_scaled+result.second_scaled==19900000000000LL,"maximum scaled total");
    }
    Pipes chain;
    for(int i=1;i<n;++i)chain.push_back({i,i-1,10});
    auto result=optimize_two_source_mixture(n,chain,0,n-2,n-1,{9999999999LL,10000000000LL},{10,1});
    validate(n,chain,0,n-2,n-1,{9999999999LL,10000000000LL},{10,1},result,{10,10,10});
}
template<class F> void invalid(F action) {
    bool threw=false;try{action();}catch(const std::invalid_argument&){threw=true;}
    require(threw,"invalid API arguments reject before arithmetic or indexing");
}
void invalid_and_parser() {
    for(auto [text,num,den]:std::vector<std::tuple<std::string,I,I>>{
        {"0",0,1},{"000.0000000000",0,1},{"01.0100",101,100},
        {"0.9999999999",9999999999LL,10000000000LL},{"10.0000000000",10,1},
        {"922337203.6854775807",std::numeric_limits<I>::max(),10000000000LL}}) {
        auto ratio=parse_decimal_10(text);require(ratio.num==num&&ratio.den==den,"exact reduced decimal parser");
    }
    for(const auto& text:std::vector<std::string>{"",".",".5","1.","+1","-0"," 0.1","0.1 ","1e-1",
        "nan","inf","1..0","0.00000000000","9223372036854775808","922337203.6854775808"})
        invalid([&]{parse_decimal_10(text);});
    auto call=[](int n,const Pipes& e,int s1,int s2,int t,ExactRatio a,ExactRatio v){
        return optimize_two_source_mixture(n,e,s1,s2,t,a,v);
    };
    for(int n:{std::numeric_limits<int>::min(),-1,0,1,2,201,std::numeric_limits<int>::max()})
        invalid([&]{call(n,{},0,1,2,{1,2},{1,1});});
    for(auto terminals:std::vector<std::array<int,3>>{{-1,1,2},{0,3,2},{0,1,3},{0,0,2},{0,1,0},{0,1,1}})
        invalid([&]{call(3,{},terminals[0],terminals[1],terminals[2],{1,2},{1,1});});
    for(const auto& e:std::vector<Pipes>{{{0,0,1}},{{0,3,1}},{{-1,2,1}},{{0,2,-1}},{{0,2,11}},
        {{0,2,std::numeric_limits<I>::min()}},{{0,2,std::numeric_limits<I>::max()}},
        {{0,2,1},{2,0,1}},{{0,1,0},{0,2,0},{1,2,0},{0,1,0}}})
        invalid([&]{call(3,e,0,1,2,{1,2},{1,1});});
    for(auto a:std::vector<ExactRatio>{{0,1},{1,1},{-1,2},{1,0},{1,-1},{1,10000000001LL},
        {std::numeric_limits<I>::min(),2},{std::numeric_limits<I>::max(),10000000000LL},
        {1,std::numeric_limits<I>::max()},{1,std::numeric_limits<I>::min()}})
        invalid([&]{call(3,{},0,1,2,a,{1,1});});
    for(auto v:std::vector<ExactRatio>{{0,1},{1,2},{11,1},{1,0},{1,-1},{1,10000000001LL},
        {std::numeric_limits<I>::max(),10000000000LL},{std::numeric_limits<I>::min(),1}})
        invalid([&]{call(3,{},0,1,2,{1,2},v);});
}
int main() {
    auto started=std::chrono::steady_clock::now();
    invalid_and_parser();exhaustive_graphs();random_and_boundaries();maximum();
    std::cout<<"Mixture C++20: checks="<<checks<<" all_small_graphs="<<small_graphs
             <<" finite_edge_assignments="<<finite_assignments<<" valid_assignments="<<finite_valid
             <<" constructions="<<constructions<<" checksum="<<checksum
             <<" seconds="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()<<'\n';
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-mixture-') as directory:
    source=Path(directory)/'check.cpp';binary=Path(directory)/'check'
    source.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    environment=os.environ.copy()
    if '--sanitize' in sys.argv:
        flags+=['-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
        environment['ASAN_OPTIONS']='detect_leaks=0'
    compiler=os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++') or 'c++'
    subprocess.run([compiler,*flags,str(source),'-o',str(binary)],check=True,timeout=120)
    subprocess.run([str(binary)],check=True,env=environment,timeout=180)
