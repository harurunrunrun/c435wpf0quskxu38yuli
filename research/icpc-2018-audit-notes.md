ICPC World Finals 2018 固定監査（2026-10-15、cutoff 2026-10-14）

公式冊子は22頁、問題見出しはAからKまでの全11題。競技日は2018年4月19日。大会全体の日程4月15〜20日と区別した。日付と問題総数を確定し、11題を固定してから技巧検索・分岐調査を行った。難度の数値資料は得ておらず、全件null。

- [公式問題冊子](https://icpc.global/worldfinals/problems/2018-ICPC-World-Finals/icpc2018.pdf)
- [ICPC公式大会ニュース](https://news.icpc.global/wf2018/)
- [公式brochure](https://icpc.global/community/history/brochures/world-finals-2018-brochure.pdf)
- [公開solution sketches](https://icpc.global/worldfinals/problems/2018-ICPC-World-Finals/finals2018solutions.pdf)

解法集の著者はPer AustrinとJakub Onufry Wojtaszczyk。冒頭が自らunofficial analysisと明記するので、公式ドメイン上の公開sketchと記録した。公式解説確認済み件数は0。冊子・公開sketchの全11節は読んだが、CとJは主要な根拠が足りず解法確認済みには数えない。変換HTMLの個別ページで読めなかったものを、読めた資料として数えていない。

凍結対象は472記事・472技巧metadata・439flow graph・15分野根。raw SVGは435枚であり、flow graph数との混同を避けた。親のIOI統合前にdata JSON、記事、src/lib、SVG、監査に使うhelperを1047ファイルへコピーし、各SHAとbyte数を保存した。

snapshot: research/snapshots/icpc-2018-{flow,technique}.json.gz（分岐とmetadata）
manifest SHA256: 246e41da7f29fbd319552dbb852f4727da46ca2dba3ef4e71f0b35f2bf896705
flows.json SHA256: 39a3d2089b8f5ac9e684092543ac49f5005555d3b6e8c0d4be3cdc2a9b1e0181

固定問題リストと初回監査は完了したためfixedProblemListCompleteとfirstPassAuditCompleteをtrueとする。fixedCorpusResearchCompleteは全11題の主要解法・補題を確認した時だけtrueであり、C/Jの証明不足がある現在はfalse。solutionReviewedCountは9。

監査結果は具体技巧不足9、未確認2、covered0、missing-route0。一般的なBFS・期待値・木DP・Fenwickがあるだけでは、具体帰着と適用条件の実装があるとは扱わなかった。初回分類の母集団は今回の全11題であり、全世界の網羅性を示す結果ではない。

| 問 | 題名 | 初回結果 | 特徴から辿った経路・停止位置 | 必要な粒度 |
| --- | --- | --- | --- | --- |
| A | Catch the Plane | missing-technique | game-probability → repeated-trials → probability-processes/goal | 確率付き時刻表の逆時刻DP、到着と出発の同時刻一括処理 |
| B | Comma Sprinkler | missing-technique | strings → changes → strings-change-goals/text-task | 語の前後二状態、文内隣接による無向閉包 |
| C | Conquer The World | unconfirmed | flow-matching → quantity-goals → costs → yes → mincost | 余剰を残せる木輸送、凸な限界費用の併合とsplitの償却 |
| D | Gem Island | missing-technique | game-probability → stateful-process → goal | 増殖urnの一様組成への変換、依存する上位rの総和計数 |
| E | Getting a Jump on Crime | missing-technique | geometry → travel-partition → geometry-task | 高い放物線の支配性、建物通過の両端判定と有向辺構築 |
| F | Go with the Flow | missing-technique | dp → sequence-removals → split → split-kind | 行幅固定の貪欲折返し、実在する空白だけの行間DP |
| G | Panda Preserve | missing-technique | geometry → enclosing-regions → point-set-shapes → goal | 固定サイトの最遠最寄り点、Voronoi頂点と多角形境界交点 |
| H | Single Cut of Failure | missing-technique | geometry → boundary-relations → geometry-task | 境界上の弦の交互端点、全ラベル一回の巡回窓 |
| I | Triangles | missing-technique | geometry/geometry-task（根に該当する回答がない） | 三方向runの三角形、斜辺の失効時刻によるFenwick計数 |
| J | Uncrossed Knight’s Tour | unconfirmed | grid-arrangements → movement-cycles → goal | 二行跨ぎのナイト辺・交差禁止のfrontier、巨大長への周期保証 |
| K | Wireless is the New Fiber | missing-technique | thinking → operation-goals → graph-build → distance-two | 次数保存をN−2予算へ直す貪欲と正の木次数列の復元 |

Cでは一般の最小費用流に到達するが、最大規模に対応できる木専用処理はない。別に木DP根からも追跡し、一般の全体最適値の分岐まで確認した。公開sketchの凸性証明とsplit移動総量≤2Xの根拠が省略されているので、資料読了を解法の完全確認と同一視しない。

Jの既存frontier-single-cycleは四近傍・全指定マス・個数計算。ナイト辺・部分集合の最大化へ答えを合わせることはできないため、その枝へ無理にyesを選んでいない。公開sketchのn≤200の観測だけから10^15までの最適周期を主張する根拠は未確認。周期を繰返して作れる下界だけでは上界は証明できない。

Dは総和Sの基底の正規化に不整合がある。独立に再導出した三次以下のDPではn≤rの基底を(n+d)×組成数にする。n=2,d=1,r=2の総和は6であり、sketchに印字された3とは異なる。補正DPを小さい全組成189条件で照合し、urnの有理数分布5004状態で等確率性を照合した。より速い包除版の演習部分は採用候補へ昇格していない。

Iは斜辺の条件D(x−i,y)≥iからj=x−iと置けば、j+D(j,y)≥xとなる。公開sketchの有効点説明から座標jが欠ける一方、直後の失効時刻j+Dは整合する。等号時刻の照会後に失効する。任意run長について29784照会を直接条件と比較した。ASCII解析や完成三角形計数実装の検証ではない。

追加の小規模研究検査として、Aの逆イベント処理と再帰的意思決定1500例、Hの巡回端点matchingと全gap対446例、Kの次数保存貪欲と全木次数列5345ベクトルも照合した。これらは補題の検査に限定し、完成C++・最大規模・数値安定性のテストとは記録していない。研究用スクリプトと結果は research/probes/icpc-2018-research-checks.py と同名.json。

監査JSONは既存icpc-2017-world-finals監査形式を参考にした。凍結版src/lib/flow.tsを実際にcompileし、全11経路と追加2経路を再生。分野根・各回答・停止位置・その時点の選択肢・関連記事のSHAと適用外理由を記録した。既存corpus-progress helperも原典確認11、解法確認9、C/J未確認と判定した。未実装候補IDの重複・関連metadataの存在・全null難度・全競技日の整合も照合した。

共有ファイルの変更は0。コード記事・公開対応reference・新しい分岐は今回作成していない。親が統合する場合は、この初回結果とsnapshotを保持し、完成記事・独立検証・自然な分岐が揃った後のresolutionを別に追加する。

恒久snapshotは分岐とmetadataのgzip、および1047ファイルの初回SHA台帳です。全MDXとSVGの元コピーを恒久保存したとはしません。`tests/icpc-2018-fixed-corpus.test.mjs` が全11題の初回経路・停止位置・回答ラベルと、主要補題未確認2題を独立に再生します。


## 2026-10-15 次数保存と比例増殖の不足を解消

Kは次数保存費用d−1の予算化と任意木の復元、Dは初期重み1の一様弱合成への変換と上位合計の非負DPを追加した。初回のpositive研究・未作成実装・全停止位置と既存resolutionを保存し、各行にresolutionだけを追加。Dの非公式sketch基底の補正と二次時間別解の未確認は残す。全原典範囲の完全C++20、作者/root/独立review者の通常・ASan/UBSan、異なる厳密oracle、根の特徴分岐を確認した。

502記事/469図/523対応、ICPC2018研究9/11・記事対応4/11。61組の回帰、ローカルビルド、日英全角129検索、全SVG/内部リンクの検証に成功。検証記録は `verification-2026-10-15-degree-polya-ioi2017.json`。世界全体の網羅完了ではない。


## 2026-10-15 折返しと空白の連なりの不足を解消

Fの実単語間空白だけの行間DP、次配置変化幅、貪欲行数の上界による停止を完全C++20で追加。初回positive研究と既存4resolutionを保存し、Fへresolutionだけ追加した。全小文字grid・全整数幅・直接path・最大7構成、別の全改行partition/boolean閉包、作者/root/独立レビューの通常/ASanで比較。保守的な最悪時間O(N²(L+1))を明記し、未証明の漸近改善を主張しない。

503記事/470図/524対応、ICPC2018研究9/11・記事対応5/11。ローカルビルド、日英全角133検索、全図/内部リンク、対象10組の回帰が成功。直前502記事で通った全61組の再実行とは区別する。記録は `verification-2026-10-15-space-river.json`。
