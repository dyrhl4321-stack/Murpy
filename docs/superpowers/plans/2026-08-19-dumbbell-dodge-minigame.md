# 덤벨 피하기 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 헬스장 필드에서 혼자 하는 낙하물 피하기 게임을 만들고, 최고점을 명예의 전당 '게임' 탭에 세운다.

**Architecture:** 게임의 **판정 전체를 Firestore·DOM 을 모르는 순수 틱 함수**(`dodgeTick`)로 떼어낸다. 화면은 그 결과를 그리기만 한다. 이 저장소엔 테스트 러너가 없어서, 순수 함수로 떼는 것이 게임 규칙을 검증할 **유일한 방법**이다. 낙하 물체는 Canvas 가 아니라 DOM 으로 굴린다 — 캐릭터가 DOM 레이어 합성이라 Canvas 로 옮기면 캐릭터가 두 벌이 된다.

**Tech Stack:** 단일 `index.html` (바닐라 JS/CSS + Firestore v10.12.0 ES module). 빌드 없음. 테스트 러너 없음.

**Spec:** `docs/superpowers/specs/2026-08-19-dumbbell-dodge-minigame-design.md`

## Global Constraints

- 모든 변경은 `C:\Users\allys\Murpy\index.html` 안에서 일어난다.
- 검증은 셋뿐이다: ①`<script>` 6블록 `node --check` ②순수 함수는 scratchpad node 하네스 ③화면은 대표 실앱 확인.
- **이모지 금지** · **틴트 칩 금지** · 색은 파랑=액션 / 초록=대숲 / **골드=별점·코인**(메달은 대표가 지정한 예외).
- **픽셀 폰트는 머피월드 전용** — 게임 화면은 머피월드 안이므로 `Galmuri` 계열을 쓴다.
- **`sw.js` 는 손대지 않는다.**
- **★다른 창이 헬스장 필드를 만지는 중이다.** `_FIELDS`·`charMove`·`_FIELD_SPOTS`·`_mwPlateHit`·
  `_mwFieldReveal` 을 **읽기만** 한다. `charSetField` 에는 **맨 끝 한 줄만** 붙인다.
- **커밋은 `git add` 와 `git commit` 을 반드시 한 Bash 호출로 묶는다.** 나누면 그 틈에 다른 창이
  인덱스를 덮는다([[feedback_murpy_two_window_git_race]]). 커밋 전 `git diff --stat` 의 **줄 수**를 본다.

**문법검사 명령 (모든 Task 동일):**

```bash
cd /c/Users/allys/Murpy && python - <<'EOF'
import re, subprocess, os, tempfile
src = open('index.html', encoding='utf-8').read(); ok=True
for m in re.finditer(r'<script(?![^>]*\bsrc=)([^>]*)>(.*?)</script>', src, re.S):
    line = src[:m.start()].count('\n')+1; ext='.mjs' if 'module' in m.group(1) else '.js'
    p=os.path.join(tempfile.gettempdir(),'chk_%d%s'%(line,ext)); open(p,'w',encoding='utf-8').write(m.group(2))
    r=subprocess.run(['node','--check',p],capture_output=True,text=True)
    print(('  OK  ' if r.returncode==0 else '  FAIL'),'line',line,ext)
    if r.returncode: ok=False; print(r.stderr[:800])
    os.remove(p)
print('ALL PASS' if ok else 'SYNTAX ERROR')
EOF
```

## File Structure

| 자리 | 무엇 |
|---|---|
| module 블록 (`// ===== 덤벨 피하기 =====` 새 구역) | 튜닝 상수 · 순수 틱 함수 · 화면 · 저장 |
| 패널 HTML (`#hof-panel` 앞) | `#dodge-screen` 오버레이 |
| `charSetField` 맨 끝 | 시작 버튼 표시 한 줄 |
| `HOF_KINDS` | `dodge` 한 줄 + 라벨 `스쿼드 참가`→`참가` |

**게임 코드는 한 구역에 모은다.** 시작·끝 주석이 node 하네스가 블록을 뽑는 표식이다.

---

## Task 1: 순수 게임 규칙 (틱 함수)

게임의 뇌. DOM·Firestore 를 모르므로 **node 로 진짜 테스트할 수 있는 유일한 부분**이다.
여기서 규칙을 잡아두면 화면은 그리기만 하면 된다.

**Files:**
- Modify: `index.html` — module 블록, `// ===== 닉네임 중복 검사 =====` **바로 위**에 새 구역
- Test: `scratchpad/dodge_tick_test.js` (임시, 커밋 안 함)

**Interfaces:**
- Produces:
  - `window.DODGE` — 튜닝 상수 한 곳
  - `window.dodgeNew(seed): State` — `{ t, score, x, alive, items:[], spawnAt, rnd }`
  - `window.dodgeTick(s, dt, targetX): State` — 같은 객체를 갱신해 돌려준다.
    `targetX` = 손가락의 논리 x(0~`DODGE.W`) 또는 `null`(입력 없음)
  - `window._dodgeRnd(s): number` — 0~1. **시드 난수**(테스트가 재현 가능해야 한다)

