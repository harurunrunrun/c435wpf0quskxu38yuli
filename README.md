# 競技プログラミング知識大全集

過去問で使われる具体的な技巧を日本語でまとめるサイトです。問題本文や個別問題の解説ページは作らず、技巧の記事に原典・解説へのリンクを載せます。

入口の一覧には、特定の遷移式や操作で使うテクニックを載せます。一般のアルゴリズム・データ構造の説明は「基本アルゴリズム・データ構造」へ分けています。

DPの状態・遷移、文字列、経路、整数・幾何、係数列、更新付きの順位・頻度、期待値、構築などの具体的な技巧を扱います。使用例には、問題の特徴から各分野の根をたどる経路を保存します。記事数・対応数・固定群ごとの進捗はサイトと `data/coverage-report.json`、出典別の確認数は `data/research-ledger.json` を参照してください。全過去問の調査は未完了です。

調査基準日は **2026年10月14日**。全世界の過去問の調査は未完了です。出典別の対象範囲と確認数を `data/research-ledger.json` に記録します。

## アップロード前にローカルで見る

Node.js **22.13以上**を使います。依存のインストールやネット接続なしで確認できます。

```sh
cd /home/admin2/flowchartcp/site
npm run build:local
npm run preview:local
```

**http://127.0.0.1:4321/flowchartcp/** を開きます。終了は `Ctrl+C`。ポートの変更は `npm run preview:local -- --port 4400`。

出力先は `dist-local/`。記事・数式・コード・使用例一覧・質問式・SVG図・検索を含みます。本文、構造化データ、図の生成関数は通常ビルドと共通です。ローカル版の本文検索は同梱した検索処理を使います。

## Astro / Starlight / Pagefind でビルドする

```sh
npm install
npm run check
npm run build
npm run preview -- --port 4321
```

同じ **http://127.0.0.1:4321/flowchartcp/** を開きます。出力先は `dist/`。Pagefind はビルド時に索引を生成するため、本文検索は preview で確認します。最初のインストールで作られる `package-lock.json` を保存した後は `npm ci` を使えます。

開発サーバーは `npm run dev`。通常版とローカル版のサーバーを同じポートで同時起動しないでください。

## 内容

- 解法フローチャート：分野を選び、入力、求める量、操作からたどる。3択以上の質問と「はい／いいえ／わからない」に対応。
- 計算量を減らすテクニック：遷移の区間和・最小値、重さの余り、重複状態などを具体的に扱う。
- 高度なテクニック：更新写像の合成順、二番目の最大値、存在時間、補助木、木の個数DPなど。
- 考察のテクニック：最大値の担当区間、ビットの寄与、差分、自己ループの移項、隣接交換、逆挿入など。
- 基本アルゴリズム・データ構造：各技巧の前提となる説明。

全体図は設けず、分野ごとの入口と詳しい図を用意します。分野を切り替えて戻ると、途中の詳しい図と回答履歴を復元します。問題文の対象と求める量から、対応の必須条件、個数、費用、移動範囲などを確認します。

座標・図形、選択・分割、移動・つながり、整数・数え上げの4分野は、入口を「わからない」を含む4〜6択にし、その先を18のカテゴリ図へ分けています。例えば座標では、点どうしの距離、図形の形・面積、長方形の集計、境界・壁、移動・分割から選びます。図の「詳細の質問・図へ」から、その条件に合う小図へ進めます。分類は入力・操作・求める量で選び、適用条件の確認と技巧への到達先は各小図に引き継ぎます。

整数、経路、木、数え上げの詳しい6図は、桁の条件、辺の費用、指定頂点、禁止条件などを確認する10の小図へ分けています。質問式では続きの図へ回答を引き継ぎます。図だけのページでもリンクから続きへ進めます。分割前の共有URLは同じ質問・候補へ移り、古い表示位置を引き継がず文字を読める位置で開きます。

