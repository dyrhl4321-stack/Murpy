# MURPY 즉석 스쿼드 + 머피 하이파이브 — 기술 타당성 및 아키텍처 검토

> 작성일 2026-07-19 · 조사·설계 문서(구현 아님). 코드 미수정.
> 검토 대상은 "스쿼드를 구현할지"가 아니라 **"어떤 방식·단계로 구현할지"**다. 스쿼드는 확정 기능으로 전제한다.
> 표기 규칙: **[사실]** = 1차 자료(Apple/MDN/caniuse) 확인, **[추정]** = 설계 판단, **[저장소 실측]** = 현재 코드 확인.

---

## 1. 결론 요약

1. **스쿼드 기능 자체(생성·참가·채팅·출석·공동기록·자동종료)는 현재 HTML/CSS/JS + Firebase 웹앱만으로 100% 구현 가능하다.** 새 기술 스택 불필요. 기존 크루의 일정·출석·QR·채팅 코드를 대부분 재활용한다. → **Go**.
2. **"두 폰을 가까이 대면 즉석 스쿼드가 생성되는 근접 체감(하이파이브)"은 순수 웹/PWA로는 iOS에서 불가능하다.** iOS Safari/WKWebView는 Web NFC·Web Bluetooth·Vibration API를 모두 지원하지 않는다 **[사실]**. 근접·햅틱은 **iOS 네이티브(Multipeer Connectivity + Nearby Interaction + Core Haptics)**로만 가능하다.
3. **NameDrop 자체를 서드파티가 호출하는 것은 불가능하다** **[사실]**. 단, "폰을 가까이 대면 연결되는 체감"을 MURPY 내부에서 **독자적으로 재현**하는 것은 네이티브로 가능하다.
4. **권장 경로: 웹 우선 → 근접 나중.** ① 웹에서 스쿼드 + QR/코드 하이파이브 MVP를 먼저 배포해 UX를 검증하고, ② 이후 **Capacitor 셸 + Swift 네이티브 플러그인**으로 근접·햅틱만 추가한다. 기존 웹 코드는 유지된다. → **웹 코드 재작성 불필요.**
5. **QR(또는 4~6자리 코드) 방식만으로 "하이파이브 → 즉석 스쿼드" UX의 제품 가설을 MVP 수준에서 충분히 검증할 수 있다.** UWB 하이파이브는 "마법 같은 체감"을 위한 상위 폴리시이지, 스쿼드 성립의 전제가 아니다.

**한 줄 요약:** 스쿼드는 지금 웹으로 만든다. 하이파이브의 "폰 대기" 감성은 나중에 Capacitor+Swift로 얹는다. 전체 네이티브 재개발은 필요 없다.

---

## 2. 스쿼드 기능의 제품 정의

- **정의:** 오늘 또는 가까운 일정에 함께 운동할 **2~8명의 임시 운동 그룹**. 조직이 아니라 "그날의 운동"을 만드는 단위.
- **핵심 특성:** 가입 심사 없음 · 장기 소속 없음 · 장소/시간/종목 중심 · 누구나 30초 내 생성 · 운동 종료 후 자동 종료 · 마음 맞으면 같은 멤버로 재생성 · 반복 관계는 별도 자산으로 축적.
- **하이파이브의 위치:** 독립적 친구추가 기능이 아니라 **"현실에서 만난 사람들이 가장 빠르게 스쿼드를 만들게 하는 입력 방식"**. 성공 후 1순위 CTA는 항상 `[오늘 스쿼드 만들기]`, 친구/방문은 부가.

---

## 3. 현재 크루 구조의 문제점 (스쿼드로 가는 이유)

**[저장소 실측]** 현재 크루는 `crews/{crewId}` + `schedules`·`applicants`·`chat`·`photos`·`feed`·`treasury` 하위 컬렉션으로, 장기 조직 운영에 최적화돼 있다(생성·가입비·승인·게시판·사진첩·공금·관리자탭).

장기 소속형의 구조적 한계:
- 기존 멤버 관계 고착 → 신규 진입장벽 ↑
- 시간이 갈수록 친목 중심화 · 운영진 규칙/심사 강화
- "조직에 소속돼야 한다"는 부담 → 소모임·당근모임·카톡오픈챗과 구조가 수렴

