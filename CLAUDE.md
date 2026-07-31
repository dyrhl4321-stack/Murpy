# MURPY 프로젝트

> **이 파일은 다른 문서들의 요약본이다.** 상세는 항상 `docs/` 아래 설계 문서가 소스이고,
> 여기에는 "어디를 봐야 하는가"와 "지금 어디까지 왔는가"만 적는다.
> 충돌하면 **설계 문서 > CLAUDE.md** 순으로 신뢰할 것.
> 전략 확정본은 `murpyworld-master-brief.md`(2026-07-12) 우선.

---

## 0. ★문서 인덱스 (먼저 여기를 본다)

작업 전에 해당 영역의 설계 문서를 읽는다. **CLAUDE.md만 믿고 "미구현"이라고 판단하지 말 것**
— 이 파일이 낡아서 이미 만든 기능을 없다고 오판한 사고가 반복됐다.

| 영역 | 문서 |
|---|---|
| **전략 확정본** | `murpyworld-master-brief.md` (7-12) |
| 사업계획 마스터 | `docs/사업계획/MASTER_INDEX.md` · `master/01_TIPS` `02_VC` `03_IR` · `MURPY_사업_설명서_최종본.md` |
| 수익화 | `MONETIZATION.md` |
| **특허 (비공개)** | `C:\Users\allys\Murpy_private\patent\` — 1차시안 + 포트폴리오 검토. **공개 저장소 금지** |
| 범프/하이파이브 타당성 | `docs/MURPY_SQUAD_HIGH_FIVE_FEASIBILITY.md` |
| 히든 캐릭터 | `docs/superpowers/specs/2026-07-27-hidden-characters-design.md` + `plans/2026-07-27-*` |
| 월간 한정 오브젝트 | `docs/superpowers/specs+plans/2026-07-21-monthly-limited-room-objects*` |
| 방 리스케일·충돌 | `docs/superpowers/specs/2026-07-22-room-rescale-and-collision-design.md` |
| 스쿼드 P0 | `docs/superpowers/specs/2026-07-19-squad-p0-design.md` + `plans/2026-07-20-squad-p0.md` |
| 체크인 탭 개편 | `docs/superpowers/specs/2026-07-19-checkin-tab-ux-redesign-design.md` |
| 센터 뱃지·도감 | `docs/superpowers/specs/2026-07-15-center-badge-dogam-design.md` |
| 에셋 스튜디오 | `docs/superpowers/specs/2026-07-10-asset-studio-triage-and-pixel-tools-design.md` · `tools/asset-studio/README.md` |
| 추출 파이프라인 | `docs/murpyworld-extraction-pipeline-reverse-engineered.md` · `tools/character-customizer/V2_DIFF_PIPELINE.md` |
| **생성 AI 자체학습(B안)** | `docs/murpyworld-ai-generation-roadmap.md` — LoRA+ControlNet, 비용 실측, 착수 순서 |
| 캐릭터 스프라이트 규격 | `docs/character-sprite-spec.md` · `docs/캐릭터-아이템-작업가이드.md` |
| AI 이미지 프롬프트 | `docs/prompts/README.md` · `01-character-sprite.md` |
| 로드맵 | `docs/murpyworld-roadmap.md` |

---

## 1. 서비스 정보

| 항목 | 내용 |
|------|------|
| 서비스명 | Murpy (머피) · 슬로건 Move Together |
| 목적 | 운동 커뮤니티 운영 플랫폼 + 픽셀 캐릭터(머피월드) |
| 운영자 | 김현수 (GBD CREW 근손실방지단 247명 운영, 퍼스널 트레이너) |
| 배포 | https://dyrhl4321-stack.github.io/Murpy |
| GitHub | https://github.com/dyrhl4321-stack/Murpy (main 직접 배포) |
| Firebase | `murpyprototype` · API Key `AIzaSyBvMB4T-ApzHDsfmBx4f5HpPmgkqlcZ7VQ` |
| RTDB | `murpyprototype-default-rtdb.asia-southeast1` (스쿼드 실시간 위치·범프 계측) |
| 관리자 | `dyrhl4321@gmail.com` |

## 2. 핵심 철학

- 소개팅앱이 아닌 **운동 커뮤니티 운영 플랫폼**. 진짜 경쟁자 = 카카오톡 오픈채팅·소모임·당근모임
- **머피월드 = 코스메틱 경제.** 운동 인증으로 캐릭터를 꾸미고 정체성·노력·희소성을 표현
- **공정성 하드룰** — 어떤 아이템도 매칭/피드 노출에 알고리즘 이점 없음
- **검증된 만남이 자산** — 위치·사진·코드·대면접촉 순으로 신뢰등급 차등 (특허 축)

## 3. 기술 스택

- **단일 HTML 파일** `index.html` (약 12,000줄) — CSS + HTML + JS 전부
- Firebase Auth(구글·카카오) / Firestore SDK 10.12.0 ES module / **Realtime Database**(실시간 위치·presence)
- imgBB 이미지 업로드 · Canvas 2D 픽셀 렌더(NEAREST, 정수배) · MapTiler 지도 타일(상업 무료)
- GitHub Pages 배포 · PWA(`manifest.json`, `sw.js`)

## 4. 파일 구조

```
Murpy/
├── index.html              # 전체 앱 (단일 파일)
├── sw.js                   # 서비스워커 (STATIC/CDN 캐시=버전접미사)
├── firestore.rules         # Firestore 규칙 소스
├── database.rules.json     # RTDB 규칙 (squadRooms/{sid}/players 읽기=로그인)
├── bump-fx.html            # 머피 범프 연출 프로토타입 (v9)
├── bump5.html              # 머피 범프 계측 도구 (v16, 혼자 측정 지원)
├── char/                   # 에셋 + 파이프라인 스크립트 (28종)
│   ├── walk.png            # base 시트 ※절대 재수정 금지
│   ├── items/ fields/ ui/ fx/ v2/
│   ├── nukki.py            # ★자체 누끼 툴 (Photoroom 대체, 7-27)
│   ├── remove_gemini_watermark.py  # ✦ 도너 프레임 이식 제거
│   ├── seal_gaps.py / recolor_edge_skin.py / level_hem.py / extend_hem.py
│   └── extract_item.py / extract_hidden.py / extract_season_item.py 등
├── tools/asset-studio/     # 선별(triage)+픽셀도구 서버
├── tools/character-customizer/  # customizer_cli.py (diff 추출·검수)
└── docs/                   # 설계·사업계획·프롬프트 (0장 인덱스 참조)
```

## 5. 앱 구조

**하단탭 6개**: 홈(피드) / 매칭 / 대숲 / **스쿼드** / 머피월드 / 센터
※ 7-20에 크루 → **스쿼드**로 전환(크루 코드는 삭제 않고 휴면).

**머피월드 내부 트리오**: 지도 · **체크인** · 카메라
※ 7-19에 "도감" → **"체크인"** 으로 개명(라벨만, `kind==='dogam'` 키는 유지).

## 6. Firebase 컬렉션

```
users/{uid}          nickname, photoURL, photos[], character, wardrobe[], credits, streak,
                     room(가구배치), roomPos, roomMsg, titles[], title,
                     hiddenChars{cult:{weekday},somm,zombie}, monthly{YYYY-MM:{axis:n}}
  └ roomstat/{날짜}   방문수(TODAY)          └ guestbook/{id}  방명록