配列・区間、区間の集計、連続区間、選ぶ数・重さ・履歴の5図は、入口を4〜6択にし、その先を15の特徴別の図へ分けています。要素を選ぶ、合計や使用回数を制限する、一点や区間の値を変える、出現回数や順位を求める、といった問題の条件から進めます。共通する桁・履歴・区間情報の確認は5つの小図にまとめ、以前の回答列も同じ質問・候補へ引き継ぎます。

文字列の一致・部分文字列・回文、木の集計、組の選択・割当の6図は、入口を4〜5択にし、23の特徴別の図と8つの確認図へ分けています。部分列では、個数と構築、本文からの取り出し、削除と文字変更から選びます。木は選ぶ個数や距離、割当は組の個数・利益・場所・時刻・数量など、求める量と制約から進めます。

考察、式・数列、つながりの変更の3図は、入口を5〜6択にし、20の小図へ分けています。操作を逆にたどる、途中で保つ条件を探す、添字の条件で積をまとめる、係数や遠い項を求める、辺を削除する、といった特徴から選びます。長い確認の連鎖も区切り、元の適用条件と到達先を引き継ぎます。

数え上げ、木の祖先・部分木・経路、移動費用の3図は、入口を5択にし、23の小図へ分けています。数える対象の条件、木で問い合わせる場所、移動で覚える情報、移動先をまとめられる規則から選びます。以前から続きの図に分かれていた質問も、回答履歴と接続先を保ちます。

共通部分列の復元では、前後の長さから切れ目を決め、復元用の全表を保存せずに列を出力します。多項式は、相異なる点から全係数を復元する場合と、次数の上限と連続点の値から一点だけを評価する場合を分けています。これらの使用例5件を根から再生し、次数・点の重複・逆元・再計算時間の条件を確認します。

辺をつなぎ替える森では、経路の和と、向きを持つ関数合成を扱います。各操作の計算量は償却保証で、一般の閉路を含むグラフや部分木の集計とは区別します。細い格子の単一閉路の計数では、境界の端点の組を持ち、最後の使用マスより前で閉じる閉路を除きます。格子の入口は配置・被覆、経路・閉路、色・数の3群へ分け、以前の回答も引き継ぎます。

質問式と図は同じ `data/flows.json` から作ります。回答履歴の保存・共有、戻る、やり直す、表示切替、経路と現在位置の強調、拡大縮小、移動に対応します。JavaScriptを無効にしても全図と文章版を閲覧できます。

図の「図だけ表示」から、図と操作ボタンだけの専用ページ `/flowchartcp/diagrams/<図ID>/` へ移動できます。ホイールでカーソル位置を中心に拡大・縮小し、ドラッグで移動します。専用ページでは二本指のピンチにも対応します。＋／−・矢印キー・0キーでも操作でき、「戻る」で回答経路と表示位置を元のページへ引き継ぎます。通常の図表示でもホイールを使えます。初期表示は根または回答中の質問の文字を読める倍率にし、「全体」で図全体へ切り替えます。選択肢にポインターかキーボードのフォーカスを合わせると、その枝を強調します。

15分野ごとに図を用意します。図を分割した際に同じ質問を複数の図へ載せるため、図やノードの数は技巧の種類数を表しません。使用例の全対応について各分野の根からの経路を保存し、分岐を変更したときに再生して検証します。原典本文を確認できた経路と未確認の経路は区別して集計します。

必要な性質を証明できない場合、候補を断定しません。例えば負数を含む区間和では尺取りの単調性が失われ、個数の軸を罰金へ変える最適化には最適値の離散凸性・凹性と同値解の扱いが必要です。

## 過去問から分岐を増やす

`data/problem-walks.json` に、問題文から読み取った特徴、原典URL、入口の分野を表す `entryGraphId`、その根からの回答列、通過した質問、期待する到達先を保存します。原典を確認できた記録は `verified`、取得できないものは `pending` とします。

