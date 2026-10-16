#!/usr/bin/env python3
"""Extract visible MDX C++20; independently validate gates and simulate two-mark images."""
from pathlib import Path
import os,re,shutil,subprocess,sys,tempfile
args=[arg for arg in sys.argv[1:] if arg!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/rotated-manhattan-two-mark-boolean-circuit.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected exactly one complete visible C++20 fence')
TESTS=r'''
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <limits>
#include <random>
#include <string>
using Kind=TwoMarkGateKind;
std::uint64_t checks=0,circuits=0,scalar_images=0,batch_images=0,callback_gates=0;
std::uint64_t checksum=0;
std::size_t max_gates=0,max_uses=0;
void require(bool yes,const char* why) {
    ++checks;if(!yes){std::cerr<<"FAIL: "<<why<<'\n';std::exit(1);}
}
void inspect(const TwoMarkCircuit& c,int h,int w,int k) {
    ++circuits;
    require(c.input_count==h*w,"input IDs are image cells only");
    require(!c.gates.empty()&&c.gates.size()<=10000,"one or more gates within original budget");
    require(c.output==c.input_count+int(c.gates.size())-1,"final gate is the answer");
    std::size_t total=0;
    for(std::size_t i=0;i<c.gates.size();++i) {
        const auto& gate=c.gates[i];
        require(!gate.inputs.empty(),"no empty AND/OR/NOT instruction");
        require(gate.kind!=Kind::Not||gate.inputs.size()==1,"NOT has exactly one input");
        for(int id:gate.inputs)require(id>=0&&id<c.input_count+int(i),"only image or previous gate outputs");
        total+=gate.inputs.size();
    }
    require(total==c.input_uses&&total<=1000000,"independent terminal count within original budget");
    const int d=h+w-1;
    if(k==0||k>=d)require(c.gates.size()==2&&total==3,"out-of-range distance uses two-gate false");
    else {
        const int r=d-k;
        require(c.gates.size()==std::size_t(4*d+4*r+1+(r>=2)),"exact generated gate count");
        require(total==std::size_t(2*h*w+4*d+12*r-4),"exact generated terminal count");
    }
    max_gates=std::max(max_gates,c.gates.size());max_uses=std::max(max_uses,total);
}
// Literal, sequential gate interpreter. No diagonals or prefix formulas here.
bool scalar(const TwoMarkCircuit& c,int first,int second) {
    std::vector<unsigned char> memory(c.input_count+c.gates.size());
    memory[first]=memory[second]=1;
    for(std::size_t i=0;i<c.gates.size();++i) {
        const auto& g=c.gates[i];unsigned char value;
        if(g.kind==Kind::Not)value=!memory[g.inputs[0]];
        else if(g.kind==Kind::And) {value=1;for(int id:g.inputs)value&=memory[id];}
        else {value=0;for(int id:g.inputs)value|=memory[id];}
        memory[c.input_count+i]=value;
    }
    ++scalar_images;return memory[c.output];
}
bool direct_distance(int w,int k,int a,int b) {
    return std::abs(a/w-b/w)+std::abs(a%w-b%w)==k;
}
// A second interpreter evaluates 64 independent images in uint64_t lanes.
// NOT complements all lanes; only genuine lanes are compared at the end.
void batch(const TwoMarkCircuit& c,int w,int k,const std::vector<std::pair<int,int>>& pairs) {
    std::vector<std::uint64_t> memory(c.input_count+c.gates.size());
    for(std::size_t begin=0;begin<pairs.size();begin+=64) {
        std::fill(memory.begin(),memory.end(),0);
        const std::size_t count=std::min<std::size_t>(64,pairs.size()-begin);
        for(std::size_t lane=0;lane<count;++lane) {
            const auto [a,b]=pairs[begin+lane];
            require(a!=b&&a>=0&&b>=0&&a<c.input_count&&b<c.input_count,"exactly two distinct black input cells");
            const std::uint64_t bit=std::uint64_t{1}<<lane;
            memory[a]|=bit;memory[b]|=bit;
        }
        for(std::size_t i=0;i<c.gates.size();++i) {
            const auto& gate=c.gates[i];std::uint64_t value;
            if(gate.kind==Kind::Not)value=~memory[gate.inputs[0]];
            else if(gate.kind==Kind::Or) {value=0;for(int id:gate.inputs)value|=memory[id];}
            else {value=~std::uint64_t{0};for(int id:gate.inputs)value&=memory[id];}
            memory[c.input_count+i]=value;
        }
        for(std::size_t lane=0;lane<count;++lane) {
            const auto [a,b]=pairs[begin+lane];
            const bool got=(memory[c.output]>>lane)&1;
            require(got==direct_distance(w,k,a,b),"full gate simulation versus literal Manhattan distance");
            ++batch_images;checksum=checksum*1000003+std::uint64_t(got);
        }
    }
}
void callback_check(int h,int w,int k) {
    std::vector<TwoMarkGate> gates;std::size_t uses=0;const int p=h*w;
    auto record=[&](Kind kind,const std::vector<int>& inputs) {
        require(!inputs.empty(),"mock grader refuses empty gate");
        require(kind!=Kind::Not||inputs.size()==1,"mock grader NOT arity");
        int id=p+int(gates.size());
        for(int input:inputs)require(input>=0&&input<id,"mock grader refuses forward references");
        uses+=inputs.size();require(gates.size()<10000&&uses<=1000000,"mock original grader budgets");
        gates.push_back({kind,inputs});++callback_gates;return id;
    };
    int result=emit_two_mark_manhattan_circuit(h,w,k,
        [&](int input){return record(Kind::Not,{input});},
        [&](std::vector<int> inputs){return record(Kind::And,inputs);},
        [&](std::vector<int> inputs){return record(Kind::Or,inputs);});
    TwoMarkCircuit emitted{p,std::move(gates),result,uses};inspect(emitted,h,w,k);
    std::vector<std::pair<int,int>> pairs;
    for(int a=0;a<p;++a)for(int b=a+1;b<p;++b) {
        if(p<=30||pairs.size()<128)pairs.push_back({a,b});
        else break;
    }
    batch(emitted,w,k,pairs);
}
void exhaustive_small() {
    for(int h=1;h<=8;++h)for(int w=1;w<=8;++w)if(h*w>=2) {
        const int p=h*w;
        std::vector<std::pair<int,int>> pairs;
        for(int a=0;a<p;++a)for(int b=a+1;b<p;++b)pairs.push_back({a,b});
        for(int k=0;k<=h+w+1;++k) {
            const auto circuit=build_two_mark_manhattan_circuit(h,w,k);inspect(circuit,h,w,k);
            for(const auto& [a,b]:pairs) {
                require(scalar(circuit,a,b)==direct_distance(w,k,a,b),"all small two-mark images and all threshold boundaries");
            }
            batch(circuit,w,k,pairs);
        }
        for(int k:{0,1,h+w-2,h+w-1,std::numeric_limits<int>::max()})callback_check(h,w,k);
    }
}
void all_slender() {
    for(auto [h,w]:std::vector<std::pair<int,int>>{{1,200},{200,1}}) {
        std::vector<std::pair<int,int>> pairs;
        for(int a=0;a<200;++a)for(int b=a+1;b<200;++b)pairs.push_back({a,b});
        for(int k=0;k<=201;++k) {
            const auto circuit=build_two_mark_manhattan_circuit(h,w,k);inspect(circuit,h,w,k);
            batch(circuit,w,k,pairs);
        }
    }
}
void full_size() {
    std::mt19937 random(20190808);
    for(int k=0;k<=400;++k) {
        const int h=200,w=200,p=h*w;
        const auto circuit=build_two_mark_manhattan_circuit(h,w,k);inspect(circuit,h,w,k);
        std::vector<std::pair<int,int>> pairs{{0,p-1},{w-1,p-w},{0,1},{0,w},
            {50*w+100,100*w+50},{50*w+50,100*w+100},{0,w-1},{0,p-w}};
        for(int distance:{k-1,k,k+1})if(distance>=1&&distance<=398) {
            int row=std::min(199,distance),col=distance-row;
            pairs.push_back({0,row*w+col});
        }
        while(pairs.size()<256) {
            int a=random()%p,b=random()%p;if(a!=b)pairs.push_back({a,b});
        }
        batch(circuit,w,k,pairs);
    }
    for(auto [h,w]:std::vector<std::pair<int,int>>{{200,199},{199,200},{2,200},{200,2},{1,2},{2,1}})
        for(int k:{0,1,h+w-2,h+w-1,std::numeric_limits<int>::max()}) {
            const auto circuit=build_two_mark_manhattan_circuit(h,w,k);inspect(circuit,h,w,k);
            std::vector<std::pair<int,int>> pairs;
            for(int i=0;i<256;++i) {
                int a=random()%(h*w),b=random()%(h*w);while(a==b)b=(b+1)%(h*w);
                pairs.push_back({a,b});
            }
            batch(circuit,w,k,pairs);
        }
    for(int k:{0,1,2,199,398,399,std::numeric_limits<int>::max()})callback_check(200,200,k);
    const auto maximum=build_two_mark_manhattan_circuit(200,200,1);
    require(maximum.gates.size()==3190&&maximum.input_uses==86368,"achieved maximum gate and terminal counts");
    require(maximum.output==43189,"largest cell/output ID");
    const auto high=build_two_mark_manhattan_circuit(200,200,std::numeric_limits<int>::max());
    inspect(high,200,200,std::numeric_limits<int>::max());
    batch(high,200,std::numeric_limits<int>::max(),{{0,39999},{0,1}});
}
void invalid() {
    int callbacks=0;
    for(auto [h,w,k]:std::vector<std::array<int,3>>{
        {0,2,1},{2,0,1},{-1,2,1},{2,-1,1},{201,2,1},{2,201,1},{1,1,0},{1,1,1},{2,2,-1},
        {std::numeric_limits<int>::min(),2,1},{2,std::numeric_limits<int>::max(),1},
        {2,2,std::numeric_limits<int>::min()}}) {
        bool threw=false;try{build_two_mark_manhattan_circuit(h,w,k);}catch(const std::invalid_argument&){threw=true;}
        require(threw,"invalid generator arguments reject safely");
        threw=false;
        try{emit_two_mark_manhattan_circuit(h,w,k,
            [&](int){++callbacks;return 0;},
            [&](std::vector<int>){++callbacks;return 0;},
            [&](std::vector<int>){++callbacks;return 0;});}
        catch(const std::invalid_argument&){threw=true;}
        require(threw&&callbacks==0,"invalid emitter arguments cause no gate callback");
    }
    bool bad_id=false;
    try{emit_two_mark_manhattan_circuit(2,2,1,
        [](int){return 0;},[](std::vector<int>){return 0;},[](std::vector<int>){return 0;});}
    catch(const std::logic_error&){bad_id=true;}
    require(bad_id,"bad callback cell ID is diagnosed");
}
int main() {
    const auto start=std::chrono::steady_clock::now();
    invalid();exhaustive_small();all_slender();full_size();
    require(max_gates==3190&&max_uses==86368,"all executed budget maxima");
    std::cout<<"Vision C++20: checks="<<checks<<" circuits="<<circuits<<" scalar_images="<<scalar_images
             <<" batch_images="<<batch_images<<" callback_gates="<<callback_gates
             <<" max_gates="<<max_gates<<" max_terminals="<<max_uses<<" checksum="<<checksum
             <<" seconds="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<'\n';
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-vision-') as directory:
    source=Path(directory)/'check.cpp';binary=Path(directory)/'check'
    source.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    environment=os.environ.copy()
    if '--sanitize' in sys.argv:
        flags+=['-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
        environment['ASAN_OPTIONS']='detect_leaks=0'
    compiler=environment.get('CXX') or shutil.which('g++') or shutil.which('clang++') or 'c++'
    subprocess.run([compiler,*flags,str(source),'-o',str(binary)],check=True,timeout=120)
    subprocess.run([str(binary)],check=True,env=environment,timeout=180)
