#!/usr/bin/env python3
"""Large arbitrary intervals checked by an independent all-sites monotone-stack oracle."""
from pathlib import Path
import hashlib,json,os,re,subprocess,sys,tempfile,time
p=Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/cartesian-prefix-meeting-cost-single-cross-envelope.mdx';blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',p.read_text(),re.M|re.S);assert len(blocks)==1
harness=r'''
#include <bit>
#include <cstdint>
#include <cstdlib>
#include <iostream>
#include <random>
using U=std::uint64_t;
long long all_sites(const std::vector<int>& h,int l,int r){
 std::vector<long long> lc(r-l+1);std::vector<std::pair<int,int>> st;long long sum=0;
 for(int i=l;i<=r;++i){int count=1;while(!st.empty()&&st.back().first<=h[i]){sum-=1LL*st.back().first*st.back().second;count+=st.back().second;st.pop_back();}st.push_back({h[i],count});sum+=1LL*h[i]*count;lc[i-l]=sum;}
 st.clear();sum=0;long long best=std::numeric_limits<long long>::max();
 for(int i=r;i>=l;--i){int count=1;while(!st.empty()&&st.back().first<=h[i]){sum-=1LL*st.back().first*st.back().second;count+=st.back().second;st.pop_back();}st.push_back({h[i],count});sum+=1LL*h[i]*count;best=std::min(best,lc[i-l]+sum-h[i]);}
 return best;
}
long long literal(const std::vector<int>& h,int l,int r){
 long long best=std::numeric_limits<long long>::max();
 for(int x=l;x<=r;++x){long long sum=h[x];int top=h[x];for(int i=x-1;i>=l;--i){top=std::max(top,h[i]);sum+=top;}top=h[x];for(int i=x+1;i<=r;++i){top=std::max(top,h[i]);sum+=top;}best=std::min(best,sum);}return best;
}
int main(){
 std::mt19937 random(849513);U checks=0,cross=0,queries=0,checksum=0;
 for(int n=1;n<=8;++n){std::vector<int> h(n,1);for(unsigned mask=0;mask<(1U<<n);++mask){for(int i=0;i<n;++i)h[i]=(mask>>i&1)?1000000000:1;for(int l=0;l<n;++l)for(int r=l;r<n;++r){++checks;++cross;if(all_sites(h,l,r)!=literal(h,l,r))std::exit(1);}}}
 constexpr int n=750000;
 for(int kind=0;kind<3;++kind){
  std::vector<int> h(n);for(int i=0;i<n;++i)h[i]=kind==0?1+int(random()%1000000000):kind==1?1000000000-int(std::countr_zero(static_cast<unsigned>(i+1))):1+33333333*int(std::countr_zero(static_cast<unsigned>(i+1)));
  std::vector<std::pair<int,int>> q{{0,n-1},{0,n/2},{n/2,n-1},{n/4,3*n/4}};
  for(int j=0;j<60;++j){int l=int(random()%(n/4)),r=3*n/4+int(random()%(n-n*3/4));q.push_back({l,r});}
  const auto a=minimum_interval_meeting_costs(h,q);
  for(std::size_t j=0;j<q.size();++j){++checks;++queries;if(a[j]!=all_sites(h,q[j].first,q[j].second)){std::cerr<<"large full-site oracle failure "<<kind<<' '<<j<<'\n';return 1;}checksum=checksum*1000003+U(a[j]);}
 }
 std::cout<<"{\"status\":\"passed\",\"checks\":"<<checks<<",\"smallLiteralCrosschecks\":"<<cross<<",\"maximumN\":750000,\"largeCases\":3,\"largeQueries\":"<<queries<<",\"checksum\":\""<<checksum<<"\"}\n";
}
'''
started=time.monotonic();san='--sanitize' in sys.argv
with tempfile.TemporaryDirectory(prefix='flowchartcp-meetings-large-') as tmp:
 src=Path(tmp)/'large.cpp';exe=Path(tmp)/'large';src.write_text(blocks[0]+'\n'+harness)
 flags=['-std=c++20','-Wall','-Wextra','-Werror']+(['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie'] if san else ['-O2'])
 subprocess.run(['g++',*flags,str(src),'-o',str(exe)],check=True)
 env=os.environ.copy();env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
 run=subprocess.run(['/usr/bin/time','-f','peak_rss_kib=%M',str(exe)],capture_output=True,text=True,env=env,check=True)
 out=json.loads(run.stdout);out.update(peakRSSKiB=int(re.search(r'peak_rss_kib=(\d+)',run.stderr)[1]),cppSha256=hashlib.sha256(blocks[0].encode()).hexdigest(),sanitized=san,secondsIncludingCompile=time.monotonic()-started)

print(json.dumps(out))
