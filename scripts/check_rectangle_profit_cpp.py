#!/usr/bin/env python3
"""Validate the published implicit rectangle profit search by all-pair comparison."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
SITE=Path(__file__).resolve().parent.parent
TESTS=r'''
long long brute(const vector<pair<long long,long long>>& a,
                const vector<pair<long long,long long>>& b) {
    long long answer = 0;
    for (auto [p,d] : a) for (auto [q,e] : b)
        if (p < q && d < e) answer = max(answer, (q-p)*(e-d));
    return answer;
}
template<class F> void rejects(F f) {
    bool caught=false;
    try {f();} catch(const invalid_argument&) {caught=true;}
    assert(caught);
}
int main() {
    using Point=pair<long long,long long>;
    vector<vector<Point>> groups(512);
    for (int mask=0;mask<512;++mask)
        for(int i=0;i<9;++i) if(mask>>i&1) groups[mask].push_back({1+i/3,1+i%3});
    for(const auto& a:groups) for(const auto& b:groups)
        assert(maximum_positive_rectangle_profit(a,b)==brute(a,b));
    mt19937 random(10202026);
    for(int t=0;t<18000;++t) {
        vector<Point> a(random()%19),b(random()%19);
        for(auto& [p,d]:a){p=1+random()%25;d=1+random()%25;}
        for(auto& [q,e]:b){q=1+random()%25;e=1+random()%25;}
        auto original_a=a,original_b=b;
        assert(maximum_positive_rectangle_profit(a,b)==brute(a,b));
        assert(a==original_a && b==original_b);
    }
    assert(maximum_positive_rectangle_profit({{10,10}},{{9,9}})==0);
    assert(maximum_positive_rectangle_profit({{1,1}},{{1000000000,1000000000}})
        ==999999998000000001LL);
    assert(maximum_positive_rectangle_profit({{1,3},{2,1}},{{3,5},{7,2}})==5);
    vector<Point> a,b;
    for(int i=0;i<500000;++i) {a.push_back({i+1,500000-i});b.push_back({i+2,500001-i});}
    assert(maximum_positive_rectangle_profit(a,b)==1);
    assert(maximum_positive_rectangle_profit(vector<Point>(500000,{1,1}),
        vector<Point>(500000,{2,2}))==1);
    assert(maximum_positive_rectangle_profit({},{{1,1}})==0);
    rejects([]{maximum_positive_rectangle_profit({{0,1}},{});});
    rejects([]{maximum_positive_rectangle_profit({},{{1,-1}});});
    rejects([]{maximum_positive_rectangle_profit({{1000000001,1}},{});});
    rejects([]{maximum_positive_rectangle_profit(vector<Point>(500001,{1,1}),{});});
    rejects([]{maximum_positive_rectangle_profit({},vector<Point>(500001,{1,1}));});
    cout<<"PASS: rectangle profit against all 3x3 point subsets, random all-pair searches and 500000-point frontiers.\n";
}
'''
def main():
    compiler=os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
    if not compiler:raise RuntimeError('A C++20 compiler is required')
    article=SITE/'src/content/docs/techniques/pareto-pruned-max-rectangle-monotone-partner.mdx'
    fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article.read_text(),re.M|re.S)
    if len(fences)!=1:raise ValueError('Expected one complete published C++ implementation')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-rectangle-profit-') as directory:
        src=Path(directory)/'test.cpp';binary=Path(directory)/'test';src.write_text(fences[0]+TESTS)
        subprocess.run([compiler,'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(src),'-o',str(binary)],check=True,timeout=90)
        subprocess.run([str(binary)],check=True,timeout=90)
if __name__=='__main__':main()
