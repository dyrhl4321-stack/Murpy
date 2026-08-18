# 명예의 전당 (랭킹) 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 활동이 많은 사람이 앱 안에서 눈에 띄도록, 이미 쌓여 있는 카운터를 줄 세워 보여주는 '명예의 전당'을 만든다.

**Architecture:** 새 데이터는 만들지 않는다. `users` 컬렉션을 한 번 읽어 클라이언트에서 4종 랭킹을 계산하고 캐시한다. 계산부(`_hofRank`)는 Firestore 를 모르는 **순수 함수**로 떼어내 node 로 검증한다. 화면은 기존 `.panel` / `.tab-bar` 문법을 재사용하고 새 UI 문법을 만들지 않는다.

**Tech Stack:** 단일 `index.html` (Firestore v10.12.0 ES module + 바닐라 JS/CSS). 빌드 없음. 테스트 러너 없음.

**Spec:** `docs/superpowers/specs/2026-08-19-hall-of-fame-ranking-design.md`

## Global Constraints

- **단일 파일** — 모든 변경은 `C:\Users\allys\Murpy\index.html` 안에서 일어난다.
- **이 저장소엔 테스트 러너가 없다.** 검증은 세 가지뿐이다:
  1. `<script>` 6블록 전부 `node --check` 통과 (아래 명령 그대로)
  2. 순수 함수는 `scratchpad` 에 node 하네스를 만들어 실측
  3. 화면은 push 후 **대표가 실앱에서 확인** (내 로컬 미리보기는 신뢰하지 않는다)
- **이모지 금지.** 아이콘은 머피 전용 라인 SVG.
- **틴트 칩 금지** — 반투명 색면 배지 대신 `background:none` + 테두리 + 글자색.
- **색** — 파랑(`#3D7EFF`)=메인/액션, 초록=대숲 전용, **골드(`#F5C24B`)=별점·코인 전용**. 등수에 골드를 쓰지 않는다.
- **픽셀 폰트는 머피월드 전용.** 이 기능은 전부 Pretendard.
- **인라인 style 을 `''` 로 지우지 말 것** — `cssText` 의 `inset:0` 까지 날아간다.
- **'벙' 이라는 단어 금지** → 스쿼드 / 스쿼드장.
- **`sw.js` 는 손대지 않는다.** `index.html` 은 서비스워커가 network-first 로 받으므로 버전 없이 배포된다.
- **커밋은 작게 자주.** 커밋 직전 `git status` 로 내 것 아닌 변경이 없는지 본다(다른 창이 같은 파일을 만진다).

**문법검사 명령 (모든 Task 에서 동일):**

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

`index.html` 한 파일이지만 손대는 자리는 넷으로 갈린다.

| 자리 | 대략 위치 | 무엇 |
|---|---|---|
| CSS | `.header-icons` 정의 (약 173줄) | 아이콘 간격 |
| 헤더 HTML | `<div class="header">` (약 969줄) | 트로피 버튼 |
| 패널 HTML | `#interest-panel` 근처 (약 2043줄) | `#hof-panel`, `#hof-popup` |
| 로직 | module 블록 (9709줄~) | `_hofRank` / `loadHof` / 패널 렌더 / 팝업 |

**로직은 전부 module 블록에 둔다** — Firestore(`getDocs`/`collection`/`db`)가 거기에만 있다. 순수 계산부(`_hofRank`)도 같은 곳에 둬서 관련 코드가 흩어지지 않게 한다.

---

## Task 1: 랭킹 계산부 (순수 함수) + 제외 상수 통일

랭킹의 뇌. Firestore 를 모르므로 node 로 진짜 테스트할 수 있는 **유일한 부분**이다. 여기서 정확도를 잡아두면 나머지는 그리기만 하면 된다.

**Files:**
- Modify: `index.html` — module 블록 안, `window.mwBumpMonthly` 정의 **바로 위**에 새 블록 추가
- Modify: `index.html` — `loadHomeTrending` 안의 `const EXCLUDE_UID = [...]` 를 새 전역으로 교체
- Test: `scratchpad/hof_rank_test.js` (임시 하네스, 저장소에 커밋하지 않는다)

**Interfaces:**
- Produces:
  - `window.HOF_EXCLUDE_UID: string[]`
  - `window.HOF_MONTH(): string` — `"2026-08"` 형식. 관리자 시즌 실험실을 타지 않는다
  - `window.HOF_KINDS: { [kind]: { label: string, unit: string, get(u, month): number } }` — kind 는 `'feed' | 'checkin' | 'host' | 'attend'`
  - `window._hofRank(users, kind, month): Array<{ uid, nick, n, rank }>` — 내림차순, 동점은 닉네임순, `rank` 는 1부터
  - `window._hofMyRank(rows, uid): { rank, n } | null`

- [ ] **Step 1: 하네스로 실패를 먼저 본다**

`scratchpad` 에 `hof_rank_test.js` 를 만든다. `index.html` 에서 `_hofRank` 블록을 정규식으로 뽑아 실행한다 — 지금은 함수가 없으므로 반드시 실패한다.

