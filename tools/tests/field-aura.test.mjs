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

// 8) 상태 그릇에 아우라 자리가 있어야 한다
const stLine = grab(/window\._seasonState = \{.*?ready: false \};/, '_seasonState');
assert(/auras:\s*\[\]/.test(stLine), '_seasonState 에 auras 배열이 없다');
assert(/auraOn:\s*''/.test(stLine), '_seasonState 에 auraOn 이 없다');

// 9) users 문서에서 fieldAuras / aura 를 읽어와야 한다
assert(/_seasonState\.auras = Array\.isArray\(d\.fieldAuras\)/.test(src),
  'users 문서의 fieldAuras 를 읽지 않는다');
assert(/_seasonState\.auraOn = \(typeof d\.aura === 'string'\)/.test(src),
  'users 문서의 aura 를 읽지 않는다');
console.log('  + 소유/장착 상태 로드 OK');

// 10) _mwAurOf — 내 것은 내 문서에서, 남의 것은 프레즌스에서
const w2 = { _MW_AUR_COLORS: ['blue'], currentUser: { uid: 'me' },
             _seasonState: { auraOn: '2026-08' }, _AUR_TEST: '' };
new Function('window', grab(/window\.FIELD_AURAS = \{[\s\S]*?\n\};/, 'FIELD_AURAS'))(w2);
new Function('window', grab(/window\._mwAurColor = function[\s\S]*?\n\};/, '_mwAurColor'))(w2);
new Function('window', grab(/window\._mwAurOf = function[\s\S]*?\n\};/, '_mwAurOf'))(w2);

assert.strictEqual(w2._mwAurOf('me', ''), 'blue', '내 장착값을 안 본다');
assert.strictEqual(w2._mwAurOf('other', '2026-08'), 'blue', '남의 프레즌스 값을 안 본다');
assert.strictEqual(w2._mwAurOf('other', ''), '', '안 켠 남에게 아우라가 뜬다');
assert.strictEqual(w2._mwAurOf('other', '2099-01'), '', '카탈로그에 없는 값이 통과함');
assert.strictEqual(w2._mwAurOf('other', '../fx/x'), '', '경로 주입이 통과함');
w2._seasonState.auraOn = '';
assert.strictEqual(w2._mwAurOf('me', ''), '', '껐는데도 내 아우라가 뜬다');
w2._AUR_TEST = 'nosuch';
assert.strictEqual(w2._mwAurOf('me', ''), '', '시험 스위치가 화이트리스트를 안 탄다');
w2._AUR_TEST = '1';
assert.strictEqual(w2._mwAurOf('me', ''), 'blue');
console.log('  + _mwAurOf 소유 판정 OK');

// 11) 합판 HTML — 세 상태 모두 **밑변이 같은 자리**여야 한다(발자국이 안 흔들린다)
const w3 = {};
new Function('window', grab(/window\._FIELD_SPOTS = \{[\s\S]*?\n\};/, '_FIELD_SPOTS'))(w3);
new Function('window', grab(/window\._PLATE_H = \{[^}]*\};/, '_PLATE_H'))(w3);
new Function('window', grab(/window\.mwPlateHtml = function[\s\S]*?\n\};/, 'mwPlateHtml'))(w3);
const bottomOf = (html) => {
  const m = html.match(/id="mw-plate"[\s\S]*?top:([\d.]+)%[\s\S]*?height:([\d.]+)%/);
  assert(m, 'mw-plate 의 top/height 를 못 읽음');
  return +m[1] + +m[2];
};
const b1 = bottomOf(w3.mwPlateHtml('closed'));
for (const st of ['ajar', 'open']) {
  assert(Math.abs(bottomOf(w3.mwPlateHtml(st)) - b1) < 0.01, st + ' 의 밑변이 어긋난다');
}
const widthOf = h => +h.match(/id="mw-plate"[\s\S]*?width:([\d.]+)%/)[1];
assert.strictEqual(widthOf(w3.mwPlateHtml('ajar')), widthOf(w3.mwPlateHtml('closed')));
assert(/gym_plate_floor/.test(w3.mwPlateHtml('closed')), '바닥 가리개가 없다');
assert(/pointer-events:auto/.test(w3.mwPlateHtml('closed')), '합판이 탭을 못 받는다');
assert(/gym_plate_closed/.test(w3.mwPlateHtml('nonsense')), '모르는 상태가 closed 로 안 떨어진다');
console.log('  + 합판 렌더 OK');

