import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

export default defineConfig({
  site: 'https://harurunrunrun.github.io',
  base: '/flowchartcp',
  trailingSlash: 'always',
  output: 'static',
  markdown: { remarkPlugins: [remarkMath], rehypePlugins: [rehypeKatex] },
  integrations: [starlight({
    title: '競技プログラミング知識大全集',
    description: '競技プログラミングの解法に使う具体的なテクニックをまとめています。',
    defaultLocale: 'root',
    locales: { root: { label: '日本語', lang: 'ja' } },
    customCss: ['./src/styles/custom.css', 'katex/dist/katex.min.css'],
    sidebar: [
      { label: '目次', link: '/flowchartcp/' },
      { label: '解法フローチャート', slug: 'flowcharts' },
      { label: '計算量を減らすテクニック', slug: 'complexity' },
      { label: '高度なテクニック', slug: 'advanced' },
      { label: '考察のテクニック', slug: 'reasoning' },
      { label: 'テクニック一覧', slug: 'catalog' },
      { label: '基本アルゴリズム・データ構造', slug: 'basics' },
      { label: '出典', slug: 'research' },
      { label: '各記事', autogenerate: { directory: 'techniques' }, collapsed: true },
    ],
    pagination: false,
    tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 2 },
  })],
});
