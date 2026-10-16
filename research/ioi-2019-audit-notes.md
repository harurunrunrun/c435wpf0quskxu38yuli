# IOI 2019 固定6題の初回監査

競技日1は **2019-08-06**、競技日2は **2019-08-08**。公式IOI一覧が各日3題を列挙し、JOI委員会の一覧で日付を確認した。練習4題とNoticeは対象外。公式IOI記事の2019-10-12は記事公開日であり、競技日に使わない。全題の難度は `null`。

- [IOI公式大会・全6題一覧](https://ioinformatics.org/page/ioi-2019/51)
- [公式アーカイブ・原典とHSC Review](https://ioi.te.lv/locations/ioi19/contest/)
- [JOI委員会・競技日と原典英日版](https://www2.ioi-jp.org/ioi/2019/tasks/index.html)

技巧検索前に6題を固定した時刻はaudit JSONの `selection.fixedAt`。フロー/記事の固定はそれより先のUTC 2026-10-15T05:57:46.305422。スナップショットは472 metadata・472 MDX・439図で、後続の共有変更を含めない。

| 対象 | canonical route（全て凍結製品runtimeで再生） | 最初の不足箇所 | 判定 |
|---|---|---|---|
| Day1 Shoes | ranges → sequence-changes → reorder-cost | range-sequence-changes/reorder-operation | 確認済み技巧不足 |
| Day1 Split | graphs → group-constraints | graphs-group-constraints/shortest | 確認済み技巧不足 |
| Day1 Rect | geometry → rectangle-aggregates | geometry-rectangle-aggregates/geometry-task | 主要細部未確認 |
| Day2 Line | heuristic → yes | heuristic/output（一般結果） | 満点接続未確認 |
| Day2 Vision | math → bits-digits | math-bits-digits/number-task | 確認済み技巧不足 |
| Day2 Walk | graphs → walk-goals → distance → many-connections | shortest-shared-connection-goals/movement | 疎化補題未確認 |

最初の不足までの全質問・回答ID・表示ラベル・停止ノードの全選択肢はJSONに保存した。一般記事に当たるだけではcoveredにしない。Lineは既存 `output-only` へ実際に到達するが、少ない縦横線で点を覆う構築はその記事にない。したがって `actualReachedTechniqueIds=[output-only]` と `expectedTechniqueIds=[]` を区別した。

## 確認済みの不足

### Shoes: oriented-equal-pair-adjacent-swaps-fenwick

[原典](https://ioinformatics.org/files/ioi2019problem1.pdf)、[公式Review p1](https://ioi.te.lv/locations/ioi19/contest/day1/Shoes/review.pdf)。隣接二要素だけを交換し、同サイズの左→右の対を並べる。サイズ重複を許す。

最初の生存要素を最左の逆符号同サイズと組にし、間の生存要素数に向き反転の一回を必要に応じて足す。先頭の対を固定しても残る要素の相対順序は変わらない。相手を遠い同型要素にする必要はなく、最左相手へ交換できる。公式Reviewはこの帰納とO(N log N)のFenwick/segment-tree実装方針を明記する。

既存 `fenwick-tree` や `palindrome-adjacent-pair-inversions` だけでは、この符号付き異型対・向き・最左相手の帰着を扱わない。新記事には型別キュー、生存距離、向きの補正、重複、64bit総数、隣接交換BFSとの比較が必要。

監査用 `research/probes/ioi-2019-shoes-probe.py` は2サイズ、長さ8以下の全5340整合列について、全合法対順を始点とする隣接交換multi-source BFSと貪欲値を照合し全一致。これは再利用C++20や最大制約検証ではない。

### Split: dfs-lowlink-three-size-two-connected-partition

[原典](https://ioinformatics.org/files/ioi2019problem2.pdf)、[公式Review p2](https://ioi.te.lv/locations/ioi19/contest/day1/Split/review.pdf)。要求は三集合全ての連結ではなく**少なくとも二つ**。指定サイズも保持する。

公式PDFの添字が抽出で欠けるため、以下を独立に補った。正のサイズを a≤b≤c とする。

1. 任意の合法解で連結な二集合から、連結探索prefixをそれぞれa,b個切り取り、残りをc個へ回せる。従って小さい二サイズを連結にする構築へ絞ってよい。
2. DFS木で、部分木がa以上かつ全子部分木がa未満となるvを取る。その部分木Pと外側Qは各々連結（Q空の場合は別途不可能判定になる）。
3. 子uの `low[u] < tin[v]` は、vの**真の祖先**へ接続できることを意味する。Pからuの部分木を丸ごとQへ動かし、P≥aを保つと両側は連結のまま。
4. Q<aで動かせない祖先接続付き子uがあれば、P−size(u)<aとsize(u)<aからP<2aとなる。しかしQ=N−P>N−2a=b+c−a≥aで矛盾。従って失敗時はそのような子は全てQへ入り、v除去後の各成分は全てa未満になる。二つの互いに素な連結集合を各a以上にすることは不可能。
5. 両側a以上なら大側はN/2≥b。小側からa、大側からbの連結prefixを取り、残りをcへ回せる。

DFS/lowlink/抽出はO(N+M)時間・空間で実装できる。サイズ0の原典許容有無は数値が読めず推測しない。一般APIを作る際は正の三サイズを契約にするか、0サイズの扱いを明示して追加する。

監査用 `research/probes/ioi-2019-probe.py` はN=3..6の全27474連結単純グラフと全81610三サイズについて、三集合への全割当・直接連結検査と照合し、可否も返す構築も一致。未確認の原典数値上限での実行や再利用C++20は未実施。

### Vision: rotated-manhattan-two-mark-boolean-circuit

[原典](https://ioinformatics.org/files/ioi2019problem5.pdf)、[公式Review p1–2](https://ioi.te.lv/locations/ioi19/contest/day2/Vision/review.pdf)。画像を先に読まず、全ての2黒画素配置に通用するゲート列を出力する。

公式Reviewの主要補題は L1 = max(|Δ(r+c)|,|Δ(r−c)|)。対角線に黒が1個/2個ある信号を作り、K+1本の対角線ブロックに二点が入ることを両方向で確認して距離≤Kを求め、距離≤K−1を除く方針と、O(H+W)ゲート/O(HW)端子を明記する。

独立に、各対角線OR `q[i]` とprefix OR `P[i]` を作り、`OR(i>d: q[i] AND P[i-d-1])` を幅>dの条件にする具体案も確認した。二方向の条件のORをB_dとすれば、距離Kは `B_(K-1) AND NOT B_K`。同じ対角線の二点、片側方向の幅0、Kが大きすぎる場合も処理できる。空のORを定数falseで作る規則は実APIで必要。

既存 `manhattan-transform` は既知の点座標を普通のC++で読む実装であり、このゲート列は生成しない。新記事にはゲート生成器・非空入力・参照順序・最後の出力・ゲート数と端子数の両方の厳密上界・全二画素配置シミュレータが必要。

監査用prefix条件式をH,W=1..6、全二画素対・全K=1..H+W+1の42140件で直接L1と比較し一致。**元のゲート/端子上限の数値、原典最大サイズ、ゲートAPIの実コード検証は未確認**。主要な数学的方針確認と、満点予算を満たす実装完了を区別する。

## 未確認の3題

- **Rect / grid-enclosing-higher-boundary-rectangle-candidates**: [原典](https://ioinformatics.org/files/ioi2019problem3.pdf)、[公式Review](https://ioi.te.lv/locations/ioi19/contest/day1/Rect/review.pdf)。四方向の外側セル全てが各内側セルより厳密に高い。good pairの単調スタック・辺候補照合、または16種類のblock-corner接続による候補列挙を読むことはできたが、同高さ、候補を一隅で一意に復元する定義、全候補の完全性が未確認。抽出で指数が消えたO(n)を、セル数に関する線形と勝手に補わない。単調スタック一般論では代用しない。
- **Line / orthogonal-point-cover-spiral-two-chains**: [原典](https://ioinformatics.org/files/ioi2019problem4.pdf)、[公式Review](https://ioi.te.lv/locations/ioi19/contest/day2/Line/review.pdf)。螺旋＋二単調鎖でN+6本、接続順と方向の工夫でN+3本と明記されるが、最終工夫はsketch自体が省略する。満点の接続補題と採点表数式を未確認とする。output-only形式を確認しただけでは満点構築をカバーしない。
- **Walk / skywalk-endpoint-sparse-shortest-path**: [原典](https://ioinformatics.org/files/ioi2019problem6.pdf)、[公式Review](https://ioi.te.lv/locations/ioi19/contest/day2/Walk/review.pdf)。全交点グラフはO(NM)規模。始終点をまたぐ通路を直近の十分高いビルで分割し、上端が水平通路内部の鉛直辺を消してO(M)規模へ絞る方針は読めた。削除で距離が不変となる補題、一般始終点への分割でそれが成立する全証明、端点/同高さのイベント実装は未確認。通常のDijkstraや区間木の辺圧縮だけでcoveredとしない。

## 数値と資料取得の制約

公式原典6件と公式Review6件のweb取得は成功した。Lineの初回archive原典だけtimeoutし、IOI本部・JOI公式ミラーで本文を取得した。solutions zipはwebではunsupported content-typeで、コードを読んだとは記録しない。

数式/数値のテキスト欠落を全題で確認した。screenshotもcontent type/errorで画像本体を返さず、視覚確認に成功したとは記録しない。N/M/座標/ゲート/端子の最大値は推測しない。公式Lineの15MB提出制限は本文で読めるが、他の数値まで確認済みとはしない。

## 成果物と整合検査

- `data/corpus-audits/ioi-2019.json`: 全6題、資料状態、根からの経路、最初の不足、技巧案、確認済み/未確認を記録。
- `research/snapshots/ioi-2019-flow.json.gz` と `ioi-2019-technique.json.gz`: 監査開始時の分岐と技巧metadataのraw JSON。展開したbytesのSHAを監査記録に保存。
- `research/snapshots/ioi-2019-manifest.json`: 開始時のmetadata・MDXなど594ファイルのSHA台帳。MDX全472本の元コピーは作業時点の一時領域で検査し、恒久snapshotは分岐とmetadataに限定する。
- `tests/ioi-2019-fixed-corpus.test.mjs`: 製品の歩行処理を使わず、凍結JSONから全6経路と最初の不足を独立再生。公式の固定ID・日付、主要手順確認3題と未確認3題、原典数値の未確認も確認する。
- `research/probes/ioi-2019-probe.py` と `ioi-2019-shoes-probe.py`: 限定した小規模比較。技巧の再利用API・最大制約実装の完成とは扱わない。

初回監査は原典6/6、解説取得6/6、主要手順確認3/6、確認済み技巧不足3件、主要細部未確認3件、covered0件。`fixedCorpusResearchComplete`・`fixedCorpusCoverageComplete`・`globalCoverageComplete` は全てfalse。


## 2026年10月15日のRectの後続確認と不足解消

初回のRectは分類・解法確認・数値上限の未確認を保った。日本委員会/大会配布原典の検索本文で縦横1..2500、高さ0..7000000と2019-08-06を再確認し、公式Reviewの欠落式や16構造全てを確認済みとはせず、最大セルからの候補完全性と行・列の高い両端の連続出現を独立証明した。初回行を上書きせず `subsequentSolutionReviews` 1件と `resolution.sourceVerification` を追加し、完全C++20・根の特徴経路へ接続した。現在の固定6題の研究/記事対応は4/6で、Line/Walkは残る。

`grid-enclosing-higher-boundary-rectangle-candidates` の公開fenceを、全小盤のliteral四外側セル比較・2500角最大7構成・通常/ASanで2884927件確認。別oracleは区間最大と違反prefixで394563盤/190182034長方形を照合し、全最大セルwitness・重複・不成立候補も検査した。実行は `scripts/check_enclosed_rectangle_candidates_cpp.py` と `research/probes/higher-boundary-rectangle-independent.py`。原典・証明・全API/資源範囲・独立レビューはresearch sidecarに分離した。

## 2026年10月15日のWalkの後続確認と不足解消

初回の全6行、分類、原典数値・公式解説の未確認flag、凍結経路、既存4resolutionを保持した。Walkへ後続の独立解法確認を一件とresolutionを追加し、研究・記事対応は5/6となった。Lineは未確認のまま残る。後続reviewを除くと研究・対応とも4/6、resolutionだけを除くと研究5/6・対応4/6となることを回帰検査で確認した。

主催LVA/IDNなどの翻訳原典からN/M各1..100000、真に増加する横座標0..10億、高さ1..10億、通路端点・高さ・接触条件、異なる始終点を再取得した。英語/JPN原典の抽出で欠けた不達返値は、主催MAC実装段落とAZE本文で-1と確認した。競技日は日本委員会一覧の2019-08-08、難度はnullとする。PDF画像の取得に成功したとは記録しない。

`skywalk-endpoint-sparse-shortest-path` は、一般の始点・終点の左右で通路を分け、上端が部分通路の内部にある鉛直辺を除く。矩形への進入を側辺・上辺へ置き換え、上端高さ順の不要辺数の辞書式最小性で、全ての不要辺を同時に除いても最短距離を保つことを独立証明した。一般の始終点に横方向の単調性を仮定しない。厳密に低い通路への接続、同高さ端接触、同座標統合、水平辺の縮約、各構築段階のメモリ、入力検査も確認した。公式Reviewに省かれた証明を原文で確認済みとはせず、独立証明として扱う。

完全C++20は原典の値渡し入口も含み、通路なしと同一始終点を拡張として許す。全小N1..4・高さ1..3・隣接横座標差1/2の有効通路集合108279例、1716019始終点対、4000乱択を、全交点を直接作る別グラフと照合した。最大N=M100000の7構成には、全交点が100億個になる配置、内部の短い二つの始終点、同高さ接触、不達、64ビット距離を含む。作者/root/別review者の通常・ASan/UBSanで9280397検査、checksum9377741248886004889が一致した。

追加の独立oracleは全ての単位格子辺を張るBFSであり、全交点の圧縮もDijkstra法も使わない。屋根の不要部分の高さ変更と、一接触だけの行き止まりビル挿入も確認し、10624入力・1750018検査で一致した。恒久入口は `scripts/check_skywalk_sparse_shortest_path_cpp.py` と `research/probes/skywalk-shortest-path-independent.py`。新三条件の否定/不明、両表示、共有・戻る、旧516経路と462図の全項目は `tests/skywalk-flow.test.mjs` で保護する。


## 2026年10月15日のLineの後続確認と不足解消

初回Lineのunconfirmed・数値未確認・officialEditorialVerified:false・凍結経路など全項目と既存5resolutionを保持し、一件の後続独立解法確認とresolutionを追加した。研究・記事対応は6/6となった。原典PDF全4頁を実画像で読み、数値制約・全採点表77値・原点を省く出力・15MB・描画器だけの1000本制限を作者/root/別review者で確認した。公式Reviewが省略する接続を確認済み原文へ帰属せず、二単調鎖を逆向き平行な初線分でつなぎ、螺旋の末尾を下又は左へ保つ固定順構築として独立証明した。

完全C++20は全点をN+3本以内で覆い、0〜10億+1の座標に収まる。原点込みpathと、原点を出さないwriterを用意した。通常/ASanは全N1〜9順位順列409113、literal点線分比較、乱択/変換/最大10万点の15生成入力で28709275検査に一致。別の支持座標辞書oracleと厳密増加座標変換は13310052検査に一致した。

原大会の固定10入力はGit-LFS/バイナリ取得と、承認済みcurlのDNS失敗で未取得・実行0件である。生成した採点表と同じ点数の入力を、実大会入力として数えない。普遍的構築の証明と実入力を実行したかは分ける。恒久checkerは `scripts/check_orthogonal_point_cover_cpp.py`、追加probeは `research/probes/orthogonal-point-cover-independent.py`。統合結果は `research/verification-2026-10-15-routing-line.json` に保存した。
