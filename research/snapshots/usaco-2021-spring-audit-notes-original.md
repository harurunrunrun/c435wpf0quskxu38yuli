# USACO 2021 February・US Open Platinum 固定6題の監査メモ

対象は公式結果一覧のPlatinum各1〜3題のみ。既存の2020 December・2021 January群とは別に先行固定した。技巧や既存記事との相性による差し替えはしていない。問題本文は転載せず、条件・主要補題・教材の不足を記録する。

## 凍結教材と順序

- snapshot: `/tmp/flowchartcp-usaco2021-spring-snapshot`
- 初回488 metadata / 488 MDX / 455図 / 509 walks / 509 references。親の後続Doll・Highway・Meetings追加はこの初回値に反映しない。
- 全620 rawのSHAをcopy前・copy内容・copy後で一致確認。`SHA256SUMS`、`hashes-before.json`、`hashes-after.json`、`manifest.json`を保持。
- flow SHA: `8e65013cc25d38030aed330d1f08d812f25cedd7dc78e33990386e03f238d256`
- walk SHA: `6a2fbef69e87ea9ae44c8b19d281c46c478293cdee4c80897ee32e7b3ee3ce90`
- raw台帳 SHA: `94fe3a533a7bea30ceab38e0134388265176d409c2ee414cfa5b1e7b4ea65b5c`

公式2一覧の全6題名列挙→ID先行固定→全6原典の全文/数値→全6公式解説の選んだ満点手順と主要補題→研究probe→凍結教材のscope比較/特徴からのraw経路、の順で確認した。ID解決の検索結果には原典の断片が出たが、その段階を全文確認済みとしなかった。

全15分野根の質問を確認して最も自然な根を選んだ。単に近いアルゴリズム名へ誘導せず、該当回答のない最初の質問で止めた。全488 metadataを検索し、凍結全MDXを特徴語で調べ、近接記事の使う場面・適用条件・証明・APIを精読した。488本文を全て逐語精読したという主張ではない。

## 原典の固定と日付精度