// 12) ★합판이 조이스틱 예외 목록에 있어야 탭이 통한다 (상자가 무반응이던 그 버그)
const joy = grab(/const onS = \(e\) => \{ if \(e\.target\.closest\([^)]*\)\) return;/, '조이스틱 제외 선택자');
assert(/\.mw-plate/.test(joy), '합판이 조이스틱 예외 목록에 없다 -> 탭해도 무반응');
// 대화창도 방 안에 있다 — 안 넣으면 다음 줄로 넘기려고 눌러도 조이스틱이 먼저 먹는다
assert(/#mw-fieldtalk/.test(joy), '대화창이 조이스틱 예외 목록에 없다 -> 눌러도 안 넘어간다');
console.log('  + 조이스틱 예외 OK');

// 13) ★고리 두 겹이 **같은 픽셀만큼** 올라가야 한다 — 각자 제 높이 기준이라 %가 다르다.
//     한쪽만 고치면 고리가 위아래로 갈라진다.
const cssF = grab(/\.mw-aur-f \{[^}]*\}/, '.mw-aur-f');
const cssB = grab(/\.mw-aur-b \{[^}]*\}/, '.mw-aur-b');
const liftF = +cssF.match(/translateY\(-([\d.]+)%\)/)[1];
const liftB = +cssB.match(/translateY\(-([\d.]+)%\)/)[1];
// 앞겹 45 / 뒤겹 75 → 같은 px 이 되려면 liftB = liftF * 45/75
assert(Math.abs(liftB - liftF * 45 / 75) < 0.01,
  `고리 두 겹의 올린 양이 다르다 (앞 ${liftF}% / 뒤 ${liftB}%) → 고리가 갈라진다`);

// 14) CSS 의 올린 양과 JS 의 _MW_AUR_LIFT 가 같아야 한다 — 어긋나면 이름표가 다시 고리를 덮는다
const liftJs = +grab(/window\._MW_AUR_LIFT = ([\d.]+);/, '_MW_AUR_LIFT').match(/= ([\d.]+);/)[1];
assert(Math.abs(liftJs - liftF / 100) < 0.001,
  `CSS 는 ${liftF}% 인데 JS _MW_AUR_LIFT 는 ${liftJs} 다 → 이름표 위치가 어긋난다`);

// 15) ★스쿼드 이름표는 margin 이 아니라 transform 이어야 한다.
//     .sq-char 는 translate(-50%,-100%) 라 **아래끝이 기준점**이다 — margin 으로 요소가
//     길어지면 캐릭터가 그만큼 위로 떠올라 벽을 뚫고 올라간 것처럼 보인다(8-19 실제 버그).
const sqNick = grab(/\.sq-char\.mw-aur-on \.sq-nick \{[^}]*\}/, '.sq-char.mw-aur-on .sq-nick');
assert(/transform:\s*translateY/.test(sqNick), '스쿼드 이름표가 transform 이 아니다');
assert(!/margin-top/.test(sqNick),
  '스쿼드 이름표에 margin-top 이 있다 → 캐릭터가 벽 위로 떠오른다');

// 16) '안 씀' 버튼이 아우라도 봐야 한다 (아우라만 켠 히든 캐릭터에서 안 눌리던 버그)
assert(/const auraOn = \(slot === 'acc'\) && !!\(\(window\._seasonState \|\| \{\}\)\.auraOn\)/.test(src),
  "'안 씀' 판정이 아우라를 안 본다");
assert(/const off = isMask \? !window\._charDraft\.mask : \(!window\._charDraft\[slot\] && !auraOn\)/.test(src),
  "'안 씀' 착용중 표시가 아우라를 안 본다");

