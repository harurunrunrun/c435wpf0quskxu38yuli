#!/usr/bin/env python3
"""Large trail-routing bijections: subdivision, relabeling, reversal, isolation."""
from pathlib import Path
import hashlib,json,re,subprocess,tempfile

HARNESS=r'''
#include <chrono>
#include <iostream>
#include <numeric>
#include <random>
#include <utility>
using Grid=std::vector<std::string>;
struct Input{Grid matrix;std::string roles;};
std::uint64_t checks=0,calls=0,checksum=0,instances=0,subdivision_checks=0;
std::uint64_t reverse_checks=0,relabel_checks=0,padding_checks=0,closed_form_checks=0;
void require(bool b,const char*why){++checks;if(!b)throw std::runtime_error(why);}
int call(const Input&a,int modulus){++calls;int got=count_almost_dag_edge_routings(a.matrix,a.roles,modulus);require(got>=0&&got<modulus,"canonical residue");checksum=checksum*1000003ULL+std::uint64_t(got+1);return got;}
int back_count(const Input&a){int count=0;for(std::size_t u=0;u<a.matrix.size();++u)for(std::size_t v=0;v<u;++v)count+=a.matrix[u][v]=='1';return count;}
Input relabel(const Input&a,const std::vector<int>&p,bool reverse_edges=false){int n=int(p.size());Input b{Grid(n,std::string(n,'0')),std::string(n,'.')};
 for(int u=0;u<n;++u){char role=a.roles[u];b.roles[p[u]]=reverse_edges?(role=='S'?'R':role=='R'?'S':'.'):role;
  for(int v=0;v<n;++v)if(a.matrix[u][v]=='1'){if(reverse_edges)b.matrix[p[v]][p[u]]='1';else b.matrix[p[u]][p[v]]='1';}}
 return b;
}
Input insert_isolated(const Input&a,int position){int n=int(a.matrix.size());Input b{Grid(n+1,std::string(n+1,'0')),std::string(n+1,'.')};
 for(int u=0;u<n;++u){int uu=u+(u>=position);b.roles[uu]=a.roles[u];for(int v=0;v<n;++v)if(a.matrix[u][v]=='1')b.matrix[uu][v+(v>=position)]='1';}return b;
}
Input subdivide(const Input&a,int u,int v) {
 // A forward edge gets an internal index; a backward edge gets an index just
 // before its head. Exactly one backward edge is retained in the latter case.
 int position=u<v?u+1:v;Input b=insert_isolated(a,position);
 int uu=u+(u>=position),vv=v+(v>=position);
 b.matrix[uu][vv]='0';b.matrix[uu][position]='1';b.matrix[position][vv]='1';return b;
}
int main(){auto begin=std::chrono::steady_clock::now();std::mt19937 rng(27191041U);
 for(int width=2;width<=5;++width)for(int layers=3;layers<=8;++layers)for(int pattern=0;pattern<5;++pattern) {
  const int sources=width*width,receiver_start=sources+layers*width,n=2*sources+layers*width;
  Input a{Grid(n,std::string(n,'0')),std::string(n,'.')};
  for(int v=0;v<sources;++v){a.roles[v]='S';a.matrix[v][sources+v/width]='1';a.roles[receiver_start+v]='R';a.matrix[sources+(layers-1)*width+v/width][receiver_start+v]='1';}
  for(int layer=0;layer+1<layers;++layer)for(int u=0;u<width;++u)for(int v=0;v<width;++v)a.matrix[sources+layer*width+u][sources+(layer+1)*width+v]='1';
  const int low=sources,high=sources+(layers-1)*width;
  if(pattern>0){a.matrix[low][high]=a.matrix[high][low]='1';}
  if(pattern>=2){int u=low+(pattern==2?0:1),v=high+(pattern==3?0:1);a.matrix[u][v]=a.matrix[v][u]='1';}
  const int backward=pattern==0?0:pattern==1?1:2;require(back_count(a)==backward,"family backward count");++instances;
  std::vector<int> order(n);std::iota(order.begin(),order.end(),0);
  auto shuffle_block=[&](int first,int size){std::shuffle(order.begin()+first,order.begin()+first+size,rng);};
  shuffle_block(0,sources);for(int layer=0;layer<layers;++layer)shuffle_block(sources+layer*width,width);shuffle_block(receiver_start,sources);
  Input permuted=relabel(a,order);require(back_count(permuted)==backward,"within-layer bijection preserves backward bound");
  std::iota(order.rbegin(),order.rend(),0);Input reversed=relabel(a,order,true);require(back_count(reversed)==backward,"reversed trails keep backward count under reversed labels");
  int fu=-1,fv=-1,bu=-1,bv=-1;
  for(int u=0;u<n;++u)for(int v=0;v<n;++v)if(a.matrix[u][v]=='1'){if(u<v){fu=u;fv=v;}else{bu=u;bv=v;}}
  Input forward_split=subdivide(a,fu,fv);require(back_count(forward_split)==backward,"forward subdivision keeps bound");
  Input backward_split=backward?subdivide(a,bu,bv):a;
  if(backward)require(back_count(backward_split)==backward,"backward subdivision keeps bound");
  Input padded=forward_split;while(padded.matrix.size()<100)padded=insert_isolated(padded,int(rng()%(padded.matrix.size()+1)));
  require(back_count(padded)==backward,"neutral padding keeps backward bound");
  for(int modulus:{97,1000000006,1000000007,2147483647}) {
   int expected=call(a,modulus);
   if(!backward){std::int64_t factorial=1,want=1;for(int k=2;k<=width;++k)factorial=factorial*k%modulus;for(int k=0;k<layers*width;++k)want=want*factorial%modulus;require(expected==want,"entire layered DAG count is product of local factorials");++closed_form_checks;}
   require(call(reversed,modulus)==expected,"trail reversal swaps senders/receivers bijectively");++reverse_checks;
   require(call(permuted,modulus)==expected,"vertex label bijection changes no scheme count");++relabel_checks;
   require(call(forward_split,modulus)==expected,"degree-one subdivision of forward edge is a scheme bijection");++subdivision_checks;
   if(backward){require(call(backward_split,modulus)==expected,"degree-one subdivision of backward edge is a scheme bijection");++subdivision_checks;}
   require(call(padded,modulus)==expected,"neutral isolated nodes plus subdivision preserve schemes atN100");++padding_checks;
  }
 }
 std::cout<<"{\"checks\":"<<checks<<",\"baseInstances\":"<<instances<<",\"apiCalls\":"<<calls
  <<",\"subdivisionChecks\":"<<subdivision_checks<<",\"trailReversalChecks\":"<<reverse_checks
  <<",\"withinLayerRelabelChecks\":"<<relabel_checks<<",\"maximumN100PaddingChecks\":"<<padding_checks
  <<",\"independentDagClosedFormChecks\":"<<closed_form_checks<<",\"checksum\":\""<<checksum
  <<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"}\n";
}
'''
article=(Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/almost-dag-edge-routing-pairing-frontier-cycle-count.mdx').read_text();blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S);assert len(blocks)==1
with tempfile.TemporaryDirectory(prefix='flowchartcp-routing-independent-')as tmp:
    src=Path(tmp)/'review.cpp';binary=Path(tmp)/'review';src.write_text(blocks[0]+'\n'+HARNESS)
    subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(src),'-o',str(binary)],check=True)
    result=json.loads(subprocess.check_output([str(binary)],text=True))
result['cppSha256']=hashlib.sha256(blocks[0].encode()).hexdigest()
result['scope']='Layered networks with4..25senders/receivers,0/1/2feedback, shared backward heads/tails, up toN100; independent exact DAG formula plus scheme-preserving bijections.'
print(json.dumps(result,ensure_ascii=False))
