// 펫 하루 일과표 검증 — 실기기 없이 확인할 수 있는 유일한 부분이다.
//
//   node tools/pet_plan_check.mjs
//
// index.html 에서 일과표 함수만 떼어내 가짜 window 에 올리고 24시간을 훑는다.
// 재는 것: 종별 수면 시간 합계 · 덩어리 수 · 경계 연속성 · 같은 씨앗이면 같은 표인가.
// ★함수를 여기 복사해 두지 말 것 — 복사본은 반드시 본체와 어긋난다. 매번 index.html 에서 읽는다.
import fs from 'fs';

const src = fs.readFileSync('index.html', 'utf8');
const from = src.indexOf('window.PET_SLOT_MIN');
const to = src.indexOf('window._mwPetAct = function');
if (from < 0 || to < 0) { console.error('일과표 코드를 못 찾았습니다'); process.exit(1); }

const win = {};
new Function('window', src.slice(from, to))(win);

const SLOTS = win.PET_SLOTS;
let fail = 0;
const bad = (m) => { console.log('  실패: ' + m); fail++; };

for (const kind of ['cat', 'dog']) {
  const H = win.PET_HABIT[kind];
  let minS = 1e9, maxS = -1, minB = 1e9, maxB = -1, firstNotSleep = 0;
  const DAYS = 400;
  for (let d = 0; d < DAYS; d++) {
    const plan = win._mwPetPlan(kind, 'uid' + (d % 7) + '|pet|2026-8-' + d);
    if (plan.length !== SLOTS) bad(kind + ' 칸 수가 ' + plan.length);
    if (plan.some(v => !v)) bad(kind + ' 안 채워진 칸이 있다');

    const sleep = plan.filter(v => v === 'sleep').length;
    minS = Math.min(minS, sleep); maxS = Math.max(maxS, sleep);

    let blocks = 0;
    for (let i = 0; i < SLOTS; i++) if (plan[i] === 'sleep' && plan[i - 1] !== 'sleep') blocks++;
    minB = Math.min(minB, blocks); maxB = Math.max(maxB, blocks);

    if (plan[0] !== 'sleep') firstNotSleep++;      // 경계(새벽5시)는 반드시 자는 중이어야 한다
  }
  const h = (n) => (n * win.PET_SLOT_MIN / 60).toFixed(1);
  console.log(`${kind}  수면 ${h(minS)}~${h(maxS)}시간 (목표 ${h(H.sleepMin)}~${h(H.sleepMax)}) · 덩어리 ${minB}~${maxB}개 (목표 ${H.blocks.join('~')})`);
  if (minS < H.sleepMin || maxS > H.sleepMax) bad(kind + ' 수면 시간이 범위를 벗어난다');
  if (minB < H.blocks[0] || maxB > H.blocks[H.blocks.length - 1]) bad(kind + ' 덩어리 수가 범위를 벗어난다');
  if (firstNotSleep) bad(kind + ' 새벽 5시에 안 자는 날이 ' + firstNotSleep + '일');
}

// 같은 씨앗 = 같은 표 (손님도 나와 똑같은 걸 봐야 한다)
const a = win._mwPetPlan('cat', 'u|p|2026-8-24').join(',');
const b = win._mwPetPlan('cat', 'u|p|2026-8-24').join(',');
const c = win._mwPetPlan('cat', 'u|p|2026-8-25').join(',');
if (a !== b) bad('같은 씨앗인데 표가 다르다 — 손님이 나와 다른 걸 본다');
if (a === c) bad('날짜가 달라도 표가 같다 — 매일 같은 시각에 잔다');
console.log('같은 씨앗 = 같은 표: ' + (a === b ? 'OK' : '실패') + ' · 날짜별로 다른 표: ' + (a !== c ? 'OK' : '실패'));

// 하루 흐름 한 눈에 (사람이 읽고 이상한지 보는 용도)
const plan = win._mwPetPlan('cat', 'sample|cat_milky|2026-8-24');
const mark = { sleep: '.', rest: 'r', roam: 'W', act1: 'g', act2: 'o', eat: 'E' };
let line = '';
for (let i = 0; i < SLOTS; i += 2) line += (mark[plan[i]] || '?');
console.log('\n고양이 하루 (새벽5시부터, 한 글자=20분)\n' + line);
console.log('  . 잠  r 쉼  W 돌아다님  g 그루밍  o 관찰  E 밥');

console.log(fail ? `\n실패 ${fail}건` : '\n전부 통과');
process.exit(fail ? 1 : 0);
