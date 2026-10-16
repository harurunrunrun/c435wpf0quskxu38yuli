"""Verify the published score, legality, neighborhood and rollback components."""
from pathlib import Path
import concurrent.futures
import json
import os
import re
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
COMMON=r'''
int main(){
    using namespace tested;
    mt19937_64 rng(120261015);
    auto close=[](long double a,long double b){assert(fabsl(a-b)<=1e-11L*max(1.0L,fabsl(b)));};
    (void)close;
'''
CASES={
'heuristic-rectangle-score-delta':r'''
    auto independent=[](AdRectangle r,AdRequest q){
        if(q.x<r.left || q.x>=r.right || q.y<r.top || q.y>=r.bottom)return 0.0L;
        long long area=1LL*(r.right-r.left)*(r.bottom-r.top),small=min(area,q.area),large=max(area,q.area);
        return (long double)((__int128)2*small*large-(__int128)small*small)/((__int128)large*large);
    };
    for(int trial=0;trial<400;++trial){int n=1+rng()%25;vector<AdRectangle> r(n);vector<AdRequest> q(n);
        for(int i=0;i<n;++i){q[i]={int(rng()%100),int(rng()%100),1+(long long)(rng()%10000)};int x=rng()%100,y=rng()%100;r[i]={x,y,x+1+int(rng()%50),y+1+int(rng()%50)};}
        AdScoreCache cache(r,q);
        auto full=[&](){long double sum=0;for(int i=0;i<n;++i)sum+=independent(r[i],q[i]);return sum;};close(cache.value(),full());
        for(int operation=0;operation<120;++operation){int i=rng()%n,x=rng()%100,y=rng()%100;AdRectangle next{x,y,x+1+int(rng()%50),y+1+int(rng()%50)};
            long double before=full(),difference=cache.delta(i,next);r[i]=next;close(difference,full()-before);close(cache.replace(i,next),difference);close(cache.value(),full());if(operation%17==0){cache.recompute();close(cache.value(),full());}}
    }
    AdRequest q{0,0,100000000};close(ad_satisfaction({0,0,10000,10000},q),1);assert(ad_satisfaction({1,0,10000,10000},q)==0);
''',
'heuristic-rectangle-contact-bound':r'''
    auto overlap=[](AdRectangle a,AdRectangle b){return max(a.left,b.left)<min(a.right,b.right) && max(a.top,b.top)<min(a.bottom,b.bottom);};
    for(int trial=0;trial<1300;++trial){int bound=1+rng()%10,n=1+rng()%min(15,bound*bound);vector<pair<int,int>> locations;for(int y=0;y<bound;++y)for(int x=0;x<bound;++x)locations.push_back({x,y});shuffle(locations.begin(),locations.end(),rng);
        vector<AdRectangle> r;vector<AdRequest> requests;for(int i=0;i<n;++i){auto [x,y]=locations[i];r.push_back({x,y,x+1,y+1});requests.push_back({x,y,1+(long long)(rng()%(2*bound*bound))});}
        for(int step=0;step<10;++step){int index=rng()%n;auto old=r[index];auto q=requests[index];auto actual=best_single_edge(r,index,q,bound);long double expected=ad_satisfaction(old,q);
            auto valid=[&](AdRectangle candidate){if(candidate.left<0 || candidate.top<0 || candidate.right>bound || candidate.bottom>bound || candidate.left>=candidate.right || candidate.top>=candidate.bottom)return false;
                if(!(candidate.left<=q.x && q.x<candidate.right && candidate.top<=q.y && q.y<candidate.bottom))return false;
                for(int j=0;j<n;++j)if(j!=index && overlap(candidate,r[j]))return false;
                return true;};
            for(int side=0;side<4;++side)for(int value=0;value<=bound;++value){auto candidate=old;if(side==0)candidate.left=value;if(side==1)candidate.right=value;if(side==2)candidate.top=value;if(side==3)candidate.bottom=value;
                if(valid(candidate))expected=max(expected,ad_satisfaction(candidate,q));}
            assert(valid(actual));close(ad_satisfaction(actual,q),expected);r[index]=actual;
        }
    }
''',
'heuristic-path-tail-rollback':r'''
    for(int trial=0;trial<400;++trial){int h=1+rng()%4,w=1+rng()%4,n=h*w;vector<int> ids(n);vector<long long> points(n);
        iota(ids.begin(),ids.end(),0);for(int y=0;y<h;++y)for(int x=0;x+1<w;x+=2)if(rng()%2)ids[y*w+x+1]=ids[y*w+x];for(auto& x:points)x=int(rng()%30)-5;
        vector<int> current{int(rng()%n)};TilePath state(h,w,ids,points,current);
        auto score=[&](const vector<int>& path){__int128 result=0;for(int v:path)result+=points[v];return result;};
        auto valid=[&](const vector<int>& path){set<int> used;for(int i=0;i<(int)path.size();++i){int v=path[i];if(v<0 || v>=n || !used.insert(ids[v]).second)return false;if(i && abs(path[i-1]/w-v/w)+abs(path[i-1]%w-v%w)!=1)return false;}return true;};
        for(int operation=0;operation<150;++operation){int keep=1+rng()%current.size();vector<int> tail;
            if(rng()%3){int v=current[keep-1];for(int step=0;step<int(rng()%12);++step){int dir=rng()%4,y=v/w+(dir==0)-(dir==1),x=v%w+(dir==2)-(dir==3);v=y>=0 && y<h && x>=0 && x<w ? y*w+x : -1;if(v<0){tail.push_back(v);break;}tail.push_back(v);}}
            else {tail.resize(rng()%12);for(int& v:tail)v=int(rng()%(n+2))-1;}
            vector<int> proposal(current.begin(),current.begin()+keep);proposal.insert(proposal.end(),tail.begin(),tail.end());bool expected=valid(proposal),commit=rng()%2;__int128 before=score(current);
            auto actual=state.replace_tail(keep,tail,commit);assert(actual.has_value()==expected);if(expected)assert(*actual==score(proposal)-before);
            if(expected && commit)current=proposal;
            assert(state.path()==current && state.score()==score(current));
        }
    }
    TilePath same_tile(1,2,{0,0},{10,20},{0});assert(!same_tile.replace_tail(1,{1},true));assert(same_tile.path()==vector<int>{0});
    TilePath alternate_cell(2,2,{0,1,2,1},{10,20,30,40},{0,1});
    assert(alternate_cell.replace_tail(1,{2,3},false)==optional<__int128>{50});
    assert(alternate_cell.path()==vector<int>({0,1}) && alternate_cell.score()==30);
    assert(alternate_cell.replace_tail(1,{2,3},true)==optional<__int128>{50});
    assert(alternate_cell.path()==vector<int>({0,2,3}) && alternate_cell.score()==80);
    assert(!alternate_cell.replace_tail(2,{3,1},true));
    assert(alternate_cell.path()==vector<int>({0,2,3}) && alternate_cell.score()==80);
''',
'heuristic-path-reachable-upper-bound':r'''
    for(int trial=0;trial<1000;++trial){int h=1+rng()%3,w=1+rng()%4,n=h*w;vector<int> ids(n);vector<long long> point(n);iota(ids.begin(),ids.end(),0);
        for(int y=0;y<h;++y)for(int x=0;x+1<w;x+=2)if(rng()%2)ids[y*w+x+1]=ids[y*w+x];
        for(auto& x:point)x=int(rng()%20)-4;
        int endpoint=rng()%n;vector<char> used(n);used[ids[endpoint]]=1;
        for(int step=0;step<5;++step){vector<int> available;for(int u=0;u<n;++u)if(!used[ids[u]] && abs(endpoint/w-u/w)+abs(endpoint%w-u%w)==1)available.push_back(u);if(available.empty() || rng()%3==0)break;endpoint=available[rng()%available.size()];used[ids[endpoint]]=1;}
        auto best=[&](auto&& self,int v)->long long{long long value=0;for(int u=0;u<n;++u)if(!used[ids[u]] && abs(v/w-u/w)+abs(v%w-u%w)==1){used[ids[u]]=1;value=max(value,point[u]+self(self,u));used[ids[u]]=0;}return value;};
        auto snapshot=used;long long expected=best(best,endpoint);assert(used==snapshot);__int128 bound=reachable_tile_upper_bound(h,w,ids,point,used,endpoint);assert(bound>=expected);
        long long coarse=0;vector<long long> maximum(n);for(int v=0;v<n;++v)if(!used[ids[v]])maximum[ids[v]]=max(maximum[ids[v]],point[v]);for(auto x:maximum)coarse+=x;assert(bound<=coarse);
    }
    assert(reachable_tile_upper_bound(1,3,{0,0,1},{1,100,1000},{1,0,0},0)==0);
    assert(reachable_tile_upper_bound(2,2,{0,1,2,1},{1,10,20,100},{1,0,0},0)==120);
''',
'heuristic-precedence-two-opt':r'''
    auto length=[](const vector<DeliveryPoint>& p,const vector<int>& route){__int128 answer=0;for(size_t i=1;i<route.size();++i){__int128 dx=(__int128)p[route[i]].x-p[route[i-1]].x,dy=(__int128)p[route[i]].y-p[route[i-1]].y;answer+=(dx<0?-dx:dx)+(dy<0?-dy:dy);}return answer;};
    for(int trial=0;trial<600;++trial){int m=rng()%8;vector<DeliveryPoint> points(2*m+1);for(auto& p:points)p={int(rng()%41)-20,int(rng()%41)-20};vector<int> route{2*m};vector<char> seen(2*m);
        for(int step=0;step<2*m;++step){vector<int> choices;for(int v=0;v<2*m;++v)if(!seen[v] && (!(v&1) || seen[v-1]))choices.push_back(v);int v=choices[rng()%choices.size()];seen[v]=1;route.push_back(v);}route.push_back(2*m);
        for(int operation=0;operation<20;++operation){PrecedenceTour state(points,route);int l=1+rng()%(route.size()-1),r=1+rng()%(route.size()-1);if(l>r)swap(l,r);auto proposal=route;reverse(proposal.begin()+l,proposal.begin()+r);vector<int> positions(2*m);for(int i=1;i+1<(int)proposal.size();++i)positions[proposal[i]]=i;
            bool valid=true;for(int j=0;j<m;++j)if(positions[2*j]>positions[2*j+1])valid=false;
            auto difference=state.reversal_delta(l,r);assert(difference.has_value()==valid);if(valid)assert(*difference==length(points,proposal)-length(points,route));
            bool applied=state.reverse_interval(l,r);assert(applied==valid);assert(state.order()==(valid ? proposal : route));if(valid && rng()%2)route=proposal;
        }
    }
    PrecedenceTour coincident({{0,0},{1,1},{0,0},{1,1},{0,0}},{4,0,2,1,3,4});
    assert(!coincident.reversal_delta(1,4));
    assert(coincident.reversal_delta(1,3)==optional<__int128>{0});
    assert(coincident.reverse_interval(1,3));
    assert(coincident.order()==vector<int>({4,2,0,1,3,4}));
''',
'heuristic-paired-insertion-prefix':r'''
    auto length=[](const vector<DeliveryPoint>& route){__int128 result=0;for(size_t i=1;i<route.size();++i){__int128 x=(__int128)route[i].x-route[i-1].x,y=(__int128)route[i].y-route[i-1].y;result+=(x<0?-x:x)+(y<0?-y:y);}return result;};
    for(int trial=0;trial<2200;++trial){int n=2+rng()%10;vector<DeliveryPoint> route(n);for(auto& p:route)p={int(rng()%21)-10,int(rng()%21)-10};route.back()=route.front();DeliveryPoint pickup{int(rng()%21)-10,int(rng()%21)-10},delivery{int(rng()%21)-10,int(rng()%21)-10};
        __int128 before=length(route),best=(__int128)1<<120;
        for(int i=0;i+1<n;++i)for(int j=i;j+1<n;++j){vector<DeliveryPoint> proposal;for(int edge=0;edge+1<n;++edge){proposal.push_back(route[edge]);if(edge==i)proposal.push_back(pickup);if(edge==j)proposal.push_back(delivery);}proposal.push_back(route.back());best=min(best,length(proposal)-before);}
        auto actual=best_paired_insertion(route,pickup,delivery);assert(actual.delta==best && length(actual.route)-before==best && actual.pickup_gap<=actual.delivery_gap && actual.route.size()==route.size()+2);
    }
    auto large=best_paired_insertion({{LLONG_MIN,LLONG_MIN},{LLONG_MIN,LLONG_MIN}},{LLONG_MAX,LLONG_MIN},{LLONG_MAX,LLONG_MAX});assert(large.delta==4*((__int128)LLONG_MAX-LLONG_MIN));
''',
'heuristic-schedule-gap-delta':r'''
    auto full=[](const vector<long long>& c,const vector<vector<long long>>& s,const vector<int>& t){vector<int> last(c.size());__int128 answer=0;for(int day=1;day<=(int)t.size();++day){int type=t[day-1];answer+=s[day-1][type];last[type]=day;for(int i=0;i<(int)c.size();++i)answer-=(__int128)c[i]*(day-last[i]);}return answer;};
    for(int trial=0;trial<600;++trial){int days=rng()%31,kinds=1+rng()%8;vector<long long> c(kinds);for(auto& x:c)x=rng()%100;vector<vector<long long>> s(days,vector<long long>(kinds));for(auto& row:s)for(auto& x:row)x=int(rng()%1000)-200;vector<int> t(days);for(int& x:t)x=rng()%kinds;ScheduleGapScore state(c,s,t);assert(state.score()==full(c,s,t));
        if(days==0)continue;
        for(int operation=0;operation<200;++operation){int day=1+rng()%days,type=rng()%kinds;__int128 before=full(c,s,t),diff=state.delta(day,type);t[day-1]=type;assert(diff==full(c,s,t)-before);assert(state.change(day,type)==diff && state.score()==full(c,s,t));for(int d=1;d<=days;++d)assert(state.type_at(d)==t[d-1]);}
    }
''',
'heuristic-schedule-swap-transaction':r'''
    auto full=[](const vector<long long>& c,const vector<vector<long long>>& s,const vector<int>& t){vector<int> last(c.size());__int128 answer=0;for(int day=1;day<=(int)t.size();++day){answer+=s[day-1][t[day-1]];last[t[day-1]]=day;for(int i=0;i<(int)c.size();++i)answer-=(__int128)c[i]*(day-last[i]);}return answer;};
    bool dependent_example=false;
    for(int trial=0;trial<500;++trial){int days=1+rng()%30,kinds=1+rng()%8;vector<long long> c(kinds);for(auto& x:c)x=rng()%100;vector<vector<long long>> s(days,vector<long long>(kinds));for(auto& row:s)for(auto& x:row)x=rng()%1000;vector<int> t(days);for(int& x:t)x=rng()%kinds;ScheduleGapScore state(c,s,t);
        for(int operation=0;operation<160;++operation){int a=1+rng()%days,b=1+rng()%days;bool commit=rng()%2;auto proposal=t;swap(proposal[a-1],proposal[b-1]);__int128 before=full(c,s,t),expected=full(c,s,proposal)-before,independent=state.delta(a,t[b-1])+state.delta(b,t[a-1]);dependent_example|=expected!=independent;
            assert(schedule_swap_delta(state,a,b,commit)==expected);if(commit)t=proposal;assert(state.score()==full(c,s,t));for(int d=1;d<=days;++d)assert(state.type_at(d)==t[d-1]);}
    }
    assert(dependent_example);
''',
'heuristic-radius-threshold-candidates':r'''
    auto square=[](BroadcastPoint a,BroadcastPoint b){long long x=a.x-b.x,y=a.y-b.y;return x*x+y*y;};
    for(int trial=0;trial<1800;++trial){int n=rng()%30,limit=rng()%40;BroadcastPoint station{int(rng()%31)-15,int(rng()%31)-15};vector<BroadcastPoint> residents(n);for(auto& p:residents)p={int(rng()%31)-15,int(rng()%31)-15};
        auto candidates=broadcast_radius_candidates(station,residents,limit);assert(!candidates.empty() && candidates.front()==0 && is_sorted(candidates.begin(),candidates.end()));assert(adjacent_find(candidates.begin(),candidates.end())==candidates.end());
        for(int radius=0;radius<=limit;++radius){int replacement=*prev(upper_bound(candidates.begin(),candidates.end(),radius));assert(replacement<=radius);for(auto p:residents)assert((1LL*replacement*replacement>=square(station,p))==(1LL*radius*radius>=square(station,p)));}
        for(auto p:residents){long long expected=0;while(expected*expected<square(station,p))++expected;assert(required_integer_radius(station,p)==expected);}
    }
    assert(required_integer_radius({0,0},{3,4})==5);assert(required_integer_radius({0,0},{2,2})==3);assert(required_integer_radius({-10000,-10000},{10000,10000})==28285);
''',
'heuristic-cover-count-delta':r'''
    for(int trial=0;trial<600;++trial){int n=rng()%8,k=rng()%40,limit=1+rng()%30;vector<BroadcastPoint> stations(n),residents(k);for(auto& p:stations)p={int(rng()%31)-15,int(rng()%31)-15};for(auto& p:residents)p={int(rng()%31)-15,int(rng()%31)-15};vector<int> radius(n);for(int& r:radius)r=rng()%(limit+1);BroadcastCoverageCache state(stations,residents,radius,limit);
        auto check=[&](){vector<int> counts(k);__int128 cost=0;for(int s=0;s<n;++s){cost+=(__int128)radius[s]*radius[s];for(int p=0;p<k;++p){long long dx=stations[s].x-residents[p].x,dy=stations[s].y-residents[p].y;counts[p]+=dx*dx+dy*dy<=1LL*radius[s]*radius[s];}}
            assert(state.coverage_counts()==counts && state.power_cost()==cost && state.covered_count()==count_if(counts.begin(),counts.end(),[](int x){return x>0;}));};
        check();if(n==0)continue;
        for(int operation=0;operation<160;++operation){int s=rng()%n,next=rng()%(limit+1),old=radius[s];state.change(s,next);radius[s]=next;check();if(rng()%3==0){state.change(s,old);radius[s]=old;check();}}
    }
    BroadcastCoverageCache overlap({{0,0},{0,0}},{{0,0},{3,4}},{5,5},5);assert(overlap.covered_count()==2);overlap.change(0,0);assert(overlap.covered_count()==2);overlap.change(1,0);assert(overlap.covered_count()==1);
'''
}

