#!/usr/bin/env python3
"""Independent actual-fence oracle: literal sites plus affine/reflection/outside-range invariants."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile,time
article=Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/cartesian-prefix-meeting-cost-single-cross-envelope.mdx'
blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
assert len(blocks)==1
harness=r'''
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <random>
using U=std::uint64_t;
U checks=0,cases=0,literal=0,affine=0,reflection=0,padding=0,slices=0,checksum=0;
void need(bool p,const char* what){++checks;if(!p){std::cerr<<what<<'\n';std::exit(1);}}
void take(long long x){checksum=checksum*1000003+U(x);}
long long direct(const std::vector<int>& h,int l,int r){
 long long best=std::numeric_limits<long long>::max();
 for(int x=l;x<=r;++x){
  long long value=0;int top=0;
  for(int i=x;i>=l;--i){top=std::max(top,h[i]);value+=top;}
  top=0;for(int i=x+1;i<=r;++i){top=std::max(top,h[i]);value+=top;}
  best=std::min(best,value);
 }
 return best;
}
void verify(const std::vector<int>& h,const std::vector<std::pair<int,int>>& q,bool brute,std::mt19937& random){
 const auto saved_h=h;const auto saved_q=q;
 const auto answer=minimum_interval_meeting_costs(h,q);++cases;
 need(h==saved_h&&q==saved_q,"input changed");need(answer.size()==q.size(),"answer size");
 if(brute)for(std::size_t i=0;i<q.size();++i){need(answer[i]==direct(h,q[i].first,q[i].second),"literal meeting-site oracle");++literal;}
 std::vector<int> transformed=h;
 for(int& x:transformed)x=2*x+3;
 const auto changed=minimum_interval_meeting_costs(transformed,q);
 for(std::size_t i=0;i<q.size();++i){need(changed[i]==2*answer[i]+3LL*(q[i].second-q[i].first+1),"positive affine height transform");++affine;}
 auto reversed=h;std::reverse(reversed.begin(),reversed.end());
 auto rq=q;for(auto& [l,r]:rq){const int old_l=l;l=int(h.size())-1-r;r=int(h.size())-1-old_l;}
 const auto mirrored=minimum_interval_meeting_costs(reversed,rq);
 for(std::size_t i=0;i<q.size();++i){need(answer[i]==mirrored[i],"reflection invariance");++reflection;}
 const int before=1+int(random()%11),after=1+int(random()%11);
 std::vector<int> padded(before,999999999);padded.insert(padded.end(),h.begin(),h.end());padded.insert(padded.end(),after,1000000000);
 auto pq=q;for(auto& [l,r]:pq){l+=before;r+=before;}
 const auto outside=minimum_interval_meeting_costs(padded,pq);
 for(std::size_t i=0;i<q.size();++i){need(answer[i]==outside[i],"unqueried outside mountains alter a result");++padding;}
 const int l=int(random()%h.size()),r=l+int(random()%(h.size()-l));
 std::vector<int> part(h.begin()+l,h.begin()+r+1);std::vector<std::pair<int,int>> local;std::vector<std::size_t> ids;
 for(std::size_t i=0;i<q.size();++i)if(q[i].first>=l&&q[i].second<=r){local.push_back({q[i].first-l,q[i].second-l});ids.push_back(i);}
 const auto isolated=minimum_interval_meeting_costs(part,local);
 for(std::size_t i=0;i<ids.size();++i){need(isolated[i]==answer[ids[i]],"literal subarray isolation");++slices;}
 for(long long x:answer)take(x);
}
int main(){
 std::mt19937 random(20261015);
 // All independent height permutations, including the tie-heavy negative-control domain.
 for(int n=1;n<=7;++n){
  std::vector<int> h(n);for(int i=0;i<n;++i)h[i]=i+1;
  do{std::vector<std::pair<int,int>> q;for(int l=0;l<n;++l)for(int r=l;r<n;++r)q.push_back({l,r});verify(h,q,true,random);}while(std::next_permutation(h.begin(),h.end()));
 }
 for(int c=0;c<600;++c){
  const int n=1+int(random()%512);std::vector<int> h(n);
  for(int i=0;i<n;++i)h[i]=1+int(random()%((c%3)?9:1000000));
  std::vector<std::pair<int,int>> q;
  for(int i=0;i<300;++i){int l=int(random()%n),r=int(random()%n);if(l>r)std::swap(l,r);q.push_back({l,r});}
  q.push_back({0,n-1});q.push_back({0,n-1});
  verify(h,q,n<=24,random);
 }
 need(minimum_interval_meeting_costs({2,1,2},{{0,2}})==std::vector<long long>{5},"same original maximum tie");
 std::cout<<"{\"status\":\"passed\",\"checks\":"<<checks<<",\"cases\":"<<cases<<",\"literalQueries\":"<<literal<<",\"affineQueries\":"<<affine<<",\"reflectionQueries\":"<<reflection<<",\"outsidePaddingQueries\":"<<padding<<",\"subarrayIsolationQueries\":"<<slices<<",\"checksum\":\""<<checksum<<"\"}\n";
}
'''
started=time.monotonic();sanitize='--sanitize' in sys.argv
with tempfile.TemporaryDirectory(prefix='flowchartcp-meetings-review-') as tmp:
 source=Path(tmp)/'review.cpp';binary=Path(tmp)/'review';source.write_text(blocks[0]+'\n'+harness)
 flags=['-std=c++20','-Wall','-Wextra','-Werror']+(['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'] if sanitize else ['-O2'])
 subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
 env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
 result=json.loads(subprocess.run([str(binary)],capture_output=True,text=True,check=True,env=env).stdout)
result.update({'sanitized':sanitize,'secondsIncludingCompile':time.monotonic()-started,'cppSha256':hashlib.sha256(blocks[0].encode()).hexdigest(),'articleSha256':hashlib.sha256(article.read_bytes()).hexdigest()})

print(json.dumps(result))