MURPY의 지향("오늘 같이 운동할 사람을 가볍게 연결")과 어긋난다. 스쿼드는 이 마찰을 제거한 **경량·일회성·현장 중심** 단위다.

---

## 4. 스쿼드로 재설계할 수 있는 범위

크루의 **엔진(일정·참가·출석·채팅·완료판정)은 그대로 쓰고, 껍데기(영구 소속·게시판·공금·등급·운영진)만 벗긴다.** 즉 새로 만드는 것은 대부분 "얇은 생성 UX + 임시 세션 + 자동 종료"이고, 백엔드 상태기계는 크루 출석 로직의 파생이다. 상세 매핑은 §6.

---

## 5. 현재 웹앱에서 즉시 구현 가능한 스쿼드 기능

전부 **현재 스택(index.html + Firestore)만으로 가능**:

| 기능 | 가능 여부 | 근거(저장소 실측) |
|---|---|---|
| 스쿼드 생성(종목·장소·시간·정원·강도·메모) | ✅ | 크루 `addDoc(schedules)` 폼 패턴 |
| 스쿼드 참가/참가 취소 | ✅ | `applyToSchedule`/`cancelApplication` 패턴 |
| 호스트 승인 / 즉시 참가 | ✅ | `applicants` 승인 흐름(`approveApplicant`) |
| 정원 제한·중복참가 차단 | ✅ | `pendingCount`/`capacity` + 트랜잭션 필요(§16) |
| 스쿼드 전용 채팅 | ✅ | `crews/{id}/chat` onSnapshot 실시간 |
| QR 체크인 | ✅ | `openQRModal`/`qrCheckinMember` 존재 |
| 4~6자리 코드 참가/출석 | ✅ | `attendCode`(6자리)·`submitAttendCode` 존재 |
| 정시·지각·불참 자동 판정 | ✅ | `submitAttendCode`의 5분 지각·`endAttendance` 결석 |
| 자동 종료(일정 종료 후) | ✅ | `status:'done'` 전이 + `expiresAt` 필드 추가 |
| 공동 운동 기록·보상 | ✅ | `checkins`·`users.credits`·머피월드 연동 |
| 같은 센터·시간 기반 참가(안 C) | ✅ | `checkins` + haversine(master-brief 3장) 재사용 |

**질문 1 답: 그렇다.** 근접 감지 없이도 스쿼드 코어 전체가 현재 웹앱에서 구현 가능하다. 근접(하이파이브)은 "생성 입력 방식 중 하나"일 뿐이고, QR/코드/센터매칭이 웹에서 그 자리를 메운다.

---

## 6. 기존 크루 코드 재활용 분석

**[저장소 실측]** 실제 함수·컬렉션 기준 분류:

| 크루 기능 | 분류 | 스쿼드 적용 방법 |
|---|---|---|
| 일정 생성 (`addDoc(crews/{id}/schedules)`) | 일부 수정 재사용 | `crews/{id}/schedules` → 최상위 `squads/{id}`로. 필드 대부분 동일 |
| 참가 신청 (`applyToSchedule`, `applicants` 서브컬렉션) | 그대로 재사용 | `squads/{id}/members` 서브컬렉션으로 이름만 |
| 신청자 승인 (`approveApplicant`/`rejectApplicant`) | 일부 수정 | "호스트 승인" 모드에서만. "즉시 참가" 모드는 스킵 |
| 채팅 (`crews/{id}/chat`, `sendCrewChatFirestore`) | 그대로 재사용 | `squads/{id}/chat` |
| QR 출석 (`openQRModal`/`qrCheckinMember`) | 그대로 재사용 | 스쿼드 체크인에 직결 |
| 출석 코드 (`startAttendance`·`attendCode` 6자리·30분 만료) | 그대로 재사용 | 하이파이브 QR/코드 폴백의 핵심 |
| 지각 판정 (`submitAttendCode`, 시작+5분) | 그대로 재사용 | 스쿼드 `scheduledAt` 기준 동일 |
| 완료/결석 처리 (`endAttendance`, absent+penalty) | 일부 수정 | 벌금(treasury)만 제거, 결석 기록은 신뢰지표로 유지 |
| 멤버 목록 | 그대로 재사용 | `memberUids` |
| 알림 (`notifications`) | 그대로 재사용 | 스쿼드 초대/시작 알림 |
| 사진 업로드 (`uploadCrewPhoto`) | 일부 수정 | 공동 운동 인증 사진 1~2장만 |
| 참가비·공금 (`treasury`) | **스쿼드에 부적합** | 일회성 그룹엔 제거(호스트 부담·심사 마찰) |
| 게시판·사진첩 중심 탭 | **삭제/보류** | 장기 조직 UI. 스쿼드는 채팅+출석만 |
| 영구 가입·등급·운영진·경고/퇴출 | **삭제** | 경량성과 충돌 |

