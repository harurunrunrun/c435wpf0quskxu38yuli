#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <cstdint>
#include <iostream>

int main() {
    // Independent counterexample search: Gray code visits every 5x5 subset.
    // Only four local occupancy counts change per step. The oracle uses the
    // literal bounding box area and cardinality, with no corner argument.
    std::array<unsigned, 5> rows{};
    int adjacent[6][6]{};
    int potential = 0, cardinality = 0;
    std::uint64_t rectangles = 0, checksum = 0;
    for (unsigned step = 1; step < (1U << 25); ++step) {
        unsigned bit = std::countr_zero(step), r = bit / 5, c = bit % 5;
        int delta = ((rows[r] >> c) & 1U) ? -1 : 1;
        rows[r] ^= 1U << c;
        cardinality += delta;
        for (unsigned i : {r, r + 1}) for (unsigned j : {c, c + 1}) {
            int& count = adjacent[i][j];
            potential -= count & 1;
            count += delta;
            assert(0 <= count && count <= 4);
            potential += count & 1;
        }
        int top = 5, bottom = -1;
        unsigned columns = 0;
        for (int i = 0; i < 5; ++i) if (rows[i]) {
            top = std::min(top, i); bottom = std::max(bottom, i);
            columns |= rows[i];
        }
        assert(columns && cardinality > 0 && potential >= 4);
        int left = std::countr_zero(columns), right = std::bit_width(columns) - 1;
        bool literal_rectangle = (bottom - top + 1) * (right - left + 1) == cardinality;
        assert((potential == 4) == literal_rectangle);
        rectangles += literal_rectangle;
        checksum = checksum * 1000003 + std::uint64_t(31 * potential + cardinality);
    }
    assert(rectangles == 225);
    // Includes repeated sentinels and even impossible repeated interior labels;
    // the interval parity identity is valid for all nondecreasing quadruples.
    std::uint64_t interval_checks = 0;
    for (int n = 1; n <= 12; ++n)
        for (int a = 0; a <= n; ++a) for (int b = 0; b <= n; ++b)
            for (int c = 0; c <= n; ++c) for (int d = 0; d <= n; ++d) {
                std::array<int, 4> q{a, b, c, d}, sorted = q;
                std::sort(sorted.begin(), sorted.end());
                for (int t = 0; t < n; ++t) {
                    int count = 0;
                    for (int value : q) count += value <= t;
                    int ranges = (sorted[0] <= t && t < sorted[1])
                               + (sorted[2] <= t && t < sorted[3]);
                    assert(ranges == (count & 1));
                    ++interval_checks;
                }
            }
    std::cout << "{\"allNonempty5x5Subsets\":33554431,\"literalRectangles\":" << rectangles
              << ",\"prefixIntervalChecks\":" << interval_checks
              << ",\"counterexamples\":0,\"checksum\":" << checksum << "}\n";
}
