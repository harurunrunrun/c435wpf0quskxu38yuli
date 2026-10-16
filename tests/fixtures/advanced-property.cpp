int main() {
    std::mt19937_64 rng(998244353);
    for (int trial = 0; trial < 200; ++trial) {
        t0::MonotoneCHT hull;
        std::vector<std::pair<long long,long long>> lines;
        long long slope = 10000;
        for (int count = 1; count <= 30; ++count) {
            slope -= 1+rng()%50;
            long long intercept = static_cast<long long>(rng()%200000)-100000;
            hull.add(slope,intercept); lines.push_back({slope,intercept});
        }
        for (long long x = -200; x <= 200; ++x) {
            __int128 best = __int128(lines[0].first)*x+lines[0].second;
            for (auto [a,b] : lines) best = std::min(best,__int128(a)*x+b);
            assert(hull.get(x) == best);
        }
    }
    // Online insertions and queries obey both monotonicity conditions.
    for (int trial = 0; trial < 100; ++trial) {
        t0::MonotoneCHT hull;
        std::vector<std::pair<long long,long long>> lines;
        long long slope = 1000, x = -1000;
        for (int step = 0; step < 100; ++step) {
            slope -= 1+rng()%30;
            long long intercept = static_cast<long long>(rng()%100000)-50000;
            hull.add(slope,intercept); lines.push_back({slope,intercept});
            x += rng()%20;
            __int128 best = __int128(lines[0].first)*x+lines[0].second;
            for (auto [a,b] : lines) best = std::min(best,__int128(a)*x+b);
            assert(hull.get(x) == best);
        }
    }
    // Cross-products and queried values exceed 64-bit even though coefficients fit.
    t0::MonotoneCHT wide;
    std::vector<std::pair<long long,long long>> bigLines = {
        {4000000000LL,800000000000000000LL},
        {0LL,-800000000000000000LL},
        {-4000000000LL,800000000000000000LL}
    };
    for (auto [a,b] : bigLines) wide.add(a,b);
    for (long long x : {-10000000000LL,-1LL,0LL,1LL,10000000000LL}) {
        __int128 best = __int128(bigLines[0].first)*x+bigLines[0].second;
        for (auto [a,b] : bigLines) best = std::min(best,__int128(a)*x+b);
        assert(wide.get(x) == best);
    }
    for (int n = 0; n <= 12; ++n) for (int trial = 0; trial < 30; ++trial) {
        t1::XorBasis basis;
        std::vector<uint64_t> values(n);
        for (auto& value : values) { value = rng()%1024; basis.add(value); }
        uint64_t seed = rng()%2048, optimum = seed;
        for (int mask = 0; mask < (1<<n); ++mask) {
            uint64_t value = seed;
            for (int i = 0; i < n; ++i) if ((mask>>i)&1) value ^= values[i];
            optimum = std::max(optimum,value);
        }
        assert(basis.maximum(seed) == optimum);
    }
    t1::XorBasis high;
    high.add(uint64_t(1)<<63); high.add(1); high.add(1);
    assert(high.maximum(0) == ((uint64_t(1)<<63)|1));
    for (int rows = 1; rows <= 35; ++rows) for (int columns = 1; columns <= 35; ++columns) {
        auto cost = [](int r,int c) { return 1LL*(r-c)*(r-c)+c; };
        auto best = t2::smawk(rows,columns,cost);
        assert(best.size() == static_cast<size_t>(rows));
        for (int r = 0; r < rows; ++r) {
            long long optimum = cost(r,0);
            for (int c = 0; c < columns; ++c) optimum = std::min(optimum,cost(r,c));
            assert(0 <= best[r] && best[r] < columns);
            assert(cost(r,best[r]) == optimum);
        }
        auto tie = [](int,int) { return 0LL; };
        auto tied = t2::smawk(rows,columns,tie);
        for (int column : tied) assert(0 <= column && column < columns);
    }
    for (int n = 2; n <= 8; ++n) for (int trial = 0; trial < 80; ++trial) {
        t3::Dinic graph(n);
        std::vector<std::tuple<int,int,long long>> edges;
        for (int i = 0; i < n; ++i) for (int j = 0; j < n; ++j) if (i != j && rng()%5 == 0) {
            long long capacity = rng()%8;
            graph.add(i,j,capacity); edges.emplace_back(i,j,capacity);
            if (rng()%3 == 0) { graph.add(i,j,1); edges.emplace_back(i,j,1); }
        }
        long long minCut = LLONG_MAX;
        for (int mask = 0; mask < (1<<(n-2)); ++mask) {
            std::vector<bool> sourceSide(n); sourceSide[0] = true;
            for (int i = 1; i < n-1; ++i) sourceSide[i] = (mask>>(i-1))&1;
            long long cut = 0;
            for (auto [u,v,cap] : edges) if (sourceSide[u] && !sourceSide[v]) cut += cap;
            minCut = std::min(minCut,cut);
        }
        long long limit = rng()%12;
        assert(graph.flow(0,n-1,limit) == std::min(minCut,limit));
        assert(graph.flow(0,n-1) == minCut-std::min(minCut,limit));
    }
    for (int trial = 0; trial < 250; ++trial) {
        // An acyclic graph allows negative costs while guaranteeing no negative cycle.
        constexpr int n = 4;
        std::vector<std::tuple<int,int,long long,long long>> edges;
        t4::MinCostFlow graph(n);
        for (int i = 0; i < n; ++i) for (int j = i+1; j < n; ++j) if (rng()%4 != 0) {
            long long capacity = rng()%3, cost = static_cast<long long>(rng()%11)-5;
            graph.add(i,j,capacity,cost); edges.emplace_back(i,j,capacity,cost);
        }
        int want = rng()%7;
        long long bestFlow = -1, bestCost = LLONG_MAX;
        auto enumerate = [&](auto&& self,int index,std::vector<long long>& balance,long long cost) -> void {
            if (index == static_cast<int>(edges.size())) {
                for (int i = 1; i < n-1; ++i) if (balance[i] != 0) return;
                long long sent = -balance[0];
                if (sent < 0 || sent > want || balance[n-1] != sent) return;
                if (sent > bestFlow || (sent == bestFlow && cost < bestCost)) { bestFlow = sent; bestCost = cost; }
                return;
            }
            auto [u,v,cap,price] = edges[index];
            for (long long sent = 0; sent <= cap; ++sent) {
                balance[u] -= sent; balance[v] += sent;
                self(self,index+1,balance,cost+sent*price);
                balance[u] += sent; balance[v] -= sent;
            }
        };
        std::vector<long long> balance(n);
        enumerate(enumerate,0,balance,0);
        auto actual = graph.flow(0,n-1,want);
        assert(actual.first == bestFlow && actual.second == bestCost);
    }
    constexpr long long MOD = 998244353;
    auto naiveConvolution = [](const std::vector<int>& a,const std::vector<int>& b) {
        if (a.empty() || b.empty()) return std::vector<int>{};
        std::vector<int> answer(a.size()+b.size()-1);
        for (size_t i = 0; i < a.size(); ++i) for (size_t j = 0; j < b.size(); ++j) {
            long long x = (static_cast<long long>(a[i])%MOD+MOD)%MOD;
            long long y = (static_cast<long long>(b[j])%MOD+MOD)%MOD;
            answer[i+j] = (answer[i+j]+x*y)%MOD;
        }
        return answer;
    };
    for (int n = 0; n <= 24; ++n) for (int m = 0; m <= 24; ++m) {
        std::vector<int> a(n),b(m);
        for (auto& x : a) x = static_cast<int>(static_cast<long long>(rng()%4000000000ULL)-2000000000LL);
        for (auto& x : b) x = static_cast<int>(static_cast<long long>(rng()%4000000000ULL)-2000000000LL);
        assert(t5::ntt998::convolution(a,b) == naiveConvolution(a,b));
    }
    assert(t5::ntt998::convolution({INT_MIN,INT_MAX,-1},{-1,0,INT_MAX}) == naiveConvolution({INT_MIN,INT_MAX,-1},{-1,0,INT_MAX}));
    for (int n = 1; n <= 40; ++n) for (int trial = 0; trial < 10; ++trial) {
        std::vector<int> a(1+rng()%8);
        for (auto& x : a) x = rng()%MOD;
        if (!a[0]) a[0] = 1;
        auto inverse = t6::fps_inverse(a,n,naiveConvolution);
        assert(inverse.size() == static_cast<size_t>(n));
        auto product = naiveConvolution(a,inverse);
        assert(product[0] == 1);
        for (int i = 1; i < n; ++i) assert(product[i] == 0);
    }
    for (int k = 1; k <= 8; ++k) for (int trial = 0; trial < 25; ++trial) {
        std::vector<long long> initial(k),coefficients(k),sequence;
        for (auto& x : initial) x = rng()%MOD;
        for (auto& x : coefficients) x = rng()%MOD;
        sequence = initial;
        while (sequence.size() <= 60) {
            long long next = 0;
            for (int j = 0; j < k; ++j) next = (next+coefficients[j]*sequence[sequence.size()-1-j])%MOD;
            sequence.push_back(next);
        }
        for (int n = 0; n <= 60; ++n) assert(t7::linear_recurrence(initial,coefficients,n) == sequence[n]);
    }
    uint64_t exponent = 1000000000000000000ULL;
    long long power = 1, factor = 7;
    for (uint64_t e = exponent; e; e >>= 1) { if (e&1) power = power*factor%MOD; factor = factor*factor%MOD; }
    assert(t7::linear_recurrence({3},{7},exponent) == 3*power%MOD);
    std::cout << "advanced properties verified\n";
}