- [ ] **Step 1: 하네스로 실패를 먼저 본다**

`scratchpad/dodge_tick_test.js` 를 만들고 실행한다. 함수가 없으므로 반드시 실패한다.

```bash
cd /c/Users/allys/AppData/Local/Temp/claude/C--Users-allys/10166e50-3479-4c68-9f73-0340bc46ed9a/scratchpad
cat > dodge_tick_test.js <<'EOF'
const fs = require('fs');
const src = fs.readFileSync('C:/Users/allys/Murpy/index.html', 'utf8');
const m = src.match(/\/\/ ===== 덤벨 피하기[\s\S]*?\/\/ ===== 덤벨 피하기 끝 =====/);
if (!m) { console.log('FAIL: 덤벨 피하기 블록을 못 찾음'); process.exit(1); }
const window = {};
eval(m[0]);
console.log('블록 찾음');
EOF
node dodge_tick_test.js
```

Expected: `FAIL: 덤벨 피하기 블록을 못 찾음` (exit 1)

- [ ] **Step 2: 규칙을 넣는다**

`index.html` module 블록에서 `// ===== 닉네임 중복 검사 =====` 를 찾아 **그 줄 바로 위**에 붙인다.
시작·끝 주석은 **글자 그대로** 넣어야 한다(하네스가 이걸로 블록을 뽑는다).

```js
// ===== 덤벨 피하기 (헬스장 필드 1인 미니게임) =====
// 설계: docs/superpowers/specs/2026-08-19-dumbbell-dodge-minigame-design.md
// ★판정을 DOM·Firestore 를 모르는 순수 함수로 뗀다 — 이 저장소엔 테스트 러너가 없어서
//   게임 규칙을 검증할 방법이 이것뿐이다. 화면은 이 결과를 그리기만 한다.
// ★튜닝 값은 전부 여기 모은다. 재미는 숫자로 못 정하고 대표가 실기기에서 고쳐야 한다 —
//   흩어져 있으면 고칠 때마다 코드를 뒤져야 한다.
window.DODGE = {
  W: 100,             // 게임판 가로(논리 단위, 화면 폭에 비례해서만 그린다)
  PLAYER_W: 12,       // 캐릭터 판정 폭
  PLAYER_SPEED: 62,   // 초당 이동
  FALL0: 34,          // 처음 낙하 속도(초당)
  FALL_UP: 1.9,       // 1분마다 이만큼 곱해진다
  GAP0: 900,          // 처음 생성 간격(ms)
  GAP_MIN: 260,       // 아무리 빨라져도 이보다 촘촘해지지 않는다
  GAP_DOWN: 0.55,     // 1분마다 간격에 곱해진다
  MAX_ITEMS: 12,      // 동시 표시 상한(저사양 폰 보호). 넘으면 생성을 건너뛴다
  ITEM_W: 11,         // 물건 판정 폭
  P_DUMBBELL: 0.5, P_PROTEIN: 0.35,   // 나머지는 치킨
  SC_PROTEIN: 10, SC_CHICKEN: -15, SC_PER_SEC: 1,
  GIFT_AT: 0,         // ★한정 오브젝트 기준점. 0 = 꺼짐. 대표가 몇 판 해본 뒤 정한다
  MAX_SCORE: 9999     // 이보다 큰 점수는 랭킹에서 버린다(조작 방어)
};
// 시드 난수 — 테스트가 재현 가능해야 한다. Math.random 을 쓰면 같은 판을 두 번 못 돌린다.
window._dodgeRnd = function (s) {
  s.rnd = (s.rnd * 1664525 + 1013904223) >>> 0;
  return s.rnd / 4294967296;
};
window.dodgeNew = function (seed) {
  return { t: 0, score: 0, x: window.DODGE.W / 2, alive: true, items: [],
           spawnAt: window.DODGE.GAP0, rnd: (seed >>> 0) || 1, hit: null, face: 'down' };
};
// dt = 지난 ms, targetX = 손가락의 논리 x(0~W) | null(입력 없음)
// ★손가락 추종 방식이다(대표 8-19 확정). 탭투워크는 도착까지 걸리는 시간 때문에
//   피하기가 성립하지 않고, 조이스틱은 손가락→스틱→캐릭터로 한 단계 멀고 화면 아래를 가린다.
//   ★단 순간이동은 안 시킨다 — 최고 속도를 걸어야 "빨리 못 옮기는" 긴장이 남는다.
window.dodgeTick = function (s, dt, targetX) {
  const D = window.DODGE;
  if (!s.alive) return s;
  s.hit = null;
  s.t += dt;
  // 난이도: 1분마다 빨라지고 촘촘해진다
  const mins = s.t / 60000;
  const fall = D.FALL0 * Math.pow(D.FALL_UP, mins);
  const gap = Math.max(D.GAP_MIN, D.GAP0 * Math.pow(D.GAP_DOWN, mins));
  // 이동 — 손가락 쪽으로 가되 한 틱에 갈 수 있는 거리를 넘지 않는다
  if (targetX != null) {
    const want = Math.max(D.PLAYER_W / 2, Math.min(D.W - D.PLAYER_W / 2, targetX));
    const step = D.PLAYER_SPEED * (dt / 1000);
    const d = want - s.x;
    if (Math.abs(d) <= step) s.x = want;
    else { s.x += (d < 0 ? -step : step); }
    if (Math.abs(d) > 0.5) s.face = d < 0 ? 'left' : 'right';
  }
  s.x = Math.max(D.PLAYER_W / 2, Math.min(D.W - D.PLAYER_W / 2, s.x));
  // 생성
  s.spawnAt -= dt;
  if (s.spawnAt <= 0) {
    s.spawnAt += gap;
    if (s.items.length < D.MAX_ITEMS) {
      const r = window._dodgeRnd(s);
      const kind = r < D.P_DUMBBELL ? 'dumbbell' : (r < D.P_DUMBBELL + D.P_PROTEIN ? 'protein' : 'chicken');
      s.items.push({ id: (s.rnd % 100000) + '_' + Math.round(s.t),
                     kind: kind, x: D.ITEM_W / 2 + window._dodgeRnd(s) * (D.W - D.ITEM_W), y: 0 });
    }
  }
  // 낙하 + 충돌. 뒤에서부터 지운다(앞에서 지우면 인덱스가 밀린다)
  for (let i = s.items.length - 1; i >= 0; i--) {
    const it = s.items[i];
    it.y += fall * (dt / 1000);
    const near = Math.abs(it.x - s.x) < (D.PLAYER_W + D.ITEM_W) / 2;
    if (it.y >= 88 && it.y <= 100 && near) {          // 캐릭터 높이대(88~100)에서만 닿는다
      if (it.kind === 'dumbbell') { s.alive = false; s.hit = 'dumbbell'; s.items.splice(i, 1); break; }
      s.score += (it.kind === 'protein') ? D.SC_PROTEIN : D.SC_CHICKEN;
      if (s.score < 0) s.score = 0;                    // 점수는 0 아래로 안 내려간다
      s.hit = it.kind;
      s.items.splice(i, 1);
      continue;
    }
    if (it.y > 110) s.items.splice(i, 1);              // 바닥 밑으로 나간 것은 즉시 버린다
  }
  if (s.alive) s.score += D.SC_PER_SEC * (dt / 1000);
  return s;
};
// ===== 덤벨 피하기 끝 =====
```