```bash
cd /c/Users/allys/AppData/Local/Temp/claude/C--Users-allys/10166e50-3479-4c68-9f73-0340bc46ed9a/scratchpad
cat > hof_rank_test.js <<'EOF'
const fs = require('fs');
const src = fs.readFileSync('C:/Users/allys/Murpy/index.html', 'utf8');
const m = src.match(/\/\/ ===== 명예의 전당[\s\S]*?\/\/ ===== 명예의 전당 끝 =====/);
if (!m) { console.log('FAIL: 명예의 전당 블록을 못 찾음'); process.exit(1); }
const window = {};
// mwSeasonKey 는 앱 함수라 하네스에서 대신 채운다(계산부가 이것만 참조한다)
window.mwSeasonKey = (d) => d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0');
eval(m[0]);

const M = '2026-08';
const users = [
  { uid: 'a', nickname: '가나', monthly: { '2026-08': { feed: 10, checkin: 2, squad: 1 } }, hostStats: { completed: 3 } },
  { uid: 'b', nickname: '나나', monthly: { '2026-08': { feed: 42, checkin: 0 } } },
  { uid: 'c', nickname: '다나', monthly: { '2026-08': { feed: 10 } } },
  { uid: 'd', nickname: '라나', monthly: { '2026-07': { feed: 99 } } },          // 지난달만 → 제외
  { uid: 'e', nickname: '마나', monthly: { '2026-08': { feed: 5 } }, deleted: true },  // 탈퇴 → 제외
  { uid: '3ojRNNyRutYE4IDQn2GrJDcXz0Q2', nickname: '패수현', monthly: { '2026-08': { feed: 999 } } }, // 대표 → 제외
  { uid: 'f', monthly: { '2026-08': { feed: 7 } } },                              // 닉네임 없음 → 제외
];
let all = true;
const eq = (name, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  if (!ok) all = false;
  console.log((ok ? '  PASS ' : '  FAIL ') + name + (ok ? '' : '\n    got  ' + JSON.stringify(got) + '\n    want ' + JSON.stringify(want)));
};

const feed = window._hofRank(users, 'feed', M);
eq('인증 순서(동점은 닉네임순)', feed.map(r => r.uid), ['b', 'a', 'c']);
eq('인증 등수', feed.map(r => r.rank), [1, 2, 3]);
eq('인증 값', feed.map(r => r.n), [42, 10, 10]);

const host = window._hofRank(users, 'host', M);
eq('스쿼드장은 월과 무관', host.map(r => r.uid), ['a']);

eq('내 순위', window._hofMyRank(feed, 'c'), { rank: 3, n: 10 });
eq('목록에 없으면 null', window._hofMyRank(feed, 'zzz'), null);
eq('제외 상수', window.HOF_EXCLUDE_UID.length, 2);
console.log(all ? 'ALL PASS' : 'FAILED');
EOF
node hof_rank_test.js
```

Expected: `FAIL: 명예의 전당 블록을 못 찾음` (exit 1)

- [ ] **Step 2: 계산부를 넣는다**

`index.html` 의 module 블록에서 `window.mwBumpMonthly = async function (axis) {` 를 찾아 **그 줄 바로 위**에 아래를 통째로 붙인다. 시작·끝 주석은 위 하네스가 블록을 뽑는 표식이므로 **글자 그대로** 넣어야 한다.

```js
// ===== 명예의 전당 (랭킹) — 순수 계산부 =====
// ★Firestore 를 모른다. 넘겨받은 배열만 본다 — 그래야 node 로 검증할 수 있다.
//   설계: docs/superpowers/specs/2026-08-19-hall-of-fame-ranking-design.md
// 대표 본인 계정 2개는 모든 랭킹·인기에서 뺀다. 운영자가 1등이면 유저에겐 벽이다.
// ★홈 '지금 인기'(loadHomeTrending)도 이 상수를 쓴다. 두 벌이 되면 한쪽만 고치는 사고가 난다.
window.HOF_EXCLUDE_UID = ['3ojRNNyRutYE4IDQn2GrJDcXz0Q2', 'h0I8ms36owTByTACh6gSw3sgCrf1'];
// ★mwSeasonKey() 를 **인자 없이** 부르면 관리자 시즌 실험실 오버라이드를 탄다.
//   랭킹이 그걸 타면 대표가 시즌을 실험하는 동안 전 유저의 기준 달이 같이 바뀐다.
window.HOF_MONTH = function () { return window.mwSeasonKey(new Date()); };
window.HOF_KINDS = {
  feed:    { label: '인증',    unit: '회', get: function (u, m) { return ((u.monthly || {})[m] || {}).feed || 0; } },
  checkin: { label: '체크인',  unit: '회', get: function (u, m) { return ((u.monthly || {})[m] || {}).checkin || 0; } },
  // ★스쿼드장만 월 구분이 없다(hostStats 는 누적). 스펙 9-(4) 참고 — 지금은 그대로 간다.
  host:    { label: '스쿼드장', unit: '회', get: function (u) { return (u.hostStats || {}).completed || 0; } },
  attend:  { label: '스쿼드 참가', unit: '회', get: function (u, m) { return ((u.monthly || {})[m] || {}).squad || 0; } }
};
// 줄 세우기. 0회·탈퇴·닉네임 없음·대표 계정은 뺀다.
// 동점은 **닉네임 가나다순** — 무작위면 볼 때마다 순서가 바뀌어 등수가 신뢰를 잃는다.
window._hofRank = function (users, kind, month) {
  const def = window.HOF_KINDS[kind]; if (!def) return [];
  return (users || [])
    .filter(function (u) {
      return u && u.nickname && !u.deleted && !u.isAnonymous
        && window.HOF_EXCLUDE_UID.indexOf(u.uid) < 0
        && def.get(u, month) > 0;
    })
    .map(function (u) { return { uid: u.uid, nick: u.nickname, n: def.get(u, month) }; })
    .sort(function (a, b) { return (b.n - a.n) || String(a.nick).localeCompare(String(b.nick), 'ko'); })
    .map(function (r, i) { r.rank = i + 1; return r; });
};
// 내 줄. 10위 밖이어도 화면 맨 아래에 고정해서 보여주려고 따로 뽑는다.
window._hofMyRank = function (rows, uid) {
  if (!uid) return null;
  for (let i = 0; i < (rows || []).length; i++) if (rows[i].uid === uid) return { rank: rows[i].rank, n: rows[i].n };
  return null;
};
// ===== 명예의 전당 끝 =====
```

- [ ] **Step 3: 하네스를 다시 돌린다**

Run: `node hof_rank_test.js` (scratchpad 에서)
Expected: 모든 줄 `PASS` + 마지막 줄 `ALL PASS`

- [ ] **Step 4: 홈 '지금 인기'가 같은 상수를 쓰게 한다**

