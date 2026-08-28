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

// ★있는지부터 본다. 예전엔 바뀌었는지로 판단해서, 이미 그 버전이면 '못 찾았다'로 죽었다(8-28)
if (!/window\._SW_V = '\d+'/.test(ix)) { console.error('index.html 에서 window._SW_V 를 못 찾았다'); process.exit(1); }
ix = ix.replace(/window\._SW_V = '\d+'/, `window._SW_V = '${next}'`);

fs.writeFileSync(SW, sw);
fs.writeFileSync(IX, ix);

// ★version.txt 도 같이 올린다 (8-28). 여기를 빠뜨려 check_version.py 가 배포를 막았다 —
//   버전이 적힌 곳이 셋인데 스크립트가 둘만 고치면 "손으로 고치다 빠뜨리는 사고"가 그대로 남는다.
const VT = 'version.txt';
if (fs.existsSync(VT)) {
  const curTxt = fs.readFileSync(VT, 'utf8');
  const tail = curTxt.slice(String(cur).length);   // 줄바꿈이 있었으면 그대로 둔다
  fs.writeFileSync(VT, String(next) + tail);
}
console.log(`v${cur} -> v${next}   (sw.js ${swHits}곳, index.html _SW_V 1곳, version.txt)`);
