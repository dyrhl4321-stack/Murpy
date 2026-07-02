# 헬토리 근방단 한정판 캐릭터 — 설계

## Context
머피월드 오버월드 캐릭터(사람, `char/walk.png`)가 4방향 걷기로 동작 중. 대표(김현수)가
근방단(GBD CREW) 마스코트 **헬토리**(흰 토끼 헬창, "BORN TO WIN" 탱크탑 + GBD 백팩)를
스프라이트 시트로 제작 → **근방단 사람만 쓸 수 있는 한정판 캐릭터**로 배포하려 함.
목적: 근방단 소속감·한정판 재미(리텐션 훅). 매출 아님.

## 결정 사항
- **자격 판별 = 코드 배포.** 근방단에게 비밀 코드를 나눠주고, 앱에서 입력하면 해금.
  단일 HTML 앱이라 코드는 소스보기로 노출 가능(완벽 비밀 아님) — 친목 한정 드롭엔 충분.
  진짜 보안은 서버검증 필요(오버킬, 안 함).
- **전환/해금 위치 = 머피월드 꾸미기 패널의 '캐릭터' 탭.**
- **헬토리는 고정 캐릭터** — 헤어/상의/색/가면 커스터마이즈 없음(토끼라 사람 슬롯 안 맞음). YAGNI.

## 데이터 모델
- `users/{uid}.character.body`: `'human'`(기본) | `'heltori'`. 없으면 human으로 취급.
- 해금 상태 = 기존 `wardrobe[]` 배열에 `'heltori'` 포함 여부(기존 저장 로직 `_charPersistWardrobe` 재사용).
- 저장은 기존 `charSave`(=`_charPersistCharacter(_charDraft)`)에 body가 함께 실려 저장됨.
- `CHAR_DEFAULT`에 `body:'human'` 추가.

## 스프라이트 시스템
- 시트 규격: 3열[정지, 걸음A, 걸음B] × 3행[아래/위/옆(왼쪽 향)], 투명 PNG. `build_walk.py`로 생성.
- 캐릭터별 메타 `_CHAR_BODIES`:
  - `human`   : `char/walk.png`,    셀 135×224
  - `heltori` : `char/heltori.png`, 셀 174×224, `code:'GBD2026'`, `limited:true`
- 표시 높이 고정 `_CHAR_DISPLAY_H=88`, 표시 폭 = round(88 × cw/ch) → 사람≈53 / 헬토리≈68.
  (헬토리는 백팩으로 폭이 넓음 → 고정 bg-size로는 찌그러짐 → 캐릭터별 폭 계산 필요.)
- `_charApplySprite(body)`: 아바타 엘리먼트의 width/height, background-image, background-size,
  그리고 `_SPR.w/.h`(프레임 스텝 계산용)를 body에 맞게 세팅.
- `_charApplyPos`는 `_SPR.w/.h` 사용(방향=행, 프레임=열, 옆모습 왼쪽 향→오른쪽만 미러). 기존 유지.

## '캐릭터' 탭 UX
- `#charworld-slot-tabs`에 **캐릭터** 탭 추가(`charSlot('body')`).
- 그리드: **사람**(기본, 누구나) · **헬토리**(잠금 시 🔒 + "근방단 한정" 뱃지).
- 현재 body에 "착용중" 표시.
- 헬토리 탭:
  - 해금됨(wardrobe에 'heltori') → 탭하면 착용(body='heltori', 스프라이트/프리뷰 갱신).
  - 잠김 → **코드 입력 모달**(`#char-code-modal`) 오픈.
- 코드 모달 제출(`submitCharCode`): 입력값 trim·대문자 비교 == `CHAR_BODIES.heltori.code`.
  - 일치: wardrobe에 'heltori' 추가·저장, 토스트("헬토리 해금!"), 모달 닫기, 자동 착용, 탭 갱신.
  - 불일치: 토스트("코드가 올바르지 않아요").
- 앞모습 프리뷰(`#charworld-preview`): body='human'이면 기존 SVG 조립, body='heltori'면 헬토리 앞 정지(down c0) 프레임 표시.
- 헬토리 선택 시 헤어/상의/색/가면 슬롯은 의미 없음 → '캐릭터' 탭에서 안내만(별도 비활성 처리 생략, 선택해도 오버월드엔 영향 없음).

## 코드 관리
- `CHAR_CODES`(또는 `_CHAR_BODIES.heltori.code`) 상수 한 곳. 기본 `'GBD2026'`. 변경 쉬움.

## 배포
- `char/heltori.png`, `char/heltori_source.png`(마스터), `char/build_walk.py`(사람+헬토리 config).
- index.html의 heltori 참조에 `?v=1` 캐시버스트. walk.png는 v=4 유지(내용 동일).
- 작업 후 git push(기존 방침).

## 검증
- 로컬 서버(http.server)에서 머피월드 → 캐릭터 탭:
  - 헬토리 잠김 표시 → 잘못된 코드=거부 토스트 → `GBD2026`=해금·착용.
  - 헬토리로 방 걷기(4방향·정지/걸음·미러·바운스) 정상, 찌그러짐 없음.
  - 사람↔헬토리 전환, 저장 후 재진입 시 유지.