- [ ] **Step 3: 규칙을 실제로 돌려 검증한다**

하네스를 아래로 바꾸고 실행한다.

```bash
cd /c/Users/allys/AppData/Local/Temp/claude/C--Users-allys/10166e50-3479-4c68-9f73-0340bc46ed9a/scratchpad
cat > dodge_tick_test.js <<'EOF'
const fs = require('fs');
const src = fs.readFileSync('C:/Users/allys/Murpy/index.html', 'utf8');
const m = src.match(/\/\/ ===== 덤벨 피하기[\s\S]*?\/\/ ===== 덤벨 피하기 끝 =====/);
if (!m) { console.log('FAIL: 블록 못 찾음'); process.exit(1); }
const window = {};
eval(m[0]);
const D = window.DODGE;
let all = true;
const ok = (n, c, e) => { if (!c) { all = false; console.log('  FAIL ' + n + (e !== undefined ? '  got=' + e : '')); } else console.log('  PASS ' + n); };

// 좌우 이동과 벽
let s = window.dodgeNew(1);
window.dodgeTick(s, 100, 0);
ok('손가락 쪽(왼쪽)으로 움직인다', s.x < D.W / 2, s.x);
ok('왼쪽을 보게 된다', s.face === 'left', s.face);
ok('한 틱에 순간이동 안 한다', s.x > 0 + D.PLAYER_W / 2, s.x);
for (let i = 0; i < 40; i++) window.dodgeTick(s, 100, 0);
ok('왼쪽 끝에 붙는다', s.x === D.PLAYER_W / 2, s.x);
for (let i = 0; i < 80; i++) window.dodgeTick(s, 100, D.W);
ok('오른쪽 벽을 안 뚫는다', s.x === D.W - D.PLAYER_W / 2, s.x);
let sNo = window.dodgeNew(1); const x0 = sNo.x;
window.dodgeTick(sNo, 100, null);
ok('입력이 없으면 안 움직인다', sNo.x === x0, sNo.x);

// 생존 점수
s = window.dodgeNew(2);
for (let i = 0; i < 100; i++) window.dodgeTick(s, 100, null);   // 10초
ok('생존 점수가 쌓인다(약 10점)', Math.round(s.score) >= 10, s.score);

// 보충제 = +10, 치킨 = -15, 덤벨 = 즉사 (물건을 직접 놓아 판정만 본다)
const drop = (kind) => {
  const st = window.dodgeNew(3);
  st.items = [{ id: 'x', kind: kind, x: st.x, y: 87 }];
  st.spawnAt = 1e9;                                   // 새로 생성되지 않게
  window.dodgeTick(st, 100, null);
  return st;
};
ok('보충제를 먹으면 +10', Math.round(drop('protein').score) >= 10, drop('protein').score);
ok('치킨을 먹으면 점수가 깎인다', drop('chicken').score === 0, drop('chicken').score);
ok('덤벨을 맞으면 죽는다', drop('dumbbell').alive === false);
ok('덤벨에 맞으면 hit 가 남는다', drop('dumbbell').hit === 'dumbbell');

// 점수는 0 아래로 안 내려간다
let st2 = window.dodgeNew(4); st2.score = 5; st2.spawnAt = 1e9;
st2.items = [{ id: 'y', kind: 'chicken', x: st2.x, y: 87 }];
window.dodgeTick(st2, 100, null);
ok('점수가 음수가 안 된다', st2.score === 0, st2.score);

// 빗나가면 아무 일도 없다
let st3 = window.dodgeNew(5); st3.spawnAt = 1e9;
st3.items = [{ id: 'z', kind: 'dumbbell', x: st3.x + 40, y: 87 }];
window.dodgeTick(st3, 100, null);
ok('빗나간 덤벨은 안 죽인다', st3.alive === true);

// 죽은 뒤에는 아무것도 안 변한다
let st4 = drop('dumbbell'); const sc = st4.score;
window.dodgeTick(st4, 1000, null);
ok('죽은 뒤엔 점수가 안 오른다', st4.score === sc);

// 동시 상한
let st5 = window.dodgeNew(6);
for (let i = 0; i < 600; i++) window.dodgeTick(st5, 50, null);
ok('동시 물체가 상한을 안 넘는다', st5.items.length <= D.MAX_ITEMS, st5.items.length);

// 시간이 갈수록 어려워진다 (같은 시드로 초반/후반 낙하 거리 비교)
let a1 = window.dodgeNew(7); a1.items = [{ id:'a', kind:'protein', x: 0, y: 0 }]; a1.spawnAt = 1e9;
window.dodgeTick(a1, 100, null); const early = a1.items[0].y;
let a2 = window.dodgeNew(7); a2.t = 120000; a2.items = [{ id:'a', kind:'protein', x: 0, y: 0 }]; a2.spawnAt = 1e9;
window.dodgeTick(a2, 100, null); const late = a2.items[0].y;
ok('2분 뒤가 더 빨리 떨어진다', late > early * 2, early + ' -> ' + late);

// 시드가 같으면 같은 판이 나온다
const run = (seed) => { const s = window.dodgeNew(seed); for (let i=0;i<200;i++) window.dodgeTick(s, 50, null); return s.items.map(i=>i.kind).join(','); };
ok('같은 시드 = 같은 판', run(9) === run(9));
console.log(all ? 'ALL PASS' : 'FAILED');
if (!all) process.exit(1);
EOF
node dodge_tick_test.js
```