**질문 2 답:** 출석 코어(코드 발급·검증·지각·결석·완료)와 채팅·QR·알림·멤버관리는 **거의 그대로 재활용**한다. 벗어낼 것은 영구 소속·공금·게시판·등급·운영진 심사다.

> ⚠️ **재활용 시 반드시 함께 고칠 것(§16):** 현재 `submitAttendCode`는 **클라이언트가 `attendCode`를 읽어 직접 비교**한다. 코드값이 클라이언트에 노출되고, Firestore 직접쓰기로 `checkedIn`을 위조할 수 있다. 스쿼드 출석/공동인증은 보상과 직결되므로 **Cloud Functions 서버 검증으로 승격**해야 한다.

---

## 7. QR 기반 하이파이브 MVP (안 B)

근접 하드웨어 없이 "만나서 즉석 스쿼드"를 검증하는 최단 경로:

```text
사용자 A가 [하이파이브] → 일회용 QR/6자리 코드 생성 (squadLobby 세션, 60~120초 만료)
→ B가 카메라로 스캔 또는 코드 입력 → 임시 로비 참가
→ 양측 승인 → [오늘 스쿼드 만들기] → A·B 자동 멤버 → 장소·시간·종목 → 스쿼드 생성
→ 전용 채팅 → 체크인 → 완료 → 자동 종료
```

- **다자(3~8인):** 호스트가 로비 QR을 띄워두고 C·D·… 가 순차 스캔 → 한 로비에 누적. UWB의 "1:1 순차 하이파이브"보다 오히려 다자에 강함.
- **웹 QR:** 생성은 순수 JS(경량 QR 라이브러리), 스캔은 `getUserMedia` + `BarcodeDetector`(iOS 17+ Safari 지원 **[추정, 확인 권장]**) 또는 jsQR 폴백. **[저장소 실측]** 이미 `openQRModal`/`qrCheckinMember`가 있어 절반은 구현돼 있다.
- **폴백:** 카메라 거부/구형 기기는 **6자리 코드 수동 입력**(`attendCode` 재사용)으로 완전 대체.

**질문 3 답: 그렇다.** QR/코드만으로 하이파이브 스쿼드 UX의 제품 가설(현장에서 빠르게 같이 운동)을 MVP로 검증 가능하다. "폰 맞대기" 촉감만 빠질 뿐, 흐름·데이터·보상은 동일하다.

---

## 8. 순수 웹앱에서 불가능/제약인 근접 기능 (iOS 기준)

§12의 판정 기준으로 분류. **[사실]** 표기는 1차 자료 확인분.

| 기능 | 판정 (iOS Safari/PWA) | 근거 |
|---|---|---|
| 스쿼드 생성/참가/종료/채팅 | ✅ 가능 | Firestore |
| QR 하이파이브 / 4~6자리 코드 | ✅ 가능 | 카메라 + Firestore |
| 동일 센터·시간 기반 참가 | ✅ 가능 | `checkins` + Geolocation |
| Geolocation 근접 추정 | 부분 가능(수십 m 오차) | GPS 정확도 한계 — "옆 사람" 식별 불가 |
| **Vibration API(진동 햅틱)** | ❌ iOS 미지원 **[사실]** | WebKit 미구현. `navigator.vibrate`는 iOS에서 no-op |
| **Web NFC(폰 태그)** | ❌ iOS 미지원 **[사실]** | WebKit 미구현. NDEFReader undefined |
| **Web Bluetooth(주변 기기)** | ❌ iOS Safari 미지원 **[사실]** | WKWebView·Safari 미구현(서드파티 브라우저만) |
| WebRTC(P2P 데이터) | ⚠️ 가능하나 부적합 | iOS Safari 지원 **[사실]**, 그러나 시그널링 서버 필요 + **근접 감지 아님**(누구와 연결할지 못 정함) |
| 동일 Wi-Fi/LAN 탐색 | ❌ 웹 표준 없음 | 브라우저가 로컬 피어 스캔 API 미제공 |
| 주변 아이폰 자동 발견 / 폰 상단 근접 감지 | ❌ 웹 불가 | 근접·P2P 발견 웹 API 부재 |
| UWB 거리측정 / Nearby Interaction | ❌ 웹 불가(네이티브 전용) | 웹 바인딩 없음 |

