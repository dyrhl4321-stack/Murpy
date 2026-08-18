// 방 가구 카탈로그 검증 — index.html 에서 ROOM_ITEMS / mwDefFor 를 추출해 본다
// 실행: node tools/tests/room-items.test.mjs
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
function grab(re, name) {
  const m = src.match(re);
  assert(m, `index.html에서 ${name}를 찾지 못함`);
  return m[0];
}
const w = { SEASON_ITEMS: [] };
new Function('window', grab(/window\.ROOM_ITEMS = \[[\s\S]*?\n\];/, 'ROOM_ITEMS'))(w);
new Function('window', grab(/window\.ROOM_CATS = \[[\s\S]*?\n\];/, 'ROOM_CATS'))(w);
new Function('window', grab(/window\.mwItemDef = function[\s\S]*?\n\};/, 'mwItemDef'))(w);
new Function('window', grab(/window\.mwDefFor = function[\s\S]*?\n\};/, 'mwDefFor'))(w);

// 1) 요가 매트는 **한 아이템의 두 상태**다 (대표 8-19: 돌리기 말고 접기/펴기, 기본은 펴진 것)
const mat = w.mwItemDef('mp_yogamat');
assert(mat, '요가 매트가 없다');
assert(Array.isArray(mat.dirs) && mat.dirs.length === 2, '요가 매트에 두 상태가 없다');
assert.deepStrictEqual(mat.flip, ['접기', '펴기'], "버튼 라벨이 '접기/펴기' 가 아니다");

// 2) 기본(d 없음 = 0) 은 **펴진 것**이어야 한다
const unfolded = w.mwDefFor({ id: 'mp_yogamat' });
assert(/mp_yogamat\.png/.test(unfolded.src), '기본 상태가 펴진 매트가 아니다');
assert.strictEqual(unfolded.flat, true, '펴진 매트는 밟고 지나가야 한다(flat)');
assert(unfolded.w > unfolded.h, '펴진 매트가 가로로 길지 않다');

// 3) 접으면 말아둔 매트 — 서 있으니 flat 이 아니어야 한다
//    (flat 이면 그림자가 안 생기고 캐릭터가 뚫고 지나간다)
const folded = w.mwDefFor({ id: 'mp_yogamat', d: 1 });
assert(/mp_yogamat_roll\.png/.test(folded.src), '접은 상태가 말아둔 매트가 아니다');
assert.strictEqual(folded.flat, false, '말아둔 매트가 flat 이라 밟고 지나간다');
assert(folded.h > folded.w, '말아둔 매트가 세로로 서 있지 않다');
assert.strictEqual(folded.sbw, 36, '말아둔 매트의 접지폭이 안 실렸다');

// 4) 옛 id 는 남아 있어야 한다 — 이미 방에 놓아둔 배치가 조용히 사라지면 안 된다
const legacy = w.mwItemDef('mp_yogamat_roll');
assert(legacy, '옛 id(mp_yogamat_roll)가 사라졌다 → 놓아둔 사람의 배치가 깨진다');
assert.strictEqual(legacy.legacy, true, '옛 id 가 legacy 로 표시되지 않았다');

// 5) 카탈로그(분류별 + 그 외)에 legacy 가 뜨면 안 된다 — 새로 사는 길은 하나여야 한다
const shown = [];
const seen = {};
for (const c of w.ROOM_CATS) {
  for (const r of w.ROOM_ITEMS.filter(r => r.cat === c.id && !r.legacy)) { shown.push(r.id); seen[r.id] = 1; }
}
for (const r of w.ROOM_ITEMS.filter(r => !seen[r.id] && !r.legacy)) shown.push(r.id);
assert(!shown.includes('mp_yogamat_roll'), '카탈로그에 옛 말아둔 매트가 아직 보인다');
assert(shown.includes('mp_yogamat'), '카탈로그에 요가 매트가 없다');

// 6) 카탈로그에 뜨는 것 중 id 중복이 없어야 한다
assert.strictEqual(new Set(shown).size, shown.length, '카탈로그에 중복 id 가 있다');

console.log(`room-items.test.mjs: 요가 매트 접기/펴기·옛 id 보존·카탈로그 ${shown.length}종 전부 통과 OK`);