Expected: 모든 줄 `PASS` + `ALL PASS`

- [ ] **Step 4: 문법검사**

Run: 위 「문법검사 명령」 / Expected: `ALL PASS`

- [ ] **Step 5: 커밋 (한 호출로)**

```bash
cd /c/Users/allys/Murpy && git status --short && git --no-pager diff --stat && git add index.html && git commit -q -F - <<'EOF' && git --no-pager log --oneline -1
feat(dodge): 덤벨 피하기 — 순수 게임 규칙(틱 함수) + 튜닝 상수

DOM·Firestore 를 모르는 순수 함수로 뗐다. 이 저장소엔 테스트 러너가 없어서
게임 규칙을 검증할 방법이 이것뿐이다. 화면은 이 결과를 그리기만 한다.

덤벨=즉사 / 보충제 +10 / 치킨 -15(0 아래로 안 감) / 생존 +1점per초.
난이도는 1분마다 낙하 속도 x1.9, 생성 간격 x0.55(하한 260ms).
동시 물체 12개 상한 — 저사양 폰에서 DOM 이 많으면 끊긴다.

난수는 시드 방식이다. Math.random 이면 같은 판을 두 번 못 돌려 테스트가 안 된다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 2: 게임 화면 + 시작 버튼

에셋 없이 **색 네모**로 먼저 돌린다. 재미는 그림이 아니라 속도·간격에서 나온다.

**Files:**
- Modify: `index.html` — `<div class="panel" id="hof-panel">` **앞**에 `#dodge-screen` 추가
- Modify: `index.html` — Task 1 구역 안(`// ===== 덤벨 피하기 끝 =====` 위)에 화면 코드
- Modify: `index.html` — `charSetField` **맨 끝** 한 줄

