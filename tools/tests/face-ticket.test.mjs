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

console.log('OK face-ticket 7항목');
