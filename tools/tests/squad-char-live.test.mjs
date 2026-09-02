// 스쿼드 명단·필드가 참가 당시 복장이 아니라 users/{uid} 최신 저장값을 실시간으로 쓰는지 검증
// 실행: node tools/tests/squad-char-live.test.mjs
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
const grab = (re, name) => {
  const m = src.match(re);
  assert(m, `index.html에서 ${name}를 찾지 못함`);
  return m[0];
};

// 실제 구독 생명주기: 나는 제외, 새 멤버만 추가, 빠진 멤버는 해제한다.
const w = {
  _sqCurId: 's1',
  currentUser: { uid: 'me' },
  _charLiveCache: {},
  _sqCharLiveWatches: {},
  _sqCharLivePaint() { this.paints = (this.paints || 0) + 1; },
  _sqCharLiveStop() {},
};
const auth = { currentUser: { uid: 'me' } };
const listeners = new Map();
const stopped = [];
const doc = (_db, ...parts) => parts.join('/');
const onSnapshot = (ref, next) => {
  listeners.set(ref, next);
  return () => { stopped.push(ref); listeners.delete(ref); };
};
new Function('window', 'auth', 'onSnapshot', 'doc', 'db',
  grab(/window\._sqCharLiveWatch = function[\s\S]*?\n\};/, '_sqCharLiveWatch'))
  (w, auth, onSnapshot, doc, {});

w._sqCharLiveWatch(['me', 'u1', 'u2']);
assert.deepStrictEqual([...listeners.keys()].sort(), ['users/u1', 'users/u2'], '본인까지 구독하거나 멤버 구독이 빠졌다');
listeners.get('users/u1')({ exists: () => true, data: () => ({ character: { top: 'new-top' } }) });
assert.deepStrictEqual(w._charLiveCache.u1.cfg, { top: 'new-top' }, 'users 최신 character가 캐시에 안 들어왔다');
assert.strictEqual(w.paints, 1, '캐릭터가 바뀌어도 화면 갱신을 예약하지 않는다');
// 같은 값은 다시 그리지 않는다(credits 같은 다른 users 필드 변경 방어).
listeners.get('users/u1')({ exists: () => true, data: () => ({ character: { top: 'new-top' }, credits: 99 }) });
assert.strictEqual(w.paints, 1, 'character가 같은데도 불필요하게 다시 그린다');
w._sqCharLiveWatch(['me', 'u1', 'u3']);
assert(stopped.includes('users/u2'), '빠진 멤버의 users 구독을 해제하지 않는다');
assert(listeners.has('users/u1') && listeners.has('users/u3'), '남은/새 멤버 구독 생명주기가 틀렸다');

// 연결 지점 회귀: 명단은 watcher를 시작하고, 닫을 때 해제하며, 필드는 live 값을 우선한다.
const detail = grab(/window\._sqRenderDetailInner = function[\s\S]*?\n\};/, '_sqRenderDetailInner');
assert(/_sqCharLiveWatch\(Object\.keys\(mem\)\.filter/.test(detail), '상세 명단이 users 실시간 구독을 시작하지 않는다');
assert(/status !== 'left'/.test(detail), '이미 나간 멤버까지 users 실시간 구독을 유지한다');
const close = grab(/window\._sqClose = function[\s\S]*?\n\};/, '_sqClose');
assert(/_sqCharLiveStop/.test(close), '상세를 닫을 때 users 구독을 해제하지 않는다');
// ★9-02 에 재적용 래퍼(_sqWrapRenderRemotes 안의 들여쓴 재대입)가 원본보다 **위에** 생겨서,
//   앵커 없는 정규식이 래퍼를 먼저 잡아 테스트가 깨져 있었다(9-03) → 줄 시작(^…m) 원본만 잡는다.
const remotes = grab(/^window\._sqRenderRemotes = function[\s\S]*?\n\};/m, '_sqRenderRemotes');
assert(/mwCharLive\(uid\) \|\| p\.character/.test(remotes), '필드가 users 최신 캐릭터보다 RTDB 과거 캐릭터를 우선한다');

console.log('squad-char-live.test.mjs: 명단·필드 최신 캐릭터 구독 및 해제 통과 OK');
