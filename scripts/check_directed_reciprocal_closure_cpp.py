#!/usr/bin/env python3
"""Extract the actual article's first C++ block and compare with a rule oracle.

Usage: python3 check_directed_reciprocal_closure_cpp.py [article.mdx] [--sanitize]
The article may be a sibling file or site/src/content/docs/techniques/<id>.mdx.
No network, project dependencies, generated fixture, or fixed cwd is required.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import subprocess
import tempfile

SLUG = "directed-reciprocal-closure-dsu-small-to-large"
HERE = Path(__file__).resolve().parent
DEFAULT = HERE / f"{SLUG}.mdx"
if not DEFAULT.exists():
    DEFAULT = HERE.parent / "src/content/docs/techniques" / f"{SLUG}.mdx"

TEST = r'''
#include <climits>
#include <cstdlib>
#include <functional>
#include <iostream>
#include <random>
#include <string>
using Edge = std::pair<int,int>;
static long long comparisons = 0, cases = 0;

static void require(bool ok, const std::string& what) {
    if (!ok) throw std::runtime_error(what);
}

// Directly apply x->y, y->z, z->y => x->z, excluding self loops.
// Start from the explicit prefix every time; no DSU or component reasoning.
static long long oracle(int n, const std::vector<Edge>& prefix) {
    std::vector<std::vector<bool>> g(n, std::vector<bool>(n));
    for (auto [x,y] : prefix) g[x][y] = true;
    bool changed = true;
    while (changed) {
        changed = false;
        for (int x = 0; x < n; ++x)
            for (int y = 0; y < n; ++y)
                for (int z = 0; z < n; ++z)
                    if (x != z && g[x][y] && g[y][z] && g[z][y] && !g[x][z]) {
                        g[x][z] = true;
                        changed = true;
                    }
    }
    long long answer = 0;
    for (const auto& row : g) for (bool v : row) answer += v;
    return answer;
}

static void check_case(int n, const std::vector<Edge>& edges) {
    DirectedReciprocalClosure actual(n);
    require(actual.edge_count() == 0, "initial state");
    std::vector<Edge> prefix;
    for (auto [x,y] : edges) {
        prefix.emplace_back(x,y);
        auto got = actual.add_edge(x,y);
        auto expected = oracle(n, prefix);
        if (got != expected) {
            std::cerr << "n=" << n << " prefix:";
            for (auto [a,b] : prefix) std::cerr << ' ' << a << "->" << b;
            std::cerr << " got=" << got << " expected=" << expected << '\n';
            throw std::runtime_error("oracle mismatch");
        }
        require(actual.edge_count() == got, "edge_count accessor");
        ++comparisons;
    }
    ++cases;
}

template<class Exception, class F> static void must_throw(F f) {
    bool caught = false;
    try { f(); } catch (const Exception&) { caught = true; }
    require(caught, "missing expected exception");
}

static void small_tests() {
    // Every ordered distinct-edge sequence, including every subset, n<=3.
    for (int n = 1; n <= 3; ++n) {
        std::vector<Edge> all, prefix;
        for (int x = 0; x < n; ++x) for (int y = 0; y < n; ++y)
            if (x != y) all.emplace_back(x,y);
        std::function<void(unsigned)> visit = [&](unsigned used) {
            check_case(n, prefix);
            for (unsigned i = 0; i < all.size(); ++i) if (!(used >> i & 1U)) {
                prefix.push_back(all[i]); visit(used | (1U << i)); prefix.pop_back();
            }
        };
        visit(0);
    }
    // Every edge subset on 4 vertices in increasing and decreasing edge order.
    std::vector<Edge> all;
    for (int x = 0; x < 4; ++x) for (int y = 0; y < 4; ++y)
        if (x != y) all.emplace_back(x,y);
    for (unsigned mask = 0; mask < (1U << all.size()); ++mask) {
        std::vector<Edge> edges;
        for (unsigned i = 0; i < all.size(); ++i) if (mask >> i & 1U)
            edges.push_back(all[i]);
        check_case(4, edges);
        std::reverse(edges.begin(), edges.end());
        check_case(4, edges);
    }
    // Every distinct-edge order of length <=4 on 4 vertices.
    std::vector<Edge> prefix;
    std::function<void(unsigned)> ordered4 = [&](unsigned used) {
        check_case(4, prefix);
        if (prefix.size() == 4) return;
        for (unsigned i = 0; i < all.size(); ++i) if (!(used >> i & 1U)) {
            prefix.push_back(all[i]); ordered4(used | (1U << i)); prefix.pop_back();
        }
    };
    ordered4(0);
    check_case(3, {{0,1},{1,2},{2,0},{1,0}});
    { DirectedReciprocalClosure g(3);
      require(g.add_edge(0,1)==1 && g.add_edge(1,2)==2 && g.add_edge(2,0)==3,
              "directed triangle is not a reciprocal component"); }
    check_case(4, {{0,1},{1,0},{2,3},{3,2},{0,2},{1,2},{0,3},{0,2},{3,0}});
    { DirectedReciprocalClosure g(4);
      g.add_edge(0,1); g.add_edge(1,0); g.add_edge(2,3); g.add_edge(3,2);
      require(g.add_edge(0,2)==6, "individual source must be retained");
      require(g.add_edge(1,2)==8, "second individual source"); }
    check_case(4, {{0,1},{1,2},{2,1},{0,2},{2,3},{3,2}});
    check_case(6, {{0,1},{1,2},{2,3},{3,4},{4,5},{5,4},{4,3},{3,2},{2,1},{1,0}});
    std::mt19937 rng(0x20200321);
    for (int t = 0; t < 6000; ++t) {
        int n = 2 + int(rng() % 7), m = int(rng() % 61);
        std::vector<Edge> edges;
        for (int i = 0; i < m; ++i) {
            int x = int(rng() % n), y = int(rng() % (n-1));
            if (y >= x) ++y;
            if (t % 3 == 0 && x > y) std::swap(x,y);
            edges.emplace_back(x,y);
        }
        check_case(n, edges);
    }
    for (int n : {0, -1, 100001, INT_MIN, INT_MAX})
        must_throw<std::invalid_argument>([&] { DirectedReciprocalClosure bad(n); });
    DirectedReciprocalClosure g(3);
    require(g.add_edge(0,1)==1, "contract initial edge");
    for (auto [x,y] : std::vector<Edge>{{-1,0},{0,-1},{3,0},{0,3},{INT_MAX,1}})
        must_throw<std::out_of_range>([&] { g.add_edge(x,y); });
    must_throw<std::invalid_argument>([&] { g.add_edge(1,1); });
    require(g.edge_count()==1 && g.add_edge(1,0)==2, "validation preserves state");
    DirectedReciprocalClosure one(1);
    must_throw<std::invalid_argument>([&] { one.add_edge(0,0); });
    require(one.edge_count()==0, "singleton empty graph");
    DirectedReciprocalClosure limit(2);
    for (int i=0; i<299999; ++i) require(limit.add_edge(0,1)==1, "duplicate edge");
    must_throw<std::out_of_range>([&] { limit.add_edge(-1,0); });
    must_throw<std::invalid_argument>([&] { limit.add_edge(0,0); });
    require(limit.add_edge(0,1)==1, "invalid operations do not use update quota");
    must_throw<std::length_error>([&] { limit.add_edge(1,0); });
    require(limit.edge_count()==1, "update limit preserves state");
    std::cout << "{\"suite\":\"independent-prefix-oracle\",\"cases\":" << cases
              << ",\"prefixComparisons\":" << comparisons << ",\"status\":\"passed\"}\n";
}

static void bench(const std::string& mode) {
    const int n = 100000;
    DirectedReciprocalClosure g(n);
    int updates = 0;
    long long last = 0;
    auto add = [&](int x, int y) {
        long long v = g.add_edge(x,y);
        require(v >= last && v <= 1LL*n*(n-1), "large monotonicity/bound");
        last = v; ++updates;
        return v;
    };
    if (mode == "no-mutual") {
        for (int i=0; i<300000; ++i)
            require(add(i%50000, 50000+i/50000)==i+1, "one-way bipartite");
    } else if (mode == "chain") {
        for (int i=0; i<n-1; ++i) require(add(i,i+1)==i+1, "forward chain");
        for (int i=n-2; i>=0; --i) {
            long long s=n-i;
            long long expected=i==0 ? 1LL*n*(n-1) : s*s+i-1;
            require(add(i+1,i)==expected, "chain every-prefix formula");
        }
        while (updates<300000) require(add(0,n-1)==1LL*n*(n-1), "closed duplicate");
    } else if (mode == "cascade") {
        for (int i=1; i<n; ++i) require(add(0,i)==i, "fan edges");
        for (int i=1; i<n-1; ++i) require(add(i,i+1)==n+i-1, "chain fan edges");
        require(add(n-1,0)==1LL*n*(n-1), "single update triggers n-1 merges");
    } else if (mode == "balanced") {
        std::vector<Edge> base;
        std::set<Edge> seen;
        auto append = [&](int x,int y) {
            if (!seen.emplace(x,y).second) return;
            base.emplace_back(x,y);
            require(add(x,y)==static_cast<long long>(base.size()), "balanced initial DAG");
        };
        for (int x=0; x+1<n; ++x) append(x,x+1);
        std::mt19937 rng(0x20200321);
        while (int(base.size())<300000-(n-1)) {
            int x=int(rng()%(n-1)), y=x+1+int(rng()%(n-x-1));
            append(x,y);
        }
        std::set<Edge>().swap(seen);
        // Known interval components after each stage give an independent count.
        for (int s=2; s/2<n; s*=2) {
            for (int begin=0; begin+s/2<n; begin+=s) add(begin+s/2,begin+s/2-1);
            std::set<Edge> distinct_sources;
            for (auto [x,y] : base) if (x/s != y/s) distinct_sources.emplace(x,y/s);
            long long expected=0;
            for (int begin=0; begin<n; begin+=s) {
                long long block=std::min(s,n-begin);
                expected+=block*(block-1);
            }
            for (auto [source,target] : distinct_sources) {
                (void)source;
                expected+=std::min(s,n-target*s);
            }
            require(last==expected, "balanced stage analytical count");
        }
        require(updates==300000 && last==1LL*n*(n-1), "balanced final");
    } else throw std::runtime_error("unknown benchmark");
    std::cout << "{\"suite\":\"" << mode << "\",\"n\":" << n
              << ",\"updates\":" << updates << ",\"answer\":" << last
              << ",\"status\":\"passed\"}\n";
}

int main(int argc, char** argv) {
    try {
        if (argc==1) small_tests();
        else bench(argv[1]);
    } catch (const std::exception& e) {
        std::cerr << e.what() << '\n'; return 1;
    }
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("article", nargs="?", type=Path, default=DEFAULT)
    parser.add_argument("--sanitize", action="store_true")
    args = parser.parse_args()
    compiler = os.environ.get("CXX") or shutil.which("g++") or shutil.which("clang++")
    if not compiler:
        parser.error("A C++20 compiler is required")
    text = args.article.read_text()
    blocks = re.findall(r"```cpp\n(.*?)\n```", text, re.S)
    if len(blocks) != 1:
        raise SystemExit(f"expected one complete C++ block, found {len(blocks)}")
    results = []
    with tempfile.TemporaryDirectory(prefix="joitter-closure-check-") as work:
        directory = Path(work)
        source, binary = directory / "check.cpp", directory / "check"
        source.write_text(blocks[0] + "\n" + TEST)
        flags = ["-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror", "-pedantic"]
        if args.sanitize:
            flags = ["-std=c++20", "-O1", "-g", "-fsanitize=address,undefined", "-fno-omit-frame-pointer"]
        subprocess.run([compiler, *flags, str(source), "-o", str(binary)], check=True, timeout=120)
        modes = [None] if args.sanitize else [None, "no-mutual", "chain", "cascade", "balanced"]
        for mode in modes:
            timing = directory / "time.txt"
            timed = sys.platform.startswith("linux") and Path("/usr/bin/time").is_file()
            command = ["/usr/bin/time", "-f", "%e %M", "-o", str(timing), str(binary)] if timed else [str(binary)]
            if mode:
                command.append(mode)
            environment = None
            if args.sanitize:
                # LeakSanitizer is incompatible with a ptrace-managed runner.
                environment = dict(os.environ, ASAN_OPTIONS="detect_leaks=0")
            started = time.perf_counter()
            process = subprocess.run(command, text=True, capture_output=True,
                                     timeout=180, env=environment)
            if process.returncode:
                raise SystemExit(process.stderr or process.stdout or f"failed with {process.returncode}")
            result = json.loads(process.stdout)
            if timed:
                seconds, kib = timing.read_text().strip().split()
                result.update(elapsedSeconds=float(seconds), peakRssKiB=int(kib))
            else:
                result.update(elapsedSeconds=time.perf_counter()-started, peakRssKiB=None)
            results.append(result)
            print(json.dumps(result), flush=True)
    print(json.dumps({"status": "passed", "article": str(args.article.resolve()),
                      "sanitizers": args.sanitize, "results": results}))


if __name__ == "__main__":
    main()
