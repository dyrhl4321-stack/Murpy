// 공동 머피룸 승인 흐름 회귀 검증
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');

function has(re, message) {
  assert(re.test(src), message);
}

has(/id="mw-party-members"[\s\S]*id="mw-party-waiters"[\s\S]*id="mw-party-bar2"/,
  '공동룸 순서가 현재 멤버 → 승인 대기 → 룸톡이 아니다');
has(/window\._mwRoomParticipant = function \(v\) \{ return window\._mwRoomAlive\(v\) && !v\.wait; \};/,
  '승인 대기자를 실제 참가자와 분리하지 않았다');
has(/wait:1, requestedAt:Date\.now\(\)/,
  '손님 최초 진입이 승인 요청으로 생성되지 않는다');
has(/mine && !mine\.wait && mine\.approvedAt/,
  '승인 뒤 손님을 공동룸으로 전환하는 조건이 없다');
has(/active\.length >= window\.MW_ROOM_CAP/,
  '승인 시 4명 정원 검사가 없다');
has(/\(!visiting && hasWaiting\)/,
  '대기자 1명부터 방주 공동룸 화면을 여는 조건이 없다');
has(/data-room-owner=/,
  '공동룸 밀어서 승인 트랙이 없다');
has(/if \(roomOwner\) window\.mwRoomApproveWait/,
  '스와이프 완료가 공동룸 승인 함수로 연결되지 않았다');
