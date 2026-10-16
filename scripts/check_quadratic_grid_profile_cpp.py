#!/usr/bin/env python3
"""Extract the actual MDX C++20 fence and compare it with independent path DP.
Usage: python3 checker.py [article.mdx] [--sanitize]
"""
from pathlib import Path
import json
import os
import shutil
import re
import subprocess
import sys
import tempfile

HARNESS = r'''
#include <array>
#include <iostream>
#include <limits>
#include <random>
#include <string>
using I = std::int64_t;
using W = __int128_t;
using Query = QuadraticGridQuery;
long long checks=0, exhaustive_grids=0, random_grids=0, invalid_cases=0;
unsigned long long checksum=0;
void equal(I actual,I expected,const char* message) {
    if(actual!=expected) {
        std::cerr<<message<<": actual="<<actual<<" expected="<<expected<<'\n';
        std::exit(1);
    }
    ++checks;
    checksum=checksum*1000003ULL+static_cast<unsigned long long>(actual);
}
template<class Action> void rejects(Action action) {
    bool caught=false;
    try {action();} catch(const std::invalid_argument&) {caught=true;}
    if(!caught) {std::cerr<<"expected invalid_argument\n";std::exit(1);}
    ++invalid_cases;
}
std::vector<std::vector<I>> direct_dp(int n,const std::vector<I>& cost) {
    int m=int(cost.size());
    std::vector<std::vector<I>> dp(n,std::vector<I>(m));
    for(int r=0;r<n;++r) for(int c=0;c<m;++c) {
        if(r==0 && c==0) continue;
        I best=std::numeric_limits<I>::max();
        if(r) best=std::min(best,dp[r-1][c]+cost[c]);
        if(c) best=std::min(best,dp[r][c-1]+I(r+1)*(r+1));
        dp[r][c]=best;
    }
    return dp;
}
void small_grid(int n,const std::vector<I>& cost) {
    auto expected=direct_dp(n,cost);
    int m=int(cost.size());
    std::vector<Query> queries;
    for(int c=m;c>=1;--c) for(int r=n;r>=1;--r) queries.push_back({r,c});
    queries.push_back({1,1});
    queries.push_back({n,m});
    auto answer=minimum_quadratic_grid_costs(n,cost,queries);
    for(std::size_t i=0;i<queries.size();++i)
        equal(answer[i],expected[queries[i].row-1][queries[i].column-1],"batch path DP");
    QuadraticGridProfile profile(n,cost[0]);
    for(int c=0;c<m;++c) {
        if(c) profile.next_column(cost[c]);
        for(int r=1;r<=n;++r) equal(profile.value(r),expected[r-1][c],"profile path DP");
    }
}
void exhaustive() {
    for(int m=1;m<=6;++m) {
        int limit=1;
        for(int j=0;j<m;++j) limit*=6;
        for(int mask=0;mask<limit;++mask) {
            std::vector<I> cost(m);
            int bits=mask;
            for(I& c:cost) {c=1+bits%6;bits/=6;}
            for(int n=1;n<=7;++n) {
                small_grid(n,cost);
                ++exhaustive_grids;
            }
        }
    }
}
// Independent two-column minimization over the row of the only column move.
I two_columns(I x,I a,I b) {
    W answer=W(1)<<120;
    I center=(b-a)/2;
    for(I t:std::array<I,7>{1,x,center-2,center-1,center,center+1,center+2}) {
        t=std::clamp(t,I(1),x);
        W candidate=W(t-1)*a+W(t)*t+W(x-t)*b;
        answer=std::min(answer,candidate);
    }
    return I(answer);
}
void breakpoints() {
    for(I a=1;a<=20;++a) for(I b=1;b<=100;++b) {
        QuadraticGridProfile profile(1000000000,a);
        profile.next_column(b);
        I center=(b-a)/2;
        for(I x:std::array<I,9>{1,2,3,center-1,center,center+1,center+2,999999999,1000000000})
            if(x>=1 && x<=1000000000)
                equal(profile.value(x),two_columns(x,a,b),"breakpoint/equality");
    }
    for(auto [a,b]:std::array<std::pair<I,I>,6>{{
        {1,1000000000},{1000000000,1},{1000000000,1000000000},
        {999999999,1000000000},{1,999999999},{500000000,1000000000}}}) {
        QuadraticGridProfile profile(1000000000,a);
        profile.next_column(b);
        I center=(b-a)/2;
        for(I x:std::array<I,10>{1,2,3,center-1,center,center+1,center+2,500000000,999999999,1000000000})
            if(x>=1 && x<=1000000000)
                equal(profile.value(x),two_columns(x,a,b),"large breakpoint/128 bit");
    }
    // Delta g(1)=a+3. Equality must keep row 2 before cutting the suffix.
    for(I a=1;a<=30;++a) {
        small_grid(48,{a,a+2});
        small_grid(48,{a,a+3});
        small_grid(48,{a,a+4});
    }
}
void official_and_random() {
    auto expected=direct_dp(5,{1,100,100,20});
    const I official[5][4]={{0,1,2,3},{1,5,9,13},{2,11,20,29},{3,19,35,49},{4,29,54,69}};
    for(int r=0;r<5;++r) for(int c=0;c<4;++c) equal(expected[r][c],official[r][c],"official oracle");
    small_grid(5,{1,100,100,20});
    std::mt19937_64 rng(1093);
    for(int it=0;it<1800;++it) {
        int n=1+int(rng()%60),m=1+int(rng()%35);
        std::vector<I> cost(m);
        for(I& c:cost) c=1+I(rng()%(it%2?1000000000:2000));
        small_grid(n,cost);
        ++random_grids;
    }
}
I sum1(I x) {return I(W(x)*(x+1)/2);}
W sum2(I x) {return W(x)*(x+1)*(2*x+1)/6;}
I increasing_closed_form(I row,int column) {
    I j=column-1,k=std::min(j,row);
    W answer=W(1+j*j)*row-1-sum2(k)+sum1(k)
            +W(j-k)*row*row-W(row)*(j*j-k*k);
    return I(answer);
}
void maximum_cases() {
    constexpr I N=1000000000;
    std::mt19937_64 rng(2021011093);
    for(int type=0;type<4;++type) {
        int m=type==3?30000:200000;
        std::vector<I> cost(m);
        for(int j=0;j<m;++j) {
            if(type==0) cost[j]=1000000000;
            if(type==1) cost[j]=1000000000-j;
            if(type==2) cost[j]=j%2?1000000000:1;
            if(type==3) cost[j]=1+I(j)*j;
        }
        std::vector<Query> queries;
        queries.reserve(200000);
        for(int i=0;i<200000;++i) {
            I row=i%4==0?1:i%4==1?N:i%4==2?1+I(rng()%1000000000):1+I(rng()%40000);
            queries.push_back({row,1+int(rng()%unsigned(m))});
        }
        auto actual=minimum_quadratic_grid_costs(N,cost,queries);
        for(int i=0;i<int(queries.size());++i) {
            auto [row,col]=queries[i];
            I expected=0;
            if(type<=1) expected=I(W(col-1)+W(row-1)*cost[col-1]);
            if(type==2) expected=(col-1)%2?two_columns(row,1,1000000000)+col-2:row+col-2;
            if(type==3) expected=increasing_closed_form(row,col);
            equal(actual[i],expected,"maximum closed-form profile");
        }
    }
    // Full-size random columns, independently evaluate the first 24 rows by path DP.
    constexpr int M=200000,H=24;
    std::vector<I> cost(M);
    for(I& c:cost) c=1+I(rng()%1000000000);
    std::vector<Query> queries;
    std::vector<std::vector<int>> at(M);
    for(int i=0;i<200000;++i) {
        int col=1+int(rng()%M),row=1+int(rng()%H);
        queries.push_back({row,col});
        at[col-1].push_back(i);
    }
    auto actual=minimum_quadratic_grid_costs(N,cost,queries);
    std::array<I,H> dp{};
    for(int col=0;col<M;++col) {
        for(int r=0;r<H;++r) {
            I from_left=col?dp[r]+I(r+1)*(r+1):std::numeric_limits<I>::max();
            I from_above=r?dp[r-1]+cost[col]:std::numeric_limits<I>::max();
            dp[r]=(col==0 && r==0)?0:std::min(from_left,from_above);
        }
        for(int id:at[col]) equal(actual[id],dp[queries[id].row-1],"maximum random columns path DP");
    }
    auto largest=minimum_quadratic_grid_costs(N,std::vector<I>(200000,1000000000),{{N,200000}});
    equal(largest[0],999999999000199999LL,"largest valid answer bound");
}
void invalid_inputs() {
    const I low=std::numeric_limits<I>::min(),high=std::numeric_limits<I>::max();
    for(I n:std::array<I,5>{0,-1,1000000001,low,high}) {
        rejects([&]{QuadraticGridProfile x(n,1);});
        rejects([&]{minimum_quadratic_grid_costs(n,{1},{});});
    }
    for(I c:std::array<I,5>{0,-1,1000000001,low,high}) {
        rejects([&]{QuadraticGridProfile x(3,c);});
        rejects([&]{minimum_quadratic_grid_costs(3,{1,c},{});});
    }
    rejects([&]{minimum_quadratic_grid_costs(3,{},{});});
    rejects([&]{minimum_quadratic_grid_costs(3,std::vector<I>(200001,1),{});});
    rejects([&]{minimum_quadratic_grid_costs(3,{1},std::vector<Query>(200001,{1,1}));});
    std::vector<Query> bad={{0,1},{-1,1},{4,1},{low,1},{high,1},{1,0},{1,-1},{1,3},
                            {1,std::numeric_limits<int>::min()},{1,std::numeric_limits<int>::max()}};
    for(Query q:bad) rejects([&]{minimum_quadratic_grid_costs(3,{5,7},{q});});
    QuadraticGridProfile profile(3,5);
    profile.next_column(7);
    auto expected=direct_dp(3,{5,7});
    for(I c:std::array<I,5>{0,-1,1000000001,low,high}) {
        rejects([&]{profile.next_column(c);});
        for(int row=1;row<=3;++row) equal(profile.value(row),expected[row-1][1],"state after bad cost");
    }
    for(I row:std::array<I,5>{0,-1,4,low,high}) rejects([&]{profile.value(row);});
    for(int row=1;row<=3;++row) equal(profile.value(row),expected[row-1][1],"state after bad row");
    QuadraticGridProfile one_row(1,1);
    for(int col=1;col<200000;++col) one_row.next_column(1);
    equal(one_row.value(1),199999,"maximum number of incremental columns");
    rejects([&]{one_row.next_column(1);});
    equal(one_row.value(1),199999,"state after too many columns");
    equal(I(minimum_quadratic_grid_costs(1,{1000000000},{}).size()),0,"empty queries");
}
int main() {
    official_and_random();
    exhaustive();
    breakpoints();
    maximum_cases();
    invalid_inputs();
    std::cout<<"{\"checks\":"<<checks<<",\"exhaustiveGrids\":"<<exhaustive_grids
             <<",\"randomGrids\":"<<random_grids<<",\"invalidCases\":"<<invalid_cases
             <<",\"checksum\":\""<<checksum<<"\"}\n";
}
'''

args = [arg for arg in sys.argv[1:] if arg != '--sanitize']
article = Path(args[0]) if args else Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/convex-piecewise-quadratic-suffix-cap.mdx'
blocks = re.findall(r'^```cpp\n(.*?)^```\s*$', article.read_text(), re.M | re.S)
if len(blocks) != 1:
    raise RuntimeError('expected exactly one visible C++ fence')
with tempfile.TemporaryDirectory(prefix='flowchartcp-mincost-paths-') as directory:
    source, executable = Path(directory)/'check.cpp', Path(directory)/'check'
    source.write_text(blocks[0] + '\n' + HARNESS)
    flags = ['-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror']
    environment = os.environ.copy()
    sanitized = '--sanitize' in sys.argv
    if sanitized:
        flags += ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        environment['ASAN_OPTIONS'] = 'detect_leaks=0'
    compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++') or 'c++'
    subprocess.run([compiler, *flags, str(source), '-o', str(executable)], check=True, timeout=120)
    result = subprocess.run([str(executable)], text=True, capture_output=True,
                            check=True, env=environment, timeout=180)
    report = json.loads(result.stdout)
    report['article'] = str(article)
    report['sanitized'] = sanitized
    print(json.dumps(report, ensure_ascii=False, indent=2))
