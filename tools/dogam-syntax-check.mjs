// tools/dogam-syntax-check.mjs — index.html 일반 script 블록 문법만 빠르게 검증
import fs from 'node:fs';
const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
// type 속성 없는 <script> ... </script> 블록만 추출 (module=Firebase는 제외)
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!blocks.length) { console.error('NO_SCRIPT_BLOCK'); process.exit(2); }
let bad = 0;
blocks.forEach((code, i) => {
  try { new Function(code); }
  catch (e) { bad++; console.error(`BLOCK ${i} SYNTAX ERROR:`, e.message); }
});
if (bad) process.exit(1);
console.log(`OK ${blocks.length} script block(s) parsed`);