has(/window\._mwPendingVisit\s*=\s*\{ uid: uid[\s\S]*?window\.charSetField/,
  '승인 전 상대 방 데이터만 보관하고 내 머피월드에서 기다리지 않는다');
has(/window\._mwRoomApprovedEnter = function \(ownerUid\)[\s\S]*?_mwVisit = v[\s\S]*?charSetField\('home'\)/,
  '승인 순간에만 상대 머피월드로 전환하지 않는다');
has(/mine && !mine\.wait && mine\.approvedAt[\s\S]*?_mwRoomApprovedEnter\(ownerUid\)/,
  '방주의 승인 스냅샷이 손님의 실제 입장 전환으로 연결되지 않았다');
has(/if \(window\._mwPendingVisit && !window\._mwVisit\)[\s\S]*?document\.body\.classList\.remove\('mw-party'\)[\s\S]*?return;/,
  '승인 대기 중 상대 캐릭터/공용룸 UI를 내 방 위에 미리 그린다');
has(/const pendingOnly = !!\(window\._mwPendingVisit[\s\S]*?window\._mwRl\.waiting = pendingOnly[\s\S]*?const base =/,
  '첫 실시간 스냅샷보다 먼저 승인 대기 상태를 고정하지 않는다');
has(/if \(!pendingOnly\) \{[\s\S]*?mwJamWatch\(ownerUid\)[\s\S]*?_mwPetLiveWatch/,
  '승인 전부터 상대 방 낙서·채팅·펫을 구독해 내 방과 상대 방이 깜빡인다');
has(/window\._mwRoomApprovedEnter = function[\s\S]*?_mwVisit = v[\s\S]*?mwJamWatch[\s\S]*?_mwPetLiveWatch/,
  '승인된 순간 상대 방 실시간 구독을 시작하지 않는다');
has(/_mwPendingVisit \? window\._mwPendingVisit\.uid : u\.uid/,
  '내 방에서 기다리는 동안 승인 대상 방에 요청 presence를 연결하지 않는다');
has(/if \(window\._mwPendingVisit && !window\._mwVisit\)[\s\S]*?입장 대기를 취소했어요/,
  '승인 대기 취소를 내 방 닫기로 잘못 처리한다');
has(/window\.mwRoomWaitCardClose = function[\s\S]*?_mwWaitCardHidden = true[\s\S]*?승인 대기는 계속돼요/,
  '입장 요청은 유지하고 대기 팝업만 닫는 기능이 없다');
has(/!window\._mwRl\.waiting \|\| window\._mwWaitCardHidden/,
  '닫은 대기 팝업이 서버 갱신 때마다 다시 열린다');
has(/>창 닫기<\/button>[\s\S]*?>대기 취소<\/button>/,
  '대기 팝업에 창 닫기와 요청 취소가 분리돼 있지 않다');

// 출석 체크/상태 선택은 스쿼드 전용이다. 공동룸 멤버 CSS/행에는 관련 표식을 두지 않는다.
const roster = src.match(/window\._mwRTalkWho = function \(\) \{[\s\S]*?\n\};/);
assert(roster, '공동룸 멤버 목록 함수를 찾지 못했다');
assert(!/출석|미체크|체크|pm-state|status/.test(roster[0]),
  '공동룸 멤버 목록에 스쿼드 출석/상태 UI가 섞였다');
assert(/mwRoomKick/.test(roster[0]), '방주 강퇴 버튼이 없다');
assert(roster[0].indexOf("roster.innerHTML") < roster[0].indexOf("if (!b) return"),
  '룸톡 패널을 열기 전에는 공동룸 참가 목록을 그리지 않는다');
assert(/pm-char[\s\S]*pm-name[\s\S]*pm-actions[\s\S]*profile \+ kick/.test(roster[0]),
  '참가 행이 캐릭터 → 닉네임 → 우측 프로필/강퇴 3열 구조가 아니다');
assert(/window\.openUserProfile/.test(roster[0]),
  '방장과 손님이 쓸 수 있는 참가자 프로필 버튼이 없다');

const quick = src.match(/window\._mwPartyVVFit = function \(\)[\s\S]*?window\._mwBubblePin = false;/);
assert(quick, '공동룸 필드 키보드 처리 블록을 찾지 못했다');
assert(!/row\.style\.(position|transform|bottom)/.test(quick[0]),
  '키보드가 뜰 때 입력줄 자체를 필드 위로 이동한다');
assert(/el\.style\.height = vv\.height/.test(quick[0]),
  '스쿼드 필드처럼 고정 화면 상자를 visualViewport에 맞추지 않는다');
assert(/el\.style\.top = '0px'/.test(quick[0]) && !/el\.style\.top = \(vv\.offsetTop/.test(quick[0]),
  'visualViewport 팬 값을 공동룸 top에 더해 화면 전체를 위아래로 움직인다');
has(/onpointerdown="window\._mwKbStart&&window\._mwKbStart\(\)"/,
  '입력 포커스보다 먼저 문서 스크롤 잠금을 시작하지 않는다');
has(/enterkeyhint="send"[\s\S]*?event\.key===\\'Enter\\'[\s\S]*?event\.preventDefault\(\);window\.mwRoomSay\(\)/,
  '모바일 키보드의 전송 키로 한 번에 말하기가 되지 않는다');
has(/id="mw-quick-send" onpointerdown="event\.preventDefault\(\)"/,
  '키보드가 열린 채 말하기 버튼을 누르면 먼저 포커스가 풀린다');
has(/body\.mw-party\.mw-kb #mw-party-row \{ position:absolute;[\s\S]*?bottom:max\(8px, env\(safe-area-inset-bottom, 0px\)\)/,
  '키보드가 열렸을 때 한마디 입력줄을 키보드 바로 위에 고정하지 않는다');
has(/window\._mwKbScrollGuard = function[\s\S]*?window\.scrollTo\(0,0\)[\s\S]*?page\.scrollTop = 0/,
  '키보드 애니메이션 동안 브라우저의 문서 자동 스크롤을 되돌리지 않는다');

const say = src.match(/window\.mwRoomSay = function \(\)[\s\S]*?\n\};/);
assert(say, '공동룸 한마디 전송 함수를 찾지 못했다');
assert(!/inp\.blur\(\)/.test(say[0]),
  '한마디 전송 때 강제로 키보드를 닫아 화면을 튕긴다');
assert(/MW_ROOM_MSG_MS\s*=\s*9000/.test(src),
  '공동룸 필드 말풍선 시간이 스쿼드와 같은 9초가 아니다');
assert(/_mwRl\.msg\s*=\s*null[\s\S]*?_mwRlSend\(\)/.test(say[0]),
  '9초 뒤 필드 말풍선 데이터를 지워 다른 참가자 화면에서도 제거하지 않는다');
assert(/R\.push\(R\.ref\(R\.db, 'roomLive\/' \+ ow \+ '\/chat'\)/.test(say[0]),
  '필드 말풍선과 별개로 머피룸 톡 기록을 저장하지 않는다');
has(/body\.mw-party #mw-party-chat[\s\S]*?padding-bottom:calc\(78px \+ env\(safe-area-inset-bottom, 0px\)\)/,
  '머피룸 톡/참가자 하단 영역이 폰 하단 내비게이션 위로 올라오지 않았다');

console.log('room-approval.test.mjs: 승인·참가 3열 UI·말풍선/룸톡 분리·하단 여백·스쿼드형 키보드 고정 통과 OK');
