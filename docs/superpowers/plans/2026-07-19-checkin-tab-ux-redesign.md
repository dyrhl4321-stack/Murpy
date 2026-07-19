# 도감 → 체크인 탭 UX 개편 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 머피월드 "도감" 탭을 "체크인"으로 리네이밍하고, 진입 즉시 ①내 센터 등록 ②다른 센터 존재 ③보상 존재가 인지되도록 도감 화면을 재구성한다.

**Architecture:** 단일 파일 `index.html` 안의 탭 바(HTML)·`mwWorldPanel`(패널 헤더)·`mwRenderDogam`(본문 렌더 함수)만 수정한다. 신규 픽셀 아이콘 1장(`char/ui/ui_ic_stamp.png`, 이미 처리·저장됨)과 기존 M코인(`char/coin.png`)을 표시에 사용한다. 로직·데이터·보상 계산은 변경하지 않고 배치·표시·라벨만 바꾼다.

**Tech Stack:** 단일 HTML/CSS/JS 파일, Canvas 2D 뱃지, Firebase(읽기만), PWA service worker(`sw.js`) 캐시 버전 접미사.

## Global Constraints

- **단일 파일**: 모든 변경은 `index.html`(약 10,300줄)과 `sw.js` 안에서. 새 파일은 에셋(`char/ui/ui_ic_stamp.png`)뿐.
- **sw 캐시**: `index.html`/에셋을 바꾸면 `sw.js`의 `murpy-v###` 3곳을 반드시 올린다(현재 **v160**). Edit 도구로만 수정(PowerShell replace는 한글 주석 CP949 깨짐).
- **머피월드 UI 위계**: 세계 레벨 요소 = 사각 픽셀 입체(`#1b2233` + 3px `#05070c` 보더 + `0 0 0 2px #2b3350`), radius 0. 픽셀 아이콘은 머피월드 안에서만.
- **색 시스템**: 블루(#3D7EFF)=액션/CTA, 골드(#F5C24B)=보상/별점, 이모지 금지(라인 SVG 또는 픽셀 에셋).
- **kind 키 불변**: `mwWorldPanel('dogam')` 호출부의 `'dogam'` 키 문자열은 그대로 둔다(호출부 여러 곳). **라벨/타이틀 문자열만** 바꾼다.
- **검증**: 자동 테스트 프레임워크 없음. 각 태스크는 (1) 편집 후 `node tools/dogam-syntax-check.mjs`(Task 0에서 생성)로 스크립트 블록 구문 통과 (2) sw 버전업 (3) 커밋. 최종 푸시 후 대표 실앱 확인.
- **커밋 메시지**: 한글·따옴표 포함 시 `git commit -F <파일>` 또는 Bash(Git Bash) `-m` 사용(PowerShell here-string 금지). 끝에 `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.

---

### Task 0: 구문 검증 스크립트 준비

**Files:**
- Create: `tools/dogam-syntax-check.mjs`

**Interfaces:**
- Produces: `node tools/dogam-syntax-check.mjs` → index.html의 최상위 `<script>`(module 아님) 블록 하나를 추출해 `new Function()`으로 파싱, 문법 에러 시 비정상 종료. 이후 모든 태스크가 편집 후 이 명령으로 회귀 확인.

- [ ] **Step 1: 스크립트 작성**

```js
// tools/dogam-syntax-check.mjs — index.html 일반 script 블록 문법만 빠르게 검증
import fs from 'node:fs';
const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
// mwRenderDogam 등 일반 script (type 없는 <script> ... </script>) 블록 추출
const blocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m => m[1]);
if (!blocks.length) { console.error('NO_SCRIPT_BLOCK'); process.exit(2); }
let bad = 0;
blocks.forEach((code, i) => {
  try { new Function(code); }
  catch (e) { bad++; console.error(`BLOCK ${i} SYNTAX ERROR:`, e.message); }
});
if (bad) process.exit(1);
console.log(`OK ${blocks.length} script block(s) parsed`);
```

- [ ] **Step 2: 실행해 현재 통과 확인**

Run: `node tools/dogam-syntax-check.mjs`
Expected: `OK N script block(s) parsed` (에러 없이 종료 0). 만약 module import 때문에 실패하면 정규식을 `type` 속성 없는 `<script>`만 잡도록 이미 한정했으므로 통과해야 함. 실패 시 해당 블록 인덱스를 보고 정규식을 조정.

- [ ] **Step 3: 커밋**

```bash
git add tools/dogam-syntax-check.mjs
git commit -m "chore(tools): 도감 개편용 index.html script 구문 체크 스크립트"
```

---

### Task 1: 도감 → 체크인 리네이밍 + 도장 아이콘

**Files:**
- Modify: `index.html` (탭 바 ~1025-1027, `mwWorldPanel` title ~9916, `icons.dogam` ~9920)
- Asset: `char/ui/ui_ic_stamp.png` (이미 저장됨 — 커밋만)
- Modify: `sw.js` (v160 → v161)

**Interfaces:**
- Consumes: `char/ui/ui_ic_stamp.png` (마젠타 despill·크롭 완료된 도장 아이콘).
- Produces: 탭 라벨/패널 타이틀 "체크인", 패널 헤더 도장 아이콘. `mwWorldPanel('dogam')` 호출 계약 불변.

- [ ] **Step 1: 탭 바 라벨·아이콘 교체**

`index.html`의 탭 버튼(현재):
```html
    <button class="mw-wb-tabbtn" onclick="window.mwWorldPanel('dogam')">
      <img src="char/ui/ui_ic_dogam.png?v=1" alt="">도감
    </button>
