// 오픈월드 실시간 만남 + 얼굴 자동생성 상태/성별/머리 프리셋 회귀
// 실행: node tools/tests/openworld-face-autogen.test.mjs
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
const rules = JSON.parse(readFileSync(join(root, 'database.rules.json'), 'utf8'));
const main = readFileSync(join(root, 'functions-py', 'main.py'), 'utf8');
const gen = readFileSync(join(root, 'functions-py', 'facegen', 'gen.py'), 'utf8');

// 1) 같은 공개 필드의 사람만 구독하고, 내 uid 노드만 쓰며 끊기면 즉시 제거한다.
const players = rules.rules.plaza.players['$field'];
assert(players, 'plaza/players 공개 필드 presence 규칙이 없다');
assert(/auth != null/.test(players['.read']) && /park/.test(players['.read']) && /walk/.test(players['.read']) && /outgym/.test(players['.read']),
  '공개 필드 read 범위가 3개 필드로 제한되지 않았다');
assert(/auth\.uid == \$uid/.test(players['$uid']['.write']), '다른 사람 presence를 쓸 수 있다');
assert(/tc/.test(players['$uid']['.validate']) && /< 48/.test(players['$uid']['.validate']), '좌표 검증이 없다');
assert(/plaza\/players\/.*field/.test(src), '클라이언트가 필드별 players 노드에 붙지 않는다');
assert(/onDisconnect\(meRef\)\.remove\(\)/.test(src), '연결 종료 시 공개 필드 유령을 지우지 않는다');
assert(/_mwOpenPresenceSync\(key\)/.test(src), '필드 전환과 공개 presence가 연결되지 않았다');
assert(/_mwOpenTick/.test(src) && /_mwOpenRender/.test(src), '이동 송신 또는 상대 렌더가 없다');
assert(/plaza\/chat\/.*field/.test(src), '산책로/야외 헬스장도 park 채팅에 섞인다');

// 2) 나노바나나 Pro 고정값은 품질 규격이다. Flash나 저해상도로 내려가면 실패한다.
assert(/model='gemini-3-pro-image'/.test(gen), '가장 강한 나노바나나 Pro 모델이 아니다');
assert(/aspect='9:16'/.test(gen) && /size='2K'/.test(gen), '검증된 9:16·2K 설정이 바뀌었다');

// 3) 머리 프리셋은 자유문장이 아니라 4개 화이트리스트이며 신청 문서까지 전달된다.
for (const key of ['as_photo', 'forehead', 'bangs', 'tied']) {
  assert(src.includes("k: '" + key + "'"), '클라이언트 머리 프리셋 누락: ' + key);
  assert(main.includes("'" + key + "':"), '서버 머리 프리셋 누락: ' + key);
}
assert(/hairPref: hairPref/.test(src), '신청 문서에 hairPref가 저장되지 않는다');
assert(/HAIR_PREFS\.get/.test(main), '서버가 머리 프리셋을 화이트리스트로 제한하지 않는다');

// 4) 성별은 화면 캐시가 아니라 트랜잭션 users 문서와 서버 users 문서에서 두 번 확정한다.
assert(/gender: String\(ud\.gender \|\| prof\.gender/.test(src), '신청 성별이 서버 유저 문서를 우선하지 않는다');
assert(/db\.collection\('users'\)\.document\(uid\)\.get\(\)/.test(main), '생성 서버가 프로필 성별을 다시 읽지 않는다');
assert(/base_%s\.png/.test(main) && /gender == '여'/.test(main), '여성 베이스 분기가 없다');

// 5) 완료 알림의 첫 스냅샷을 놓쳐도 faceRequests 문서 자체를 구독해 회수한다.
assert(/onSnapshot\(doc\(db, 'faceRequests', uid\)/.test(src), 'faceRequests 실시간 상태 구독이 없다');
assert(/status === 'done'/.test(src) && /_charLoadMyFaceChars\(uid\)/.test(src), '완료 뒤 캐릭터 재로딩이 없다');
assert(/getDocFromServer\(doc\(db, 'users', uid\)\)/.test(src), '실패 환불 잔액을 서버에서 다시 맞추지 않는다');
assert(/window\._faceOwnerUid !== uid/.test(src) && /delete window\._CHAR_BODIES\[k\]/.test(src),
  '계정 전환 시 이전 사용자의 얼굴 캐시를 지우지 않는다');
assert(/if \(b\.dynamic\) return !!b\.owner && window\._charBodyIsMine\(b\)/.test(src),
  '남의 렌더용 동적 얼굴(owner:null)이 내 로스터 선택 카드로 노출된다');

// 6) 특정 Android PWA에서 필드만 검게 빈 경우 배경·캐릭터 겹·가구를 독립 복구한다.
assert(/window\._mwRepairStage = function/.test(src), '빈 머피월드 필드 자가복구가 없다');
assert(/!av\.querySelector\('\.cw-layer'\)/.test(src), '캐릭터 겹 유실을 복구하지 않는다');
assert(/repair=/.test(src) && /room\.style\.backgroundImage/.test(src), '깨진 배경 캐시를 우회하지 않는다');

assert(/id = 'murpy-grant'[\s\S]{0,800}?touch-action:pan-y/.test(src), '관리자 머피 지급창이 iOS에서 자체 세로 스크롤을 갖지 않는다');
assert(/box\.innerHTML = list\.map\(u =>/.test(src), '관리자 머피 지급 명단을 첫 80명에서 잘라 ㅇ 이후 사용자가 보이지 않는다');
assert(!/box\.innerHTML = list\.slice\(0, 80\)/.test(src), '관리자 머피 지급 명단에 80명 제한이 남아 있다');

console.log('OK openworld-face-autogen 31항목');
