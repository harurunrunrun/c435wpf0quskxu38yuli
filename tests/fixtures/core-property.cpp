// All tested routines are extracted from the published articles by the test runner.
int main() {
    std::mt19937 rng(20261014);
    for (int n = 0; n <= 25; ++n) for (int trial = 0; trial < 30; ++trial) {
        std::vector<long long> a(n);
        for (auto& x : a) x = int(rng()%31)-15;
        t0::PrefixSum prefix(a);
        t1::DifferenceArray differences(n);
        t5::Fenwick fenwick(n);
        auto sum = [](long long x, long long y) { return x+y; };
        t6::SegmentTree<long long,decltype(sum)> tree(a,0,sum);
        for (int i = 0; i < n; ++i) fenwick.add(i,a[i]);
        for (int l = 0; l <= n; ++l) for (int r = l; r <= n; ++r) {
            long long expected = std::accumulate(a.begin()+l,a.begin()+r,0LL);
            assert(prefix.sum(l,r) == expected);
            assert(fenwick.sum(l,r) == expected);
            assert(tree.prod(l,r) == expected);
        }
        std::vector<long long> increments(n);
        for (int update = 0; update < 50; ++update) {
            int l = rng()%(n+1), r = rng()%(n+1);
            if (l > r) std::swap(l,r);
            long long value = int(rng()%21)-10;
            differences.add(l,r,value);
            for (int i = l; i < r; ++i) increments[i] += value;
            assert(differences.materialize() == increments);
            assert(differences.materialize() == increments); // materialization is non-mutating
            if (n) {
                int position = rng()%n;
                long long replacement = int(rng()%31)-15;
                fenwick.add(position,replacement-a[position]);
                tree.set(position,replacement);
                a[position] = replacement;
            }
            long long expected = std::accumulate(a.begin()+l,a.begin()+r,0LL);
            assert(fenwick.sum(l,r) == expected && tree.prod(l,r) == expected);
        }
        auto concat = [](const std::string& a, const std::string& b) { return a+b; };
        std::vector<std::string> strings(n);
        for (auto& word : strings) word = std::string(1,char('a'+rng()%26));
        t6::SegmentTree<std::string,decltype(concat)> words(strings,"",concat);
        for (int l = 0; l <= n; ++l) for (int r = l; r <= n; ++r) {
            std::string expected;
            for (int i = l; i < r; ++i) expected += strings[i];
            assert(words.prod(l,r) == expected); // catches reversal in a noncommutative monoid
        }
    }
    for (long long lo = -10; lo <= 10; ++lo) for (long long hi = lo; hi <= 11; ++hi)
        for (long long boundary = lo-1; boundary <= hi+1; ++boundary) {
            long long expected = lo;
            while (expected < hi && expected < boundary) ++expected;
            assert(t2::first_true(lo,hi,[&](long long x) { return x >= boundary; }) == expected);
        }
    for (long long boundary : {LLONG_MIN, -1LL, 0LL, 1LL, LLONG_MAX})
        assert(t2::first_true(LLONG_MIN,LLONG_MAX,[&](long long x) { return x >= boundary; }) == boundary);
    assert(t2::first_true(LLONG_MIN,LLONG_MAX,[](long long) { return false; }) == LLONG_MAX);
    for (int n = 1; n <= 9; ++n) for (int trial = 0; trial < 80; ++trial) {
        constexpr long long INF = 1LL<<60;
        std::vector<std::vector<std::pair<int,int>>> binaryGraph(n);
        std::vector<std::vector<std::pair<int,long long>>> graph(n);
        std::vector<std::vector<long long>> expected(n,std::vector<long long>(n,INF));
        std::vector<std::vector<long long>> expected01 = expected;
        for (int i = 0; i < n; ++i) expected[i][i] = expected01[i][i] = 0;
        for (int i = 0; i < n; ++i) for (int j = 0; j < n; ++j) if (rng()%4 == 0) {
            int bit = rng()%2;
            long long weight = rng()%20;
            binaryGraph[i].push_back({j,bit}); graph[i].push_back({j,weight});
            expected[i][j] = std::min(expected[i][j],weight);
            expected01[i][j] = std::min(expected01[i][j],static_cast<long long>(bit));
            // Repeated edges exercise stale queue entries.
            if (rng()%3 == 0) { graph[i].push_back({j,weight+1}); binaryGraph[i].push_back({j,1}); }
        }
        for (int k = 0; k < n; ++k) for (int i = 0; i < n; ++i) for (int j = 0; j < n; ++j) {
            expected[i][j] = std::min(expected[i][j],expected[i][k]+expected[k][j]);
            expected01[i][j] = std::min(expected01[i][j],expected01[i][k]+expected01[k][j]);
        }
        for (int s = 0; s < n; ++s) {
            assert(t4::dijkstra(graph,s) == expected[s]);
            auto actual01 = t3::zero_one_bfs(binaryGraph,s);
            for (int v = 0; v < n; ++v)
                assert(actual01[v] == (expected01[s][v] == INF ? 1<<30 : expected01[s][v]));
        }
    }
    // A vertex discovered at cost 1 must still be improved later through zero-cost edges.
    assert(t3::zero_one_bfs({{{1,1},{2,0}}, {}, {{1,0}}},0)[1] == 0);
    // A large candidate must not overflow even though a valid, shorter distance exists.
    assert(t4::dijkstra({{{1,LLONG_MAX},{1,2}},{}},0) == std::vector<long long>({0,2}));
    std::cout << "core properties verified\n";
}
