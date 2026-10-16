"""Run the twelve actual geometry article snippets against independent small models."""
from pathlib import Path
import concurrent.futures
import json
import os
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
HELPERS=r'''
using namespace std;
using ModelPoint=pair<long long,long long>;
__int128 model_cross(ModelPoint a,ModelPoint b,ModelPoint c){return (__int128)(b.first-a.first)*(c.second-a.second)-(__int128)(b.second-a.second)*(c.first-a.first);}
__int128 model_distance(ModelPoint a,ModelPoint b){__int128 x=(__int128)a.first-b.first,y=(__int128)a.second-b.second;return x*x+y*y;}
vector<ModelPoint> model_hull(vector<ModelPoint> p){
    sort(p.begin(),p.end());p.erase(unique(p.begin(),p.end()),p.end());if(p.size()<=1)return p;
    vector<ModelPoint> h;for(auto v:p){while(h.size()>=2 && model_cross(h[h.size()-2],h.back(),v)<=0)h.pop_back();h.push_back(v);}
    int lower=h.size();for(int i=int(p.size())-2;i>=0;--i){while(int(h.size())>lower && model_cross(h[h.size()-2],h.back(),p[i])<=0)h.pop_back();h.push_back(p[i]);}h.pop_back();return h;
}
int model_location(const vector<ModelPoint>& p,ModelPoint q){
    bool inside=false;
    for(int i=0;i<int(p.size());++i){auto a=p[i],b=p[(i+1)%p.size()];
        if(model_cross(a,b,q)==0 && min(a.first,b.first)<=q.first && q.first<=max(a.first,b.first) && min(a.second,b.second)<=q.second && q.second<=max(a.second,b.second))return 1;
        if((a.second>q.second)!=(b.second>q.second)){
            __int128 numerator=(__int128)(a.first-q.first)*(b.second-a.second)+(__int128)(b.first-a.first)*(q.second-a.second);
            bool to_right=(b.second>a.second)?numerator>0:numerator<0;
            if(to_right)inside=!inside;
        }
    }
    return inside?2:0;
}
int main(){using namespace tested;mt19937_64 rng(168248);
'''
CASES={
'geometry-closest-pair':r'''
    for(int trial=0;trial<2000;++trial){int n=2+rng()%70;vector<Point> p;vector<ModelPoint> model;
        for(int i=0;i<n;++i){long long x=int(rng()%101)-50,y=int(rng()%101)-50;p.push_back({x,y});model.push_back({x,y});}
        __int128 expected=(__int128)1<<120;for(int i=0;i<n;++i)for(int j=i+1;j<n;++j)expected=min(expected,model_distance(model[i],model[j]));
        assert(closest_distance_squared(p)==expected);
    }
    assert(closest_distance_squared({{-1000000000000LL,-1000000000000LL},{1000000000000LL,1000000000000LL}})==(__int128)8000000000000000000LL*1000000);
    vector<Point> vertical;for(int i=0;i<40000;++i)vertical.push_back({7,13LL*i});assert(closest_distance_squared(vertical)==169);
    bool thrown=false;try{closest_distance_squared({{0,0}});}catch(const invalid_argument&){thrown=true;}assert(thrown);
''',
'convex-point-membership':r'''
    for(int trial=0;trial<500;++trial){vector<ModelPoint> cloud;for(int i=0;i<25;++i)cloud.push_back({int(rng()%41)-20,int(rng()%41)-20});auto h=model_hull(cloud);if(h.size()<3)continue;
        vector<Point> p;for(auto [x,y]:h)p.push_back({x,y});ConvexLocation location(p);
        for(int q=0;q<200;++q){ModelPoint point={int(rng()%61)-30,int(rng()%61)-30};assert(location.locate({point.first,point.second})==model_location(h,point));}
        for(auto [x,y]:h)assert(location.locate({x,y})==1);
        for(int i=0;i<int(h.size());++i){auto a=h[i],b=h[(i+1)%h.size()];if((a.first+b.first)%2==0 && (a.second+b.second)%2==0)assert(location.locate({(a.first+b.first)/2,(a.second+b.second)/2})==1);}
    }
    ConvexLocation box({{-1000000000000LL,-1000000000000LL},{1000000000000LL,-1000000000000LL},{1000000000000LL,1000000000000LL},{-1000000000000LL,1000000000000LL}});
    assert(box.locate({0,0})==2 && box.locate({1000000000000LL,0})==1);
    ConvexLocation tri({{0,0},{4,0},{0,4}});assert(tri.locate({10,0})==0 && tri.locate({0,-1})==0 && tri.locate({1,1})==2);
''',
'convex-minkowski-sum':r'''
    auto convert=[](const vector<ModelPoint>& h){vector<Point> p;for(auto [x,y]:h)p.push_back({x,y});return p;};
    auto canonical=[](const vector<Point>& p){vector<ModelPoint> result;for(auto a:p)result.push_back({a.x,a.y});sort(result.begin(),result.end());return result;};
    for(int trial=0;trial<1000;++trial){vector<ModelPoint> a,b,c;for(int i=0;i<12;++i){a.push_back({int(rng()%31)-15,int(rng()%31)-15});b.push_back({int(rng()%31)-15,int(rng()%31)-15});c.push_back({int(rng()%31)-15,int(rng()%31)-15});}
        a=model_hull(a);b=model_hull(b);c=model_hull(c);if(a.size()<3 || b.size()<3 || c.size()<3)continue;
        auto pa=convert(a),pb=convert(b),pc=convert(c);rotate(pa.begin(),pa.begin()+rng()%pa.size(),pa.end());rotate(pb.begin(),pb.begin()+rng()%pb.size(),pb.end());
        vector<ModelPoint> all;for(auto x:a)for(auto y:b)all.push_back({x.first+y.first,x.second+y.second});auto expected=model_hull(all);sort(expected.begin(),expected.end());auto sum=minkowski_sum(pa,pb);assert(canonical(sum)==expected);
        vector<ModelPoint> triple;for(auto x:a)for(auto y:b)for(auto z:c)triple.push_back({x.first+y.first+z.first,x.second+y.second+z.second});auto third=model_hull(triple);sort(third.begin(),third.end());assert(canonical(minkowski_sum(sum,pc))==third);
    }
    auto square=convert({{-1,-1},{1,-1},{1,1},{-1,1}});assert(canonical(minkowski_sum(square,square))==vector<ModelPoint>({{-2,-2},{-2,2},{2,-2},{2,2}}));
''',
'convex-diameter-calipers':r'''
    for(int trial=0;trial<2000;++trial){int n=2+rng()%60;vector<Point> p;vector<ModelPoint> model;for(int i=0;i<n;++i){long long x=int(rng()%101)-50,y=int(rng()%101)-50;p.push_back({x,y});model.push_back({x,y});}
        __int128 expected=-1;for(int i=0;i<n;++i)for(int j=i+1;j<n;++j)expected=max(expected,model_distance(model[i],model[j]));auto [a,b]=furthest_pair(p);assert(a!=b && model_distance(model[a],model[b])==expected);
    }
    auto test=[&](vector<Point> p){auto [a,b]=furthest_pair(p);__int128 expected=-1;for(auto x:p)for(auto y:p)expected=max(expected,model_distance({x.x,x.y},{y.x,y.y}));assert(a!=b && model_distance({p[a].x,p[a].y},{p[b].x,p[b].y})==expected);};
    test({{3,4},{3,4},{3,4}});test({{-1000000000000LL,-1000000000000LL},{1000000000000LL,1000000000000LL},{0,0}});test({{0,0},{1,0},{2,0},{2,2},{1,2},{0,2}});test({{0,0},{100,0},{100,1},{0,1}});
''',
'convex-minimum-width':r'''
    auto brute=[](const vector<ModelPoint>& p){if(p.size()<2)return 0.L;long double best=numeric_limits<long double>::infinity();
        for(int i=0;i<int(p.size());++i)for(int j=0;j<i;++j)if(p[i]!=p[j]){__int128 lo=(__int128)1<<120,hi=-lo;for(auto q:p){auto value=model_cross(p[i],p[j],q);lo=min(lo,value);hi=max(hi,value);}long double width=(long double)(hi-lo)/sqrt((long double)model_distance(p[i],p[j]));best=min(best,width);}
        return isfinite(best)?best:0.L;};
    for(int trial=0;trial<1200;++trial){int n=rng()%25;vector<Point> p;vector<ModelPoint> model;for(int i=0;i<n;++i){long long x=int(rng()%51)-25,y=int(rng()%51)-25;p.push_back({x,y});model.push_back({x,y});}
        long double expected=brute(model),actual=minimum_width(p);assert(fabsl(actual-expected)<1e-10L);
    }
    assert(fabsl(minimum_width({{0,0},{3,0},{0,4}})-2.4L)<1e-12L);
    assert(minimum_width({{0,0},{1,1},{2,2},{1,1}})==0);
    assert(fabsl(minimum_width({{-1000000000,-1000000000},{1000000000,-1000000000},{1000000000,1000000000},{-1000000000,1000000000}})-2000000000.L)<1e-6L);
''',
'polygon-winding-integer':r'''
    auto check=[](vector<ModelPoint> model){for(int direction=0;direction<2;++direction){vector<Point> p;for(auto [x,y]:model)p.push_back({x,y});for(int x=-15;x<=15;++x)for(int y=-15;y<=15;++y)assert(polygon_location(p,{x,y})==model_location(model,{x,y}));reverse(model.begin(),model.end());}};
    for(int trial=0;trial<120;++trial){int w=2+rng()%10,h=2+rng()%10,a=1+rng()%(w-1),b=1+rng()%(h-1),tx=int(rng()%9)-4,ty=int(rng()%9)-4;
        vector<ModelPoint> p{{0,0},{w,0},{w,b},{a,b},{a,h},{0,h}};for(auto& q:p){q.first+=tx;q.second+=ty;}check(p);
    }
    check({{-8,-8},{8,-8},{8,8},{2,8},{2,0},{-2,0},{-2,8},{-8,8}});
    vector<Point> p{{-1000000000000LL,-1000000000000LL},{1000000000000LL,-1000000000000LL},{1000000000000LL,1000000000000LL},{-1000000000000LL,1000000000000LL}};assert(polygon_location(p,{0,0})==2 && polygon_location(p,{1000000000000LL,0})==1);
''',
'segment-intersection-orientation':r'''
    auto brute=[](ModelPoint a,ModelPoint b,ModelPoint c,ModelPoint d){
        auto inside=[](ModelPoint x,ModelPoint y,ModelPoint z){return model_cross(x,y,z)==0 && min(x.first,y.first)<=z.first && z.first<=max(x.first,y.first) && min(x.second,y.second)<=z.second && z.second<=max(x.second,y.second);};
        if(a==b)return inside(c,d,a);
        if(c==d)return inside(a,b,c);
        __int128 rx=b.first-a.first,ry=b.second-a.second,sx=d.first-c.first,sy=d.second-c.second,den=rx*sy-ry*sx;
        if(den==0)return inside(a,b,c)||inside(a,b,d)||inside(c,d,a)||inside(c,d,b);
        __int128 cx=c.first-a.first,cy=c.second-a.second,t=cx*sy-cy*sx,u=cx*ry-cy*rx;if(den<0){den=-den;t=-t;u=-u;}return 0<=t && t<=den && 0<=u && u<=den;
    };
    vector<ModelPoint> grid;for(int x=-1;x<=1;++x)for(int y=-1;y<=1;++y)grid.push_back({x,y});for(auto a:grid)for(auto b:grid)for(auto c:grid)for(auto d:grid)assert(segments_intersect({a.first,a.second},{b.first,b.second},{c.first,c.second},{d.first,d.second})==brute(a,b,c,d));
    for(int trial=0;trial<10000;++trial){array<ModelPoint,4> p;for(auto& q:p)q={int(rng()%101)-50,int(rng()%101)-50};assert(segments_intersect({p[0].first,p[0].second},{p[1].first,p[1].second},{p[2].first,p[2].second},{p[3].first,p[3].second})==brute(p[0],p[1],p[2],p[3]));}
    assert(segments_intersect({-1000000000000LL,-1000000000000LL},{1000000000000LL,1000000000000LL},{-1000000000000LL,1000000000000LL},{1000000000000LL,-1000000000000LL}));
''',
'collinear-direction-gcd':r'''
    for(int trial=0;trial<1000;++trial){int n=2+rng()%15;set<ModelPoint> unique;while(int(unique.size())<n)unique.insert({int(rng()%15)-7,int(rng()%15)-7});vector<ModelPoint> model(unique.begin(),unique.end());vector<Point> p;for(auto [x,y]:model)p.push_back({x,y});shuffle(p.begin(),p.end(),rng);
        set<tuple<long long,long long,long long>> lines;for(int i=0;i<n;++i)for(int j=0;j<i;++j){long long a=model[j].second-model[i].second,b=model[i].first-model[j].first,g=gcd(llabs(a),llabs(b));a/=g;b/=g;if(a<0 || (a==0 && b<0)){a=-a;b=-b;}long long c=-a*model[i].first-b*model[i].second;lines.insert({a,b,c});}
        for(int k=2;k<=n+1;++k){long long expected=0;for(auto [a,b,c]:lines){int count=0;for(auto [x,y]:model)count+=a*x+b*y+c==0;expected+=count>=k;}assert(count_rich_lines(p,k)==expected);}
        assert(!count_rich_lines(p,1));
    }
    assert(count_rich_lines({},1)==0);
    assert(count_rich_lines({{0,0}},2)==0);
    assert(count_rich_lines({{-1000000000000LL,0},{0,0},{1000000000000LL,0},{0,1000000000000LL}},3)==1);
    bool thrown=false;try{count_rich_lines({{0,0},{0,0}},2);}catch(const invalid_argument&){thrown=true;}assert(thrown);
''',
'perpendicular-direction-pairs':r'''
    for(int trial=0;trial<1200;++trial){int n=rng()%14;vector<pair<long long,long long>> p;for(int i=0;i<n;++i)p.push_back({int(rng()%9)-4,int(rng()%9)-4});long long expected=0;
        for(unsigned mask=1;mask<(1u<<n);++mask){bool ok=true;for(int i=0;i<n;++i)if(mask>>i&1)for(int j=0;j<i;++j)if(mask>>j&1)ok&=(__int128)p[i].first*p[j].first+(__int128)p[i].second*p[j].second!=0;expected+=ok;}
        assert(count_nonorthogonal_subsets(p)==expected);
    }
    assert(count_nonorthogonal_subsets({{1000000000000000000LL,1000000000000000000LL},{-1000000000000000000LL,1000000000000000000LL},{0,0}})==3);
    assert(count_nonorthogonal_subsets({{0,0},{0,0},{0,0}})==3);
    assert(count_nonorthogonal_subsets({{1,2},{-1,-2},{2,-1},{-2,1}})==6);
''',
'angle-vector-two-pointers':r'''
    for(int trial=0;trial<1000;++trial){int n=3+rng()%13;vector<ModelPoint> model;
        while(int(model.size())<n){ModelPoint q={int(rng()%101)-50,int(rng()%101)-50};bool ok=find(model.begin(),model.end(),q)==model.end();for(int i=0;i<int(model.size());++i)for(int j=0;j<i;++j)ok&=model_cross(model[i],model[j],q)!=0;if(ok)model.push_back(q);}
        vector<Point> p;for(auto [x,y]:model)p.push_back({x,y});array<long long,3> expected{};
        for(int i=0;i<n;++i)for(int j=0;j<i;++j)for(int k=0;k<j;++k){int type=0;array<int,3> ids{i,j,k};for(int t=0;t<3;++t){auto a=model[ids[t]],b=model[ids[(t+1)%3]],c=model[ids[(t+2)%3]];__int128 dot=(__int128)(b.first-a.first)*(c.first-a.first)+(__int128)(b.second-a.second)*(c.second-a.second);if(dot==0)type=max(type,1);if(dot<0)type=2;}++expected[type];}
        assert(triangle_angle_counts(p)==expected);
        if(trial<100){for(auto& q:p){q.x+=999999000;q.y+=999999000;}assert(triangle_angle_counts(p)==expected);}
    }
    assert((triangle_angle_counts({{0,0},{3,0},{0,4}})==array<long long,3>{0,1,0}));
    assert((triangle_angle_counts({{0,0},{2,0},{1,1}})==array<long long,3>{0,1,0}));
    vector<Point> parabola;for(int i=0;i<500;++i)parabola.push_back({i,1LL*i*i});auto counts=triangle_angle_counts(parabola);assert(counts[0]>=0 && counts[1]>=0 && counts[2]>=0 && counts[0]+counts[1]+counts[2]==500LL*499*498/6);
''',
'manhattan-nearest-octants':r'''
    auto check=[](const vector<Point>& p){int n=p.size();vector<long long> distance(n,LLONG_MAX);vector<bool> seen(n);__int128 expected=0;if(n)distance[0]=0;
        for(int step=0;step<n;++step){int v=-1;for(int i=0;i<n;++i)if(!seen[i] && (v<0 || distance[i]<distance[v]))v=i;seen[v]=true;expected+=distance[v];for(int i=0;i<n;++i)if(!seen[i])distance[i]=min(distance[i],llabs(p[i].x-p[v].x)+llabs(p[i].y-p[v].y));}
        auto actual=manhattan_mst(p);assert(actual.weight==expected && actual.edges.size()==(n?size_t(n-1):0));
        vector<int> parent(n);iota(parent.begin(),parent.end(),0);auto find=[&](int v){while(v!=parent[v])v=parent[v];return v;};__int128 weight=0;
        for(auto [a,b]:actual.edges){assert(0<=a && a<n && 0<=b && b<n);int u=find(a),v=find(b);assert(u!=v);parent[u]=v;weight+=llabs(p[a].x-p[b].x)+llabs(p[a].y-p[b].y);}assert(weight==expected);
    };
    vector<Point> grid;for(int x=-1;x<=1;++x)for(int y=-1;y<=1;++y)grid.push_back({x,y});for(unsigned mask=0;mask<(1u<<9);++mask){vector<Point> p;for(int i=0;i<9;++i)if(mask>>i&1)p.push_back(grid[i]);check(p);}
    for(int trial=0;trial<3500;++trial){int n=rng()%80;vector<Point> p;for(int i=0;i<n;++i)p.push_back({int(rng()%51)-25,int(rng()%51)-25});check(p);}
    for(int trial=0;trial<200;++trial){vector<Point> p;for(int i=0;i<60;++i)p.push_back({(long long)(rng()%2000000001)-1000000000,(long long)(rng()%2000000001)-1000000000});check(p);}
    check({{0,0},{0,0},{0,0},{0,0}});check({{0,0},{1,1},{2,0},{1,-1},{-1,1},{-2,0},{-1,-1}});
    vector<Point> large;for(int x=0;x<200;++x)for(int y=0;y<200;++y)large.push_back({x,y});auto result=manhattan_mst(large);assert(result.weight==39999 && result.edges.size()==39999);
''',
'convex-polygon-half-area':r'''
    auto check=[](vector<ModelPoint> p){int n=p.size();if(n<4)return;__int128 total=0;for(int i=0;i<n;++i)total+=(__int128)p[i].first*p[(i+1)%n].second-(__int128)p[i].second*p[(i+1)%n].first;__int128 expected=(__int128)1<<120;
        for(int i=0;i<n;++i)for(int length=2;length<=n-2;++length){vector<ModelPoint> piece;for(int k=0;k<=length;++k)piece.push_back(p[(i+k)%n]);__int128 area=0;for(int k=0;k<int(piece.size());++k){auto a=piece[k],b=piece[(k+1)%piece.size()];area+=(__int128)a.first*b.second-(__int128)a.second*b.first;}__int128 error=total-4*area;if(error<0)error=-error;expected=min(expected,error);}
        vector<Point> input;for(auto [x,y]:p)input.push_back({x,y});assert(quarter_area_error(input)==expected);for(int repeat=0;repeat<3;++repeat){rotate(input.begin(),input.begin()+1,input.end());assert(quarter_area_error(input)==expected);}
    };
    for(int trial=0;trial<1500;++trial){vector<ModelPoint> cloud;for(int i=0;i<30;++i)cloud.push_back({int(rng()%61)-30,int(rng()%61)-30});check(model_hull(cloud));}
    check({{0,0},{2,0},{4,0},{4,2},{4,4},{2,4},{0,4},{0,2}});
    check({{-1000000000,-1000000000},{1000000000,-1000000000},{1000000000,1000000000},{-1000000000,1000000000}});
    assert(quarter_area_error({{3,0},{2,3},{-1,3},{-3,1},{-1,-1}})==1);
'''
}

