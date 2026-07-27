# 히든 캐릭터 3종 + 비밀 관찰 파일 연출 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 실제 운동 패턴(체크인)으로 조용히 해금되는 히든 캐릭터 3종(교주·소믈리에·좀비)을, "비밀 관찰 파일 → 판정" 타자기 연출로 지급한다.

**Architecture:** 단일 `index.html`에 (1) 판정 순수함수 `mwEvalHidden`, (2) 해금 저장 `users.hiddenChars`, (3) 연출 `mwHiddenReveal`(오버레이+타자기+도장+스프라이트+카드), (4) 체크인/진입 훅을 추가. 아트는 누끼본을 게임 시트로 추출해 `_CHAR_BODIES`에 등록. 설계: `docs/superpowers/specs/2026-07-27-hidden-characters-design.md`.

**Tech Stack:** Vanilla JS(단일 파일), Firebase Firestore, Canvas/CSS 도트 UI(Galmuri 폰트), Python/PIL(아트 추출), Node(순수로직 테스트).

## Global Constraints

- 단일 파일 `index.html`(약 13,600줄) — CSS/HTML/JS 전부 한 파일. 기존 패턴 따를 것.
- Firebase 모듈 스코프 함수는 onclick에서 접근 불가 → `window.xxx` 전역 등록.
- 에셋/JS 변경 시 `sw.js`의 `murpy-vNNN` 3곳 + `index.html` 2행 `cache-bust: vYYYYMMDDNNN` 올릴 것.
- 공정성 하드룰: 코스메틱 전용(매칭/피드 버프 없음), 해금조건 비공개(체크리스트화 금지), 시간대 강제 아님.
- 스프라이트: 정수배 + NEAREST만. `char/walk.png` 등 base 재수정 금지.
- 문법 검증 = `python <scratchpad>/checkjs.py index.html` (인라인 script 블록 node --check). 커밋 전 필수.
- 캐릭터 id: `cult` / `somm` / `zombie` (전 태스크 동일 사용).
- 작업 후 `git add`+commit+`git push origin main`.
- reduced-motion: 글리치·슬램·흔들림·타자기 생략(텍스트 즉시).

---

### Task 1: 히든 3종 게임 스프라이트 시트 추출 + `_CHAR_BODIES` 등록

**Files:**
- Create: `char/hidden_cult.png`, `char/hidden_somm.png`, `char/hidden_zombie.png`
- Create: `char/extract_hidden.py` (누끼본 → 게임 셀 그리드 리사이즈·정렬)
- Modify: `index.html` `_CHAR_BODIES`(현재 line ~1935)
- Source(읽기): Desktop `…/머피_로고삭제툴_에셋보관/{화요일교 교주 시안,소믈리에,좀비}_clean-nukki.png` (1408×3008, 3열×4행, 셀 469×752, 투명)

**Interfaces:**
- Produces: `_CHAR_BODIES.cult|somm|zombie = { name, src, cw, ch, hidden:true, limited:true }` (다른 태스크가 스프라이트 렌더에 사용). `char/hidden_*.png` = 3열×4행 게임 시트.

- [ ] **Step 1: 추출 스크립트 작성** — `char/extract_hidden.py`. 누끼본(1408×3008)을 정수 축소(예 ÷4 = 352×752 → 셀 117×188)하되, 헬토리/사람 셀 비율과 어긋나지 않게 **셀 폭:높이 비율 유지**. NEAREST. 각 셀 캐릭터의 발바닥선이 셀 하단 일정 위치에 오도록 확인(어긋나면 셀별 크롭→재배치).

```python
# char/extract_hidden.py — 누끼본을 게임 시트로. 정수 축소 + 셀 정렬 검증.
import sys
from PIL import Image
SRC = { 'cult':r'...\화요일교 교주 시안_clean-nukki.png',
        'somm':r'...\소믈리에_clean-nukki.png', 'zombie':r'...\좀비_clean-nukki.png' }
SCALE = 4   # 1408x3008 -> 352x752 (셀 117x188). 필요시 조정.
for key, p in SRC.items():
    im = Image.open(p).convert('RGBA')
    w, h = im.size
    out = im.resize((w//SCALE, h//SCALE), Image.NEAREST)
    out.save(f'char/hidden_{key}.png')
    print(key, out.size, 'cell', out.width//3, out.height//4)
```

