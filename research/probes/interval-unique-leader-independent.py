#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re,subprocess,tempfile
article=Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/interval-unique-endpoints-singleton-middle-active-lazy.mdx'
cpp=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)[0]
harness=r'''
#include <cstdlib>
#include <iostream>
#include <map>
#include <numeric>
#include <random>
using I=std::int64_t;using U=std::uint64_t;
U checks=0,patterns=0,triples=0,crosses=0,maximums=0,checksum=0;
void need(bool ok,const char* message){++checks;if(!ok){std::cerr<<message<<'\n';std::exit(1);}}
void record(I x){checksum=checksum*1000003+U(x)+1;}
I neighbors_oracle(const std::vector<I>& a){
 int n=int(a.size());std::vector<int> before(n,-1),after(n,n);
 for(int i=0;i<n;++i){for(int j=0;j<i;++j)if(a[j]==a[i])before[i]=j;for(int j=n-1;j>i;--j)if(a[j]==a[i])after[i]=j;}
 I answer=0;
 for(int l=0;l<n;++l)for(int m=l+1;m<n;++m)for(int r=m+1;r<n;++r){
  answer+=after[l]>r&&before[r]<l&&before[m]<l&&after[m]>r;++triples;
 }
 return answer;
}
I literal(const std::vector<I>& a){I answer=0;int n=int(a.size());
 for(int l=0;l<n;++l)for(int m=l+1;m<n;++m)for(int r=m+1;r<n;++r){int left=0,middle=0,right=0;for(int p=l;p<=r;++p){left+=a[p]==a[l];middle+=a[p]==a[m];right+=a[p]==a[r];}answer+=left==1&&middle==1&&right==1;}
 return answer;
}
void restricted(std::vector<I>& a,int position,int maximum){
 if(position==int(a.size())){I want=neighbors_oracle(a);if(a.size()<=7)need(want==literal(a),"nearest-occurrence oracle literal crosscheck");need(count_interval_unique_leader_triples(a)==want,"every equality partition");record(want);++patterns;return;}
 for(int color=0;color<=maximum+1;++color){a[position]=color;restricted(a,position+1,std::max(maximum,color));}
}
struct Stats{I candidates=0,weights=0;};
Stats prefix_stats(const std::vector<I>& a){std::map<I,int> counts;I singles=0;Stats out;
 for(I x:a){int& count=counts[x];if(count==0)++singles;else if(count==1)--singles;++count;if(count==1){++out.candidates;out.weights+=singles-1;}}
 return out;
}
void concatenation(std::vector<I> a,std::vector<I> b){
 auto reversed=a;std::reverse(reversed.begin(),reversed.end());Stats left=prefix_stats(reversed),right=prefix_stats(b);
 I want=count_interval_unique_leader_triples(a)+count_interval_unique_leader_triples(b)+left.weights*right.candidates+left.candidates*right.weights;
 a.insert(a.end(),b.begin(),b.end());I got=count_interval_unique_leader_triples(a);need(got==want,"disjoint-alphabet concatenation identity");record(got);++crosses;
}
int main(){
 for(int n=0;n<=10;++n){std::vector<I>a(n);restricted(a,0,-1);}
 need(patterns==142418,"all Bell equality partitions length0..10");
 std::mt19937 rng(20211140);
 for(int test=0;test<1000;++test){int n=int(rng()%200),m=int(rng()%200);std::vector<I>a(n),b(m);
  for(I&x:a)x=-1-I(rng()%151);for(I&x:b)x=I(rng()%139);
  concatenation(a,b);
 }
 for(int type=0;type<8;++type){const int n=100000;std::vector<I>a(n),b(n);
  for(int i=0;i<n;++i){
   a[i]=type&1?-1-I(rng()%100000):-1-I(i);
   b[i]=type&2?I(rng()%100000):I(i);
   if(type&4){if(i%3==0)a[i]=std::numeric_limits<I>::min();if(i%5==0)b[i]=std::numeric_limits<I>::max();}
  }
  concatenation(a,b);++maximums;
 }
 std::cout<<"{\"checks\":"<<checks<<",\"allEqualityPartitionsN0to10\":"<<patterns<<",\"allTriplesByNearestOccurrence\":"<<triples<<",\"disjointAlphabetConcatenations\":"<<crosses<<",\"maximumN200000Concatenations\":"<<maximums<<",\"checksum\":\""<<checksum<<"\"}\n";
}
'''
# Braces keep independent sequential loops unambiguous under -Werror.
harness=harness.replace('for(I&x:a)x=-1-I(rng()%151);for(I&x:b)x=I(rng()%139);','for(I&x:a){x=-1-I(rng()%151);}for(I&x:b){x=I(rng()%139);}')
with tempfile.TemporaryDirectory(prefix='flowchartcp-unitedcows-review-extra-') as directory:
 source=Path(directory)/'check.cpp';binary=Path(directory)/'check';source.write_text(cpp+harness)
 subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],check=True)
 r=subprocess.run([str(binary)],capture_output=True,text=True,check=True)
 result=json.loads(r.stdout);result['cppSha256']=hashlib.sha256(cpp.encode()).hexdigest();print(json.dumps(result,indent=2))