```
→ 로:
```html
    <button class="mw-wb-tabbtn" onclick="window.mwWorldPanel('dogam')">
      <img src="char/ui/ui_ic_stamp.png?v=1" alt="">체크인
    </button>
```

- [ ] **Step 2: 패널 타이틀 문자열 교체**

`mwWorldPanel` 내부(현재):
```js
  const title = kind==='map' ? '지도' : kind==='field' ? '필드 이동' : '도감';
```
→ 로:
```js
  const title = kind==='map' ? '지도' : kind==='field' ? '필드 이동' : '체크인';
```

- [ ] **Step 3: 패널 헤더 아이콘 교체**

`mwWorldPanel`의 `icons` 객체(현재):
```js
    dogam:`<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h11a3 3 0 0 1 3 3v13a2 2 0 0 0-2-2H4z"/><path d="M4 4v14"/></svg>`,
```
> 참고: 이 값은 커밋 `cba187b`에서 이미 `<img ... ui_ic_dogam.png ...>`로 바뀌어 있을 수 있다. 현재 파일 실제 값을 Read로 확인 후, dogam 항목을 아래로 교체한다.
→ 로:
```js
    dogam:`<img src="char/ui/ui_ic_stamp.png?v=1" alt="" style="width:27px;height:27px;image-rendering:pixelated">`,