- [ ] **Step 2: 실행 + 출력 확인** — `python char/extract_hidden.py`.
  Expected: 3파일 저장, `cell WxH` 출력. 파일이 3열×4행 그리드로 균등한지 셀 크기 정수 확인.

- [ ] **Step 3: 시각 검증** — 각 시트를 마젠타에 합성해 12칸 정렬(발바닥선·크기 일정, 잘림/헤일로 없음) 눈으로 확인.

```python
# scratchpad 검증: 각 char/hidden_*.png 를 마젠타 합성 저장 후 Read로 확인
from PIL import Image
for k in ('cult','somm','zombie'):
    im=Image.open(f'char/hidden_{k}.png').convert('RGBA')
    m=Image.new('RGBA',im.size,(255,0,255,255)); m.alpha_composite(im)
    m.convert('RGB').save(f'<scratchpad>/chk_{k}.png')
```
Expected: 12칸 모두 캐릭터 온전, 발 정렬 일정. 어긋나면 Step1 SCALE/정렬 보정.

- [ ] **Step 4: `_CHAR_BODIES` 등록** — `index.html` line ~1937 `heltori` 항목 다음에 추가(cw/ch = Step2의 셀 크기).

```javascript
  cult:   { name: '요일교 교주',   src: "char/hidden_cult.png?v=1",   cw: 117, ch: 188, hidden: true, limited: true, tag: '히든' },
  somm:   { name: '헬스장 소믈리에', src: "char/hidden_somm.png?v=1",   cw: 117, ch: 188, hidden: true, limited: true, tag: '히든' },
  zombie: { name: '작심삼일 좀비',  src: "char/hidden_zombie.png?v=1", cw: 117, ch: 188, hidden: true, limited: true, tag: '히든' },
```

- [ ] **Step 5: 문법검사 + 커밋** — `python <scratchpad>/checkjs.py index.html` → 문법 오류 0. sw.js 3곳 + cache-bust +1.

```bash
git add char/hidden_cult.png char/hidden_somm.png char/hidden_zombie.png char/extract_hidden.py index.html sw.js
git commit -m "feat(hidden): 히든 3종 스프라이트 추출 + _CHAR_BODIES 등록"
git push origin main
```

---

### Task 2: 판정 순수함수 `mwEvalHidden(checkins, now)`

**Files:**
- Modify: `index.html` (헬퍼 구역, `mwLoadCheckins` 근처 line ~10715)
- Test: `tools/test/test_eval_hidden.mjs` (Create)

**Interfaces:**
- Consumes: checkins 배열 = `[{centerId, day:'YYYYMMDD', at:{toDate()}|Date}, ...]`
- Produces: `window.mwEvalHidden(checkins, now=Date) → ['cult'|'somm'|'zombie' 판정결과]`.
  각 원소 = `{ id:'cult', weekday:'화' }` | `{ id:'somm' }` | `{ id:'zombie' }`. 조건 미충족은 미포함.

- [ ] **Step 1: 실패 테스트 작성** — `tools/test/test_eval_hidden.mjs`. `mwEvalHidden`를 별도 모듈로 두지 않으므로, 테스트는 함수 본문을 복사한 `evalHidden`을 검증(로직 동치성 확인용). 표본 3케이스.