`loadHomeTrending` 안의 아래 4줄(주석 3줄 + const 1줄)을 찾아 지운다.

```js
    //   ★uid 로 건다(대표가 8-18 에 확인해 줌: 패수현 / 김현수). 닉네임으로 걸면
    //     앱에 중복 닉네임 검사가 없어서 남이 같은 닉을 만들면 그 사람까지 같이 빠진다.
    const EXCLUDE_UID = ['3ojRNNyRutYE4IDQn2GrJDcXz0Q2', 'h0I8ms36owTByTACh6gSw3sgCrf1'];
```

그리고 같은 함수 안 **두 곳**의 `EXCLUDE_UID.indexOf(u.uid) < 0` 를 `window.HOF_EXCLUDE_UID.indexOf(u.uid) < 0` 로 바꾼다. (`grep -n "EXCLUDE_UID" index.html` 로 남은 것이 없는지 확인 — `window.HOF_EXCLUDE_UID` 정의 1곳과 사용 2곳, 총 3곳만 남아야 한다)

- [ ] **Step 5: 문법검사**

Run: 위 「문법검사 명령」
Expected: 6줄 전부 `OK` + `ALL PASS`

- [ ] **Step 6: 커밋**

```bash
cd /c/Users/allys/Murpy && git status --short
git add index.html
git commit -m "feat(hof): 랭킹 계산부 (순수 함수) + 제외 상수 통일

users 배열만 보고 4종 랭킹을 줄 세운다. Firestore 를 모르므로 node 로 검증했다.
0회·탈퇴·닉네임없음·대표 계정 2개를 뺀다. 동점은 닉네임 가나다순.

★HOF_MONTH 는 mwSeasonKey 에 **인자를 준다** — 인자 없이 부르면 관리자
  시즌 실험실 오버라이드를 타서, 대표가 시즌을 실험하는 동안 전 유저의
  랭킹 기준 달이 같이 바뀐다.

홈 '지금 인기'의 제외 목록도 이 상수를 보게 합쳤다(두 벌이면 한쪽만 고치는 사고가 난다).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 2: 데이터 로더 + 캐시

`users` 를 한 번 읽어 Task 1 의 계산부에 넘긴다.

**Files:**
- Modify: `index.html` — Task 1 블록의 `// ===== 명예의 전당 끝 =====` **바로 위**에 추가

**Interfaces:**
- Consumes: `window._hofRank`, `window.HOF_MONTH`
- Produces: `window.loadHof(force?): Promise<{ month, rows: { feed, checkin, host, attend } }>` — 실패하면 빈 rows 를 돌려준다(화면이 안 깨지게)

- [ ] **Step 1: 로더를 넣는다**

```js
// users 한 번 읽어 4종을 한꺼번에 계산한다. 세션 캐시 10분.
// ★사람이 500명쯤 되면 여기가 무거워진다. 그때는 상위 20명만 담은 집계 문서(stats/hof)로
//   바꿀 것 — 지금(46명)은 한 번 읽어도 무시할 수준이고, 집계 문서는 쓰는 쪽이 더 복잡하다.
window._hofCache = null;
window.loadHof = async function (force) {
  const now = Date.now();
  if (!force && window._hofCache && now - window._hofCache.at < 600000) return window._hofCache;
  const month = window.HOF_MONTH();
  let users = [];
  try {
    const qs = await getDocs(collection(db, 'users'));
    users = qs.docs.map(function (d) { return Object.assign({ uid: d.id }, d.data()); });
  } catch (e) { console.warn('hof load', e); }
  const rows = {};
  Object.keys(window.HOF_KINDS).forEach(function (k) { rows[k] = window._hofRank(users, k, month); });
  window._hofCache = { at: now, month: month, rows: rows };
  return window._hofCache;
};
```

- [ ] **Step 2: 문법검사**

Run: 위 「문법검사 명령」 / Expected: `ALL PASS`

- [ ] **Step 3: 브라우저 콘솔로 실측** (대표에게 부탁하지 않고 내가 확인할 수 없는 유일한 항목)

push 후 `murpy.app` 콘솔에서 `await loadHof()` 를 실행해 `rows.feed[0]` 이 실제 사람인지 본다. **이 단계는 대표에게 부탁한다** — 로그인이 필요해 자동화가 막혀 있다.

- [ ] **Step 4: 커밋**

```bash
cd /c/Users/allys/Murpy && git status --short
git add index.html
git commit -m "feat(hof): 랭킹 데이터 로더 + 10분 캐시

users 를 한 번 읽어 4종을 한꺼번에 계산한다. 실패해도 빈 목록을 돌려
화면이 안 깨지게 한다. 500명 전환 지점을 주석으로 남겼다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 3: 명예의 전당 패널

화면. 여기까지 하면 **눈에 보이는 것이 나온다.**

**Files:**
- Modify: `index.html` — `<div class="panel" id="interest-panel">` **바로 위**에 패널 HTML 추가
- Modify: `index.html` — `function openPanel(id)` 안 `if (id==='blocked-panel'...)` 줄 **다음**에 한 줄 추가
- Modify: `index.html` — module 블록, Task 2 로더 **아래**에 렌더 함수 추가

**Interfaces:**
- Consumes: `window.loadHof`, `window.HOF_KINDS`, `window._hofMyRank`, 기존 `openUserProfile(uid, nick, photo)`
- Produces: `window.loadHofPanel()`, `window.hofTab(kind)`

- [ ] **Step 1: 패널 HTML 을 넣는다**

```html
<!-- 명예의 전당 — 활동이 많은 사람이 눈에 띄는 유일한 자리.
     ★새 UI 문법을 만들지 않는다: .panel / .panel-header / .panel-body / .tab-bar / .tab-btn 재사용.
     설계 = docs/superpowers/specs/2026-08-19-hall-of-fame-ranking-design.md -->
