# 調査用の収集基盤

サイト用教材と問題メタデータの収集を分離する。問題本文は保存せず、タイトル・原典URL・公開索引に含まれる属性だけを取得する。収集で得たタグは未確認候補であり、技巧記事の使用例一覧には自動掲載しない。

```sh
node scripts/collect.mjs --source all --until 2026-10-14 --resume --limit 3
node scripts/lib/ledger.mjs
```

`--limit` は今回処理するバッチ数。AtCoderは1コンテスト、Library Checkerは1問題、CodeforcesとCSESは公式の索引全体を1バッチとする。制限を外すと公開範囲の列挙完了まで進む。`--until` は日本時間のその日の終わり。基準日を変える場合は別の `--output` ディレクトリを使うか、`--resume` を外して新しく収集する。

`research/raw/<source>.jsonl` はID順の重複のないメタデータ、`<source>.checkpoint.json` は成功済みの位置・件数・対象範囲を保持する。各バッチを一時ファイルからrenameして保存し、その後カーソルを保存する。途中失敗では成功済みデータを保持し、同じコマンドの `--resume` で再開できる。初回バッチ前に新しい収集が失敗した場合は、以前の完全スナップショットとカーソルを保持し、失敗を `<source>.attempt.json` に残す。

HTTPリクエスト間隔は2.1秒以上。429/5xx/通信失敗は最大3回再試行し、403等は再試行しない。認証やアクセス制限を回避する処理はない。

| 出典 | 自動収集の対象 | 基準日の扱い |
| --- | --- | --- |
| Codeforces | 公式APIの通常problemset。Gym・グループ・非公開・acmsguruを除く | contest.listの開催時刻で判定。開催日不明は除外件数を記録 |
| AtCoder | 公式コンテストアーカイブとタスク一覧 | アーカイブの開催時刻で判定。アクセス不能は失敗として保持 |
| Library Checker | 公式repoのinfo.tomlとディレクトリ分類 | 基準日以前の最終commitで固定。repoへの追加とjudge公開は同一視しない |
| CSES | 現在の公式Problem Setの一覧 | 掲載日が索引にないためhistorical cutoff未確認の候補として記録 |

その他の出典は `data/sources.json` で所在・公開範囲・アクセス状況を登録する。登録や入口の所在確認は全件列挙に数えない。

`ledger.mjs` は明示的に実行する台帳更新コマンド。rawの実取得件数と、チェックインされた `references-*.json` の確認済み対応を集計する。`metadataCollected` は自動取得数、`bootstrapProblems` は教材作成時に確認した問題数、`fetched` は両者のIDの和集合。`solutionReviewed` は解説または参照解答の確認済み問題数、`techniquesExtracted` は確認済み問題と技巧の対応数。`official-tag` は形式確認として別集計し、解法を読んだ件数には入れない。出典ごとの歴史上の真の全問題数は、証明できるまでは `totalKnown: null` とする。

Node標準ライブラリだけで動く。テストはfetchを注入して、再試行・ページ送り・基準日・重複排除・失敗と再開・スナップショット保持を検証する。
