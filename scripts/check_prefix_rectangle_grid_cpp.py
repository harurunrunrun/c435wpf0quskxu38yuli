#!/usr/bin/env python3
"""Compile the actual visible C++20 and compare to literal prefix bounding boxes."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess,sys,tempfile

TESTS=r'''
#include <bit>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <random>
using U=std::uint64_t;
U checks=0,permutations=0,exhaustive_swaps=0,random_instances=0,random_swaps=0;
U bitmaps=0,maximum_swaps=0,checksum=0;int maximum_cells=0,maximum_height=0,maximum_width=0;
double maximum_construction_seconds=0,maximum_swap_batch_seconds=0;
void require(bool condition,const char* why){++checks;if(!condition){std::cerr<<"FAIL "<<why<<'\n';std::exit(1);}}
void absorb(int value){checksum=checksum*1000003+U(value+2);}
struct Position{int row,column;};
int bounding_boxes(const std::vector<Position>& position){
    int minr=1000001,minc=1000001,maxr=-1,maxc=-1,answer=0;
    for(int label=0;label<int(position.size());++label){
        minr=std::min(minr,position[label].row);maxr=std::max(maxr,position[label].row);
        minc=std::min(minc,position[label].column);maxc=std::max(maxc,position[label].column);
        answer+=std::int64_t(maxr-minr+1)*(maxc-minc+1)==label+1;
    }
    return answer;
}
PrefixRectangleGrid construct(int h,int w,const std::vector<Position>& position){
    std::vector<int> row,column;for(const auto& cell:position){row.push_back(cell.row);column.push_back(cell.column);}
    const auto row_before=row,column_before=column;PrefixRectangleGrid model(h,w,row,column);
    require(row==row_before&&column==column_before,"constructor preserves both caller arrays");return model;
}
void exhaustive(){
    // Every grid shape and every placement with HW<=8, including 1x8,2x4,4x2,8x1.
    for(int h=1;h<=8;++h)for(int w=1;w<=8;++w)if(h*w<=8){
        const int n=h*w;std::vector<int> placement(n);std::iota(placement.begin(),placement.end(),0);
        do{
            std::vector<Position> position(n);
            for(int cell=0;cell<n;++cell)position[placement[cell]]={cell/w,cell%w};
            auto model=construct(h,w,position);const int original=bounding_boxes(position);
            require(model.rectangle_prefixes()==original,"ALL small permutations literal bboxarea==prefixcount");
            for(int a=0;a<n;++a){
                require(model.swap_labels(a,a)==original,"same-label extension before every exhaustive swap group");
                for(int b=a+1;b<n;++b){
                    std::swap(position[a],position[b]);const int expected=bounding_boxes(position);
                    const int actual=model.swap_labels(a,b);require(actual==expected,"ALL pairs in EVERY small placement match bbox oracle");
                    require(model.rectangle_prefixes()==expected,"getter after every exhaustive swap");absorb(actual);
                    std::swap(position[a],position[b]);require(model.swap_labels(b,a)==original,"reversed second swap restores every prefix");
                    ++exhaustive_swaps;
                }
            }
            ++permutations;
        }while(std::next_permutation(placement.begin(),placement.end()));
    }
}
void check_corner_criterion(){
    // Independent finite-shape test. It never supplies the implementation's answer oracle.
    for(int h=1;h<=4;++h)for(int w=1;w<=4;++w){
        const unsigned limit=1U<<(h*w);
        for(unsigned bitmap=1;bitmap<limit;++bitmap){
            int minr=h,minc=w,maxr=-1,maxc=-1,one=0,three=0;
            for(int r=0;r<h;++r)for(int c=0;c<w;++c)if(bitmap>>(r*w+c)&1U){
                minr=std::min(minr,r);minc=std::min(minc,c);maxr=std::max(maxr,r);maxc=std::max(maxc,c);
            }
            for(int r=0;r<=h;++r)for(int c=0;c<=w;++c){
                int black=0;for(int dr=-1;dr<=0;++dr)for(int dc=-1;dc<=0;++dc){
                    const int x=r+dr,y=c+dc;if(x>=0&&x<h&&y>=0&&y<w)black+=bitmap>>(x*w+y)&1U;
                }
                one+=black==1;three+=black==3;
            }
            const bool rectangle=(maxr-minr+1)*(maxc-minc+1)==std::popcount(bitmap);
            require(one>=4,"at least four single-black windows for every nonempty shape");
            require((one+three==4)==rectangle,"holes and arbitrary diagonal contacts: exact criterion on EVERY bitmap");++bitmaps;
        }
    }
}
void randomized(){
    std::mt19937 rng(20180903);
    for(int test=0;test<400;++test){
        const int h=1+int(rng()%13),w=1+int(rng()%13),n=h*w;
        std::vector<int> permutation(n);std::iota(permutation.begin(),permutation.end(),0);std::shuffle(permutation.begin(),permutation.end(),rng);
        std::vector<Position> position(n),transposed(n),reflected(n);
        for(int i=0;i<n;++i){position[permutation[i]]={i/w,i%w};transposed[permutation[i]]={i%w,i/w};reflected[permutation[i]]={h-1-i/w,w-1-i%w};}
        auto model=construct(h,w,position),transpose=construct(w,h,transposed),reflection=construct(h,w,reflected);
        for(int q=0;q<600;++q){
            const int a=int(rng()%n),b=int(rng()%n);std::swap(position[a],position[b]);const int expected=bounding_boxes(position);
            const int actual=model.swap_labels(a,b);require(actual==expected,"random cumulative swaps equal direct independent prefix bbox scan");
            require(transpose.swap_labels(a,b)==expected&&reflection.swap_labels(a,b)==expected,"transpose/reflection preserve rectangle predicate and all update boundaries");
            absorb(actual);++random_swaps;
        }
        ++random_instances;
    }
}
void rejects(int h,int w,const std::vector<int>& row,const std::vector<int>& column){
    bool threw=false;try{PrefixRectangleGrid model(h,w,row,column);}catch(const std::invalid_argument&){threw=true;}
    require(threw,"reject invalid dimensions, lengths, coordinates or duplicate cells");
}
void boundaries(){
    std::vector<int> row{0,1,1,0,0,1},column{0,0,1,1,2,2};
    PrefixRectangleGrid example(2,3,row,column);require(example.rectangle_prefixes()==4,"official initial example");
    require(example.swap_labels(0,5)==3&&example.swap_labels(0,5)==4,"official repeated sample swaps");
    PrefixRectangleGrid singleton(1,1,{0},{0});require(singleton.rectangle_prefixes()==1&&singleton.swap_labels(0,0)==1,"single cell and repeated exterior sentinel");
    rejects(0,1,{},{});rejects(1,0,{},{});rejects(-1,1,{},{});rejects(1,-1,{},{});
    rejects(1000001,1,{},{});rejects(1,1000001,{},{});rejects(1001,1000,{},{});
    rejects(std::numeric_limits<int>::max(),std::numeric_limits<int>::max(),{},{});
    rejects(1,1,{},{});rejects(1,1,{0},{});rejects(1,1,{}, {0});rejects(1,1,{0,0},{0,0});
    rejects(1,1,{-1},{0});rejects(1,1,{1},{0});rejects(1,1,{0},{-1});rejects(1,1,{0},{1});
    rejects(2,2,{0,0,1,1},{0,0,0,1});rejects(2,2,{0,0,1,2},{0,1,0,1});
    for(auto [a,b]:std::vector<std::pair<int,int>>{{-1,0},{0,-1},{6,0},{0,6},{-1,-1},{6,6}}){
        bool threw=false;try{(void)example.swap_labels(a,b);}catch(const std::invalid_argument&){threw=true;}
        require(threw&&example.rectangle_prefixes()==4,"invalid swap validates BOTH indices before no-op and preserves state");
        require(example.swap_labels(0,5)==3&&example.swap_labels(5,0)==4,"valid operations after every rejection");
    }
    PrefixRectangleGrid copy=example;require(copy.swap_labels(0,5)==3&&example.rectangle_prefixes()==4,"deep copy does not share tree/grid or positions");
    PrefixRectangleGrid moved=std::move(copy);require(moved.rectangle_prefixes()==3,"move constructor preserves updated lazy tree");
    bool threw=false;try{(void)copy.rectangle_prefixes();}catch(const std::logic_error&){threw=true;}require(threw,"moved-from getter checked");
    threw=false;try{(void)copy.swap_labels(-1,-1);}catch(const std::invalid_argument&){require(false,"state error precedes query range error");}catch(const std::logic_error&){threw=true;}
    require(threw,"moved-from swap checked before index/no-op handling");
    copy=example;require(copy.rectangle_prefixes()==4,"copy assignment revives moved-from object");
    require(copy.swap_labels(0,5)==3&&example.rectangle_prefixes()==4,"copy assignment has independent state");
    copy=copy;require(copy.rectangle_prefixes()==3,"self copy assignment");
    auto* alias=&copy;copy=std::move(*alias);require(copy.rectangle_prefixes()==3,"self move assignment preserves data");
    moved=std::move(example);require(moved.rectangle_prefixes()==4&&copy.rectangle_prefixes()==3,"move assignment replaces an already initialized state");
    require(row==std::vector<int>({0,1,1,0,0,1})&&column==std::vector<int>({0,0,1,1,2,2}),"all operations leave caller input unchanged");
}
bool row_major_prefix_rectangle(int width,int end){return end+1<=width||(end+1)%width==0;}
bool adjacent_swapped_prefix_rectangle(int width,int end){
    // Only prefix ending at 'end' changes when adjacent row-major labels end/end+1 swap.
    // Bound the unchanged labels 0..end-1, then insert cell end+1. No local windows/tree.
    if(end==0)return true;
    const int previous_last=end-1,new_cell=end+1;
    const int maxrow=std::max(previous_last/width,new_cell/width);
    const int maxcolumn=std::max(end>=width?width-1:previous_last,new_cell%width);
    return std::int64_t(maxrow+1)*(maxcolumn+1)==end+1;
}
void maximum_case(int h,int w){
    const int n=h*w;std::vector<int> row(n),column(n);
    for(int i=0;i<n;++i){row[i]=i/w;column[i]=i%w;}
    const auto start=std::chrono::steady_clock::now();PrefixRectangleGrid model(h,w,row,column);
    maximum_construction_seconds=std::max(maximum_construction_seconds,std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count());
    const int original=h+w-1;require(model.rectangle_prefixes()==original,"maximum row-major grid count from complete rows or partial first row");
    const auto begin=std::chrono::steady_clock::now();
    for(int q=0;q<25000;++q){
        int a,b,expected;
        if(h==1||w==1){
            a=int(U(q)*100003%(n-1));b=a+1+int((U(q)*91771+31)%(n-1-a));
            if(q%7==0){a=0;b=n-1;}if(q%7==1){a=0;b=1;}
            expected=n-(b-a)+(a==0?(b==1?1:2):0);
        }else{
            a=int((U(q)*100003+q%3)%(n-1));b=a+1;
            if(q%7==0)a=w-1,b=a+1;
            if(q%7==1)a=0,b=1;
            expected=original-int(row_major_prefix_rectangle(w,a))+int(adjacent_swapped_prefix_rectangle(w,a));
        }
        const int actual=model.swap_labels(a,b);require(actual==expected,"maximum grid original-range queries: independent row-major bbox formula");absorb(actual);
        require(model.swap_labels(b,a)==original,"maximum grid returns to identity after each varied swap pair");maximum_swaps+=2;
    }
    maximum_swap_batch_seconds=std::max(maximum_swap_batch_seconds,std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count());
    maximum_cells=std::max(maximum_cells,n);maximum_height=std::max(maximum_height,h);maximum_width=std::max(maximum_width,w);
}
int main(){
    const auto start=std::chrono::steady_clock::now();check_corner_criterion();exhaustive();randomized();boundaries();
    maximum_case(1,1000000);maximum_case(1000000,1);maximum_case(1000,1000);maximum_case(2,500000);maximum_case(500000,2);
    require(maximum_cells==1000000&&maximum_height==1000000&&maximum_width==1000000,"full original HW/H/W boundaries exercised");
    require(maximum_swaps==250000,"five original-maximum Q50000 batches exercised");
    std::cout<<"{\"checks\":"<<checks<<",\"exhaustivePermutations\":"<<permutations<<",\"exhaustiveSwapPairs\":"<<exhaustive_swaps
             <<",\"bitmaps\":"<<bitmaps<<",\"randomInstances\":"<<random_instances<<",\"randomSwaps\":"<<random_swaps
             <<",\"maximumSwaps\":"<<maximum_swaps<<",\"maximumCells\":"<<maximum_cells<<",\"maximumHeight\":"<<maximum_height<<",\"maximumWidth\":"<<maximum_width
             <<",\"maximumConstructionSeconds\":"<<maximum_construction_seconds<<",\"maximumSwapBatchSeconds\":"<<maximum_swap_batch_seconds
             <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''

args=[arg for arg in sys.argv[1:] if arg!='--sanitize']
article=Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/dynamic-grid-prefix-rectangle-corner-minimum-count.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
if len(blocks)!=1:raise RuntimeError('expected one complete visible C++20 fence')
with tempfile.TemporaryDirectory(prefix='flowchartcp-seats-check-') as directory:
    source=Path(directory)/'check.cpp';binary=Path(directory)/'check';source.write_text(blocks[0]+'\n'+TESTS)
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror'];environment=os.environ.copy()
    if '--sanitize' in sys.argv:
        flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer']
        environment['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';environment['UBSAN_OPTIONS']='halt_on_error=1'
    compiler=environment.get('CXX') or shutil.which('g++') or shutil.which('clang++') or 'c++'
    subprocess.run([compiler,*flags,str(source),'-o',str(binary)],check=True,timeout=120)
    command=[str(binary)];timer=Path('/usr/bin/time')
    if timer.exists() and sys.platform.startswith('linux'):command=[str(timer),'-f','peak_rss_kib=%M',*command]
    result=subprocess.run(command,text=True,capture_output=True,env=environment,timeout=300)
    if result.returncode:
        print(result.stdout,end='',file=sys.stderr);print(result.stderr,end='',file=sys.stderr);result.check_returncode()
    report=json.loads(result.stdout);match=re.search(r'^peak_rss_kib=(\d+)$',result.stderr,re.M)
    if match:report['peakRSSKiB']=int(match[1])
    report.update(article=str(article),sanitized='--sanitize' in sys.argv,cppSha256=hashlib.sha256(blocks[0].encode()).hexdigest())
    print(json.dumps(report,ensure_ascii=False,indent=2))
