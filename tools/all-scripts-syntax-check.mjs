// index.html 의 **모든** <script> 블록을 통째로 파싱한다 (module 블록만 보던 module-syntax-check 의 사각지대).
// 9-07 밤: _FIELDS.park 뒤 쉼표 누락이 클래식 스크립트 블록을 통째로 죽여 머피월드·매칭이 먹통이었는데 기존 검사 2종이 못 잡았다.
import fs from 'fs';
import vm from 'vm';
const html = fs.readFileSync('index.html', 'utf8');
const re = /<script\b([^>]*)>([\s\S]*?)<\/script>/gi; let m, n = 0, bad = 0;
while ((m = re.exec(html))) {
  const attrs = m[1], src = m[2]; if (/\bsrc=/.test(attrs) || !src.trim()) continue; n++;
  const isModule = /type\s*=\s*["']module["']/.test(attrs);
  try {
    if (isModule) new vm.SourceTextModule ? new vm.SourceTextModule(src) : null;   // 모듈은 module-syntax-check 가 본다
    else new vm.Script(src, { filename: 'script#' + n });
  } catch (e) {
    bad++; const line = (html.slice(0, m.index + m[0].indexOf(src)).match(/\n/g) || []).length;
    console.log('x script#' + n + ' (html ' + line + '행부터): ' + e.message);
  }
}
console.log(bad ? ('FAIL ' + bad + ' block(s)') : ('OK ' + n + ' blocks'));
process.exit(bad ? 1 : 0);
