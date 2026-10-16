from pathlib import Path
import re, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[2]
checks={
'weighted-tree-exact-length-min-edges':r'''
 auto brute=[](int n,int target,const vector<tuple<int,int,int>>&edges){vector<vector<pair<int,int>>>g(n);for(auto[u,v,w]:edges){g[u].push_back({v,w});g[v].push_back({u,w});}int answer=n+1;for(int source=0;source<n;++source){vector<tuple<int,int,int,int>>st{{source,-1,0,0}};while(!st.empty()){auto[v,p,d,h]=st.back();st.pop_back();if(v!=source&&d==target)answer=min(answer,h);for(auto[u,w]:g[v])if(u!=p)st.push_back({u,v,d+w,h+1});}}return answer<=n?answer:-1;};
 assert(minimum_edges_exact_tree_length(0,0,{})==-1);
 assert(minimum_edges_exact_tree_length(1,0,{})==-1);
 assert(minimum_edges_exact_tree_length(2,0,{{0,1,0}})==1);
 assert(minimum_edges_exact_tree_length(2,0,{{0,1,1}})==-1);
 assert(minimum_edges_exact_tree_length(4,3,{{0,1,1},{1,2,2},{1,3,4}})==2);
 for(int trial=0;trial<2000;++trial){int n=1+rng()%15;vector<tuple<int,int,int>>e;for(int v=1;v<n;++v)e.push_back({v,int(rng()%v),int(rng()%8)});int target=rng()%50;assert(minimum_edges_exact_tree_length(n,target,e)==brute(n,target,e));}
 vector<tuple<int,int,int>>chain;for(int v=1;v<200000;++v)chain.push_back({v-1,v,1});assert(minimum_edges_exact_tree_length(200000,123456,chain)==123456);
 vector<tuple<int,int,int>>star;for(int v=1;v<200000;++v)star.push_back({0,v,1});assert(minimum_edges_exact_tree_length(200000,1000000,star)==-1);
''',
'range-clamp-composition':r'''
 for(int trial=0;trial<500;++trial){int n=rng()%35;vector<long long>a(n);for(auto&x:a)x=int(rng()%31)-15;RangeClamps tree(a);for(int q=0;q<80;++q){int l=rng()%(n+1),r=rng()%(n+1);if(l>r)swap(l,r);long long h=int(rng()%31)-15;bool lower=rng()%2;if(lower){tree.chmax(l,r,h);for(int i=l;i<r;++i)a[i]=max(a[i],h);}else{tree.chmin(l,r,h);for(int i=l;i<r;++i)a[i]=min(a[i],h);}if(q%7==0)assert(tree.values()==a);}assert(tree.values()==a);}
 RangeClamps edge({LLONG_MIN,LLONG_MAX,0});edge.chmax(0,3,LLONG_MAX);edge.chmin(0,2,LLONG_MIN);assert(edge.values()==vector<long long>({LLONG_MIN,LLONG_MIN,LLONG_MAX}));
 RangeClamps chronology({0,0,0,0});chronology.chmax(0,4,10);chronology.chmin(1,3,3);chronology.chmax(2,4,7);assert(chronology.values()==vector<long long>({10,3,7,10}));
 RangeClamps large(vector<long long>(2000000));large.chmax(0,2000000,4);large.chmin(500000,1500000,2);auto output=large.values();assert(output.size()==2000000);assert(output[499999]==4&&output[500000]==2&&output[1499999]==2&&output[1500000]==4);
''',
'active-top-k-count-sum':r'''
 for(int trial=0;trial<300;++trial){int n=rng()%35;vector<long long>a(n);for(auto&x:a)x=int(rng()%15)-7;ActiveTopK state(a);vector<bool>enabled(n);for(int q=0;q<100;++q){if(n){int id=rng()%n;bool on=rng()%2;state.set_active(id,on);state.set_active(id,on);enabled[id]=on;}vector<long long>active;for(int i=0;i<n;++i)if(enabled[i])active.push_back(a[i]);sort(active.rbegin(),active.rend());for(int k=0;k<=n+2;++k){long long expected=accumulate(active.begin(),active.begin()+min<int>(k,active.size()),0LL);assert(state.largest_sum(k)==expected);}}}
 ActiveTopK empty({});assert(empty.largest_sum(LLONG_MAX)==0);
 ActiveTopK large(vector<long long>(200000,1000000000000LL));for(int i=0;i<200000;++i)large.set_active(i,true);assert(large.largest_sum(LLONG_MAX)==200000000000000000LL);for(int i=0;i<100000;++i)large.set_active(i,false);assert(large.largest_sum(50000)==50000000000000000LL);
''',
'median-window-budget':r'''
 auto brute=[](const vector<long long>&x,long long budget){int n=int(x.size()),best=0;for(int mask=1;mask<(1<<n);++mask){vector<long long>chosen;for(int i=0;i<n;++i)if(mask>>i&1)chosen.push_back(x[i]);long long median=chosen[chosen.size()/2],cost=0;for(auto v:chosen)cost+=llabs(v-median);if(cost<=budget)best=max(best,int(chosen.size()));}return best;};
 assert(maximum_gathered_points({},0)==0);assert(maximum_gathered_points({1,2,10,12,14},6)==3);assert(maximum_gathered_points({7,7,7,7},0)==4);
 for(int trial=0;trial<1200;++trial){vector<long long>x(rng()%13);for(auto&v:x)v=int(rng()%41)-20;sort(x.begin(),x.end());long long b=rng()%100;assert(maximum_gathered_points(x,b)==brute(x,b));}
 vector<long long>x(200000);for(int i=0;i<200000;++i)x[i]=1000000LL*i;assert(maximum_gathered_points(x,0)==1);assert(maximum_gathered_points(x,LLONG_MAX)==200000);
''',
'dp-sliding-min':r'''
 auto brute=[](const vector<long long>&a,int lo,int hi){long long answer=LLONG_MIN;for(int l=0;l<int(a.size());++l){long long sum=0;for(int r=l;r<int(a.size());++r){sum+=a[r];if(r-l+1>=lo&&r-l+1<=hi)answer=max(answer,sum);}}return answer;};
 assert(maximum_sum_with_length_bounds({-5,-3,-8},1,3)==-3);assert(maximum_sum_with_length_bounds({-1,3,-2,5,3,-5,2,2},1,2)==8);
 for(int trial=0;trial<1200;++trial){int n=1+rng()%25;vector<long long>a(n);for(auto&x:a)x=int(rng()%21)-10;int lo=1+rng()%n,hi=1+rng()%n;if(lo>hi)swap(lo,hi);assert(maximum_sum_with_length_bounds(a,lo,hi)==brute(a,lo,hi));}
''',
'dsu-threshold-queries':r'''
 for(int trial=0;trial<1000;++trial){int n=1+rng()%20;vector<WeightedEdge>edges;vector<vector<pair<int,long long>>>graph(n);for(int u=0;u<n;++u)for(int v=u+1;v<n;++v)if(rng()%5==0){long long w=int(rng()%9)-4;edges.push_back({u,v,w});graph[u].push_back({v,w});graph[v].push_back({u,w});}vector<ComponentThresholdQuery>queries;for(int q=0;q<50;++q)queries.push_back({int(rng()%n),int(rng()%11)-5});auto answers=threshold_component_sizes(n,edges,queries);for(int i=0;i<int(queries.size());++i){vector<bool>seen(n);vector<int>queue{queries[i].vertex};seen[queue[0]]=true;for(size_t k=0;k<queue.size();++k)for(auto[u,w]:graph[queue[k]])if(w>=queries[i].limit&&!seen[u]){seen[u]=true;queue.push_back(u);}assert(answers[i]==int(queue.size()));}}
 assert(threshold_component_sizes(2,{{0,1,5}},{{0,5},{0,6}})==vector<int>({2,1}));
'''
}
with tempfile.TemporaryDirectory(prefix='flowchartcp-olympiad-property-') as tmp:
 for id,body in checks.items():
  text=(ROOT/'src/content/docs/techniques'/f'{id}.mdx').read_text()
  code=re.findall(r'```cpp\n(.*?)\n```',text,re.S)[0]
  source=Path(tmp)/(id+'.cpp');binary=Path(tmp)/id
  source.write_text('#include <bits/stdc++.h>\nusing namespace std;\n'+code+'\nint main(){std::mt19937 rng(89101112);\n'+body+'\n}\n')
  result=subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
  if result.returncode:raise RuntimeError(result.stderr)
  subprocess.run([str(binary)],check=True,timeout=45)
  print(id+' PASS',flush=True)
