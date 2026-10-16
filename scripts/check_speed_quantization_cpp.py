#!/usr/bin/env python3
"""Compare the actual MDX examples with generated roots and representative sets."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile


SITE = Path(__file__).resolve().parent.parent
ARTICLES = (
    "positive-denominator-offset-real-bisection",
    "weighted-squared-quantization-interval-dp",
)
FENCE = re.compile(r"^```cpp\s*\n(.*?)^```\s*$", re.M | re.S)


def extracted_source():
    includes = set()
    examples = []
    for slug in ARTICLES:
        article = SITE / "src/content/docs/techniques" / (slug + ".mdx")
        matches = FENCE.findall(article.read_text(encoding="utf8"))
        if len(matches) != 1:
            raise ValueError(f"{article.name}: expected one complete C++ fence")
        source = matches[0]
        includes.update(re.findall(r"^#include[^\n]*$", source, re.M))
        source = re.sub(r"^#include[^\n]*\n?", "", source, flags=re.M)
        namespace = "article_" + slug.replace("-", "_")
        examples.append(f"namespace {namespace} {{\n{source}\n}}")
    return "\n".join(sorted(includes) + examples)


TESTS = r'''
#include <cassert>
#include <iostream>
#include <random>
#include <string>
using namespace std;
using article_positive_denominator_offset_real_bisection::positive_denominator_offset;
using article_weighted_squared_quantization_interval_dp::minimum_weighted_squared_error;

template<class Function> void rejects(Function function) {
    bool rejected = false;
    try { function(); }
    catch (const invalid_argument&) { rejected = true; }
    assert(rejected);
}

using Segment = pair<long double, long double>;
int speed_checks = 0;

void compare_root(const vector<Segment>& segments, long double time,
                  long double expected) {
    long double actual = positive_denominator_offset(segments, time);
    assert(isfinite(actual));
    // Substantially tighter than the article's 1e-6 absolute/relative target.
    assert(abs(actual - expected) <= 2e-12L * max(1.0L, abs(expected)));
    for (auto [distance, reading] : segments) {
        (void)distance;
        assert(reading + actual > 0);
    }
    ++speed_checks;
}

void check_speed() {
    // The oracle here is the closed form of a single term, without bisection.
    for (long double reading : {-1000.0L, -5.75L, 0.0L, 7.125L, 1000.0L}) {
        for (long double distance : {1.0L, 1.125L, 1000.0L}) {
            for (long double time : {1.0L, 1.5L, 999999.5L, 1000000.0L}) {
                compare_root({{distance, reading}}, time, distance / time - reading);
            }
        }
    }
    // The exact maximum correction exceeds the tempting 1e6 cap.
    compare_root(vector<Segment>(1000, {1000, -1000}), 1, 1001000);
    compare_root(vector<Segment>(1000, {1000, 1000}), 1000000, -999);
    compare_root({{1, 5}, {2, 10}}, 1 + 2.0L / 6, -4);
}

void check_generated_speed() {
    mt19937_64 random(20170525);
    int accepted = 0;
    for (int trial = 0; trial < 25000 && accepted < 5000; ++trial) {
        int count = 1 + int(random() % 30);
        vector<Segment> segments;
        long double minimum = 1000;
        for (int i = 0; i < count; ++i) {
            long double reading = static_cast<long double>(int(random() % 32001) - 16000) / 16;
            long double distance = static_cast<long double>(16 + random() % 15985) / 16;
            segments.push_back({distance, reading});
            minimum = min(minimum, reading);
        }
        long double gap = pow(10.0L, static_cast<long double>(int(random() % 12001) - 6000) / 1000);
        long double correction = gap - minimum;
        // Construct the time from a known correction with the original formula.
        // This oracle neither brackets nor searches for the answer.
        long double time = 0;
        for (auto [distance, reading] : segments) time += distance / (reading + correction);
        if (time < 1 || time > 1000000) continue;
        compare_root(segments, time, correction);
        ++accepted;
    }
    assert(accepted == 5000);
    // Different readings separated by a very small real gap, close to a pole.
    vector<Segment> close = {{1, 1000}, {1, 999.999999L}};
    long double correction = -999.999996L;
    long double time = 0;
    for (auto [distance, reading] : close) time += distance / (reading + correction);
    assert(time >= 1 && time <= 1000000);
    compare_root(close, time, correction);
}

void check_speed_contract() {
    const long double nan = numeric_limits<long double>::quiet_NaN();
    const long double inf = numeric_limits<long double>::infinity();
    rejects([] { positive_denominator_offset({}, 1); });
    rejects([] { positive_denominator_offset(vector<Segment>(1001, {1, 0}), 1); });
    for (long double time : {0.0L, -1.0L, 1000001.0L, nan, inf, -inf}) {
        rejects([&] { positive_denominator_offset({{1, 0}}, time); });
    }
    for (long double distance : {0.0L, -1.0L, 1000.5L, nan, inf, -inf}) {
        rejects([&] { positive_denominator_offset({{distance, 0}}, 1); });
    }
    for (long double reading : {-1000.5L, 1000.5L, nan, inf, -inf}) {
        rejects([&] { positive_denominator_offset({{1, reading}}, 1); });
    }
}

// Enumerate complete representative sets and assign each value directly to its
// nearest chosen representative. No intervals, moments, means or DP are used.
// Values outside the input's enclosing integer range can be clipped into it
// without increasing any distance, so the small-domain enumeration is complete.
long long direct_small(const vector<long long>& frequency, int maximum) {
    const int values = static_cast<int>(frequency.size());
    if (all_of(frequency.begin(), frequency.end(), [](long long w) { return w == 0; })) return 0;
    long long best = numeric_limits<long long>::max();
    for (int subset = 1; subset < (1 << values); ++subset) {
        if (__builtin_popcount(static_cast<unsigned>(subset)) > maximum) continue;
        long long error = 0;
        for (int x = 0; x < values; ++x) {
            int nearest = 1000000;
            for (int representative = 0; representative < values; ++representative) {
                if ((subset >> representative) & 1) {
                    nearest = min(nearest, (x - representative) * (x - representative));
                }
            }
            error += frequency[x] * nearest;
        }
        best = min(best, error);
    }
    return best;
}

long long direct_one(const vector<long long>& frequency) {
    long long best = numeric_limits<long long>::max();
    for (int representative = 0; representative < 256; ++representative) {
        long long error = 0;
        for (int x = 0; x < static_cast<int>(frequency.size()); ++x) {
            error += frequency[x] * (x - representative) * (x - representative);
        }
        best = min(best, error);
    }
    return best;
}

long long direct_two(const vector<long long>& frequency) {
    long long best = direct_one(frequency);
    for (int first = 0; first < 256; ++first) {
        for (int second = first + 1; second < 256; ++second) {
            long long error = 0;
            for (int x = 0; x < static_cast<int>(frequency.size()); ++x) {
                error += frequency[x] * min((x - first) * (x - first),
                                             (x - second) * (x - second));
            }
            best = min(best, error);
        }
    }
    return best;
}

int quantization_checks = 0;
void compare_small(const vector<long long>& frequency, int maximum) {
    assert(minimum_weighted_squared_error(frequency, maximum) == direct_small(frequency, maximum));
    ++quantization_checks;
}

void check_quantization() {
    // Exhaust every frequency vector over {0,1,2} for domains of size 0..6.
    for (int values = 0, powers = 1; values <= 6; ++values, powers *= 3) {
        for (int encoded = 0; encoded < powers; ++encoded) {
            int remaining = encoded;
            vector<long long> frequency(values);
            for (long long& count : frequency) { count = remaining % 3; remaining /= 3; }
            for (int maximum = 1; maximum <= max(1, values); ++maximum) {
                compare_small(frequency, maximum);
            }
        }
    }
    mt19937 random(20170601);
    for (int trial = 0; trial < 400; ++trial) {
        int values = 1 + int(random() % 8);
        vector<long long> frequency(values);
        for (long long& count : frequency) count = random() % 21;
        compare_small(frequency, 1 + int(random() % values));
    }
    // Empty data, holes, representatives absent from the input and tied rounding.
    assert(minimum_weighted_squared_error({}, 0) == 0);
    assert(minimum_weighted_squared_error({}, 256) == 0);
    assert(minimum_weighted_squared_error(vector<long long>(256), 0) == 0);
    assert(minimum_weighted_squared_error({1, 1}, 1) == 1);
    assert(minimum_weighted_squared_error({2, 1}, 1) == 1);
    assert(minimum_weighted_squared_error({1, 2}, 1) == 1);
    assert(minimum_weighted_squared_error({1, 0, 1}, 1) == 2);
    assert(minimum_weighted_squared_error({0, 1, 0}, 1) == 0);
    assert(minimum_weighted_squared_error({0, 4, 0, 0, 7, 0}, 256) == 0);

    const long long limit = 1LL << 26;
    vector<long long> only_last(256);
    only_last[255] = limit;
    assert(minimum_weighted_squared_error(only_last, 1) == 0);
    vector<long long> endpoints(256);
    endpoints[0] = endpoints[255] = limit;
    assert(minimum_weighted_squared_error(endpoints, 1) == direct_one(endpoints));
    assert(minimum_weighted_squared_error(endpoints, 2) == 0);
    vector<long long> full(256, limit);
    long long one = minimum_weighted_squared_error(full, 1);
    assert(one == direct_one(full));
    assert(one > numeric_limits<int>::max());
    assert(minimum_weighted_squared_error(full, 2) == direct_two(full));
    assert(minimum_weighted_squared_error(full, 255) == limit);
    assert(minimum_weighted_squared_error(full, 256) == 0);
    for (int x = 0; x < 256; ++x) full[x] = (x % 7 == 0 ? 0 : limit - x);
    assert(minimum_weighted_squared_error(full, 1) == direct_one(full));
    assert(minimum_weighted_squared_error(full, 2) == direct_two(full));
    quantization_checks += 18;
}

void check_quantization_contract() {
    rejects([] { minimum_weighted_squared_error({1}, 0); });
    rejects([] { minimum_weighted_squared_error({0, 1}, 0); });
    rejects([] { minimum_weighted_squared_error({}, -1); });
    rejects([] { minimum_weighted_squared_error({}, 257); });
    rejects([] { minimum_weighted_squared_error(vector<long long>(257), 1); });
    rejects([] { minimum_weighted_squared_error({-1}, 1); });
    rejects([] { minimum_weighted_squared_error({(1LL << 26) + 1}, 1); });
    // Invalid data must be checked even when K or a zero prefix could short-cut.
    rejects([] { minimum_weighted_squared_error({0, -1}, 256); });
    rejects([] { minimum_weighted_squared_error({0, (1LL << 26) + 1}, 0); });
}

int main() {
    check_speed();
    check_generated_speed();
    check_speed_contract();
    cout << "positive-denominator-offset-real-bisection PASS: " << speed_checks
         << " known roots, pole/negative/upper-bound cases and finite-input contracts\n";
    check_quantization();
    check_quantization_contract();
    cout << "weighted-squared-quantization-interval-dp PASS: " << quantization_checks
         << " representative-set comparisons, rounding/zero/K/64-bit cases and contracts\n";
    cout << "All 2 speed and quantization implementations passed independent comparisons and contract checks.\n";
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compiler", default=os.environ.get("CXX", "g++"))
    args = parser.parse_args()
    compiler = shutil.which(args.compiler)
    if compiler is None:
        print(f"C++ compiler not found: {args.compiler}", file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix="flowchartcp-speed-quantization-") as directory:
        source = Path(directory) / "published.cpp"
        executable = Path(directory) / "published"
        source.write_text(extracted_source() + "\n" + TESTS, encoding="utf8")
        subprocess.run(
            [compiler, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror",
             str(source), "-o", str(executable)],
            check=True, timeout=90,
        )
        subprocess.run([str(executable)], check=True, timeout=90)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
        print(error, file=sys.stderr)
        sys.exit(1)