1. 原典を読み、入力・操作・求める量を記録する。
2. 問題の特徴に合う分野を選び、その根から実際の選択肢を選ぶ。
3. 自然な回答で進めない箇所に質問・選択肢を追加する。
4. 必要条件を確認して到達先と技巧記事を結び付ける。
5. 経路を保存し、既存の問題の経路もテストする。

`tests/flow.test.ts` が全記録を分野の根から再生し、到達先、表示する回答ラベル、SVGの全ノード・辺、参照先、到達性、循環を検証します。`tests/flow-layout.test.mjs` は生成した全図の曲線を解析し、線がノードや回答ラベルを貫かないこと、文字とカードの重なり、異なる枝の線の重複を検査します。ノード・辺・折返し後の回答文字列・分野へのリンクが分岐データと一致し、重複や欠落がないことも確かめます。回答ラベルは行数に合わせた専用の領域に配置します。分野の選択・履歴復元・共有URLは実際のクライアント処理を実行するテストで確認します。

`tests/flow-continuation-sharing.test.mjs` は分割前の6図を独立にたどり、全834通りの回答途中で、質問・選択肢・説明・適用条件・候補が一致することを確認します。図をまたいだ共有URLの復元、履歴の重複防止、元の図の根まで戻れること、元6図の縮小も検査します。さらに、最初の分野別分割より前の593回答経路と404使用例の共有URLを引き続き検証します。

`tests/flow-category-regrouping.test.mjs` は、配列・区間と状態の図の全844旧回答経路と404使用例を検証します。`tests/flow-nested-migrations.test.mjs` は複数段のカテゴリー分割と小図への移動を組み合わせ、以前の共有URL・履歴・戻る操作を確認します。不正な回答対応や循環は検証時に拒否します。

`tests/flow-string-graph-regrouping.test.mjs` は、文字列・木・割当の全801旧回答経路と404使用例を検証します。部分列の分類を増やした質問も、元の10択のラベルと分岐先がすべて残ることを確認します。

`tests/flow-reasoning-regrouping.test.mjs` は、考察・式・つながりの全691旧回答経路と404使用例を検証します。元の質問・適用条件・候補の保持、共有URLと戻る操作、分割後の各図の縮小を確かめます。

`tests/flow-count-tree-regrouping.test.mjs` は、数え上げ・木・移動費用の全271旧回答経路と404使用例を検証します。以前から存在する続きの図を独立に復元し、元の確認条件・接続先と新しい分割後の履歴を確かめます。

図の改行では、句読点・閉じ括弧を行頭、開き括弧を行末に置かないよう調整します。枠に収まる英単語・略称は途中で折らず、次の行へ送ります。`tests/flow-text-wrapping.test.mjs` で、元の文字列を保ち、文字が枠内に収まることを確認します。

## 固定した問題群で網羅性を調べる

`data/coverage-plan.json` に調べる大会・年度・部門を先に固定し、`data/corpus-audits/` に全問題の原典確認と、分野の根からたどった際の最初の不足を保存します。一般記事や名前が一致するだけでは対応済みにしません。元の監査を残し、不足を補った後に記事・確認済み使用例・根からの再走査を `resolution` として追記します。

```sh
npm run audit:coverage
npm run audit:coverage -- --write
```

二つ目のコマンドは現時点の集計を `data/coverage-report.json` に保存します。各固定群について、解法を確認した問題数と、必要な記事・実装・分岐まで揃った問題数を分けて示します。対象はUSACOの指定回・部門、ICPC World Finals、JOI春合宿、IOIの指定年度です。一つの固定群で全問の不足を補っても、別年度・部門や世界全体の完了とは扱いません。

初回監査の問題集合、当時の記事と分岐、最初の不足、未確認の補題を保持します。その後の解法確認は `subsequentSolutionReviews`、記事・使用例・根からの経路まで揃った対応は `resolution` に追記します。研究用の小実験だけでは、原典の全範囲を扱う実装が完成したことにしません。全体の母数が未確定なので、世界の網羅率は表示しません。