```

- [ ] **Step 4: 구문 체크**

Run: `node tools/dogam-syntax-check.mjs`
Expected: `OK ...` 종료 0.

- [ ] **Step 5: sw 버전업**

`sw.js`의 `v160` 3곳을 `v161`로(Edit 도구, replace_all).

- [ ] **Step 6: 커밋**

```bash
git add index.html sw.js char/ui/ui_ic_stamp.png
git commit -F <메시지파일>   # "feat(checkin): 도감 탭 → 체크인 리네이밍 + 도장 픽셀 아이콘 (sw v161)"
```

---

### Task 2: 도장 랠리 보상 — 원정 목록 위로 이동 + 픽셀 M코인

**Files:**
- Modify: `index.html` (`mwRenderDogam`: `bonusBar` 조립 ~9742-9782, `root.innerHTML` ~9783-9791)
- Modify: `sw.js` (v161 → v162)

**Interfaces:**
- Consumes: 기존 변수 `homeCard`, `passport`, `bonusBar`, `missionHead`, `tiers`, `next`, `claimed`.
- Produces: 보상바가 홈카드 바로 아래·원정 목록 위에 렌더. 보상 금액 옆 M코인 이미지.

- [ ] **Step 1: 코인 표기 헬퍼를 mwRenderDogam 상단에 추가**

`window.mwRenderDogam = async function () {` 바로 다음 줄에 추가:
```js
  const coin = (sz) => `<img src="char/coin.png?v=2" alt="머피" style="width:${sz||13}px;height:${sz||13}px;image-rendering:pixelated;vertical-align:-2px;flex-shrink:0">`;
```

- [ ] **Step 2: 미션 헤더 보상 문구에 코인 적용**

`missionHead`(next 있을 때) 내부 현재:
```js
          <div style="font-size:11.5px;color:#F5C24B;margin-top:3px">보상 <b>+${amt} 머피</b></div>
```
→ 로:
```js
          <div style="font-size:11.5px;color:#F5C24B;margin-top:3px;display:flex;align-items:center;gap:3px">보상 ${coin(14)}<b>+${amt}</b></div>
```

- [ ] **Step 3: 티어 칩 보상 표기에 코인 적용**

`bonusBar`의 티어 칩 map 현재:
```js
            <div style="font-size:10px;color:${got?'#F5C24B':isNext?'#cfd6e6':'#4a5266'};margin-top:3px">${got?'✓ 받음':'+'+amt}</div>
```
→ 로:
```js
            <div style="font-size:10px;color:${got?'#F5C24B':isNext?'#cfd6e6':'#4a5266'};margin-top:3px;display:flex;align-items:center;justify-content:center;gap:2px">${got?'✓ 받음':coin(11)+'+'+amt}</div>
```

- [ ] **Step 4: root.innerHTML 순서 변경 — bonusBar를 원정 위로**

현재:
```js
    ${homeCard}
    <div style="font-size:12px;color:#8a93a8;margin:0 2px 9px">원정 스탬프 <span style="color:#4a5266">— 다른 센터에 가면 열려요</span></div>
    ${passport||'<div style="color:#4a5266;font-size:12px;text-align:center;padding:14px">등록된 센터가 없어요</div>'}
    ${bonusBar}`;
```
→ 로:
```js
    ${homeCard}
    ${bonusBar}
    <div style="font-size:12px;color:#8a93a8;margin:16px 2px 9px">원정 스탬프 <span style="color:#4a5266">— 다른 센터에 가면 열려요</span></div>
    ${passport||'<div style="color:#4a5266;font-size:12px;text-align:center;padding:14px">등록된 센터가 없어요</div>'}`;
```

- [ ] **Step 5: 구문 체크 → sw v162 → 커밋**

Run: `node tools/dogam-syntax-check.mjs` (Expected: OK)
그 후 `sw.js` v161→v162, 커밋:
```
feat(checkin): 도장 랠리 보상을 원정 목록 위로 이동 + 픽셀 M코인 표시 (sw v162)
```

---

### Task 3: 내 센터 카드 콜드스타트 강화 (미등록 상태)

**Files:**
- Modify: `index.html` (`mwRenderDogam`: `homeCard` 미등록 분기 ~9702-9707)
- Modify: `sw.js` (v162 → v163)

**Interfaces:**
- Consumes: `window.mwPickHome()` (기존 홈센터 선택 함수).
- Produces: 미등록 시 점선 뱃지 플레이스홀더 + 큰 안내 + 혜택 + CTA.

- [ ] **Step 1: 미등록 분기 교체**

`homeCard`의 미등록(else) 분기 현재:
```js
    <div class="mw-panel" style="padding:22px 16px;margin-bottom:14px;text-align:center">
      <div style="font-family:'Galmuri14',sans-serif;font-size:14px;color:#fff;margin-bottom:7px">내 홈 센터를 정해요</div>
      <div style="font-size:12px;color:#8a93a8;margin-bottom:14px;line-height:1.7">매일 도장 찍고 뜨내기에서<br><b style="color:#F5C24B">터줏대감</b>까지 레벨업!</div>
      <button class="mw-btn" style="width:100%" onclick="window.mwPickHome()">홈 센터 정하기</button>
    </div>`;
```
→ 로:
```js
    <div class="mw-panel" style="padding:20px 16px 18px;margin-bottom:14px;text-align:center;position:relative;overflow:hidden">
      <div style="width:66px;height:66px;margin:0 auto 12px;border:3px dashed #2b3350;display:flex;align-items:center;justify-content:center;background:#0e1320">
        <span style="font-family:'Galmuri14',sans-serif;font-size:26px;color:#3b465e">?</span>
      </div>
      <div style="font-family:'Galmuri14',sans-serif;font-size:14px;color:#fff;margin-bottom:8px;line-height:1.5">여기에 <b style="color:#3D7EFF">내 센터</b>가 와요</div>
      <div style="font-size:12px;color:#8a93a8;margin-bottom:6px;line-height:1.7">자주 가는 센터를 등록하면<br>매일 도장 찍고 <b style="color:#F5C24B">뜨내기→터줏대감</b> 레벨업!</div>
      <div style="font-size:10.5px;color:#4a5266;margin-bottom:15px">도장을 모으면 아래 <b style="color:#F5C24B">도장 랠리</b> 보상도 열려요</div>
      <button class="mw-btn" style="width:100%" onclick="window.mwPickHome()">내 센터 등록하기</button>
    </div>`;
```

- [ ] **Step 2: 구문 체크 → sw v163 → 커밋**

Run: `node tools/dogam-syntax-check.mjs` (Expected: OK)
`sw.js` v162→v163, 커밋:
```
feat(checkin): 내 센터 미등록 콜드스타트 강화 (점선 플레이스홀더·안내·CTA) (sw v163)
```

---

### Task 4: 원정 스탬프 압축 (발견 N/M + 내 지역만 펼침)

**Files:**
- Modify: `index.html` (`mwRenderDogam`: `passport` 조립 ~9721-9728, 원정 라벨 ~9789)
- Modify: `sw.js` (v163 → v164)

**Interfaces:**
- Consumes: `regions`(지역별 센터 맵), `byCenter`, `others`, `home`.
- Produces: 지역 아코디언은 홈센터 지역만 `open`, 원정 라벨에 `발견 N/M`.

- [ ] **Step 1: 홈센터 지역 + fallback 계산 (passport 조립 직전에 추가)**

`const passport = Object.keys(regions).sort().map(r => {` 바로 위에 추가:
```js
  const homeRegion = home ? ((home.loc||'').split(/\s+/)[0] || '') : '';
  // 홈 미등록 시: 발견 센터가 가장 많은 지역 하나만 펼침
  let fallbackRegion = '';
  if (!homeRegion) {
    let best = -1;
    Object.keys(regions).forEach(r => {
      const got = regions[r].filter(c => byCenter[c.id]).length;
      if (got > best) { best = got; fallbackRegion = r; }
    });
    if (best <= 0) fallbackRegion = '';   // 발견 0이면 전부 접힘
  }
  const openRegion = homeRegion || fallbackRegion;
```

- [ ] **Step 2: 아코디언 open 조건 변경**

현재:
```js
      <details class="mw-region"${got?' open':''}>
```
→ 로:
```js
      <details class="mw-region"${r===openRegion?' open':''}>
```

- [ ] **Step 3: 원정 라벨에 발견 N/M 추가**

root.innerHTML 조립 직전(또는 passport 계산 후)에 카운트 추가. `const others = ...` 는 이미 존재. passport 아래쪽, root.innerHTML 위에 추가:
```js
  const expDiscovered = others.filter(c => byCenter[c.id]).length;
  const expTotal = others.length;
```
원정 라벨 현재(Task 2에서 margin 16px로 바뀐 상태):
```js
    <div style="font-size:12px;color:#8a93a8;margin:16px 2px 9px">원정 스탬프 <span style="color:#4a5266">— 다른 센터에 가면 열려요</span></div>
```
→ 로:
```js
    <div style="display:flex;align-items:baseline;justify-content:space-between;margin:16px 2px 9px">
      <span style="font-size:12px;color:#8a93a8">원정 스탬프 <span style="color:#4a5266">— 다른 센터에 가면 열려요</span></span>
      <span style="font-size:11px;color:#4a5266;flex-shrink:0">발견 <b style="color:#cfd6e6">${expDiscovered}</b>/${expTotal}</span>
    </div>`;
```
> 주의: 이 `<div>`가 template literal 안의 마지막 요소가 아니므로 끝의 백틱은 붙이지 말고, passport 라인이 그 뒤에 오도록 유지한다. (실제 편집 시 현재 파일의 정확한 문자열을 Read로 확인 후 교체.)

- [ ] **Step 4: 구문 체크 → sw v164 → 커밋**

Run: `node tools/dogam-syntax-check.mjs` (Expected: OK)
`sw.js` v163→v164, 커밋:
```
feat(checkin): 원정 스탬프 압축 — 발견 N/M 요약 + 내 지역만 펼침 (sw v164)
```

---

### Task 5: 상단 요약 3타일 + 섹션 앵커 + 스무스 스크롤

**Files:**
- Modify: `index.html` (`mwRenderDogam`: root.innerHTML 조립부에 타일·앵커 추가)
- Modify: `sw.js` (v164 → v165)

**Interfaces:**
- Consumes: `home`, `distinct`, `next`(다음 미션 `[n,amt,k]` 또는 undefined), `coin(sz)`(Task 2 헬퍼), `tiers`.
- Produces: 3타일(내 센터/원정/다음 보상), 각 섹션 앵커 id(`mw-dg-home`/`mw-dg-rally`/`mw-dg-expedition`), 타일 클릭 시 스무스 스크롤.

- [ ] **Step 1: 타일 HTML 문자열을 root.innerHTML 조립 전에 준비**

root.innerHTML 조립 직전에 추가(`next` 는 이미 존재: 다음 미션 튜플 또는 undefined):
```js
  const homeTileVal = home ? `<b style="color:#fff">${(home.name||'').length>5?home.name.slice(0,5)+'…':home.name}</b>` : `<b style="color:#F5C24B">미정</b>`;
  const nextReward = next ? `${coin(12)}<b style="color:#F5C24B">+${next[1]}</b>` : `<b style="color:#F5C24B">완료</b>`;
  const scroll = id => `document.getElementById('${id}')&&document.getElementById('${id}').scrollIntoView({behavior:'smooth',block:'start'})`;
  const tileCss = 'flex:1;min-width:0;padding:10px 6px;background:#1b2233;border:3px solid #05070c;box-shadow:0 0 0 2px #2b3350;cursor:pointer;text-align:center;font-family:inherit';
  const tileLbl = 'font-size:10px;color:#8a93a8;margin-bottom:5px;white-space:nowrap';
  const tileVal = 'font-size:12px;line-height:1.2;display:flex;align-items:center;justify-content:center;gap:3px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap';
  const tiles = `
    <div style="display:flex;gap:8px;margin:0 2px 14px">
      <div style="${tileCss}" onclick="${scroll('mw-dg-home')}"><div style="${tileLbl}">내 센터</div><div style="${tileVal}">${homeTileVal}</div></div>
      <div style="${tileCss}" onclick="${scroll('mw-dg-expedition')}"><div style="${tileLbl}">원정</div><div style="${tileVal}"><b style="color:#fff">${distinct}</b><span style="color:#8a93a8">곳</span></div></div>
      <div style="${tileCss}" onclick="${scroll('mw-dg-rally')}"><div style="${tileLbl}">다음 보상</div><div style="${tileVal}">${nextReward}</div></div>
    </div>`;
```

- [ ] **Step 2: root.innerHTML에 타일 삽입 + 섹션 앵커 부여**

root.innerHTML을 아래 형태로 교체(FITNESS PASSPORT 헤더 다음에 `${tiles}`, 각 섹션을 앵커 div로 감쌈):
```js
  root.innerHTML = `
    <div style="display:flex;align-items:baseline;justify-content:space-between;margin:2px 2px 12px">
      <span style="font-family:'Galmuri14',sans-serif;font-size:13px;color:#F5C24B;letter-spacing:1px">FITNESS PASSPORT</span>
      <span style="font-size:11px;color:#4a5266">도장 ${checkins.length}개</span>
    </div>
    ${tiles}
    <div id="mw-dg-home" style="scroll-margin-top:8px">${homeCard}</div>
    <div id="mw-dg-rally" style="scroll-margin-top:8px">${bonusBar}</div>
    <div id="mw-dg-expedition" style="scroll-margin-top:8px">
      <div style="display:flex;align-items:baseline;justify-content:space-between;margin:16px 2px 9px">
        <span style="font-size:12px;color:#8a93a8">원정 스탬프 <span style="color:#4a5266">— 다른 센터에 가면 열려요</span></span>
        <span style="font-size:11px;color:#4a5266;flex-shrink:0">발견 <b style="color:#cfd6e6">${expDiscovered}</b>/${expTotal}</span>
      </div>
      ${passport||'<div style="color:#4a5266;font-size:12px;text-align:center;padding:14px">등록된 센터가 없어요</div>'}
    </div>`;
```
> 이 단계는 Task 2·4에서 만든 순서(홈→보상→원정)와 라벨을 앵커 div로 감싸는 최종 형태다. Task 2·4의 원정 라벨/보상 순서 조립과 중복되므로, **이 Step에서 root.innerHTML 전체를 위 블록으로 확정**한다(이전 태스크의 인라인 라벨은 이 블록으로 흡수됨).

- [ ] **Step 3: 구문 체크**

Run: `node tools/dogam-syntax-check.mjs`
Expected: `OK ...` 종료 0.

- [ ] **Step 4: 헤드리스 렌더 스모크(가능 시)**

`bonusBar`/`passport`/`tiles` 문자열이 정의된 변수만 참조하는지 확인하기 위해, 스크래치패드에 mwRenderDogam 본문을 Function으로 감싸 정의되지 않은 식별자 참조가 없는지 정적 확인. 최소한 `node tools/dogam-syntax-check.mjs` 통과 + Read로 `coin`/`distinct`/`next`/`expDiscovered`/`expTotal`/`homeCard`/`bonusBar`/`passport`가 root.innerHTML보다 앞에서 선언됨을 확인.

- [ ] **Step 5: sw v165 → 커밋**

`sw.js` v164→v165, 커밋:
```
feat(checkin): 상단 요약 3타일(내 센터·원정·다음 보상) + 섹션 스무스 스크롤 (sw v165)
```

---

### Task 6: 통합 검증 + 푸시

**Files:** 없음(푸시·검증만)

- [ ] **Step 1: 전체 구문 체크**

Run: `node tools/dogam-syntax-check.mjs` → OK.

- [ ] **Step 2: 푸시**

```bash
git push
```

- [ ] **Step 3: 대표 실앱 확인 요청 (checklist)**

대표에게 실앱 새로고침 후 머피월드 → 체크인 탭에서 확인 요청:
1. 홈 탭이 "체크인" + 도장 아이콘.
2. (홈 미등록 계정) 점선 "?" 플레이스홀더 + "내 센터 등록하기" 크게 보임.
3. 상단 3타일 보이고 탭하면 해당 섹션으로 스크롤.
4. 도장 랠리 보상이 원정 목록 위에 M코인과 함께 보임.
5. 원정 목록이 짧아짐(발견 N/M, 내 지역만 펼침).

---

## Self-Review

**Spec coverage:**
- A. 네이밍(도감→체크인, 아이콘) → Task 1 ✅
- B. 상단 3타일 + 스크롤 → Task 5 ✅
- C. 콜드스타트 강화 → Task 3 ✅
- D. 보상 위로 + M코인 → Task 2 ✅
- E. 원정 압축(발견 N/M, 내 지역만) → Task 4 ✅
- 도장 아이콘 에셋 처리 → 이미 완료(char/ui/ui_ic_stamp.png), Task 1에서 커밋 ✅

**Placeholder scan:** 모든 코드 스텝에 실제 코드 포함. "적절히 처리" 류 없음. ✅

**Type/이름 일관성:**
- `coin(sz)` 헬퍼: Task 2 정의 → Task 5 사용. 두 태스크 순서상 Task 2가 먼저이므로 OK. (subagent 분리 실행 시 Task 5 구현자에게 `coin`이 mwRenderDogam 상단에 이미 있음을 Interfaces에 명시함.)
- 앵커 id: `mw-dg-home`/`mw-dg-rally`/`mw-dg-expedition` — Task 5에서 정의·사용 일치. ✅
- `next` 튜플 형태 `[n,amt,k]` → 타일에서 `next[1]`=amt 사용. 일치. ✅
- `expDiscovered`/`expTotal`: Task 4에서 선언 → Task 5 root.innerHTML에서 사용. Task 5 Step 2가 최종 root.innerHTML을 확정하므로, 선언은 root.innerHTML 앞이어야 함(Task 4 Step 3에서 이미 앞쪽 배치). ✅

**주의(실행 시):** mwRenderDogam은 단일 함수 안에서 Task 2·4·5가 같은 root.innerHTML을 순차 편집한다. Task 5 Step 2가 root.innerHTML 최종형을 확정하므로, Task 2 Step 4·Task 4 Step 3의 인라인 라벨/순서는 Task 5에서 앵커 div로 감싼 최종형에 수렴한다. 순서대로 실행하면 각 중간 커밋도 동작 가능(앵커 없이도 렌더됨).
