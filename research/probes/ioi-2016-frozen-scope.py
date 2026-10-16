from pathlib import Path
import hashlib,json,re,subprocess,tempfile
from ioi_2016_snapshot import snapshot_baseline
_snapshot_holder,BASE=snapshot_baseline()
SLUGS=['two-pointers','knapsack-bitset-shift','knapsack','euler-degree-connectivity','graph-reduction','binary-search','manhattan-transform','tree-eccentricity-diameter-endpoints','state-design','interactive','interactive-bit-group-testing','aliens-trick','dp-exact-count-penalty','convex-hull-trick','dp-affine-transition','li-chao-tree','union-find','lcs-hirschberg-reconstruction','dp-monotone-split']
TESTS=[
 'require(t0::count_sum_at_most({6,8,8,7},17)==7,"contiguous interval COUNT, not arbitrary subset witness");',
 'auto bits=t1::subset_sum_bits({6,8,8,7},17);require((bits[0]>>15&1)&&!(bits[0]>>17&1),"sum bits, no selected original indices");',
 'auto kd=t2::knapsack_exact({{6,1},{8,1},{8,1},{7,1}},17);require(kd[15]==2,"capacity-indexed max values, no witness");',
 'require(!t3::directed_euler_path(2,{{0,1},{0,1},{1,0}},0,0),"railroad2 equal increasing sections require paid augmentation before Euler");',
 'auto hubs=t4::group_hubs(2,{{0,1}});require(hubs.size()==3&&hubs[0][0]==std::pair{2,0},"group movement graph, no speed-order augmentation");',
 'require(t5::first_true(0,201,[](long long k){return k>=100;})==100,"binary search requires external proven shortcut feasibility");',
 'require(t6::maximum_manhattan_distance({{0,0},{100,0},{200,0}})==200,"fixed point diameter200, legal shortcut reduces railway diameter to100");',
 'auto ecc=t7::tree_eccentricities(3,{{0,1,100},{1,2,100}});require(*max_element(ecc.begin(),ecc.end())==200,"fixed tree only; added shortcut creates cycle and reduces diameter to100");',
 'auto parity=t8::parity_bfs({{1},{}},{false,false},0);require(parity[1][0]==1,"parity BFS does not represent run-length puzzle completions");',
 'static_assert(std::is_same_v<decltype(&t9::ask_interval),int(*)(int,int,int&,int)>);require(true,"compile-only protocol; MUST NOT invoke stdin/stdout in original messy callback");',
 'auto groups=t10::binary_test_groups(4);require(groups.size()==2&&t10::decode_binary_test(4,"11")==3,"one hidden item, not whole bit permutation; API cap100 below source128");',
 '''auto penalty=[](long long lambda){t11::Penalized best{t11::i128(1)<<100,0};for(int q=1;q<=3;++q){t11::Penalized v{t11::i128(std::array{9,5,3}[q-1])+t11::i128(lambda)*q,q};if(t11::better(v,best))best=v;}return best;};require(t11::exact_count(2,-10,10,penalty)==5,"generic wrapper only; photo DP/convexity/count bounds are caller obligations");''',
 'require(t12::nonadjacent_exact_cost({1,100,1},2)==2,"nonadjacent POSITION selection, not square area union partition");',
 't13::MonotoneCHT hull;hull.add(3,0);hull.add(2,-1);hull.add(1,0);require(hull.get(0)==-1&&hull.get(5)==5,"scalar min lines; no photo count tie metadata or overlap formula");',
 'auto affine=t14::affine_transition_dp({0,1,2},{3,2,1});require(affine[1]==3&&affine[2]==6,"fixed scalar affine recurrence; no geometric preprocessing/photo penalty");',
 't15::LiChao lichao({-1,0,1});lichao.add(1,0);lichao.add(-1,0);require(lichao.get(1)&&*lichao.get(1)==-1,"scalar line query; generality does not create photo count API");',
 't16::DSU dsu(3);require(dsu.merge(0,1)&&!dsu.merge(1,0)&&dsu.size(0)==2,"merge primitive, no cut balance/MST cost derivation");',
 'require(t17::lcs_hirschberg(std::string("ABBA"),std::string("BABA")).size()==3,"returns ONE LCS, not colors common to ALL run-length completions");',
 'require(t18::squared_partition_cost({1,1,1},2)==5,"sum-of-weights squared partitions, lacks photo overlap correction and full unrestrictedK scaling");'
]
records=[];parts=['#include <bits/stdc++.h>\nusing namespace std;']
for i,slug in enumerate(SLUGS):
    p=BASE/'src/content/docs/techniques'/f'{slug}.mdx';text=p.read_text();fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',text,re.M|re.S);assert len(fences)==1,slug
    records.append({'techniqueId':slug,'file':str(p.relative_to(BASE)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'cppFenceSha256':hashlib.sha256(fences[0].encode()).hexdigest(),'fullArticleAndAllCodeRead':True,'originalFullRangeApiReusable':False,'nativeCheckKind':'compile-only protocol signature; no IO performed' if slug=='interactive' else 'actual frozen fence component scope check; not a full-source solver','fullImplementationRevalidatedForOriginal':False})
    parts.append(f'namespace t{i} {{\n'+fences[0]+'\n}')
parts.append('int checks=0;void require(bool b,const char*msg){++checks;if(!b){std::cerr<<msg;std::exit(1);}}\nint main(){\n'+'\n'.join(TESTS)+'\nstd::cout<<checks<<"\\n";\n}')
source='\n'.join(parts)
with tempfile.TemporaryDirectory(prefix='flowchartcp-ioi2016-scope-') as temp:
    sourcepath=Path(temp)/'check.cpp';sourcepath.write_text(source);binary=Path(temp)/'check';subprocess.run(['g++','-std=c++20','-O2',str(sourcepath),'-o',str(binary)],check=True,timeout=120);run=subprocess.run([str(binary)],capture_output=True,text=True,check=True,timeout=30)
    assert int(run.stdout)==19
output={'actualFrozenFencesCompiled':len(SLUGS),'componentScopeChecks':int(run.stdout),'allAreCompletedSourceApis':False,'unmodifiedOriginalFences':True,'cppHarnessSha256':hashlib.sha256(source.encode()).hexdigest(),'records':records}
print(json.dumps(output,ensure_ascii=False,indent=2))
