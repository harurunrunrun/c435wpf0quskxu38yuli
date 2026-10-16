#!/usr/bin/env python3
"""Independent support-coordinate dictionary geometry and rank-warp checks."""
from pathlib import Path
import hashlib,json,re,subprocess,tempfile

HARNESS=r'''
#include <chrono>
#include <iostream>
#include <map>
#include <random>
#include <sstream>
using namespace orthogonal_cover;
using Points=std::vector<Point>;
std::uint64_t checks=0,cases=0,points_checked=0,segments_checked=0,signature_checks=0,checksum=0;
std::uint64_t maximum_calls=0,endpoint_hits=0,interior_hits=0;
std::uint64_t writer_calls=0;
void require(bool b,const char*why){++checks;if(!b)throw std::runtime_error(why);}
std::vector<int> check_geometry(const Points&p,const Points&q) {
 require(!q.empty()&&q.front()==Point{0,0},"geometry starts at origin");
 require(q.size()<=p.size()+4,"N+3 universal bound");
 std::map<std::int64_t,int> x_lookup,y_lookup;
 for(int i=0;i<int(p.size());++i){x_lookup.emplace(p[i].x,i);y_lookup.emplace(p[i].y,i);}
 std::vector<bool> covered(p.size());std::vector<int> signature;
 for(std::size_t i=0;i<q.size();++i) {
  require(q[i].x>=0&&q[i].x<=1000000001LL&&q[i].y>=0&&q[i].y<=1000000001LL,"strong coordinate bound");
  checksum=checksum*1000003ULL+std::uint64_t(q[i].x)+std::uint64_t(q[i].y);
  if(!i)continue;
  ++segments_checked;Point a=q[i-1],b=q[i];
  require(!(a==b)&&((a.x==b.x)^(a.y==b.y)),"nonzero axis-aligned segment");
  const bool vertical=a.x==b.x;
  signature.push_back(vertical?(b.y>a.y?2:3):(b.x>a.x?0:1));
  const auto& lookup=vertical?x_lookup:y_lookup;
  const auto found=lookup.find(vertical?a.x:a.y);
  if(found!=lookup.end()) {
   const Point dot=p[found->second];
   const auto at=vertical?dot.y:dot.x,lo=vertical?std::min(a.y,b.y):std::min(a.x,b.x),hi=vertical?std::max(a.y,b.y):std::max(a.x,b.x);
   if(lo<=at&&at<=hi){covered[found->second]=true;if(dot==a||dot==b)++endpoint_hits;else ++interior_hits;}
  }
 }
 for(bool seen:covered){++points_checked;require(seen,"segment-to-dot coordinate dictionary covers each dot");}
 return signature;
}
void verify(const std::vector<int>& y_rank,std::mt19937_64&rng) {
 ++cases;const int n=int(y_rank.size());
 Points base;for(int i=0;i<n;++i)base.push_back({i+1,y_rank[i]+1});
 const auto initial=cover_points_orthogonally(base);const auto signature=check_geometry(base,initial);
 if(n==100000)++maximum_calls;
 for(int mode=0;mode<3;++mode) {
  std::vector<std::int64_t> xs(n),ys(n);
  for(auto*coords:{&xs,&ys}) {
   std::int64_t sum=0;for(int i=0;i<n;++i){sum+=1+std::int64_t(rng()%97);(*coords)[i]=sum;}
   if(mode==0){const auto first=coords->front(),span=coords->back()-first;for(auto&v:*coords)v=n==1?1:1+(v-first)*999999999LL/span;}
   if(mode==1){const auto end=coords->back();for(auto&v:*coords)v=1000000000LL-(end-v);}
   if(mode==2){for(int i=0;i<n;++i)(*coords)[i]=(i<n/2?1+i:1000000000LL-n+i+1);}
  }
  Points warped;for(int i=0;i<n;++i)warped.push_back({xs[i],ys[y_rank[i]]});
  const auto path=cover_points_orthogonally(warped);const auto got=check_geometry(warped,path);
  require(got==signature,"strict independent coordinate warps preserve axis/direction and number of segments");++signature_checks;
  if(n==100000)++maximum_calls;
  if(n==100000&&mode==1) {
   ++writer_calls;
   std::ostringstream out;write_line_output(out,warped);const auto bytes=out.str();
   require(bytes.size()<=2200073,"analytical worst decimal output size");
   std::istringstream in(bytes);std::size_t k=0;require(bool(in>>k)&&k+1==path.size(),"output writer count");
   for(std::size_t i=1;i<=k;++i){Point p{};require(bool(in>>p.x>>p.y)&&p==path[i],"output writer integer vertices excluding origin");}
   std::string extra;require(!(in>>extra),"output writer has no extra origin/trailing point");
  }
 }
}
int main(){auto begin=std::chrono::steady_clock::now();std::mt19937_64 rng(40192177ULL);
 for(int n:{1,2,3,4,5,6,7,8,9,10,11,17,32,101,500,5000,100000})for(int pattern=0;pattern<6;++pattern) {
  std::vector<int> rank(n);std::iota(rank.begin(),rank.end(),0);
  if(pattern==1)std::reverse(rank.begin(),rank.end());
  if(pattern==2)for(int i=0;i<n;++i)rank[i]=i%2==0?i/2:n-1-i/2;
  if(pattern==3)std::rotate(rank.begin(),rank.begin()+n/2,rank.end());
  if(pattern==4)std::shuffle(rank.begin(),rank.end(),rng);
  if(pattern==5){std::vector<int> next;for(int i=0;i<n;i+=2)next.push_back(i);for(int i=1;i<n;i+=2)next.push_back(i);rank=std::move(next);}
  verify(rank,rng);
 }
 for(int trial=0;trial<300;++trial){int n=10+int(rng()%2991);std::vector<int> rank(n);std::iota(rank.begin(),rank.end(),0);std::shuffle(rank.begin(),rank.end(),rng);verify(rank,rng);}
 std::cout<<"{\"checks\":"<<checks<<",\"baseRankPatterns\":"<<cases<<",\"directCoverCalls\":"<<4*cases
  <<",\"writerCalls\":"<<writer_calls<<",\"totalCoverConstructions\":"<<4*cases+writer_calls
  <<",\"strictCoordinateWarpSignatures\":"<<signature_checks<<",\"pointsChecked\":"<<points_checked<<",\"segmentsChecked\":"<<segments_checked
  <<",\"maximumN100000DirectCoverCalls\":"<<maximum_calls<<",\"maximumN100000WriterCalls\":"<<writer_calls
  <<",\"endpointCoverageHits\":"<<endpoint_hits<<",\"interiorCoverageHits\":"<<interior_hits
  <<",\"originalContestInputFilesTested\":0,\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count()<<"}\n";
}
'''
article=(Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/orthogonal-point-cover-spiral-two-chains.mdx').read_text();blocks=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S);assert len(blocks)==1
with tempfile.TemporaryDirectory(prefix='flowchartcp-line-independent-')as tmp:
    src=Path(tmp)/'review.cpp';binary=Path(tmp)/'review';src.write_text(blocks[0]+'\n'+HARNESS)
    subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(src),'-o',str(binary)],check=True)
    result=json.loads(subprocess.check_output([str(binary)],text=True))
result['cppSha256']=hashlib.sha256(blocks[0].encode()).hexdigest()
result['oracle']='For each segment, its unique supporting x/y identifies at most one input dot; direct coordinate-dictionary membership, no per-point all-segment search or interval union. Independent strict monotone x/y warps preserve segment axis/direction signatures.'
print(json.dumps(result,ensure_ascii=False))