**Interfaces:**
- Consumes: `window.dodgeNew` / `window.dodgeTick` / `window.DODGE` / `mwMiniCharHtml` / `getMyCharacter`
- Produces: `window.dodgeOpen()` · `window.dodgeClose()` · `window.dodgeFieldBtn(fieldKey)`

- [ ] **Step 1: 화면 HTML 을 넣는다**

`<div class="panel" id="hof-panel">` 앞(그 위 주석 블록 앞)에 넣는다.

```html
<!-- 덤벨 피하기 (헬스장 필드 1인 미니게임).
     ★필드 걷기 로직을 안 건드리려고 **별도 오버레이**로 만든다 — 헬스장 필드는
       다른 창이 합판 히든 오브젝트를 넣는 중이다. -->
<div id="dodge-screen" style="display:none;position:fixed;inset:0;z-index:2300;background:#05070c;max-width:390px;margin:0 auto;overflow:hidden;touch-action:none;font-family:'Galmuri11',sans-serif">
  <div id="dodge-bg" style="position:absolute;inset:0;background:#0e0f14 center/cover no-repeat;image-rendering:pixelated;opacity:.45"></div>
  <div id="dodge-field" style="position:absolute;inset:0"></div>
  <div style="position:absolute;left:10px;top:10px;z-index:5;font-size:13px;color:#fff;text-shadow:0 1px 3px #000">
    <span id="dodge-score">0</span>
  </div>
  <button onclick="window.dodgeClose()" style="position:absolute;right:10px;top:10px;z-index:5;background:rgba(0,0,0,.45);border:1px solid rgba(255,255,255,.16);border-radius:9px;color:rgba(255,255,255,.7);font-size:11px;font-family:inherit;cursor:pointer;padding:7px 11px">나가기</button>
  <div id="dodge-over" style="display:none;position:absolute;inset:0;z-index:6;background:rgba(5,7,12,.86);flex-direction:column;align-items:center;justify-content:center;gap:14px;padding:24px;text-align:center">
    <div style="font-size:20px;font-weight:800;color:#fff">게임 오버</div>
    <div id="dodge-result" style="font-size:14px;color:#cfd6e6;line-height:1.7"></div>
    <div style="display:flex;gap:9px">
      <button onclick="window.dodgeOpen()" style="background:var(--accent);color:#fff;border:none;border-radius:12px;padding:13px 22px;font-size:14px;font-weight:800;cursor:pointer;font-family:inherit">다시 하기</button>
      <button onclick="window.dodgeClose()" style="background:rgba(255,255,255,.08);color:#cfd6e6;border:none;border-radius:12px;padding:13px 20px;font-size:14px;font-weight:700;cursor:pointer;font-family:inherit">그만</button>
    </div>
  </div>
</div>
```

- [ ] **Step 2: 화면 코드를 넣는다**

`// ===== 덤벨 피하기 끝 =====` **바로 위**에 넣는다.

