#include <cassert>
#include <iostream>
#include <limits>
#include <numeric>
#include <set>
#include <tuple>

using namespace triplet_packing;
using namespace std;
long long boards_checked=0, subsets_checked=0, legal_states=0, transitions_checked=0;
long long search_checks=0, search_hits_optimum=0;
using Key=tuple<int,char,array<int,3>>;
struct Reference {
    vector<Key> keys;
    vector<uint64_t> masks;
};

// Independent enumeration starts at a P endpoint and walks toward a G endpoint.
Reference enumerate_reference(const Board& b) {
    int h=int(b.size()),w=int(b[0].size());
    Reference result;
    for(int r=0;r<h;++r) for(int c=0;c<w;++c) if(b[r][c]=='P')
        for(int vr=-1;vr<=1;++vr) for(int vc=-1;vc<=1;++vc) {
            if(vr==0 && vc==0) continue;
            int rr=r+2*vr,cc=c+2*vc;
            if(rr<0 || rr>=h || cc<0 || cc>=w) continue;
            if(b[r+vr][c+vc]!='W' || b[rr][cc]!='G') continue;
            int center=(r+vr)*w+c+vc;
            char symbol=vr==0?'-':vc==0?'|':vr*vc>0?'\\':'/';
            array<int,3> cells{r*w+c,center,rr*w+cc};
            sort(cells.begin(),cells.end());
            result.keys.emplace_back(center,symbol,cells);
        }
    sort(result.keys.begin(),result.keys.end());
    assert(adjacent_find(result.keys.begin(),result.keys.end())==result.keys.end());
    for(const auto& [center,symbol,cells]:result.keys) {
        (void)center;(void)symbol;
        uint64_t mask=0;
        for(int cell:cells) mask|=uint64_t(1)<<cell;
        result.masks.push_back(mask);
    }
    return result;
}

Key candidate_key(const Triplet& t) {
    auto cells=t.cell;sort(cells.begin(),cells.end());
    return {t.center,t.symbol,cells};
}

// Rebuild occupancy and score from independently enumerated reference masks.
void audit_state(const Model& m,const Reference& ref,const vector<int>& mapping,const Packing& p) {
    vector<int> reconstructed(m.rows*m.cols,-1);
    auto ids=p.ids();
    for(int id:ids) {
        uint64_t mask=ref.masks[mapping[id]];
        for(int cell=0;cell<m.rows*m.cols;++cell) if((mask>>cell)&1) {
            assert(reconstructed[cell]==-1);reconstructed[cell]=id;
        }
    }
    assert(p.owners()==reconstructed);
    assert(p.score()==int(ids.size()));
    assert(validate_output(m,p.output())==p.score());
    assert(Packing(m,ids_from_output(m,p.output()))==p);
}

void check_move(const Model& m,const Reference& ref,const vector<int>& mapping,Packing& p,int id) {
    auto before=p;
    vector<int> expected=before.ids();
    auto at=find(expected.begin(),expected.end(),id);
    if(at!=expected.end()) expected.erase(at);
    else {
        erase_if(expected,[&](int other){return (ref.masks[mapping[other]]&ref.masks[mapping[id]])!=0;});
        expected.push_back(id);sort(expected.begin(),expected.end());
    }
    auto change=p.apply(id);
    auto after=p;
    assert(p.ids()==expected);
    assert(change.delta==int(expected.size())-before.score());
    audit_state(m,ref,mapping,p);
    p.undo(change);
    assert(p==before && p.output()==before.output());
    auto repeated=p.apply(id);
    assert(repeated.added==change.added && repeated.removed==change.removed &&
           repeated.size==change.size && repeated.delta==change.delta && p==after);
    p.undo(repeated);
    assert(p==before);
    ++transitions_checked;
}

// Slow independent search: scan all selected candidates for every conflict and
// copy the complete selection at every improvement. Match the random stream.
vector<int> slow_search(const Reference& ref,const vector<int>& mapping,int iterations,
                        uint64_t seed,const vector<int>& initial={}) {
    int m=int(mapping.size());
    vector<int> chosen(m,0);
    for(int id:initial) chosen[id]=1;
    if(m==0) return {};
    mt19937_64 random(seed);
    vector<int> order(m);iota(order.begin(),order.end(),0);
    for(int i=m-1;i>0;--i) swap(order[i],order[random()%(i+1)]);
    auto overlaps=[&](int a,int b){return (ref.masks[mapping[a]]&ref.masks[mapping[b]])!=0;};
    for(int id:order) if(!chosen[id]) {
        bool free=true;
        for(int other=0;other<m;++other) if(chosen[other] && overlaps(id,other)) free=false;
        if(free) chosen[id]=1;
    }
    auto best=chosen;
    int best_score=accumulate(best.begin(),best.end(),0);
    for(int step=0;step<iterations;++step) {
        int id=int(random()%m);
        auto next=chosen;
        if(next[id]) next[id]=0;
        else {
            for(int other=0;other<m;++other) if(next[other] && overlaps(id,other)) next[other]=0;
            next[id]=1;
        }
        int score=accumulate(chosen.begin(),chosen.end(),0);
        int value=accumulate(next.begin(),next.end(),0),delta=value-score;
        double fraction=iterations<=1?0:double(step)/(iterations-1);
        double temperature=exp((1-fraction)*log(1.5)+fraction*log(0.03));
        double u=double(random()>>11)*0x1.0p-53;
        if(delta>=0 || u==0 || log(u)<delta/temperature) chosen=next;
        score=accumulate(chosen.begin(),chosen.end(),0);
        if(score>best_score) {best=chosen;best_score=score;}
    }
    vector<int> result;
    for(int id=0;id<m;++id) if(best[id]) result.push_back(id);
    return result;
}