<div class="panel" id="hof-panel">
  <div class="panel-header">
    <button class="back-btn" onclick="closePanel('hof-panel')">←</button>
    <span style="font-weight:700;font-size:16px">명예의 전당</span>
    <span id="hof-month" style="margin-left:auto;font-size:11.5px;color:rgba(255,255,255,0.4)"></span>
  </div>
  <div style="padding:10px 16px 0">
    <div class="tab-bar" id="hof-tabs"></div>
  </div>
  <div class="panel-body" id="hof-list"></div>
</div>
```

- [ ] **Step 2: 패널을 열 때 데이터를 채우게 한다**

`openPanel` 안, `if (id==='blocked-panel' && window.loadBlockedList) window.loadBlockedList();` 줄 **바로 아래**에 추가한다.

```js
  if (id==='hof-panel') { window.loadHofPanel && window.loadHofPanel(); }
```

- [ ] **Step 3: 렌더 함수를 넣는다**

module 블록, Task 2 의 `loadHof` 아래·`// ===== 명예의 전당 끝 =====` 위에 넣는다.

```js
window._hofTab = 'feed';
window.hofTab = function (kind) { window._hofTab = kind; window.loadHofPanel(); };
window.loadHofPanel = async function () {
  const listEl = document.getElementById('hof-list'); if (!listEl) return;
  const tabsEl = document.getElementById('hof-tabs');
  const esc = function (s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); };
  // 탭 줄은 데이터를 기다리지 않고 먼저 그린다(빈 화면이 덜 어색하다)
  if (tabsEl) {
    tabsEl.innerHTML = Object.keys(window.HOF_KINDS).map(function (k) {
      const on = k === window._hofTab;
      return '<button class="tab-btn" onclick="window.hofTab(\'' + k + '\')" style="'
        + (on ? 'background:var(--accent);color:#fff;font-weight:800' : '') + '">'
        + '<span>' + window.HOF_KINDS[k].label + '</span></button>';
    }).join('');
  }
  listEl.innerHTML = '<div style="text-align:center;padding:34px;color:rgba(255,255,255,.35);font-size:13px">불러오는 중…</div>';
  const data = await window.loadHof();
  const mEl = document.getElementById('hof-month');
  if (mEl) mEl.textContent = (window._hofTab === 'host') ? '누적' : data.month.replace('-', '년 ') + '월';
  const kind = window._hofTab, def = window.HOF_KINDS[kind], rows = data.rows[kind] || [];
  const myUid = (window.currentUser || {}).uid || '';
  if (!rows.length) {
    listEl.innerHTML = '<div style="text-align:center;padding:40px 24px">'
      + '<div style="font-size:13.5px;font-weight:700;color:rgba(255,255,255,.75);margin-bottom:5px">이번 달은 아직 비어 있어요</div>'
      + '<div style="font-size:12px;color:rgba(255,255,255,.35)">첫 주인공이 되어보세요</div></div>';
    return;
  }
  // 등수는 **색이 아니라 크기·굵기**로 구분한다(골드는 별점·코인 전용).
  const row = function (r, me) {
    const big = r.rank <= 3;
    return '<div onclick="openUserProfile(\'' + r.uid + '\',\'' + esc(r.nick).replace(/'/g, '') + '\',\'\')"'
      + ' style="display:flex;align-items:center;gap:12px;padding:13px 16px;cursor:pointer;'
      + (me ? 'background:rgba(61,126,255,0.07);border-top:1px solid rgba(255,255,255,0.09)' : 'border-bottom:1px solid rgba(255,255,255,0.05)') + '">'
      + '<span style="width:26px;flex-shrink:0;text-align:center;font-size:' + (big ? '17px' : '13px')
      + ';font-weight:' + (big ? '900' : '600') + ';color:' + (big ? '#fff' : 'rgba(255,255,255,0.4)') + '">' + r.rank + '</span>'
      + '<span style="flex:1;min-width:0;font-size:14px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
      + esc(r.nick) + (me ? ' <span style="font-size:11px;font-weight:600;color:var(--accent)">나</span>' : '') + '</span>'
      + '<span style="flex-shrink:0;font-size:13.5px;font-weight:800">' + r.n + '<span style="font-size:11px;font-weight:600;color:rgba(255,255,255,0.45)">' + def.unit + '</span></span>'
      + '</div>';
  };
  let html = rows.slice(0, 10).map(function (r) { return row(r, r.uid === myUid); }).join('');
  // 10위 밖이면 내 줄을 맨 아래에 붙인다 — 내 등수가 보여야 "한 칸만 올리면 되는데"가 생긴다
  const mine = window._hofMyRank(rows, myUid);
  if (mine && mine.rank > 10) html += row({ uid: myUid, nick: (window.currentUser || {}).nickname || '나', n: mine.n, rank: mine.rank }, true);
  listEl.innerHTML = html;
};
```

- [ ] **Step 4: 문법검사**

Run: 위 「문법검사 명령」 / Expected: `ALL PASS`

- [ ] **Step 5: 커밋**

```bash
cd /c/Users/allys/Murpy && git status --short
git add index.html
git commit -m "feat(hof): 명예의 전당 패널 (서브탭 4종 + 내 순위 고정)

기존 .panel / .tab-bar 문법을 그대로 쓴다 — 새 UI 문법을 만들지 않는다.
상위 10명 + 10위 밖이면 내 줄을 맨 아래에 붙인다.
등수는 색이 아니라 숫자 크기·굵기로 구분한다(골드는 별점·코인 전용).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 4: 헤더 트로피 (들어가는 문)

Task 3 까지는 **갈 길이 없다.** 이 태스크가 문을 연다.

**Files:**
- Modify: `index.html` — `.header-icons` CSS (약 173줄)
- Modify: `index.html` — 헤더의 종(Bell) `</div>` 다음, `<!-- Login btn -->` 앞

- [ ] **Step 1: 아이콘 간격을 줄인다**

`.header-icons { display: flex; gap: 16px; align-items: center; }` 를 아래로 바꾼다.

```css
  /* ★아이콘이 5개가 되면서 gap 16 이면 360px 폰(갤럭시)에서 1px 넘친다.
     12 로 줄이면 16px 여유가 생긴다. 실측: 로고+글자 93px + 아이콘 5개 228px = 321px / 여유 320px */
  .header-icons { display: flex; gap: 12px; align-items: center; }