**핵심:** 현재 코드의 `navigator.vibrate(10)`(체크인 시)은 **Android에서만 동작하고 iOS에선 조용히 무시**된다 **[저장소 실측 + 사실]**. iOS에서 햅틱을 주려면 네이티브가 유일하다.

---

## 9. iOS 네이티브에서 가능한 범위

| 프레임워크 | 용도 | 핵심 사실 |
|---|---|---|
| **Multipeer Connectivity** | 주변 MURPY 실행 아이폰 발견 · 일회성 토큰 교환 · 인터넷 없이 임시 연결 | Bluetooth+peer Wi-Fi. **포그라운드 전용**(백그라운드 미지원) **[사실]**. **App Clip 불가**(Bonjour 미지원) **[사실]** |
| **Nearby Interaction** | UWB 거리(±cm) 측정 · 10~20cm 임계 판정 · 방향 | **iPhone 11+ U1 칩**(iPhone 15+는 U2) **[사실]**. 폰-폰은 **앱 포그라운드 필요**(백그라운드는 iOS16+ 액세서리 세션 한정) **[사실]**. **discovery token은 세션 수명 동안만 유효**, 별도 채널(Multipeer 또는 Firebase/WebSocket)로 교환 **[사실]** |
| **Core Haptics / UIKit 햅틱** | 근접 시 "웅—", 연결/생성 완료 햅틱 | 네이티브 전용(웹 Vibration은 iOS 불가) |
| **Firebase(공용)** | 세션·승인 동기화 · 로비 · 최종 스쿼드 · 채팅 · 출석 · 보상 중복방지 | 기존 웹 스택 그대로 |

**전형적 조합:** Multipeer로 "주변에 누가 있나"를 발견하고 discovery token을 교환 → Nearby Interaction으로 "그 사람이 실제로 20cm 안에 왔나"를 UWB로 확인 → Core Haptics로 촉감 → 승인 → 로비는 Firebase에 만들고 → 이후 스쿼드/채팅/출석은 기존 웹 로직.

**질문 4 답: 그렇다.** 웹 코드를 유지한 채 **Capacitor + Swift 플러그인**으로 근접·햅틱·캐릭터 애니메이션을 실서비스급으로 구현 가능하다. 단 UWB 정밀 근접은 **iPhone 11+ · 포그라운드 · 양측 앱 실행** 조건이며, 미지원 기기·Android는 **QR/BLE 폴백**으로 흡수한다(§19).

---

## 10. NameDrop과의 차이

- **[사실]** NameDrop은 시스템 AirDrop 기능이다. **서드파티가 호출/복제할 공개 API가 없다.** iOS17부터는 같은 앱끼리 커스텀 타입 AirDrop 교환도 제한됐다.
- 즉 MURPY는 NameDrop을 "부를" 수 없다. 대신 **"두 폰을 가까이 대면 반응하는 체감"을 앱 내부에서 독자 구현**한다(Multipeer 발견 + Nearby Interaction 근접 + Core Haptics). 잠금화면·앱 미실행 상태의 자동 트리거는 불가 — **양측 모두 하이파이브 화면을 포그라운드로 열어야 한다** **[사실 기반 추정]**.

**질문(§13) 답:** 시스템 NameDrop 접근·백그라운드 자동실행·잠금화면 트리거·앱 미실행 트리거는 **불가**. "포그라운드에서 폰을 맞대면 즉석 스쿼드가 만들어지는 체감"은 **가능**.

---

## 11. 구현안 A~E 비교표