```js
// ---- 화면 ----
// ★낙하 물체는 DOM 이다. Canvas 로 옮기면 캐릭터를 Canvas 에 다시 그려야 하고,
//   그러면 레이어 합성·조합 규칙이 두 벌이 된다(_charRenderTo 하나로만 그린다는 규칙).
// ★지금은 에셋이 없어 색 네모로 그린다. 재미는 그림이 아니라 속도·간격에서 나오므로
//   먼저 돌려보고 숫자를 잡은 뒤 그림을 붙인다.
window._dodgeKindCss = {
  dumbbell: 'background:#e5484d;border-radius:3px',
  protein:  'background:#3dde7c;border-radius:3px',
  chicken:  'background:#F5C24B;border-radius:50%'
};
window._dodgeS = null; window._dodgeRaf = 0; window._dodgeTargetX = null; window._dodgeLast = 0;
window.dodgeOpen = function () {
  const el = document.getElementById('dodge-screen'); if (!el) return;
  const bg = document.getElementById('dodge-bg');
  if (bg) bg.style.backgroundImage = "url('char/fields/field_gym.png?v=1')";
  document.getElementById('dodge-over').style.display = 'none';
  el.style.display = 'block';
  window._dodgeS = window.dodgeNew(Date.now());
  window._dodgeTargetX = null; window._dodgeLast = 0;
  window._dodgeBind();
  cancelAnimationFrame(window._dodgeRaf);
  window._dodgeRaf = requestAnimationFrame(window._dodgeFrame);
};
window.dodgeClose = function () {
  cancelAnimationFrame(window._dodgeRaf); window._dodgeRaf = 0;
  const el = document.getElementById('dodge-screen'); if (el) el.style.display = 'none';
  window._dodgeS = null;
};
// 조작 — **손가락 추종**(대표 8-19 확정). 화면 아무 데나 눌러 좌우로 움직이면
// 캐릭터가 그 x 를 따라온다. 탭투워크는 도착 시간 때문에 피하기가 성립하지 않고,
// 조이스틱은 한 단계 멀고 화면 아래(떨어지는 걸 보는 자리)를 가린다. 점프는 없다.
window._dodgeBind = function () {
  const el = document.getElementById('dodge-screen'); if (!el || el._bound) return;
  el._bound = true;
  // 화면 x -> 논리 x. 게임판 폭(DODGE.W)은 화면 폭에 비례해서만 쓴다.
  const toLogic = function (clientX) {
    const host = document.getElementById('dodge-field');
    const r = host.getBoundingClientRect();
    return ((clientX - r.left) / (r.width || 1)) * window.DODGE.W;
  };
  const set = function (e) {
    const t = e.touches ? e.touches[0] : e;
    window._dodgeTargetX = toLogic(t.clientX);
    if (e.cancelable) e.preventDefault();
  };
  const off = function () { window._dodgeTargetX = null; };   // 떼면 그 자리에 선다
  el.addEventListener('touchstart', set, { passive: false });
  el.addEventListener('touchmove', set, { passive: false });
  el.addEventListener('touchend', off, { passive: true });
  el.addEventListener('touchcancel', off, { passive: true });
  el.addEventListener('mousedown', set);
  el.addEventListener('mousemove', function (e) { if (e.buttons) set(e); });
  el.addEventListener('mouseup', off);
};
window._dodgeFrame = function (ts) {
  const s = window._dodgeS; if (!s) return;
  if (!window._dodgeLast) window._dodgeLast = ts;
  const dt = Math.min(50, ts - window._dodgeLast);      // 탭 전환 후 한 번에 튀는 것을 막는다
  window._dodgeLast = ts;
  window.dodgeTick(s, dt, window._dodgeTargetX);
  window._dodgePaint(s);
  if (s.alive) window._dodgeRaf = requestAnimationFrame(window._dodgeFrame);
  else window._dodgeEnd(s);
};
window._dodgePaint = function (s) {
  const D = window.DODGE, host = document.getElementById('dodge-field'); if (!host) return;
  const W = host.clientWidth || 360, H = host.clientHeight || 640;
  const px = (v) => (v / D.W) * W;
  let html = '';
  for (const it of s.items) {
    html += `<div style="position:absolute;left:${px(it.x - D.ITEM_W / 2).toFixed(1)}px;top:${(it.y / 100 * H).toFixed(1)}px;`
      + `width:${px(D.ITEM_W).toFixed(1)}px;height:${px(D.ITEM_W).toFixed(1)}px;${window._dodgeKindCss[it.kind]}"></div>`;
  }
  let ch = '';
  try {
    const cfg = window.getMyCharacter ? window.getMyCharacter() : null;
    if (cfg && window.mwMiniCharHtml) ch = window.mwMiniCharHtml(cfg, 72, s.face) || '';
  } catch (e) {}
  html += `<div style="position:absolute;left:${px(s.x).toFixed(1)}px;top:${(0.88 * H).toFixed(1)}px;transform:translate(-50%,-100%)">${ch}</div>`;
  host.innerHTML = html;
  const sc = document.getElementById('dodge-score');
  if (sc) sc.textContent = Math.floor(s.score);
};
window._dodgeEnd = function (s) {
  const score = Math.floor(s.score);
  const r = document.getElementById('dodge-result');
  if (r) r.textContent = score + '점';
  const o = document.getElementById('dodge-over'); if (o) o.style.display = 'flex';
  window.dodgeSave && window.dodgeSave(score);
};
// 헬스장 필드에서만 뜨는 시작 버튼. ★필드에 닿는 것은 이 함수 하나뿐이다.
window.dodgeFieldBtn = function (key) {
  const room = document.getElementById('charworld-room'); if (!room) return;
  let b = document.getElementById('dodge-start');
  if (key !== 'gym') { if (b) b.remove(); return; }
  if (b) return;
  b = document.createElement('button');
  b.id = 'dodge-start'; b.className = 'mw-fieldchip'; b.style.top = '52px';
  b.textContent = '덤벨 피하기';
  b.onclick = function (e) { e.stopPropagation(); window.dodgeOpen(); };
  room.appendChild(b);
};
```

- [ ] **Step 3: `charSetField` 맨 끝에 한 줄 붙인다**

아래 줄을 찾아

```js
  if (bar) bar.querySelectorAll('button').forEach(function (b) { b.classList.toggle('active', b.dataset.f === key); });
```

**그 다음 줄**에 넣는다(다른 창 코드는 건드리지 않는다).

```js
  window.dodgeFieldBtn && window.dodgeFieldBtn(key);   // 헬스장에서만 게임 시작 버튼
