// 필드 히든 오브젝트 순수함수 테스트 — index.html에서 추출해 검증
// 실행: node tools/tests/field-aura.test.mjs
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

const w = {};
new Function('window', grab(/window\.FIELD_AURAS = \{[\s\S]*?\n\};/, 'FIELD_AURAS'))(w);
new Function('window', grab(/window\._FIELD_SPOTS = \{[\s\S]*?\n\};/, '_FIELD_SPOTS'))(w);
new Function('window', grab(/window\._MW_AUR_COLORS = \[[^\]]*\];/, '_MW_AUR_COLORS'))(w);
new Function('window', grab(/window\._mwPlateHit = function[\s\S]*?\n\};/, '_mwPlateHit'))(w);
new Function('window', grab(/window\._mwAurColor = function[\s\S]*?\n\};/, '_mwAurColor'))(w);
new Function('window', grab(/window\._PLATE_TAPS_1 = \d+;/, '_PLATE_TAPS_1'))(w);
new Function('window', grab(/window\._PLATE_TAPS_2 = \d+;/, '_PLATE_TAPS_2'))(w);

// 1) 합판 칸을 밟으면 'plate', 아니면 ''
assert.strictEqual(w._mwPlateHit('gym', 11, 7), 'plate');
assert.strictEqual(w._mwPlateHit('gym', 12, 7), 'plate');
assert.strictEqual(w._mwPlateHit('gym', 10, 7), '', '왼쪽 옆 칸이 걸림');
assert.strictEqual(w._mwPlateHit('gym', 13, 7), '', '오른쪽 옆 칸이 걸림');

// 2) ★물러서는 칸(tr 8)은 절대 트리거가 아니어야 한다 — 아니면 물러서자마자 재발동해 무한루프
assert.strictEqual(w._mwPlateHit('gym', 11, 8), '', '물러서는 칸이 트리거다 -> 무한루프');
assert.strictEqual(w._mwPlateHit('gym', 12, 8), '', '물러서는 칸이 트리거다 -> 무한루프');

// 3) 다른 필드엔 합판이 없다
assert.strictEqual(w._mwPlateHit('home', 11, 7), '');
assert.strictEqual(w._mwPlateHit('tennis', 11, 7), '');
assert.strictEqual(w._mwPlateHit('golf', 11, 7), '');

// 4) 트리거 칸과 물러설 칸이 둘 다 걸을 수 있는 칸이어야 한다 (_FIELDS.gym.map 과 대조)
const fm = grab(/gym: \{ name: '헬스장'[\s\S]*?\] \},/, '_FIELDS.gym');
const rows = fm.match(/"[.#]{16}"/g).map(s => s.slice(1, -1));
const sp = w._FIELD_SPOTS.gym.plate;
for (let tc = sp.tc[0]; tc <= sp.tc[1]; tc++) {
  assert.strictEqual(rows[7][tc], '.', `트리거 칸 tc${tc},tr7 이 벽이다`);
  assert.strictEqual(rows[8][tc], '.', `물러설 칸 tc${tc},tr8 이 벽이다`);
}

// 5) 색은 카탈로그 + 화이트리스트를 둘 다 통과해야 한다 (경로 주입 방지)
const key = Object.keys(w.FIELD_AURAS)[0];
assert.strictEqual(w._mwAurColor(key), 'blue');
assert.strictEqual(w._mwAurColor('2099-01'), '', '없는 시즌이 색을 돌려줌');
assert.strictEqual(w._mwAurColor(''), '');
assert.strictEqual(w._mwAurColor('../../etc/passwd'), '', '경로 주입이 통과함');
assert.strictEqual(w._mwAurColor(null), '');

// 6) 카탈로그의 모든 색이 화이트리스트 안에 있어야 한다 (에셋 없는 색 등록 방지)
for (const k in w.FIELD_AURAS) {
  assert(w._MW_AUR_COLORS.includes(w.FIELD_AURAS[k].color), `화이트리스트에 없는 색: ${k}`);
  assert(w.FIELD_AURAS[k].name && w.FIELD_AURAS[k].title, `이름/칭호 누락: ${k}`);
}

// 7) 탭 수 상수
assert(w._PLATE_TAPS_1 > 0 && w._PLATE_TAPS_2 > 0);

console.log('field-aura.test.mjs: 밟기 판정·물러설 칸·색 화이트리스트 전부 통과 OK');
