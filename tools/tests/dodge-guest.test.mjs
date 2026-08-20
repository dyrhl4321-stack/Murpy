// 덤벨 피하기 미가입자 바이럴 — 순수함수 테스트 (index.html 에서 추출해 검증)
// 실행: node tools/tests/dodge-guest.test.mjs
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
new Function('window', grab(/window\.DODGE = \{[\s\S]*?\n\};/, 'DODGE'))(w);
new Function('window', grab(/window\.dodgeParseLink = function[\s\S]*?\n\};/, 'dodgeParseLink'))(w);
new Function('window', grab(/window\.dodgeMakeLink = function[\s\S]*?\n\};/, 'dodgeMakeLink'))(w);

// 1) 정상 링크
let r = w.dodgeParseLink('?game=dodge&n=%ED%8C%A8%EC%88%98%ED%98%84&s=320');
assert.strictEqual(r.on, true, '게임 링크를 못 알아본다');
assert.strictEqual(r.nick, '패수현');
assert.strictEqual(r.score, 320);

// 2) game 파라미터가 없거나 다른 값이면 꺼진다 (방 초대 ?room= 을 삼키면 안 된다)
assert.strictEqual(w.dodgeParseLink('').on, false);
assert.strictEqual(w.dodgeParseLink('?room=abc123').on, false, '방 초대 링크를 게임이 가로챈다');
assert.strictEqual(w.dodgeParseLink('?sq=xyz').on, false, '스쿼드 초대 링크를 게임이 가로챈다');
assert.strictEqual(w.dodgeParseLink('?game=tennis').on, false, '모르는 게임을 연다');

// 3) ★점수 조작 방어 — MAX_SCORE 로 자른다
assert.strictEqual(w.dodgeParseLink('?game=dodge&s=999999').score, w.DODGE.MAX_SCORE);
assert.strictEqual(w.dodgeParseLink('?game=dodge&s=-5').score, 0);
assert.strictEqual(w.dodgeParseLink('?game=dodge&s=abc').score, 0);
assert.strictEqual(w.dodgeParseLink('?game=dodge&s=3.7').score, 3);
assert.strictEqual(w.dodgeParseLink('?game=dodge').score, 0, '점수가 없으면 0');

// 4) 닉네임 — 12자로 자르고, 없으면 빈 문자열
assert.strictEqual(w.dodgeParseLink('?game=dodge&n=' + encodeURIComponent('가'.repeat(30))).nick.length, 12);
assert.strictEqual(w.dodgeParseLink('?game=dodge').nick, '');
// 태그 문자는 그대로 돌려준다 — 지우는 게 아니라 **넣을 때 textContent 로** 막는다.
// 여기서 지우면 '<' 를 쓴 진짜 닉네임이 망가진다.
assert.strictEqual(w.dodgeParseLink('?game=dodge&n=' + encodeURIComponent('<b>')).nick, '<b>');

// 5) 깨진 URL 인코딩에도 안 터진다
assert.doesNotThrow(() => w.dodgeParseLink('?game=dodge&n=%E0%A4%A'));

// 6) 링크 만들기 — 항상 murpy.app, 닉네임은 인코딩
const link = w.dodgeMakeLink('패 수&현', 320);
assert(link.startsWith('https://murpy.app/?game=dodge'), '정식 주소가 아니다: ' + link);
assert(link.includes('s=320'));
assert(!link.includes('패 수&현'), '닉네임이 인코딩되지 않았다 — & 가 파라미터를 쪼갠다');
assert.strictEqual(w.dodgeParseLink(link.slice(link.indexOf('?'))).nick, '패 수&현', '만든 링크를 다시 못 읽는다');

// 7) 닉네임이 없어도 링크는 만들어진다
const bare = w.dodgeMakeLink('', 0);
assert(bare.startsWith('https://murpy.app/?game=dodge'));

console.log('dodge-guest.test.mjs: 링크 파싱·만들기 통과 OK');

// 8) 게스트 점수 보관 — Firestore 의 games.dodge 와 **같은 모양**이어야 옮길 때 변환이 없다
new Function('window', grab(/window\.dodgeGuestMerge = function[\s\S]*?\n\};/, 'dodgeGuestMerge'))(w);