```

- [ ] **Step 2: 트로피 버튼을 넣는다**

`<!-- Bell icon -->` 블록의 닫는 `</div>` 다음 줄, `<!-- Login btn -->` 앞에 넣는다.

```html
    <!-- 명예의 전당 (대표 8-18) — 어느 탭에서든 항상 갈 수 있어야 한다.
         ★배지를 달지 않는다. 하트·톡·종은 "나한테 뭔 일이 생겼다"라 배지가 의미 있지만
           트로피는 "내가 보러 가는 곳"이다. 여기까지 빨간 점을 달면 진짜 신호 셋의 무게가 떨어진다. -->
    <div onclick="openPanel('hof-panel')" style="display:flex;align-items:center;justify-content:center;padding:6px;border-radius:8px;cursor:pointer">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" opacity="0.7">
        <path d="M7 4h10v6a5 5 0 0 1-10 0z"/><path d="M17 5h2.5a2.5 2.5 0 0 1 0 5H17"/><path d="M7 5H4.5a2.5 2.5 0 0 0 0 5H7"/><path d="M12 15v3"/><path d="M8.5 21h7"/><path d="M10 18h4l.6 3h-5.2z"/>
      </svg>
    </div>
```

- [ ] **Step 3: 문법검사**

Run: 위 「문법검사 명령」 / Expected: `ALL PASS`

- [ ] **Step 4: 커밋 + push (여기서 대표 확인을 받는다)**

```bash
cd /c/Users/allys/Murpy && git status --short
git add index.html
git commit -m "feat(hof): 헤더 트로피 + 아이콘 간격 16->12

아이콘이 5개가 되면서 360px 폰에서 1px 넘쳐 간격만 줄였다.
트로피에는 배지를 달지 않는다 — '보러 가는 곳'이지 '일이 생긴 곳'이 아니다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push origin main
```

**대표 확인 항목:** ①헤더가 한 줄로 유지되는지(특히 갤럭시) ②트로피를 누르면 명예의 전당이 뜨는지 ③4개 탭이 각각 사람을 보여주는지 ④본인(패수현/김현수)이 목록에 없는지

---

## Task 5: 홈 한 줄

트로피가 *언제든 가는 문*이라면 이건 *지금 가고 싶게 만드는 것*이다.

**Files:**
- Modify: `index.html` — `<div id="home-live-bar" ...></div>` 다음 줄
- Modify: `index.html` — module 블록, Task 3 렌더 함수 아래

**Interfaces:**
- Consumes: `window.loadHof`
- Produces: `window.loadHofLine()`

- [ ] **Step 1: 자리를 만든다**

`<div id="home-live-bar" style="display:none;margin:12px 16px 0"></div>` **바로 다음 줄**에 넣는다.

```html
  <!-- 명예의 전당 한 줄 (대표 8-18). 카드가 아니라 한 줄이라 피드를 밀어내지 않는다.
       ★핵심은 1위가 아니라 **내 순위**다. 1위만 보이면 남 얘기라 안 누른다. -->
  <div id="home-hof-line" style="display:none;margin:10px 16px 0"></div>
```

- [ ] **Step 2: 그리는 함수를 넣는다**

```js
// 홈 한 줄. 이번 달 인증 1위 + 내 순위.
window.loadHofLine = async function () {
  const el = document.getElementById('home-hof-line'); if (!el) return;
  const data = await window.loadHof();
  const rows = data.rows.feed || [];
  if (!rows.length) { el.style.display = 'none'; return; }
  const esc = function (s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); };
  const mine = window._hofMyRank(rows, (window.currentUser || {}).uid || '');
  const mineTxt = mine ? ' · 내 순위 <b style="color:#fff">' + mine.rank + '위</b>' : '';
  el.style.display = '';
  el.innerHTML = '<div onclick="openPanel(\'hof-panel\')" style="display:flex;align-items:center;gap:8px;padding:11px 14px;'
    + 'border:1px solid rgba(255,255,255,0.09);border-radius:12px;cursor:pointer;font-size:12.5px;color:rgba(255,255,255,0.6)">'
    + '<span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
    + '이번 달 인증 1위 <b style="color:#fff">' + esc(rows[0].nick) + '</b>' + mineTxt + '</span>'
    + '<span style="flex-shrink:0;color:rgba(255,255,255,0.3)">›</span></div>';
};
```

- [ ] **Step 3: 홈에 들어올 때 부른다**

`goPage` 안의 아래 줄을 찾아

```js
  if (name === 'home') { if (window.renderFeedFilterBar) window.renderFeedFilterBar(); if (window.renderStreakUI) window.renderStreakUI(); }
```

이렇게 바꾼다.

```js
  if (name === 'home') { if (window.renderFeedFilterBar) window.renderFeedFilterBar(); if (window.renderStreakUI) window.renderStreakUI(); if (window.loadHofLine) window.loadHofLine(); }
```

- [ ] **Step 4: 문법검사 + 커밋**

Run: 위 「문법검사 명령」 / Expected: `ALL PASS`

```bash
cd /c/Users/allys/Murpy && git status --short
git add index.html
git commit -m "feat(hof): 홈 라이브바 아래 한 줄 (1위 + 내 순위)

카드가 아니라 한 줄이라 피드를 밀어내지 않는다.
★핵심은 1위가 아니라 내 순위다 — 1위만 보이면 남 얘기라 안 누른다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 6: 스쿼드 탭 '인기 스쿼드' 섹션

명예의 전당에 넣지 않는다 — 나머지 넷은 *사람*이고 목적이 **자랑**인데 이건 *스쿼드*고 목적이 **참가**다.

