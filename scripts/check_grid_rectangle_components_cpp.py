#!/usr/bin/env python3
"""Compile the actual article fence and compare it with rectangle-local BFS.

Usage: python3 check.py --article path/to/grid-rectangle-components-euler-boundary.mdx
All generated files stay under /tmp/flowchartcp-paint-components-*.
"""
import argparse
import os
import shutil
import json
from pathlib import Path
import re
import subprocess
import tempfile

HARNESS = r'''
struct Oracle {
    const vector<string>& g;
    int n, m, token = 0;
    vector<int> seen, work;
    explicit Oracle(const vector<string>& grid)
        : g(grid), n(int(g.size())), m(int(g[0].size())), seen(n*m,0) {
        work.reserve(n*m);
    }
    int count(int r0, int c0, int r1, int c1) {
        ++token;
        int answer = 0;
        const int dr[4] = {-1,1,0,0}, dc[4] = {0,0,-1,1};
        for(int r=r0;r<r1;++r) for(int c=c0;c<c1;++c) {
            int seed = r*m+c;
            if(seen[seed]==token) continue;
            ++answer;
            work.clear();
            work.push_back(seed);
            seen[seed]=token;
            for(size_t head=0;head<work.size();++head) {
                int p=work[head], rr=p/m, cc=p%m;
                for(int d=0;d<4;++d) {
                    int nr=rr+dr[d],nc=cc+dc[d];
                    if(nr<r0||nr>=r1||nc<c0||nc>=c1) continue;
                    int next=nr*m+nc;
                    if(seen[next]!=token && g[nr][nc]==g[rr][cc]) {
                        seen[next]=token;
                        work.push_back(next);
                    }
                }
            }
        }
        return answer;
    }
};

using Rect=array<int,4>;
long long queries=0, binary_grids=0, ternary_grids=0, four_color_grids=0;
long long random_grids=0, explicit_grids=0, stress_grids=0, invalid_cases=0;
unsigned long long checksum=0;
void compare(GridRectangleComponents& fast, Oracle& slow, const Rect& q,
             optional<int> known=nullopt) {
    int expected=slow.count(q[0],q[1],q[2],q[3]);
    int actual=fast.count(q[0],q[1],q[2],q[3]);
    if(actual!=expected || (known && actual!=*known)) {
        cerr<<"mismatch: ";
        for(int x:q) cerr<<x<<' ';
        cerr<<" fast="<<actual<<" bfs="<<expected<<'\n';
        for(const string& row:slow.g) cerr<<row<<'\n';
        exit(1);
    }
    ++queries;
    checksum=checksum*1000003ULL+unsigned(actual);
}
vector<Rect> rectangles(int n,int m) {
    vector<Rect> result;
    for(int r0=0;r0<n;++r0) for(int c0=0;c0<m;++c0)
        for(int r1=r0+1;r1<=n;++r1) for(int c1=c0+1;c1<=m;++c1)
            result.push_back({r0,c0,r1,c1});
    return result;
}
void all_rectangles(const vector<string>& g) {
    GridRectangleComponents fast(g);
    Oracle slow(g);
    auto all=rectangles(int(g.size()),int(g[0].size()));
    for(const auto& q:all) compare(fast,slow,q);
    // Interleave repeats after other queries to check that no boundary mark leaks.
    compare(fast,slow,all.back());
    compare(fast,slow,all.front());
    compare(fast,slow,all[all.size()/2]);
}
void exhaustive(int colors,int max_side,int max_area,long long& amount) {
    for(int n=1;n<=max_side;++n) for(int m=1;m<=max_side;++m) {
        if(n*m>max_area) continue;
        unsigned long long count=1;
        for(int i=0;i<n*m;++i) count*=unsigned(colors);
        for(unsigned long long mask=0;mask<count;++mask) {
            auto bits=mask;
            vector<string> g(n,string(m,'A'));
            for(int i=0;i<n*m;++i) {
                g[i/m][i%m]=char('A'+bits%unsigned(colors));
                bits/=unsigned(colors);
            }
            all_rectangles(g);
            ++amount;
        }
    }
}
template<class Action> void invalid(Action action) {
    bool caught=false;
    try { action(); } catch(const invalid_argument&) { caught=true; }
    if(!caught) { cerr<<"missing invalid_argument\n"; exit(1); }
    ++invalid_cases;
}
void invalid_inputs() {
    vector<vector<string>> grids={
        {},{""},{"AA","A"},{"A","AA"},{"a"},{"0"},{"."},{"@"},{"["},
        {string(1,'\0')},{string(1,char(255))},
        vector<string>(1001,"A"),{string(1001,'A')},{"AA","AZ","Aa"}
    };
    for(const auto& g:grids) invalid([&]{GridRectangleComponents x(g);});
    vector<string> g={"AAA","ABA","AAA"};
    GridRectangleComponents fast(g);
    Oracle slow(g);
    vector<Rect> bad={
        {-1,0,1,1},{0,-1,1,1},{0,0,4,1},{0,0,1,4},
        {0,0,0,1},{0,0,1,0},{2,0,1,1},{0,2,1,1},
        {INT_MIN,0,INT_MAX,1},{0,INT_MIN,1,INT_MAX},
        {INT_MAX,0,INT_MAX,1},{0,INT_MAX,1,INT_MAX},
        {0,0,INT_MIN,1},{0,0,1,INT_MIN},{3,0,4,1},{0,3,1,4}
    };
    for(const auto& q:bad) {
        invalid([&]{fast.count(q[0],q[1],q[2],q[3]);});
        compare(fast,slow,{0,0,3,3},2);
    }
}
void official_and_explicit() {
    vector<string> sample={"ABBAAAAA","ABAAAABA","CAADABBA","AAAAAAAA"};
    GridRectangleComponents fast(sample);
    Oracle slow(sample);
    vector<Rect> q={{0,0,4,8},{2,4,3,8},{0,2,2,4},{0,3,2,5},
                    {0,0,3,3},{3,3,4,4},{1,5,4,8},{2,4,4,6},{0,5,3,8}};
    vector<int> expected={6,3,2,1,4,1,3,2,2};
    for(size_t i=0;i<q.size();++i) compare(fast,slow,q[i],expected[i]);
    vector<vector<string>> grids={
        {"A"},{"AAAA"},{"ABBA"},{"A","B","B","A"},
        {"AAA","ABA","AAA"}, // one hole
        {"AAAAAAA","ABBBBBA","ABCCCBA","ABCDCBA","ABCCCBA","ABBBBBA","AAAAAAA"},
        {"AAAA","ABBA","AAAA"}, // same color connected only outside one-row query
        {"ABBA","AAAA","ABBA"}, // boundary touches and repeated wall labels
        {"AB","BA"}, // diagonal point contact
        {"AB","CD"}, // four-color junction
        {"ABC","DBE","FGH"}, // many colors and repeated center color
        {"AAAAAAAAA","ABABABABA","AAAAAAAAA","ABABABABA","AAAAAAAAA"},
        {"ABBBBBBA","ABAABABA","ABCCBABA","ABCCBABA","ABAABABA","ABBBBBBA"},
        {"ABCDEFGHIJKLMNOPQRSTUVWXYZ"},
        {"A","B","C","D","E","F","G","H","I","J","K","L","M",
         "N","O","P","Q","R","S","T","U","V","W","X","Y","Z"}
    };
    for(const auto& g:grids) {all_rectangles(g);++explicit_grids;}
    vector<string> outside={"AAAA","ABBA","AAAA"};
    GridRectangleComponents cut(outside);
    if(cut.count(0,0,3,4)!=2 || cut.count(1,0,2,4)!=3) exit(1);
}
void random_cases() {
    mt19937 rng(1094);
    for(int it=0;it<2500;++it) {
        int n=1+int(rng()%10),m=1+int(rng()%11);
        int colors=1+int(rng()%26);
        vector<string> g(n,string(m,'A'));
        for(auto& row:g) for(char& c:row) c=char('A'+rng()%unsigned(colors));
        GridRectangleComponents fast(g);
        Oracle slow(g);
        for(int j=0;j<80;++j) {
            int r0=int(rng()%unsigned(n)),r1=int(rng()%unsigned(n));
            int c0=int(rng()%unsigned(m)),c1=int(rng()%unsigned(m));
            if(r0>r1) swap(r0,r1);
            if(c0>c1) swap(c0,c1);
            compare(fast,slow,{r0,c0,r1+1,c1+1});
        }
        ++random_grids;
    }
}
void maximum_cases() {
    mt19937 rng(202101);
    for(int type=0;type<6;++type) {
        int n=1000,m=1000;
        vector<string> g(n,string(m,'A'));
        for(int r=0;r<n;++r) for(int c=0;c<m;++c) {
            if(type==1) g[r][c]=char('A'+(r+c)%26);
            if(type==2) g[r][c]=char('A'+r%26);
            if(type==3) g[r][c]=char('A'+c%26);
            if(type==4) g[r][c]=char('A'+min({r,c,n-1-r,m-1-c})%26);
            if(type==5) g[r][c]=(r%2 && c%2)?'B':'A';
        }
        GridRectangleComponents fast(g);
        Oracle slow(g);
        int full=type==0?1:type==1?n*m:type==2?n:type==3?m:type==4?500:250001;
        compare(fast,slow,{0,0,n,m},full);
        for(int j=0;j<24;++j) {
            int r0=int(rng()%unsigned(n)),r1=int(rng()%unsigned(n));
            int c0=int(rng()%unsigned(m)),c1=int(rng()%unsigned(m));
            if(r0>r1) swap(r0,r1);
            if(c0>c1) swap(c0,c1);
            compare(fast,slow,{r0,c0,r1+1,c1+1});
        }
        if(type<=1) for(int j=0;j<1000;++j) {
            int actual=fast.count(0,0,n,m);
            if(actual!=full) {cerr<<"maximum repeated query failed\n";exit(1);}
            ++queries;
            checksum=checksum*1000003ULL+unsigned(actual);
        }
        ++stress_grids;
    }
    for(int axis=0;axis<2;++axis) {
        int n=axis?1000:1,m=axis?1:1000;
        vector<string> g(n,string(m,'A'));
        for(int r=0;r<n;++r) for(int c=0;c<m;++c) g[r][c]=char('A'+(r+c)%26);
        GridRectangleComponents fast(g);
        Oracle slow(g);
        compare(fast,slow,{0,0,n,m},1000);
        ++stress_grids;
    }
}
int main(int argc,char** argv) {
    bool small_only=argc>1 && string(argv[1])=="--small-only";
    official_and_explicit();
    invalid_inputs();
    exhaustive(2,4,16,binary_grids);
    exhaustive(3,3,9,ternary_grids);
    exhaustive(4,3,6,four_color_grids);
    random_cases();
    if(!small_only) maximum_cases();
    cout<<"{\"binaryGrids\":"<<binary_grids
        <<",\"ternaryGrids\":"<<ternary_grids
        <<",\"fourColorGrids\":"<<four_color_grids
        <<",\"randomGrids\":"<<random_grids
        <<",\"explicitGrids\":"<<explicit_grids
        <<",\"stressGrids\":"<<stress_grids
        <<",\"invalidCases\":"<<invalid_cases
        <<",\"checkedQueries\":"<<queries
        <<",\"checksum\":"<<checksum<<"}\n";
}
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--article', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/grid-rectangle-components-euler-boundary.mdx')
    parser.add_argument('--sanitize', action='store_true')
    args = parser.parse_args()
    content = args.article.read_text()
    blocks = re.findall(r'^```cpp\n(.*?)^```\s*$', content, re.M | re.S)
    if len(blocks) != 1:
        raise SystemExit('Expected exactly one visible cpp fence in the article')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-paint-components-') as temporary_directory:
        directory = Path(temporary_directory)
        source = directory / 'check.cpp'
        binary = directory / 'check'
        source.write_text(blocks[0] + '\n' + HARNESS)
        compiler = os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++') or 'c++'
        command = [compiler, '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror']
        if args.sanitize:
            command += ['-O1', '-g', '-fsanitize=address,undefined', '-fno-omit-frame-pointer']
        command += [str(source), '-o', str(binary)]
        subprocess.run(command, check=True, timeout=120)
        # This environment cannot run LeakSanitizer under ptrace; ASan/UBSan stay on.
        environment = dict(os.environ)
        if args.sanitize:
            environment['ASAN_OPTIONS'] = 'detect_leaks=0'
        result = subprocess.run([str(binary)], check=True, text=True,
                                capture_output=True, env=environment, timeout=180)
    report = json.loads(result.stdout)
    report['article'] = str(args.article)
    report['sanitized'] = args.sanitize
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