void check_board(const Board& b,bool all_moves=true) {
    assert(b.size()*b[0].size()<=64);
    Model m(b);
    auto ref=enumerate_reference(b);
    vector<Key> actual;
    vector<int> mapping;
    for(const auto& t:m.triplets) {
        auto key=candidate_key(t);actual.push_back(key);
        auto at=lower_bound(ref.keys.begin(),ref.keys.end(),key);
        assert(at!=ref.keys.end() && *at==key);
        mapping.push_back(int(at-ref.keys.begin()));
    }
    sort(actual.begin(),actual.end());
    assert(actual==ref.keys);
    int count=int(ref.keys.size());
    assert(count<=20);
    int optimum=0;
    vector<int> optimum_ids;
    // Every subset, including illegal subsets, is considered by this oracle.
    for(uint64_t subset=0;subset<(uint64_t(1)<<count);++subset) {
        ++subsets_checked;
        uint64_t occupied=0;bool legal=true;int score=0;
        for(int j=0;j<count;++j) if((subset>>j)&1) {
            if(occupied&ref.masks[j]) {legal=false;break;}
            occupied|=ref.masks[j];++score;
        }
        if(!legal) continue;
        ++legal_states;
        vector<int> ids;
        for(int id=0;id<int(mapping.size());++id) if((subset>>mapping[id])&1) ids.push_back(id);
        if(score>optimum) {optimum=score;optimum_ids=ids;}
        if(all_moves) {
            Packing state(m,ids);
            audit_state(m,ref,mapping,state);
            for(int id=0;id<count;++id) check_move(m,ref,mapping,state,id);
        }
    }
    uint64_t seed=0x123456789abcdef0ULL+boards_checked;
    auto greedy=anneal(m,0,seed), answer=anneal(m,160,seed);
    assert(answer.score()>=greedy.score() && answer.score()<=optimum);
    assert(answer.ids()==slow_search(ref,mapping,160,seed));
    assert(answer==anneal(m,160,seed));
    audit_state(m,ref,mapping,answer);
    auto optimal_start=anneal(m,75,seed,optimum_ids);
    assert(optimal_start.score()==optimum);
    assert(optimal_start.ids()==slow_search(ref,mapping,75,seed,optimum_ids));
    ++search_checks;
    if(answer.score()==optimum) ++search_hits_optimum;
    if(count) {
        mt19937_64 rng(seed);
        Packing walk(m);
        for(int step=0;step<50;++step) {
            int id=int(rng()%count);
            check_move(m,ref,mapping,walk,id);
            auto before=walk;
            auto change=walk.apply(id);
            if(rng()%2==0) {walk.undo(change);assert(walk==before);}
            audit_state(m,ref,mapping,walk);
        }
    }
    ++boards_checked;
}

template<class F> void rejects(F action) {
    bool caught=false;
    try {action();} catch(const invalid_argument&) {caught=true;}
    assert(caught);
}
template<class F> void io_rejects(F action) {
    bool caught=false;
    try {action();} catch(const exception&) {caught=true;}
    assert(caught);
}

