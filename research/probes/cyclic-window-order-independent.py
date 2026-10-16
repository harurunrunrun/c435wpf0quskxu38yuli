#!/usr/bin/env python3
"""Read-only independent closure stress against the actual article fence."""
from pathlib import Path
import re,json,subprocess,tempfile,hashlib
article=Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/cyclic-window-height-poset-two-neighbor-doubling.mdx'
cpp=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)[0]
tests=r'''
#include <cstdint>
#include <iostream>
#include <numeric>
#include <random>
#include <chrono>
using Bits=std::vector<std::uint64_t>;
std::uint64_t cases=0,queries=0,checksum=0;
void need(bool x){if(!x){std::cerr<<"independent failure\n";std::exit(1);}}
int main(){
 std::mt19937 rng(7312020);const auto start=std::chrono::steady_clock::now();
 for(int test=0;test<48;++test){
  const int n=65+int(rng()%936);
  const int choices[]={1,2,3,n/4,n/2,n/2+1,n-1,n};
  const int k=test<40?choices[test%8]:1+int(rng()%n);
  std::vector<int> height(n),counts(n),order(n);std::iota(height.begin(),height.end(),0);
  std::shuffle(height.begin(),height.end(),rng);
  for(int i=0;i<n;++i)order[height[i]]=i;
  // Observation oracle counts actual comparisons in the original clockwise windows.
  for(int x=0;x<n;++x)for(int step=1;step<k;++step)counts[x]+=height[(x+step)%n]>height[x];
  CyclicWindowOrder model(k,counts);
  const int words=(n+63)/64;std::vector<Bits> reach(n,Bits(words));
  // Full near-comparison graph, evaluated from short to tall. No compressed
  // candidate links or directional greedy walks are used in this closure oracle.
  for(int rank=0;rank<n;++rank){const int x=order[rank];
   for(int y=0;y<n;++y)if(height[y]<height[x]&&((x-y+n)%n<k||(y-x+n)%n<k)){
    reach[x][y/64]|=1ULL<<(y%64);
    for(int word=0;word<words;++word)reach[x][word]|=reach[y][word];
   }
  }
  for(int x=0;x<n;++x)for(int y=0;y<n;++y){
   const int expected=(reach[x][y/64]>>(y%64)&1)?1:(reach[y][x/64]>>(x%64)&1)?-1:0;
   const int got=model.compare(x,y);need(got==expected);++queries;checksum=checksum*1000003+got+2;
  }
  // Clockwise observations change under reflection, but the induced undirected
  // near-pair set and true heights are preserved, hence all forced comparisons.
  std::vector<int> reflected_height(n),reflected_counts(n);
  for(int x=0;x<n;++x)reflected_height[(n-x)%n]=height[x];
  for(int x=0;x<n;++x)for(int step=1;step<k;++step)
   reflected_counts[x]+=reflected_height[(x+step)%n]>reflected_height[x];
  CyclicWindowOrder reflected(k,reflected_counts);
  for(int q=0;q<10000;++q){int x=int(rng()%n),y=int(rng()%n);
   need(model.compare(x,y)==reflected.compare((n-x)%n,(n-y)%n));++queries;
  }
  ++cases;
 }
 std::cout<<"{\"cases\":"<<cases<<",\"queries\":"<<queries<<",\"checksum\":\""<<checksum
          <<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
'''
with tempfile.TemporaryDirectory(prefix='flowchartcp-plants-independent-build-') as tmp:
 p=Path(tmp);(p/'test.cpp').write_text(cpp+'\n'+tests)
 subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
 r=subprocess.run([str(p/'test')],check=True,text=True,capture_output=True)
 result=json.loads(r.stdout);result['cppSha256']=hashlib.sha256(cpp.encode()).hexdigest()
 print(json.dumps(result))