```javascript
// tools/test/test_eval_hidden.mjs  —  node tools/test/test_eval_hidden.mjs
import assert from 'node:assert';
import { evalHidden } from './eval_hidden_ref.mjs';   // Step3에서 생성(함수 본문 사본)
const D = (s)=>({ day:s, at:new Date(s.slice(0,4)+'-'+s.slice(4,6)+'-'+s.slice(6,8)+'T09:00') });
const WEEKS8 = (n, dow) => {           // 최근 8주 안, 특정 요일 n회
  const out=[]; const base=new Date('2026-07-27');   // now
  for(let i=0;i<n;i++){ const d=new Date(base); d.setDate(d.getDate()-i*7); // 매주 같은 요일
    out.push({ centerId:'c1', day:'x', at:new Date(d) }); }
  return out;
};
const now = new Date('2026-07-27T12:00');
// 교주: 최근 8주 화요일 6회(비중 100%)
assert.deepEqual(evalHidden(WEEKS8(6,2), now), [{id:'cult', weekday:'화'}]);
// 소믈리에: 5개 서로 다른 센터
const somm=[1,2,3,4,5].map(i=>({centerId:'c'+i, day:'x', at:new Date('2026-07-01')}));
assert.deepEqual(evalHidden(somm, now), [{id:'somm'}]);
// 좀비: 옛 체크인 → 14일+ 공백 → 최근 복귀
const zom=[D('20260601'), D('20260702')];   // 31일 공백 후 복귀
assert.deepEqual(evalHidden(zom, now), [{id:'zombie'}]);
console.log('ok');
```

- [ ] **Step 2: 테스트 실패 확인** — `node tools/test/test_eval_hidden.mjs`
  Expected: FAIL — `Cannot find module './eval_hidden_ref.mjs'`.

- [ ] **Step 3: 로직 구현(참조 사본 + index.html 동시)** — 아래 함수를 `tools/test/eval_hidden_ref.mjs`(export)와 `index.html`(window 등록) 둘 다에 **동일 본문**으로 넣는다.

```javascript
// 요일 몰림(교주)·센터다양성(소믈리에)·복귀(좀비) 판정. 조건 충족분만 배열로.
window.mwEvalHidden = function (checkins, now) {
  now = now || new Date();
  const out = [];
  const at = (k) => (k.at && k.at.toDate) ? k.at.toDate() : (k.at instanceof Date ? k.at : new Date());
  // --- 교주: 최근 8주(56일) 체크인 ≥6, 최다 요일 비중 ≥0.58 ---
  const cut = new Date(now); cut.setDate(cut.getDate() - 56);
  const recent = checkins.filter(k => at(k) >= cut);
  if (recent.length >= 6) {
    const dow = [0,0,0,0,0,0,0];
    recent.forEach(k => dow[at(k).getDay()]++);
    let mi = 0; for (let i = 1; i < 7; i++) if (dow[i] > dow[mi]) mi = i;
    if (dow[mi] / recent.length >= 0.58) out.push({ id: 'cult', weekday: '일월화수목금토'[mi] });
  }
  // --- 소믈리에: 서로 다른 센터 ≥5 ---
  if (new Set(checkins.map(k => String(k.centerId))).size >= 5) out.push({ id: 'somm' });
  // --- 좀비: day 오름차순, 인접 간격 ≥14일 존재 & 가장 최근 체크인이 그 복귀분 ---
  const days = checkins.map(k => k.day).filter(Boolean).sort();
  if (days.length >= 2) {
    const toD = (s) => new Date(s.slice(0,4), +s.slice(4,6)-1, s.slice(6,8));
    const gap = (toD(days[days.length-1]) - toD(days[days.length-2])) / 86400000;
    if (gap >= 14) out.push({ id: 'zombie' });
  }
  return out;
};
export const evalHidden = window.mwEvalHidden;   // (ref 사본에만; index.html엔 이 줄 제외)
```

- [ ] **Step 4: 테스트 통과 확인** — `node tools/test/test_eval_hidden.mjs`
  Expected: `ok` (3 assert 통과).

- [ ] **Step 5: 문법검사 + 커밋** — `checkjs.py` 0오류.

```bash
git add index.html tools/test/test_eval_hidden.mjs tools/test/eval_hidden_ref.mjs
git commit -m "feat(hidden): mwEvalHidden 판정 로직 + Node 테스트"
git push origin main
```

---

### Task 3: 해금 저장/로드 `hiddenChars`

