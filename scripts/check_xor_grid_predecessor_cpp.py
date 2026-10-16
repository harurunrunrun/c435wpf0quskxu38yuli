#!/usr/bin/env python3
"""Compile the visible article fence; direct finite assignments and infinite-grid forward oracle."""
from pathlib import Path
import os,re,shutil,subprocess,sys,tempfile
args=[a for a in sys.argv[1:] if a!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/xor-grid-predecessor-boundary-single-error.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected exactly one complete visible C++20 fence')
TESTS=r'''
#include <array>
#include <bit>
#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <map>
#include <random>
#include <set>
#include <tuple>
using Grid=std::vector<std::string>;
using Cell=std::pair<int,int>;
using Cells=std::set<Cell>;
std::uint64_t checks=0, arbitrary_patterns=0, forward_cases=0, candidate_assignments=0;
std::uint64_t histories=0, checksum=0;
void require(bool condition,const char* reason) {
    ++checks;if(!condition){std::cerr<<"FAIL "<<reason<<'\n';std::exit(1);}
}
void absorb(std::uint64_t value){checksum=checksum*1000003+value+1;}
Cells cells_of(const Grid& input,int top=0,int left=0) {
    Cells out;for(int r=0;r<int(input.size());++r)for(int c=0;c<int(input[r].size());++c)
        if(input[r][c]=='#')out.emplace(r+top,c+left);
    return out;
}
struct View {Grid grid;int top,left;};
// Independent normalization through a coordinate set, without production crop().
View view(const Cells& cells) {
    require(!cells.empty(),"oracle pattern nonempty");
    int top=cells.begin()->first,bottom=top,left=cells.begin()->second,right=left;
    for(auto [r,c]:cells){top=std::min(top,r);bottom=std::max(bottom,r);left=std::min(left,c);right=std::max(right,c);}
    Grid out(bottom-top+1,std::string(right-left+1,'.'));
    for(auto [r,c]:cells)out[r-top][c-left]='#';
    return {out,top,left};
}
// Enumerate target cells and count all nine OLD neighbours.  No division or syndrome.
Cells forward(const Cells& old) {
    auto shape=view(old);Cells out;
    for(int r=shape.top-1;r<=shape.top+int(shape.grid.size());++r)
        for(int c=shape.left-1;c<=shape.left+int(shape.grid[0].size());++c) {
            int count=0;for(int dr=-1;dr<=1;++dr)for(int dc=-1;dc<=1;++dc)
                count+=old.contains({r+dr,c+dc});
            if(count%2)out.emplace(r,c);
        }
    return out;
}
void toggle(Cells& cells,Cell p){if(cells.contains(p))cells.erase(p);else cells.insert(p);}
std::uint64_t bits(const Grid& g) {
    std::uint64_t out=0;int bit=0;
    for(const auto& row:g)for(char ch:row){if(ch=='#')out|=1ULL<<bit;++bit;}
    return out;
}
Grid from_bits(int h,int w,std::uint64_t mask) {
    Grid out(h,std::string(w,'.'));
    for(int r=0;r<h;++r)for(int c=0;c<w;++c)if(mask>>(r*w+c)&1)out[r][c]='#';
    return out;
}
struct Assignment {std::uint64_t previous,updated;};
std::map<Cell,std::vector<Assignment>> candidate_cache;
// Every nonempty assignment in the possible predecessor window. Each update is
// computed by literal neighbourhood counting; no polynomial remainder criterion.
const std::vector<Assignment>& candidates(int h,int w) {
    auto key=Cell{h,w};if(candidate_cache.contains(key))return candidate_cache.at(key);
    auto& out=candidate_cache[key];
    if(h<3||w<3)return out;
    const int area=(h-2)*(w-2);require(area<=9,"finite oracle window <=9");
    for(unsigned mask=1;mask<(1U<<area);++mask) {
        std::uint64_t before=0,after=0;
        for(int r=1;r<h-1;++r)for(int c=1;c<w-1;++c)
            if(mask>>((r-1)*(w-2)+c-1)&1)before|=1ULL<<(r*w+c);
        for(int r=0;r<h;++r)for(int c=0;c<w;++c) {
            int count=0;
            for(int rr=1;rr<h-1;++rr)for(int cc=1;cc<w-1;++cc)
                if(before>>(rr*w+cc)&1)if(std::abs(rr-r)<=1&&std::abs(cc-c)<=1)++count;
            if(count%2)after|=1ULL<<(r*w+c);
        }
        out.push_back({before,after});
    }
    return out;
}
std::optional<Assignment> oracle_step(const Grid& observed) {
    const int h=int(observed.size()),w=int(observed[0].size());
    const auto target=bits(observed);std::optional<Assignment> answer;
    for(auto x:candidates(h,w)) {
        ++candidate_assignments;
        if(std::popcount(x.updated^target)<=1) {
            require(!answer,"direct assignments have at most one one-error predecessor");answer=x;
        }
    }
    return answer;
}
void check_result(const Grid& observed,const std::optional<XorGridPredecessor>& got,
                  const std::optional<Assignment>& expected) {
    require(bool(got)==bool(expected),"predecessor existence equals all-assignment oracle");
    if(!got){absorb(0);return;}
    const int h=int(observed.size()),w=int(observed[0].size());
    const Cells previous=cells_of(got->pattern,got->top,got->left);
    std::uint64_t located=0;
    for(auto [r,c]:previous) {
        require(r>=1&&r<h-1&&c>=1&&c<w-1,"previous in effective interior window");
        located|=1ULL<<(r*w+c);
    }
    require(located==expected->previous,"all predecessor cells and absolute offsets");
    const auto difference=expected->updated^bits(observed);
    require(bool(got->flipped)==bool(difference),"no-error versus one-error");
    if(got->flipped)require(difference==(1ULL<<(got->flipped->row*w+got->flipped->column)),"exact error cell");
    const auto normalized=view(previous);
    require(got->pattern==normalized.grid&&got->top==normalized.top&&got->left==normalized.left,"minimal bbox returned");
    require(observed.size()>=got->pattern.size()+2&&observed[0].size()>=got->pattern[0].size()+2,"both dimensions shrink by >=2");
    absorb(located);absorb(difference);
}
void check_small(const Grid& observed,bool check_minimum=true) {
    auto expected=oracle_step(observed);
    check_result(observed,xor_grid_predecessor(observed),expected);
    if(!check_minimum)return;
    auto start=view(cells_of(observed));Grid current=start.grid;
    int top=start.top,left=start.left,steps=0;
    for(;;) {
        auto before=oracle_step(current);if(!before)break;
        auto raw=from_bits(int(current.size()),int(current[0].size()),before->previous);
        auto next=view(cells_of(raw));current=next.grid;top+=next.top;left+=next.left;++steps;
    }
    const auto got=smallest_xor_grid_seed(observed);
    require(got.pattern==current&&got.reverse_steps==steps&&got.top==top&&got.left==left,"minimum seed equals direct recursive assignments");
    require(!xor_grid_predecessor(got.pattern),"reported minimum has no predecessor");
    absorb(steps);absorb(bits(current));
}
void verify_known_forward(const Cells& before,std::optional<Cell> error,bool compare_small_oracle) {
    const Cells clean=forward(before);Cells after=clean;
    if(error)toggle(after,*error);
    require(!after.empty(),"forward one error cannot erase nonempty update");
    const auto observed=view(after);const auto expected=view(before);
    require(observed.grid.size()<=300&&observed.grid[0].size()<=300,"test source within public dimensions");
    auto got=xor_grid_predecessor(observed.grid);
    require(bool(got),"forward case has predecessor");
    require(got->pattern==expected.grid&&got->top==expected.top-observed.top&&got->left==expected.left-observed.left,"forward case original pattern and position");
    require(bool(got->flipped)==bool(error),"forward error/no-error report");
    if(error)require(got->flipped->row==error->first-observed.top&&got->flipped->column==error->second-observed.left,"forward exact flip location including outlier");
    if(compare_small_oracle&&observed.grid.size()<=5&&observed.grid[0].size()<=5)check_small(observed.grid);
    ++forward_cases;absorb(got->top);absorb(got->left);absorb(got->flipped?got->flipped->row*301+got->flipped->column:90001);
}
void must_throw(const Grid& input) {
    bool one=false,all=false;
    try{(void)xor_grid_predecessor(input);}catch(const std::invalid_argument&){one=true;}
    try{(void)smallest_xor_grid_seed(input);}catch(const std::invalid_argument&){all=true;}
    require(one&&all,"both public APIs reject invalid argument");
}
int main() {
    auto begin=std::chrono::steady_clock::now();
    // Every nonempty bit pattern, INCLUDING padded presentations, on all <=4x4 rectangles.
    for(int h=1;h<=4;++h)for(int w=1;w<=4;++w)
        for(unsigned mask=1;mask<(1U<<(h*w));++mask){check_small(from_bits(h,w,mask));++arbitrary_patterns;}
    // Explicit code minimum weight: all possible nonzero differences <=3x3.
    for(int h=3;h<=5;++h)for(int w=3;w<=5;++w)for(auto a:candidates(h,w))
        require(std::popcount(a.updated)>=4,"all nonzero small codewords have weight >=4");
    // Every <=3x3 nonempty initial assignment times EVERY flip in expanded bbox,
    // plus every flip in one further surrounding layer (including isolated outliers).
    for(int h=1;h<=3;++h)for(int w=1;w<=3;++w)
        for(unsigned mask=1;mask<(1U<<(h*w));++mask) {
            auto old=cells_of(from_bits(h,w,mask));verify_known_forward(old,std::nullopt,true);
            for(int r=-2;r<=h+1;++r)for(int c=-2;c<=w+1;++c)
                verify_known_forward(old,Cell{r,c},true);
        }
    // Equal local shapes translated to very large positive/negative absolute coordinates.
    // Input remains a finite bbox; the infinite lattice has no distinguished origin.
    std::array<Cell,8> distant={Cell{-297,-296},{-297,0},{0,-297},{297,0},{0,297},{296,297},{-296,297},{297,-296}};
    for(int phase=0;phase<3;++phase)for(auto [r,c]:distant) {
        Cells p={{1000000000+phase,-1000000000+phase}};
        verify_known_forward(p,Cell{1000000000+phase+r,-1000000000+phase+c},false);
    }
    // Six residues for row/column positions; no restriction to a periodic coordinate class.
    for(int r=-6;r<=6;++r)for(int c=-6;c<=6;++c)
        verify_known_forward(Cells{{0,0},{0,1},{1,0}},Cell{r,c},false);
    // Complete repeated histories from small seeds; each first predecessor must be the
    // exact previous state, and the minimum must equal the seed's independently decoded minimum.
    std::mt19937 random(27052017);
    for(int test=0;test<240;++test) {
        Grid initial=from_bits(3,3,1+random()%511);auto min_seed=smallest_xor_grid_seed(initial);
        check_small(initial);Cells state=cells_of(initial);
        const int count=1+random()%8;
        for(int i=0;i<count;++i) {
            auto v=view(state);std::optional<Cell> error;
            if(random()%3)error=Cell{v.top-1+int(random()%(v.grid.size()+2)),v.left-1+int(random()%(v.grid[0].size()+2))};
            verify_known_forward(state,error,false);state=forward(state);if(error)toggle(state,*error);
        }
        auto v=view(state);auto got=smallest_xor_grid_seed(v.grid);
        require(got.pattern==min_seed.pattern&&got.reverse_steps==count+min_seed.reverse_steps,"complete random history minimum");
        require(got.top==min_seed.top-v.top&&got.left==min_seed.left-v.left,"complete random history origin");
        ++histories;
    }
    // Maximal 300x300: a 2x2 irreducible seed and 149 exact forward steps, with
    // deterministic one-cell errors at interior/boundary positions on alternating steps.
    Cells state={{0,0},{0,1},{1,1}};
    for(int step=0;step<149;++step) {
        const auto v=view(state);std::optional<Cell> error;
        if(step%2)error=Cell{v.top-1+(step*37)%int(v.grid.size()+2),v.left-1+(step*53)%int(v.grid[0].size()+2)};
        state=forward(state);if(error)toggle(state,*error);
    }
    const auto max_view=view(state);require(max_view.grid.size()==300&&max_view.grid[0].size()==300,"maximal original dimensions attained");
    const auto max_result=smallest_xor_grid_seed(max_view.grid);
    require(max_result.pattern==Grid{"##",".#"}&&max_result.reverse_steps==149,"maximal 149-step exact reconstruction");
    require(max_result.top==149&&max_result.left==149,"maximal origin accumulation");
    Grid dense(300,std::string(300,'#'));auto dense_step=xor_grid_predecessor(dense);
    Grid dense_previous(298,std::string(298,'.'));
    for(int r=0;r<298;r+=3)for(int c=0;c<298;c+=3)dense_previous[r][c]='#';
    require(dense_step&&dense_step->pattern==dense_previous&&dense_step->top==1&&dense_step->left==1&&!dense_step->flipped,"300x300 dense noiseless exact division");
    Grid impossible(300,std::string(300,'.'));impossible[0][0]='#';impossible[299][299]='#';
    auto impossible_result=smallest_xor_grid_seed(impossible);
    require(impossible_result.pattern==impossible&&impossible_result.reverse_steps==0,"maximal sparse nondecodable observation");
    Grid padded(300,std::string(300,'.'));padded[150][149]='#';
    auto padded_result=smallest_xor_grid_seed(padded);
    require(padded_result.pattern==Grid{"#"}&&padded_result.top==150&&padded_result.left==149&&padded_result.reverse_steps==0,"maximal zero padding and singleton stop");
    // Public statement samples; compare concrete minimum and exact reverse step reconstruction.
    std::array<Grid,3> samples={
        Grid{".#...#...#","##..##..##","##.#.##...","##.#.##...",".#...#####","...##..#.#","......###.","##.#.##...","#..#..#..#","##..##..##"},
        Grid{"##..#.##","#.####.#",".#.#.#..",".##.#.##",".#.#.#..",".##.#.##","#..#.###","##.#.##."},
        Grid{"#....","..###","..###","..###"}};
    std::array<Grid,3> expected_samples={Grid{".#","##"},Grid{"####","#..#","#.##","###."},Grid{"#"}};
    for(int i=0;i<3;++i)require(smallest_xor_grid_seed(samples[i]).pattern==expected_samples[i],"published sample minimum");
    must_throw({});must_throw({""});must_throw({"...","..."});must_throw({"#.","#"});
    must_throw({"#x"});must_throw({"#0"});must_throw(Grid(301,"#"));must_throw({std::string(301,'#')});
    const auto seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
    std::cout<<"PASS checks="<<checks<<" arbitrary_patterns="<<arbitrary_patterns<<" forward_cases="<<forward_cases
             <<" candidate_assignments="<<candidate_assignments<<" histories="<<histories
             <<" max_dimensions=300x300 max_reverse_steps=149 checksum="<<checksum<<" seconds="<<seconds<<'\n';
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-replicate-') as folder:
    source=Path(folder)/'check.cpp';binary=Path(folder)/'check'
    source.write_text(blocks[0]+'\n'+TESTS)
    options=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if '--sanitize' in sys.argv:options=['-std=c++20','-O1','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer']
    compiler=os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++') or 'c++'
    subprocess.run([compiler,*options,str(source),'-o',str(binary)],check=True,timeout=120)
    environment=dict(os.environ)
    if '--sanitize' in sys.argv:environment['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';environment['UBSAN_OPTIONS']='halt_on_error=1'
    subprocess.run([str(binary)],check=True,env=environment,timeout=180)