出典別の集計は、掲載使用例からの `solutionReviewed`、固定群の原典確認 `corpusStatementsReviewed`、固定群の解法確認 `corpusSolutionsReviewed` を分けます。`allSolutionsReviewed` は掲載使用例と固定群の和集合です。同じ問題を複数群で調べたり、確認済みの問題を後から記事化したりしても二重計数しません。確認数は台帳の各項目から確認できます。取得したメタデータや未確認の証明だけでは解法確認数を増やしません。`tests/corpus-ledger.test.mjs` が重複・追加掲載・未確認の扱いを検証します。

JOIの初回監査時の分岐と技巧データは `research/snapshots/` へ圧縮して保存し、`tests/joi-fixed-corpus.test.mjs` でハッシュ、公式全12題、当時の根から最初の不足までの回答とラベルを再生します。

`tests/corpus-coverage.test.mjs` は、全問を調査しただけで網羅完了にならないこと、記事・使用例・根からの経路が欠けた対応を解消済みにしないことを検証します。

## 記事・使用例を追加する

`src/content/docs/techniques/<id>.mdx` と 既存の `data/techniques-specific-*.json` に記事・名前・別名・適用条件の概要・前提・入口・資料を登録します。データファイルを増やす場合は `src/lib/content.ts` にも読み込みを登録します。基本事項は `techniques-core.json`、`techniques-advanced.json`、`techniques-reasoning.json` に置きます。

見出しは「使う場面」「考え方」「適用条件」「なぜ正しいか」「計算量」「実装」「関連する手法」「参考資料」。具体的な式、成立しない場合、改善前後の時間・空間計算量、呼び出せる実装を掲載します。

使用例は `data/references-*.json` へ追加します。

- `editorial`：公開解説で確認。
- `reference-solution`：公開解答で確認。
- `independent-analysis`：問題文から独立に式を導き、証明と小規模全探索との比較で確認。公開解説を確認した記録とは区別する。
- `official-tag`：対話などの問題形式を確認。解法確認数には含めない。

タグだけの推測は掲載済みの対応にしません。難易度不明は `null`。公開日を原典で確認できないアーカイブは `cutoffVerification: undated-archive` として、問題文・解法の確認とは分けて記録します。追加後は `node scripts/lib/ledger.mjs` で台帳を更新します。

原典の再確認で見つけた資料と、まだ確認できていない内容は `data/research-followups.json` に記録します。ある問題の前処理・評価部分に使う技巧は、使用例の分類根拠と図の到達先でその範囲を明記します。使用例に表示する `evidence` は条件と使用箇所を説明し、調査・比較テストの作業記録は任意の `verificationNotes` に保持します。

図のSVGは直接編集せず、`node scripts/build-diagrams.mjs` またはビルドコマンドで生成します。

## 手動で収集する

```sh
npm run collect -- --source all --until 2026-10-14 --resume
npm run collect -- --source atcoder --until 2026-10-14 --resume --limit 3
node scripts/lib/ledger.mjs
```

メタデータはGit管理外の `research/raw/` に保存します。カーソル・取得日時・失敗記録を残して再開できます。収集結果を教材へ自動反映しません。詳細は [収集基盤の説明](scripts/lib/README.md)。定期実行は設定していません。

## 検証

```sh
npm run validate
npm test
npm run test:cpp
npm run build:local
npm run verify:local
```

C++検証には Python 3 と C++20対応の `g++` または `clang++` を使います。記事のコードを独立にコンパイルし、条件別の実装は本文から抽出して素朴な計算・全探索と比較します。必要なAtCoder Libraryのヘッダーとライセンスは `vendor/ac-library/` にあります。