**Files:**
- Modify: `index.html` — `window.renderSquadPage` 안, `root.innerHTML = rows.map(...)` **직전**

**Interfaces:**
- Consumes: `renderSquadPage` 안의 지역 변수 `rows`(살아 있는 스쿼드 배열), `window._sqFmtTime`, `window.openSquadDetail`

- [ ] **Step 1: 섹션을 그린다**

`renderSquadPage` 안에서 `const now = Date.now();` 다음, `root.innerHTML = rows.map(s => {` 앞에 넣는다.

```js
  // ★인기 스쿼드 (대표 8-18) — 목록 맨 위에 3개.
  //   명예의 전당(사람 랭킹)과 자리를 나눈 이유: 여기는 자랑이 아니라 **참가**가 목적이라
  //   누르면 프로필이 아니라 스쿼드 상세로 가야 한다.
  //   나중에 정기반이 다시 열리면 자연스럽게 여기 올라온다.
  let hotHtml = '';
  try {
    const hot = rows.filter(function (s) { return !s._cls && (s.memberUids || []).length >= 2; })
                    .sort(function (a, b) { return (b.memberUids || []).length - (a.memberUids || []).length; })
                    .slice(0, 3);
    if (hot.length) {
      hotHtml = '<div style="margin-bottom:14px">'
        + '<div style="font-size:12.5px;font-weight:800;color:rgba(255,255,255,0.55);margin-bottom:8px;letter-spacing:-0.2px">인기 스쿼드</div>'
        + hot.map(function (s, i) {
            const n = (s.memberUids || []).length;
            return '<div onclick="window.openSquadDetail(\'' + s.id + '\')" style="display:flex;align-items:center;gap:11px;'
              + 'padding:11px 13px;margin-bottom:6px;border:1px solid rgba(255,255,255,0.09);border-radius:12px;cursor:pointer">'
              + '<span style="width:18px;flex-shrink:0;text-align:center;font-size:13px;font-weight:800;color:rgba(255,255,255,0.45)">' + (i + 1) + '</span>'
              + '<span style="flex:1;min-width:0;font-size:13.5px;font-weight:700;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'
              + (s.title || '').replace(/</g, '&lt;') + '</span>'
              + '<span style="flex-shrink:0;font-size:12px;font-weight:700;color:rgba(255,255,255,0.6)">' + n + '/' + s.capacity + '명</span>'
              + '</div>';
          }).join('')
        + '</div>';
    }
  } catch (e) { console.warn('인기 스쿼드', e); }
```

- [ ] **Step 2: 목록 앞에 붙인다**

`root.innerHTML = rows.map(s => {` 를 `root.innerHTML = hotHtml + rows.map(s => {` 로 바꾼다.

- [ ] **Step 3: 문법검사 + 커밋**

Run: 위 「문법검사 명령」 / Expected: `ALL PASS`

```bash
cd /c/Users/allys/Murpy && git status --short
git add index.html
git commit -m "feat(squad): 목록 위에 인기 스쿼드 3개

참가자 2명 이상인 것만 줄 세운다(1명이면 '인기'가 아니라 그냥 새 스쿼드다).
명예의 전당에 안 넣은 이유 = 여기는 자랑이 아니라 참가가 목적이라
누르면 프로필이 아니라 스쿼드 상세로 가야 한다.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Task 7: 1위 한마디 + 주간 팝업

마지막. 팝업이 한마디를 보여주므로 **한마디를 먼저** 만든다.

**Files:**
- Modify: `index.html` — `#mw-promo` 정의 **다음**에 `#hof-popup` HTML 추가
- Modify: `index.html` — module 블록, Task 5 함수 아래

**Interfaces:**
- Consumes: `window.loadHof`, `window.HOF_KINDS`, `window.mwMiniCharHtml`, `window.mwSeasonKey`, 기존 `showToast`, `db`/`doc`/`updateDoc`
- Produces: `window.hofSaveMsg()`, `window.showHofPopup(kind)`, `window._maybeHofPopup()`, `window.hofPopupClose(forever)`

- [ ] **Step 1: 한마디 입력칸을 패널에 붙인다**

Task 3 의 `loadHofPanel` 안, `listEl.innerHTML = html;` **직전**에 넣는다.

```js
  // 내가 1위면 한마디를 쓸 수 있다. 이 글은 주간 팝업으로 **전체 유저에게** 나간다.
  if (rows[0] && rows[0].uid === myUid) {
    const cur = (window.currentUser || {}).hofMsg || '';
    html += '<div style="padding:14px 16px;border-top:1px solid rgba(255,255,255,0.09)">'
      + '<div style="font-size:12px;font-weight:700;color:rgba(255,255,255,0.55);margin-bottom:7px">1위 한마디 <span style="font-weight:600;color:rgba(255,255,255,0.3)">· 모두에게 보여요</span></div>'
      + '<div style="display:flex;gap:7px">'
      + '<input id="hof-msg-input" maxlength="30" value="' + esc(cur) + '" placeholder="30자까지"'
      + ' style="flex:1;min-width:0;background:rgba(255,255,255,0.06);border:1px solid rgba(255,255,255,0.12);border-radius:10px;padding:11px 13px;color:#fff;font-size:13.5px;outline:none;font-family:inherit">'
      + '<button onclick="window.hofSaveMsg()" style="flex-shrink:0;background:var(--accent);color:#fff;border:none;border-radius:10px;padding:0 16px;font-size:13px;font-weight:800;cursor:pointer;font-family:inherit">저장</button>'
      + '</div></div>';
  }
```

- [ ] **Step 2: 저장 함수를 넣는다**

