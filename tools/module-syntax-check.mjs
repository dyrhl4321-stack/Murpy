// tools/module-syntax-check.mjs — index.html 의 <script type="module"> 블록 문법 검증
//
// ★왜 따로 있나 (2026-08-26 사고)
//   tools/dogam-syntax-check.mjs 는 **type 속성이 없는 <script> 블록만** 본다.
//   그래서 module 블록(파이어베이스·머피월드 대부분이 여기 산다)이 깨져도 "OK" 가 떴다.
//   실제로 v758 에서 `if (have) ...` 줄만 주석으로 바꿔 **else 가 고아**가 됐는데
//   그 검사기는 통과시켰고, module 이 통째로 파싱 실패해
//   **Firebase 초기화가 안 되어 전 유저 로그인이 막혔다.**
//
// ★index.html 을 고쳤으면 **두 검사를 항상 같이** 돌린다:
//     node tools/dogam-syntax-check.mjs
//     node tools/module-syntax-check.mjs
//
// module 은 new Function 으로 못 만든다(import 구문). 파일로 떨궈 `node --check` 를 태운다.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const blocks = [...html.matchAll(/<script type="module">([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!blocks.length) { console.error('NO_MODULE_BLOCK'); process.exit(2); }

let bad = 0;
blocks.forEach((code, i) => {
  const f = path.join(os.tmpdir(), `murpy_module_${process.pid}_${i}.mjs`);
  fs.writeFileSync(f, code, 'utf8');
  try {
    execFileSync(process.execPath, ['--check', f], { stdio: 'pipe' });
    console.log(`MODULE ${i}: OK (${code.split('\n').length} lines)`);
  } catch (e) {
    bad++;
    console.error(`MODULE ${i} SYNTAX ERROR:\n${(e.stderr || '').toString().slice(0, 1200)}`);
  }
  try { fs.unlinkSync(f); } catch {}
});
if (bad) process.exit(1);
