// 배포 버전 한 번에 올리기 — sw.js 3곳 + index.html 의 _SW_V 를 같이 맞춘다.
//
// ★두 곳이 어긋나면 CDN 캐시가 안 깨져서 "푸시했는데 늦게 반영된다"가 다시 생긴다.
//   손으로 고치다 한 곳을 빠뜨리는 사고를 막으려고 만든 스크립트다.
//
//   node tools/bump-version.mjs          # 현재 버전 + 1
//   node tools/bump-version.mjs 305      # 특정 버전으로
import fs from 'fs';

const SW = 'sw.js', IX = 'index.html';
let sw = fs.readFileSync(SW, 'utf8');
let ix = fs.readFileSync(IX, 'utf8');

const cur = parseInt((sw.match(/murpy-v(\d+)/) || [])[1], 10);
if (!cur) { console.error('sw.js 에서 murpy-vNNN 을 못 찾았다'); process.exit(1); }
const next = process.argv[2] ? parseInt(process.argv[2], 10) : cur + 1;
if (!next || next <= 0) { console.error('버전이 이상하다:', process.argv[2]); process.exit(1); }

const swHits = (sw.match(/murpy-(?:static-|cdn-)?v\d+/g) || []).length;
sw = sw.replace(/murpy-v\d+/g, `murpy-v${next}`)
       .replace(/murpy-static-v\d+/g, `murpy-static-v${next}`)
       .replace(/murpy-cdn-v\d+/g, `murpy-cdn-v${next}`);

const before = ix;
ix = ix.replace(/window\._SW_V = '\d+'/, `window._SW_V = '${next}'`);
if (ix === before) { console.error('index.html 에서 window._SW_V 를 못 찾았다'); process.exit(1); }

fs.writeFileSync(SW, sw);
fs.writeFileSync(IX, ix);
console.log(`v${cur} -> v${next}   (sw.js ${swHits}곳, index.html _SW_V 1곳)`);
