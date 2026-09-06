// 커마권 구매 계산 — 잔액 판정과 짝(머피 -1000 / 커마권 +1)이 맞는지 본다
// 실행: node tools/tests/face-ticket.test.mjs
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
function grab(re, name) { const m = src.match(re); assert(m, `index.html에서 ${name}를 찾지 못함`); return m[0]; }
const w = { _charState: {} };
// ★lookahead 에 \r? 가 필요하다 — index.html 은 CRLF 라 `};` 뒤가 \r\n 이다.
//   `\nwindow` 로 쓰면 영원히 안 맞는다 (Task 1 에서 실제로 걸렸다).
new Function('window', grab(/window\.FACE_TICKET_PRICE = [\s\S]*?\n\};(?=\r?\nwindow\.faceTickets)/, '_faceTicketBuyTx'))(w);
new Function('window', grab(/window\.faceTickets = function[\s\S]*?\n\};/, 'faceTickets'))(w);

// 1) 가격은 상수 한 곳에서만 온다 (정식 전환 때 여기만 고친다)
assert.strictEqual(w.FACE_TICKET_PRICE, 1000, '커마권 가격 상수가 1000머피가 아니다');

// 2) 잔액이 되면 정확히 -1000 / +1
const ok = w._faceTicketBuyTx(1000, 0);
assert.strictEqual(ok.ok, true, '딱 맞는 잔액인데 구매가 막혔다');
assert.strictEqual(ok.credits, 0, '머피가 정확히 안 빠졌다');
assert.strictEqual(ok.faceTickets, 1, '커마권이 정확히 한 장 안 늘었다');

// 3) 잔액이 모자라면 아무것도 안 바뀐다
const no = w._faceTicketBuyTx(999, 3);
assert.strictEqual(no.ok, false, '잔액 부족인데 통과했다');
assert.strictEqual(no.reason, 'insufficient');

// 4) 이미 가진 장수 위에 쌓인다 (여러 개 보유 = 스펙)
const more = w._faceTicketBuyTx(2500, 2);
assert.strictEqual(more.credits, 1500); assert.strictEqual(more.faceTickets, 3);

// 5) 더러운 값(없음·문자열·음수)이 와도 0 으로 본다 — 규칙이 정수만 받는다
assert.strictEqual(w._faceTicketBuyTx(1000, undefined).faceTickets, 1);
assert.strictEqual(w._faceTicketBuyTx(1000, '5').faceTickets, 1, '문자열 보유량을 그대로 더했다');
assert.strictEqual(w._faceTicketBuyTx(1000, -4).faceTickets, 1, '음수 보유량을 그대로 더했다');

// 6) 보유 조회도 더러운 값에 안 넘어간다
w._charState.faceTickets = '3'; assert.strictEqual(w.faceTickets(), 0, '문자열 보유량을 그대로 보여준다');
w._charState.faceTickets = -1; assert.strictEqual(w.faceTickets(), 0);
w._charState.faceTickets = 2;  assert.strictEqual(w.faceTickets(), 2);

// 7) 규칙이 짝을 강제하는지 (규칙은 여기서 실행할 수 없으니 문자열로 본다)
const rules = readFileSync(join(root, 'firestore.rules'), 'utf8');
assert(/faceTickets/.test(rules), 'firestore.rules 에 커마권 잠금이 없다 — 무한 발급된다');
assert(/faceChars/.test(rules), 'firestore.rules 에 faceChars 규칙이 없다');
// 규칙의 하드코딩 가격이 JS 상수와 같아야 한다 (규칙은 JS 를 못 읽는다)
assert(new RegExp('resource\.data\.credits - ' + w.FACE_TICKET_PRICE).test(rules),
  '규칙의 차감액이 FACE_TICKET_PRICE 와 다르다 — 구매가 규칙에 막힌다');

