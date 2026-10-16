import { cutoffEnd } from './collection.mjs';

export function plainText(html) {
  return html.replace(/<[^>]*>/g, ' ').replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(+n)).replace(/&#x([\da-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16))).replace(/&amp;/g, '&').replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;/g, ' ').replace(/\s+/g, ' ').trim();
}
const links = html => [...html.matchAll(/<a\b[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi)].map(([, href, title]) => ({ href, title: plainText(title) }));

export function parseLibraryCheckerTitle(toml) {
  // Official metadata uses TOML literal strings as well as basic strings.
  const literal = toml.match(/^title\s*=\s*'([^']*)'/m);
  if (literal) return literal[1];
  const basic = toml.match(/^title\s*=\s*("(?:\\.|[^"\\])*?")/m);
  if (basic) return JSON.parse(basic[1].replace(/\\U([\da-fA-F]{8})/g, (_, hex) => JSON.stringify(String.fromCodePoint(parseInt(hex, 16))).slice(1, -1)));
  throw new Error('Official Library Checker metadata is missing a supported title');
}

export function parseAtCoderArchive(html) {
  const contests = [];
  for (const [, row] of html.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)) {
    const date = row.match(/\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\+\d{4})?/);
    const contest = links(row).find(x => /^\/contests\/[\w-]+$/.test(x.href));
    if (!date || !contest) continue;
    const startedAt = new Date(date[0].replace(' ', 'T').replace(/\+(\d{2})(\d{2})$/, '+$1:$2') + (date[0].includes('+') ? '' : '+09:00')).toISOString();
    contests.push({ id: contest.href.split('/').pop(), title: contest.title, startedAt });
  }
  return contests;
}

export function parseAtCoderTasks(html, contest) {
  const tasks = new Map();
  for (const item of links(html)) {
    if (!new RegExp(`^/contests/${contest.id}/tasks/[\\w-]+$`).test(item.href)) continue;
    const problemId = item.href.split('/').pop();
    const existing = tasks.get(problemId);
    if (!existing || item.title.length > existing.title.length) tasks.set(problemId, { id: `atcoder:${problemId}`, source: 'atcoder', problemId, title: item.title, url: `https://atcoder.jp${item.href}`, contestId: contest.id, contestTitle: contest.title, startedAt: contest.startedAt, difficulty: null, tags: [], verification: 'unreviewed', editorialUrl: `https://atcoder.jp/contests/${contest.id}/editorial` });
  }
  return [...tasks.values()];
}

