# ローカル確認用レンダラー

`markdown.mjs` は micromark 4.0.2、micromark-extension-gfm 3.0.0、KaTeX 0.16.47 をまとめたローカル確認用のバンドルです。各ライセンスをこのディレクトリに保存しています。KaTeX の CSS・フォントも同梱しています。

ネット接続なしで `npm run build:local` を使うための補助です。通常のサイト生成は Astro / Starlight / Pagefind が担当します。ローカル確認用の検索は独自の本文・名称検索です。

分岐データ・技巧記事・問題との対応は両ビルドで共通です。`typescript.cjs` は TypeScript 5.9.3 のトランスパイラーをまとめた補助バンドルです。型除去機能を含まないNode.js環境でも動作し、上流のApache-2.0ライセンスを保存しています。