let g = w.dodgeGuestMerge(null, { s: 120, t: 30, lv: 'mid', at: 1000 }, 20);
assert.strictEqual(g.best, 120, '첫 기록이 최고점이 안 된다');
assert.strictEqual(g.plays, 1);
assert.strictEqual(g.recent.length, 1);

// 더 낮은 점수를 내도 최고점은 안 내려간다
g = w.dodgeGuestMerge(g, { s: 50, t: 12, lv: 'mid', at: 2000 }, 20);
assert.strictEqual(g.best, 120, '낮은 점수가 최고점을 덮었다');
assert.strictEqual(g.plays, 2);

// 최신 판이 **앞**에 온다
assert.strictEqual(g.recent[0].s, 50, '최신 판이 맨 앞이 아니다');

// 더 높은 점수는 갱신된다
g = w.dodgeGuestMerge(g, { s: 300, t: 60, lv: 'hard', at: 3000 }, 20);
assert.strictEqual(g.best, 300);

// max 를 넘으면 오래된 것부터 버린다
let many = null;
for (let i = 0; i < 30; i++) many = w.dodgeGuestMerge(many, { s: i, t: i, lv: 'mid', at: i }, 20);
assert.strictEqual(many.recent.length, 20, '보관 개수를 안 자른다');
assert.strictEqual(many.recent[0].s, 29, '최신이 맨 앞이 아니다');

// 망가진 보관분이 들어와도 안 터진다 (localStorage 는 사람이 고칠 수 있다)
assert.doesNotThrow(() => w.dodgeGuestMerge({ best: 'x', recent: 'nope' }, { s: 10, t: 1, lv: 'mid', at: 1 }, 20));
const fixed = w.dodgeGuestMerge({ best: 'x', recent: 'nope' }, { s: 10, t: 1, lv: 'mid', at: 1 }, 20);
assert.strictEqual(fixed.best, 10, '망가진 best 를 복구 못 한다');
assert(Array.isArray(fixed.recent), '망가진 recent 를 배열로 못 되돌린다');
console.log('  + 게스트 점수 보관 OK');

// 9) 계정이 없어도 점수를 버리지 않는다
const save = grab(/window\.dodgeSave = async function[\s\S]*?\n\};/, 'dodgeSave');
assert(!/if \(!user\) return;/.test(save),
  'dodgeSave 가 계정 없으면 그냥 버린다 → 비회원 최고점이 사라진다');
assert(/dodgeGuestSave\(/.test(save) && /dodgeGuestMerge\(/.test(save),
  'dodgeSave 가 계정 없을 때 폰에 보관하지 않는다');
// 보관 뒤에는 반드시 return — 그 아래 Firestore 코드로 흘러가면 터진다
assert(/dodgeGuestSave\([\s\S]{0,200}?return;/.test(save),
  '게스트 보관 뒤 return 이 없다 → Firestore 코드로 흘러간다');
console.log('  + dodgeSave 게스트 경로 OK');

// 10) 게스트 닉네임 저장이 끝난 뒤 **어디로 갈지**를 부르는 쪽이 정할 수 있어야 한다
//     (스쿼드에서 왔으면 스쿼드로, 게임에서 왔으면 게임으로)
const gogo = grab(/window\._guestGoSquad = function[\s\S]*?\n\};/, '_guestGoSquad');
assert(/_guestAfter/.test(gogo), '_guestGoSquad 에 콜백 훅이 없다 → 게임에서 와도 스쿼드로 간다');
assert(/window\._guestAfter = null/.test(gogo), '콜백을 비우지 않는다 → 다음 번에 또 불린다');
// 콜백이 없으면 지금 동작 그대로여야 한다(스쿼드 흐름 무영향)
assert(/_sqInviteSid/.test(gogo), '스쿼드 흐름이 사라졌다');

// 11) 승격 함수 — 옮기고 나면 폰 보관분을 비운다
const pro = grab(/window\.dodgeGuestPromote = async function[\s\S]*?\n\};/, 'dodgeGuestPromote');
assert(/dodgeGuestClear\(\)/.test(pro), '옮긴 뒤 폰 보관분을 안 비운다 → 두 벌이 남는다');
console.log('  + 점수 승격·콜백 훅 OK');