**Files:**
- Modify: `index.html` — `_charState`(line ~7566), 로드부(`ensureCreditsInit`/users 문서 로드), persist 헬퍼(`_charPersistWardrobe` 근처 ~7569)

**Interfaces:**
- Consumes: Task2 판정결과.
- Produces: `window._charState.hidden = { cult:{weekday}, somm:true, zombie:true }`(맵),
  `window._charPersistHidden(map)` (Firestore `users/{uid}.hiddenChars` 저장),
  `window.mwHasHidden(id)` → bool.

- [ ] **Step 1: `_charState`에 hidden 필드 + 헬퍼 추가** — line ~7566.

```javascript
window._charState = { character: null, wardrobe: [], hidden: {}, ready: false };
window.mwHasHidden = function (id) { return !!(window._charState.hidden && window._charState.hidden[id]); };
window._charPersistHidden = async (map) => {
  if (!window.currentUser) return;
  try { await updateDoc(doc(db, 'users', window.currentUser.uid), { hiddenChars: map }); }
  catch (e) { console.error('hidden save', e); }
};
```

- [ ] **Step 2: users 문서 로드 시 hidden 주입** — users 문서를 읽어 `_charState`를 채우는 곳(캐릭터/워드로브 로드부)에 `window._charState.hidden = data.hiddenChars || {};` 추가.

- [ ] **Step 3: 문법검사 + 수동 확인** — `checkjs.py` 0오류. 앱에서 로그인 후 콘솔 `window._charState.hidden` = `{}`(신규) 또는 기존 맵.

- [ ] **Step 4: 커밋**

```bash
git add index.html
git commit -m "feat(hidden): hiddenChars 저장/로드 + mwHasHidden"
git push origin main
```

---

### Task 4: 타자기 유틸 + 판정서 카드 CSS/구조

**Files:**
- Modify: `index.html` — CSS(`<style>` 내 `.mw-inkstamp` 근처 ~723), JS 유틸 구역

**Interfaces:**
- Produces: `window.mwTypewriter(el, lines, opts) → Promise`(줄 배열을 한 글자씩 출력, `▓` 블록 지원, reduced-motion시 즉시), CSS 클래스 `.mw-dossier`, `.mw-dossier-line`, `.mw-verdict-card`.

- [ ] **Step 1: 타자기 유틸 구현** — 글자당 setInterval, `\n`으로 줄 구분, reduced-motion 즉시.

```javascript
// lines: 문자열 배열. el에 한 글자씩. 완료 시 resolve. speed=글자당 ms.
window.mwTypewriter = function (el, lines, opts) {
  opts = opts || {}; const speed = opts.speed || 45;
  const reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const text = lines.join('\n');
  if (reduce) { el.textContent = text; return Promise.resolve(); }
  el.textContent = '';
  return new Promise(res => {
    let i = 0;
    const t = setInterval(() => {
      el.textContent = text.slice(0, ++i);
      if (opts.tick && i % 2 === 0 && navigator.vibrate) navigator.vibrate(4);
      if (i >= text.length) { clearInterval(t); res(); }
    }, speed);
  });
};
```

- [ ] **Step 2: CSS 추가** — 기밀 파일/판정서 스타일(어두운 종이·Galmuri·검열블록·카드). `.mw-inkstamp.slam` 재활용.

```css
  .mw-dossier { background:#12151d; border:3px solid #05070c; box-shadow:0 0 0 2px #2b3350;
    padding:18px; font-family:'Galmuri11',monospace; color:#cfd6e6; white-space:pre-wrap; line-height:1.8; }
  .mw-dossier .cens { background:#3a4056; color:#3a4056; }   /* ▓ 검열: 배경=글자색으로 가림 */
  .mw-verdict-card { background:#1b2233; border:3px solid #05070c; box-shadow:0 0 0 2px #F5C24B; padding:20px; text-align:center; }
```

- [ ] **Step 3: 시각 확인(스탠드얼론)** — scratchpad에 최소 HTML로 `mwTypewriter`+카드 렌더 스크린샷/수동 확인, 또는 앱 콘솔에서 임시 오버레이 호출로 타이핑 동작 확인.