| 항목 | A 웹 스쿼드 MVP | B 웹 QR 하이파이브 | C 위치·시간·코드 | D Capacitor+Multipeer | E D + Nearby Interaction |
|---|---|---|---|---|---|
| 스쿼드 생성 | ✅ | ✅ | ✅ | ✅ | ✅ |
| 근접 감지 | ❌ | ⚠️ 대용(스캔) | ⚠️ 대용(GPS+코드) | ✅ 발견(수 m~수십 m) | ✅ 정밀(±cm, 10~20cm) |
| 웹앱 유지 정도 | 100% | 100% | 100% | 95%(셸+플러그인) | 90%(셸+플러그인) |
| UX "폰 맞대기" 감성 | 없음 | 낮음 | 낮음 | 중 | **높음**(햅틱+애니) |
| iOS 지원 | 전 기종 | 전 기종 | 전 기종 | iOS 전반(포그라운드) | iPhone 11+ 만 정밀 |
| Android 지원 | ✅ | ✅ | ✅ | ⚠️ 별도 구현(Nearby Connections) | ⚠️ UWB 기기 한정 |
| 다자(3~8) | ✅ | ✅(로비 누적) | ✅ | ⚠️ 순차 세션 | ⚠️ 순차 세션 |
| 오작동 위험 | 낮음 | 낮음 | 중(GPS 오차) | 중(엉뚱 발견) | 낮음(cm 임계) |
| 개발 난이도 | 낮음 | 낮음 | 중 | 높음(Swift) | 매우 높음(UWB+다자) |
| 예상 기간 **[추정]** | 1~2주 | +3~5일 | +1주 | +3~5주 | +3~6주(누적) |
| MVP 적합성 | ★★★ | ★★★ | ★★ | ★ | ✗ |
| 장기 적합성 | ★★ | ★★ | ★★ | ★★★ | ★★★(차별화) |

---

## 12. 권장 스쿼드 MVP 구조

**A + B + C를 웹으로 묶은 것이 MVP.** 근접 네이티브(D/E)는 Phase 2.

```text
[스쿼드] 탭 (크루 탭을 점진 전환 또는 신설)
├─ 오늘의 스쿼드(피드): 종목·센터·시간·현재인원 카드
├─ [+ 스쿼드 만들기]: 종목→센터→시간→정원→강도→메모 (30초, source=manual)
├─ [하이파이브]: 일회용 QR/6자리 코드 로비 (source=highFive, QR로 대용)
├─ 매칭/대숲/센터에서 생성: source=match/bamboo/center
└─ 스쿼드 상세: 멤버·채팅·체크인(QR/코드)·완료·자동종료
```

- 생성 3경로(일반·QR·센터매칭)를 먼저, 근접은 나중에 "하이파이브" 버튼 뒤에 네이티브로 승격.
- **[저장소 실측]** 크루 출석 UI(코드 입력 모달·타이머·QR 모달)를 그대로 재사용.

---

## 13. 권장 하이파이브 최종 구조 (Phase 2)

```text
양측 [하이파이브] 포그라운드 실행
→ (네이티브) Multipeer로 주변 MURPY 기기 광고/발견 + 일회용 세션토큰·NI discovery token 교환
→ (네이티브) Nearby Interaction UWB 거리측정, 10~20cm 이하 확인
→ (네이티브) Core Haptics "웅—"
→ (웹) 두 머피 캐릭터 접근·하이파이브 애니메이션(기존 캔버스/DOM)
→ 양측 승인 → (웹) Firebase에 squadLobby 세션 생성
→ [오늘 스쿼드 만들기] → 스쿼드 생성(=웹 로직)
```

- **웹↔네이티브 통신:** Capacitor Bridge. 네이티브 플러그인은 "근접 성공 + 상대 uid/토큰"만 JS 콜백으로 넘기고, **스쿼드 생성·채팅·출석은 전부 기존 JS/Firebase**가 담당(플러그인 최소화).
- **다자:** 호스트가 로비 유지, 참가자가 순차 하이파이브로 로비에 합류(NI 1:1 순차 + Firebase 로비가 진실원본).
- **폴백:** UWB 미지원/Android → 같은 화면에서 자동으로 **QR/코드**로 전환(§19).

**질문 5 답: 그렇다.** 스쿼드를 웹으로 먼저, 근접만 네이티브로 나중에 붙이는 것이 기술·비용·리스크 모두에서 가장 합리적이다. 근접은 "성공 신호"만 만들고 나머지는 검증된 웹 로직을 재사용하므로 결합도가 낮다.