追加したLCS復元・積の木による補間・連続点の補間は、`python3 scripts/check_reconstruction_cpp.py` で本文の実装をコンパイルし、全表DP・独立な差商法・多項式の直接評価と比較します。累乗和と繰り返し累積和の小規模計算も確かめます。`tests/reconstruction-flow.test.mjs` は、省メモリの入口、出力する量、次数・法の条件、5件の使用例と共有履歴を検証します。

動的森と単一閉路の実装は `python3 scripts/check_forest_frontier_cpp.py` で検証します。BFSによる経路・関数合成、全3×3障害物配置の辺集合と閉路の全列挙、幅制限、転置、64ビットを超える個数を比較します。単一閉路の実装はBoost.Multiprecisionのヘッダーを使います。`tests/forest-frontier-flow.test.mjs` は適用条件の分岐、3件の使用例、格子の旧回答列と共有履歴を検証します。

最小全域木の辺の三分類・厳密次小全域木、列の切り貼り・反転、動的列の一次変換と区間和、固定点に着く区間更新、全出現の逆順置換は `python3 scripts/check_specific_expansion_cpp.py` で検証します。全域木の列挙、配列の直接更新、整数平方根・約数個数の独立計算と比較します。`tests/specific-expansion-flow.test.mjs` は適用条件と使用例10件を分野の根からたどり、共有URLと戻る操作も確認します。

最長増加部分列の位置の分類・個数、極値を使う分割DP、同色削除の持ち越し状態、不等号列の順位DPは `python3 scripts/check_dp_expansion_cpp.py` で検証します。部分列・区間分割・現在の列からの削除手順・順列を独立に全列挙し、重複・負値・整数境界・法1も比較します。`tests/dp-expansion-flow.test.mjs` は適用条件、使用例8件、共有・戻る操作を確認します。原典の特徴は `data/dp-expansion-problem-features.json` に記録します。

最短路の必須辺・存在しない辺からの探索、剰余ごとの到達額・大きなトーティエント総和、全入力の共通部分文字列・非交差な奇数長回文の積は `python3 scripts/check_archive_expansion_cpp.py` で検証します。経路・補グラフ・到達額・部分文字列・回文の独立全探索と比較し、最大10の10乗の総和はメビウス反転による別計算でも照合します。`tests/archive-expansion-flow.test.mjs` が使用例6件の分岐・条件・共有履歴を、`data/archive-expansion-problem-features.json` が原典の特徴を記録します。

根からの経路上のLIS、木の増加ラベル付け、mexでの整列、順列の平方根、各要素に一つの前後条件がある順序、二部性を保つ追加辺の個数は `python3 scripts/check_tree_construction_cpp.py` で検証します。経路の部分列、頂点の全順序、全写像、全単純グラフ、順列の二乗を独立に列挙し、構築した操作や順序の合法性と最適値も比較します。`tests/tree-construction-flow.test.mjs` が6件の特徴・適用条件・共有履歴を検証し、原典の特徴と確認日は `data/tree-construction-problem-features.json` に記録します。

長さ制限付き区間和の上位K個、負数を含む積の順位、桁和による可除性、二数の商の床の総和、回文の長さと出現回数の積、両本文に一回ずつ現れる最短部分文字列は `python3 scripts/check_frequency_rank_cpp.py` で検証します。全区間と全添字対の列挙、整数の直接判定、本文別の部分文字列mapと比較し、重複・負数・整数境界・最大入力も確認します。`tests/frequency-rank-flow.test.mjs` が6件の条件・共有履歴を検証し、原典の特徴は `data/frequency-rank-problem-features.json` に記録します。