// 8) 관리자 입력 → Firestore 문서 조립
new Function('window', grab(/window\._faceCharDocFrom = function[\s\S]*?\n\};/, '_faceCharDocFrom'))(w);
const good = w._faceCharDocFrom({ name: '현수', sheetUrl: 'https://murpy.app/char/faces/hyunsu.png', skinPrefix: 'https://murpy.app/char/skin/face_hyunsu' });
assert.strictEqual(good.ok, true, '정상 입력이 막혔다: ' + good.error);
assert.strictEqual(good.doc.name, '현수');
assert.strictEqual(good.doc.sheetUrl, 'https://murpy.app/char/faces/hyunsu.png');
// 톤 5종이 규칙(t3 는 원본이라 없다)대로 조립된다
assert.deepStrictEqual(Object.keys(good.doc.skinUrls).sort(), ['t1','t2','t4','t5','t6']);
assert.strictEqual(good.doc.skinUrls.t4, 'https://murpy.app/char/skin/face_hyunsu_t4.png');
assert.strictEqual(good.doc.retryCount, 0, '재생성 횟수가 0 으로 안 시작한다');
// 이름은 1~12자
assert.strictEqual(w._faceCharDocFrom({ name: '', sheetUrl: 'https://a/b.png' }).ok, false, '빈 이름이 통과했다');
assert.strictEqual(w._faceCharDocFrom({ name: '가'.repeat(13), sheetUrl: 'https://a/b.png' }).ok, false, '13자 이름이 통과했다');
// 시트 URL 은 필수 + http(s) 만
assert.strictEqual(w._faceCharDocFrom({ name: 'x' }).ok, false, '시트 없이 통과했다');
assert.strictEqual(w._faceCharDocFrom({ name: 'x', sheetUrl: 'javascript:alert(1)' }).ok, false, 'javascript: URL 이 통과했다');
// 톤 접두사가 없으면 skinUrls 는 null (피부톤 탭이 "바꿀 수 없어요"로 떨어진다)
assert.strictEqual(w._faceCharDocFrom({ name: 'x', sheetUrl: 'https://a/b.png' }).doc.skinUrls, null);
// 이름 금칙어는 **새로 만들지 않았다.** 이 저장소엔 `_textBlocked` 가 없고, 광장 외치기·닉네임이
// 같이 쓰는 FILTER_WORDS(연락처 필터) 기반 `window._hasContact` 가 있어 그걸 그대로 태운다.
// 여기선 index.html 의 실제 목록을 읽어 같은 판정을 붙여 준다.
const fw = src.match(/const FILTER_WORDS = (\[[\s\S]*?\]);/);
assert(fw, 'index.html 에서 FILTER_WORDS 를 찾지 못함');
w.FILTER_WORDS = JSON.parse(fw[1]);
w._hasContact = (t) => w.FILTER_WORDS.some(x => String(t || '').toLowerCase().includes(String(x).toLowerCase()));
assert.strictEqual(w._faceCharDocFrom({ name: '카톡열어', sheetUrl: 'https://a/b.png' }).ok, false, '금칙어 이름이 통과했다');
assert.strictEqual(w._faceCharDocFrom({ name: '현수', sheetUrl: 'https://a/b.png' }).ok, true, '멀쩡한 이름까지 막혔다');

// 9) 진입 버튼이 상황마다 뭘 말해야 하는가 (스펙 4장 흐름)
new Function('window', grab(/window\._faceEntryState = function[\s\S]*?\n\};/, '_faceEntryState'))(w);
assert.strictEqual(w._faceEntryState(0, false, true, true).mode, 'buy', '티켓 0장인데 상점으로 안 보낸다');
assert.strictEqual(w._faceEntryState(1, false, false, true).mode, 'verify', '인증 없이 생성으로 보낸다');
assert.strictEqual(w._faceEntryState(1, false, false, false).mode, 'photo', '사진 없이 인증으로 보낸다');
assert.strictEqual(w._faceEntryState(1, false, true, true).mode, 'create', '조건이 다 됐는데 생성으로 안 간다');
assert.strictEqual(w._faceEntryState(0, true, true, true).mode, 'buy', '이미 있어도 더 만들려면 티켓이 필요하다');
// 문구에 이모지가 없어야 한다 (머피 UI 규칙)
for (const m of [[0,false,true,true],[1,false,false,true],[1,false,false,false],[1,false,true,true]]) {
  const s = w._faceEntryState.apply(null, m);
  assert(!/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u.test(s.label + s.desc), '진입 문구에 이모지가 있다: ' + s.label);
}

console.log('OK face-ticket 27항목');