```js
// 1위 한마디 저장. 30자 제한은 화면과 저장 **양쪽**에서 건다(화면만 믿지 않는다).
window.hofSaveMsg = async function () {
  const el = document.getElementById('hof-msg-input'); if (!el) return;
  const user = auth.currentUser || window.currentUser; if (!user) return;
  const msg = (el.value || '').trim().slice(0, 30);
  try {
    await updateDoc(doc(db, 'users', user.uid), { hofMsg: msg });
    if (window.currentUser) window.currentUser.hofMsg = msg;
    showToast(msg ? '한마디를 남겼어요' : '한마디를 지웠어요');
  } catch (e) { console.error('hofMsg', e); showToast('저장 실패'); }
};
// ★관리자 삭제 경로. 이 글은 전 유저에게 팝업으로 나가는 유일한 자유 텍스트라
//   지울 방법이 없으면 안 된다. 규칙상 관리자는 남의 users 문서를 쓸 수 있다.
window.adminClearHofMsg = async function (uid) {
  if (!(typeof isAdmin === 'function' && isAdmin())) return;
  try { await updateDoc(doc(db, 'users', uid), { hofMsg: '' }); showToast('한마디를 지웠어요'); }
  catch (e) { console.error('hofMsg admin', e); showToast('실패'); }
};
```

- [ ] **Step 3: 팝업 HTML 을 넣는다**

`#mw-promo` 를 닫는 `</div>` 다음에 넣는다.

```html
<!-- 주간 명예의 전당 팝업 (대표 8-18). 헬토리 홍보 팝업과 같은 문법(.mfg-card 재사용). -->
<div id="hof-popup" style="display:none;position:fixed;inset:0;z-index:10047;align-items:center;justify-content:center;padding:24px;background:rgba(0,0,0,0.62);-webkit-backdrop-filter:blur(6px);backdrop-filter:blur(6px)">
  <div class="mfg-card" style="max-width:344px;width:100%;background:#161616;border:1px solid rgba(255,255,255,0.1);border-radius:20px;padding:26px 22px;text-align:center">
    <div id="hof-pop-kind" style="font-size:11.5px;font-weight:800;letter-spacing:1px;color:var(--accent);margin-bottom:12px"></div>
    <div id="hof-pop-char" style="display:flex;justify-content:center;margin-bottom:12px;min-height:104px;align-items:flex-end"></div>
    <div id="hof-pop-nick" style="font-size:19px;font-weight:800;letter-spacing:-0.3px;margin-bottom:3px"></div>
    <div id="hof-pop-n" style="font-size:12.5px;color:rgba(255,255,255,0.45);margin-bottom:14px"></div>
    <div id="hof-pop-msg" style="display:none;font-size:13px;line-height:1.6;color:rgba(255,255,255,0.8);border:1px solid rgba(255,255,255,0.12);border-radius:12px;padding:12px 14px;margin-bottom:18px"></div>
    <button class="mfg-btn" onclick="window.hofPopupClose();openPanel('hof-panel')" style="width:100%;background:var(--accent);color:#fff;border:none;border-radius:12px;padding:13px;font-size:14px;font-weight:800;cursor:pointer;font-family:inherit">명예의 전당 보기</button>
    <button onclick="window.hofPopupClose()" style="width:100%;background:none;border:none;color:rgba(255,255,255,0.4);font-size:13px;cursor:pointer;margin-top:9px;padding:4px">닫기</button>
    <button onclick="window.hofPopupClose(true)" style="width:100%;background:none;border:none;color:rgba(255,255,255,0.25);font-size:11.5px;cursor:pointer;margin-top:2px;padding:4px">다시 보지 않기</button>
  </div>
</div>
```

- [ ] **Step 4: 팝업 로직을 넣는다**

```js
// 그 달의 몇 번째 주 (ISO 주차가 아니다 — 종목 회전이 월 카운터와 같은 주기를 돌아야 한다)
window._hofWeek = function (d) { return Math.min(4, Math.floor((d.getDate() - 1) / 7) + 1); };
window._hofWeekKey = function (d) { return window.mwSeasonKey(d) + '-W' + window._hofWeek(d); };
// ★주차마다 종목을 돌린다. 카운터가 월 누적이라 월초에 앞선 사람이 그 달 내내 1위다 —
//   같은 얼굴이 4주 연속 뜨면 첫 주만 재밌고 그다음은 광고가 된다. 네 명이 돌아가며 주인공이 된다.
window._HOF_WEEK_KIND = { 1: 'feed', 2: 'checkin', 3: 'host', 4: 'attend' };
window.hofPopupClose = function (forever) {
  const el = document.getElementById('hof-popup'); if (el) el.style.display = 'none';
  if (forever) { try { localStorage.setItem('hof_popup', 'off'); } catch (e) {} }
};
window.showHofPopup = async function (kind) {
  const el = document.getElementById('hof-popup'); if (!el) return false;
  const data = await window.loadHof();
  const rows = data.rows[kind] || []; if (!rows.length) return false;
  const top = rows[0];
  // 차단한 사람이 1위면 한마디는 숨긴다(이름·기록은 그대로 — 스펙 7장).
  // ★_blocked 는 객체가 아니라 Set 이다. 이미 있는 헬퍼를 쓴다(양방향 차단까지 본다).
  const blocked = window._isBlocked ? window._isBlocked(top.uid) : false;
  const def = window.HOF_KINDS[kind];
  const esc = function (s) { return String(s == null ? '' : s); };
  document.getElementById('hof-pop-kind').textContent = '이번 주의 ' + def.label + ' 1위';
  document.getElementById('hof-pop-nick').textContent = esc(top.nick);
  document.getElementById('hof-pop-n').textContent = top.n + def.unit;
  let ch = '';
  try { ch = (window._hofChar && window._hofChar[top.uid] && window.mwMiniCharHtml) ? window.mwMiniCharHtml(window._hofChar[top.uid], 104) : ''; } catch (e) {}
  document.getElementById('hof-pop-char').innerHTML = ch;
  const mEl = document.getElementById('hof-pop-msg');
  const msg = blocked ? '' : ((window._hofMsg || {})[top.uid] || '');
  mEl.style.display = msg ? '' : 'none';
  mEl.textContent = msg;                       // ★textContent — 남이 쓴 글이다
  el.style.display = 'flex';
  return true;
};
// 월요일 첫 접속 1회. 같은 주에 두 번 뜨지 않게 주차 키를 적어둔다.
window._maybeHofPopup = async function () {
  try {
    if (localStorage.getItem('hof_popup') === 'off') return;
    if (!window.currentUser) return;
    const d = new Date();
    if (d.getDay() !== 1) return;                        // 월요일만
    const key = window._hofWeekKey(d);
    if (localStorage.getItem('hof_popup_week') === key) return;
    const ok = await window.showHofPopup(window._HOF_WEEK_KIND[window._hofWeek(d)] || 'feed');
    if (ok) localStorage.setItem('hof_popup_week', key);
  } catch (e) { console.warn('hof popup', e); }
};
```

