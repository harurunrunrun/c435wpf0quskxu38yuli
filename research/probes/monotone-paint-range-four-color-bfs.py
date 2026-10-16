#!/usr/bin/env python3
"""Independent five-state brush BFS with outside positions explicitly unpainted."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile,time
article=Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/monotone-paint-stroke-links-offline-containment.mdx';blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S);assert len(blocks)==1
harness=r'''
#include <algorithm>
#include <cstdlib>
#include <iostream>
#include <random>
using I=std::int64_t;using U=std::uint64_t;
U checks=0,states=0,actions=0,arrays=0,queries=0,empty_queries=0,checksum=0;
void need(bool p,const char* what){++checks;if(!p){std::cerr<<what<<'\n';std::exit(1);}}
std::vector<int> distances(int n){
 int count=1;for(int i=0;i<n;++i)count*=5;
 std::vector<int> distance(count,-1),queue{0};distance[0]=0;
 for(std::size_t at=0;at<queue.size();++at){int code=queue[at];std::vector<int> now(n);for(int& x:now){x=code%5;code/=5;}
  for(int l=0;l<n;++l)for(int r=l+1;r<=n;++r)for(int color=1;color<=4;++color){
   bool legal=true;for(int i=l;i<r;++i)legal=legal&&now[i]<=color;
   if(!legal)continue;++actions;
   auto painted=now;for(int i=l;i<r;++i)painted[i]=color;
   int next=0,power=1;for(int x:painted){next+=x*power;power*=5;}
   if(distance[next]<0){distance[next]=distance[queue[at]]+1;queue.push_back(next);}
  }
 }
 need(queue.size()==std::size_t(count),"all5^N painted/blank configurations reached");states+=queue.size();return distance;
}
int main(){std::mt19937 random(445201);
 const I palette[4]={std::numeric_limits<I>::min(),-1,0,std::numeric_limits<I>::max()};
 for(int n=0;n<=6;++n){auto optimum=distances(n);int targets=1;for(int i=0;i<n;++i)targets*=4;
  for(int code=0;code<targets;++code){auto x=code;std::vector<int> rank(n);std::vector<I> colors(n);for(int i=0;i<n;++i){rank[i]=1+x%4;x/=4;colors[i]=palette[rank[i]-1];}
   std::vector<std::pair<int,int>> batch;for(int l=0;l<=n;++l)for(int r=l;r<=n;++r)batch.push_back({l,r});std::shuffle(batch.begin(),batch.end(),random);
   auto saved_colors=colors;auto saved_batch=batch;const auto answer=range_monotone_paint_strokes(colors,batch);
   need(answer.size()==batch.size(),"batch size");need(colors==saved_colors&&batch==saved_batch,"both inputs unchanged");
   for(std::size_t q=0;q<batch.size();++q){auto [l,r]=batch[q];int goal=0,power=1;
    for(int i=0;i<n;++i){if(l<=i&&i<r)goal+=rank[i]*power;power*=5;}
    need(answer[q]==optimum[goal],"literal FULL-board shortest painting with OUTSIDE explicitly blank");++queries;empty_queries+=l==r;checksum=checksum*1000003+U(answer[q]);
   }
   ++arrays;
  }
 }
 std::vector<std::pair<int,int>> empty_batch(200000,{0,0});const auto empty=range_monotone_paint_strokes({},empty_batch);
 for(int x:empty){need(x==0,"maximumQ with emptyN and all empty queries");++empty_queries;}
 const int n=200000;std::vector<I> all_equal(n,std::numeric_limits<I>::min());
 for(int i=0;i<n;++i){int cut=i%3==0?0:i%3==1?n:i;empty_batch[i]={cut,cut};}
 const auto zero=range_monotone_paint_strokes(all_equal,empty_batch);
 for(int x:zero){need(x==0,"all active same-color links excluded from maximum empty queries at0/N/interior");++empty_queries;}
 std::cout<<"{\"status\":\"passed\",\"checks\":"<<checks<<",\"fiveStateBfsConfigurations\":"<<states<<",\"legalBrushActions\":"<<actions<<",\"fourColorArraysIncludingEmpty\":"<<arrays<<",\"fullBoardBlankOutsideQueries\":"<<queries<<",\"emptyQueriesIncludingMaximumBatches\":"<<empty_queries<<",\"maximumN\":200000,\"maximumQ\":200000,\"checksum\":\""<<checksum<<"\"}\n";
}
'''
# Keep control-flow braces explicit under -Werror.
harness=harness.replace('if(!legal)continue;++actions;','if(!legal)continue;\n   ++actions;')
started=time.monotonic();san='--sanitize' in sys.argv
with tempfile.TemporaryDirectory(prefix='flowchartcp-notime-review-') as tmp:
 src=Path(tmp)/'review.cpp';exe=Path(tmp)/'review';src.write_text(blocks[0]+'\n'+harness)
 flags=['-std=c++20','-Wall','-Wextra','-Werror']+(['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'] if san else ['-O2'])
 subprocess.run(['g++',*flags,str(src),'-o',str(exe)],check=True)
 env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
 result=subprocess.run(['/usr/bin/time','-f','peak_rss_kib=%M',str(exe)],capture_output=True,text=True,check=True,env=env)
 out=json.loads(result.stdout);out.update(sanitized=san,cppSha256=hashlib.sha256(blocks[0].encode()).hexdigest(),secondsIncludingCompile=time.monotonic()-started,peakRSSKiB=int(re.search(r'peak_rss_kib=(\d+)',result.stderr)[1]))
print(json.dumps(out))
