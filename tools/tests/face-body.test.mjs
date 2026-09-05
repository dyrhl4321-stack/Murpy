// 얼굴 커마 동적 몸통 — index.html 에서 함수를 뽑아 가짜 window 에서 돌린다
// 실행: node tools/tests/face-body.test.mjs
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
new Function('window', grab(/window\._CHAR_BODIES = \{[\s\S]*?\n\};/, '_CHAR_BODIES'))(w);
new Function('window', grab(/window\.SQ_MG_EYES = \{[\s\S]*?\};/, 'SQ_MG_EYES'))(w);
// ★index.html 은 CRLF 다. 앞의 `\n\};` 는 `\r\n};` 안에서도 맞지만, 뒤를 보는 lookahead 는
//   `};` 다음에 오는 `\r` 때문에 `\nwindow` 로는 절대 안 맞는다(계획서 원문에서 고친 한 곳).
new Function('window', grab(/window\.FACE_BODY_PREFIX = [\s\S]*?\n\};(?=\r?\nwindow\._charRegisterFaceBody)/, '_charFaceBodyDef'))(w);
new Function('window', grab(/window\._charRegisterFaceBody = function[\s\S]*?\n\};/, '_charRegisterFaceBody'))(w);
new Function('window', grab(/window\._charBodyIsMine = function[\s\S]*?\n\};/, '_charBodyIsMine'))(w);
new Function('window', grab(/window\.CHAR_SKINS = \[[\s\S]*?\];/, 'CHAR_SKINS'))(w);
new Function('window', grab(/window\._charSkinSrc = function[\s\S]*?\n\};/, '_charSkinSrc'))(w);

const DOC = {
  name: '현수',
  sheetUrl: 'https://example.com/sheet.png',
  skinUrls: { t1: 'https://example.com/t1.png', t2: 'https://example.com/t2.png' },
  eyes: { y: 0.31, x: [0.33, 0.65] }
};

// 1) 키는 'face:' 접두사가 강제된다 — 기존 몸통 키와 절대 안 겹쳐야 한다
const r = w._charFaceBodyDef('abc123', DOC, 'UID1');
assert.strictEqual(w.FACE_BODY_PREFIX, 'face:', "접두사가 'face:' 가 아니다");
assert.strictEqual(r.key, 'face:abc123', '키에 접두사가 안 붙었다');
assert(!Object.keys(w._CHAR_BODIES).some(k => k.startsWith('face:')), '하드코딩 표에 이미 face: 키가 있다');

// 2) 기존 옷을 그대로 입어야 한다 — kin:'human' · wearable · fixedHair
assert.strictEqual(r.def.kin, 'human', "kin 이 'human' 이 아니면 기존 옷이 안 맞는다");
assert.strictEqual(r.def.wearable, true, 'wearable 이 아니면 옷을 못 입는다');
assert.strictEqual(r.def.fixedHair, true, 'fixedHair 가 아니면 머리가 두 겹이 된다');
assert.strictEqual(r.def.cw, 141); assert.strictEqual(r.def.ch, 224);

// 3) 주인 판정은 _charBodyIsMine 한 곳으로 간다
w.currentUser = { uid: 'UID1', email: 'a@b.c' };
assert.strictEqual(w._charBodyIsMine(r.def), true, '주인인데 내 것이 아니라고 한다');
w.currentUser = { uid: 'UID2', email: 'x@y.z' };
assert.strictEqual(w._charBodyIsMine(r.def), false, '남의 커마를 내 것이라고 한다');

// 4) 이름은 12자로 자른다(스펙 1~12자)
const long = w._charFaceBodyDef('c', { ...DOC, name: '가나다라마바사아자차카타파하' }, 'UID1');
assert.strictEqual(long.def.name.length, 12, '이름이 12자로 안 잘렸다');

// 5) 시트 URL 이 없으면 몸통을 만들지 않는다 — 빈 캐릭터가 뜨느니 안 만드는 게 낫다
assert.strictEqual(w._charFaceBodyDef('c', { name: 'x' }, 'UID1'), null, 'sheetUrl 없이 몸통이 만들어졌다');
assert.strictEqual(w._charFaceBodyDef('', DOC, 'UID1'), null, 'charId 없이 몸통이 만들어졌다');

// 6) 등록하면 표와 눈 좌표표에 같이 들어간다
const key = w._charRegisterFaceBody('abc123', DOC, 'UID1');
assert.strictEqual(key, 'face:abc123');
assert(w._CHAR_BODIES[key], '_CHAR_BODIES 에 안 들어갔다');
assert.deepStrictEqual(w.SQ_MG_EYES[key], DOC.eyes, '무궁화 하트눈 좌표가 안 들어갔다');

// 7) 눈 좌표가 없으면 표에 넣지 않는다 — 소비처가 human 좌표로 폴백한다(40644행)
w._charRegisterFaceBody('noeye', { name: 'n', sheetUrl: 'https://e/s.png' }, 'UID1');
assert.strictEqual(w.SQ_MG_EYES['face:noeye'], undefined, '눈 좌표 없는 몸통이 표를 오염시켰다');

// 8) 피부톤 — 동적 몸통은 경로 조립이 아니라 URL 표를 본다
assert.strictEqual(w._charSkinSrc('face:abc123', 't1'), DOC.skinUrls.t1, '구운 톤 URL 을 안 쓴다');
assert.strictEqual(w._charSkinSrc('face:abc123', 't3'), DOC.sheetUrl, 't3(원본)은 시트 그대로여야 한다');
assert.strictEqual(w._charSkinSrc('face:abc123', 't5'), DOC.sheetUrl, '없는 톤은 원본으로 폴백해야 한다');
// 기존 몸통은 하나도 안 바뀐다
assert.strictEqual(w._charSkinSrc('human', 't1'), 'char/skin/walk_t1.png?v=4', '기존 피부톤 경로가 바뀌었다');
assert.strictEqual(w._charSkinSrc('human', 't3'), w._CHAR_BODIES.human.src, '기존 t3 폴백이 깨졌다');

// 9) 착용 저장 시 남길 characterSheet — 남이 나를 그릴 때 이 URL 하나만 본다
new Function('window', grab(/window\._charSheetForBody = function[\s\S]*?\n\};/, '_charSheetForBody'))(w);
assert.strictEqual(w._charSheetForBody('face:abc123'), DOC.sheetUrl, '커마 시트 URL 을 안 남긴다');
assert.strictEqual(w._charSheetForBody('human'), null, '기본 몸통인데 시트 URL 을 남긴다');
assert.strictEqual(w._charSheetForBody('heltori'), null, '고정 캐릭터인데 시트 URL 을 남긴다');
assert.strictEqual(w._charSheetForBody(undefined), null, '몸통이 없는데 시트 URL 을 남긴다');

console.log('OK face-body 12항목');
