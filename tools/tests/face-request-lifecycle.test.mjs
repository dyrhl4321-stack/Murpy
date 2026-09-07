import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const src = readFileSync(new URL('../../index.html', import.meta.url), 'utf8');
const submit = src.match(/window\._faceSubmitUrls = async function[\s\S]*?\n\};/)[0];
async function run(previous, changeAccount = false) {
  const writes = [];
  const w = { currentUser: { uid: 'alice' }, _cachedProfile: { gender: '남성' },
    _charState: { faceTickets: 99 }, _faceHairPref: x => x, charRenderRoster() {} };
  const tx = {
    get: async ref => ({ exists: () => ref.includes('users') || !!previous,
      data: () => ref.includes('users') ? { gender: '여성', faceTickets: 2 } : previous }),
    update: (ref, data) => writes.push({ ref, data }), set: (ref, data) => writes.push({ ref, data })
  };
  new Function('window', 'db', 'doc', 'runTransaction', 'showToast', submit)(w, {},
    (_, ...parts) => parts.join('/'), async (_, fn) => {
      const r = await fn(tx); if (changeAccount) w.currentUser = { uid: 'bob' }; return r;
    }, () => {});
  const ok = await w._faceSubmitUrls(['own-photo'], 'forehead');
  return { w, writes, ok };
}
for (const status of ['pending', 'working']) {
  const r = await run({ status });
  assert.equal(r.ok, false); assert.equal(r.writes.length, 0, '중복 신청이 이용권을 차감한다');
}
for (const previous of [null, { status: 'done' }, { status: 'failed' }]) {
  const r = await run(previous);
  assert.equal(r.ok, true); assert.equal(r.writes.length, 2);
  assert.equal(r.writes[0].data.faceTickets, 1);
  assert.equal(r.writes[1].ref, 'faceRequests/alice');
  assert.equal(r.writes[1].data.gender, '여성', '오래된 남성 화면 캐시가 서버 여성 프로필을 덮었다');
  assert.equal(r.writes[1].data.photoUrl, 'own-photo');
}
const changed = await run(null, true);
assert.equal(changed.w._charState.faceTickets, 99, '이전 계정 요청 결과가 새 계정 상태에 반영됐다');

const descriptor = src.match(/async function _descriptorFrom\(input, ref\) \{[\s\S]*?\n\}/)[0];
let canvas, inferredSize;
const document = { createElement() { canvas = { width: 0, height: 0, getContext: () => ({ drawImage() {} }) }; return canvas; } };
const faceapi = { TinyFaceDetectorOptions: class {}, detectSingleFace(c) {
  inferredSize = [c.width, c.height]; return { withFaceLandmarks: () => ({ withFaceDescriptor: async () => ({ descriptor: [1, 2] }) }) };
} };
const infer = new Function('document', 'faceapi', descriptor + '; return _descriptorFrom;')(document, faceapi);
assert.deepEqual(await infer({ naturalWidth: 4032, naturalHeight: 3024 }, true), [1, 2]);
assert.deepEqual(inferredSize, [640, 480]);
assert.deepEqual([canvas.width, canvas.height], [1, 1], '추론 캔버스가 해제되지 않았다');
assert.equal(await infer({ width: 0, height: 0 }, true), null);
const auto = src.match(/window\._charAutoSave = function[\s\S]*?\n\};/)[0];
const draftWindow = { currentUser: { uid: 'alice' }, FACE_BODY_PREFIX: 'face:',
  _charDraft: { body: 'face:bob' }, _charState: { character: { body: 'human_f' } },
  _CHAR_BODIES: { 'face:bob': { owner: 'bob', dynamic: true } },
  _charBodyIsMine: () => false, _charSetSaveStatus: () => {},
  _mwRlSend() { throw new Error('Unauthorized avatar broadcast'); } };
new Function('window', auto)(draftWindow);
draftWindow._charAutoSave(true);
assert.equal(draftWindow._charState.character.body, 'human_f', '남의 얼굴을 로컬 내 캐릭터에 반영했다');
console.log('OK face-request-lifecycle: 중복 차감·성별·계정 전환·추론 메모리 회귀');
