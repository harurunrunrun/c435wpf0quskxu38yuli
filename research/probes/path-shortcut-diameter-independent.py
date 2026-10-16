#!/usr/bin/env python3
"""Actual MDX fence versus physical unit-edge BFS and branch-length translations."""
import argparse, hashlib, json, os, pathlib, re, subprocess, tempfile

CPP_SHA='3a6f404db20af159ce47c67688ee05f93586a6833da3d6fce24a38bb3f41cad4'
HARNESS=r'''
#include <chrono>
#include <iostream>
#include <numeric>
#include <random>
#include <sys/resource.h>
using V=std::vector<int>;using I=std::int64_t;using Graph=std::vector<V>;
static std::uint64_t checks=0,api_calls=0,checksum=0,small=0,randoms=0,graphs=0,bfs_runs=0,bfs_visits=0,bfs_arcs=0,thresholds=0,translations=0,scaled=0,two_station=0,boxes=0,box_pairs=0,max_translations=0;
void need(bool v,const char*message){++checks;if(!v)throw std::runtime_error(message);}
void record(I x){checksum=checksum*1000003ULL+static_cast<std::uint64_t>(x);}
int vertex(Graph&g){g.emplace_back();return static_cast<int>(g.size())-1;}
void join(Graph&g,int a,int b,int length){
 for(int step=1;step<length;++step){int mid=vertex(g);g[a].push_back(mid);g[mid].push_back(a);a=mid;}
 g[a].push_back(b);g[b].push_back(a);
}
struct Instance{V l,d;int c;};
struct Literal{I best,original;};
I physical_diameter(const Graph&g,const V&stations){
 I answer=0;V distance(g.size()),queue(g.size());
 for(int source:stations){++bfs_runs;std::fill(distance.begin(),distance.end(),-1);int left=0,right=0;distance[source]=0;queue[right++]=source;++bfs_visits;
  while(left<right){int a=queue[left++];for(int b:g[a]){++bfs_arcs;if(distance[b]<0){distance[b]=distance[a]+1;queue[right++]=b;++bfs_visits;}}}
  for(int target:stations){need(distance[target]>=0,"literal expanded graph connected");answer=std::max<I>(answer,distance[target]);}
 }
 return answer;
}
Literal literal(const Instance&a){
 const int n=static_cast<int>(a.d.size());Graph base(n);V stations(n);std::iota(stations.begin(),stations.end(),0);
 for(int i=0;i+1<n;++i)join(base,i,i+1,a.l[i]);
 for(int i=0;i<n;++i)if(a.d[i]){int leaf=vertex(base);stations.push_back(leaf);join(base,i,leaf,a.d[i]);}
 // Subdivision vertices participate only in routes. Original main/leaf stations
 // alone are diameter targets; a continuous-edge diameter would be different.
 Literal out{std::numeric_limits<I>::max(),physical_diameter(base,stations)};
 for(int u=0;u<n;++u)for(int v=u+1;v<n;++v){Graph g=base;join(g,u,v,a.c);++graphs;out.best=std::min(out.best,physical_diameter(g,stations));}
 return out;
}
I core(const Instance&a){++api_calls;I answer=minimum_path_shortcut_diameter(a.l,a.d,a.c);record(answer);return answer;}
void test(const Instance&a,bool transform){
 const auto expected=literal(a);PathShortcut value(a.l,a.d,a.c);++api_calls;
 ++api_calls;I actual=value.minimum_diameter();record(actual);need(actual==expected.best,"production minimum versus expanded unit-edge BFS");
 for(I k=0;k<=expected.original+1;++k){++api_calls;++thresholds;bool got=value.can_achieve(k);record(got);need(got==(k>=expected.best),"every threshold versus physical BFS optimum");}
 ++api_calls;need(value.can_achieve(std::numeric_limits<I>::max()),"large predicate shortcut avoids overflow");
 if(!transform)return;
 Instance lifted=a;for(int&d:lifted.d)d+=2;
 const auto lifted_expected=literal(lifted);need(lifted_expected.best==expected.best+4,"all branches +2 gives exact diameter +4 via literal graph");
 need(core(lifted)==expected.best+4,"all branches +2 production translation");++translations;
 if(a.d.size()<=7){Instance times=a;for(int&l:times.l)l*=3;for(int&d:times.d)d*=3;times.c*=3;
  need(literal(times).best==3*expected.best,"unit subdivision scale preserves original-station target set");need(core(times)==3*expected.best,"production common edge scale");++scaled;
 }
}
void exhaustive(){
 for(int n=2;n<=4;++n){int branch_profiles=1;for(int i=0;i<n;++i)branch_profiles*=4;
  for(int gap_bits=0;gap_bits<(1<<(n-1));++gap_bits){V l(n-1);for(int i=0;i<n-1;++i)l[i]=1+((gap_bits>>i)&1);
   for(int profile=0;profile<branch_profiles;++profile){int code=profile;V d(n);for(int&v:d){v=code%4;code/=4;}
    for(int c=1;c<=4;++c){++small;test({l,d,c},small%23==0);}
   }
  }
 }
}
void varied(){std::mt19937_64 rng(0x53484f5254435554ULL);
 for(int it=0;it<480;++it){int n=5+static_cast<int>(rng()%5);Instance a{V(n-1),V(n),1+static_cast<int>(rng()%8)};
  for(int&v:a.l)v=1+static_cast<int>(rng()%4);
  for(int&v:a.d)v=static_cast<int>(rng()%5);
  test(a,true);++randoms;
 }
}
void n2_boundaries(){const V lengths{1,2,3,999999937,999999999,1000000000},leaves{0,1,2,999999999,1000000000};
 for(int length:lengths)for(int a:leaves)for(int b:leaves)for(int c:lengths){Instance x{{length},{a,b},c};I expected=I(a)+b+std::min(length,c);
  need(core(x)==expected,"N2 exact single alternate edge with extreme coordinates");PathShortcut p(x.l,x.d,c);++api_calls;
  ++api_calls;need(!p.can_achieve(expected-1),"N2 extreme lower boundary");++api_calls;need(p.can_achieve(expected),"N2 extreme exact boundary");
  ++api_calls;need(p.can_achieve(std::numeric_limits<I>::max()),"N2 INT64_MAX guard");++api_calls;need(find_shortcut(2,x.l,x.d,c)==expected,"N2 original adapter exact closed form");++two_station;
 }
}
void extreme_boxes(){std::mt19937_64 rng(0x56414c4c4559ULL);
 for(int it=0;it<20000;++it){int n=2+static_cast<int>(rng()%19);std::vector<I>x(n);for(int i=1;i<n;++i)x[i]=x[i-1]+1+static_cast<I>(rng()%1000000000ULL);
  int u=static_cast<int>(rng()%n),v=static_cast<int>(rng()%n);if(u>v)std::swap(u,v);I sum=x[u]+x[v],diff=x[v]-x[u];
  auto around=[&](I center){return center+static_cast<I>(rng()%5)-2;};
  std::array<I,4>b{around(sum),around(sum),around(diff),around(diff)};
  if(it%4==0){b[0]=-10000000000000000LL;b[1]=10000000000000000LL;}
  if(it%5==0){b[2]=1;b[3]=x.back();}
  bool expected=false;for(int i=0;i<n;++i)for(int j=i+1;j<n;++j){++box_pairs;expected|=b[0]<=x[i]+x[j]&&x[i]+x[j]<=b[1]&&b[2]<=x[j]-x[i]&&x[j]-x[i]<=b[3];}
  bool got=path_shortcut_detail::station_pair(x,b);need(got==expected,"extreme/inverted/exact boxes versus literal distinct station pairs");record(got);++boxes;
 }
}
void maximum_translation(){const int n=1000000;Instance a{V(n-1),V(n),123457};
 for(int i=0;i+1<n;++i)a.l[i]=1+static_cast<int>((std::uint64_t(i)*13007)%1000000000);
 for(int i=0;i<n;++i)a.d[i]=static_cast<int>((std::uint64_t(i)*7919)%1000);
 const I before=core(a);for(int&d:a.d)d+=999998000;need(core(a)==before+1999996000LL,"million-station heterogeneous branch translation");++max_translations;
}
int main(){try{const auto start=std::chrono::steady_clock::now();exhaustive();varied();n2_boundaries();extreme_boxes();maximum_translation();rusage usage{};getrusage(RUSAGE_SELF,&usage);
 std::cout<<"{\"checks\":"<<checks<<",\"apiCalls\":"<<api_calls<<",\"allSmallN2to4\":"<<small<<",\"randomPhysicalCases\":"<<randoms<<",\"unitExpandedShortcutGraphs\":"<<graphs<<",\"originalStationBfsRuns\":"<<bfs_runs<<",\"bfsVertexVisits\":"<<bfs_visits<<",\"bfsArcScans\":"<<bfs_arcs<<",\"allThresholdComparisons\":"<<thresholds<<",\"literalBranchTranslations\":"<<translations<<",\"literalTripleScales\":"<<scaled<<",\"extremeTwoStationCases\":"<<two_station<<",\"extremeDiscreteBoxes\":"<<boxes<<",\"literalBoxStationPairs\":"<<box_pairs<<",\"millionStationBranchTranslations\":"<<max_translations<<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"peakRSSKiB\":"<<usage.ru_maxrss<<"}\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--sanitize',action='store_true')
    parser.add_argument('--article',default=str(pathlib.Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/path-shortcut-diameter-rotated-constraints-extrema-sweep.mdx'))
    parser.add_argument('--output')
    args=parser.parse_args()
    article=pathlib.Path(args.article).read_text()
    fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
    assert len(fences)==1
    cpp=fences[0];assert hashlib.sha256(cpp.encode()).hexdigest()==CPP_SHA
    flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-shortcut-independent-')as folder:
        source=pathlib.Path(folder)/'probe.cpp';binary=pathlib.Path(folder)/'probe'
        source.write_text(cpp+'\n'+HARNESS)
        subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
        env=os.environ.copy()
        if args.sanitize:env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1:print_stacktrace=1'
        run=subprocess.run([str(binary)],env=env,capture_output=True,text=True)
        if run.returncode:raise RuntimeError(run.stderr or run.stdout)
        result=json.loads(run.stdout)
    result.update(cppSha256=CPP_SHA,sanitized=args.sanitize)
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:pathlib.Path(args.output).write_text(text)
    print(text,end='')
if __name__=='__main__':main()