- [ ] **Step 4: 문법검사 + 커밋** — `checkjs.py` 0오류.

```bash
git add index.html
git commit -m "feat(hidden): 타자기 유틸 + 관찰파일/판정서 CSS"
git push origin main
```

---

### Task 5: 등장 연출 `mwHiddenReveal(result)` + 큐

**Files:**
- Modify: `index.html` — 연출 구역(`mwSeasonCelebrate`/`_mwSeasonModalNext` 근처 ~7592)

**Interfaces:**
- Consumes: Task2 결과 원소, Task1 `_CHAR_BODIES`, Task3 저장, Task4 `mwTypewriter`/CSS.
- Produces: `window.mwHiddenReveal(result)`(1건 연출: 파일→타자기 증거→판정도장→캐릭터 걸어나옴→카드, 완료 시 소유 저장), `window._hiddenQueue`/`window.mwHiddenNext()`(여러 건 순차).

- [ ] **Step 1: 캐릭터별 증거/문구 테이블 + 연출 함수 구현** — 오버레이 생성 → 글리치 → 파일 → `mwTypewriter`로 증거(검열 `▓` 포함) → `.mw-inkstamp.slam` 판정 도장 + `.mw-shake` → 스프라이트(해당 시트 row0 걷기) 등장 + 대사 → 판정서 카드([자랑하기][닫기]). 완료 시 `_charState.hidden[id]` 세팅 + `_charPersistHidden`.

```javascript
window._HIDDEN_META = {
  cult:   (r) => ({ title: r.weekday + '요일교 교주',
    lines: ['관찰기록 #머피-'+Math.floor(1000+Math.random()*9000)+' [기밀]','',
      '대상: '+(window._mwMyNick||'머피'),'관찰기간: 지난 8주','패턴 감지... ▓▓▓▓',
      r.weekday+'요일 · '+r.weekday+'요일 · '+r.weekday+'요일 · '+r.weekday+'요일 · '+r.weekday+'요일'],
    quip: '찾았다. '+r.weekday+'요일에만 오는 자여.' }),
  somm:   () => ({ title: '헬스장 소믈리에',
    lines: ['관찰기록 [기밀]','','대상: '+(window._mwMyNick||'머피'),'헬스장 5곳 시음 확인 ▓▓▓','정착: 실패'],
    quip: '다섯 곳을 떠도는 혀로군.' }),
  zombie: () => ({ title: '작심삼일 좀비',
    lines: ['관찰기록 [기밀]','','대상: '+(window._mwMyNick||'머피'),'사망 확인... 공백 ▓▓일...','부활 감지'],
    quip: '또 돌아왔네. 근성인가 저주인가.' }),
};
window._hiddenQueue = [];
window.mwHiddenReveal = function (r) { window._hiddenQueue.push(r); if (!document.getElementById('mw-hidden')) window.mwHiddenNext(); };
window.mwHiddenNext = async function () {
  const old = document.getElementById('mw-hidden'); if (old) old.remove();
  const r = window._hiddenQueue.shift(); if (!r) return;
  const meta = window._HIDDEN_META[r.id](r), body = window._CHAR_BODIES[r.id];
  const el = document.createElement('div'); el.id = 'mw-hidden';
  el.style.cssText = 'position:fixed;inset:0;z-index:2200;display:flex;align-items:center;justify-content:center;padding:18px;background:rgba(5,7,12,.9);max-width:390px;margin:0 auto';
  el.innerHTML = '<div style="width:100%;max-width:340px">'
    + '<div class="mw-dossier" id="mw-dossier-txt"></div>'
    + '<div id="mw-dossier-stamp" style="text-align:center;margin-top:-10px;height:0"></div>'
    + '<div id="mw-dossier-card" style="display:none"></div></div>';
  document.body.appendChild(el);
  await window.mwTypewriter(document.getElementById('mw-dossier-txt'), meta.lines, { tick: true });
  // 판정 도장
  const st = document.getElementById('mw-dossier-stamp');
  st.style.height = 'auto'; st.innerHTML = '<div class="mw-inkstamp slam" style="margin:14px auto"><i>판정</i></div>';
  el.classList.add('mw-shake'); if (navigator.vibrate) navigator.vibrate(30);
  await new Promise(res => setTimeout(res, 700)); el.classList.remove('mw-shake');
  // 캐릭터 등장 + 카드
  const w = 94, h = Math.round(w * body.ch / body.cw);
  const card = document.getElementById('mw-dossier-card'); card.style.display = 'block';
  card.className = 'mw-verdict-card';
  card.innerHTML = '<div style="width:'+w+'px;height:'+h+'px;margin:0 auto 10px;image-rendering:pixelated;'
    + "background:url('"+body.src+"') no-repeat;background-size:"+(w*3)+'px '+(h*4)+"px\"></div>"
    + '<div style="font-family:\'Galmuri14\',sans-serif;font-size:16px;color:#F5C24B">〈'+meta.title+'〉</div>'
    + '<div style="font-size:12px;color:#cfd6e6;margin:8px 0 4px">'+meta.quip+'</div>'
    + '<div style="font-size:11px;color:#8a93a8;margin-bottom:14px">내 히든: '+meta.title+'</div>'
    + '<button class="mw-btn" style="width:100%" onclick="window.mwHiddenShare(\''+r.id+'\')">자랑하기</button>'
    + '<button onclick="document.getElementById(\'mw-hidden\').remove();window.mwHiddenNext()" style="display:block;margin:10px auto 0;background:none;border:none;color:#4a5266;font-size:12px;cursor:pointer;font-family:inherit">닫기</button>';
  // 소유 저장
  window._charState.hidden = window._charState.hidden || {};
  window._charState.hidden[r.id] = (r.id === 'cult') ? { weekday: r.weekday } : true;
  window._charPersistHidden && window._charPersistHidden(window._charState.hidden);
  window.mwUpdateQuestBadge && window.mwUpdateQuestBadge();
};
window.mwHiddenShare = function (id) {
  const t = '나 머피월드 히든 캐릭터 떴다 ㅋㅋ'; 
  if (navigator.share) navigator.share({ text: t }).catch(()=>{}); else showToast('스크린샷으로 자랑해보세요!');
};
```

