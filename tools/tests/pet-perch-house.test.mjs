import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
const block = src.match(/window\._mwPetSpots = function \(p, want\) \{[\s\S]*?\n\};/);
assert(block, '_mwPetSpots를 찾지 못했다');

const defs = {
  pet_tower_cream: { id:'pet_tower_cream', petPerch:'cat', w:150, h:177 },
  pet_house_blue: { id:'pet_house_blue', petHouse:'dog', w:66, h:78 },
};
const w = {
  _myRoom:{ f:[] },
  _mwRoomShown(){ return this._myRoom; },
  _mwPetDef(id){ return { kind:String(id).startsWith('cat') ? 'cat' : 'dog' }; },
  mwDefFor(it){ return defs[it.id]; },
  _mwCritterWalkable(){ return true; },
};
new Function('window', block[0])(w);

w._myRoom = { f:[{ id:'pet_tower_cream', x:96, y:192 }] };
const tower = w._mwPetSpots({ id:'cat_milky' }, 'tower');
assert.equal(tower.length, 3, '캣타워가 꼭대기·중간·낮은 발판 3곳을 제공하지 않는다');
assert.deepEqual(new Set(tower.map(s => s.perch)), new Set(['top','mid','low']),
  '캣타워 높이별 자리 이름이 빠졌다');
assert.equal(new Set(tower.map(s => `${s.tc},${s.tr}`)).size, 3,
  '캣타워 세 자리가 같은 타일로 뭉쳤다');
assert(tower.every(s => s.up && s.perchZ > 0 && Number.isFinite(s.posDy)),
  '캣타워 높이·앞뒤 정렬 미세좌표가 없다');

w._myRoom = { f:[{ id:'pet_house_blue', x:240, y:310 }] };
const house = w._mwPetSpots({ id:'dog_small' }, 'house');
assert.equal(house.length, 1, '강아지 하우스 대기 자리를 찾지 못한다');
assert(house[0].house && house[0].perch === 'house', '개집 안 상태 표식이 없다');
assert.equal(w._mwPetSpots({ id:'cat_milky' }, 'house').length, 0,
  '고양이가 강아지 전용 하우스 모드를 사용한다');

assert(/\{ k: 'house', t: '하우스'[\s\S]*kind: 'dog'/.test(src),
  '강아지 행동 UI에 하우스 버튼이 없다');
assert(/mode === 'house'[\s\S]*?_mwPetNearest\(p, 'house'\)/.test(src),
  '하우스 모드가 실제 개집 이동으로 연결되지 않았다');
assert(/var bed = tower \|\| window\._mwPetNearest\(p, 'perch'\)/.test(src),
  '고양이 수면이 캣타워를 최우선으로 고르지 않는다');
assert(/var high = tower \|\|/.test(src), '고양이 휴식도 캣타워를 우선하지 않는다');
assert(/\{ k: 'bowl', t: '밥 주기'/.test(src) && /bowl:\s*'<svg/.test(src),
  '밥 주기 버튼이 전용 밥그릇 픽셀 아이콘을 쓰지 않는다');
assert(/house:\s*'<svg/.test(src), '하우스 픽셀 아이콘이 없다');

console.log('pet-perch-house.test.mjs: 캣타워 3단 휴식·수면 우선·강아지 하우스·픽셀 아이콘 통과 OK');