```

- [ ] **Step 4: 문법검사 + 커밋 + push (한 호출로)**

Run: 위 「문법검사 명령」 / Expected: `ALL PASS`

```bash
cd /c/Users/allys/Murpy && git status --short && git --no-pager diff --stat && git add index.html && git commit -q -F - <<'EOF' && git push -q origin main && git --no-pager log --oneline -1
feat(dodge): 게임 화면 + 헬스장 필드 시작 버튼 (에셋 전, 색 네모)

별도 오버레이다 — 필드 걷기 로직을 안 건드린다(그 필드는 다른 창이 만지는 중).
필드에 닿는 것은 charSetField 맨 끝 한 줄뿐이다.

낙하 물체는 DOM 이다. Canvas 로 옮기면 캐릭터를 다시 그려야 하고 그러면
레이어 합성·조합 규칙이 두 벌이 된다.

에셋이 없어 색 네모로 돌린다 — 재미는 그림이 아니라 속도·간격에서 나온다.
먼저 해보고 숫자를 잡은 뒤 그림을 붙인다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

**대표 확인:** 헬스장 필드에 버튼이 뜨는지 · 좌우로 끌어 움직이는지 · 빨간(덤벨) 맞으면 끝나는지 ·
초록(보충제) 먹으면 오르는지 · 노랑(치킨) 먹으면 깎이는지 · **속도와 간격이 할 만한지**

---

## Task 3: 최고점 저장 + 명예의 전당 '게임' 탭

**Files:**
- Modify: `index.html` — Task 1 구역 안에 `dodgeSave`
- Modify: `index.html` — `window.HOF_KINDS` 에 `dodge` 한 줄 + `attend` 라벨 축약
- Modify: `index.html` — `loadHofPanel` 의 머리글(`hof-month`) 처리

**Interfaces:**
- Consumes: `window.HOF_KINDS` / `loadHof`
- Produces: `window.dodgeSave(score)`

- [ ] **Step 1: 저장 함수를 넣는다**

```js
// 최고점만 갱신한다(매 판 쓰면 낭비다). plays 는 '재밌는지'를 판정할 유일한 숫자라 매 판 올린다.
window.dodgeSave = async function (score) {
  const user = auth.currentUser || window.currentUser; if (!user) return;
  const n = Math.max(0, Math.min(window.DODGE.MAX_SCORE, Math.floor(score || 0)));
  try {
    const ref = doc(db, 'users', user.uid);
    const snap = await getDoc(ref);
    const cur = ((snap.exists() && snap.data().games) || {}).dodge || {};
    const upd = { 'games.dodge.plays': increment(1), 'games.dodge.lastAt': Date.now() };
    if (n > (cur.best || 0)) upd['games.dodge.best'] = n;
    await updateDoc(ref, upd);
    window._hofCache = null;                 // 랭킹을 다시 읽게 한다(최고점이 바뀌었을 수 있다)
  } catch (e) { console.warn('dodgeSave', e); }
};
```

- [ ] **Step 2: 명예의 전당에 탭을 추가한다**

`window.HOF_KINDS` 의 `attend` 줄을 찾아 라벨을 줄이고 그 **뒤에** `dodge` 를 넣는다.

```js
  attend:  { label: '참가', unit: '회', get: function (u, m) { return ((u.monthly || {})[m] || {}).squad || 0; } },
  // ★게임 탭 (대표 8-19). 나중에 테니스·골프가 붙을 자리다.
  //   ※말이 안 되는 점수는 버린다 — 랭킹은 남에게 보이는 자리라, 큰 수를 한 번 써넣고
  //     영구 점유하는 것을 막는다. 돈이 안 걸려도 이 정도는 한다.
  dodge:   { label: '게임', unit: '점', game: '덤벨 피하기',
             get: function (u) {
               const n = ((u.games || {}).dodge || {}).best || 0;
               return (n > 0 && n <= window.DODGE.MAX_SCORE) ? n : 0;
             } }
```

- [ ] **Step 3: 머리글이 '이번 달'을 안 말하게 한다**

`loadHofPanel` 의 아래 줄을 찾아

```js
  if (mEl) mEl.textContent = (window._hofTab === 'host') ? '누적' : data.month.replace('-', '년 ') + '월';
```

이렇게 바꾼다(게임·스쿼드장은 월 개념이 없다).

```js
  // 스쿼드장(누적)·게임(최고점)은 월 개념이 없다 — '이번 달'이라고 적으면 거짓말이 된다
  const _kd = window.HOF_KINDS[window._hofTab] || {};
  if (mEl) mEl.textContent = _kd.game ? _kd.game
         : (window._hofTab === 'host' ? '누적' : data.month.replace('-', '년 ') + '월');
```

- [ ] **Step 4: 검증 — 기존 렌더 테스트에 게임 탭을 태운다**

`scratchpad/hof_render_test.js` 의 `els` 목록은 그대로 두고, 아래를 파일 끝의 `console.log` 앞에 넣어
실행한다. `window.DODGE` 가 같은 블록에 없으므로 하네스에 상수만 채워준다.