ANDが0になる相手と非空部分集合の個数、同じ末尾色を除くDP、対応括弧の着色、辺数固定の最短費用、通路を通れる円の半径は `python3 scripts/check_mask_bracket_path_cpp.py` で検証します。直接のAND比較・全部分集合・全削除・全着色・回数ごとのDP・独立なmin-max Floyd法と比較し、最大ビット幅、深い括弧、負の価値、巨大な回数と整数境界、接触条件も確認します。`tests/mask-bracket-path-flow.test.mjs` が6件の条件・共有履歴を検証し、原典の特徴は `data/mask-bracket-path-problem-features.json` に記録します。

全区間の二番目最大値、出現回数が値に等しい種類数、壁付き格子の方向別累積DP、転倒数を指定した順列の計数、前向きグラフで各頂点を避ける最短路、全ての根での辺反転費用は `python3 scripts/check_ray_rank_avoidance_cpp.py` で検証します。区間の整列・頻度の直接集計・移動先の全列挙・順列の全列挙・各頂点を除くBFS・各根からの探索と比較し、重複・壁・空入力・整数境界・最大入力も確かめます。`tests/ray-rank-avoidance-flow.test.mjs` が6件の必須条件と共有履歴を検証し、原典の特徴は `data/ray-rank-avoidance-problem-features.json` に記録します。

フィボナッチ列の区間加算、隣接交換による回文化、行ごとの採取個数制限、未定文字の補完と語の重複出現、平方積になる部分集合、共通XOR後の最大値の最小化は `python3 scripts/check_fib_palindrome_quota_cpp.py` で検証します。直接の配列更新・隣接交換BFS・全対象回文への安定対応・全経路と採取集合・文字の全置換・全部分集合・全Xとの比較に加え、GF(2)の階数による計数とフィボナッチ数の独立倍加法でも照合します。`tests/fib-palindrome-quota-flow.test.mjs` が6件の必須条件と共有履歴を検証し、原典の特徴は `data/fib-palindrome-quota-problem-features.json` に記録します。

少数指定頂点の接続費用と全域木の個数は `scripts/check_steiner_matrix_cpp.py`、一般グラフの最大組数とLCSのビット並列化は `scripts/check_blossom_lcs_cpp.py` で本文のC++を抽出して検証します。辺部分集合の全列挙・独立の集合DP・通常の全表LCSと比較し、奇閉路の入れ子、64ビット語の境界、法による零と行交換も確かめます。大小条件の極大対応は `scripts/check_threshold_matching_cpp.py` で全対応を列挙し、同期する複数グラフの距離和は `scripts/check_product_distance_cpp.py` で小さな積グラフを実際に構築して比較します。`tests/corpus-closure-flow.test.mjs` は6技巧の条件・共有履歴・図への移動・根への戻りを検証します。原典の特徴は `data/corpus-closure-problem-features.json` に保存します。

ICPC 2017の監査から追加した実数補正の方程式と重み付き整数代表値は `scripts/check_speed_quantization_cpp.py`、行列の最大高さを共有する配置と位置独立な文字置換は `scripts/check_silhouette_translation_cpp.py`、暗黙の全組の最大利益は `scripts/check_rectangle_profit_cpp.py` で検証します。既知の補正・全代表集合・全合法高さ配置・語全体のBFS・全二者比較を独立に使います。USACO Spaceshipの番号の再使用条件は `scripts/check_spaceship_cpp.py` で使用不可番号マスクの直接DPと比較します。`tests/icpc-priority-flow.test.mjs` が6技巧の条件・共有履歴・SVGリンクを確認し、`data/icpc-priority-problem-features.json` が確認済みの年・月と原典の特徴を保存します。

係数列の平方根は `scripts/check_fps_square_root_cpp.py` で、掲載コードと係数比較・直接二乗を照合します。先頭の零、平方根がない場合、7000件の乱数列、50万項、範囲外の引数を検査します。`tests/fps-square-root-flow.test.mjs` が法・出力・必要精度の確認と共有履歴を検証します。

IOI 2019とICPCの追加5技巧は、次のコマンドで記事中のC++20を直接抽出して検証できます。各コマンドに `--sanitize` を付けるとASan/UBSanでも実行します。