- [ ] **Step 5: 로더가 캐릭터·한마디도 담게 한다**

Task 2 의 `loadHof` 안, `const rows = {};` **바로 앞**에 넣는다. (팝업이 1위의 캐릭터와 한마디를 그리려면 필요하다)

```js
  // 팝업이 1위의 캐릭터·한마디를 그린다 — 같은 읽기에서 같이 담는다(다시 읽지 않는다)
  window._hofChar = {}; window._hofMsg = {};
  users.forEach(function (u) {
    if (u.character) window._hofChar[u.uid] = u.character;
    if (u.hofMsg) window._hofMsg[u.uid] = u.hofMsg;
  });
```

- [ ] **Step 6: 홈에 들어올 때 판정한다**

Task 5 에서 고친 `goPage` 의 home 줄 끝에 한 번 더 붙인다.

```js
  if (name === 'home') { if (window.renderFeedFilterBar) window.renderFeedFilterBar(); if (window.renderStreakUI) window.renderStreakUI(); if (window.loadHofLine) window.loadHofLine(); if (window._maybeHofPopup) setTimeout(window._maybeHofPopup, 1500); }
```

- [ ] **Step 7: 주차 회전을 실측한다**

```bash
cd /c/Users/allys/AppData/Local/Temp/claude/C--Users-allys/10166e50-3479-4c68-9f73-0340bc46ed9a/scratchpad
cat > hof_week_test.js <<'EOF'
const hofWeek = (d) => Math.min(4, Math.floor((d.getDate() - 1) / 7) + 1);
const KIND = { 1: 'feed', 2: 'checkin', 3: 'host', 4: 'attend' };
const want = { 1:'feed', 7:'feed', 8:'checkin', 14:'checkin', 15:'host', 21:'host', 22:'attend', 28:'attend', 29:'attend', 31:'attend' };
let all = true;
Object.keys(want).forEach(day => {
  const got = KIND[hofWeek(new Date(2026, 7, +day))];
  const ok = got === want[day]; if (!ok) all = false;
  console.log((ok ? '  PASS ' : '  FAIL ') + '8/' + day + ' -> ' + got + ' (기대 ' + want[day] + ')');
});
console.log(all ? 'ALL PASS' : 'FAILED');
EOF
node hof_week_test.js
```

Expected: 10줄 전부 `PASS` + `ALL PASS`

- [ ] **Step 8: 문법검사 + 커밋 + push**

Run: 위 「문법검사 명령」 / Expected: `ALL PASS`

```bash
cd /c/Users/allys/Murpy && git status --short
git add index.html
git commit -m "feat(hof): 1위 한마디 + 월요일 주간 팝업 (종목 4주 로테이션)

팝업은 헬토리 홍보 팝업과 같은 문법. 월요일 첫 접속 1회 + 다시 보지 않기.
★주차마다 종목을 돌린다 — 카운터가 월 누적이라 그냥 두면 같은 얼굴이 4주 연속
  뜬다. 인증/체크인/스쿼드장/참가로 돌려 네 명이 주인공이 된다. 새 데이터 0.

한마디는 전 유저에게 팝업으로 나가는 유일한 자유 텍스트라 모더레이션을 같이 넣었다:
30자 제한(화면+저장 양쪽) · textContent 로만 표시 · 차단한 사람이면 한마디 숨김 ·
관리자 삭제 경로(adminClearHofMsg).

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
git push origin main
```

**대표 확인 항목:** ①1위일 때 한마디 입력칸이 뜨는지 ②저장 후 다시 열면 남아 있는지 ③월요일에 팝업이 뜨는지(테스트하려면 콘솔에서 `showHofPopup('feed')`) ④'다시 보지 않기'가 먹는지

---

## 자체 점검 결과

- **스펙 커버리지** — 3장 데이터=Task 1·2 / 4장 A·B·C=Task 3·5·6 / 5장 헤더=Task 4 / 6장 팝업=Task 7 / 7장 한마디=Task 7. 8장(안 하는 것)은 구현 없음. 9장 위험은 주석으로 코드에 남긴다. **빠진 항목 없음.**
- **이름 일관성** — `_hofRank` / `_hofMyRank` / `loadHof` / `loadHofPanel` / `loadHofLine` / `showHofPopup` / `_maybeHofPopup` / `hofSaveMsg` / `HOF_EXCLUDE_UID` / `HOF_MONTH` / `HOF_KINDS`. Task 간 호출 이름이 전부 일치한다.
- **`_blocked` 모양 확인 완료** — 객체가 아니라 `Set` 이고 헬퍼 `window._isBlocked(uid)` 가 이미 있다(양방향 차단을 본다). Task 7 은 그 헬퍼를 쓴다.
- **남는 판단 하나(대표 몫)** — 스펙대로 차단한 사람이 1위면 **한마디만 숨기고 이름·기록은 보여준다.** "팝업에 얼굴도 띄우지 말라"로 바꾸려면 다음 사람으로 넘기게 해야 하는데, 그러면 사람마다 팝업 주인공이 달라진다. 지금은 스펙을 따른다.
