# IOI 2017 固定6題の初回監査

対象は日本委員会の[公式課題一覧](https://www2.ioi-jp.org/ioi/2017/tasks/index.html)の競技日1・2各3題であり、母数は6。Day1は2017-07-30の Nowruz / Wiring / Toy Train、Day2は2017-08-01の The Big Prize / Simurgh / Ancient Books。練習4題、Implementation Notice、翻訳の重複を除く。rootが技巧照合前に保存したselectionのraw SHAは `3b93bcdae6d32392e837c062c3db01d16d991abc2c679b59b17624d82cc2e762`。本監査でその6題を入れ替えていない。原典ヘッダからID `nowruz,wiring,train,prize,simurgh,books` を確認した。数値難度は全てnull。

[IOI公式履歴アーカイブ](https://ioi.te.lv/locations/ioi17/contest/)にも同じ競技日2群と全6題があり、英語原典・各国翻訳・Editorialへの実リンクを確認した。解説URLを題名から推測していない。この一覧のEditorialは公式配布資料として扱い、課題著者と解説本文の署名を混同しない。Booksの15頁資料だけは署名Daniel Grafを確認できる。ほかのEditorialに個人署名を補わない。

## 初回凍結と保存範囲

`/tmp/flowchartcp-ioi2017-baseline` の初回coreは921 rawファイル。data/src/scripts/testsとpackage/config/READMEをコピー前後に全件SHA比較し、全コピーも照合した。498 MDX・498 metadata・420 specific・465図・519walk・519参照・15分野根が基準である。core台帳SHAは `718d89756d8413a1836046b321415fa220edb68718173fb5797039574fa7e71e`、flow raw SHAは `5e86b750545b089d2e1427c4a956287e6925f8d69cabae4a89cfa1e5a1bb0c38`、walk raw SHAは `4d0fd03bc210fd47f941af4ba336289d354a9012d9e3238f5b34b3a56b680adb`。`.env*`は列挙対象から除き、内容を読んでいない。

その後、凍結TypeScriptの製品walkerまで動かすためにvendor/compilerとpublicの571ファイルを別時点で安定コピーした。合計1492 rawの各SHAも照合したが、この依存拡張時にはrootの共有data更新が始まっていた。初回921ファイルはコピーし直していない。初回coreのbefore/afterは `core-hashes-before.json` / `core-hashes-after.json`、全1492の各epochでのbefore/afterは `hashes-before.json` / `hashes-after.json`、拡張時に変化していた共有ファイル一覧はmanifestに記録した。後時点public SVGを初回図の根拠へ使わず、初回の465図を519/後続図数などへ遡及しない。動的再生は初回 `src/lib/flow.ts` と初回 `data/flows.json` を、凍結vendorのTypeScriptコンパイラで実行する。

全1492raw台帳SHAは `1c2d89f4e92c6dcf6279b26a1a206082331906385f8be2a866e10f50e0765bac`。初回metadata/refsのaggregate JSONはraw群から作った派生資料で、rawファイルの代わりではない。全MDX・元JSON・runtimeそのものもbaselineに保存してある。初回selectionのbytesもbaselineへ複製した。

## 原典の数値根拠

6原典の本文を読んだ後、全6Editorialを読んでから、凍結教材との照合を行った。英語PDF抽出から数式が欠ける箇所は、公式アーカイブが直接配布する翻訳の検索本文で補完した。次のURLとqueryは実際に数値を読めたもの。PDF画像を実際に目視したとは主張しない。web screenshotが参照だけを返して画像を渡さなかった試行も、画像確認に数えない。

| ID | 満点範囲・重要な規約 | 数値を読めた一次資料と検索query |
|---|---|---|
| nowruz | 行/列1..1024、固定10入力のoutput-only、`.`を`X`へだけ変えられる。残す自由セルの誘導グラフは木、次数1が隠れ場所。各入力 `min(10,10*l/k)` を小数2桁へ切り捨て、l>=kで10点、全入力満点解の存在保証。k独立の上限は抽出に見える条件としては書かれていない | [BRA原典](https://ioi.te.lv/locations/ioi17/contest/day1/nowruz/nowruz-BRA.pdf)、query `site:ioi.te.lv/locations/ioi17/contest/day1/nowruz/ "m" "n" "1024"`。固定10入力は[NOR原典](https://ioi.te.lv/locations/ioi17/contest/day1/nowruz/nowruz-NOR.pdf)と[LVA原典](https://ioi.te.lv/locations/ioi17/contest/day1/nowruz/nowruz-LVA.pdf)の検索本文でも確認 |
| wiring | 赤/青各1..100000点、座標0..1e9、各列昇順・全点の座標が相異なる、異色へ各点少なくとも一本、次数上限なし、総長最小・int64 | [JPN原典](https://ioi.te.lv/locations/ioi17/contest/day1/wiring/wiring-JPN.pdf)、query `site:ioi.te.lv/locations/ioi17/contest/day1/wiring/wiring-JPN.pdf "100000"` |
| train | N1..5000、N<=M<=20000、出次数1以上、充電駅1以上、loop可・同一有向辺重複不可、所有者固定、初訪問で選んだ出辺は変更不可。満充電はN本を走れ、次の一本で停止 | [UZB配布原典](https://ioi.te.lv/locations/ioi17/contest/day1/train/train-UZB.pdf)、query `site:ioi.te.lv/locations/ioi17/contest/day1/train/train-UZB.pdf "20" "5000"`。初訪問/固定/終局は[公式英語](https://ioi.te.lv/locations/ioi17/contest/day1/train.pdf)と[日本語](https://www2.ioi-jp.org/ioi/2017/tasks/day1-train-JPN.pdf)本文 |
| prize | N3..200000、type1は一つ、type t-1 がk個ならtype tはk²より多い。ask位置0..N-1、左右の厳密に高価な個数を返す。適応graderあり。hard10000、満点5000以下、5000<q<=6000は80-(q-5000)/100、6000<q<=10000は70（いずれも80点小課題の配点） | [SWE原典](https://ioi.te.lv/locations/ioi17/contest/day2/prize/prize-SWE.pdf)、query `site:ioi.te.lv/locations/ioi17/contest/day2/prize/prize-SWE.pdf "Constraints"`。同PDFのQuestions/Score検索本文で全4行を確認 |
| simurgh | N2..500、N-1<=M<=N(N-1)/2、単純連結無向。隠れたN-1本も全域木。質問は必ず全域木で、その共通辺数が返る。小課題のq30000/完全グラフq12000/最終q8000を区別 | [AZE原典](https://ioi.te.lv/locations/ioi17/contest/day2/simurgh/simurgh-AZE.pdf)、query `site:ioi.te.lv/locations/ioi17/contest/day2/simurgh/simurgh-AZE.pdf "8000"`。最終小課題30点の8000、先行3群30000と完全グラフ群12000を読んだ。サンプルgraderの30000だけを満点制限へしない |
| books | N1..1000000、s0..N-1、pは0..N-1の順列。手に持てるのは一冊、拾う/交換/空位置へ置く、歩行距離|i-j|だけ課金、最後sへ戻る、int64 | [KOR最終原典](https://ioi.te.lv/locations/ioi17/contest/day2/books/books-KOR.pdf)、query `site:ioi.te.lv/locations/ioi17/contest/day2/books "Constraints" "000"`。最終5小課題（12/10/28/20/30点）も同時確認。後述Library稿の旧N/API/小課題表は本選数値の根拠へ使わない |

## 根からの経路と初回不足

全15分野根の表示選択肢を検討し、原典の特徴から次の経路を選んだ。問い・回答ID・表示ラベル・停止ノードの全選択肢はaudit/probe JSONに保存する。独立raw JSON walkerと、凍結製品runtimeの両方で全6経路を照合した。汎用記事へ到達した場合も到達を隠さず、gapの停止位置を同じ実ノードへ合わせた。具体的な新分岐を前の質問へ置く案は `proposedBranchAt` に分離する。

| ID | choices | 実際の停止 | 初回判定 |
|---|---|---|---|
| nowruz | fixed-output / [] | fixed-output/output-result、汎用output-only | 未確認（全10出力の満点未確認） |
| wiring | flow-matching / quantity-goals,costs,yes | assignment-quantity-goals/mincost、汎用min-cost-flow | 具体技巧不足 |
| train | game-probability / win,other,no | game-general/fallback、汎用state-design | 具体技巧不足 |
| prize | interactive-oracles / other | interactive-oracles/general-result、汎用interactive | 未確認（満点質問数証明） |
| simurgh | interactive-oracles / other | interactive-oracles/general-result、汎用interactive | 具体技巧不足 |
| books | ranges / sequence-changes,reorder-cost | range-sequence-changes/reorder-operation質問 | 具体技巧不足 |

Wiringは重複使用禁止のmatching枝へ進まない。数量・費用の一般枝へは進めるので、その汎用結果まで正直に記録した。Booksの運搬は好きな位置への移動一回の費用でも、自由な二位置交換回数でもない。Toy Trainは位置所有者が決めるため同じ人の選択が連続し得る。「二人が交互」のguardにはnoとなり、引分終局の枝へねじ込まない。Nowruzには出力形式を直接表すfixed-output根を使った。

全498既存記事のmetadata/ref/featureを6題の原典URL・ID・題名で検索し、既登録原典との一致0。近接13種類の記事を本文・全コードまで読み、原典へ使えない条件と元SHAを個別にauditへ保存した。matching、retrograde-winning-draw、permutation-cycle-minimum-swapsは凍結C++fenceを実際に抽出・コンパイルし、モデルの差が見える小例も実行した。これは既存記事のバグ報告でも、IOI2017の完成API検査でもない。

## Nowruz：誘導木を保つ一近傍追加と葉の差分

[原典](https://www2.ioi-jp.org/ioi/2017/tasks/day1-nowruz-ISC.pdf)、[公式配布Editorial](https://ioi.te.lv/locations/ioi17/contest/day1/editorial/nowruz.pdf)。候補IDは `induced-grid-tree-single-neighbor-leaf-growth`。

既に残した自由セルが非空の誘導木で、未使用自由セルvの隣接済みセルがちょうど一つなら、vを追加すると連結性を保ち、辺と頂点が一つずつ増えるので木であり続ける。選択可能な辺を任意に削る全域木構築とは異なり、残したセル間の全隣接辺が自動的に存在する点が本質。親の現在次数dに対し葉数差は `1+[d=0]-[d=1]`。初めの一頂点から二頂点へは葉が2増え、d>=2なら1増え、d=1なら0となる。

元入力に複数連結成分があれば一つを選ぶ必要がある。適当な最初のセルや固定順の追加だけでは目標葉数を保証しない。probeは1..3行/列の全673非空自由盤面で局所追加の木性と葉差分1254回を検査し、全誘導部分集合の最良葉数とも比べた。固定順で最適に届かない例160件を検出。障害物のない2x3でも、固定順の出力mask47は葉2、mask23の星なら葉3である。

公式資料の反復走査/乱択再始動は86点、複数セルを葉にする貪欲拡張は99+点という実績記述であり、100点の保証ではない。元の10入力/満点出力を取得・検証していない。従って局所不変量の確認を「原典全点を解決」と呼ばず、初回分類はunconfirmedのまま。単なるoutput-only保存APIやタイルを再使用しない一本の経路は、この誘導木と葉数を扱わない。

## Wiring：同色blockの重複境界一つと二方向の最小値

[原典](https://www2.ioi-jp.org/ioi/2017/tasks/day1-wiring-ISC.pdf)、[公式配布Editorial](https://ioi.te.lv/locations/ioi17/contest/day1/editorial/wiring.pdf)。候補IDは `line-bipartite-edge-cover-monochromatic-block-prefix-dp`。公式には同色block/線形DPの方針だけがあり、以下の具体式は独立補足。

全点を座標昇順へmergeする。最適な辺は隣接同色block間だけになる。三つ以上の境界を飛ぶ赤x→青yの間には青b・赤aが `x<b<a<y` の順で存在する。辺xyをxbとayへ置き換えると全必須端点を覆ったまま `a-b` だけ短くなる。

同じblockのu<vについて、uが右block、vが左blockへ結ばれる場合、左右の相手をz,wとして `z<u<v<w`。z-vとu-wをz-uとv-wへ替えると `2(v-u)` 短くなる。従って各blockの左へ結ぶ点はprefix、右へ結ぶ点はsuffixで、両方へ結ぶ点は境界の高々一個だけになる。

左block末尾k点A、右block先頭j点Bを全て覆う最小費用をC(k,j)とする。左最後をa、右最初をb、両群の座標和をSA,SBとすると

- k>=j: `C=SB-SA+(k-j)*b`。
- k<=j: `C=SB-SA+(k-j)*a`。

各点から境界までの距離は一度以上払い、群間の正の隙間はmax(k,j)本以上必要。多い側は各一点ずつ、少ない側の境界に一番近い点へ余分な辺を集める星でこの下界を達成する。

最初t点の最小費用をD[t]、右blockの先頭添字をq（0始まり）、左block長をAとする。左suffixの先頭点を前の解と重複させるかどうかだけを選べるため

`D[q+j] = min(1<=k<=A) { min(D[q-k],D[q-k+1]) + C(k,j) }`。

D[0]=0、最初の単色blockだけのprefixは∞。`P[k]=min(D[q-k],D[q-k+1])` とすると、k>=jは `P[k]+k*b-SA[k]` のsuffix最小、k<=jは `P[k]+k*a-SA[k]` のprefix最小へ分かれる。右j点の和からそれぞれj*b/j*aを引いて足す。境界一つにつき左右block長の和だけで全jを計算でき、各blockは高々二回登場する。整列済み二列のmergeを含めO(n+m)時間・O(n+m)空間。座標1e9・合計点数20万なので中間積と費用は64bitを使う。

全長2..7の480色列/座標profileに対し、701112個の異色辺部分集合を文字通り列挙した最適費用、独立の二次元prefix DP、新線形DPが一致。さらに1000乱択と合計20万点の3構成を比較。これは研究Pythonの式の検査であり、再利用C++20・不正入力/例外/最大メモリ/ASanを完成したとはしない。

## Toy Train：到達attractorを二人で交互に取り除く

[原典](https://ioi.te.lv/locations/ioi17/contest/day1/train.pdf)、[公式配布Editorial](https://ioi.te.lv/locations/ioi17/contest/day1/editorial/train.pdf)。候補IDは `buchi-owned-graph-repeated-target-attractor-elimination`。

固定スイッチの走行は有限prefixの後で一つの単純周期へ入る。周期に充電駅があれば充電間隔は高々Nで永続し、なければいずれ電池切れ。目的は無限走行中に充電集合Rを繰り返し訪れることと同値になる。

現在残る全域W内で、ArezouがRへ必ず到達させられる集合Attr_A(R)を作る。Rから始め、A所有なら一辺でも集合へ出る頂点、B所有なら全ての残存出辺が集合へ出る頂点を加える。X=W\Attr_A(R)では、BがRを永久に避けられる。XへBが到達を強制できるAttr_B(X)もBの勝ちなので除き、残りで繰り返す。

除去後はA頂点に少なくとも一つ残存出辺があり、B頂点の全残存対象辺は残りへ向く。そうでなければBのattractorへ入るためで、残ったゲームは常に出次数1以上を保つ。終了時に全残存頂点がAのR-attractorなら、AはR外でattractor rankを下げる辺を固定して選び、Rでは残存辺を選べる。Bのどの選択でもRへ戻り続ける。

除去された側では、Bはその回のattractor rankを下げてXへ向かい、Xではその回のRを避ける。先に除去された集合へ入る場合も、除去回の順序が下がるので最後は充電なしに閉じる。この両側の戦略は頂点ごとに一辺を固定でき、再訪後にスイッチを変えない原典の規則を満たす。単に「毎回選び直せるゲーム」へ条件を黙って拡張したのではない。

逆辺と未到達出辺数で一attractorはO(N+M)、一回以上の頂点を除くので高々N回、M>=NからO(NM)時間・O(N+M)領域。probeの集合反復は式の検査用であり、そのまま満点実装の時間を主張しない。N1..3のloopを含む全353 total graph、全19318所有者/非空充電集合、N4..8の400乱択について、初訪問の全分岐を実際にminimaxした結果に一致した。

出次数0から勝敗を伝え、無限継続を引分にする既存APIは、原典sampleと同じ二駅でも全drawを返す。原典では両初期点A勝ちであり、終了条件の違いを埋める新手順が必要。

## Prize：同じ価値の端点で区間内の高価な個数を差し引く

[原典](https://www2.ioi-jp.org/ioi/2017/tasks/day2-prize-ISC.pdf)、[公式配布Editorial](https://ioi.te.lv/locations/ioi17/contest/day2/editorial/prize.pdf)。候補IDは `rank-count-oracle-equal-level-interval-pruning`。

ask(i)の左右和は、その箱より高価な全箱数なので、二位置の和が等しいことと価値が等しいことが同値。同じ価値のi<jについて、ask(j).left-ask(i).leftは開区間(i,j)内のより高価な箱数である。既に特定した高価な箱の個数を差し引けば、未調査部分に高価な箱が残るか判定できる。0なら、その間にdiamondが残る可能性を全て排除できる。

この局所式は、今までの全返答に整合するどの配列にも成立する。一方、それだけでは適応graderに対して探索全体を5000回に抑える証明にならない。公式は効率的な実装で4759回と記すが、その分岐の詳細と厳密な償却上界は独立に埋め切れていない。よってreviewStatus=unconfirmedを維持する。固定配列で当たったことを適応graderの満点検査へ読み替えない。

小さい合法配列832件の全31294位置対で式を確認。個数増大条件を満たす13,098通りの「最安typeより高価なtype個数列」を整数で列挙し、N<=200000の高価な個数最大472も確認した。達成例のtype個数は1,4,21,446,198917（総199389）。この数を使う単純な一個ずつの二分探索は満点質問数の証明としては不足する。unorderedな箱列へ単峰最大値APIを使えず、自由な部分集合にdiamondがあるかを質問するAPIも原典にはない。

## Simurgh：基準木の辺の差分から、星の個数質問と葉の復元へ

[原典](https://www2.ioi-jp.org/ioi/2017/tasks/day2-simurgh-ISC.pdf)、[公式配布Editorial](https://ioi.te.lv/locations/ioi17/contest/day2/editorial/simurgh.pdf)。候補IDは `spanning-tree-overlap-oracle-reference-labeling-leaf-peeling`。

公式のforest補完/次数/葉二分の方針を用いるが、原典full-rangeに必要な「基準木の辺の正解性」を調べる部分は、ear decompositionの短文を検証済みと呼ばず、次の独立なfundamental cycle手順へ具体化した。

任意の固定全域木Tの共通辺数bを一回聞く。非木辺eを足したcycle Cで木辺fを外すと、質問は常に全域木で、返答差は `delta_f=w(e)-w(f)`（隠れた木のmembershipは0/1）。

Cに未確定のT辺がある場合だけ処理する。既知T辺gがあれば、一回の差分でw(e)を求め、各未確定fを一回ずつの差分で分類する。CのT辺が全部未知なら、それらを一回ずつ聞く。非0差分があればw(e)が決まり、全fを分類できる。全差分0ならcycle全辺のmembershipが同じだが、全1は隠れた木にcycleを作るため不可能で、全部0と決まる。

各未確定T辺を質問するのは一回、処理するcycle数も未確定辺数を減らすため高々N-1。既知辺への補助質問も各cycle一回以下で、基準一回を含め `<=1+2(N-1)`。最後までどのfundamental cycleにも属さなかったT辺は橋なので隠れた木に必ず入る。

任意のforest Fを、Tの辺を追加して全域木にできる。追加したT辺のmembershipは既知なので、全域木の返答から引けばF内の正解辺数を一回で聞ける。頂点vに接続する全辺は星でforestだから、全頂点の隠れた木での次数をN回で調べられる。

隠れた残存木の次数1の頂点vを取り、残存隣接候補の半分だけの星をFとして質問すれば、唯一の正解辺がその半分にあるか分かる。高々ceil(log2(N-1))回でその辺を確定し、葉を除き、相手の次数を一減らす。この手順は最後の一点まで高々N-1回である。総質問数は

`1+2(N-1)+N+(N-1)*ceil(log2(N-1)) <= 5990`（N<=500）。

満点8000より小さく、sample graderの30000に依存しない。各質問は元グラフのN-1本の相異なる辺からなる全域木であることを構成で保証する。forest補完のたびDSUとT走査を使えば局所時間O(MN+N² logN alpha(N))、空間O(N+M)。oracle内部の走査を計算量へ隠して定数時間と呼ぶことはしない。

全N2..5の771連結単純グラフと、その全8135隠れ全域木を独立な組合せ列挙で固定し、実質問108860回をDSUで合法性検査して復元を比較。N500の鎖/完全グラフ3種も、実際の全域木質問を行い最大5284回であった。これは研究Pythonの検査で、完成した再利用C++20/callback例外契約/ASanの実績ではない。公式ear-decomposition節の圧縮式の詳細は、この別手順の正しさへ必要ないため別の未確認として残す。

## Ancient Books：運搬の下界と、実際に触れたcycleの閉包

[最終原典](https://www2.ioi-jp.org/ioi/2017/tasks/day2-books-ISC.pdf)、[公式アーカイブがEditorialとして配布するDaniel Grafの15頁資料](https://ioi.te.lv/locations/ioi17/contest/day2/editorial/books.pdf)。後者は題名Library、APIbooksort、6小課題など本選と異なる旧稿を含む。本選の制約・APIは原典だけで確認し、同じ一冊運搬モデルに対する証明と実装だけを資料から参照する。候補IDは `permutation-cycle-interval-closure-two-sided-walk-greedy`。

各本が目的位置へ動く総距離 `D=sum_i |i-p[i]|` は下界。一つの順列cycleは、本を持ってcycle順に置換しながら回ればこの下界だけで処理できる。運搬中に通る他cycleの本のある位置へ着いたら、手元の本を一時的に交換し、そのcycleを処理して同じ位置へ戻ってから元を続けられる。

現在処理可能な区間[l,r]を持ち、その区間内に**実際の頂点を持つcycle**の左右端まで広げることを繰り返す。この閉包拡張は追加の非本質的歩行を不要にする。単にcycleの外接区間が交わることだけを使って、一方向へ無条件に広げてはいけない。p=[2,1,0],s=1では外側cycle[0,2]の本は開始点に無く、答えはD=4ではなく6。資料の短い「interval overlap」の文章だけを、この反例に合わない実装へ移していない。

閉包後の区間で未処理が残るなら、左右のどちらかへ一歩広げて戻る分の2を払う。これを二次元区間DPにすれば最適値を得るが、N100万には大きすぎる。

線形化には、左へ進んだ場合と右へ進んだ場合について、初めて反対側まで無料拡張が起こるcycleを探す。左側の必要な追加費用をcL、右をcRとする。一方で見つかればもう一方でも見つかる。左で最初に触れるcycleの右端までの中には、右で最初に触れるcycleの頂点があり、右側も対称だからである。いずれかを触れば両方を同じ閉包へ取り込めるので、min(cL,cR)を払い、その共通閉包から続ける。両方とも見つからない外側の部分では、左右両方の費用が必須となる。

左右の試行で新たに調べる範囲は、最後の反対側への無料拡張までは左右に分離している。そこで共通閉包へ入った範囲はその回で全て処理済みになる。延長時に元区間を走査し直さず、新たな両端だけを調べれば各位置を高々定数回調べるため、cycle分解を含めO(N)時間・O(N)空間。DはTheta(N²)になり得るので64bitが必要。

全N1..6の5039順列/開始点に対し、棚と手持ち一冊を実際の状態にし、拾う/交換/置くをcost0・左右一歩をcost1とする0-1BFSの全201602状態から得た最短値と、区間閉包DP・上の両側貪欲が一致した。probeは小さい閉包を明示走査するので、それ自体をN100万の線形APIとして登録しない。

## 初回集計と次の実装作業

原典確認6/6、数値確認6/6、公式Editorial取得6/6、選定した主要手順の確認4/6。研究positiveはWiring/Toy Train/Simurgh/Ancient Booksの4題だけ。Nowruzの全10出力満点とPrizeの最悪質問数証明は未確認。初回分類はmissing-technique4/unconfirmed2/covered0、完成C++20/API0、原典walk登録0、固定6題coverage0/6。`fixedCorpusResearchComplete=false`、`fixedCorpusCoverageComplete=false`、`globalCoverageComplete=false`。部分補題とprobeが成功しただけで研究6/6へ変えない。

原典を読めたこと、解法の主要補題を確認したこと、原典全域を扱う完成APIがあること、ナビゲーションからその技巧へ到達できることを分けた。完成4候補にも、自然な日本語の技巧記事・完全C++20・実fence抽出checker・API不正/例外/最大/ASan・独立レビューが必要である。既存の汎用記事をcoveredへ数えていない。

再現は手動で `python3 research/probes/ioi-2017-research-checks.py`。標準出力だけを返し、明示的に新しい出力先を第二引数へ渡した場合だけJSONを書き出す。npm collectやtimerなどの定期収集設定は行っていない。CF/CSES/原本zip/rawGitHubの既知DNS失敗経路を再試行せず、取得できた一次本文/翻訳/Editorialと独立証明で進めた。共有plan/ledger/audit/source/article/flowは未編集。


## 恒久保存の範囲

初回921rawと後時点571rawは当初の一時領域で全SHAを照合した。恒久領域では全1492の台帳、flow/metadata/walk/reference/sourceの正確なraw、近接13記事全MDX、7runtime TS/helper、既存8監査を保持する。全498記事/全1492rawを恒久保存したとは主張しない。manifestは初回と依存拡張のepochを分け、元manifest/before/after台帳の正確なbytesも保つ。normalized probeは恒久snapshotだけから一時領域へ展開し、既設compilerのSHAを確認して凍結runtimeと独立walkerを比較する。compilerをダウンロードしない。


## 2026-10-15 Wiringの不足を解消

初回6recordsと研究4/6・完成API0/6・記事対応0/6の記録は保存し、Wiring行にresolutionのみ追加した。単色区間の交換法、高々一点共有、二群の被覆費用、二方向最小値によるO(R+B)を完全C++20へ移した。全小literal辺集合・指数cover・別二次DP、原典各色10万、通常/ASanと別matching還元・割当失敗を作者/root/別review者で確認。原典genericと公式Noticeからadapter署名を導出し、配布header未取得は記録のまま維持する。

現在研究4/6・記事対応1/6。504記事/471図/525対応のローカルビルド、日英全角138検索、全図/内部リンクと対象10組の回帰が成功。全体検証は `verification-2026-10-15-ioi2017-wiring.json`。Nowruz/Prizeの主要手順は未確認のままで、局所補題を満点解法に昇格させない。


## 2026-10-15 Trainの不足を解消

初回6recordsと研究4/6・完成API0/6・記事対応0/6を保存し、Train行にresolutionのみ追加した。到達集合の反復除去から両者の固定戦略を作り、初訪問時に進路を固定する規則と電池容量Nの原典へ正当性を接続した。通常/ASan+UBSan、実際の初訪問探索、固定方策列挙、別の有限電池安全ゲームと割当失敗を確認した。配布header未取得と追加検査のLSan終了時失敗は記録に残す。

現在研究4/6・記事対応2/6。505記事/472図/526対応のローカルビルド、日英全角143検索、全図/内部リンク、対象10組の回帰が成功。全体検証は `verification-2026-10-15-ioi2017-train.json`。Nowruz/Prizeの未確認手順は完成扱いにしない。


## 2026-10-15 Booksの不足を解消

初回6recordsと研究4/6・完成API0/6・記事対応0/6を保存し、Books行にresolutionのみ追加した。一冊運搬の下界、サイクルの実頂点閉包、切れ目の追加往復下界、左右の最初の橋と線形償却を完全C++20へ移した。最終原典と旧Library稿のAPI・数値範囲を区別し、全小物理BFS・別指数DP・有向全域木oracle、最大100万と通常/ASan+UBSan、割当失敗を独立に確認した。

現在研究4/6・記事対応3/6。506記事/473図/527対応のローカルビルド、日英全角148検索、全図・内部リンクと対象10組の回帰が成功。全体検証は `verification-2026-10-15-ioi2017-books.json`。Nowruz/Prizeは未確認のまま維持する。


## 2026-10-15 Simurghの不足を解消

初回6recordsと研究4/6・完成API0/6・記事対応0/6を保存し、Simurgh行にresolutionのみ追加した。基本閉路の交換差分で基準辺を分類し、森の個数を合法な全域木質問へ変換して葉から復元する。最悪5990回を証明し、全小graph×全秘密木、全質問の合法性、最大N500/M124750と通常/ASan+UBSan、別の整合transcript/leafstrip・予算/例外/割当失敗を確認した。公式ear分解の別手順は未確認、実配布headerも未取得として保持する。

現在研究4/6・記事対応4/6。507記事/474図/528対応のローカルビルド、日英全角152検索、全図・内部リンクと対象10組の回帰が成功。全体検証は `verification-2026-10-15-ioi2017-simurgh.json`。Nowruz/Prizeの初回未確認も維持する。


## Prize：後続の独立証明と記事対応

左右の上位個数への返答から最下位を確定し、区間内の上位個数を保ちながら中央走査と二分を組み合わせる手順を追加した。全整合列を対象とする正しさ、個数上界472/26、全分岐のD_H(k)と初期走査の吸収から最悪4779質問を証明した。公式の省略4759法を確認済みとは扱わない。原典全域C++20、全小適応分岐、最大域の合法補完族、全容量分割DP、通常ASan/UBSanと別レビューを確認した。

初回Prize unknown・研究4/6・API0/coverage0と既存4resolutionsを保持し、後続positive1件とresolutionを追加した。現在研究5/6・記事対応5/6。Nowruzと、公式の別4759手順は未確認として残る。509記事/476図/530対応のローカルビルド、161日英全角検索、全図・内部リンクと対象11組の回帰が成功。全体記録は `verification-2026-10-15-ioi2017-prize.json`。