---

## 14. Firestore 데이터 구조 (제안)

**[추정]** 현재 코드 스타일(최상위 컬렉션 + 서브컬렉션, `window.*` 브릿지) 준수.

```text
squads/{squadId}
  hostUid, memberUids[]            // 배열(빠른 읽기) + members 서브컬렉션(상세)
  title, exerciseType
  centerId, location, scheduledAt
  startedAt, endedAt
  capacity(2~8), level, oneLineMemo
  status                           // §15
  source                           // manual|match|bamboo|center|highFive|qr
  createdAt, expiresAt             // 자동 종료 기준
  checkinCode, checkinCodeExpiry   // ★값은 서버에만, 클라 노출 금지(§16)
squads/{squadId}/members/{uid}
  status                           // invited|accepted|checkedIn|late|noShow|completed|left
  nickname, joinedAt, checkinTime, checkinType
squads/{squadId}/chat/{msgId}     // 크루 chat과 동형
squadLobby/{sessionId}            // 하이파이브/QR 임시 세션
  hostUid, challenge, participants[], createdAt, expiresAt, consumed
records/{recordId}                // 공동 운동 기록(완료 시 생성)
  squadId, memberUids[], centerId, at, verified
```

- 신뢰지표는 `users/{uid}`에 누적: `squadCount, attendRate, noShowCount, dayCancelCount, hostRating, repeatRate`.

---

## 15. 스쿼드 상태 전이

```text
forming → recruiting → ready → active → completed
   │           │                          
   └──────────→ cancelled                 
   (any) ─────→ expired  (expiresAt 경과 · 로비 미완)
```

- 멤버: `invited → accepted → checkedIn → (late) → completed` / 이탈 `left` / 미출석 `noShow`.
- **자동 종료:** `endedAt` 또는 `expiresAt` 경과 시 Cloud Functions(스케줄) 또는 클라 진입 시 lazy 전이로 `completed`/`expired`. 채팅은 종료 후 읽기전용, 운동 기록은 프로필·머피월드에 영구 유지.

---

## 16. 보안·어뷰징 방지

**핵심 위험과 대응(현재 클라 검증 구조의 승격 필요):**

| 위험 | 대응 |
|---|---|
| QR/코드 캡처 재사용·전달 | 일회용 `challenge` + 짧은 만료(60~120초) + `consumed` 플래그, 서버 검증 |
| `checkedIn` 위조(Firestore 직접쓰기) | **Cloud Functions로만 체크인 기록** + 보안규칙에서 클라 직접쓰기 차단 |
| 코드 노출(현재 `attendCode` 클라 비교) | 코드값을 클라에 내려주지 않음. 서버가 대조 |
| 정원 초과·동시참가 경합 | 서버 트랜잭션으로 원자적 멤버등록 + capacity 확인 |
| GPS 조작·비대면 공동인증 | 근접(UWB/BLE) + 동일센터 체크인 + 시간창 **다중조건 AND**, 단일 GPS 불신 |
| 다계정 보상·중복완료 | 서버 멱등키(squadId+uid)로 보상 1회 · 기기/계정 지표 |
| 스팸 스쿼드·노쇼 반복 | 생성 레이트리밋 · `noShowCount` 기반 제한 · 호스트 신고 |
| 차단 사용자 재연결·미성년·위치노출 | 차단목록 필터 · 연령 게이트 · 장소 공개범위(정확좌표 대신 센터명) |

**Cloud Functions 필요 여부: 필요(공개 런칭 전 필수).** 근거: (1) 현재 출석은 클라 검증이라 보상 연동 시 위조 가능 **[저장소 실측]**, (2) 정원 원자성·challenge 발급·보상 멱등은 서버가 있어야 안전. master-brief도 체크인·해금의 Functions 이관을 공개 런칭 전 필수로 규정.

---

## 17. Capacitor 전환 필요성

