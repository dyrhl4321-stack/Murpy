// index.html 압축 — 배포 산출물 전용 (GitHub Actions `.github/workflows/pages.yml` 이 부른다)
//
//   node tools/build/minify-index.mjs <원본 index.html> <결과 경로>
//
// ★저장소의 index.html 은 그대로 둔다. 테스트·문법 검사·다른 창은 전부 원본을 읽는다.
//   여기서 만든 파일은 Pages 에 올라가는 사본일 뿐이다.
// ★하는 일은 세 가지뿐이다 — 인라인 <script> 압축, <style> 압축, 마크업의 HTML 주석 제거.
//   마크업 공백·속성·onclick 문자열은 건드리지 않는다(화면이 달라질 여지를 안 만든다).
//   CSS 는 공백·주석만 뺀다(값·규칙은 그대로).
// ★classic <script> 는 맨 위 이름을 바꾸지 않는다 — onclick="foo()" 와 다른 블록이 그 이름으로 부른다.
//   module 블록만 맨 위 이름까지 줄인다(모듈 밖에서는 어차피 window.xxx 로만 닿는다).
// ★실패하면 0 이 아닌 코드로 끝난다. 워크플로가 그때는 원본을 그대로 올린다 — 압축 때문에 배포가 막히면 안 된다.
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const [src, out] = process.argv.slice(2);
if (!src || !out) {
  console.error('사용법: node tools/build/minify-index.mjs <원본 index.html> <결과 경로>');
  process.exit(2);
}

const esbuild = await import('esbuild');
const html = fs.readFileSync(src, 'utf8');
const gz = s => zlib.gzipSync(Buffer.from(s), { level: 9 }).length;

// sw.js 의 htmlMatchesThisWorker 와 tools/check_version.py 가 이 모양 그대로를 찾는다.
const SW_V_EXACT = /window\._SW_V = '(\d+)'/g;
const before = [...html.matchAll(SW_V_EXACT)];
if (before.length !== 1) throw new Error(`원본의 window._SW_V 대입이 ${before.length} 곳이다 (1곳이어야 한다)`);
const version = before[0][1];

const JS_TYPES = new Set(['', 'text/javascript', 'module']);
const BLOCK = /<(script|style)\b([^>]*)>([\s\S]*?)<\/\1\s*>/gi;

async function minifyJs(code, isModule) {
  const r = await esbuild.transform(code, {
    loader: 'js',
    minify: true,
    charset: 'utf8',           // 한글을 \uXXXX 로 풀지 않는다
    legalComments: 'none',
    format: isModule ? 'esm' : undefined,   // classic 은 format 을 안 준다 → 맨 위 이름 보존
    target: 'es2020',
  });
  return r.code.trimEnd();
}

async function minifyCss(code) {
  const r = await esbuild.transform(code, {
    loader: 'css',
    // 공백·주석만 뺀다. minifySyntax 는 translateX(-50%)→translate(-50%) 처럼 값을 고쳐 쓰고
    // 이웃 규칙을 합친다 — 뜻은 같아도 "브라우저가 읽은 규칙이 원본과 글자까지 같다"를 검증할 수 없게 된다.
    minifyWhitespace: true,
    charset: 'utf8',
    legalComments: 'none',
  });
  if (r.warnings.length) {
    for (const w of r.warnings.slice(0, 5)) console.warn('css 경고:', w.text, w.location ? `(${w.location.line}:${w.location.column})` : '');
  }
  return r.code.trimEnd();
}

// 마크업 조각: HTML 주석만 지운다. <textarea> 안은 글자 그대로라 건너뛴다.
function stripComments(markup) {
  return markup.replace(/(<textarea\b[\s\S]*?<\/textarea\s*>)|<!--[\s\S]*?-->/gi, (m, keep) => keep || '');
}

let result = '';
let last = 0;
const stats = { js: 0, css: 0, skipped: 0 };
for (const m of html.matchAll(BLOCK)) {
  const [whole, tag, attrs, body] = m;
  result += stripComments(html.slice(last, m.index));
  last = m.index + whole.length;
  const lower = tag.toLowerCase();
  if (lower === 'style') {
    result += `<style${attrs}>${await minifyCss(body)}</style>`;
    stats.css++;
    continue;
  }
  const type = (/\btype\s*=\s*["']?([^"'\s>]+)/i.exec(attrs) || [, ''])[1].toLowerCase();
  const hasSrc = /\bsrc\s*=/i.test(attrs);
  if (hasSrc || !JS_TYPES.has(type) || !body.trim()) {
    result += whole;   // 외부 스크립트·JSON 등은 그대로
    stats.skipped++;
    continue;
  }
  let code = await minifyJs(body, type === 'module');
  if (/<\/script/i.test(code)) throw new Error('압축 결과에 </script 가 들어 있다 — 블록이 중간에 끊긴다');
  result += `<script${attrs}>${code}</script>`;
  stats.js++;
}
result += stripComments(html.slice(last));

// 압축기가 `window._SW_V="1219"` 로 바꾼 것을 서비스워커가 찾는 모양으로 되돌린다.
const loose = /window\._SW_V\s*=\s*(["'])(\d+)\1/g;
const hits = [...result.matchAll(loose)];
if (hits.length !== 1 || hits[0][2] !== version) {
  throw new Error(`압축 뒤 window._SW_V 대입이 ${hits.length} 곳이다 (원본 버전 ${version})`);
}
result = result.replace(loose, `window._SW_V = '${version}'`);
if ([...result.matchAll(SW_V_EXACT)].length !== 1) throw new Error('버전 표식 복원 실패');

// 상식 검사 — 터무니없이 작아졌으면 뭔가 잘려 나간 것이다.
const inBytes = Buffer.byteLength(html), outBytes = Buffer.byteLength(result);
if (outBytes >= inBytes) throw new Error(`압축 결과가 원본보다 크다 (${outBytes} >= ${inBytes})`);
if (outBytes < inBytes * 0.35) throw new Error(`압축 결과가 너무 작다 (${outBytes} < 원본의 35%)`);
if (!/<\/html>\s*$/i.test(result)) throw new Error('결과가 </html> 로 끝나지 않는다');

fs.mkdirSync(path.dirname(out), { recursive: true });
fs.writeFileSync(out, result);
console.log(`v${version} · script ${stats.js}블록 · style ${stats.css}블록 · 그대로 둔 블록 ${stats.skipped}`);
console.log(`원본 ${inBytes} B (gzip ${gz(html)}) → 압축 ${outBytes} B (gzip ${gz(result)})`);
