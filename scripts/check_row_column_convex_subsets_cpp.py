#!/usr/bin/env python3
"""Extract the actual complete MDX C++20 API and test it with literal cell subsets."""
import argparse, hashlib, json, os, re, subprocess, tempfile
from pathlib import Path

HARNESS=r'''
#include <chrono>
#include <climits>
#include <functional>
#include <iostream>
#include <random>
#include <sys/resource.h>
#include <utility>

using Grid=std::vector<std::string>;
constexpr int MOD=1000000007;
std::uint64_t checks=0,checksum=0,literal_shapes=0,all_grass_boards=0,random_subset_boards=0;
std::uint64_t subset_candidates=0,metamorphic_checks=0,direct_dp_boards=0,invalid_calls=0;
void require(bool ok,const char* label){++checks;if(!ok)throw std::runtime_error(label);}
void record(int value){checksum=checksum*1000003ULL+std::uint64_t(value);}
int mod(std::int64_t value){value%=MOD;if(value<0)value+=MOD;return int(value);}
bool literal_shape(int h,int w,std::uint64_t mask){
    if(!mask)return false;
    for(int r=0;r<h;++r){int first=w,last=-1,count=0;for(int c=0;c<w;++c)if(mask>>(r*w+c)&1ULL){first=std::min(first,c);last=c;++count;}
        if(count&&last-first+1!=count)return false;}
    for(int c=0;c<w;++c){int first=h,last=-1,count=0;for(int r=0;r<h;++r)if(mask>>(r*w+c)&1ULL){first=std::min(first,r);last=r;++count;}
        if(count&&last-first+1!=count)return false;}
    int root=0;while(!(mask>>root&1ULL))++root;
    std::uint64_t seen=1ULL<<root;std::vector<int> queue{root};
    for(std::size_t k=0;k<queue.size();++k){const int r=queue[k]/w,c=queue[k]%w;
        for(auto [dr,dc]:std::vector<std::pair<int,int>>{{1,0},{-1,0},{0,1},{0,-1}}){const int rr=r+dr,cc=c+dc;
            if(rr<0||rr>=h||cc<0||cc>=w)continue;
            const int p=rr*w+cc;
            if((mask>>p&1ULL)&&!(seen>>p&1ULL)){seen|=1ULL<<p;queue.push_back(p);}}
    }
    return seen==mask;
}
Grid board(int h,int w,std::uint64_t mask){Grid a(h,std::string(w,'.'));for(int i=0;i<h*w;++i)if(mask>>i&1ULL)a[i/w][i%w]='G';return a;}
int literal_subsets(const Grid&a){const int h=int(a.size()),w=int(a[0].size());std::uint64_t grass=0;
    for(int i=0;i<h*w;++i)if(a[i/w][i%w]=='G')grass|=1ULL<<i;
    int answer=0;for(std::uint64_t sub=grass;sub;sub=(sub-1)&grass){++subset_candidates;answer+=literal_shape(h,w,sub);}
    return answer;
}
void exhaustive(){
    for(int h=1;h<=4;++h)for(int w=1;w<=4;++w){const int cells=h*w,total=1<<cells;std::vector<int> zeta(total);
        for(int mask=1;mask<total;++mask){zeta[mask]=literal_shape(h,w,std::uint64_t(mask));++literal_shapes;}
        for(int bit=0;bit<cells;++bit)for(int mask=0;mask<total;++mask)if(mask>>bit&1)zeta[mask]+=zeta[mask^(1<<bit)];
        for(int grass=0;grass<total;++grass){const Grid a=board(h,w,std::uint64_t(grass));const int got=count_row_column_convex_subsets(a);record(got);
            require(got==zeta[grass],"all small grass boards versus literal subset zeta");++all_grass_boards;}
    }
}
int direct_transitions(const Grid&a){
    const int h=int(a.size()),w=int(a[0].size());
    struct State{int l,r,lf,rf,ways;};std::vector<State> previous;int answer=0;
    for(int row=0;row<h;++row){std::vector<State> next;
        for(int L=0;L<w;++L)for(int R=L;R<w;++R){if(a[row][R]!='G')break;std::int64_t value[4]={1,0,0,0};
            for(const State&old:previous){if(L>old.r||R<old.l||(old.lf&&L<old.l)||(old.rf&&R>old.r))continue;
                const int q=2*(old.lf||L>old.l)+(old.rf||R<old.r);value[q]+=old.ways;}
            for(int q=0;q<4;++q){const int ways=mod(value[q]);if(ways)next.push_back({L,R,q/2,q%2,ways});answer=mod(std::int64_t(answer)+ways);}
        }previous.swap(next);
    }return answer;
}
// A second maximum-size reference: only old left endpoints are prefix-summed.
// Enumerate every old right endpoint explicitly. O(H*W^3), not the API's2D rectangles.
int one_axis_reference(const Grid&a){
    const int h=int(a.size()),w=int(a[0].size()),stride=w+1;std::array<std::vector<int>,4>old,next,pref;
    for(int q=0;q<4;++q){old[q].assign(w*w,0);next[q].assign(w*w,0);pref[q].assign(w*stride,0);}
    int answer=0;
    for(int row=0;row<h;++row){
        for(int q=0;q<4;++q){std::fill(next[q].begin(),next[q].end(),0);
            for(int r=0;r<w;++r){pref[q][r*stride]=0;for(int l=0;l<w;++l)pref[q][r*stride+l+1]=mod(std::int64_t(pref[q][r*stride+l])+old[q][l*w+r]);}}
        for(int L=0;L<w;++L)for(int R=L;R<w;++R){if(a[row][R]!='G')break;std::int64_t value[4]={1,0,0,0};
            for(int r=L;r<w;++r){const int off=r*stride,upper=std::min(R,r)+1;
                int x00=pref[0][off+upper]-pref[0][off+L];if(x00<0)x00+=MOD;
                int x01=pref[1][off+upper]-pref[1][off+L];if(x01<0)x01+=MOD;
                const std::int64_t x10=std::int64_t(pref[0][off+L])+pref[2][off+L+1];
                const std::int64_t x11=std::int64_t(pref[1][off+L])+pref[3][off+L+1];
                if(r<=R){value[0]+=x00;value[2]+=x10;}else{value[1]+=x00;value[3]+=x10;}
                if(r>=R){value[1]+=x01;value[3]+=x11;}
            }
            for(int q=0;q<4;++q){next[q][L*w+R]=mod(value[q]);answer=mod(std::int64_t(answer)+next[q][L*w+R]);}
        }old.swap(next);
    }return answer;
}
Grid transpose(const Grid&a){Grid b(a[0].size(),std::string(a.size(),'.'));for(std::size_t i=0;i<a.size();++i)for(std::size_t j=0;j<a[0].size();++j)b[j][i]=a[i][j];return b;}
void random_tests(){
    std::mt19937 rng(19692021);
    for(int rep=0;rep<600;++rep){const int h=1+int(rng()%5),w=1+int(rng()%5);Grid a(h,std::string(w,'.'));int grass=0;
        for(auto&row:a)for(char&v:row)if(rng()%2&&grass<18){v='G';++grass;}
        const int expected=literal_subsets(a),got=count_row_column_convex_subsets(a);record(got);
        require(got==expected,"random literal subsets");++random_subset_boards;
        require(direct_transitions(a)==expected,"direct row DP also matches literal");
        require(one_axis_reference(a)==expected,"one-axis max reference matches literal");
        const Grid before=a;
        for(int type=0;type<4;++type){Grid b=a;if(type&1)std::reverse(b.begin(),b.end());if(type&2)for(auto&row:b)std::reverse(row.begin(),row.end());
            require(count_row_column_convex_subsets(b)==expected,"grid reflections");require(count_row_column_convex_subsets(transpose(b))==expected,"grid transpose");metamorphic_checks+=2;}
        Grid padded=a;for(auto&row:padded)row='.'+row+'.';padded.insert(padded.begin(),std::string(w+2,'.'));padded.push_back(std::string(w+2,'.'));
        require(count_row_column_convex_subsets(padded)==expected,"empty padding");++metamorphic_checks;
        require(a==before,"const input unchanged");
    }
    for(int rep=0;rep<240;++rep){const int h=1+int(rng()%18),w=1+int(rng()%18);Grid a(h,std::string(w,'.'));
        for(auto&row:a)for(char&v:row)if(rng()%5)v='G';
        const int expected=direct_transitions(a),got=count_row_column_convex_subsets(a);record(got);
        require(got==expected,"literal old-interval transition reference");require(one_axis_reference(a)==expected,"max reference versus explicit transitions");++direct_dp_boards;
    }
}
void api_cases(){
    require(count_row_column_convex_subsets({})==0,"empty grid");require(count_row_column_convex_subsets({"",""})==0,"zero-width grid");
    require(count_row_column_convex_subsets({"G"})==1,"single allowed");require(count_row_column_convex_subsets({"."})==0,"single blocked");
    require(count_row_column_convex_subsets({"GG","GG"})==13,"official sample1");
    require(count_row_column_convex_subsets({"GGGG","GGGG","GG.G","GGGG"})==642,"official sample2");
    for(const Grid&a:std::vector<Grid>{{"GG",".G","GG"},{"G.",".G"},{"GGG","G.G","GGG"},{".G.","GGG",".G."},{"GGG","GGG","GGG"}})
        require(count_row_column_convex_subsets(a)==literal_subsets(a),"holes diagonal contacts equal boundary plateaus");
    for(int n=2;n<=4;++n){
        Grid a(n,std::string(n,'.'));for(int i=0;i<n;++i)a[i][n/2]='G';a[n/2]=std::string(n,'G');
        const std::int64_t L=n/2,R=n-1-L;
        require(literal_subsets(a)==mod((L+1)*(R+1)*(L+1)*(R+1)+L*(L+1)+R*(R+1)),"small literal cross formula");
        a.assign(n,std::string(n,'.'));a[0]=a[1]=std::string(n,'G');
        const std::int64_t T=n*(n+1)/2,D=std::int64_t(n+2)*(n+1)*n*(n-1)/24;
        require(literal_subsets(a)==mod(2*T+T*T-2*D),"small literal two-row formula");
        if(n>=3){a.assign(n,std::string(n,'.'));for(int i=0;i<n;++i)a[i][0]=a[i][n-1]=a[0][i]=a[n-1][i]='G';
            require(literal_subsets(a)==4*n*(n+1)/2-4+4*(n-1)*(n-1),"small literal outer frame formula");}
    }
    auto reject=[&](const Grid&a){bool caught=false;try{(void)count_row_column_convex_subsets(a);}catch(const std::invalid_argument&){caught=true;}
        require(caught,"invalid grid accepted");++invalid_calls;require(count_row_column_convex_subsets({"G"})==1,"valid after exception");};
    reject(Grid(151,""));reject(Grid(151,std::string(1,'G')));reject({std::string(151,'G')});
    reject({"G","GG"});reject({"","G"});reject({"G",""});reject({"X"});reject({".","X"});reject({std::string(1,'\0')});reject({std::string(1,char(255))});
    for(int k=0;k<50;++k){require(count_row_column_convex_subsets({"GG","GG"})==13,"repeated fresh state");require(count_row_column_convex_subsets({})==0,"interleaved empty state");}
}
std::vector<std::pair<std::string,int>> maximum_values;
void max_case(const std::string&name,const Grid&a,int expected){const Grid before=a;const int got=count_row_column_convex_subsets(a);record(got);
    require(got==expected,"maximum expected count");require(a==before,"maximum input unchanged");require(got>=0&&got<MOD,"modular range");maximum_values.push_back({name,got});}
void maximum(){
    const int n=150;Grid a(n,std::string(n,'G'));
    max_case("all grass",a,one_axis_reference(a));
    a.assign(n,std::string(n,'.'));max_case("all blocked",a,0);
    for(int i=0;i<n;++i)for(int j=0;j<n;++j)a[i][j]=(i+j)%2?'.':'G';
    max_case("checkerboard",a,n*n/2);
    a.assign(n,std::string(n,'.'));for(int i=0;i<n;i+=2)a[i]=std::string(n,'G');max_case("separated row stripes",a,(n/2)*(n*(n+1)/2));
    a.assign(n,std::string(n,'.'));for(int i=0;i<n;++i)a[i][n/2]='G';a[n/2]=std::string(n,'G');
    const std::int64_t L=n/2,R=n-1-L;
    max_case("four-arm cross",a,mod((L+1)*(R+1)*(L+1)*(R+1)+L*(L+1)+R*(R+1)));
    a.assign(n,std::string(n,'.'));a[75]=a[76]=std::string(n,'G');const std::int64_t intervals=n*(n+1)/2,disjoint=std::int64_t(n+2)*(n+1)*n*(n-1)/24;
    max_case("two-row band",a,mod(2*intervals+intervals*intervals-2*disjoint));
    a.assign(n,std::string(n,'.'));for(int i=0;i<n;++i)a[i][0]=a[i][n-1]=a[0][i]=a[n-1][i]='G';
    max_case("one-cell outer frame",a,4*n*(n+1)/2-4+4*(n-1)*(n-1));
    max_case("thin column extension",Grid(n,"G"),n*(n+1)/2);max_case("thin row extension",Grid{std::string(n,'G')},n*(n+1)/2);
    std::mt19937 rng(913717);a.assign(n,std::string(n,'.'));for(auto&row:a)for(char&v:row)if(rng()%4)v='G';max_case("random maximum",a,one_axis_reference(a));
}
int main(){try{const auto start=std::chrono::steady_clock::now();api_cases();exhaustive();random_tests();maximum();rusage usage{};getrusage(RUSAGE_SELF,&usage);
    std::cout<<"{\"checks\":"<<checks<<",\"allSmallGrassBoards\":"<<all_grass_boards<<",\"literalNonemptyShapes\":"<<literal_shapes
      <<",\"randomLiteralSubsetBoards\":"<<random_subset_boards<<",\"literalEnumeratedSubsetCandidates\":"<<subset_candidates
      <<",\"metamorphicChecks\":"<<metamorphic_checks<<",\"directTransitionBoards\":"<<direct_dp_boards<<",\"invalidCalls\":"<<invalid_calls
      <<",\"checksum\":\""<<checksum<<"\",\"seconds\":"<<std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()
      <<",\"peakRSSKiB\":"<<usage.ru_maxrss<<",\"maximumCases\":[";bool comma=false;
    for(const auto&[name,value]:maximum_values){if(comma)std::cout<<',';comma=true;std::cout<<"{\"name\":\""<<name<<"\",\"count\":"<<value<<'}';}std::cout<<"]}\n";
}catch(const std::exception&e){std::cerr<<e.what()<<'\n';return 1;}}
'''