- **웹만으로 앱스토어 배포 위험 [사실]:** 원격 URL(`server.url`) 로딩은 프로덕션 비권장이며, 단순 웹뷰는 **가이드라인 4.2(최소 기능)**로 거절되기 쉽다. → **로컬 번들 + 네이티브 요소(푸시·네이티브 플러그인·오프라인)**로 "app-like" 확보.
- **권장:** 기존 `index.html`·에셋을 **Capacitor에 로컬 번들**로 포함(원격 GitHub Pages 로딩 X). 하이파이브만 Swift 플러그인. 스쿼드/채팅/출석은 기존 JS+Firebase 유지.
- **점검 필요:** (1) Firebase Auth `signInWithPopup` → 네이티브 웹뷰에선 리다이렉트/네이티브 SDK 방식 검토 **[추정, 확인 권장]**, (2) PWA 서비스워커와 Capacitor 캐시 충돌 → 셸에선 sw 비활성 또는 역할 분리, (3) 카메라·알림·딥링크 권한.

---

## 18. 기기·OS 지원 범위

- **스쿼드 웹 코어:** iOS/Android 전 기종, 최신 브라우저.
- **UWB 정밀 하이파이브:** **iPhone 11 이상(U1)**, iPhone 15+는 U2 **[사실]**, 양측 앱 포그라운드.
- **Multipeer 발견(비정밀):** UWB 없는 iPhone도 가능(수 m~수십 m), 포그라운드 전용 **[사실]**.
- **App Clip:** Multipeer 불가(Bonjour 미지원) **[사실]** → 하이파이브 완전판은 정식 앱에서만. App Clip은 QR 진입 정도로 한정.

---

## 19. Android 폴백

- Android는 iOS의 Multipeer/NI와 API가 다름 → **Nearby Connections(구글)** 또는 UWB(Android 12+ 일부 기기)로 별도 구현 필요 **[추정]**.
- **MVP·크로스플랫폼 공통 폴백 = QR + 6자리 코드 + 동일센터·시간.** 하이파이브 화면은 UWB 미지원이면 자동으로 QR/코드 UI로 폴백 → **모든 기기에서 스쿼드 생성은 보장**.

---

## 20. 특허 설명서용 기술 구조 (기술 설명만; 등록 가능성 단정 금지)

```text
복수 사용자 단말기의 근접상태 또는 연결의사 확인
→ 복수 사용자를 임시 연결 세션(로비)에 등록
→ 위치·시간·운동장소 정보 결합
→ 소규모 즉석 운동 스쿼드 생성
→ 공동 운동 세션 시작
→ 출석·지각·완료 판정
→ 공동 운동 기록 생성(참여자 전원 프로필 연결)
→ 참여자별 가상 캐릭터 상태 동기화(머피월드)
→ 공동 보상·관계(REAL LINK)·방문권한 생성
→ 운동 종료 후 스쿼드 자동 해산, 반복관계는 별도 자산으로 축적
```

**차별화 포인트:** 근접 이벤트가 곧 즉석 운동 스쿼드 생성으로 연결 · 장소+시간 결합 · 다수 공동 세션 · 출석/완료가 복수 사용자에 동시 반영 · **현실 운동 결과가 캐릭터 관계/보상/가상공간에 동기화** · 종료 후 자동 해산 · 반복관계 자산화.

> ⚠️ 울라불라 등 **과거 근접 만남 인증 특허가 선행기술로 존재할 수 있음.** 단순 근접 인증을 복제하지 말고 "근접→즉석 운동 스쿼드→공동 운동 결과의 가상 캐릭터 동기화" 결합 구조로 차별화. **변리사 선행기술 조사 필수**(본 문서는 법률 판단 아님).

---

## 21. 예상 개발 단계와 난이도

| 단계 | 내용 | 스택 | 난이도 | 기간 **[추정]** |
|---|---|---|---|---|
| P0 | 스쿼드 코어(생성·참가·채팅·출석·완료·자동종료) | 웹(크루 재활용) | 낮음 | 1~2주 |
| P1 | QR/6자리 하이파이브 로비 + 동일센터·시간 참가 | 웹 | 낮음 | 3~7일 |
| P2 | 보안 승격(Cloud Functions: challenge·원자적 참가·보상 멱등·서버 체크인) | Functions | 중 | 1~2주 |
| P3 | Capacitor 셸 패키징(로컬 번들·푸시·Auth/SW 정합) | Capacitor | 중 | 1~2주 |
| P4 | Swift 네이티브 하이파이브 플러그인(Multipeer 발견 + Core Haptics) | Swift | 높음 | 2~3주 |
| P5 | Nearby Interaction UWB 정밀 근접 + 다자 세션 + 폴백 | Swift | 매우 높음 | 3~6주 |

