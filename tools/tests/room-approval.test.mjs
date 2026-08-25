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