feed/ bamboo/ (+comments) · matches/ likes/ chats/ notifications/
centers/{id}/ratings/{uid} · reports/ centerEditRequests/
checkins/{uid}_{centerId}_{yyyymmdd}   # ★센터 체크인 도장 (GPS 200m)
crews/{id}/...       # 휴면 (스쿼드로 대체)
squads/              # 스쿼드 + schedules/applicants/chat/treasury
RTDB squadRooms/{sid}/players/{uid}    # 실시간 위치·presence (onDisconnect)
```

## 7. 완료된 기능 (2026-07-28 기준)

**계정·피드·소통** — 구글/카카오 로그인, 온보딩·코치마크, 프로필 다중사진,
홈 피드(4:5 크롭 컴포저·태그·인증뱃지·페이지네이션), 대숲(카테고리·저에요 신청·상호수락),
1:1 채팅 실시간, 알림

**매칭** — users 실연동, 좋아요/패스, 상호매칭 시 채팅 자동개설, 매칭 전 정보 차등공개

**스쿼드 (7-19~20, 크루 대체)** — 즉석 스쿼드 생성/참가/승인, 스쿼드 톡, 공금,
**RTDB 워킹룸**(탭투워크·쓰로틀 위치동기화·CSS보간·presence·입퇴장 연출),
**출석**(호스트 코드/QR 발급·멤버 입력·지각 판정·도장 팝 브로드캐스트),
호스트 머피 적립(멱등), 벙주 등급(새싹/단골/인증), 종목별 와이드 필드 7종

**센터·체크인 (7-15~19)** — Firestore 센터(42곳 시딩), 지역 필터, 별점/리뷰, 신고, 수정요청,
**GPS 반경 200m 체크인 도장**(`checkins`), 센터별 방문 누적 → **레벨 칭호**(뜨내기→터줏대감→전설),
**체크인 탭 개편**(상단 3타일 목차·콜드스타트 안내·도장 랠리 보상 상단 이동·원정 스탬프 아코디언),
지도 MapTiler + 내 위치 버튼, 카메라 스탬프 + SNS 공유 3버튼

**머피월드 캐릭터** — 레이어 합성(body→bottom→shoes→top→hair→hat→acc), 꾸미기·옷장,
오버월드(방+필드), 캐릭터 코드 공유, **헤어 3종**(7-13), 링 커맨드 메뉴, 발밑 닉네임

**방 인테리어 (7-15~23)** — 방 배경 재제작, **Pixel Interiors 가구 4배 교체**,
배치 저장, 벽 기댐 자동정렬·상판 스택·**가구 충돌(바닥 발자국만)**·겹침 금지·클램프,
접지 그림자, 캠프파이어/아기공룡 애니메이션, **남의 방 구경 + TODAY 방문수 + 방명록**

**시즌 한정 (7-21~23)** — 월간 한정 오브젝트 5종, `monthly.YYYY-MM.axis` 활동 카운터
(피드/대숲/매칭/스쿼드/체크인), 획득 판정 엔진 + 공개형 축하연출, 히든 상자 개봉,
도감 이번달 섹션(실루엣+힌트)·지난 시즌 아카이브, **칭호 시스템**, 관리자 **시즌 실험실**

**히든 캐릭터 3종 (7-27, 배포됨)** — 교주(요일 몰림)·소믈리에(센터 5곳)·좀비(14일 공백 복귀),
`mwEvalHidden` 판정(checkins만으로 계산), **"비밀 관찰 파일" 연출**(글리치→기밀파일→타자기 증거→
기밀해제 스탬프→캐릭터 등장→판정서 공유), 로스터 실루엣 게이트, 관리자 테스트버튼

**퀘스트·크레딧** — 캐릭터 해금을 퀘스트 체계로 통합, 크레딧(`CREDITS_MODE='beta'` 적립만), 스트릭

**에셋 파이프라인** — **자체 누끼 `char/nukki.py`**(Photoroom 대체), 워터마크 도너 이식,
diff 추출(trimap 3분류), 선별 4분류 + 픽셀 도구, seal_gaps/extend_hem/level_hem/recolor_edge_skin

**머피 범프 (7-28, 프로토타입)** — 연출 v9(`bump-fx.html`), 계측 v16(`bump5.html`),
실측 Δt 평균26/중앙17/최대100ms(11쌍). **특허 출원 준비 중** → `Murpy_private/patent/`

## 8. 진행 중 / 미완성

- [ ] **머피 범프 인앱 구현** — 범퍼(관계)·범프 도감·방명록 도장·도장 번지기(연쇄 검증)
- [ ] 범프 계측 재실측 — 감지 임계 11 검증, 1인 2단말 배제(움직임 상관·심박)
- [ ] 특허 출원 — 1차시안 + 포트폴리오(변리사 미팅 7-29). **공개 시점 정리 시급**
- [ ] imgBB API 키 → Cloud Functions 프록시 (공개 런칭 전)
- [ ] 크레딧 `enforced` 모드 전환 (사용자 확보 후)
- [ ] 체크인/해금 **Cloud Functions 이관 + 어뷰징 방어** (공개 런칭 전 필수, 현재 클라 판정)
- [ ] 에셋 파이프라인 슬롯템플릿 자동추출 (생산속도 병목)
- [ ] 우리센터 머피들 심화 · 센터 도감 깊이축
- [ ] 실제 나이 인증(현재 15~80 범위검증만)

## 9. 주요 함수

| 함수 | 역할 |
|------|------|
| `goPage`/`openPanel`/`openModal`/`showToast`/`requireLogin` | 네비·UI 공통 |
| `renderMatch`/`sendLike` · `postBambooFirestore`/`sendBambooRequest` | 매칭·대숲 |
| `submitFeedPost`/`setFeedFilter`/`submitComment` | 피드 |
| `mwCheckin`/`mwLoadCheckins`/`mwLevel`/`mwPickHome`/`mwRenderDogam` | 체크인·도감 |
| `mwVisitRoom`/`mwGbLoad`/`mwGbWrite` | 남의 방 구경·방명록 |
| `mwCenterField`/`mwMiniCharHtml`/`mwBadgeHtml` | 시설별 캐릭터 표시 |
| `mwEvalHidden`/`mwCheckHidden`/`mwHiddenReveal`/`mwTypewriter` | 히든 캐릭터 |
| `mwSeasonKey`/`mwItemDef`/`celebrateMurpy`/`mwValidTitle`/`mwTitleColor` | 시즌·칭호 |
| `mwFurnHtml`/`mwBoxHtml`/`_mwSaveRoomPos`/`_mwBlocked` | 방 인테리어·충돌 |
| `renderCharacter`/`_charBuildLayers`/`_charPersistCharacter`/`submitCharCode` | 캐릭터 |
| 스쿼드: 생성/참가/승인 · `startAttendance`/`submitAttendCode`/`qrCheckinMember` | 스쿼드·출석 |
| `renderCreditUI`/`spendCredit`/`mwUpdateCoin`/`renderStreakUI` | 크레딧·스트릭 |

## 10. 작업 시 주의사항

- **단일 파일** — 모든 CSS/HTML/JS가 `index.html`
- **Firebase 모듈 스코프** — onclick에서 쓰려면 `window.xxx` 전역 등록(브릿지 패턴)
- **작업 후 반드시 git push.** 에셋/JS 바꾸면 `sw.js`의 `murpy-vNNN` 3곳 + `index.html` cache-bust 갱신
- **로컬 미리보기 말고 푸시** — 대표가 배포앱에서 확인하는 게 기본 (내 미리보기는 신뢰 안 함)
- **`sw.js`를 PowerShell로 편집 금지** (인코딩 깨짐). Write 도구 사용. 한글 md/html도 동일
- **에셋 하드룰** — `char/walk.png` 재수정 금지 · 정수배 NEAREST만 · 알파 128 이진화 ·
  레이어 z = body→bottom→shoes→top→hair→hat→acc
- **등록 전 합성 미리보기로 증명·승인** — 말로만 "됐어요" 금지
- **이모지 금지** — 머피 전용 라인 SVG 아이콘 사용
- **색** — 블랙70/화이트20/블루(#3D7EFF)7/골드(#F5C24B)3. 블루=액션, 골드=별점/VERIFIED,
  초록=대숲 악센트. **범프 색 규칙은 별도**(개시자=골드/참여자=파랑, 캐릭터 본체 채색 금지)
- **AI 이미지 누끼용 배경은 형광 마젠타/그린 단색** 요청 (투명배경은 못 그림)

## 11. 절대 하지 말 것

- base 시트 수정 / 비정수배 리샘플 / NEAREST 외 보간
- PixelLab·Imagen 마스크 API·SAM2·ControlNet 재검토
- 카메라 실착 인식으로 캐릭터 옷 대체 (코스메틱 경제와 충돌)
- 해금 조건 명시적 공개(체크리스트화) / 시간대 강제 해금
- 아이템의 매칭·피드 노출 버프
- 클라이언트 단독 판정으로 공개 런칭
- **특허 초안·수익구조 문서를 공개 저장소에 두는 것** (신규성 상실 위험)

---
*마지막 업데이트: 2026-07-28 — 7-13 이후 207커밋 반영 전면 재작성.
스쿼드 전환·체크인 도장/레벨·방 인테리어·시즌 한정·히든 3종·자체 누끼·MapTiler·머피 범프/특허 추가.
문서 인덱스(0장) 신설 — 이 파일은 `docs/` 문서들의 요약이며 상세는 그쪽이 소스.*
