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

console.log('room-approval.test.mjs: 전원 사전 승인·4명 제한·방주 대기 UI·출석 UI 제외 통과 OK');