```js
  // 게임 탭
  window.DODGE = { MAX_SCORE: 9999 };
  const gamers = [
    { uid:'g1', nickname:'고수', games:{ dodge:{ best: 320 } } },
    { uid:'g2', nickname:'중수', games:{ dodge:{ best: 120 } } },
    { uid:'g3', nickname:'조작러', games:{ dodge:{ best: 999999 } } },
  ];
  const gr = window._hofRank(gamers, 'dodge', month);
  ok('게임 랭킹 순서', gr.map(r=>r.nick).join(',') === '고수,중수', gr.map(r=>r.nick).join(','));
  ok('말이 안 되는 점수는 버린다', !gr.some(r=>r.nick==='조작러'));
  ok('탭이 5개가 됐다', Object.keys(window.HOF_KINDS).length === 5, Object.keys(window.HOF_KINDS).length);
```

Run: `node hof_render_test.js` / Expected: `ALL PASS`

- [ ] **Step 5: 문법검사 + 커밋 + push (한 호출로)**

```bash
cd /c/Users/allys/Murpy && git status --short && git --no-pager diff --stat && git add index.html && git commit -q -F - <<'EOF' && git push -q origin main && git --no-pager log --oneline -1
feat(dodge): 최고점 저장 + 명예의 전당 '게임' 탭

HOF_KINDS 에 한 줄 더하는 것으로 끝났다 — 랭킹 계산부·패널·팝업이 그대로 재사용된다.
탭이 5개가 되면서 '스쿼드 참가'가 잘려 라벨을 '참가'로 줄였다.

최고점만 갱신하고 plays 는 매 판 올린다 — '재밌는지'를 판정할 유일한 숫자다.
말이 안 되는 점수(MAX_SCORE 초과)는 랭킹에서 버린다. 돈이 안 걸려도 이 정도는 한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Task 4: 에셋 프롬프트 (.txt)

**Files:**
- Create: `바탕화면\머피브랜딩\에셋생성용프롬프터\덤벨피하기_오브젝트_프롬프트.txt`

- [ ] **Step 1: 실제 표시 크기를 먼저 잰다**

Task 2 가 배포된 뒤 화면에서 물체가 몇 px 로 보이는지 확인한다(`ITEM_W 11` × 화면폭/100).
390px 폰이면 약 **43px**. 프롬프트에 이 숫자를 넣는다 — **보이는 크기에서 판정해야 한다**
(필드 아우라 때 141px 원본을 보며 튜닝하다 47px 에서 뭉개져 폐기한 적이 있다).

- [ ] **Step 2: 프롬프트를 쓴다**

물체마다 **완결 블록**으로. 공통 규칙을 각 블록에 **모두 반복해서** 넣는다(대표가 블록째 복붙한다).

각 블록에 반드시 들어갈 것:
- `#00FF00` 형광 초록 **단색 배경** (나노바나나는 투명 배경을 못 그린다)
- 정사각 1:1, 픽셀아트, 외곽선 있는 도트 스타일(우리 캐릭터와 같은 결)
- **정지컷 한 장.** 회전·애니메이션 프레임을 요구하지 않는다(프레임마다 어긋난다)
- 43px 로 줄여도 뭉개지지 않게 **덩어리가 크고 단순하게**

대상 4개: **덤벨(위험)** · **프로틴 보충제 통(좋음)** · **치킨(나쁨)** · **맞았을 때 별 이펙트**

- [ ] **Step 3: 대표에게 전달**

파일 경로를 알려주고, 뽑은 뒤 `char/game/` 에 넣어달라고 한다.
받으면 `_dodgeKindCss` 를 `background:url(...)` 로 바꾸는 것이 교체의 전부다.

---

## 자체 점검 결과

- **스펙 커버리지** — 3장 규칙=Task 1 / 4장 조작·5장 화면=Task 2 / 6장 데이터·7장 게임탭·8장 B=Task 3 /
  9장 에셋=Task 4. **8장 C(한정 오브젝트)는 안 넣었다** — `GIFT_AT` 이 0(꺼짐)으로 나가고
  값이 정해진 뒤에 붙이는 것이 스펙의 결정이다. 값이 정해지면 별도 태스크로 추가한다.
- **이름 일관성** — `DODGE` / `dodgeNew` / `dodgeTick` / `_dodgeRnd` / `dodgeOpen` / `dodgeClose` /
  `dodgeSave` / `dodgeFieldBtn` / `_dodgeS` / `_dodgePaint` / `_dodgeEnd`. Task 간 호출이 일치한다.
- **알려진 빈틈** — `getMyCharacter` 가 `mwMiniCharHtml` 에 넘길 형태를 그대로 주는지 확인하지 않았다.
  Task 2 Step 2 착수 전에 `grep -n "getMyCharacter" index.html` 로 반환값을 보고 맞출 것.
  안 맞으면 `window._charState.character` 를 쓴다(홈 인기 카드가 그렇게 쓴다).
