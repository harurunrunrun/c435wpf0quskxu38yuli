# IOI 2018 固定6題の初回監査

対象は主催公式の **Contest 1 / Contest 2 各3題、計6題**。競技日1は **2018-09-03**、競技日2は **2018-09-05**。練習4題（Bubble Sort 2 / Road Service / Timecard / Xylophone）、Implementation Notice、翻訳の重複は対象外とした。全題の難度は公式値が分からないため `null`。

- [主催公式・全課題一覧](https://ioi2018.jp/competition/tasks/)：Combo / Seats / Werewolf、Mechanical Doll / Highway Tolls / Meetings の全6題。
- [日本委員会・日付と日本語/英語原典・Review](https://www2.ioi-jp.org/ioi/2018/tasks/index.html)：競技日1/2の日付を確認。練習は2018-09-02であり、本競技と混ぜない。
- [IOI公式履歴アーカイブ](https://ioi.te.lv/locations/ioi18/contest/)：同じ6題とReviewを照合。

技巧検索前に `data/corpus-audits/ioi-2018.json` の `selection` へ全ID・題名・日付を固定した時刻はUTC **2026-10-15T06:55:35.241243**。それより前の **06:54:51.559241** に現在の製品を凍結した。

## 開始スナップショット

初回作業時に482 metadata・482 MDX・404 specific・449図・503既存walk・15分野根を作業用snapshotへ固定。metadata/refs/features/MDX/flow/runtime/progress/compilerなど607ファイルのraw bytesをコピーし、コピー後に元と各SHAを再比較して変更0を確認した。後続の共有記事・データ追加を、この開始状態へ遡及しない。

| 対象 | SHA256 |
|---|---|
| manifest raw bytes | `bc97c90a87d59f384a931ca5e315799372169b8ac5a78fbb4b3bced5d9a600bf` |
| manifest entriesのcompact JSON | `ccdb633a48e808042bd11343f074010512219d5406b5e3d47f872e55e6648111` |
| 開始flow raw JSON | `51b48b37676eb0d9d19a5306bd736b83950c8573ff4790bddb6853b4e7b0ea2e` |
| 全metadataのaggregate JSON | `74d4857883b0cb6e5e3a8a4518d64143ddc334a534aee4b26797370ba02341be` |

初回には607ファイルの再hash、題名・IDの一意性、482 MDXとの対応を確認した。恒久保存するrawデータは `research/snapshots/ioi-2018-flow.json.gz` と `ioi-2018-technique.json.gz` の2種だけで、展開bytesは元JSONと一致する。607件のSHA台帳と元manifestのraw bytesは `ioi-2018-manifest.json` に保持するが、482 MDXや他の605ファイルの本文は恒久保存していない。現在の共有本文を初回の凍結本文とみなして再検証しない。

元の作業用manifest raw SHAは `bc97c90a87d59f384a931ca5e315799372169b8ac5a78fbb4b3bced5d9a600bf`、パスと保存範囲を追記した恒久manifest raw SHAは `5f4e3a6d77568ffdd1fbd25f6632c6520bc06b09ec5713b5fcf82385c8cca104`。`manifestEntriesSha256` は607件の台帳内容を表すSHAであり、どちらのファイル全体SHAとも別である。元manifestのbytesはbase64で埋め込み、元SHA自体も恒久ファイルだけから再計算できる。

## 全件の根からの経路

技巧名から経路を探すのではなく、原典の入力特徴を使い、凍結された15分野根から再生した。全質問・回答ID・表示ラベル・停止ノードの全選択肢はaudit JSONに保持する。独立raw JSON walkerと、凍結TypeScriptをコンパイルした製品walkerの両方で一致した。

| 日・公式ID | canonical route | 止まる場所 | 初回判定 |
|---|---|---|---|
| Day1 `combo` | interactive-oracles → other | interactive-oracles/general-result (`interactive`) | 確認済みの具体技巧不足 |
| Day1 `seats` | grid-arrangements → color-numbers | grid-color-numbers/goal | 確認済みの具体技巧不足 |
| Day1 `werewolf` | graphs → network-connection → connectivity → static-or-add → static | connectivity-static-or-add/components (`bfs`,`union-find`) | 確認済みの具体技巧不足 |
| Day2 `doll` | thinking → operation-goals | thinking-operation-goals/reason-task | 確認済みの具体技巧不足 |
| Day2 `highway` | interactive-oracles → other | interactive-oracles/general-result (`interactive`) | 確認済みの具体技巧不足 |
| Day2 `meetings` | ranges → aggregate-goals → static → aggregate-forms | range-static-aggregate-forms/kind | 確認済みの具体技巧不足 |

汎用 `interactive` や `bfs`/`union-find` への到達をcoverageにしない。`actualReachedTechniqueIds` と、完成記事を意味する `expectedTechniqueIds=[]` を区別した。Werewolfの元の辺は固定なので静的な分岐を選べるが、その結果記事に二つの頂点閾値・変身・成分共通部分の処理はない。Dollは状態付き交互出口であり、距離や個数を指定する静的グラフの構築へ無理に進めない。

開始時のrefs/featuresを6題の題名・ID・URLで検索し、一致する原典登録は0件。新候補の6技巧IDも全て未登録だった。関連する既存記事の範囲・入口/APIを読み、元ファイルSHAと適用できない理由を `relatedArticleReview` に残した。既存参照を重複登録する作業はしていない。

## Combo：先頭一意の接頭辞oracleを一質問へ多重化

候補IDは `unique-first-symbol-prefix-oracle-multiplexing`。

[原典](https://www2.ioi-jp.org/ioi/2018/tasks/day1-combo.pdf) と [公式Review](https://www2.ioi-jp.org/ioi/2018/tasks/day1-combo-review.pdf) を確認した。未知文字列の先頭文字は後半に現れず、質問内に含まれる未知列の最長接頭辞の長さが返る。一般的な等値質問ではない。

先頭を2質問で確定し、残る文字をa,b,c、既知prefixをPとする。中間位置では `Paa + Pab + Pac + Pb` と質問する。次文字がaなら、その次はa/b/cのいずれかであり返答は `|P|+2` 以上。bなら `|P|+1`、cなら `|P|` になる。先頭文字がPの最初にしかないので、秘密prefixの開始候補は質問中のPの開始点だけであり、連結境界に偽の開始点が増えない。

中間は `|P|<=N−2` で質問長 `4|P|+7<=4N−1`。先頭2回、中間N−2回、最後2回で満点のN+2回を満たす。N=1は先頭を決めて終わる。文字列生成の総時間はO(N²)、空間O(N)。oracle内の計算をlocal complexityへ混ぜない。

probeでは長さ1〜8の全13,120合法秘密列を、全prefixの部分文字列出現を直接調べるoracleで確認した。既存 `interactive` は通信の共通処理、`prefix-border-occurrences` は既知列の接頭辞出現集約であり、この質問列と予算証明を含まない。再利用callback API・返答整合・N=2000での実装検証は今後の記事で必要。

## Seats：全prefixの矩形性を局所の角の最小値へ

候補IDは `dynamic-grid-prefix-rectangle-corner-minimum-count`。

[原典](https://www2.ioi-jp.org/ioi/2018/tasks/day1-seats.pdf) と [公式Review](https://www2.ioi-jp.org/ioi/2018/tasks/day1-seats-review.pdf) を確認した。prefix番号のセルを黒、外部を白とする。2×2窓で黒が1個/3個の数をC1/C3とすると、矩形条件はC1=4,C3=0である。

この幾何条件も独立に確認した。最上行・最下行の左右端からC1>=4。C3=0なら、隣り合う行の黒runが縦に接続すると両runの範囲が完全一致する。片端だけがはみ出せば黒3窓になるためである。従って各4近傍成分は長方形。

成分矩形がC個、斜めの角接触がD個ならC1=4C−2D。角接触グラフは単純平面で三角形を持たない。三矩形が対ごとに接すると、軸区間のHelly性により共通点があり、その三象限で黒3窓を生じる。C>=3ではD<=2C−4、C=2ではD<=1なのでC1=4にはC=1が必要。逆は明らか。よって `F=C1+C3>=4`、`F=4 iff矩形` と一つの最小値条件にできる。

各格子頂点の四隣接セル番号をa<=b<=c<=d、外部はsentinel P=HWとする。prefix末尾tについて、その窓のFへの寄与は `[a,b)` と `[c,d)` へ+1。交換前の高々8頂点の寄与を引き、交換後を加えれば、番号軸のrange add/min/countだけで全prefixの矩形数を保てる。全体minは必ず4である（全格子prefixが矩形）。初期は差分配列からO(P)で構築でき、全体O(P+Q logP)時間・O(P)空間。

全1〜4行/列の74,938非空bitmapで角条件と直接bbox面積を比較。さらに1,481全順列・21,784全交換で局所の番号区間更新とprefix面積条件が一致した。一般 `lazy-segment-tree` や静的 `grid-rectangle-components-euler-boundary` は、交換する順列とこの角不変量を扱わない。完成記事には窓の重複除去、sentinel、1行/列、min/count木と最大P/Qの検証が必要。

## Werewolf：二つの閾値成分木の交差を二次元へ

候補IDは `two-threshold-component-merge-trees-rectangle-intersection`。

[原典](https://www2.ioi-jp.org/ioi/2018/tasks/day1-werewolf.pdf) と [公式Review](https://www2.ioi-jp.org/ioi/2018/tasks/day1-werewolf-review.pdf) を確認した。人間は番号>=L、狼は番号<=Rを通り、途中の同じ頂点で一回だけ変身する。

人間でSから到達できる成分と、狼でEから逆向きに到達できる成分が交わることが必要十分。頂点を降順に有効化するDSU併合木と、昇順の木を作り、各queryでその時点のcomponent nodeを保存する。併合のたび新しい親を作るので、過去成分の葉集合は後で変わらない。各木は最大2N−1ノード。

それぞれの成分は葉Euler順の一つの半開区間になる。ただし**二つの木の順序は別物**なので、区間同士を一次元で交差させてはいけない。各元頂点vを二順序の座標点 `(inLow[v],inHigh[v])` にし、二成分の区間の積長方形に点があるかを求める。x端のprefix差2イベントとy Fenwickの範囲和で処理でき、全体O((N+M)α(N)+(N+Q)log(N+Q))時間、O(N+M+Q)空間。

N=2〜5の全771連結単純グラフ・全115,398合法queryで、実際に二併合木・Euler・長方形sweep/Fenwickを構成し、直接二状態BFSと一致した。probeは閾値/始点を全保存する小規模版であり、原典最大の実装では必要なQ個だけを保存する。既存 `union-find` / `subtree-euler-interval` / `offline-queries` はこの二木の対応点を作らない。最大規模では再帰なしの構築とinclusive閾値/半開区間の検証が必要。

## Doll：交互スイッチを共有routerへ集め、空間的な不要葉を刈る

候補IDは `alternating-switch-bit-reversal-pruned-router`。

[原典](https://www2.ioi-jp.org/ioi/2018/tasks/day2-doll.pdf) と [公式Review](https://www2.ioi-jp.org/ioi/2018/tasks/day2-doll-review.pdf) を確認した。初回基点復帰までに指定列を厳密に再生するだけでなく、全スイッチがXへ戻る必要がある。出口の使い方を固定した通常の関数グラフではない。

全トリガーと基点の出口を一つのrouter根へ向け、K=N+1個の出力列 `A+[0]` を実現する。P=nextpow2(K)葉・高さhの完全二分スイッチ木は、葉をbit-reversal順で訪れる。空間的に先頭P−K葉を根へ戻し、全部が不要な部分木はまとめて根へ向ければ、不要スイッチも除去できる。残る葉を実際の訪問順に並べて `A+[0]` を割り当てる。

最後に訪問される葉はP−1であり、必ず残す。そこだけを0にすれば、初回基点復帰は全周期の最後で、保持した全スイッチの訪問回数が偶数になる。保持ノード数は

`S=sum(j=1..h) ceil((N+1)/2^j)=N−popcount(N)+h<=N+floor(log2N)`。

任意の葉を無造作に消しても個数上界は得られない。「空間的に連続する不要葉」と「時間的なbit-reversal訪問順」を区別する必要がある。P<=262144、h<=18なので状態変化はP*h<=4,718,592で20,000,000以内。

全2トリガー列・長さ1〜8の510件を、最初に0へ戻るまで本当にsimulateし、列・全X・スイッチ上界を確認。原典最大N=200000/M=100000もsimulateし、S=200012、状態変化3,836,286で成功した。これは監査用Python構築であり、可視C++20/APIを完成したとはしない。

## Highway：最短路上の一辺から未知両端を50質問で絞る

候補IDは `binary-weight-distance-oracle-edge-split-endpoint-search`。

[原典](https://www2.ioi-jp.org/ioi/2018/tasks/day2-highway.pdf) と [公式Review](https://www2.ioi-jp.org/ioi/2018/tasks/day2-highway-review.pdf) を確認した。既知グラフの各辺をA/Bに変えた際の未知二点間最短距離を質問する。既存 `interactive-tree-diameter` の「指定二点の距離」とは質問APIが違う。

全Aのbaseline Dを一回取得し、辺番号のprefixをBにすると初めて距離>Dになる辺e=(u,v)を二分する。直前にはprefixを避ける元の最短路があり、次に重くしたeはその路上にある。複数最短路でも成立する。

その最短路をS..u−v..Tと向ければ、Sはuに、Tはvに厳密に近い。そうでなければeを通らず短縮できる。二BFS距離により厳密近接集合U,Vを作ると、各集合の根への最短路は集合から出ない。各集合内BFS木とeだけをA、その他を全てBにすれば、長さDのA路が残り、そのA路は木上で一意になる。

一意A路の辺の一部をBへ変えたとき、距離がDのままかは、その辺を一意路が避けるかと一致する。Bを含む路は、もとのhop最短距離以上の辺数を使いB>AなのでDを超える。各木の祖先が先の頂点順で、親辺suffixをBにする質問を二分すれば、その最大番号である未知端点が分かる。根自身も候補に含む。

質問数は `1+ceil(log2M)+ceil(log2|U|)+ceil(log2|V|)`。M<=130000で17、U/Vの合計<=90000から後二項は32以下（33になる最小和は65537+32769>90000）。よって満点50回以内。queryベクトル作成込みlocal時間O((N+M)log(N+M))、空間O(N+M)。返答は最大(N−1)B<9×10^13でint64に収まる。

全771連結単純グラフN=2〜5・全未知対×三つの料金設定、計22,563件で、各実質問を独立Dijkstraで回答し、未知対の復元を確認した。N=90000で全二集合サイズのceil log和も直接調べた。最大規模APIと実callback予算検査は、記事で別途必要。

## Meetings：Cartesian prefix費用と一本交差の一次式包絡

候補IDは `cartesian-prefix-meeting-cost-single-cross-envelope`。

[原典](https://www2.ioi-jp.org/ioi/2018/tasks/day2-meetings.pdf) と [公式Review](https://www2.ioi-jp.org/ioi/2018/tasks/day2-meetings-review.pdf) を確認した。PDF抽出から消える具体式は、[IOI本部掲載のTomasz Idziaszek解答冊子](https://ioinformatics.org/files/booklet-ioi2018.pdf) と [著者本人の公開HTML](https://www.algonotes.com/en/solutions-ioi2018/) で確認し、以下を独立に検査した。著者冊子は2020年3月改訂で、当日の公式Reviewとは区別する。

最大Cartesian treeの根v、部分木区間[l,r]に対し、各prefixの最適費用S_vを持つ。左部分木の全費用をLcost、右prefix k個の最適費用をR(k)とすると、右側を含むprefix費用は

`min(F(k),G(k)) = min(Lcost+(k+1)H_v, (v−l+1)H_v+R(k))`。

会場がvより左なら、vから右の参加者は全員H_vを払う。会場が右なら、左とvは全員H_vを払う。この二つが全てを尽くす。v自身を選ぶ費用も、空側または他の最適会場で同じか小さい候補として含められる。

右prefixを一人延ばしても以前の最適会場に追加する費用はH_v以下なので、`F(k+1)−G(k+1) >= F(k)−G(k)`。従って前半はF、後半はGで、一度しか交差しない。各S_vを区分一次fragmentとして持ち、左prefixを保持、中心一点を追加し、右prefixの初めだけ一本の直線で上書きして残りに定数を加える。各ノードで新fragmentは高々2個、消したfragmentは復活しない。

一般区間[l,r]の最大vに対して、会場が右側の候補 `(v−l+1)H_v + cost(v+1,r)` を、vの右子のprefix表から取得できる。queryは表が破壊される前にその子へ登録して読む。反転した配列でも同じ処理をしてminを取れば左側も尽くす。

**同高さの具体反例を保存する。** `[2,1,2]` 全区間の最適費用は5。両向きでそれぞれ「右端の最大」を選ぶと、どちらも端の2を会場候補側から外し、6を返す。Cartesian比較の第二キーを元indexとして固定し、反転後も元indexの優先順位を保つ必要がある。修正後の全3,279配列（高さ1〜3、N<=7）・全81,192区間と、全63,084 Cartesian prefix費用が直接会場列挙に一致した。

圧縮実装ではglobal位置のmapからfragmentを探し、全削除を一回ずつchargeする。offset調整の大小には、生存fragment数ではなく元部分木の頂点数を使うと安全に証明できる。移動をfragmentの出生元頂点へchargeすれば、その元頂点を含む集団が小側になるたびに倍増し、削除でfragment数が減ってもO(NlogN)の証明は崩れない。交点とqueryの探索を含めO((N+Q)logN)時間、O(N+Q)空間という満点方針を確認した。

ただし**今回のprobeは明示配列DPで、圧縮map/offset構築そのものではない**。既存 `skyline-cartesian-star-paths` は祖先パスpacking、`subarray-extremum-contribution` は全区間最大値の総和で、この最適会場選択を扱わない。新記事では750000長鎖の反復処理、fragment寿命、mass/offset償却、等値・空側・端点・int64の最大検査が必要。著者公開コードのmap keyを `const_cast` で変える箇所を、そのまま安全な再利用C++20として転載しない。

## 原典数値の確認と残る実装作業

通常の英日PDF抽出には数値が欠けるが、主催hostの翻訳版の検索本文では次を読めた。画像を目視したとは記録しない。AOI公開repoには2018ディレクトリがなく、2019以降と同じ取得経路が使えたとはしない。

| 公式ID | 確認できた満点範囲・予算 | 数値根拠 |
|---|---|---|
| combo | N=1..2000、質問長0..4N、hard8000回・満点N+2回 | [IND原典](https://ioi2018.jp/tasks/contest1/IND-combo.pdf) |
| seats | H,W正、HW<=10^6、Q=1..50000、各交換a!=b | [TWN原典](https://ioi2018.jp/tasks/contest1/TWN-seats.pdf) |
| werewolf | N=2..200000、N−1<=M<=400000、Q=1..200000、単純連結、L<=S、E<=R、S!=E、L<=R | [CUB原典](https://ioi2018.jp/tasks/contest1/CUB-werewolf.pdf) |
| doll | M=1..100000、N=1..200000、S<=400000、状態反転<=20000000、満点S<=N+log2N | [SYR原典](https://ioi2018.jp/tasks/contest2/SYR-doll.pdf)、[英語原典のgrader失敗条件](https://www2.ioi-jp.org/ioi/2018/tasks/day2-doll.pdf) |
| highway | N=2..90000、M<=130000、1<=A<B<=10^9、hard100回・満点50回 | [HKG原典](https://ioi2018.jp/tasks/contest2/HKG-highway.pdf) |
| meetings | N,Q=1..750000、高さ1..10^9、0<=L<=R<N、query対は相異なる | [TWN原典](https://ioi2018.jp/tasks/contest2/TWN-meetings.pdf) |

初回結果は**原典6/6、公式Review取得6/6、主要手順確認6/6、原典数値確認6/6、具体技巧不足6、covered0**。主要補題未確認は今回は0だが、再利用C++20/APIと全最大制約の完成検査は全題未実施であり、別の未完了項目として保持する。`fixedCorpusResearchComplete=true` はこの固定6題の主要手順の調査が終わった意味に限る。`fixedCorpusCoverageComplete=false`、`globalCoverageComplete=false`、記事解消完了もfalseである。

## 恒久保存と再現

- `data/corpus-audits/ioi-2018.json`：初回6行の全field、分類、状態、資料provenanceを維持。元の全行・status・selectionを別々のSHAでも固定した。
- `research/snapshots/ioi-2018-{flow,technique}.json.gz`：開始flowとaggregate metadataの元JSON bytes。全MDXを永久保存したものではない。
- `research/snapshots/ioi-2018-manifest.json`：初回607件のSHA台帳、元manifestのbytes/SHA、実際の永続保存範囲。
- `research/probes/ioi-2018-research-checks.py` と `ioi-2018-research-checks-results.json`：6題の限定した独立比較。引数なしでは表示だけを行い、出力先を引数に渡した場合だけ結果JSONを書き出す。
- `research/probes/ioi-2018-independent-review.py` と `.json`：独立再確認、原典provenance、研究/coverageの区別、追加境界検査。607ファイル全体の再hashは初回レビューの実績であり、恒久ファイルからの再実行では保存された2種と元SHA台帳を検証する。
- `tests/ioi-2018-fixed-corpus.test.mjs`：固定6対象・日程・数値・元/恒久manifest SHA・元全行/status・凍結flowからの全質問と回答ラベル・停止位置・関連IDと不足IDを再確認する。

再現コマンドは `python3 research/probes/ioi-2018-research-checks.py`、`python3 research/probes/ioi-2018-independent-review.py`、`node tests/ioi-2018-fixed-corpus.test.mjs`。検査を再実行してもコミット済みの初回結果は上書きしない。

独立レビューではMeetingsの同一元最大IDによる5/誤tieによる6、Doll全N=1..200000のswitch数と反転上限・追加99長の実simulate、Highwayの43全連結小グラフ・全1938重みvector・11418固定対のliteral単純path/Dijkstra一致も確認した。具体記事や再利用C++20の完成は全6題とも別作業である。

この保存作業で既存coverage-plan、sources、ledger、README、flows、walksは編集していない。追加案は別のJSONにまとめ、登録はrootが行う。環境ファイル読取、外部push・公開も行っていない。


## 2026年10月15日の不足解消

初回の6行・停止位置・分類・状態・snapshotは保持し、後続の完成作業を各行の `resolution` と研究sidecarへ追加した。Comboに続き、Seats、Werewolf、Doll、Highway、Meetingsを全て技巧記事・使用例・分野の根からの経路へ接続した。初回の covered 0/6 を書き換えず、現在の判定は研究6/6・記事対応6/6である。全世界の網羅完了を意味しない。

Meetingsは `cartesian-prefix-meeting-cost-single-cross-envelope` に統合した。単一の可視C++20から直接抽出し、元添字固定tie・空側・一交差・破壊的併合の寿命・元頂点数による償却・全反復・64bit中間量を独立に確認した。全小列51367件の全1766247区間、一方向候補1288632件、500乱択列、最大N=Q750000を7構成、通常/ASan+UBSanとも10223222 checks/checksum14312679095217143898を再現した。別の変換・部分区間検査1255051件、最大一般高さ3構成/192長区間の全会場monotone-stack oracleも一致した。

恒久の実行入口は `scripts/check_cartesian_meeting_cost_cpp.py`、`research/probes/cartesian-meeting-cost-{metamorphic,large}.py`、`tests/ioi-2018-meetings-{cpp,flow}.test.mjs`。独立レビューは `research/probes/cartesian-meeting-cost-independent-review.json`、出典・証明・全API範囲と作者/root実測は `research/technique-verifications/cartesian-prefix-meeting-cost-single-cross-envelope.json` に分離している。研究probeを完成APIへ言い換えず、後続実装を別記録にした。
