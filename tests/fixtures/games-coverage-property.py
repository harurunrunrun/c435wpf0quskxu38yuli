"""Compare the published game code and interactive queries with independent models."""
from pathlib import Path
import concurrent.futures
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
COMMON = r'''
int main(){
    using namespace tested;
    mt19937_64 rng(1098269);
'''
CASES = {
'bounded-take-grundy-period': r'''
    for(int k=1;k<=7;++k){
        map<vector<int>,bool> memo;
        auto brute=[&](auto&& self,vector<int> a)->bool{
            if(memo.count(a))return memo[a];
            for(int i=0;i<(int)a.size();++i)for(int removed=1;removed<=min(k,a[i]);++removed){
                auto b=a;b[i]-=removed;if(!self(self,b))return memo[a]=true;}
            return memo[a]=false;};
        for(int a=0;a<=9;++a)for(int b=0;b<=9;++b)for(int c=0;c<=5;++c)
            assert(bounded_take_first_wins({(unsigned)a,(unsigned)b,(unsigned)c},k)==brute(brute,{a,b,c}));
    }
    assert(!bounded_take_first_wins({},3));
    assert(bounded_take_first_wins({1000000000,1000000001},3));
    assert(!bounded_take_first_wins({~0ULL},~0ULL-1));
    assert(bounded_take_first_wins({~0ULL},~0ULL-2));
''',
'stair-game-even-piles': r'''
    map<vector<int>,bool> memo;
    auto brute=[&](auto&& self,vector<int> a)->bool{
        if(memo.count(a))return memo[a];
        for(int i=1;i<(int)a.size();++i)for(int moved=1;moved<=a[i];++moved){
            auto b=a;b[i]-=moved;b[i-1]+=moved;
            if(!self(self,b))return memo[a]=true;}
        return memo[a]=false;};
    for(int n=1;n<=6;++n){vector<int> a(n);
        auto all=[&](auto&& self,int i,int left)->void{
            if(i==n){vector<unsigned long long> x(a.begin(),a.end());assert(stair_first_wins(x)==brute(brute,a));return;}
            for(int count=0;count<=left;++count){a[i]=count;self(self,i+1,left-count);}};
        all(all,0,7);
    }
    assert(!stair_first_wins({0,0,1}));assert(!stair_first_wins({1,1,1,1}));
    assert(stair_first_wins({~0ULL,~0ULL}));
''',
'retrograde-winning-draw': r'''
    for(int trial=0;trial<140;++trial){int n=1+rng()%4;vector<vector<int>> g(n);
        for(int v=0;v<n;++v)for(int u=0;u<n;++u)if(rng()%3==0)g[v].push_back(u);
        if(trial%10==0 && !g[0].empty())g[0].push_back(g[0][0]);
        vector<vector<int>> strategies;vector<int> selected(n,-1);
        auto enumerate=[&](auto&& self,int v)->void{
            if(v==n){strategies.push_back(selected);return;}
            if(g[v].empty()){selected[v]=-1;self(self,v+1);}
            else for(int u:g[v]){selected[v]=u;self(self,v+1);}};
        enumerate(enumerate,0);
        auto run=[&](int start,const vector<int>& first,const vector<int>& second){
            vector<bool> seen(2*n);int v=start,turn=0;
            while(true){if(g[v].empty())return turn==0 ? -1 : 1;
                if(seen[2*v+turn])return 0;seen[2*v+turn]=true;
                v=(turn==0 ? first[v] : second[v]);turn^=1;}
        };
        auto result=classify_normal_graph_game(g);
        for(int start=0;start<n;++start){bool first_forces=false,second_forces=false;
            for(const auto& s:strategies){bool all=true;for(const auto& t:strategies)
                if(run(start,s,t)!=1){all=false;break;}if(all){first_forces=true;break;}}
            for(const auto& t:strategies){bool all=true;for(const auto& s:strategies)
                if(run(start,s,t)!=-1){all=false;break;}if(all){second_forces=true;break;}}
            assert(!(first_forces && second_forces));
            int expected=first_forces ? 1 : second_forces ? -1 : 0;
            assert(result[start]==expected);
        }
    }
    assert((classify_normal_graph_game({{0}})==vector<int>{0}));
    assert((classify_normal_graph_game({{0,1},{}})==vector<int>{1,-1}));
    assert((classify_normal_graph_game({{1,1},{}})==vector<int>{1,-1}));
''',
'tree-cut-grundy': r'''
    for(int trial=0;trial<450;++trial){int n=1+rng()%11;vector<vector<int>> g(n);
        for(int v=1;v<n;++v){int u=rng()%v;g[v].push_back(u);g[u].push_back(v);}
        int root=rng()%n;vector<int> parent(n,-1),order{root};
        for(int i=0;i<n;++i)for(int u:g[order[i]])if(u!=parent[order[i]]){parent[u]=order[i];order.push_back(u);}
        vector<unsigned> removed(n);for(int i=n-1;i>=0;--i){int v=order[i];removed[v]|=1u<<v;if(parent[v]>=0)removed[parent[v]]|=removed[v];}
        map<unsigned,int> memo;
        auto brute=[&](auto&& self,unsigned live)->int{
            if(memo.count(live))return memo[live];set<int> found;
            for(int v=0;v<n;++v)if(v!=root && (live>>v&1))found.insert(self(self,live&~removed[v]));
            int value=0;while(found.count(value))++value;return memo[live]=value;};
        assert(rooted_cut_grundy(g,root)==brute(brute,(1u<<n)-1));
    }
    vector<vector<int>> path(100000);for(int v=1;v<(int)path.size();++v){path[v-1].push_back(v);path[v].push_back(v-1);}
    assert(rooted_cut_grundy(path)==99999);
''',
'divisor-game-prime-count': r'''
    map<vector<int>,bool> memo;
    auto brute=[&](auto&& self,vector<int> a)->bool{
        if(memo.count(a))return memo[a];
        for(int i=0;i<(int)a.size();++i)for(int d=1;d<a[i];++d)if(a[i]%d==0){auto b=a;b[i]=d;
            if(!self(self,b))return memo[a]=true;}
        return memo[a]=false;};
    for(int a=1;a<=15;++a)for(int b=1;b<=15;++b)for(int c=1;c<=6;++c)
        assert(divisor_game_first_wins({a,b,c})==brute(brute,{a,b,c}));
    assert(!divisor_game_first_wins({4,6}));assert(!divisor_game_first_wins({2,3}));
    assert(divisor_game_first_wins({65536}));assert(!divisor_game_first_wins({1}));
''',
'weighted-board-terminal-minimax': r'''
    const int lines[8][3]={{0,1,2},{3,4,5},{6,7,8},{0,3,6},{1,4,7},{2,5,8},{0,4,8},{2,4,6}};
    for(int trial=0;trial<35;++trial){array<long long,9> w;for(auto& x:w)x=(long long)(rng()%15)-7;
        if(accumulate(w.begin(),w.end(),0LL)%2==0)++w[0];
        auto brute=[&](auto&& self,array<int,9> board,int turn,long long difference)->int{
            for(auto& line:lines)if(board[line[0]] && board[line[0]]==board[line[1]] && board[line[0]]==board[line[2]])return board[line[0]]-1;
            if(count(board.begin(),board.end(),0)==0)return difference>0 ? 0 : 1;
            for(int i=0;i<9;++i)if(board[i]==0){auto b=board;b[i]=turn+1;
                if(self(self,b,turn^1,difference+(turn==0 ? w[i] : -w[i]))==turn)return turn;}
            return turn^1;
        };
        assert(weighted_tictactoe_winner(w)==brute(brute,{},0,0));
    }
    assert(weighted_tictactoe_winner({0,0,0,0,1,0,0,0,0})==0);
    assert(weighted_tictactoe_winner({-1,1,0,-4,-2,-5,-4,-1,-5})==1);
    assert(weighted_tictactoe_winner({1000000000,1000000000,1000000000,1000000000,1000000000,1000000000,1000000000,1000000000,999999999})==0);
''',
'grundy-conserved-state-bound': r'''
    map<pair<int,int>,int> single;
    auto grundy=[&](auto&& self,pair<int,int> state)->int{
        if(single.count(state))return single[state];auto [w,b]=state;set<int> values;
        if(w)values.insert(self(self,{w-1,b+w}));
        for(int k=1;k<=b/2;++k)values.insert(self(self,{w,b-k}));
        int value=0;while(values.count(value))++value;return single[state]=value;};
    vector<pair<int,int>> states;for(int w=0;w<=5;++w)for(int b=0;b<=10;++b)states.push_back({w,b});
    auto results=stone_pair_grundies(states);for(int i=0;i<(int)states.size();++i)assert(results[i]==grundy(grundy,states[i]));
    map<vector<pair<int,int>>,bool> memo;
    auto play=[&](auto&& self,vector<pair<int,int>> heaps)->bool{
        if(memo.count(heaps))return memo[heaps];
        for(int i=0;i<(int)heaps.size();++i){auto [w,b]=heaps[i];
            if(w){auto next=heaps;next[i]={w-1,b+w};if(!self(self,next))return memo[heaps]=true;}
            for(int k=1;k<=b/2;++k){auto next=heaps;next[i]={w,b-k};if(!self(self,next))return memo[heaps]=true;}}
        return memo[heaps]=false;};
    for(int trial=0;trial<180;++trial){vector<pair<int,int>> heaps;for(int i=0;i<3;++i)heaps.push_back({int(rng()%3),int(rng()%5)});
        int value=0;for(int x:stone_pair_grundies(heaps))value^=x;assert((value!=0)==play(play,heaps));}
    auto big=stone_pair_grundies({{50,50},{0,50},{50,0}});assert(big.size()==3);
''',
'pair-removal-mask-game': r'''
    for(int trial=0;trial<400;++trial){int n=rng()%9;vector<pair<long long,long long>> a(n);
        for(auto& [x,y]:a){x=rng()%4;y=rng()%4;}
        auto brute=[&](auto&& self,vector<pair<long long,long long>> cards)->bool{
            for(int i=0;i<(int)cards.size();++i)for(int j=i+1;j<(int)cards.size();++j)
                if(cards[i].first==cards[j].first || cards[i].second==cards[j].second){auto next=cards;next.erase(next.begin()+j);next.erase(next.begin()+i);
                    if(!self(self,next))return true;}
            return false;};
        assert(pair_removal_first_wins(a)==brute(brute,a));
    }
    assert(!pair_removal_first_wins({{1,9},{2,5},{4,9},{1,4},{2,5}}));
    vector<pair<long long,long long>> same(18,{1,1});assert(pair_removal_first_wins(same));
''',
'interactive-tree-diameter': r'''
    for(int trial=0;trial<500;++trial){int n=1+rng()%50;vector<vector<pair<int,long long>>> g(n);
        for(int v=1;v<n;++v){int u=rng()%v;long long w=1+rng()%1000000;g[u].push_back({v,w});g[v].push_back({u,w});}
        vector<vector<long long>> d(n,vector<long long>(n));long long maximum=0;
        for(int start=0;start<n;++start){queue<int> q;vector<bool> seen(n);q.push(start);seen[start]=true;
            while(!q.empty()){int v=q.front();q.pop();for(auto [u,w]:g[v])if(!seen[u]){seen[u]=true;d[start][u]=d[start][v]+w;maximum=max(maximum,d[start][u]);q.push(u);}}}
        int calls=0;auto ask=[&](int a,int b){assert(a!=b && 0<=a && a<n && 0<=b && b<n);++calls;return d[a][b];};
        assert(diameter_from_distance_queries(n,ask)==maximum);assert(calls==2*(n-1));
    }
    // Equal farthest distances and zero-weight edges remain valid tree metrics.
    for(int n=2;n<=12;++n)for(int weight:{0,1,7}){
        int calls=0;auto star=[&](int a,int b){assert(a!=b);++calls;return 1LL*weight*((a==0 || b==0)?1:2);};
        long long expected=weight*(n==2?1LL:2LL);
        assert(diameter_from_distance_queries(n,star)==expected);assert(calls==2*(n-1));
    }
    int calls=0;try{diameter_from_distance_queries(50,[&](int,int){++calls;return 0LL;},97);assert(false);}catch(const invalid_argument&){}assert(calls==0);
''',
'interactive-fibonacci-maximum': r'''
    int largest=0;
    for(int n=1;n<=1500;++n)for(int peak=0;peak<n;++peak){
        int calls=0;vector<bool> seen(n);
        auto ask=[&](int i){assert(0<=i && i<n && !seen[i]);seen[i]=true;++calls;return 100000LL-abs(i-peak);};
        assert(fibonacci_peak_value(n,ask)==100000);assert(calls<=15);largest=max(largest,calls);
    }
    assert(largest==15);
    for(int trial=0;trial<3500;++trial){int n=1+rng()%1500,peak=rng()%n;vector<long long> a(n);a[peak]=10000000;
        for(int i=peak-1;i>=0;--i)a[i]=a[i+1]-1-rng()%100;
        for(int i=peak+1;i<n;++i)a[i]=a[i-1]-1-rng()%100;
        int calls=0;set<int> queried;auto ask=[&](int i){assert(queried.insert(i).second);++calls;return a[i];};
        assert(fibonacci_peak_value(n,ask)==*max_element(a.begin(),a.end()));assert(calls<=15);
    }
    // Equal values across opposite sides of the peak and a zero endpoint.
    for(int n=1;n<=60;++n)for(int peak=0;peak<n;++peak){
        int height=max(peak,n-1-peak),calls=0;
        auto ask=[&](int i){++calls;return 1LL*height-abs(i-peak);};
        assert(fibonacci_peak_value(n,ask)==height);assert(calls<=15);
    }
    assert(fibonacci_peak_value(1,[](int i){assert(i==0);return 0LL;})==0);
    int calls=0;try{fibonacci_peak_value(1500,[&](int){++calls;return 1LL;},14);assert(false);}catch(const invalid_argument&){}assert(calls==0);
''',
'interactive-missing-rook': r'''
    for(int n=1;n<=12;++n)for(int row=0;row<n;++row)for(int col=0;col<n;++col){
        vector<int> columns;for(int c=0;c<n;++c)if(c!=col)columns.push_back(c);shuffle(columns.begin(),columns.end(),rng);
        vector<pair<int,int>> placed;int at=0;for(int r=0;r<n;++r)if(r!=row)placed.push_back({r,columns[at++]});
        int calls=0;auto ask=[&](int a,int b,int c,int d){assert(0<=a && a<b && b<=n && 0<=c && c<d && d<=n);++calls;int count=0;
            for(auto [r,k]:placed)count+=a<=r && r<b && c<=k && k<d;return count;};
        assert((find_missing_rook(n,ask)==pair<int,int>{row,col}));assert(calls<=20);
    }
    for(int n:vector<int>{13,99,100,999,1000})for(int i=0;i<100;++i){int row=rng()%n,col=rng()%n,calls=0;
        auto ask=[&](int a,int b,int c,int d){++calls;
            if(c==0 && d==n)return b-a-(a<=row && row<b);
            assert(a==0 && b==n);return d-c-(c<=col && col<d);};
        assert((find_missing_rook(n,ask)==pair<int,int>{row,col}));assert(calls<=20);
    }
    int calls=0;bool refused=false;try{find_missing_rook(INT_MAX,[&](int,int,int,int){++calls;return 0;});}catch(const invalid_argument&){refused=true;}assert(refused && calls==0);
    bool stopped=false;try{find_missing_rook(10,[](int,int,int,int){return -1;});}catch(const runtime_error&){stopped=true;}assert(stopped);
''',
'interactive-bit-group-testing': r'''
    for(int n=1;n<=100;++n){auto groups=binary_test_groups(n);int m=groups.size();assert((1<<m)>=n);if(m)assert((1<<(m-1))<n);
        set<string> patterns;
        for(int bad=0;bad<n;++bad){string response;
            for(const auto& group:groups){assert(is_sorted(group.begin(),group.end()));assert(adjacent_find(group.begin(),group.end())==group.end());
                response+=find(group.begin(),group.end(),bad)==group.end() ? '0' : '1';}
            assert(patterns.insert(response).second);assert(decode_binary_test(n,response)==bad);
        }
    }
    for(string bad:vector<string>{"","2","111"}){bool caught=false;try{decode_binary_test(3,bad);}catch(const invalid_argument&){caught=true;}assert(caught);}
    bool caught=false;try{decode_binary_test(3,"11");}catch(const invalid_argument&){caught=true;}assert(caught);
'''
}

def check(case):
    identifier, body = case
    document = (ROOT / f'src/content/docs/techniques/{identifier}.mdx').read_text()
    snippets = re.findall(r'```cpp\n(.*?)\n```', document, re.S)
    assert len(snippets) == 1, identifier
    published = snippets[0]
    includes = '\n'.join(line for line in published.splitlines() if line.startswith('#include'))
    implementation = '\n'.join(line for line in published.splitlines() if not line.startswith('#include'))
    with tempfile.TemporaryDirectory(prefix='flowchartcp-games-') as directory:
        source = Path(directory) / 'case.cpp'
        binary = Path(directory) / 'case'
        source.write_text(includes + '\nnamespace tested {\n' + implementation + '\n}\n' + COMMON + body + '\n}\n')
        result = subprocess.run([os.environ.get('CXX', 'g++'), '-std=c++20', '-O2', '-Wall', '-Wextra', str(source), '-o', str(binary)], capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, f'{identifier} compile FAIL\n{result.stderr}'
        result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, f'{identifier} FAIL\n{result.stderr}'
    return f'{identifier} PASS'

if __name__ == '__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        for output in executor.map(check, CASES.items()):
            print(output, flush=True)
