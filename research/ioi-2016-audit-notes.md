# IOI2016 本競技の固定初回監査

基準日2026-10-14、調査日2026-10-15。母集団は本競技の六題であり、全世界の教材網羅完了はfalseとする。全問列挙・原典読了・解法と主要補題の確認を先に行い、その後に固定教材を照合した。今回の結論は研究6/6、具体技巧と完成APIの不足6/6、coverage0/6。研究prototypeは完成記事/APIの検証ではない。

## 選定と保存範囲

[日本委員会の公式一覧](https://www2.ioi-jp.org/ioi/2016/tasks/index.html) と [公式参加報告](https://www2.ioi-jp.org/ioi/2016/report.html) で、2016-08-14にMolecules/Railroad/Shortcut、2016-08-16にPaint/Messy/Aliensの各三題と確認した。日付は大会期間8/12〜19や練習日8/13から代用していない。各英語リンクを実際に開き、印刷されたtask IDを確認してselectionを先に保存した。Martian DNA/Laugh Analysis/Reversing a Sequence/Mini Tetrisと翻訳重複は除外した。

`/tmp/flowchartcp-ioi2016-baseline` は初回 **504MDX/471図/525walk/9既存corpus**。全core959とpublic472を同じbefore/copy/after区間で保存し、1431ファイル全てのSHAが一致した。`SHA256SUMS` のSHAは `dd7151810d712521a5f3f19c206eecb7630c3b9688575c6243dee4b170992a56`、publicを除いたcore台帳は `5c76f569d8093b743896da6498b3828d1f2ea283b6efccff34fe2ceee506ed3a`。`.env*` は列挙対象から除外し開いていない。後のvendor105は別時点の依存拡張であり、初回SVGの同時点証拠へ混ぜない。rootの後続Train等の統合を初回値へ足さない。

既存9corpusは全rawを保存済み。将来の回帰検査では、既存のresolution/subsequent reviewを含め全old keysをfreshから射影してdeep比較する。初回に存在しなかったfieldの追加だけを許す。

## 一次資料とAPIの版差

六原典と全数値・小課題配点をJSONの各recordへ保存した。数式が本文から外れて抽出された箇所も、同じPDFの後続行で全数値を確認できた。画像未読を目視済みとは記録しない。原典のgeneric型は、[Day1 Notice](https://www2.ioi-jp.org/ioi/2016/tasks/day1-notice-ISC.pdf) と [Day2 Notice](https://www2.ioi-jp.org/ioi/2016/tasks/day2-notice-ISC.pdf) によりC++のvector/int64/string/boolへ対応する。実zip/headerを取得したとは主張しない。

Moleculesの日本委員会ISC/JPN版は`int[] solve(int l,int u,int[] w)`。一方、[公式アーカイブの実Official Englishリンク](https://ioi.te.lv/locations/ioi16/contest/day1/molecules.pdf) は`Country: api - ISC`、`int[] find_subset(int l,int u,int[] w)`である。直接openはtimeoutだが、`site:ioi.te.lv/locations/ioi16 "find_subset"` のprimary indexed全文で署名と同じモデルを読める。版の公開順は未確認なので年代順の断定はしない。残り五題はJP版のgeneric APIを確認した。

全解説は [IOI公式履歴archive](https://ioi.te.lv/locations/ioi16/contest/) の実Solutionsリンク先 [IOI2016_analysis.pdf](https://ioi.te.lv/locations/ioi16/contest/IOI2016_analysis.pdf)、全17頁。印刷著者はMolecules/Messy: Shi-Chun Tsai、Railroad: Kento Nikaido、Shortcut: Gleb Evstropov、Paint: Michal Forišek、Aliens: Chethiya Abeysinghe。公式高位方針と以下の独立補足を区別する。全別解を確認済みとはしていない。

## Molecules: 任意部分集合からソート窓への存在変換

[原典](https://www2.ioi-jp.org/ioi/2016/tasks/day1-molecules-ISC.pdf): N1..200000、正のw/l/u<2^31、u−l>=maxw−minw、元添字の証拠集合を一つ返し、無ければ空。求めるのは個数や全ての和の可否ではない。

任意の解の要素数をkとする。最小k個の和はu以下、最大k個の和はl以上。ソート後の長さk窓の和を左から動かすと非減少で、各増分はw[i+k]−w[i]<=maxw−minw<=u−l。最初の和がl以上なら既に解であり、それ以外でも初めてlへ達する窓がuを飛び越すことはない。よって連続窓が十分である。正の和に対する二端点走査で窓を見つけ、値と元添字のpairで復元する。全体O(NlogN)、和は64bit。

公式p1のGreedy1はprinted `maxSum<=l` を含むが、その向きは必要条件ではない。採用はGreedy2と、上の正しい`maxSum>=l`による独立証明。制約を外した反例はw=[2,3,7],l=u=9。部分集合2+7はあるがソート連続窓にはない。

probeはN<=8/重さ1..6の全3002multiset、234228範囲を全subsetの到達和を求める独立集合DPと比較した。471040は表現されるsubset選択の母数であり、同じ和を持つ選択を重複実行した回数ではない。既存two-pointersは連続区間数、knapsackは容量添字の最大価値、bitsetは和の可否だけであり、存在変換・元添字証拠・u約21億を含む全域APIを満たさない。

## Railroad: 速度座標の平衡補正と最安接続

[原典](https://www2.ioi-jp.org/ioi/2016/tasks/day1-railroad-ISC.pdf): N2..200000、s/t1..1e9、初速1、全区間を一度ずつ好きな順で使う。次の区間jへ入るための長さはmax(0,t_i−s_j)。速度は常に正。generic `int64 plan_roller_coaster(int[] s,int[] t)`。

s_max→1の補助区間を足し、その直後で切って初速1からの順列へ戻す。各区間をs→tの必須辺とし、接続では右向きの仮想昇速を無料、左向き減速を距離分有料とする。仮想昇速は入口上限までの余裕を表すだけで、元モデルへ実加速器を追加しない。元接続のcostと抽象経路の最低costは両方向に一致する。

圧縮した隣接速度座標間のbalanceを必須右向き数−左向き数とする。閉路では各方向のcut通過数が同じなので、正balanceには同数の有料左向き、負balanceには無料右向きを追加する必要がある。必要費用max(balance,0)*gapは下界。全cutを0にすると各頂点の入出次数が一致する。

必須辺と非ゼロ補正でDSUを併合する。残る成分はzero-balance区間に双方向を加えて接続し、その有料分がgapとなる。任意の接続augmentationから縮約上の連結辺集合が必要なためMSTが下界。Kruskalで選んだ隣接区間を双方向に入れれば平衡と弱連結が同時に成立し、Euler閉路が作れる。下界を達成するO(NlogN)手順である。

probeは速度1..3/N2..4の全7371配列と160乱択を、literal全1174270区間順列と比較した。既存Euler APIは既に与えられた辺での経路だけを作り、辺追加費用は求めない。例えば(1,2)二本と補助(2,1)はそのままEuler閉路にならないが、原典答えは1。DSU/hub帰着も必要な補正費用を導かない。

## Shortcut: 悪い駅対の四境界と自己組の除外

[原典](https://www2.ioi-jp.org/ioi/2016/tasks/day1-shortcut-ISC.pdf): N2..1000000、主辺l1..1e9、各枝d0..1e9、新辺c1..1e9。異なる主駅間へ一本追加し、元の全主駅・枝先間の直径を最小にする。隣接二駅も合法。generic `int64 find_shortcut(int n,int[] l,int[] d,int c)`。

主駅座標xは狭義増加。i<j、端点y<zに対して通常向きの経由距離は逆向き以下なので、新辺を使うならd_i+d_j+c+|x_i−y|+|x_j−z|でよい。元の距離d_i+d_j+x_j−x_iがK以下の組は制約を加えない。それより大きい悪い組だけを、新辺でK以下へ縮める。

`a_i=x_i−d_i,b_i=x_i+d_i`、S=y+z、D=z−yとすると、各悪い組の必要十分条件は

- b_i+b_j+c−K <= S <= a_i+a_j+K−c
- b_j−a_i+c−K <= D <= a_j−b_i+K−c

となる。新辺長cを全四式に含める。原典の自己駅に高々一枝という条件から、i=iを2d_iの組として課さない。

異なる枝先の距離はd_i+d_j以上なので、Kが最大二枝長の和より小さければ不可能。この必要条件を満たした後は、i>jならb_j−a_i=d_i+d_j−(x_i−x_j)<Kでありeligibleにならない。よって`a_i<b_j−K`を満たす全iから自己i=jだけを外せば、ちょうど元のi<jの悪い組となる。

b_j昇順でjを走査し、a_i昇順のpointerでeligibleを加える。min a/max bそれぞれ異なる添字の最良二個を保存すれば、自己jを外した極値が定数時間で得られる。四式はこの二極値だけで全組のintersectionへ集約できる。二つのsortはKに依存しないので一度だけ行う。

集約したS/D境界に対しDlo=max(Dlo,1)とする。y=x_aに対するzの下限はmax(Slo−y,y+Dlo)、上限はmin(Shi−y,y+Dhi)。下限はV字で、最小の候補zの位置は高々一度だけ減少から増加へ切り替わる。z>yを守るpointerで全yの存在判定がO(N)。元の木の直径は十分な上限なので、整数Kの二分によりO(NlogN+NlogDiameter)となる。

このself除外とtop-two枝長下界は、公式sort/two-pointers方針の独立補足。公式の別dominance-filter解法は未確認の別手順として保持した。probeでは各新辺候補を実際の主駅/枝先graphへ追加してFloydするliteral oracleと、quadratic全悪い組/linear extremaの二判定を比較した。全小1548ネットワーク＋1800乱択、21861閾値が一致。長い一本の枝[100,0]も自己組で誤排除しない。最大原典の本番C++実装時間は未検証であり完成API0へ数える。

## Paint: 全解で共通の色を前後可否から決める

[原典](https://www2.ioi-jp.org/ioi/2016/tasks/day2-paint-ISC.pdf): N<=200000、K<=100かつK<=N、各clue1..N。入力X/_/.、出力X/_/?。黒blockの長さ・順序は固定、block間に少なくとも白一つが必要。少なくとも一解が保証される。generic `string solve_puzzle(string s,int[] c)`。

F[t][j]を先頭jマスに最初t個のblockを置けるかとする。末尾が白にできる場合と、末尾に長さc[t−1]の黒blockを置く場合で完全に分割できる。後者ではblock内に既知白がなく、その直前が白にでき、残るprefixがt−1個で実現できる必要十分条件を使う。逆列・逆clueでsuffix側も同じ表を作る。

位置vを白にできるのは、既知黒でなく、あるtについて左prefixにt個/右suffixにK−t個を置ける場合。白が左右のseparatorとなる。block tを[a,b)に置けるなら、内側の既知白なし・外側二隣が白可能・前後の表が成立する。全合法block区間を差分へ加えて、黒になれる位置のunionをO(NK)で得る。解存在保証により白/黒どちらかは必ず可能で、両方なら?。

全N<=8のbinary解と既知マスクから、同じclue/partial rowへ対応する全解をliteralに合成した。62701観測、86870 full-solution/reveal pairsが前後DPと一致。既存state-designの掲載APIは偶奇BFS、Hirschbergは一つのLCSであり、同じ前後DPという名前だけでは全解必須色APIにならない。将来は矛盾入力のAPI契約、byte表の領域・最大実行・ASanを別途要する。

## Messy: compile前の署名設計と後の所属判定

[原典](https://www2.ioi-jp.org/ioi/2016/tasks/day2-messy-ISC.pdf): Nは2冪、採点ケースは8/32/128。満点はN128でwrite/read各896。全write→compile一回→全readの順で、pは呼出し前に固定。compile後のbit iはcompile前のbit p[i]である。generic `int[] restore_permutation(int n,int w,int r)`、library add_element(string)/compile_set()/check_element(string)。

size mの原位置区間について外を1、内を0とし、左半分の一位置だけ1へするm/2個のsignatureをあらかじめ書く。深さが違うと重みN−m+1が違う。同じ深さの別区間はzero supportの所属区間が異なるため一致しない。size1ではsignatureを書かない。

compile後、ある原区間に対応する出力位置集合が分かっているとする。その集合内を0、外を1にし、候補一点だけ1にして所属判定すると、その点の元位置が左半分にある場合に限ってtrueとなる。左右を再帰的に分け、葉でanswer[outputPosition]=originalIndexとする。逆置換を返す間違いを避ける。

levelごとにwrites N/2、reads N、深さlog2Nなので、N128で448/896、N32で80/160。非対称の320/1024と1024/320も含む全採点予算を満たす。長さNの文字列生成はO(N²logN)でありoracle call数O(NlogN)と別に数える。全40347置換(N1,2,4,8、うち1/2/4は一般化)と元制約32/128の400乱択をliteral compileで比較した。

既存interactiveへotherで到達するが、掲載ask_intervalはstdin/stdoutであり、この原典Noticeではstdio禁止。bit group testingは不良一個の識別で、全置換でもcompile phaseでもない。generic記事への到達は初回coverageを変えない。

## Aliens: 重複面積の補正、Mongeと離散凸性

[原典](https://www2.ioi-jp.org/ioi/2016/tasks/day2-aliens-ISC.pdf): N1..100000、M1..1e6、K1..N、各座標0..M−1。点は重複可。対角線上の二頂点を持つcell-aligned正方形を高々K枚選び、全要求セルを含むunionセル数を最小にする。generic `int64 take_photos(int n,int m,int k,int[] r,int[] c)`。

要求セル(r,c)をinterval[min(r,c),max(r,c)]へ移す。含まれる要求を消すと、残るL/Rはともに狭義増加する。写真の包含を消して順に並べ、各写真へ連続した要求群を担当させる。その写真は群の最初L〜最後Rへ縮められる。以前の写真unionと新写真の共通部分は、最後の写真との共通部分に一致する。その辺長はmax(0,R_t−L_{t+1}+1)なので、t以降の新群をiまで撮る増分は

W(t,i)=(R_i−L_{t+1}+1)^2−max(0,R_t−L_{t+1}+1)^2

である。t=0の重複項は0とする。面積和だけのDPではない。

a<=b<c<=dについて、二乗展開により

W(a,c)+W(b,d)−W(a,d)−W(b,c) = −2(L_{b+1}−L_{a+1})(R_d−R_c) <=0。

重複減算は出発点ごとの項なので相殺する。離散凸性の証明は次の独立補足を使う。q−1辺のpartition path Pとq+1辺のQの内部cutを昇順に読む。Qのcut数−Pのcut数が初めて2になるQcutをdとする。直前Qcut bと直前/次のPcut a,cはa<=b<d<=cで、prefix辺数はQが一つ多い。P辺a→cとQ辺b→dのsuffixを交換し、a→dとb→cへつなぐと、両方q辺となる。元の二辺はnested、新しい二辺はcrossingで、上のMonge不等式を順序a,b,d,cへ適用すると合計費用は増えない。共通頂点ならその頂点でsuffixを交換すれば同じ結論。従って2F(q)<=F(q−1)+F(q+1)。

一群を二つに分けた写真は元写真内に収まりunionを増やさないのでFは非増加でもある。枚数を一つ増やす節約差は非増加の整数。罰金lambdaを整数で動かし、同値なら少数枚を選ぶと、初めて枚数<=Kとなる境界でKも罰金問題の最適枚数に含まれる。従ってG(lambda)−lambda*KがF(K)。Kは包含除去後の群数へclampし、K1もこの境界で扱える。

Wを展開すれば傾き−2(L_t−1)、切片DP[t]+(L_t−1)^2−overlap_t²+lambdaの直線となる。Lが増加/Rが増加なので、追加傾き減少/問い合わせ増加のCHTで罰金一回O(N)。費用/少数枚tieはH=N+1倍して下位へ枚数をencodeしてもよい。面積<=M²、罰金<=M²、prefix罰金最適値<=2M²を使えばscaled値は64bit内、交点積は128bit内に収められる。原典全域の具体C++/契約/最大実行は未作成。

実際の全正方形セル集合のunion bitmaskをliteral oracleとし、M1..4の全1094非empty要求interval集合、候補photo subset437(高々M枚で十分)、1400乱択を、overlap DP・単調CHT・罰金境界と比較した。同名aliens-trickはsolve callback付きwrapperだけ、exact-count APIは隣接禁止位置選択、既存CHT/Li Chaoはscalar直線componentであり、これらをphoto全域APIと呼ばない。Editorialの小課題Knuth等は別の未確認手順として保持する。

## 初回経路と照合

独立JSON walkerと、凍結した実flow.tsを別epoch vendor/compilerで変換したwalkFromRootが、六経路の全question/answerLabel/target/stop/optionsで一致した。15根を検討し、初回canonicalは入力の場面が最も直接表れるものを選ぶ。

- Molecules: ranges → selected-elements、range-selected-elements/updates質問で停止。
- Railroad: graphs → walk-goals、graphs-walk-goals/shortest質問で停止。全区間の順序と追加接続費用は単一最短路と異なり、既存all-edgesの固定始終点・既存辺だけという条件にも合わない。
- Shortcut: graphs → network-connection、graphs-network-connection/shortest質問で停止。接続費用/MSTと直径最小化は異なる。
- Paint: dp → sequence-removals → split、dp-sequence-removals/split-kind質問で停止。黒blockK個と白gapを含む全列のK区間分割を混同しない。
- Messy: interactive-oracles → other、general-resultのinteractiveへ到達。gapも実際のresultへ合わせ、将来のbranchAtだけを元responseへ別保存。
- Aliens: geometry → enclosing-regions → point-set-shapes、point-set-shape-features/goal質問で停止。DP/CHT経由の一般名を原典特徴の直接経路と混同しない。

全19unique関連MDXを全文・全CPPまで読み、raw/CPP/metadata元ファイルのSHAを保存した。全19実fenceを改変せずnamespace内で同じC++ harnessへ組み込み、18component呼出しと1protocol compile-only検査を実行した。これは既存教材が誤りという検査でも、原典の完成APIを再検証したという主張でもない。`/tmp/flowchartcp-ioi2016-scope-checks.json` がscope反例とSHAの補助記録。親による独立レビュー前の登録案は六gap全てpendingのままで、完成article/ref/walk/resolutionを作らない。

## 手動再現と残る実装作業

- 数学研究: `python3 /tmp/flowchartcp-ioi2016-probe.py /tmp/flowchartcp-ioi2016-probe-rerun.json`
- raw walker: `python3 /tmp/flowchartcp-ioi2016-replay.py`
- 凍結実runtime照合: `node /tmp/flowchartcp-ioi2016-runtime-replay.mjs`
- 凍結実CPP scope: `python3 /tmp/flowchartcp-ioi2016-scope-checks.py`

probeは手動実行のみで、収集コマンドや定期実行へ追加していない。元のBooks三成果物も変更しない。今後の技巧完成は各題で自然な日本語記事/完全C++20/原典全域API/独立oracle/最大/不正/多重call/通常ASan/別担当review/特徴rootwalk/referenceを揃え、初回record/statusを保持してresolutionだけを追加する。


## 登録時の保存範囲と再現コマンド

初回rawのnotes/audit/proposalはそのまま別gzipへ保存した。登録版では初回1431raw（core959＋同時点public472）を全て永久保存し、504記事の全MDXも含める。原案の近接19記事だけの保存より広い。後時点vendor105は別archive/別epochであり初回図の同時点証拠へ混ぜない。`research/snapshots/ioi-2016-manifest.json` が全rawと保存形式を記録する。Railroadの上記「s_max」は `max_i max(s_i,t_i)` を意味する。audit/probe本体の式と同じで、入口sだけの最大値ではない。

- 数学研究: `python3 research/probes/ioi-2016-research-checks.py [optional-new-output.json]`
- 独立raw経路: `python3 research/probes/ioi-2016-root-replay.py`
- 凍結実runtime: `node research/probes/ioi-2016-frozen-runtime.mjs`
- 凍結19実CPPのscope: `python3 research/probes/ioi-2016-frozen-scope.py`
- 別担当の補助検証: `python3 research/probes/ioi-2016-independent-checks.py`

各コマンドは永久archiveから一時フォルダへ元bytesを復元し、初回1431と別epoch105の各SHAを照合する。数学計数・6根経路・19実fenceの意味は初回と同じ。既定では標準出力のみで、収集や定期実行へつないでいない。初回研究6/6・完成API0/6・記事対応0/6を後続の実装で遡及更新しない。