| 技巧 | 検証コマンドと比較対象 |
|---|---|
| 同サイズの左右を対にする最小隣接交換 | `python3 scripts/check_oriented_pair_swaps_cpp.py` — 合法な完成列を始点にした全隣接交換BFS |
| 未知の二画素の距離判定回路 | `python3 scripts/check_two_mark_manhattan_circuit_cpp.py` — 生成した全ゲートを実行し、直接の座標差と比較 |
| 指定三サイズと二集合の連結性 | `python3 scripts/check_three_size_two_connected_cpp.py` — 頂点の全三分割と、集合内部の直接探索 |
| 一セル誤りを含むXOR格子更新の逆算 | `python3 scripts/check_xor_grid_predecessor_cpp.py` — 全前状態の直接更新と、一反転を含む履歴 |
| 確率付き時刻表の便と待機の選択 | `python3 scripts/check_stochastic_timetable_cpp.py` — 全決定方策と全運行結果の前向きシミュレーション |

`tests/ioi-2019-three-flow.test.mjs` と `tests/icpc-inverse-timetable-flow.test.mjs` は5件の入口・必要条件・共有履歴に加え、追加前の498/501経路、質問ラベル、到達先、初回調査記録の不変性を独立に検証します。詳細な取得根拠と実装の確認記録は `research/technique-verifications/` に置き、教材本文と分けています。後から得た証明は初回の未確認記録を書き換えずに反映し、解法確認・記事完成・分岐確認を別々に数えます。

二択列の正確な個数と復元、集合の色数からの未知関係、木の全同色頂点の併合、格子三マス候補の入替えは `tests/joi-closure-cpp.test.mjs` から掲載したC++を検証します。全選択列・原色と好みの直接シミュレーション・全色集合の連結性・候補部分集合と全コピー探索を独立oracleにし、最大100万位置・20万頂点・質問回数上限・ロールバック・独立出力validatorを確認します。`tests/joi-closure-flow.test.mjs` が4技巧の13適用条件と原典の日付・共有履歴・初回監査からの解消記録を検証します。

相互辺による有向閉包、区間端点の縮小、生存位置を指定する二本ずつの高さ列、左右角の対応と境界検査は `tests/joi-dynamics-cpp.test.mjs` で検証します。規則の固定点・点の直接移動・元の重複順列の同時更新・全角対応順列を独立oracleにし、最大規模と退化例も比較します。`tests/joi-dynamics-flow.test.mjs` は4技巧の13条件・二種類の縮小対象・別分野からの入口・共有履歴・原典と日付精度を確認します。

通常ビルド後の内部リンク・SVG・Pagefind検査は `npm run verify:links`。`--external` を付けると原典のHTTP確認も行います。

ブラウザ検証は依存インストール後に `npx playwright install chromium`、`npm run test:browser`。スマートフォン幅、検索、質問・図の切替、経路強調、共有、拡大縮小、JavaScript無効時の表示を確認します。

`tests/usaco-interval-grid-cpp.test.mjs` は巨大区間からのXOR三数計数を直接列挙・独立した桁DPと比較し、部分長方形の同色成分数を局所BFSの8,488,341問い合わせと照合します。`tests/usaco-interval-grid-flow.test.mjs` は適用条件・共有履歴・使用例と追加前487歩行の不変性を検証します。

`tests/usaco-mincost-cpp.test.mjs` は巨大格子の区分二次費用を、全小格子DP・境界の閉形式・最大制約の21,926,323比較で検証します。`tests/usaco-mincost-flow.test.mjs` は特徴・必要条件・元の489歩行を確認します。

`tests/clue-partition-cpp.test.mjs` は局所条件付き三集合の分割を、13,521,480の直接配分と比較します。`tests/clue-partition-flow.test.mjs` は特徴・必要条件・元の490歩行と、非公式資料の区別を確認します。

