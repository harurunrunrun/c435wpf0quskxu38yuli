#!/usr/bin/env python3
"""Compare corner sweeps with all permutations and closed-rectangle relations."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
SITE=Path(__file__).resolve().parent.parent
ARTICLE=Path(sys.argv[1]) if len(sys.argv)>1 else SITE/'src/content/docs/techniques/nested-rectangle-corner-sweep-and-validation.mdx'
TESTS=r'''
using Point=pair<long long,long long>;
using Rect=nested_corners_detail::Rectangle;
bool valid_pair(const Rect& a,const Rect& b) {
    bool disjoint=a.bottom<b.top || b.bottom<a.top || a.right<b.left || b.right<a.left;
    bool a_inside=a.top>b.top && a.bottom<b.bottom && a.left>b.left && a.right<b.right;
    bool b_inside=b.top>a.top && b.bottom<a.bottom && b.left>a.left && b.right<a.right;
    return disjoint || a_inside || b_inside;
}
bool valid_witness(const vector<Point>& a,const vector<Point>& b,const vector<int>& order) {
    int n=a.size();if(int(order.size())!=n)return false;
    vector<bool> seen(n);vector<Rect> rectangles;
    for(int i=0;i<n;++i) {
        int j=order[i];if(j<0 || j>=n || seen[j])return false;seen[j]=true;
        if(a[i].first>b[j].first || a[i].second>b[j].second)return false;
        rectangles.push_back({a[i].first,a[i].second,b[j].first,b[j].second});
        for(int k=0;k<i;++k)if(!valid_pair(rectangles[k],rectangles.back()))return false;
    }
    return true;
}
bool oracle(const vector<Point>& a,const vector<Point>& b) {
    vector<int> order(a.size());iota(order.begin(),order.end(),0);
    do {if(valid_witness(a,b,order))return true;}while(next_permutation(order.begin(),order.end()));
    return false;
}
void compare(const vector<Point>& a,const vector<Point>& b) {
    auto old_a=a,old_b=b;
    auto answer=recover_nested_rectangles(a,b);
    assert(bool(answer)==oracle(a,b));
    if(answer)assert(valid_witness(a,b,*answer));
    assert(a==old_a && b==old_b);
}
template<class F> void rejects(F f) {
    bool caught=false;try{f();}catch(const invalid_argument&){caught=true;}assert(caught);
}
long long exhaustive_grid(int width,int maximum) {
    int cells=width*width;long long cases=0;
    vector<int> masks;
    for(int n=0;n<=maximum;++n) {
        masks.clear();for(int mask=0;mask<(1<<cells);++mask)if(popcount(unsigned(mask))==n)masks.push_back(mask);
        for(int left:masks)for(int right:masks)if(!(left&right)) {
            vector<Point>a,b;
            for(int i=0;i<cells;++i) {
                Point p={1+i/width,1+i%width};
                if(left>>i&1)a.push_back(p);
                if(right>>i&1)b.push_back(p);
            }
            compare(a,b);++cases;
        }
    }
    return cases;
}
int main() {
    vector<Rect> rectangles;
    for(int t=1;t<=3;++t)for(int b=t;b<=3;++b)
      for(int l=1;l<=3;++l)for(int r=l;r<=3;++r)rectangles.push_back({t,l,b,r});
    long long border_cases=0;
    for(const auto& a:rectangles)for(const auto& b:rectangles)for(const auto& c:rectangles) {
        bool valid=valid_pair(a,b)&&valid_pair(a,c)&&valid_pair(b,c);
        assert(nested_corners_detail::boundaries_disjoint({a,b,c})==valid);
        ++border_cases;
    }
    long long complete=exhaustive_grid(3,4)+exhaustive_grid(4,3);
    mt19937 random(10202026);
    for(int trial=0;trial<9000;++trial) {
        int n=random()%7;
        vector<Point>a,b;set<Point> occupied;
        while(int(a.size())<n) {
            Point p={1+random()%12,1+random()%12};if(occupied.insert(p).second)a.push_back(p);
        }
        while(int(b.size())<n) {
            Point p={1+random()%12,1+random()%12};if(occupied.insert(p).second)b.push_back(p);
        }
        compare(a,b);
    }
    compare({{4,7},{9,8}},{{14,17},{19,18}});
    compare({{4,7},{14,17}},{{9,8},{19,18}});
    compare({{4,8},{9,7}},{{14,18},{19,17}});
    compare({{1,1},{4,8},{8,4}},{{10,6},{6,10},{10,10}});
    compare({{1,1},{2,4}},{{4,4},{3,6}});
    compare({{1,1},{2,1}},{{3,1},{4,1}});
    compare({{1,1},{1,3}},{{1,2},{1,4}});
    compare({{1,1}},{{1000000000,1000000000}});
    const int maximum=100000;
    for(int kind=0;kind<3;++kind) {
        vector<Point>a(maximum),b(maximum);
        for(int i=0;i<maximum;++i) {
            if(kind==0){a[i]={2*i+1,1};b[i]={2*i+1,3};}
            else if(kind==1){a[i]={1,2*i+1};b[i]={3,2*i+1};}
            else{a[i]={i+1,i+1};b[i]={2*maximum-i,2*maximum-i};}
        }
        auto answer=recover_nested_rectangles(a,b);assert(answer);
        for(int i=0;i<maximum;++i)assert((*answer)[i]==i);
    }
    rejects([]{recover_nested_rectangles({{1,1}},{});});
    rejects([]{recover_nested_rectangles({{1,1}},{{1,1}});});
    rejects([]{recover_nested_rectangles({{0,1}},{{2,2}});});
    rejects([]{recover_nested_rectangles({{1,1}},{{2,1000000001}});});
    rejects([]{recover_nested_rectangles({{1,1},{1,1}},{{2,2},{3,3}});});
    rejects([]{recover_nested_rectangles(vector<Point>(100001,{1,1}),vector<Point>(100001,{2,2}));});
    cout<<"PASS: nested rectangle corner matching; "<<complete<<" exhaustive corner assignments, "<<border_cases
        <<" closed-boundary triples, 9000 random all-permutation cases, 4 official cases, 100000 rectangles and API limits.\n";
}
'''
def main():
    compiler=os.environ.get('CXX') or shutil.which('g++') or shutil.which('clang++')
    if not compiler:raise RuntimeError('A C++20 compiler is required')
    fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',ARTICLE.read_text(),re.M|re.S)
    if len(fences)!=1:raise ValueError('Expected one complete C++ implementation')
    with tempfile.TemporaryDirectory(prefix='flowchartcp-corner-pairing-') as directory:
        source=Path(directory)/'test.cpp';binary=Path(directory)/'test';source.write_text(fences[0]+TESTS)
        subprocess.run([compiler,'-std=c++20','-O2','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],check=True,timeout=90)
        subprocess.run([str(binary)],check=True,timeout=180)
if __name__=='__main__':main()
