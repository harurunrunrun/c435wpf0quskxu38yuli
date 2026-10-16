#!/usr/bin/env python3
"""Compare the actual C++ examples in 18 specific technique articles with brute force."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

SITE = Path(__file__).resolve().parent.parent
FENCE = re.compile(r"^```cpp\s*\n(.*?)^```\s*$", re.M | re.S)

APIS = {
    "two-fenwick-range-add": ["RangeAddSum"],
    "difference-2d-corners": ["RectAdd", "rectangle_additions"],
    "affine-lazy-composition": ["AffineSumTree"],
    "range-chmin-second-maximum": ["ChminSumTree"],
    "subarray-extremum-contribution": ["all_interval_maximum_sum"],
    "subarray-prefix-frequency": ["count_exact_sum"],
    "subarray-prefix-order": ["count_sum_at_least"],
    "sliding-distinct-count": ["window_distinct_counts"],
    "offline-rightmost-occurrence": ["offline_distinct_counts"],
    "reverse-edge-deletion": ["disconnected_pairs_after_deletions"],
    "connectivity-time-intervals": ["DynamicOp", "offline_connected"],
    "reroot-prefix-suffix": ["farthest_with_exclusion"],
    "reroot-directed-edge-state": ["best_rewarded_destination"],
    "tree-path-prefix-lca": ["RootedTree"],
    "subtree-euler-interval": ["SubtreeSums"],
    "virtual-tree-adjacent-lca": ["make_virtual_tree"],
    "centroid-count-cross-subtrees": ["count_pairs_at_distance"],
    "dsu-threshold-queries": ["WeightedEdge", "ThresholdQuery", "threshold_connected"],
}


def article_namespace(technique_id):
    return "article_" + technique_id.replace("-", "_")


def extracted_source():
    """Isolate complete examples so each article keeps its own helper implementations."""
    available = {item["id"] for item in json.loads(
        (SITE / "data/techniques-specific-core.json").read_text(encoding="utf8"))}
    missing = set(APIS) - available
    if missing:
        raise ValueError("Missing specific technique metadata: " + ", ".join(sorted(missing)))
    includes = set()
    examples = []
    bindings = []
    for technique_id, names in APIS.items():
        article = SITE / "src/content/docs/techniques" / (technique_id + ".mdx")
        matches = FENCE.findall(article.read_text(encoding="utf8"))
        if len(matches) != 1:
            raise ValueError(f"{article.name}: expected exactly one complete C++ example")
        source = matches[0]
        # Standard headers belong at global scope; the authored example is otherwise intact.
        for line in re.findall(r"^#include[^\n]*$", source, re.M):
            includes.add(line)
        source = re.sub(r"^#include[^\n]*\n?", "", source, flags=re.M)
        namespace = article_namespace(technique_id)
        examples.append(f"namespace {namespace} {{\n{source}\n}}")
        for name in names:
            bindings.append(f"using {namespace}::{name};")
    bindings.append("using VirtualRootedTree = article_virtual_tree_adjacent_lca::RootedTree;")
    return "\n".join(sorted(includes) + examples + bindings)


TESTS = r'''
#include <random>
#include <set>
#include <queue>
#include <iostream>
int main() {
    std::mt19937 rng(715);
    auto random=[&](int n){return int(rng()%n);};
    for(int trial=0;trial<350;++trial) {
        int n=random(14);
        std::vector<long long> initial(n);
        for(auto& x:initial) x=random(21)-10;
        {
            auto a=initial;RangeAddSum t(n);
            for(int i=0;i<n;++i) t.add(i,i+1,a[i]);
            for(int step=0;step<100;++step) {
                int l=random(n+1),r=random(n+1);if(l>r) std::swap(l,r);
                long long x=random(31)-15;t.add(l,r,x);
                for(int i=l;i<r;++i) a[i]+=x;
                for(int i=0;i<=n;++i) for(int j=i;j<=n;++j) {
                    long long s=0;for(int k=i;k<j;++k) s+=a[k];assert(t.sum(i,j)==s);
                }
            }
        }
        {
            auto a=initial;for(auto& x:a) x=(x+100)%AffineSumTree::MOD;
            AffineSumTree t(a);
            for(int step=0;step<60;++step) {
                int l=random(n+1),r=random(n+1);if(l>r) std::swap(l,r);
                long long m=random(12),b=random(12);t.apply(l,r,m,b);
                for(int i=l;i<r;++i) a[i]=(m*a[i]+b)%AffineSumTree::MOD;
                for(int i=0;i<=n;++i) for(int j=i;j<=n;++j) {
                    long long s=0;for(int k=i;k<j;++k) s=(s+a[k])%AffineSumTree::MOD;
                    assert(t.range_sum(i,j)==s);
                }
            }
        }
        {
            auto a=initial;ChminSumTree t(a);
            for(int step=0;step<60;++step) {
                int l=random(n+1),r=random(n+1);if(l>r) std::swap(l,r);
                long long x=random(21)-15;t.chmin(l,r,x);
                for(int i=l;i<r;++i) a[i]=std::min(a[i],x);
                for(int i=0;i<=n;++i) for(int j=i;j<=n;++j) {
                    long long s=0;for(int k=i;k<j;++k) s+=a[k];assert(t.sum(i,j)==s);
                }
            }
        }
        {
            __int128 sum=0;long long target=random(11)-5,equal=0,greater=0;
            for(int l=0;l<n;++l) {
                long long s=0,m=initial[l];
                for(int r=l;r<n;++r) {
                    s+=initial[r];m=std::max(m,initial[r]);sum+=m;
                    equal+=s==target;greater+=s>=target;
                }
            }
            assert(all_interval_maximum_sum(initial)==sum);
            assert(count_exact_sum(initial,target)==equal);
            assert(count_sum_at_least(initial,target)==greater);
            if(n) {
                int k=1+random(n);auto answer=window_distinct_counts(initial,k);
                for(int l=0;l+k<=n;++l) {
                    std::set<long long> values(initial.begin()+l,initial.begin()+l+k);
                    assert(answer[l]==int(values.size()));
                }
            }
            std::vector<std::pair<int,int>> qs;
            for(int i=0;i<30;++i) {
                int l=random(n+1),r=random(n+1);if(l>r) std::swap(l,r);qs.push_back({l,r});
            }
            auto answer=offline_distinct_counts(initial,qs);
            for(int i=0;i<int(qs.size());++i) {
                auto [l,r]=qs[i];std::set<long long> values(initial.begin()+l,initial.begin()+r);
                assert(answer[i]==int(values.size()));
            }
        }
        {
            int h=random(6),w=random(6);std::vector<RectAdd> updates;
            std::vector brute(h,std::vector<long long>(w));
            for(int i=0;i<20;++i) {
                int y1=random(h+1),y2=random(h+1),x1=random(w+1),x2=random(w+1);
                if(y1>y2) std::swap(y1,y2);
                if(x1>x2) std::swap(x1,x2);
                long long v=random(15)-7;updates.push_back({y1,x1,y2,x2,v});
                for(int y=y1;y<y2;++y) for(int x=x1;x<x2;++x) brute[y][x]+=v;
            }
            assert(rectangle_additions(h,w,updates)==brute);
        }
    }
    for(int trial=0;trial<350;++trial) {
        int n=1+random(16);
        std::vector<std::vector<std::pair<int,long long>>> weighted(n);
        std::vector<std::vector<int>> unweighted(n);
        for(int v=1;v<n;++v) {
            int u=random(v),w=random(6);
            weighted[u].push_back({v,w});weighted[v].push_back({u,w});
            unweighted[u].push_back(v);unweighted[v].push_back(u);
        }
        RootedTree tree(weighted);
        auto maxima=farthest_with_exclusion(weighted);
        std::vector<long long> reward(n);for(auto& x:reward) x=random(20);
        auto expense=best_rewarded_destination(weighted,reward);
        std::vector distance(n,std::vector<long long>(n));
        std::vector edge_count(n,std::vector<int>(n));
        for(int s=0;s<n;++s) {
            std::vector<int> order{s},parent(n,-1);parent[s]=s;
            for(int i=0;i<int(order.size());++i)
                for(auto [u,w]:weighted[order[i]]) if(u!=parent[order[i]]) {
                    parent[u]=order[i];distance[s][u]=distance[s][order[i]]+w;
                    edge_count[s][u]=edge_count[s][order[i]]+1;order.push_back(u);
                }
            assert(maxima[s]==*std::max_element(distance[s].begin(),distance[s].end()));
            long long best=std::numeric_limits<long long>::lowest()/4;
            for(int u=0;u<n;++u) {
                assert(tree.path_sum(s,u)==distance[s][u]);
                if(s!=u) best=std::max(best,distance[s][u]+reward[u]);
            }
            assert(expense[s]==best);
        }
        for(int k=0;k<=n;++k) {
            long long expected=0;
            for(int u=0;u<n;++u) for(int v=u+1;v<n;++v) expected+=edge_count[u][v]==k;
            assert(count_pairs_at_distance(unweighted,k)==expected);
        }
        auto current=reward;SubtreeSums subtree(unweighted,current);
        for(int step=0;step<50;++step) {
            int v=random(n),x=random(15)-7;subtree.add(v,x);current[v]+=x;
            for(int u=0;u<n;++u) {
                long long s=0;for(int w=0;w<n;++w) if(tree.ancestor(u,w)) s+=current[w];
                assert(subtree.sum(u)==s);
            }
        }
        VirtualRootedTree virtual_tree_index(weighted);
        for(int step=0;step<20;++step) {
            std::vector<int> selected;
            for(int u=0;u<n;++u) if(random(3)==0) selected.push_back(u);
            auto virtual_tree=make_virtual_tree(virtual_tree_index,selected);
            std::set<int> expected(selected.begin(),selected.end());
            for(int u:selected) for(int v:selected) expected.insert(tree.lca(u,v));
            assert(std::set<int>(virtual_tree.vertices.begin(),virtual_tree.vertices.end())==expected);
            for(int i=0;i<int(virtual_tree.vertices.size());++i) {
                int v=virtual_tree.vertices[i],parent=-1;
                for(int j=0;j<int(virtual_tree.vertices.size());++j) {
                    int u=virtual_tree.vertices[j];
                    if(u!=v && tree.ancestor(u,v) && (parent<0 || tree.depth[u]>tree.depth[virtual_tree.vertices[parent]])) parent=j;
                }
                assert(virtual_tree.parent[i]==parent);
                if(parent>=0) assert(virtual_tree.edge_length[i]==distance[v][virtual_tree.vertices[parent]]);
            }
        }
    }
    auto connected=[](int n,const std::vector<std::pair<int,int>>& edges,int s,int goal) {
        std::vector<std::vector<int>> g(n);for(auto [u,v]:edges){g[u].push_back(v);g[v].push_back(u);}
        std::vector<bool> seen(n);std::vector<int> order{s};seen[s]=true;
        for(int i=0;i<int(order.size());++i) for(int u:g[order[i]]) if(!seen[u]){seen[u]=true;order.push_back(u);}
        return bool(seen[goal]);
    };
    for(int trial=0;trial<350;++trial) {
        int n=1+random(9);std::vector<std::pair<int,int>> edges;
        for(int u=0;u<n;++u) for(int v=u+1;v<n;++v) if(random(2)) edges.push_back({u,v});
        std::shuffle(edges.begin(),edges.end(),rng);
        auto answer=disconnected_pairs_after_deletions(n,edges);
        for(int i=0;i<int(edges.size());++i) {
            std::vector<std::pair<int,int>> remaining(edges.begin()+i+1,edges.end());long long pairs=0;
            for(int u=0;u<n;++u) for(int v=u+1;v<n;++v) pairs+=!connected(n,remaining,u,v);
            assert(answer[i]==pairs);
        }
        std::vector<DynamicOp> operations;std::set<std::pair<int,int>> active;std::vector<bool> expected;
        for(int step=0;step<90;++step) {
            int u=random(n),v=random(n);if(u>v) std::swap(u,v);
            std::pair<int,int> edge{u,v};
            if(random(3)==0) {
                operations.push_back({2,u,v});
                std::vector<std::pair<int,int>> current(active.begin(),active.end());expected.push_back(connected(n,current,u,v));
            } else if(active.contains(edge)) {operations.push_back({1,u,v});active.erase(edge);}
            else {operations.push_back({0,u,v});active.insert(edge);}
        }
        assert(offline_connected(n,operations)==expected);
        std::vector<WeightedEdge> w_edges;for(auto [u,v]:edges) w_edges.push_back({u,v,random(6)});
        std::vector<ThresholdQuery> qs;
        for(int step=0;step<50;++step) qs.push_back({random(n),random(n),random(8)-1});
        auto ans=threshold_connected(n,w_edges,qs);
        for(int i=0;i<int(qs.size());++i) {
            std::vector<std::pair<int,int>> eligible;
            for(auto e:w_edges) if(e.weight<qs[i].limit) eligible.push_back({e.u,e.v});
            assert(ans[i]==connected(n,eligible,qs[i].u,qs[i].v));
        }
    }
    std::cout<<"All 18 specific scenarios passed randomized brute-force comparisons.\n";
}
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    if not shutil.which(args.compiler):
        parser.error(f"C++20 compiler not found: {args.compiler}")
    with tempfile.TemporaryDirectory(prefix="flowchartcp-specific-cpp-") as directory:
        source = Path(directory) / "comparisons.cpp"
        executable = Path(directory) / "comparisons"
        source.write_text(extracted_source() + "\n" + TESTS, encoding="utf8")
        compile_result = subprocess.run(
            [args.compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
             str(source), "-o", str(executable)],
            capture_output=True, text=True, timeout=120)
        if compile_result.returncode:
            print(compile_result.stderr, file=sys.stderr)
            return compile_result.returncode
        result = subprocess.run([str(executable)], timeout=120)
        return result.returncode


if __name__ == "__main__":
    sys.exit(main())
