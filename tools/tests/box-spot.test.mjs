// 히든 깜짝 상자 구석 배치 테스트 — index.html에서 mwBoxSpot/mwBoxFootprint 추출해 검증
// 실행: node tools/tests/box-spot.test.mjs
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');

const w = {};
for (const re of [
  /window\._MW_BOX_W = \d+;/,
  /window\.mwBoxSpots = \[[\s\S]*?\];/,
  /window\.mwBoxFootprint = function[\s\S]*?\n};/,
  /window\.mwBoxSpot = function[\s\S]*?\n};/,
]) {
  const m = src.match(re);
  assert(m, 'index.html에서 찾지 못함: ' + re);
  new Function('window', m[0])(w);
}
const { mwBoxSpot: spot, mwBoxFootprint: foot, mwBoxSpots: spots, _MW_BOX_W: W } = w;

// 방 걷기 가능 영역: _FIELDS.home.map 기준 행 3~14, 열 1~14 (48px 타일, 16×16)
const walkable = (t) => { const r = Math.floor(t / 16), c = t % 16; return r >= 3 && r <= 14 && c >= 1 && c <= 14; };

// 1) 네 후보 모두 상자 전체가 방 안(768) + 발자국이 걷기영역 안
for (const s of spots) {
  assert(s.x >= 0 && s.x + W <= 768 && s.y >= 0 && s.y + W <= 768, `상자가 방 밖으로 나감: ${JSON.stringify(s)}`);
  for (const t of foot(s.x, s.y)) assert(walkable(t), `발자국이 벽 타일을 침범: ${JSON.stringify(s)} tile=${t}`);
}

// 2) 후보끼리 발자국이 겹치지 않음(= 진짜 서로 다른 구석)
for (let i = 0; i < spots.length; i++) for (let j = i + 1; j < spots.length; j++) {
  const a = new Set(foot(spots[i].x, spots[i].y));
  assert(!foot(spots[j].x, spots[j].y).some(t => a.has(t)), `후보 ${i}/${j} 발자국이 겹침`);
}

// 3) 시작 지점(중앙 tc7,tr9)을 막지 않음 — 막으면 입장하자마자 갇힌다
const startTile = 9 * 16 + 7;
for (const s of spots) assert(!foot(s.x, s.y).includes(startTile), '시작 칸을 막는 후보가 있음');

// 4) 결정적: 같은 uid → 항상 같은 자리
const empty = new Set();
assert.deepStrictEqual(spot(empty, 'abc123'), spot(empty, 'abc123'), '같은 uid인데 자리가 바뀜');

// 5) 사람마다 갈림: 여러 uid를 넣으면 네 구석이 모두 쓰임
const used = new Set(Array.from({ length: 60 }, (_, i) => JSON.stringify(spot(empty, 'user' + i))));
assert.strictEqual(used.size, spots.length, `구석이 고르게 안 쓰임(${used.size}/${spots.length})`);

// 6) 가구가 있는 구석은 피한다 — 첫 후보를 통째로 막으면 다른 구석으로 감
for (let i = 0; i < spots.length; i++) {
  const blocked = new Set(foot(spots[i].x, spots[i].y));
  for (const uid of ['a', 'bb', 'ccc', 'dddd', 'eeeee', 'ffffff']) {
    const got = spot(blocked, uid);
    assert(got.x !== spots[i].x || got.y !== spots[i].y, `가구로 막힌 구석을 그대로 고름(uid=${uid})`);
  }
}

// 7) 네 구석이 전부 막혀도 크래시 없이 하나는 고른다
const all = new Set(spots.flatMap(s => foot(s.x, s.y)));
assert(spot(all, 'zzz'), '전부 막힌 경우 자리를 못 고름');

console.log('ok — 상자 구석 배치 7케이스 통과');