`tests/joi-path-arrivals-cpp.test.mjs` はビル上の星の削除と祖先パスの選択を全小画像・全経路集合と比較し、再生する対象の円周収穫と時間付き巡回の累積到着を26,409,576比較で検証します。`tests/joi-harvest-constellation-flow.test.mjs` は原典向けと一般形の四入口・適用条件・旧491歩行を確認します。

## リポジトリと公開

保存先は `harurunrunrun/flowchartcp` の非公開リポジトリを想定しています。アップロード前にローカルで確認します。

GitHub Actionsは検証・静的ビルド・成果物の保存のみです。Pagesのデプロイはありません。将来の公開先に合わせて `site: https://harurunrunrun.github.io`、`base: /flowchartcp` を設定しています。

`tests/joi-path-arrivals-cpp.test.mjs` は、ビルの上に残す星を長方形の直接判定と祖先パス集合で比較し、円周の収穫を秒単位の物理シミュレーションと個体ごとの移動で照合します。`tests/joi-harvest-constellation-flow.test.mjs` は原典向けと一般形の4入口、全条件の否定・不明、追加前491経路を確認します。

`tests/ioi-local-construction-cpp.test.mjs` は、中央値得点の券配分を元の全割当と比較し、単純路本数の構築を全小グラフ・全小対称行列と照合します。木の局所経路選択は全小木・全根をBFSと比較し、準備関数を含まない別実行ファイルでも確認します。`tests/ioi-local-construction-flow.test.mjs` は3技巧の条件、後続証明による解消、追加前493経路を検証します。

`tests/equal-bag-mixture-cpp.test.mjs` は、等しい合計の袋の数え上げを37,626,900通りの実物配分と比較し、原典範囲の1000連続呼出しを検証します。二始点の混合流は91,138,194通りの有限二種流割当と全小グラフのカットを比較し、最大200頂点・19900辺・分母10^10、および表示後の容量・保存則・同方向を照合します。`tests/equal-bag-values-flow.test.mjs` と `tests/two-source-mixture-flow.test.mjs` で必要条件と旧経路を検証します。

隣接変化回数の質問は `python3 scripts/check_transition_species_cpp.py` で、全小固定配置・全小適応返答枝・226問の最悪例・原典adapterとstub無しcallbackの別リンクを検証します。読点規則の閉包は `python3 scripts/check_word_boundary_comma_cpp.py` で、規則の直接反復・全閉包候補・独立の字句文法・最大入力と追加後の全文を検証します。両方とも `--sanitize` でASan/UBSanを実行できます。

`tests/combo-flow.test.mjs` と `tests/plants-flow.test.mjs` は接頭辞の質問と循環窓の比較を、問題の特徴からの入口・条件確認・共有履歴・既存505/506経路と初回監査記録の保持まで検証します。`tests/prefix-cyclic-order-cpp.test.mjs` は公開C++20を実際に抽出して、未知列の直接照合、全整合順列からの比較、独立した近距離グラフの到達性と照合します。

`tests/ioi-2018-rectangle-flow.test.mjs` は格子の番号交換と二閾値の移動について、既存507経路・初回6題の監査・条件不足の分岐・表示と共有履歴を検証します。`tests/ioi-2018-rectangle-cpp.test.mjs` は公開コードを抽出し、外接長方形と二形態BFSの独立oracleに加え、5×5の全非空配置とコピー時の割当失敗も確認します。追加調査の再実行用コードは `research/probes/` に保存しています。

`tests/ioi-2018-circuits-flow.test.mjs` は交互回路と二重み距離の質問を、旧509経路と455図・3,601旧ノードの保持、全必要条件、両表示と履歴共有まで検証します。`tests/ioi-2018-circuits-cpp.test.mjs` は公開コードを抽出し、実際のスイッチ反転とDijkstraによる独立返答で、小入力・最大入力・最悪予算を検証します。
