// 공동 머피룸 그림 목록·모바일 터치·액션 버튼·도화지 카펫 회귀 검증
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');

const artWatch = src.match(/window\._mwVisitArtWatch = function \(ownerUid\)[\s\S]*?\n\};/);
assert(artWatch, '손님용 그림 목록 실시간 감시가 없다');
assert(/onSnapshot\(doc\(db, 'users', ownerUid\)/.test(artWatch[0]),
  '방주 문서의 그림 목록을 실시간으로 구독하지 않는다');
assert(/_mwVisit\.artworks\s*=/.test(artWatch[0]) && /mwArtChip/.test(artWatch[0]),
  '새 그림을 손님 목록과 그림 칩에 즉시 반영하지 않는다');
assert(/_mwRoomApprovedEnter = function[\s\S]*?_mwVisitArtWatch\(ownerUid\)/.test(src),
  '승인되어 공동룸에 실제 입장할 때 그림 감시를 시작하지 않는다');

const big = src.match(/window\.mwArtBig = function \(id\)[\s\S]*?\n\};/);
assert(big, '그림 크게 보기 함수를 찾지 못했다');
assert(!/b\.onclick\s*=\s*function/.test(big[0]),
  '전파 차단 코드가 공유·가져오기·사기·값 매기기 onclick을 덮어쓴다');
assert(/addEventListener\('click',[\s\S]*?stopPropagation/.test(big[0]),
  '원래 버튼 액션을 보존한 채 배경 닫기만 막지 않는다');
// ★값 매기기(mwArtPrice)는 8-25 에 경매(mwAucOpen·mwAucBid)로 대체됐다 — 테스트가 옛 이름을 보고 있었다(9-03 수리)
assert(/mwArtShare/.test(big[0]) && /mwArtTake/.test(big[0]) && /mwAucOpen|mwAucBid/.test(big[0]),
  '공유·가져오기/사기·경매 액션 중 하나가 빠졌다');

const joy = src.match(/const onS = \(e\) => \{ if \(e\.target\.closest\([\s\S]*?e\.preventDefault\(\); \};/);
assert(joy, '방 조이스틱 시작 함수를 찾지 못했다');
assert(/\.mw-arttap/.test(joy[0]) && /\.mw-artrug/.test(joy[0]),
  '폰에서 액자·카펫 탭보다 조이스틱이 먼저 작동한다');

// ★입체 원근면(::before 마름모)은 8-26 에 **일부러 제거**됐다 — CSS 로 뭘 얹으면 구운 러그 위에
//   흰 액자가 한 겹 더 씌워 보인다(폴라로이드 두 겹 함정과 동일). 새 불변식으로 교체(9-03):
//   래퍼는 장식 없이 absolute 만, 그림은 자식 img 가 꽉 채우고 pixelated 여야 한다.
assert(/\.mw-artrug \{ position:absolute;[^}]*\}/.test(src) && !/\.mw-artrug \{[^}]*(background|border|box-shadow)/.test(src),
  '도화지 카펫 래퍼 CSS 에 장식이 얹혀 있다 — 러그가 액자처럼 보인다');
assert(/\.mw-artrug > img \{[^}]*inset:0[^}]*pixelated/.test(src.replace(/\n/g, ' ')) || /\.mw-artrug > img \{[\s\S]{0,200}?pixelated/.test(src),
  '카펫 그림이 래퍼를 꽉 채우는 pixelated img 가 아니다');
assert(/def\.art === 'rug'[\s\S]*?<div class="\$\{cls\}" data-idx/.test(src),
  '도화지 카펫을 입체 바닥 래퍼로 렌더하지 않는다');
assert(/closest\('\[data-idx\]'\)/.test(src) && /querySelector\('\[data-idx=/.test(src),
  '입체 카펫으로 바꾼 뒤 꾸미기 드래그 선택이 깨졌다');

assert(/id="mw-memory-btn"[\s\S]*?>오늘의 추억</.test(src),
  '공동룸 나가기 왼쪽에 오늘의 추억 버튼이 없다');
assert(/window\.mwMemoryOpen = function[\s\S]*?같이 찍은 사진[\s\S]*?같이 그린 그림/.test(src),
  '오늘의 추억이 사진/그림 두 탭으로 나뉘지 않았다');
assert(/_mwMemoryAddShot\(data, owner, ownerNick/.test(src),
  '같이 찍은 사진을 오늘의 추억에 저장하지 않는다');
assert(/document\.getElementById\(\\'mw-memory\\'\)\.remove\(\);window\.mwArtBig/.test(src),
  '추억 속 그림을 누르면 구매/가져오기/값 매기기 화면으로 바로 가지 않는다');
assert(/body\.mw-party #mw-art-chip \{ display:none/.test(src),
  '공동룸에서도 왼쪽 위 그림 숫자 칩이 중복 노출된다');

console.log('art-guest-mobile.test.mjs: 손님 목록·모바일 탭·그림 액션·입체 카펫 통과 OK');