- [ ] **Step 2: 앱에서 수동 트리거 확인** — 콘솔에서 `window.mwHiddenReveal({id:'cult',weekday:'화'})` 호출 → 파일→타자기→도장→카드 순서·검열블록·도장 흔들림·캐릭터 표시 확인. `somm`/`zombie`도.

- [ ] **Step 3: 문법검사 + 커밋** — `checkjs.py` 0오류. sw.js/cache-bust +1.

```bash
git add index.html sw.js
git commit -m "feat(hidden): 비밀 관찰 파일 판정 연출 mwHiddenReveal + 큐"
git push origin main
```

---

### Task 6: 훅 연결(체크인 후 + 머피월드 진입) + 중복방지

**Files:**
- Modify: `index.html` — `mwSealCheckin` 성공부(도감 보너스 판정 근처 ~11693 이후), 머피월드 진입(`renderCharSpace`/`mwEnterFx` ~3105)

**Interfaces:**
- Consumes: Task2 `mwEvalHidden`, Task3 `mwHasHidden`, Task5 `mwHiddenReveal`.
- Produces: `window.mwCheckHidden()` — 체크인 로드→판정→미보유분만 연출 큐잉.

- [ ] **Step 1: `mwCheckHidden` 구현** — 최신 체크인 로드(`mwLoadCheckins(true)`) → `mwEvalHidden` → `mwHasHidden(id)` 아닌 것만 `mwHiddenReveal`.

```javascript
window.mwCheckHidden = async function () {
  if (!window.currentUser) return;
  let ck = []; try { ck = await mwLoadCheckins(true); } catch (e) { return; }
  const res = window.mwEvalHidden(ck, new Date());
  res.forEach(r => { if (!window.mwHasHidden(r.id)) window.mwHiddenReveal(r); });
};
```