int main(int argc,char** argv) {
    assert(argc==2);
    const string colors="PWG";
    for(auto [h,w]:vector<pair<int,int>>{{1,1},{1,2},{1,3},{2,2},{2,3},{3,3}}) {
        int total=1;for(int i=0;i<h*w;++i) total*=3;
        for(int encoded=0;encoded<total;++encoded) {
            int code=encoded;
            Board b(h,string(w,'P'));
            for(auto& row:b) for(char& ch:row) {ch=colors[code%3];code/=3;}
            check_board(b);
        }
    }
    mt19937_64 rng(202010152026ULL);
    int random_boards=0;
    while(random_boards<400) {
        int h=3+int(rng()%4),w=3+int(rng()%4);
        Board b(h,string(w,'P'));
        for(auto& row:b) for(char& ch:row) ch=colors[rng()%3];
        auto ref=enumerate_reference(b);
        if(ref.keys.size()>15) continue;
        check_board(b,random_boards<70);
        ++random_boards;
    }
    Model star({"PGPPP","PWPPP","PPWGP","PPGWP","PPPPP"});
    auto find_id=[&](int center,char symbol) {
        for(int i=0;i<int(star.triplets.size());++i)
            if(star.triplets[i].center==center && star.triplets[i].symbol==symbol) return i;
        assert(false);return -1;
    };
    Packing three(star,{find_id(12,'|'),find_id(6,'|'),find_id(18,'|')});
    auto before=three;
    auto change=three.apply(find_id(12,'-'));
    assert(change.size==3 && change.delta==-2 && three.score()==1);
    assert(validate_output(star,three.output())==1);
    three.undo(change);assert(three==before);

    rejects([]{Model m({});});
    rejects([]{Model m({""});});
    rejects([]{Model m({"PWG","PW"});});
    rejects([]{Model m({"P?G"});});
    rejects([]{Model m(Board(501,"P"));});
    rejects([]{Model m({string(501,'P')});});
    Model line({"PWG"}),none({"P"});
    Packing p(line);
    rejects([&]{p.apply(-1);});rejects([&]{p.apply(1);});
    rejects([&]{p.selected(-1);});rejects([&]{p.selected(1);});
    rejects([&]{Packing bad(line,{0,0});});
    rejects([&]{Packing bad(line,{1});});
    Model crossing({"PWGWP"});
    rejects([&]{Packing bad(crossing,{0,1});});
    rejects([&]{anneal(line,-1,1);});
    for(double bad:{0.,-1.,numeric_limits<double>::infinity(),numeric_limits<double>::quiet_NaN()}) {
        rejects([&]{anneal(line,1,1,{},bad,0.03);});
        rejects([&]{anneal(line,1,1,{},1.5,bad);});
    }
    rejects([&]{anneal(line,1,1,{},0.01,0.03);});
    assert(anneal(none,10,1).score()==0);
    assert(validate_output(line,{"P-G"})==1);
    rejects([&]{validate_output(line,{});});
    rejects([&]{validate_output(line,{"P-G","PWG"});});
    rejects([&]{validate_output(line,{"PG"});});
    rejects([&]{validate_output(line,{"P?G"});});
    rejects([&]{validate_output(line,{"GWP"});});
    rejects([&]{validate_output(line,{"-WG"});});
    rejects([&]{validate_output(line,{"P|G"});});
    rejects([&]{validate_output(none,{"-"});});
    Model wrong_ends({"PWP"});
    rejects([&]{validate_output(wrong_ends,{"P-P"});});
    rejects([&]{validate_output(crossing,{"P-G-P"});});
    assert(validate_output(Model({"P","W","G"}),{"P","|","G"})==1);
    assert(validate_output(Model({"PPP","PWP","PPG"}),{"PPP","P\\P","PPG"})==1);
    assert(validate_output(Model({"PPP","PWP","GPP"}),{"PPP","P/P","GPP"})==1);

    filesystem::path target=filesystem::path(argv[1])/"best.txt";
    assert(save_if_better(line,target,line.board));
    assert(read_output(target)==line.board);
    assert(save_if_better(line,target,{"P-G"}));
    assert(!save_if_better(line,target,line.board));
    assert(!save_if_better(line,target,{"P-G"}));
    rejects([&]{save_if_better(line,target,{"P|G"});});
    assert(read_output(target)==Board{"P-G"});
    auto bad_target=filesystem::path(argv[1])/"invalid.txt";
    {ofstream f(bad_target);f<<"P|G\n";}
    rejects([&]{save_if_better(line,bad_target,{"P-G"});});
    assert(read_output(bad_target)==Board{"P|G"});
    auto blocked=filesystem::path(argv[1])/"blocked.txt";
    {ofstream f(blocked.string()+".tmp");f<<"reserved\n";}
    io_rejects([&]{save_if_better(line,blocked,{"P-G"});});
    assert(read_output(blocked.string()+".tmp")==Board{"reserved"});
    io_rejects([&]{save_if_better(line,filesystem::path(argv[1])/"absent"/"out",{"P-G"});});

    Board big(500,string(500,'P'));
    for(int r=0;r<500;++r) for(int c=0;c<500;++c) big[r][c]=colors[(r+c)%3];
    Model large(big);
    auto large_a=anneal(large,30000,414141),large_b=anneal(large,30000,414141);
    assert(large_a==large_b && validate_output(large,large_a.output())==large_a.score());
    Model empty_big(Board(500,string(500,'W')));
    assert(empty_big.triplets.empty() && anneal(empty_big,100,0).score()==0);
    cout<<"PASS: grid triplet packing; endpoint oracle, all subsets, operation rollback, independent output validation, deterministic seeds, saved output and API boundaries.\n";
    cout<<"{\"boards\":"<<boards_checked<<",\"allCandidateSubsets\":"<<subsets_checked
        <<",\"legalStates\":"<<legal_states<<",\"operationChecks\":"<<transitions_checked
        <<",\"searchChecks\":"<<search_checks<<",\"searchesMatchingSmallOptimum\":"<<search_hits_optimum
        <<",\"largeCandidates\":"<<large.triplets.size()<<",\"largeScore\":"<<large_a.score()<<"}\n";
}