// 17) '안 씀' 이 아우라까지 벗겨야 한다 (둘 다 켰을 때 하나만 벗던 버그)
assert(/slot === 'acc' && window\.mwAuraSet && \(window\._seasonState \|\| \{\}\)\.auraOn\) window\.mwAuraSet\(''\)/.test(src),
  "'안 씀' 이 아우라를 안 벗긴다");

// 18) 끄는 길은 한 벌이어야 한다 — mwAuraToggle 도 mwAuraSet 을 거친다
assert(/window\.mwAuraToggle = async function[\s\S]{0,400}?return window\.mwAuraSet\(/.test(src),
  'mwAuraToggle 이 mwAuraSet 을 안 쓴다 → 끄는 길이 두 벌이 된다');

console.log('  + 고리 위치·이름표·안 씀 버튼 OK');

// 19) ★아우라 칭호가 칭호 탭에 떠야 한다 (대표 8-19: "칭호탭에서 누락되어있음")
//     mwValidTitle 이 '' 을 돌려주면 목록(mwTitlePick)에서도 빠지고 머리 위에도 안 뜬다.
const w4 = { SEASON_ITEMS: [{ title: '공룡의 친구', kind: 'hidden' }, { title: '보통칭호' }] };
new Function('window', grab(/window\.FIELD_AURAS = \{[\s\S]*?\n\};/, 'FIELD_AURAS'))(w4);
new Function('window', grab(/window\._mwTitleDefs = function[\s\S]*?\n\};/, '_mwTitleDefs'))(w4);
new Function('window', grab(/window\.mwValidTitle = function[\s\S]*?\n\};/, 'mwValidTitle'))(w4);
new Function('window', grab(/window\.mwTitleColor = function[\s\S]*?\n\};/, 'mwTitleColor'))(w4);

for (const k in w4.FIELD_AURAS) {
  const t = w4.FIELD_AURAS[k].title;
  assert.strictEqual(w4.mwValidTitle(t), t, `아우라 칭호 '${t}' 가 칭호 탭에서 누락된다`);
  assert.strictEqual(w4.mwTitleColor(t), '#C9A8FF', `아우라 칭호 '${t}' 색이 히든 보라가 아니다`);
}
// 기존 칭호는 그대로여야 한다 (회귀)
assert.strictEqual(w4.mwValidTitle('공룡의 친구'), '공룡의 친구');
assert.strictEqual(w4.mwTitleColor('공룡의 친구'), '#C9A8FF');
assert.strictEqual(w4.mwTitleColor('보통칭호'), '#F5C24B');
// 없는 칭호는 여전히 막아야 한다 (주입 방지 — 보안규칙상 임의 문자열 쓰기가 가능하다)
assert.strictEqual(w4.mwValidTitle('아무거나'), '');
assert.strictEqual(w4.mwValidTitle('<b>주입</b>'), '');
console.log('  + 아우라 칭호 등록 OK');

// 20) 칭호 이름이 바뀌어도 **이미 받은 사람**이 새 칭호를 받아야 한다
//     (지급은 한 번뿐이라 mwPlateGrant 가 다시 안 돈다 — 보정이 없으면 영영 못 받는다)
assert(/window\.mwAuraTitleRepair = async function/.test(src), '칭호 보정 함수가 없다');
assert(/if \(window\.mwAuraTitleRepair\) window\.mwAuraTitleRepair\(\);/.test(src),
  '칭호 보정을 users 문서 로드 뒤에 안 부른다 → 이미 받은 사람은 영영 못 받는다');
// 안 가진 칭호를 주면 안 된다 (가진 아우라만 훑어야 한다)
const rep = grab(/window\.mwAuraTitleRepair = async function[\s\S]*?\n\};/, 'mwAuraTitleRepair');
assert(/for \(const k of st\.auras\)/.test(rep), '보정이 가진 아우라만 보지 않는다');
assert(/indexOf\(meta\.title\) < 0/.test(rep), '보정이 이미 있는 칭호를 다시 쓴다');
console.log('  + 칭호 보정 OK');