def main():
    p=argparse.ArgumentParser();p.add_argument('--sanitize',action='store_true');p.add_argument('--article',default=str(Path(__file__).resolve().parents[1] / 'src/content/docs/techniques/orthogonally-convex-row-interval-phase-prefix-dp.mdx'));args=p.parse_args()
    article=Path(args.article).read_text();fences=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S)
    assert len(fences)==1
    assert re.findall(r'^## (.+)$',article,re.M)==['使う場面','考え方','適用条件','なぜ正しいか','計算量','実装','関連する手法','参考資料']
    cpp=fences[0];flags=['-std=c++20','-O2','-Wall','-Wextra','-Werror']
    if args.sanitize:flags+=['-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
    with tempfile.TemporaryDirectory(prefix='flowchartcp-balanced-cpp-') as directory:
        source=Path(directory)/'check.cpp';binary=Path(directory)/'check';source.write_text(cpp+'\n'+HARNESS)
        subprocess.run(['g++',*flags,str(source),'-o',str(binary)],check=True)
        env=os.environ.copy()
        if args.sanitize:env['ASAN_OPTIONS']='detect_leaks=0:halt_on_error=1';env['UBSAN_OPTIONS']='halt_on_error=1'
        out=subprocess.run([str(binary)],capture_output=True,text=True,check=True,env=env)
        result=json.loads(out.stdout);result.update({'sanitized':args.sanitize,'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'article':args.article})
        print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
