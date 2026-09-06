// iOS 더블탭 확대 방어가 스쿼드 필드의 빠른 연속 탭 이동을 삼키지 않는지 검증한다.
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
const match = src.match(/\/\/ ═══ 아이폰 더블탭 확대 차단[\s\S]*?\n\}\)\(\);/);
assert(match, '아이폰 더블탭 확대 차단 코드를 찾지 못함');

let touchend = null;
const document = {
  documentElement: {},
  addEventListener(type, fn, options) {
    if (type === 'touchend') {
      touchend = fn;
      assert.deepStrictEqual(options, { passive: false, capture: true });
    }
  },
};
class MouseEvent {
  constructor(type, options) { this.type = type; Object.assign(this, options); }
}
new Function('document', 'MouseEvent', match[0])(document, MouseEvent);
assert(touchend, 'touchend 캡처 핸들러가 등록되지 않음');

const replayed = [];
const detail = { id: 'sq-detail', parentElement: document.documentElement };
const stage = {
  id: 'sq-room-stage',
  parentElement: detail,
  dispatchEvent(ev) { replayed.push(ev); },
  click() { throw new Error('필드에 좌표 없는 click()을 사용하면 안 됨'); },
};
const target = {
  parentElement: stage,
  closest(selector) { return selector.includes('#sq-room-stage') ? stage : null; },
};
let prevented = 0;
const event = (x, y) => ({
  target,
  cancelable: true,
  changedTouches: [{ clientX: x, clientY: y }],
  preventDefault() { prevented++; },
});

const realNow = Date.now;
try {
  const times = [1000, 1200];
  Date.now = () => times.shift();
  touchend(event(42, 77));       // 첫 탭은 브라우저의 정상 click을 기다린다.
  touchend(event(128, 311));     // 350ms 안 두 번째 탭은 확대만 막고 좌표를 재생한다.
} finally {
  Date.now = realNow;
}

assert.strictEqual(prevented, 1, '빠른 두 번째 탭의 확대를 막지 못함');
assert.strictEqual(replayed.length, 1, '빠른 두 번째 필드 탭이 재생되지 않음');
assert.strictEqual(replayed[0].type, 'click');
assert.strictEqual(replayed[0].clientX, 128, '재생 탭의 X 좌표가 유실됨');
assert.strictEqual(replayed[0].clientY, 311, '재생 탭의 Y 좌표가 유실됨');
assert.strictEqual(replayed[0].bubbles, true, '재생 click이 기존 stage.onclick까지 전달되지 않음');

console.log('squad-walk-touch: iOS 빠른 연속 탭 좌표 보존 통과');