def run(item):
    slug,body=item
    article=(ROOT/'src/content/docs/techniques'/f'{slug}.mdx').read_text()
    snippets=re.findall(r'```cpp\n(.*?)```',article,re.S)
    if len(snippets)!=1:return slug,False,'Expected one published implementation'
    includes=[];code=[]
    for line in snippets[0].splitlines():(includes if line.startswith('#include ') else code).append(line)
    source='\n'.join(includes)+'\nusing namespace std;\nnamespace tested{\n'+'\n'.join(code)+'\n}\n'+COMMON+body+'\n}\n'
    with tempfile.TemporaryDirectory(prefix='heuristic-coverage-') as directory:
        cpp=Path(directory)/'test.cpp';executable=Path(directory)/'test';cpp.write_text(source)
        compiled=subprocess.run([os.environ.get('CXX','g++'),'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(cpp),'-o',str(executable)],capture_output=True,text=True,timeout=60)
        if compiled.returncode:return slug,False,compiled.stderr
        executed=subprocess.run([str(executable)],capture_output=True,text=True,timeout=60)
        return slug,executed.returncode==0,executed.stderr

if __name__=='__main__':
    features=json.loads((ROOT/'data/heuristic-problem-features.json').read_text())
    assert {x['techniqueId'] for x in features}==set(CASES)
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,CASES.items()))
    for slug,passed,output in results:print(slug,'PASS' if passed else 'FAIL',output)
    if any(not passed for _,passed,_ in results):raise SystemExit(1)