|大会|番号・ID・原題|日付の一次確認精度|
|---|---|---|
|[2021 February公式一覧](https://usaco.org/index.php?page=feb21results)|1:1116 No Time to Dry / 2:1117 Minimizing Edges / 3:1118 Counting Graphs|2021-02、正確な開始/終了日は未確認|
|[2021 US Open公式一覧](https://usaco.org/index.php?page=open21results)|1:1140 United Cows of Farmer John / 2:1141 Routing Schemes / 3:1142 Balanced Subsets|2021年、正確な月日未確認|

現在の公式sidebarは別年度の日程なので流用しない。記憶の2021日程やクロール日も採用しない。公式開催年により基準日2026-10-14以前であることは確認できる。全題のdivisionはPlatinumと確定、数値difficultyはroot指定どおりnull。Goldの同名United CowsやCodeforcesの同名Counting Graphsを混ぜない。

## 研究完了と教材未完を分ける

選んだ満点解法の主要補題は6/6確認し、独立小全探索も成功した。初回分類は **missing-technique 6 / covered 0 / missing-route 0 / unconfirmed 0**。ここでunconfirmed0は必要な原典モデル/数値/選んだ満点解法の主要補題についてであり、正確な開催日や任意の別解まで確認済みという意味ではない。

完成した再利用C++20/API・教材記事・最大ケース/native/ASan・flow/参照/feature/原典walkの追加は今回0件。researchCompleteとcoverageCompleteを同一視しない。独立研究probeは生産用の掲載APIの検証ではない。

## 問題ごとの根拠と初回停止位置

### 1116 No Time to Dry

[原典](https://usaco.org/index.php?page=viewproblem2&cpid=1116) / [公式解説](https://usaco.org/current/data/sol_prob1_platinum_feb21.html)。Analysis: Benjamin Qi。公式resultsの当該PlatinumのSolution直リンクで出自を確認。

原典の全数値・意味: `{"N": "1..200000", "Q": "1..200000", "colors": "1..N, increasing darkness", "queries": "1<=a<=b<=N, paint onlyinside range, outside remainsuncolored; queries independent", "paint": "onecontiguousinterval/color perstroke, no lighteroverdarker"}`。

**特徴からの初回経路**: `ranges`。
- `ranges/updates`: 数列について、何を求めますか？ → `aggregate-goals`「連続する区間・利用期間・開催日の得点を集計する」
- `range-aggregate-goals/updates`: 数列について、何を求めますか？ → `static`「変わらない配列の指定区間を集計する」

停止: `range-static/kind` (question)「変わらない配列から何を求めますか？」。その時点の回答labelは以下。
- `occurrence-goals`: 値の出現・区間内の順位・条件を満たす部分列数
- `aggregate-forms`: 最小最大・並べ替えた一致・全加算後の値
- `sum`: 指定区間の和・XOR
- `iterate`: 同じ移動を K 回繰り返した位置
- `unknown`: わからない

不足回答案: 「指定区間だけを濃い色で上書きできるとき、完成までの最小筆数を多数回求める」。不足技巧ID: `monotone-paint-stroke-links-offline-containment`。

不足理由: 固定配列の区間集計には到達するが、順序付き色の上書き最小回数という回答がない。等値対の最短距離・種類数・一般offlineでは、間に小さい色がない同色リンクと筆数の同値を説明できない。

**確認した満点手順**: 等色A_l=A_rで内部が全て厳密に大きい対を単調stackでO(N)個生成する。一区間の最小筆数は長さ−区間内に両端を含むそのリンク本数。質問を右端で走査し、閉じたリンクを左端へ+1記録してFenwick区間和を引く。

- 同色を一筆で結べるのは、その間により薄い最終色がないとき。より薄い位置を濃く塗ると後から戻せないので、こうした障害をまたぐ同色出現は別の筆を必要とする。
- 有効な同色リンクは各色の連続出現を結ぶ鎖であり、成分ごとに薄い色から一筆ずつ塗れば実現できる。制限区間でも内部リンクだけの森林となり、必要十分な筆数は頂点数−辺数。
- stackから新色より大きい色をpopし、topが等しければリンクを一つ生成してtopを最新位置へ置換。等値を二重保持しないため内部の厳密大と空の内部の両方を扱う。
- 右端rまでに閉じた全リンクの左端へ+1する。左端L以上の記録数は、両端が[L,r]内にあるリンク数そのもの。

計算量: O((N+Q)logN)時間、O(N+Q)空間。質問を右端bucketに入れればQlogQは不要。筆数<=区間長。

近接旧記事のscope差分（全て凍結SHA）:
- `offline-range-equal-gap` / `82c58765fe9ee4b6db49aec8f49f6d5a6c3130c3fc574b675d8d2c51c0ddca5b`: 全ての連続同値出現対を最短距離の候補にする記事。ここでは間により小さい色がある対を除外し、有効リンクの本数から筆数を求める。
- `subarray-extremum-contribution` / `02c2260416e06ab697b9eac3c5bba5c80a2eba8f1c769a6fe7f5e1df51c19833`: 単調stackで極値の担当範囲を求めるが、同色を結ぶbrush成分と多数区間の内包リンク数は扱わない。
- `grid-rectangle-components-euler-boundary` / `9df245577b10bfe299b45b07200d99334d4a78a7344e4dbf25d243e2525c4a8a`: 静的二次元の上書きなし同色成分。原典は一次元で濃い色の上書きを許すため、同色の直接隣接成分数と最小筆数は一致しない。

独立probe: `{"arrays": 1092, "allSubintervals": 19956, "literalPaintingBFSStates": 5460, "oracle": "BFS from all-zero fence, enumerate EVERY legal contiguous brush stroke of colors1..3 (never decrease any cell), then compare minimum action counts. No monotone-stack oracle."}`。

別経路 `ranges → query-times → offline → yes → yes` は `range-offline/sweep` の一般offline/Fenwick結果へ達する。既知の有効リンクを数える部分には一般offline/BITを使えるが、原典の最小筆数→有効リンクの主要同値が記事にない。canonical gapは自然な静的区間集計の質問で固定。

今後必要な実装検証:
- 任意の順序付き整数色/座標圧縮と半開区間を受ける完全C++20 API。N,Q各20万を包含。
- 同色stack更新・隣接等色・小さい色の障害・区間外未塗装・単点・独立呼出しと不正区間を検査。
- 実MDX C++を実塗りBFS/全小色列・全区間/maxで照合しASan/UBSan。

### 1117 Minimizing Edges

[原典](https://usaco.org/index.php?page=viewproblem2&cpid=1117) / [公式解説](https://usaco.org/current/data/sol_prob2_platinum_feb21.html)。Analysis: Benjamin Qi, Danny Mittal。公式resultsの当該PlatinumのSolution直リンクで出自を確認。

原典の全数値・意味: `{"N": "2..100000", "M": "N−1..N(N+1)/2, sumM<=200000", "T": "1..50000,sumN<=100000", "graph": "connectedundirected, selfloops allowed, no parallel edges", "target": "preserve all root1→a walk-length feasibility for ALLa and b>=0; repeatededges counted; minimize edges; Gprime not restrictedtosubgraph"}`。

**特徴からの初回経路**: `graphs`。
- `graphs/shortest`: 頂点・辺について何を求めますか？ → `network-connection`「全体の接続・接続の変化・道路の復元」

停止: `graphs-network-connection/shortest` (question)「頂点・辺について何を求めますか？」。その時点の回答labelは以下。
- `connectivity`: 到達する頂点・成分・全体をつなぐ操作
- `spanning`: 全頂点を安くつなぐとき、追加する辺を使うか
- `failures`: 辺や頂点を一つ禁止した後の、到達性・最短距離
- `mst-replace`: 全頂点を安くつなぐ辺を、追加辺と置き換える
- `distance-table`: 全二点間の最短距離表から、道路の長さの総和を最小にして復元する
- `specified-mst-count`: 指定された木が唯一の最小全域木になる、追加道路の選び方の個数
- `mst-roles`: 全頂点を安くつなぐ辺の必須性、または最小値より厳密に重い次の木
- `steiner-terminals`: 少数の指定頂点を全てつなぎ、共有する辺の費用は一度だけ払う
- `spanning-count`: 全頂点をつなぐ、閉路のない辺集合の個数を数える
- `path-count-table`: 全頂点対の単純路本数0/1/2/3を指定し、その通りのグラフを構築する
- `two-threshold-switch`: 前半は番号の下限・後半は上限を守り、一つの頂点で切り替えて移動する
- `unknown`: わからない

不足回答案: 「始点から各頂点へ到達できる全歩数を保ち、グラフの辺数を最小にする」。不足技巧ID: `parity-walk-profile-layer-greedy-realization`。

不足理由: 道路復元の選択肢は全二点最短距離表や単純路本数表であり、固定始点の全walk長の真偽を保つ回答がない。偶奇別距離を計算する既存記事にも、許容A/B/C辺と最小実現greedyがない。

**確認した満点手順**: 偶奇二層BFSでg(v)=(even,odd)を求め、h(v)=(a<b)へまとめる。二部ならBFS木のN−1。非二部ではhのA=(a−1,b−1)、B=(a−1,b+1)/(a+1,b−1)、末端C=(a,a+1)内の辺だけを許し、各頂点に二つの距離の前駆証人を付ける。同じa+bの層の隣接bucketへ渡すB辺数を、同費用なら将来へ渡すgreedyで最小化する。

- 連結N>=2の無向graphでは一往復により各偶奇の最小歩数以降を二歩ずつ実現できる。従って全walk長の言語は二つの最小歩数と同値。sortしても整数の偶奇から元のgを復元できる。
- 許容辺は両端の偶奇距離に対しd(v,p)<=d(u,1−p)+1を双方で守るものだけ。これをhで分類するとA/B/Cとなる。全非零距離に−1の前駆証人があれば、距離について帰納して必要な最短walkを実現できる。rootのeven0は証人不要、odd距離の証人だけ要る。
- A前駆一本なら二つの距離を同時に満たす。なければ左Bと右Bが両方必要、b=a+1の末端だけ右Bを同profileのC辺/loopが代替する。Aは上層側だけの制約を満たし、B/Cは同a+b層内なので層ごと独立。
- bucketサイズf、左からの既存B辺数pは可能な限り別頂点へ分散する。A候補があれば、左Bを既に持つx=min(f,p)頂点には右Bを、残りにはAを一本ずつ足す。費用同額なら右の制約を助ける選択が優越する。Aがなければ不足の左Bをmax(f−p,0)本補い、右Bをf本作る。
- root a0はeven証人を免除し、b>1なら右Bを一本だけ作る。層末端Cでは、A候補があればf−floor(min(p,f)/2)、なければmax(f−p,0)+ceil(f/2)が追加費用。C一本は最大二頂点を満たし、奇数の残り一頂点はloopで満たす。非末端で次bucketが空なら既存Aへ一本ずつつなぎブロックを終える。

計算量: BFS O(N+M)、profileの整列/mapとgreedy O(NlogN)。全体O(NlogN+M)時間、O(N+M)空間。総N<=1e5/総M<=2e5を包含。

近接旧記事のscope差分（全て凍結SHA）:
- `synchronous-product-parity-distance-sum` / `74d1847356382ee96f12b01a0081a2977da371a4d98e6a82afc74699eaaceec7`: 無向walkの偶奇別最小距離から二歩刻みの到達性を使う点は共通。ただしグラフを実現/最小辺数へ変換するAPI・A/B/C層の証明はない。
- `distance-matrix-essential-edges` / `fb49903a578074ce7531f41259e9f0e58314128f49333e34ce7bc14d15b71a39`: 全二点の数値最短距離を保存する重み付き道路復元。固定始点の全walk長、loop、別の辺を許す無向実現とは異なる。
- `bipartite-component-edge-addition-count` / `b12016f0044c095a2edc0d6613ff276f6a95f4c4f0c46e472d403846b8cb1c52`: 二部性を保つ辺一本の追加数であり、各頂点の二つの歩数しきい値を同時に保存する最小実現ではない。

独立probe: `{"allConnectedUndirectedGraphsWithOptionalLoopsN2to5": 23940, "completeInfiniteWalkLanguageGroups": 932, "literalParityFeasibilityComparisons": 595764, "oracle": "Enumerate EVERY labeled graph including loops/no parallel; group by the COMPLETE eventually-periodic sequence of literal exact-length reachable vertex bitsets (cycle detection, not an arbitrary length cutoff). Min edge count over the entire group is independent oracle for greedy."}`。

今後必要な実装検証:
- loopを正しく二層へ移すBFS、二部INF、root例外、a+b層/空bucket/末端Cを含む再利用C++20/API。
- greedyが返す辺数だけでなく任意Gprimeでよいこと/元辺に限定しないことを明示。原典N10万/総M20万で実行。
- 全小loop付きgraphの完全walk言語群内最小辺数をoracleにし、公開fenceを通常/ASan/UBSan検証。

### 1118 Counting Graphs

[原典](https://usaco.org/index.php?page=viewproblem2&cpid=1118) / [公式解説](https://usaco.org/current/data/sol_prob3_platinum_feb21.html)。Analysis: Danny Mittal, Benjamin Qi。公式resultsの当該PlatinumのSolution直リンクで出自を確認。

原典の全数値・意味: `{"N": "2..100", "M": "N−1..N(N+1)/2", "T": "1..25000,sumN²<=100000", "graph": "connectedundirected with loops allowed/no parallel edges", "target": "same ALL rootwalk-length feasibility, count labeledGprime mod1000000007"}`。

**特徴からの初回経路**: `graphs`。
- `graphs/shortest`: 頂点・辺について何を求めますか？ → `network-connection`「全体の接続・接続の変化・道路の復元」

停止: `graphs-network-connection/shortest` (question)「頂点・辺について何を求めますか？」。その時点の回答labelは以下。
- `connectivity`: 到達する頂点・成分・全体をつなぐ操作
- `spanning`: 全頂点を安くつなぐとき、追加する辺を使うか
- `failures`: 辺や頂点を一つ禁止した後の、到達性・最短距離
- `mst-replace`: 全頂点を安くつなぐ辺を、追加辺と置き換える
- `distance-table`: 全二点間の最短距離表から、道路の長さの総和を最小にして復元する
- `specified-mst-count`: 指定された木が唯一の最小全域木になる、追加道路の選び方の個数
- `mst-roles`: 全頂点を安くつなぐ辺の必須性、または最小値より厳密に重い次の木
- `steiner-terminals`: 少数の指定頂点を全てつなぎ、共有する辺の費用は一度だけ払う
- `spanning-count`: 全頂点をつなぐ、閉路のない辺集合の個数を数える
- `path-count-table`: 全頂点対の単純路本数0/1/2/3を指定し、その通りのグラフを構築する
- `two-threshold-switch`: 前半は番号の下限・後半は上限を守り、一つの頂点で切り替えて移動する
- `unknown`: わからない

不足回答案: 「始点から各頂点へ到達できる全歩数を保つ、ラベル付きグラフの個数を数える」。不足技巧ID: `parity-walk-profile-layer-inclusion-exclusion-count`。

不足理由: 全walk長の真偽を保存してgraphそのものを数える枝がなく、同名CountingGraphsの別原典はMSTの唯一性であって対応しない。一般包除や偶奇距離だけでは層の未充足頂点数DPを説明できない。

**確認した満点手順**: 1117と同じ偶奇profileのA/B/C辺条件を使う。二部なら各距離層の頂点が一つ前の層から非空辺集合を選ぶ積。非二部ならa+b層ごと、前bucketへのB辺と下層へのA辺を二段で選び、未充足頂点数を状態にする。B辺行列の指定行/列非零とC末端の指定頂点非孤立を包除する。

- 1117の偶奇profileと許容辺/前駆証人の必要十分性を共有する。A辺の選択は上層側だけに影響するので、異なるa+b層の選択は独立に掛けられる。
- 二部で距離層人数f_dならprod_{d>=1}(2^{f_(d−1)}−1)^{f_d}。同層辺/loop/距離を飛ばす辺は許さず、各非根の直前層への少なくとも一本だけを要求する。
- 前bucketサイズp、未充足y、現bucketサイズmでx頂点をB入辺無しとする場合、C(m,x)Σ_{k=0}^y(−1)^k C(y,k)(2^{p−k}−1)^{m−x}通り。指定y行とm−x列を両方非零にする0/1辺行列の包除である。
- B入辺無しy頂点にはAが必須。A下層サイズl、最終未充足xは他のm−y頂点から選び、C(m−y,x)(2^l−1)^{m−x}を掛ける。A/Bを両方持つ場合も選択は一意な段階へ分解される。
- C終端サイズm、未充足yを救うloop込み内部graph数はΣ_{k=0}^y(−1)^k C(y,k)2^{(m−k)(m−k+1)/2}。この式は公式説明ではexerciseであり、必要y頂点を孤立させる補集合から独立に導出した。root0距離は免除しodd側のみ未充足として初期化。

計算量: powers/binomialを前計算してO(N³+M)時間、O(N²+M)空間にできる。原典はN<=100/総N²<=1e5、法1e9+7。公式掲載直接累乗版の細かいlog因子は実装時に区別する。

近接旧記事のscope差分（全て凍結SHA）:
- `synchronous-product-parity-distance-sum` / `74d1847356382ee96f12b01a0081a2977da371a4d98e6a82afc74699eaaceec7`: 偶奇最小walkの性質まで共通だが、実現graphの辺選択数を数えない。
- `unique-mst-completion-count` / `dc18ce766268cb5b4876f0d7a76d8f123ed53541474972459200a7c6fd61390a`: Codeforces1857Gの同名CountingGraphs。指定木が唯一MSTになる追加辺の個数であり、USACOcpid1118の全walk言語保存とは別問題。
- `inclusion-exclusion-forbidden` / `f7909ade73c4979492e43887327aa7548c05ed48c9ad81e7da0cfc718a2858ad`: 必須文字が欠ける列の包除。二部辺行列の両側非零条件とloops付きC終端を扱う具体DPではない。

独立probe: `{"allConnectedUndirectedGraphsWithOptionalLoopsN2to5": 23940, "completeInfiniteWalkLanguageGroups": 932, "oracle": "Group size in the same exhaustive infinite-language partition is independent graph-count oracle; compare bipartite formula, layered two-stage PIE, root exemption and independently derived terminal C-edge/loop PIE. Exact integers, not modulo coincidences."}`。

今後必要な実装検証:
- 二部/非二部、a0 root、空bucket、C終端とloopsの完全API。法/0^0/二項係数の範囲を明示。
- N100/総N²1e5を含むC++20と積/累乗前計算・整数境界を確認。
- 全小graph完全walk言語の群サイズをexact oracleに公開fenceを照合し、通常/ASan/UBSan。

### 1140 United Cows of Farmer John

[原典](https://usaco.org/index.php?page=viewproblem2&cpid=1140) / [公式解説](https://usaco.org/current/data/sol_prob1_platinum_open21.html)。Analysis: Benjamin Qi。公式resultsの当該PlatinumのSolution直リンクで出自を確認。

原典の全数値・意味: `{"N": "1..200000", "breeds": "1..N", "interval": "contiguous length>=3, endpointsare2leaders plusoneinteriorleader", "leaders": "threeleaders eachbreedunique among ENTIREinterval, not only pairwise distinct", "target": "count interval+leaders, exact64bitanswer"}`。

**特徴からの初回経路**: `ranges`。
- `ranges/updates`: 数列について、何を求めますか？ → `aggregate-goals`「連続する区間・利用期間・開催日の得点を集計する」
- `range-aggregate-goals/updates`: 数列について、何を求めますか？ → `window`「連続する区間の長さ・個数・和・最大最小」

停止: `range-window/wanted` (question)「連続する区間について何を求めますか？」。その時点の回答labelは以下。
- `aggregate-values`: 固定長の集計、全区間の最大最小・GCD・OR
- `sum-conditions`: 区間和・平均・長さ制限・和と XOR の一致
- `feasible-selection`: 種類数・重複・移動費用・訪問予算の範囲で区間を選ぶ
- `unknown`: わからない

不足回答案: 「区間の両端と内側一点を選び、その三値がそれぞれ区間内で一度だけ現れる選び方を数える」。不足技巧ID: `interval-unique-endpoints-singleton-middle-active-lazy`。

不足理由: 連続区間の個数へは進めるが、両端単出現を満たす候補左端と内部単出現数の積を数える枝がない。全区間singleton寄与やsingleton一つの証人とは数量が異なる。

**確認した満点手順**: 右端rを加える直前に、左端lが[l,r−1]で単出現ならactive[l]=1、内部[l+1,r−1]のsingleton個数をw[l]とする。直前同色位置pより右のlのΣactive[l]w[l]を加える。r追加後にpをdeactivate、wの[p,r)へ+1、[pp,p)へ−1し、現在位置をactive/w0で追加。active個数と積和を持つlazyで実行。

- 両端leaderが区間で単出現なら、その二breedは互いにも内部にも現れない。従って内部leaderの選択数は内部singleton個数と等しい。右端breedの直前位置より左を除けば右端の単出現条件を保証する。
- 同じbreedの前二出現pp<p<rを用いると、rを内部へ加えてsingleton数が増える左端lはp<=l<r、減る左端はpp<=l<pだけ。負のsentinelは有効左端0へclampする。
- 以前の同色左端pは以後永久にactiveでない。nodeはactive人数cとΣactive*wを持ち、wへのdelta加算をsum+=delta*cで処理する。point無効化前にはlazyをpushし、過去の加算と人数を取り違えない。
- 答えは全位置三点組C(N,3)以下なので原典N200000で符号付き64bitに収まる。内部singleton値更新には−1があり、unsigned算術へ安易に移さない。

計算量: O(NlogN)時間、O(N)空間。最大exact答えC(200000,3)=1333313333400000。

近接旧記事のscope差分（全て凍結SHA）:
- `singleton-subarray-contribution` / `342c85f8a3467d792df9e5a5ab46b1f639c1124d409a1a0aafbbc4bf6d8e9c7b`: 全区間の一単出現の寄与は数えるが、両端も全区間内で単出現という追加条件と内側leaderの選択を同時には数えない。
- `offline-range-singleton-witness` / `972f7b8ac0222dc782f3f4f2466fd8843ac53fefcb8603a83bc61579bd8365cc`: 静的区間の単出現値一つを返すだけで、全区間/三leaderの総数ではない。
- `lazy-segment-tree` / `37fb93ce171c2a1deee8e07e0f5ebdcce02faf5f6f5c5371e47b2c370d0e38b8`: 一般affine sumの実装。active点だけの加算と不可逆deactivate、前二出現の範囲からunique数を更新する技巧/APIはない。

独立probe: `{"allArraysLength1to8AlphabetAtMost3": 9833, "allLeaderTriplesTested": 461322, "oracle": "Enumerate ALL ordered-by-position leader triples l<m<r; directly count each leader breed in ENTIREdelegation l..r. Compare literal active/singleton interval-update equations (not a production lazy API), also check every intermediate active/weight invariant."}`。

今後必要な実装検証:
- queryの前後、前二出現sentinel、activate/deactivateとlazyの完全C++20/API。色圧縮とN20万全包含。
- 全同色/全異色/交互/少数色と各三leader全列挙、原典PlatinumをGold版と分けて確認。
- 公開fenceをexact triple oracle/max/不正API/呼出し独立性/ASan/UBSanで検証。

### 1141 Routing Schemes

[原典](https://usaco.org/index.php?page=viewproblem2&cpid=1141) / [公式解説](https://usaco.org/current/data/sol_prob2_platinum_open21.html)。Analysis: Benjamin Qi。公式resultsの当該PlatinumのSolution直リンクで出自を確認。

原典の全数値・意味: `{"N": "2..100", "T": "1..20,sumN²<=20000", "K": "0..2 edgeswithfrom>to; allothers increasing", "graph": "directed0/1 adjacency, no selfloops, verticesmayrevisit inpath, eachDIRECTEDedge usedexactlyonceacrossallpaths", "roles": "Ssenders andSreceivers,S>=1, eachnodeS/R/neither; everyendpoint distinct", "guarantee": "atleastonevalidscheme", "target": "countschemes mod1000000007"}`。

**特徴からの初回経路**: `graphs`。
- `graphs/shortest`: 頂点・辺について何を求めますか？ → `walk-goals`「移動費用・訪れる頂点・辺の通り方」

停止: `graphs-walk-goals/shortest` (question)「頂点・辺について何を求めますか？」。その時点の回答labelは以下。
- `distance`: 移動費用や移動回数の最小値
- `exact-walk`: 決まった回数歩く・各頂点を一回ずつ通る
- `functional`: 各頂点の行き先が一つで、大きい回数進む
- `all-edges`: 指定した始点と終点で、すべての辺を一回ずつ通る
- `through-pivot`: 指定した中継頂点を通り、頂点を繰り返さずに両端を結べるか
- `collect-once-reward`: 頂点を再訪しながら、一度だけ受け取れる報酬の総和を最大にする
- `synchronous-factors`: 複数の無向グラフで全成分を同時に一歩ずつ動かす、組状態の距離の総和
- `label-reset`: 移動のたびに番号を使い、同番号の再使用には間に大きい番号が必要な列を数える
- `unknown`: わからない

不足回答案: 「複数の始点と終点を対応させ、全有向辺を一度使う経路分解の個数を数える」。不足技巧ID: `almost-dag-edge-routing-pairing-frontier-cycle-count`。

不足理由: 全辺を一度通る枝は指定一始点/一終点の構築であり、複数sender/receiverの対応も含めた経路分解の数え上げを選べない。一般のgrid plug DPとは幅の条件も対象も違う。

**確認した満点手順**: 各senderに仮想入辺、receiverに仮想出辺を追加し、各頂点で入出辺のbijectionを選ぶ。全pairingのうちsenderから来ない閉路成分を排除する。番号順に頂点を処理し、最大二つのbackwardedgeを含む未完道の未来端点を状態にする。追跡道の到着0/1/2本に対し異なる出辺を選び、道の合併と閉路の禁止を行い、残りの局所pairing数(deg−tracked)!を掛ける。

- 全辺一度の経路分解と、仮想S入辺から仮想R出辺へ至る閉路なし局所bijectionは一対一。次数整合だけでは別閉路が残るので不足。
- 閉路があれば少なくとも一本のbackwardedgeを含む。処理済み部分を縮約した未完道のうち、未来に始点/終点が両方あるものだけが将来閉路を作るため、その最大K本の端点だけを保持する。
- 同一追跡道へ戻る出辺は即閉路として拒否。他方のbackwardedgeへ入るなら二道を合併する。二本が同時到着し互いのbackwardedgeへ入る二重crossも閉路なので拒否する。receiverでの終端や過去へ確定した端点は状態から落とす。
- 追跡入辺c本へ割り当てるc出辺は相異なる。残る入出辺の組は任意の(deg−c)!通りで、状態遷移に必要な情報は増えない。完成時に追跡道なしなら別閉路は一つも残らない。
- c0の状態はO(N²)個で定数遷移、c1の状態はO(N)個でO(N)候補、c2は一状態でO(N²)候補。各行O(N²)、全体O(N³)となる。

計算量: K<=2でO(N³)時間。行をrollすればO(N²)空間、公式の全行保存はO(N³)空間。原典N<=100/総N²<=20000を含む。

近接旧記事のscope差分（全て凍結SHA）:
- `euler-degree-connectivity` / `777802d7b13319261e739199fc7f31f9959ba0ac5a9a5396a3c2f17c3a454d1c`: 指定s/tのEulertrailを一つ構築するAPIで、局所pairingの総数から閉路成分を除く数え上げは扱わない。
- `frontier-single-cycle` / `cad6a26e9f2bc47f93ae398e21e05e3b99b2aa80df9fa5a755e07ea4b3644961`: 幅12以下の無向格子Hamilton閉路。原典はN100のほぼDAG、有向辺を全使用する複数trail分解であり、K<=2 backwardedgeの圧縮が必要。
- `dag-path-cover-vertex-disjoint` / `36b60700441b34de29f849ec8d5dac952f2878d33241f91f325d052535d3983f`: 頂点を一度ずつ使うパスの最小本数であり、全辺一度/頂点再訪可/経路分解個数とは異なる。

独立probe: `{"allDirectedSimpleGraphsN2to4WithAtMostTwoBackwardEdges": 1468, "allDegreeBalancedRoleConfigurationsWithSender": 574, "validInstances": 562, "balancedButNoValidScheme": 12, "allLiteralTrailSchemes": 1481, "oracle": "For EVERY eligible graph, local degree balance uniquely determines S/R/. roles. Enumerate actual sender-to-unusedreceiver edge-disjoint directed TRAILS in fixed sender order, permitting repeated vertices, stopping at receivers optionally, accepting iff EVERY edge used once. Compare two-backedge frontier DP including single-path cycle closure, cross merger, double cross closure, receiver termination and deg-minus-tracked factorial."}`。

**別解の未確認**: 公式末尾のO(N²) PIE/小行列式には証明がexerciseとなる箇所があり、BESTの回路数の規約も今回は未検証。上で証明・実trail比較したO(N³) frontier満点解と区別する。

今後必要な実装検証:
- role/次数/仮想辺/頂点再訪を定義した完全C++20/API。K0/1/2と道合併・両道cross閉路・receiver終端を明示。
- 法1e9+7/factorial0/deg0の孤立点、原典は存在保証ありだが一般APIで不正/0解をどう返すか決める。
- 実trail列挙をoracleに全小graph・全roleと比較し、N100/通常/ASan/UBSanを確認。

### 1142 Balanced Subsets

[原典](https://usaco.org/index.php?page=viewproblem2&cpid=1142) / [公式解説](https://usaco.org/current/data/sol_prob3_platinum_open21.html)。Analysis: Spencer Compton。公式resultsの当該PlatinumのSolution直リンクで出自を確認。

原典の全数値・意味: `{"N": "1..150", "grid": "N×N, G/.", "subset": "nonempty grassy4connected with everyoccupiedrow andcolumn acontiguousinterval", "target": "countorthogonallyconvexconnectedsubsets mod1000000007"}`。

**特徴からの初回経路**: `grid-arrangements`。
- `grid-arrangements/goal`: 格子で何を求めますか？ → `color-numbers`「色や数を置く条件・選んだマスの外接長方形」

停止: `grid-color-numbers/goal` (question)「格子で何を求めますか？」。その時点の回答labelは以下。
- `other`: その他の格子の配置・被覆
- `color-separation`: 二色のマスが同じ行・列を使わない配置の個数
- `bounding-area`: 一様に選んだ K マスの、外接長方形の期待面積
- `neighbor-modulo`: 異なる正整数を置き、隣接する大きい値÷小さい値の余りをそろえる
- `height-silhouette`: 各行・各列の最大高さと、各マスが空かを保って残す総量を最小にする
- `rectangle-components`: 固定された色の格子で、各部分長方形の中だけの同色成分数を求める
- `xor-predecessor`: 3×3のXOR更新と一セルの誤りから、最小の初期図形を逆算する
- `prefix-rectangles`: 二番号を交換するたび、番号順に選んだマスが長方形になる段階を数える
- `unknown`: わからない

不足回答案: 「草のあるマスから、四連結で各行・各列が途切れない非空部分集合を数える」。不足技巧ID: `orthogonally-convex-row-interval-phase-prefix-dp`。

不足理由: 格子の配置/選択へは進めるが、全使用マスを選ぶHamilton閉路、固定矩形内成分、番号prefix矩形性のいずれでもない。行ごとの区間/両端の一転換と2D累積DPが不足する。

**確認した満点手順**: 非空行は連続し各行は[L_i,R_i]。連続行の区間overlapに加え、Lは非増加から非減少へ一度だけ、Rは非減少から非増加へ一度だけ変化することが列連続性と同値。現在行のL/Rと最初の厳密な内向き変化が起きたかの二flagを持つ。前行L/Rの条件を矩形範囲へ分け、四枚の2D prefix sumで遷移する。

- 行の連続区間性は原典条件そのもの。四連結なら非空行に空白行がなく、隣接行区間がoverlapする。逆にこれで全選択マスは四連結。
- overlapを保ちながらLが増えた後で減れば、その間に一度消えた列が再出現し列連続性に反する。Rも逆向きに同じ。逆に谷型L/山型Rなら、各列についてL_i<=cかつR_i>=cとなる行集合が区間同士の交わりなので途切れない。
- phaseは最初の厳密L増加/R減少で切り替え、等号では切り替えない。これで平坦部の好きな位置で切り替えて同じ集合を重複計数することを防ぐ。
- 前区間[l,r]と新[L,R]のoverlapはl<=R,r>=L。L旧phase0→新0はl>=L、0→1はl<L、1→1はl<=L。Rは0→0 r<=R、0→1 r>R、1→1 r>=R。各組をoverlapと交差すると(l,r)の長方形範囲となる。l>rの状態は0とし、定数個の矩形和でO(1)遷移。
- 各行の全G連続区間だけを受理し、単一行開始はflags0/0で1を加える。全底行・全区間・全flagを足すと非空集合を一意に数える。

計算量: O(N³)時間、行をrollしてO(N²)空間。原典N<=150を包含。mod1e9+7、2D累積差分の負値補正が必要。

近接旧記事のscope差分（全て凍結SHA）:
- `frontier-single-cycle` / `cad6a26e9f2bc47f93ae398e21e05e3b99b2aa80df9fa5a755e07ea4b3644961`: 全使用マスの一閉路と幅12のplug状態であり、行列凸な任意部分集合のN150数え上げとは異なる。
- `grid-rectangle-components-euler-boundary` / `9df245577b10bfe299b45b07200d99334d4a78a7344e4dbf25d243e2525c4a8a`: 固定された部分長方形内の色成分数。選ぶ部分集合そのものを数えず、矩形以外の直交凸形の境界を扱わない。
- `prefix-sum` / `8ac6537327de079dc9a5e1e0b05bf45226959e65850670104f5156540cd59961`: 二次元矩形和の部品だけで、行区間状態/strict phase/連結なoverlap条件と重複のない生成は説明しない。

独立probe: `{"everyNonemptyBitmapEveryH_W1to4": 74938, "allGrassBoardsN1to3AndRandom4": 1556, "oracle": "Enumerate actual cell subsets and test literal occupied-row contiguity, occupied-column contiguity,4-neighbor BFS connectivity. Compare endpoint/unimodality characterization for EVERYsmallshape. Zeta sum over allvalidsubsets gives exact answer for eachgrassboard, independently checked against interval/two-strict-phase-flags DP. No prefix-sum optimization/API implemented in this research probe."}`。

今後必要な実装検証:
- 行/列の向き・inclusive overlap・strict phaseと開始状態を具体化した完全C++20/API。G/.とempty/不揃い盤/上限を検査。
- 全小実subsetの4BFSと行列穴判定を独立oracleに公開fence/矩形和最適化と照合。
- N150の全草/全空/細い形/穴/対角接触/等号平坦部、ASan/UBSan。

## 再現

```sh
python3 /tmp/flowchartcp-usaco2021-spring-probe.py
```

probeは凍結rawだけで六つのcanonical経路を独立再生し、質問/回答label、initialReached、gapのgraph/node/currentQuestion/optionsを全て凍結nodeへ突合する。全620SHAも再検査する。問題の実装を使ったoracleにはしていない。

期待する決定的counterはauditの各probeResultと-probe.jsonに保存。時間だけは環境で変わる。probe実行時の出力jsonは再生成されるので、決定的結果SHAはsecondsを除いた正規化JSONから算出した。

## 登録案と保存方針

`/tmp/flowchartcp-usaco2021-spring-registration-proposal.json` は未登録提案であり、現在のexpectedTechniqueIdsは全て空のまま。候補IDを既存記事や確認済み使用例へ先に入れない。各記事/API・原典範囲・最大/invalid/独立oracle/native/sanitizer・guard付き新分岐・旧walk保存を完了してから、初回監査の全fieldを保ったまま後続review/resolutionを追加する。

この作業では共有plan/ledger/data/source/article/flow/auditを変更していない。
