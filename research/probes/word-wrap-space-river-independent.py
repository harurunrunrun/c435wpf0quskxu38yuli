#!/usr/bin/env python3
"""All legal line partitions + boolean transitive closure; no production wrap or river DP oracle."""
from pathlib import Path
import hashlib,itertools,json,random,re,subprocess,tempfile,time
article=(Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/word-wrap-sparse-space-river-dp.mdx').read_text();fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S);assert len(fences)==1;cpp=fences[0]
harness=r'''
#include <cstddef>
#include <cstdlib>
#include <new>
#include <limits>
#include <iostream>
#include <locale>
#include <sstream>
static bool counting=false;static std::size_t live=0,peak=0;
struct alignas(std::max_align_t) Header{std::size_t size;bool tracked;};
[[gnu::noinline]] void* operator new(std::size_t n){auto*p=static_cast<Header*>(std::malloc(sizeof(Header)+(n?n:1)));if(!p)throw std::bad_alloc();p->size=n;p->tracked=counting;if(counting){live+=n;peak=std::max(peak,live);}return p+1;}
[[gnu::noinline]] void* operator new[](std::size_t n){return ::operator new(n);}
[[gnu::noinline]] void operator delete(void*ptr)noexcept{if(!ptr)return;auto*p=static_cast<Header*>(ptr)-1;if(p->tracked)live-=p->size;std::free(p);}
[[gnu::noinline]] void operator delete[](void*p)noexcept{::operator delete(p);}
[[gnu::noinline]] void operator delete(void*p,std::size_t)noexcept{::operator delete(p);}
[[gnu::noinline]] void operator delete[](void*p,std::size_t)noexcept{::operator delete(p);}
struct Comma:std::numpunct<char>{char do_decimal_point()const override{return ',';}char do_thousands_sep()const override{return '.';}std::string do_grouping()const override{return "\3";}};
struct Short:std::streambuf{std::streamsize xsputn(const char*,std::streamsize n)override{return n-1;}};
struct Explodes:std::streambuf{std::streamsize xsputn(const char*,std::streamsize)override{throw std::runtime_error("custom write failure");}};
int checks=0;void require(bool b){++checks;if(!b)throw std::runtime_error("new memory/writer check");}
int main(){std::vector<int> maximum(2500,80);counting=true;const auto large=space_river::longest_river_at_width(maximum,std::numeric_limits<int>::max());counting=false;
 require(live==0);require(peak==40000);require(large.longest==1&&large.line_count==1&&!large.next_width);
 const std::vector<std::string> words{"A","bb","c","DD","e"};const auto answer=space_river::best_space_river_words(words);
 const std::string expected=std::to_string(answer.width)+" "+std::to_string(answer.longest)+"\n";
 std::locale loc(std::locale::classic(),new Comma);std::ostringstream out;out.imbue(loc);out.setf(std::ios::hex,std::ios::basefield);out.setf(std::ios::showbase|std::ios::showpos|std::ios::uppercase);out.width(29);out.fill('@');out.precision(2);
 auto flags=out.flags();auto locale=out.getloc();space_river::write_best_space_river(out,words);require(out.str()==expected);require(out.flags()==flags);require(out.width()==29);require(out.fill()=='@');require(out.precision()==2);require(out.getloc()==locale);
 Short a;std::ostream shortstream(&a);shortstream.width(17);space_river::write_best_space_river(shortstream,words);require(shortstream.bad());require(shortstream.width()==17);
 Short b;std::ostream throwing(&b);throwing.exceptions(std::ios::badbit);bool thrown=false;try{space_river::write_best_space_river(throwing,words);}catch(const std::ios_base::failure&){thrown=true;}require(thrown);
 Explodes c;std::ostream exploding(&c);exploding.exceptions(std::ios::badbit);thrown=false;try{space_river::write_best_space_river(exploding,words);}catch(const std::runtime_error&e){thrown=std::string(e.what())=="custom write failure";}require(thrown);
 std::cout<<"{\"memoryWriterAssertions\":"<<checks<<",\"maxNIntMaxWidthPeakRequestedAllocationBytes\":"<<peak<<",\"liveRequestedBytesAfterCall\":"<<live<<"}\n";
 int n;while(std::cin>>n){std::vector<int> a(n);int total=n-1,minimum=0;for(int&x:a){std::cin>>x;total+=x;minimum=std::max(minimum,x);}const auto optimum=space_river::best_space_river(a);std::cout<<optimum.width<<' '<<optimum.longest;
  for(int w=minimum;w<=total+2;++w){const auto v=space_river::longest_river_at_width(a,w);std::cout<<' '<<v.longest<<' '<<v.line_count<<' '<<v.next_width.value_or(-1);}
  for(int w:{std::numeric_limits<int>::max()-1,std::numeric_limits<int>::max()}){const auto v=space_river::longest_river_at_width(a,w);std::cout<<' '<<v.longest<<' '<<v.line_count<<' '<<v.next_width.value_or(-1);}std::cout<<'\n';
 }
}
'''
start=time.monotonic();inputs=[]
for n in range(1,8):inputs.extend(itertools.product((1,4,9),repeat=n))
inputs.extend(itertools.product((1,80),repeat=8))
rng=random.Random(20181112)
for _ in range(120):inputs.append(tuple(rng.randint(1,80)for _ in range(rng.randrange(8,13))))
# Hand-selected empty-row cuts and changes exactly at a required width.
inputs.extend([(1,1,3,1,1),(1,1,2,2,1,1),(80,1,1,80,1,1),(1,)*6,(80,)*8])
partition_count=width_count=closure_nodes=closure_edges=empty_row_evaluations=0
checksum=0;optimum_ties=0;witness=None

def literal(lengths):
 global partition_count,width_count,closure_nodes,closure_edges,empty_row_evaluations,optimum_ties,witness
 n=len(lengths);L=max(lengths);T=sum(lengths)+n-1;layouts=[]
 # Each cut mask is a complete legal ordered line partition. The layout uses
 # the lexicographically largest endpoint tuple among those fitting width w.
 for mask in range(1<<(n-1)):
  endpoints=tuple(i+1 for i in range(n-1)if mask>>i&1)+(n,);begin=0;required=0
  for end in endpoints:required=max(required,sum(lengths[begin:end])+end-begin-1);begin=end
  layouts.append((required,endpoints));partition_count+=1
 layouts.sort();at=0;current=();minrows=n+1;by_width=[];rivers=[];cache={}
 for w in range(L,T+3):
  while at<len(layouts)and layouts[at][0]<=w:
   current=max(current,layouts[at][1]);minrows=min(minrows,len(layouts[at][1]));at+=1
  assert current and len(current)==minrows;by_width.append(current)
  if current not in cache:
   vertices=[];begin=0
   for row,end in enumerate(current):
    col=0
    for i in range(begin,end):
     if i>begin:vertices.append((row,col));col+=1
     col+=lengths[i]
    begin=end
   V=len(vertices);closure_nodes+=V;reach=[1<<i for i in range(V)]
   for i,(r,c)in enumerate(vertices):
    for j,(s,d)in enumerate(vertices):
     if s==r+1 and abs(c-d)<=1:reach[i]|=1<<j;closure_edges+=1
   # Boolean transitive closure, with no maximum-length recurrence or DFS paths.
   for k in range(V):
    for i in range(V):
     if reach[i]>>k&1:reach[i]|=reach[k]
   longest=max((vertices[j][0]-vertices[i][0]+1 for i in range(V)for j in range(V)if reach[i]>>j&1),default=0)
   cache[current]=longest
  rivers.append(cache[current]);width_count+=1
  if any(b-a==1 for a,b in zip((0,)+current,current)):empty_row_evaluations+=1
 nexts=[-1]*len(by_width)
 for i in range(len(by_width)-2,-1,-1):nexts[i]=L+i+1 if by_width[i+1]!=by_width[i] else nexts[i+1]
 best=max(rivers);first=L+rivers.index(best);ties=sum(v==best for v in rivers);optimum_ties+=ties>1
 if witness is None and lengths==(1,1,3,1,1):witness={'lengths':lengths,'width3River':rivers[3-L],'width3Rows':by_width[3-L]}
 fixed=[(r,len(layout),q)for r,layout,q in zip(rivers,by_width,nexts)]
 fixed.extend([(int(n>1),1,-1)]*2)
 return [first,best]+[v for row in fixed for v in row]

with tempfile.TemporaryDirectory(prefix='flowchartcp-river-independent-') as td:
 source=Path(td)/'probe.cpp';binary=Path(td)/'probe';source.write_text(cpp+'\n'+harness)
 subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-Wno-mismatched-new-delete',str(source),'-o',str(binary)],check=True)
 result=subprocess.check_output([str(binary)],input=''.join(str(len(a))+' '+' '.join(map(str,a))+'\n'for a in inputs),text=True).splitlines();memory=json.loads(result[0]);assert len(result)==len(inputs)+1
 for lengths,line in zip(inputs,result[1:]):
  actual=list(map(int,line.split()));expected=literal(lengths);assert actual==expected,(lengths,actual,expected)
  for v in actual:checksum=(checksum*1000003+v+1)%(1<<64)
out={'articleSha256':hashlib.sha256(article.encode()).hexdigest(),'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'inputCases':len(inputs),'allLegalOrderedLinePartitionsExamined':partition_count,'fixedWidthsComparedIncludingTwoPastOneLine':width_count,'minimumRowCountAcrossAllFeasiblePartitionsChecks':width_count,'additionalIntExtremeWidthComparisons':2*len(inputs),'booleanClosureNodes':closure_nodes,'booleanAdjacentRowEdges':closure_edges,'casesWithTiedOptimalWidths':optimum_ties,'emptyRowEvaluations':empty_row_evaluations,'emptyRowCutWitness':witness,'checksum':str(checksum),'apiMemoryAndWriter':memory,'seconds':time.monotonic()-start,'oracle':'Enumerate every cut mask, select the lexicographically greatest feasible ordered line endpoints, form the actual interword-space DAG and compute boolean transitive closure. Reachable row distance gives the river length. Next change is the first later differing endpoint tuple among every integer width, without the excluded-word threshold formula.','sanitizerForThisAdditionalProbe':False,'sharedOrAuthorArtifactsModified':False}
print(json.dumps(out,ensure_ascii=False,indent=2))