- [ ] **Step 2: 훅 삽입** — (a) `mwSealCheckin`에서 도장/도감 보너스 연출이 끝난 뒤 `window.mwCheckHidden()` 호출(도감 축하 큐 뒤에 이어지도록 setTimeout 여유). (b) 머피월드 진입(`renderCharSpace` 초기 로드 완료 지점)에 1회 `window.mwCheckHidden()`.

- [ ] **Step 3: 중복방지 확인** — 이미 보유 시 재연출 안 됨(`mwHasHidden` 가드 + Task5가 저장). 앱에서 관리자 테스트 체크인으로 조건 만들어 1회만 뜨는지 확인.

- [ ] **Step 4: 문법검사 + 커밋** — `checkjs.py` 0오류.

```bash
git add index.html
git commit -m "feat(hidden): 체크인/진입 훅 + 미보유분만 연출(mwCheckHidden)"
git push origin main
```

---

### Task 7: 로스터/도감 표시 + 교주 동적 칭호

**Files:**
- Modify: `index.html` — 캐릭터 로스터(`charRenderRoster`/`_charState.wardrobe` 표시부 ~2917), 도감 히든 표기(`mwRenderDogam` ~10723)

**Interfaces:**
- Consumes: Task1 `_CHAR_BODIES`, Task3 `_charState.hidden`.
- Produces: 로스터에서 보유 히든 캐릭터 선택 가능(고정 캐릭터=꾸미기 잠금), 교주 이름은 `hidden.cult.weekday + '요일교 교주'`로 렌더.

- [ ] **Step 1: 로스터에 보유 히든 노출** — 로스터 목록 생성 시 `_charState.hidden`의 키를 `_CHAR_BODIES`로 매핑해 카드 추가. 교주 표시명은 저장된 요일로 조립. 미보유 히든은 도감에 실루엣만(힌트 없음), 로스터엔 미노출.

```javascript
// 로스터 카드 라벨(교주 동적):
function hiddenLabel(id) {
  if (id === 'cult' && window._charState.hidden.cult) return window._charState.hidden.cult.weekday + '요일교 교주';
  return (window._CHAR_BODIES[id] || {}).name || id;
}
```

- [ ] **Step 2: 도감 히든 슬롯** — `mwRenderDogam`에 히든 3종 칸 추가: 보유=캐릭터+이름, 미보유=검은 실루엣+`???`(조건 문구 없음, 하드룰).

- [ ] **Step 3: 선택/착용 확인** — 보유 히든을 로스터에서 고르면 `_charState.character.body='cult'|'somm'|'zombie'`로 적용되고 오버월드/필드에서 그 스프라이트로 걷는지, 꾸미기는 잠금 안내 뜨는지 확인.

- [ ] **Step 4: 문법검사 + 커밋 + 최종 배포** — `checkjs.py` 0오류. sw.js 3곳 + cache-bust 최종 +1.

```bash
git add index.html sw.js
git commit -m "feat(hidden): 로스터/도감 히든 표시 + 교주 동적 칭호"
git push origin main
```

---

## Self-Review 메모
- 스펙 커버리지: 캐릭터/트리거(T1,T2), 저장(T3), 연출 파일→타자기→도장→캐릭터→카드(T4,T5), 훅·중복방지(T6), 로스터·도감·동적칭호(T7), 공정성(도감 조건 비공개=T7 Step2, 코스메틱=고정캐릭터) — 전부 태스크 있음.
- 타입 일관: `cult/somm/zombie` id, `_charState.hidden` 맵(`{weekday}`/true), `mwEvalHidden`→`mwHiddenReveal`→`_charPersistHidden` 체인 일치.
- 열린 리스크: (1) 아트 추출 셀 정렬(T1 Step3 시각검증으로 잡음), (2) 좀비 판정의 '복귀 순간' 정의는 가장 최근-직전 간격만 봄(단순화, 스펙과 일치), (3) 서버 강제·어뷰징은 런칭 전 별도(스펙 5장).
