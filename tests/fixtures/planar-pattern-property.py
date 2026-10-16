from pathlib import Path
import re, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
checks={
'parallelogram-diagonal-midpoints':r'''
 using P=pair<long long,long long>;
 auto brute=[](const vector<P>&p){long long answer=0;for(int a=0;a<int(p.size());++a)for(int b=a+1;b<int(p.size());++b)for(int c=b+1;c<int(p.size());++c)for(int d=c+1;d<int(p.size());++d){int v[4]={a,b,c,d};bool good=false;for(int j=1;j<4;++j){int k=(j==1?2:1),l=6-j-k;auto A=p[v[0]],B=p[v[j]],C=p[v[k]],D=p[v[l]];if(A.first+B.first==C.first+D.first&&A.second+B.second==C.second+D.second){__int128 cross=(__int128)(B.first-A.first)*(D.second-C.second)-(__int128)(B.second-A.second)*(D.first-C.first);if(cross)good=true;}}answer+=good;}return answer;};
 for(int trial=0;trial<1000;++trial){set<P>s;int n=rng()%13;while(int(s.size())<n)s.insert({int(rng()%9)-4,int(rng()%9)-4});vector<P>p(s.begin(),s.end());assert(count_positive_parallelograms(p)==brute(p));}
 assert(count_positive_parallelograms({{0,0},{1,0},{2,0},{3,0}})==0);
 assert(count_positive_parallelograms({{-1000000000,-1000000000},{1000000000,-1000000000},{1000000000,1000000000},{-1000000000,1000000000}})==1);
 vector<P> parabola;for(int i=0;i<2000;++i)parabola.push_back({i,1LL*i*i});assert(count_positive_parallelograms(parabola)==0);
''',
'scaled-circle-lattice-scan':r'''
 auto text=[](long long value){bool neg=value<0;value=llabs(value);string frac=to_string(value%10000);frac=string(4-frac.size(),'0')+frac;return string(neg?"-":"")+to_string(value/10000)+"."+frac;};
 auto brute=[](long long x,long long y,long long r){long long answer=0;for(long long a=-12;a<=12;++a)for(long long b=-12;b<=12;++b){__int128 dx=10000*a-x,dy=10000*b-y;if(dx*dx+dy*dy<=(__int128)r*r)++answer;}return answer;};
 assert(parse_decimal4("-0.0001")==-1);assert(parse_decimal4("100000")==1000000000);assert(parse_decimal4("+.5")==5000);
 bool rejected=false;try{parse_decimal4("0.00001");}catch(const invalid_argument&){rejected=true;}assert(rejected);
 for(int trial=0;trial<2500;++trial){long long x=int(rng()%100001)-50000,y=int(rng()%100001)-50000,r=rng()%50001;assert(count_decimal_circle_lattice(text(x),text(y),text(r))==brute(x,y,r));}
 assert(count_decimal_circle_lattice("0.2","0.8","1.1")==3);
 assert(count_decimal_circle_lattice("100","100","1")==5);
 assert(count_decimal_circle_lattice("42782.4720","31949.0192","99999.99")==31415920098LL);
 auto large=count_decimal_circle_lattice("-0.0001","0","100000");assert(large==count_decimal_circle_lattice("0.0001","0","100000"));
 assert(count_decimal_circle_lattice("0","0","0")==1);assert(count_decimal_circle_lattice("0.1","0","0")==0);
''',
'point-congruence-cyclic-signature':r'''
 using P=CongruencePoint;using I=__int128;
 auto brute=[](const vector<P>&p,const vector<P>&q){if(p.size()!=q.size())return false;if(p.size()<=1)return true;long long dx=p[1].first-p[0].first,dy=p[1].second-p[0].second;I square=(I)dx*dx+(I)dy*dy;for(int a=0;a<int(q.size());++a)for(int b=0;b<int(q.size());++b)if(a!=b){long long ex=q[b].first-q[a].first,ey=q[b].second-q[a].second;if((I)ex*ex+(I)ey*ey!=square)continue;I co=(I)dx*ex+(I)dy*ey,si=(I)dx*ey-(I)dy*ex;set<pair<I,I>> wanted;for(auto[x,y]:q)wanted.insert({square*(x-q[a].first),square*(y-q[a].second)});bool good=true;for(auto[x,y]:p){x-=p[0].first;y-=p[0].second;if(!wanted.count({co*x-si*y,si*x+co*y}))good=false;}if(good)return true;}return false;};
 for(int trial=0;trial<1600;++trial){int n=rng()%9;set<P>a,b;while(int(a.size())<n)a.insert({int(rng()%11)-5,int(rng()%11)-5});while(int(b.size())<n)b.insert({int(rng()%11)-5,int(rng()%11)-5});vector<P>p(a.begin(),a.end()),q(b.begin(),b.end());assert(congruent_by_rotation_translation(p,q)==brute(p,q));if(trial%2==0){q.clear();for(auto[x,y]:p)q.push_back({-y+19,x-31});shuffle(q.begin(),q.end(),rng);assert(congruent_by_rotation_translation(p,q));}}
 assert(!congruent_by_rotation_translation({{1,0},{1,1},{3,0}},{{-1,0},{-1,1},{-3,0}}));
 assert(congruent_by_rotation_translation({{0,0},{5,0},{0,10}},{{10,20},{13,24},{2,26}}));
 assert(congruent_by_rotation_translation({{-2,0},{-1,0},{0,0},{1,0},{2,0}},{{7,11},{7,9},{7,10},{7,12},{7,8}}));
 vector<P>p,q;for(int i=0;i<200000;++i){p.push_back({i-100000,0});q.push_back({1000000000,999800000+i});}assert(congruent_by_rotation_translation(p,q));
''',
 'translated-convex-halfplane-max':r'''
 using P=pair<long long,long long>;
 auto cross=[](P a,P b,P c){return (__int128)(b.first-a.first)*(c.second-a.second)-(__int128)(b.second-a.second)*(c.first-a.first);};
 auto hull=[&](vector<P>p){sort(p.begin(),p.end());p.erase(unique(p.begin(),p.end()),p.end());vector<P>h;for(auto a:p){while(h.size()>=2&&cross(h[h.size()-2],h.back(),a)<=0)h.pop_back();h.push_back(a);}auto lower=h.size();for(int i=int(p.size())-2;i>=0;--i){while(h.size()>lower&&cross(h[h.size()-2],h.back(),p[i])<=0)h.pop_back();h.push_back(p[i]);}if(h.size()>1)h.pop_back();return h;};
 for(int trial=0;trial<1000;++trial){vector<P>p;for(int i=0;i<15;++i)p.push_back({int(rng()%21)-10,int(rng()%21)-10});p=hull(p);if(p.size()<3)continue;vector<P>shift;for(int j=0;j<1+int(rng()%8);++j)shift.push_back({int(rng()%7)-3,int(rng()%7)-3});TranslatedConvexIntersection subject(p,shift);for(int query=0;query<100;++query){P q={int(rng()%31)-15,int(rng()%31)-15};bool expected=true;for(auto [x,y]:shift)for(int i=0;i<int(p.size());++i){P a={p[i].first+x,p[i].second+y},b={p[(i+1)%p.size()].first+x,p[(i+1)%p.size()].second+y};if(cross(a,b,q)<0)expected=false;}assert(subject.contains(q)==expected);}}
 vector<P>square={{-1000000000,-1000000000},{1000000000,-1000000000},{1000000000,1000000000},{-1000000000,1000000000}};TranslatedConvexIntersection huge(square,{{1000000000,1000000000},{-1000000000,-1000000000}});assert(huge.contains({0,0}));assert(!huge.contains({1,0}));
 vector<P>shifts(200000,{0,0});TranslatedConvexIntersection many(square,shifts);for(int i=0;i<200000;++i)assert(many.contains({i,-i}));
''',
'repeated-grid-walk-orbits':r'''
 auto brute=[](const string&s,int k){set<pair<int,int>>visited={{0,0}};int x=0,y=0;while(k--)for(char c:s){if(c=='L')--x;if(c=='R')++x;if(c=='U')--y;if(c=='D')++y;visited.insert({x,y});}return (long long)visited.size();};
 string dirs="LRUD";
 for(int len=0;len<=6;++len){int total=1<<(2*len);for(int mask=0;mask<total;++mask){string s(len,'L');int m=mask;for(auto&c:s){c=dirs[m%4];m/=4;}for(int k=0;k<=5;++k)assert(count_repeated_grid_visits(s,k)==brute(s,k));}}
 for(int trial=0;trial<2500;++trial){string s(rng()%50,'L');for(auto&c:s)c=dirs[rng()%4];int k=rng()%11;assert(count_repeated_grid_visits(s,k)==brute(s,k));}
 assert(count_repeated_grid_visits("RDRUL",2)==7);assert(count_repeated_grid_visits("UUURRDDDRRRUUUURDLLUURRRDDDDDDLLLLLLU",31415926535LL)==219911485785LL);
 for(char c:dirs)assert(count_repeated_grid_visits(string(200000,c),1000000000000LL)==200000000000000001LL);
 string closed;for(int i=0;i<100000;++i)closed+="LR";assert(count_repeated_grid_visits(closed,1000000000000LL)==2);
''',
'plane-wall-compressed-cells':r'''
 using Wall=array<long long,3>;
 auto brute=[](const vector<Wall>&h,const vector<Wall>&v)->optional<long long>{set<pair<int,int>>seen={{0,0}};vector<pair<int,int>>q={{0,0}};int di[]={-1,1,0,0},dj[]={0,0,-1,1};for(size_t head=0;head<q.size();++head){auto [x,y]=q[head];if(abs(x)>=6||abs(y)>=6)return nullopt;for(int d=0;d<4;++d){int a=x+di[d],b=y+dj[d];bool blocked=false;if(d<2){int boundary=max(x,a);for(auto [vx,low,high]:v)if(vx==boundary&&low<=y&&y+1<=high)blocked=true;}else{int boundary=max(y,b);for(auto[low,high,hy]:h)if(hy==boundary&&low<=x&&x+1<=high)blocked=true;}if(!blocked&&seen.insert({a,b}).second)q.push_back({a,b});}}return seen.size();};
 for(int trial=0;trial<2500;++trial){vector<Wall>h,v;for(int k=0;k<12;++k){int a=int(rng()%7)-3,b=int(rng()%7)-3,c=int(rng()%7)-3;if(a>b)swap(a,b);if(a==b||(c==0&&a<=0&&0<=b))continue;if(rng()%2)h.push_back({a,b,c});else v.push_back({c,a,b});}assert(origin_region_area(h,v)==brute(h,v));}
 assert(origin_region_area({{-1,1,-1},{-1,1,1}},{{-1,-1,1},{1,-1,1}})==optional<long long>(4));
 assert(origin_region_area({{-1000000000,1000000000,-1000000000},{-1000000000,1000000000,1000000000}},{{-1000000000,-1000000000,1000000000},{1000000000,-1000000000,1000000000}})==optional<long long>(4000000000000000000LL));
 vector<Wall>h,v;for(int i=1;i<=500;++i){h.push_back({-i,i,-i});h.push_back({-i,i,i});v.push_back({-i,-i,i});v.push_back({i,-i,i});}assert(origin_region_area(h,v)==optional<long long>(4));
 assert(!origin_region_area({},{}));assert(!origin_region_area({{-2,2,1}},{{1,-2,2}}));
''',
'disk-cover-center-intersections':r'''
 using P=pair<long long,long long>;
 auto brute=[](const vector<P>&p){if(p.empty())return 0.0L;long double best=1e100L;auto test=[&](long double x,long double y){long double r2=0;for(auto[a,b]:p)r2=max(r2,(x-a)*(x-a)+(y-b)*(y-b));best=min(best,sqrtl(r2));};for(auto[x,y]:p)test(x,y);for(int i=0;i<int(p.size());++i)for(int j=0;j<i;++j)test((p[i].first+p[j].first)/2.0L,(p[i].second+p[j].second)/2.0L);for(int i=0;i<int(p.size());++i)for(int j=0;j<i;++j)for(int k=0;k<j;++k){long double ax=p[j].first-p[i].first,ay=p[j].second-p[i].second,bx=p[k].first-p[i].first,by=p[k].second-p[i].second,d=2*(ax*by-ay*bx);if(d==0)continue;long double aa=ax*ax+ay*ay,bb=bx*bx+by*by;test(p[i].first+(aa*by-bb*ay)/d,p[i].second+(ax*bb-bx*aa)/d);}return best;};
 for(int trial=0;trial<450;++trial){vector<P>p;for(int i=0,n=rng()%10;i<n;++i)p.push_back({int(rng()%15)-7,int(rng()%15)-7});long double expected=brute(p),got=minimum_covering_radius(p);assert(fabsl(expected-got)<=1e-8L*max(1.0L,expected));}
 assert(fabsl(minimum_covering_radius({{0,0},{1,0}})-0.5L)<1e-10L);
 assert(fabsl(minimum_covering_radius({{10,9},{5,9},{2,0},{0,0},{2,7},{3,3},{2,5},{10,0},{3,7},{1,9}})-6.726812023536805158L)<1e-8L);
 vector<P>line;for(int i=0;i<100;++i)line.push_back({-1000000+2000000*i/99,1});assert(fabsl(minimum_covering_radius(line)-1000000.0L)<1e-6L);
 assert(fabsl(minimum_covering_radius({{-1000000,-1000000},{1000000,-1000000},{1000000,1000000},{-1000000,1000000}})-sqrtl(2.0L)*1000000)<1e-6L);
 assert(minimum_covering_radius(vector<P>(100,{7,8}))==0);
''',
'isosceles-trapezoid-bisector-groups':r'''
 using P=WeightedPlanarPoint;
 auto cross=[](P a,P b,P c){return (__int128)(b.x-a.x)*(c.y-a.y)-(__int128)(b.y-a.y)*(c.x-a.x);};
 auto norm=[](P a,P b){return (__int128)(a.x-b.x)*(a.x-b.x)+(__int128)(a.y-b.y)*(a.y-b.y);};
 auto brute=[&](const vector<P>&p)->optional<long long>{optional<long long>answer;for(int a=0;a<int(p.size());++a)for(int b=a+1;b<int(p.size());++b)for(int c=b+1;c<int(p.size());++c)for(int d=c+1;d<int(p.size());++d){vector<P>s={p[a],p[b],p[c],p[d]};sort(s.begin(),s.end(),[](auto u,auto v){return tie(u.x,u.y)<tie(v.x,v.y);});vector<P>h;for(auto point:s){while(h.size()>=2&&cross(h[h.size()-2],h.back(),point)<=0)h.pop_back();h.push_back(point);}auto lower=h.size();for(int i=2;i>=0;--i){while(h.size()>lower&&cross(h[h.size()-2],h.back(),s[i])<=0)h.pop_back();h.push_back(s[i]);}h.pop_back();if(h.size()!=4||norm(h[0],h[2])!=norm(h[1],h[3]))continue;bool good=false;for(int i=0;i<2;++i){auto u=h[i],v=h[(i+1)%4],w=h[(i+2)%4],z=h[(i+3)%4];if((__int128)(v.x-u.x)*(z.y-w.y)-(__int128)(v.y-u.y)*(z.x-w.x)==0)good=true;}long long weight=p[a].weight+p[b].weight+p[c].weight+p[d].weight;if(good&&(!answer||weight>*answer))answer=weight;}return answer;};
 for(int trial=0;trial<2000;++trial){set<pair<int,int>>s;int n=rng()%13;while(int(s.size())<n)s.insert({int(rng()%11)-5,int(rng()%11)-5});vector<P>p;for(auto[x,y]:s)p.push_back({x,y,1+int(rng()%100)});assert(maximum_isosceles_trapezoid_weight(p)==brute(p));}
 assert(maximum_isosceles_trapezoid_weight({{0,3,10},{3,3,10},{-1,0,10},{2,0,10000},{4,0,10}})==optional<long long>(40));
 assert(!maximum_isosceles_trapezoid_weight({{-3,0,1},{-2,0,1},{-1,0,1},{0,0,1},{1,0,1},{2,0,1},{3,0,1}}));
 assert(maximum_isosceles_trapezoid_weight({{-1000000000,-1000000000,1000000000},{1000000000,-1000000000,1000000000},{1000000000,1000000000,1000000000},{-1000000000,1000000000,1000000000}})==optional<long long>(4000000000LL));
 vector<P>large;for(int i=0;i<500;++i){large.push_back({i,0,1000000000});large.push_back({i,2,1000000000});}assert(maximum_isosceles_trapezoid_weight(large)==optional<long long>(4000000000LL));
'''
}
rejections={
    'parallelogram-diagonal-midpoints':'count_positive_parallelograms({{LLONG_MIN,0}});',
    'point-congruence-cyclic-signature':'congruent_by_rotation_translation({{LLONG_MIN,0}},{{0,0}});',
    'plane-wall-compressed-cells':'origin_region_area({{LLONG_MIN,1,1}},{});',
    'disk-cover-center-intersections':'minimum_covering_radius({{LLONG_MIN,0}});',
    'isosceles-trapezoid-bisector-groups':'maximum_isosceles_trapezoid_weight({{LLONG_MIN,0,1}});'
}
for id,call in rejections.items():
    checks[id]+='\n{bool invalid_rejected=false;try{'+call+'}catch(const invalid_argument&){invalid_rejected=true;}assert(invalid_rejected);}\n'
with tempfile.TemporaryDirectory(prefix='flowchartcp-planar-patterns-') as tmp:
    for id,body in checks.items():
        article=(ROOT/'src/content/docs/techniques'/f'{id}.mdx').read_text()
        code=re.findall(r'```cpp\n(.*?)\n```',article,re.S)[0]
        source=Path(tmp)/(id+'.cpp');binary=Path(tmp)/id
        source.write_text('#include <bits/stdc++.h>\nusing namespace std;\n'+code+'\nint main(){mt19937 rng(34902851);\n'+body+'\n}\n')
        result=subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(id+'\n'+result.stderr)
        subprocess.run([str(binary)],check=True,timeout=50)
        print(id+' PASS',flush=True)