def run(item):
    slug,body=item
    article=(ROOT/'src/content/docs/techniques'/f'{slug}.mdx').read_text()
    snippets=re.findall(r'```cpp\n(.*?)```',article,re.S)
    if len(snippets)!=1:return slug,False,'Expected one published C++ implementation'
    includes=[];code=[]
    for line in snippets[0].splitlines():
        (includes if line.startswith('#include ') else code).append(line)
    source='#include <bits/stdc++.h>\n'+'\n'.join(includes)+'\nnamespace tested {\n'+'\n'.join(code)+'\n}\n'+HELPERS+body+'\n}\n'
    with tempfile.TemporaryDirectory(prefix='geometry-coverage-') as directory:
        cpp=Path(directory)/'test.cpp';exe=Path(directory)/'test';cpp.write_text(source)
        compiled=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)],capture_output=True,text=True,timeout=60)
        if compiled.returncode:return slug,False,compiled.stderr
        executed=subprocess.run([str(exe)],capture_output=True,text=True,timeout=40)
        return slug,executed.returncode==0,executed.stderr

if __name__=='__main__':
    rows=json.loads((ROOT/'data/geometry-problem-features.json').read_text())
    assert {id for row in rows for id in row['techniqueIds']}==set(CASES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES.items()))
    for slug,passed,output in results:print(slug,'PASS' if passed else 'FAIL',output)
    if any(not passed for _,passed,_ in results):raise SystemExit(1)