- **P0~P2가 실제 제품 가치의 대부분**(스쿼드 성립·안전). P4~P5는 "마법 체감" 차별화.

---

## 22. 최종 Go / No-Go 판단

| 질문 | 판단 |
|---|---|
| Q1 웹앱으로 스쿼드 코어 구현? | **Go** — 현재 스택으로 전부 가능, 크루 재활용 |
| Q2 크루 재활용 범위? | 출석코어·채팅·QR·알림·멤버 재사용 / 공금·게시판·영구소속 제거 |
| Q3 QR만으로 하이파이브 MVP 검증? | **Go** — 촉감만 빠질 뿐 흐름·데이터·보상 동일 |
| Q4 웹 유지 + Capacitor+Swift로 근접·햅틱 실서비스? | **Go(조건부)** — iPhone11+·포그라운드·양측실행, 폴백 필수 |
| Q5 웹 먼저 · 근접 나중이 합리적? | **Go** — 결합도 낮고 리스크·비용 최적 |

**종합 Go/No-Go:**
- ✅ **GO (즉시): P0~P2 웹 스쿼드 + QR 하이파이브 + 보안 승격.** 전체 네이티브 재개발 불필요.
- ✅ **GO (Phase 2): P3~P5 Capacitor + Swift 근접 플러그인.** 웹 코드 유지, 근접만 네이티브.
- ⚠️ **주의:** iOS 근접의 포그라운드·기기(U1) 제약과 App Clip/Multipeer 한계, 클라 검증→서버 검증 승격, Android 폴백은 설계 초기부터 QR/코드로 흡수.

---

## 부록 — 확인된 1차 사실 요약

- Web NFC(NDEFReader): iOS Safari/WebKit 미지원(Chrome Android 전용).
- Web Bluetooth: iOS Safari 미지원(서드파티 브라우저/확장만).
- Vibration API(`navigator.vibrate`): iOS Safari 미지원(no-op). → iOS 햅틱은 네이티브.
- Nearby Interaction(UWB): iPhone 11+ U1(15+ U2), 폰-폰 포그라운드 필요, discovery token 세션 수명 한정·별도 채널 교환.
- Multipeer Connectivity: 포그라운드 전용, App Clip 불가(Bonjour), CoreBluetooth가 App Clip 대안.
- NameDrop: 서드파티 호출 불가(공개 API 없음).
- Capacitor: `server.url` 원격 로딩 프로덕션 비권장, 단순 웹뷰는 4.2 거절 위험 → 로컬 번들+네이티브 기능.

### Sources
- [Web NFC — Can I use](https://caniuse.com/webnfc) · [NDEFReader — MDN](https://developer.mozilla.org/en-US/docs/Web/API/NDEFReader)
- [Web Bluetooth — Can I use](https://caniuse.com/web-bluetooth) · [Web Bluetooth API — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Web_Bluetooth_API)
- [navigator.vibrate iOS 논의 — MDN BCD #29166](https://github.com/mdn/browser-compat-data/issues/29166) · [Vibration API 지원](https://www.testmuai.com/learning-hub/vibration-api-browser-support/)
- [Nearby Interaction — Apple Developer](https://developer.apple.com/nearby-interaction/) · [Nearby Interaction 문서](https://developer.apple.com/documentation/nearbyinteraction) · [Meet Nearby Interaction WWDC20](https://developer.apple.com/videos/play/wwdc2020/10668/)
- [Multipeer Connectivity — Apple](https://developer.apple.com/documentation/multipeerconnectivity) · [App Clips & Multipeer(Bonjour 불가) — Apple Forums](https://developer.apple.com/forums/thread/701374)
- [Webview 앱 4.2 심사 — MobiLoud](https://www.mobiloud.com/blog/app-store-review-guidelines-webview-wrapper) · [Capacitor server.url 프로덕션 비권장 — GH Discussion #4080](https://github.com/ionic-team/capacitor/discussions/4080)
- [iOS17 AirDrop/NameDrop 서드파티 제약 — Apple Forums](https://developer.apple.com/forums/thread/738469)