export function createAdapter(source, http, until) {
  const end = +cutoffEnd(until);
  if (source === 'codeforces') return { async next(cursor) {
    if (cursor?.done) return { records: [], cursor, done: true };
    const contests = await http.get('https://codeforces.com/api/contest.list?gym=false', 'json');
    const problemset = await http.get('https://codeforces.com/api/problemset.problems', 'json');
    if (contests.status !== 'OK' || problemset.status !== 'OK') throw new Error('Codeforces API returned a failed result');
    const dates = new Map(contests.result.filter(c => c.startTimeSeconds).map(c => [c.id, c.startTimeSeconds * 1000]));
    let excludedUnknownDate = 0;
    const records = [];
    for (const problem of problemset.result.problems) {
      const timestamp = dates.get(problem.contestId);
      if (timestamp === undefined) { excludedUnknownDate++; continue; }
      if (timestamp > end) continue;
      const problemId = `${problem.contestId}${problem.index}`;
      records.push({ id: `codeforces:${problemId}`, source, problemId, title: problem.name, contestId: String(problem.contestId), startedAt: new Date(timestamp).toISOString(), url: `https://codeforces.com/problemset/problem/${problem.contestId}/${problem.index}`, difficulty: problem.rating == null ? null : `rating ${problem.rating}`, tags: problem.tags ?? [], verification: 'unreviewed', editorialUrl: null });
    }
    return { records, cursor: { done: true }, done: true, discovered: problemset.result.problems.length, excludedUnknownDate, scope: 'Official public regular problemset; Gym/private/group/acmsguru excluded. Contest start date used for cutoff. Tags are unreviewed hints.' };
  }};
  if (source === 'atcoder') return { async next(cursor) {
    let state = cursor ?? { page: 1, queue: [], index: 0, discovered: 0 };
    while (true) {
      if (state.index >= state.queue.length) {
        const html = await http.get(`https://atcoder.jp/contests/archive?lang=en&page=${state.page}`);
        const queue = parseAtCoderArchive(html);
        if (!queue.length) {
          if (!/<table|Contest Archive/i.test(html)) throw new Error('Unexpected AtCoder archive response; refusing to mark complete');
          return { records: [], cursor: state, done: true, discovered: state.discovered, scope: 'Official public archive and task index; private/inaccessible contests excluded.' };
        }
        state = { page: state.page + 1, queue, index: 0, discovered: state.discovered + queue.length };
      }
      const contest = state.queue[state.index];
      const next = { ...state, index: state.index + 1 };
      if (+new Date(contest.startedAt) > end) { state = next; continue; }
      const html = await http.get(`https://atcoder.jp/contests/${contest.id}/tasks?lang=en`);
      const records = parseAtCoderTasks(html, contest);
      if (!records.length) throw new Error(`No public task metadata parsed for ${contest.id}; inspect access or markup before retrying`);
      return { records, cursor: next, done: false, discovered: records.length, scope: 'Official public archive/task indexes; progress cursor is per contest. Discovery count is problem metadata, not a claimed global total.' };
    }
  }};
  if (source === 'library-checker') return { async next(cursor) {
    let state = cursor;
    if (!state) {
      const commits = await http.get(`https://api.github.com/repos/yosupo06/library-checker-problems/commits?until=${encodeURIComponent(cutoffEnd(until).toISOString())}&per_page=1`, 'json');
      if (!commits[0]?.sha) throw new Error('No official Library Checker commit exists before cutoff');
      const sha = commits[0].sha;
      const tree = await http.get(`https://api.github.com/repos/yosupo06/library-checker-problems/git/trees/${sha}?recursive=1`, 'json');
      if (tree.truncated) throw new Error('GitHub tree is truncated; completeness cannot be established');
      state = { sha, paths: tree.tree.filter(t => t.type === 'blob' && /^[^/]+\/[^/]+\/info\.toml$/.test(t.path)).map(t => t.path).sort(), index: 0 };
      if (!state.paths.length) throw new Error('No Library Checker info.toml entries found');
    }
    if (state.index >= state.paths.length) return { records: [], cursor: state, done: true, discovered: state.paths.length };
    const file = state.paths[state.index];
    const toml = await http.get(`https://raw.githubusercontent.com/yosupo06/library-checker-problems/${state.sha}/${file}`);
    const problemId = file.split('/')[1];
    const title = parseLibraryCheckerTitle(toml);
    const next = { ...state, index: state.index + 1 };
    return { records: [{ id: `library-checker:${problemId}`, source, problemId, title, url: `https://judge.yosupo.jp/problem/${problemId}`, difficulty: null, tags: [file.split('/')[0]], verification: 'unreviewed', editorialUrl: `https://github.com/yosupo06/library-checker-problems/tree/${state.sha}/${file.slice(0, -10)}/sol`, revision: state.sha }], cursor: next, done: next.index === state.paths.length, discovered: state.paths.length, scope: `Official repository metadata at cutoff commit ${state.sha}; categories are hints. A repository snapshot is not proof every entry was already published in the judge.` };
  }};
  if (source === 'cses') return { async next(cursor) {
    if (cursor?.done) return { records: [], cursor, done: true };
    const html = await http.get('https://cses.fi/problemset/list/');
    const records = links(html).filter(x => /^\/problemset\/task\/\d+\/?$/.test(x.href)).map(x => ({ id: `cses:${x.href.match(/\d+/)[0]}`, source, problemId: x.href.match(/\d+/)[0], title: x.title, url: `https://cses.fi${x.href}`, difficulty: null, tags: [], verification: 'unreviewed', editorialUrl: null, publicationDate: null, cutoffVerified: false }));
    if (!records.length) throw new Error('No CSES task index found');
    return { records, cursor: { done: true }, done: true, discovered: records.length, scope: 'Current official public problemset index. CSES does not expose publication dates here; historical cutoff is unverified and these records remain research candidates.' };
  }};
  throw new Error(`No automated adapter for ${source}`);
}
