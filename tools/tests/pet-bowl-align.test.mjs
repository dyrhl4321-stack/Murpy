// 밥그릇을 타일 사이에 놓아도 펫 얼굴 목표점이 실제 그릇 중심을 따라가는지 검증
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
const m = src.match(/window\._mwPetSpots = function \(p, want\) \{[\s\S]*?\n\};/);
assert(m, '_mwPetSpots를 찾지 못했다');

const bowl = { petBowl:true, w:30, h:21 };
const w = {
  _mwRoomShown: () => ({ f: [] }),
  _mwPetDef: () => ({ kind:'dog' }),
  mwDefFor: () => bowl,
  _mwCritterWalkable: () => true,
};
new Function('window', m[0])(w);

function topSpot(x, y) {
  w._mwRoomShown = () => ({ f:[{ id:'pet_bowl_blue', x, y }] });
  const spots = w._mwPetSpots({ id:'dog_1' }, 'bowl');
  const s = spots.find(v => v.dir === 0);
  assert(s, '그릇 위쪽 먹기 자리가 없다');
  return s;
}

for (const x of [81, 98, 121, 143]) {
  const s = topSpot(x, 330);
  const faceX = (s.tc + 0.5) + s.eatDx;
  const bowlX = (x + bowl.w / 2) / 48;
  assert(Math.abs(faceX - bowlX) < 1e-9,
    `그릇 x=${x}에서 얼굴이 중심과 어긋남: ${faceX} vs ${bowlX}`);
}

assert(/eatDx: \+\(p\.eatDx \|\| 0\)/.test(src), '방주가 먹기 미세좌표를 실시간 전송하지 않는다');
assert(/p\.eatDx = \+\(d\.eatDx \|\| 0\)/.test(src), '손님 화면에 먹기 미세좌표를 적용하지 않는다');

console.log('pet-bowl-align.test.mjs: 그릇 실제 배치 좌표·실시간 먹기 위치 동기화 통과 OK');
