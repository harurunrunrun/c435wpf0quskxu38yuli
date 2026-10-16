from pathlib import Path
import hashlib,json,re,subprocess,tempfile
article=Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/dynamic-grid-prefix-rectangle-corner-minimum-count.mdx'
cpp=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
assert len(cpp)==1
extra=r'''
#include <cassert>
#include <cstdlib>
#include <new>
#include <iostream>
int allocation_budget=-1;
std::uint64_t allocation_calls=0;
void* operator new(std::size_t n) {
    if(allocation_budget==0)throw std::bad_alloc();
    if(allocation_budget>0)--allocation_budget;
    ++allocation_calls;
    if(void* p=std::malloc(n?n:1))return p;
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete(void* p,std::size_t) noexcept {std::free(p);}
void* operator new[](std::size_t n){return ::operator new(n);}
void operator delete[](void* p) noexcept {std::free(p);}
void operator delete[](void* p,std::size_t) noexcept {std::free(p);}
int main(){
    std::vector<int> r(15),c(15);
    for(int i=0;i<15;++i)r[i]=i/5,c[i]=i%5;
    PrefixRectangleGrid source(3,5,r,c);
    assert(source.rectangle_prefixes()==7);
    int copy_failures=0,assignment_failures=0;
    for(int budget=0;budget<=5;++budget){
        allocation_budget=budget;bool failed=false;
        try {PrefixRectangleGrid copy(source);assert(copy.rectangle_prefixes()==7);}
        catch(const std::bad_alloc&){failed=true;}
        allocation_budget=-1;assert(failed==(budget<5));copy_failures+=failed;
        assert(source.rectangle_prefixes()==7);
        PrefixRectangleGrid target(2,3,{0,1,1,0,0,1},{0,0,1,1,2,2});
        assert(target.rectangle_prefixes()==4);
        allocation_budget=budget;failed=false;
        try {target=source;}catch(const std::bad_alloc&){failed=true;}
        allocation_budget=-1;assert(failed==(budget<5));assignment_failures+=failed;
        if(failed){
            assert(target.rectangle_prefixes()==4);
            assert(target.swap_labels(0,5)==3);
            assert(target.swap_labels(5,0)==4);
        }else assert(target.rectangle_prefixes()==7);
        assert(source.rectangle_prefixes()==7);
    }
    PrefixRectangleGrid model(2,3,{0,1,1,0,0,1},{0,0,1,1,2,2});
    const auto before=allocation_calls;
    allocation_budget=0;
    for(int repeat=0;repeat<10000;++repeat){
        assert(model.swap_labels(0,5)==3);
        assert(model.swap_labels(5,0)==4);
        assert(model.rectangle_prefixes()==4);
        assert(model.swap_labels(0,0)==4);
    }
    allocation_budget=-1;assert(allocation_calls==before);
    std::cout<<"{\"copyAllocationFailures\":"<<copy_failures
             <<",\"assignmentAllocationFailures\":"<<assignment_failures
             <<",\"successfulCopyBudgets\":1,\"successfulAssignmentBudgets\":1"
             <<",\"noAllocationValidSwaps\":30000,\"noAllocationGetters\":10000}\\n";
}
'''
with tempfile.TemporaryDirectory(prefix='seats-independent-api-') as directory:
    source=Path(directory)/'check.cpp';binary=Path(directory)/'check'
    source.write_text(cpp[0]+extra)
    subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-Wno-mismatched-new-delete',str(source),'-o',str(binary)],check=True)
    result=subprocess.run([str(binary)],text=True,capture_output=True,check=True)
    report=json.loads(result.stdout.strip().removesuffix('\\n'))
    report['cppSha256']=hashlib.sha256(cpp[0].encode()).hexdigest()
    print(json.dumps(report,indent=2))
