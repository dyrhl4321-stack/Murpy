# 얼굴 커마권 — 클라이언트·경제 구현 계획 (Phase A-1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 얼굴 커마 캐릭터를 **하드코딩이 아니라 Firestore 문서로** 굴러가게 만들고, 커마권을 사고 보유하는 경제를 붙인다. 고객이 생길 때마다 index.html 을 고치고 재배포하는 구조를 없앤다.

**Architecture:** `users/{uid}/faceChars/{charId}` 문서를 앱 부팅 때 읽어 `window._CHAR_BODIES['face:'+charId]` 에 **주입**한다. 렌더·착용·옷호환 코드는 한 줄도 안 고친다(`kin:'human'` 이라 기존 옷이 그대로 맞는다). 남의 커마를 그릴 때는 그 사람 유저 문서의 `characterSheet` URL 하나로 임시 몸통을 등록한다. 커마권은 `users/{uid}.faceTickets` 정수 한 필드이며, 구매는 머피 차감과 **같은 트랜잭션**으로 묶고 규칙에서 짝을 강제한다.

**Tech Stack:** 단일 HTML(index.html, 순수 JS + window 전역) · Firebase Firestore/Storage · 테스트 = `node tools/tests/*.test.mjs`(index.html 에서 함수를 정규식으로 뽑아 가짜 window 에서 실행)

**Spec:** `docs/superpowers/specs/2026-09-04-face-ticket-design.md`

**범위 밖(별도 계획):** 셀카→시트 자가생성 서버(Firebase Functions + 제미나이 Pro 2K), 웹캠 캡처 흐름, 눈 좌표 자동 실측. 이 계획은 **관리자가 만들어 즉시 지급**하는 데까지 완결한다. 서버가 붙으면 그 자리에 생성 호출만 꽂힌다.

## Global Constraints

- 작업 위치 = 워크트리 `C:\Users\dyrhl\Murpy\.claude\worktrees\face-custom`, 브랜치 `feat/face-custom`. main 에서 직접 작업 금지(반대 창이 main 에서 NPC 음성 작업 중).
- `git add` 와 `git commit` 은 **한 호출로 묶는다**(두 창이 같은 파일을 만져 커밋이 섞인 전례). `git add .` 금지 — 파일을 명시한다.
- 몸통 키는 `'face:'` 접두사를 **강제**한다. 기존 키(human/heltori/jaejin…)와 절대 안 겹치게 한다.
- 캐릭터를 그리는 곳은 `window._charRenderTo` **하나뿐**이다. 새 렌더 경로를 만들지 않는다.
- 몸통 소유 판정은 `window._charBodyIsMine` **하나뿐**, 아이템 호환 판정은 `window._charFits` **하나뿐**이다.
- UI 에 이모지 금지(머피 전용 라인 SVG 아이콘만). 반투명 색면 배지(틴트 칩) 금지 — `background:none` + 테두리 + 글자색.
- '벙' 단어 금지(스쿼드/스쿼드장).
- 대표 허락 없이 **새 UI 를 만들지 않는다.** 기존 화면(로스터·시착 확인창·머피월드 홍보 팝업)을 재사용한다.
- 가격은 상수로 분리한다: `window.FACE_TICKET_PRICE = 1000` (머피). 정식 가격(19,900원)은 PG 시점에 이 상수만 바꾼다.
- **index.html 을 고친 Task 는 커밋 전에 문법 검사 2종을 둘 다 돌린다** (CLAUDE.md 10장): `node tools/module-syntax-check.mjs` + `node tools/dogam-syntax-check.mjs`. 하나만 돌리면 다른 블록의 문법 오류가 조용히 배포된다.
- 버전은 **손으로 고치지 않는다** — `node tools/bump-version.mjs <N>` 이 세 곳을 한 번에 올린다. 그 뒤 `python tools/check_version.py`(`PYTHONIOENCODING=utf-8` 필요). 이 계획의 중간 커밋은 배포가 아니므로 마지막 Task 에서 한 번만 올린다.
- 테스트 실행: `node tools/tests/<name>.test.mjs` — 통과하면 마지막 줄에 OK 를 찍는다. 실패는 assert 로 죽는다.

---

### Task 0: main 병합 — 60 커밋 뒤진 워크트리를 현재로 올린다

이 브랜치는 9-04 오전에 갈라져 나왔고 main 은 그 뒤 세계지도 v13·공원 오픈월드·NPC 퀘스트까지 60 커밋을 더 갔다. 병합을 미루면 index.html 충돌이 눈덩이가 된다.

**Files:**
- Modify: 병합 결과 전체 (`index.html`, `sw.js` 등)

- [ ] **Step 1: 현재 상태를 확인한다**

```bash
cd /c/Users/dyrhl/Murpy/.claude/worktrees/face-custom
git status -s
git log --oneline main ^feat/face-custom | wc -l
```

기대: 워킹트리에 커밋 안 된 스파이크 산출물(`char/faces/hyunsu*.png` 등)이 있고, main 이 60 커밋 앞선다.

- [ ] **Step 2: 스파이크 산출물을 먼저 커밋한다 — 병합 충돌에 휩쓸리지 않게**

`char/faces/*` 와 `char/skin/face_*` 는 실험 산출물이지만 재생성에 돈(제미나이 Pro 건당 $0.1~0.15)이 든다. 지운다는 선택지는 없다.

```bash
git add char/faces char/skin tools/face_composite.py skin_bake2.txt && \
git commit -m "chore(face): 9-04 커마 스파이크 산출물 보존 — 재생성에 유료 API 가 드는 시트·톤 실험본"
```

- [ ] **Step 3: main 을 병합한다**

```bash
git merge main
```

- [ ] **Step 4: 충돌을 푼다**

충돌은 `index.html` 에서만 날 가능성이 높다. 이 브랜치가 만진 자리는 세 곳뿐이다:
1. `window._CHAR_BODIES`(3777행 근처) — 커마 주석 + jaejin/paesuhyun
2. `window._charBodyIsMine`(3816행 근처)
3. `charRenderRoster` 의 커마 필터(8903행 근처)

main 쪽 변경(오픈월드·NPC)은 이 자리와 겹치지 않는다. 충돌이 나면 **양쪽을 다 남긴다** — 한쪽을 버리면 커마가 사라지거나 오픈월드가 깨진다.

- [ ] **Step 5: 병합이 앱을 깨지 않았는지 확인한다**

```bash
node -e "const s=require('fs').readFileSync('index.html','utf8'); for(const k of ['_CHAR_BODIES','_charBodyIsMine','_charFits','charRenderRoster','SQ_MG_EYES']) if(!s.includes('window.'+k)) throw new Error('사라졌다: '+k); console.log('OK 핵심 심볼 5종 살아 있음');"
for t in tools/tests/*.test.mjs; do node "$t" >/dev/null || echo "FAIL $t"; done; echo "테스트 스위트 끝"
```

기대: `OK 핵심 심볼 5종 살아 있음` + FAIL 줄이 하나도 없음.

- [ ] **Step 6: 커밋**

병합 커밋이 이미 만들어졌으면 이 단계는 건너뛴다. 충돌을 풀었으면:

```bash
git add index.html && git commit -m "chore: main 병합 — 세계지도 v13·공원 오픈월드·NPC 퀘스트 반영"
```

---

### Task 1: 데이터 기반 커마 몸통 — 정의 만들기·주입·피부톤 URL 분기

`_CHAR_BODIES` 는 하드코딩 표다. 고객이 한 명 생길 때마다 사람이 index.html 을 고치고 재배포해야 하니 "바로 지급"이 원천적으로 불가능하다. 문서 한 장을 몸통 정의로 바꾸는 **순수 함수**를 만들고, 그걸 표에 꽂는 얇은 등록 함수를 붙인다. 순수 함수라 테스트가 된다.

**Files:**
- Modify: `index.html` — `_CHAR_BODIES` 정의 직후(현 3812행 `};` 다음), `_charSkinSrc`(현 4009행)
- Test: `tools/tests/face-body.test.mjs` (새로 만든다)

**Interfaces:**
- Consumes: `window._CHAR_BODIES`, `window.SQ_MG_EYES`, `window.CHAR_SKINS`, `window._charBodyIsMine`
- Produces:
  - `window.FACE_BODY_PREFIX` — 문자열 `'face:'`
  - `window._charFaceBodyDef(charId, d, ownerUid)` → `{ key, def, eyes } | null` (순수)
  - `window._charRegisterFaceBody(charId, d, ownerUid)` → `key | null` (`_CHAR_BODIES`·`SQ_MG_EYES` 에 꽂는다)
  - `window._charSkinSrc(bodyKey, skin)` — 동작 확장(`skinUrls` 우선)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tools/tests/face-body.test.mjs` 를 만든다:

```js
// 얼굴 커마 동적 몸통 — index.html 에서 함수를 뽑아 가짜 window 에서 돌린다
// 실행: node tools/tests/face-body.test.mjs
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
function grab(re, name) {
  const m = src.match(re);
  assert(m, `index.html에서 ${name}를 찾지 못함`);
  return m[0];
}
const w = {};
new Function('window', grab(/window\._CHAR_BODIES = \{[\s\S]*?\n\};/, '_CHAR_BODIES'))(w);
new Function('window', grab(/window\.SQ_MG_EYES = \{[\s\S]*?\};/, 'SQ_MG_EYES'))(w);
new Function('window', grab(/window\.FACE_BODY_PREFIX = [\s\S]*?\n\};(?=\nwindow\._charRegisterFaceBody)/, '_charFaceBodyDef'))(w);
new Function('window', grab(/window\._charRegisterFaceBody = function[\s\S]*?\n\};/, '_charRegisterFaceBody'))(w);
new Function('window', grab(/window\._charBodyIsMine = function[\s\S]*?\n\};/, '_charBodyIsMine'))(w);
new Function('window', grab(/window\.CHAR_SKINS = \[[\s\S]*?\];/, 'CHAR_SKINS'))(w);
new Function('window', grab(/window\._charSkinSrc = function[\s\S]*?\n\};/, '_charSkinSrc'))(w);

const DOC = {
  name: '현수',
  sheetUrl: 'https://example.com/sheet.png',
  skinUrls: { t1: 'https://example.com/t1.png', t2: 'https://example.com/t2.png' },
  eyes: { y: 0.31, x: [0.33, 0.65] }
};

// 1) 키는 'face:' 접두사가 강제된다 — 기존 몸통 키와 절대 안 겹쳐야 한다
const r = w._charFaceBodyDef('abc123', DOC, 'UID1');
assert.strictEqual(w.FACE_BODY_PREFIX, 'face:', "접두사가 'face:' 가 아니다");
assert.strictEqual(r.key, 'face:abc123', '키에 접두사가 안 붙었다');
assert(!Object.keys(w._CHAR_BODIES).some(k => k.startsWith('face:')), '하드코딩 표에 이미 face: 키가 있다');

// 2) 기존 옷을 그대로 입어야 한다 — kin:'human' · wearable · fixedHair
assert.strictEqual(r.def.kin, 'human', "kin 이 'human' 이 아니면 기존 옷이 안 맞는다");
assert.strictEqual(r.def.wearable, true, 'wearable 이 아니면 옷을 못 입는다');
assert.strictEqual(r.def.fixedHair, true, 'fixedHair 가 아니면 머리가 두 겹이 된다');
assert.strictEqual(r.def.cw, 141); assert.strictEqual(r.def.ch, 224);

// 3) 주인 판정은 _charBodyIsMine 한 곳으로 간다
w.currentUser = { uid: 'UID1', email: 'a@b.c' };
assert.strictEqual(w._charBodyIsMine(r.def), true, '주인인데 내 것이 아니라고 한다');
w.currentUser = { uid: 'UID2', email: 'x@y.z' };
assert.strictEqual(w._charBodyIsMine(r.def), false, '남의 커마를 내 것이라고 한다');

// 4) 이름은 12자로 자른다(스펙 1~12자)
const long = w._charFaceBodyDef('c', { ...DOC, name: '가나다라마바사아자차카타파하' }, 'UID1');
assert.strictEqual(long.def.name.length, 12, '이름이 12자로 안 잘렸다');

// 5) 시트 URL 이 없으면 몸통을 만들지 않는다 — 빈 캐릭터가 뜨느니 안 만드는 게 낫다
assert.strictEqual(w._charFaceBodyDef('c', { name: 'x' }, 'UID1'), null, 'sheetUrl 없이 몸통이 만들어졌다');
assert.strictEqual(w._charFaceBodyDef('', DOC, 'UID1'), null, 'charId 없이 몸통이 만들어졌다');

// 6) 등록하면 표와 눈 좌표표에 같이 들어간다
const key = w._charRegisterFaceBody('abc123', DOC, 'UID1');
assert.strictEqual(key, 'face:abc123');
assert(w._CHAR_BODIES[key], '_CHAR_BODIES 에 안 들어갔다');
assert.deepStrictEqual(w.SQ_MG_EYES[key], DOC.eyes, '무궁화 하트눈 좌표가 안 들어갔다');

// 7) 눈 좌표가 없으면 표에 넣지 않는다 — 소비처가 human 좌표로 폴백한다(40644행)
w._charRegisterFaceBody('noeye', { name: 'n', sheetUrl: 'https://e/s.png' }, 'UID1');
assert.strictEqual(w.SQ_MG_EYES['face:noeye'], undefined, '눈 좌표 없는 몸통이 표를 오염시켰다');

// 8) 피부톤 — 동적 몸통은 경로 조립이 아니라 URL 표를 본다
assert.strictEqual(w._charSkinSrc('face:abc123', 't1'), DOC.skinUrls.t1, '구운 톤 URL 을 안 쓴다');
assert.strictEqual(w._charSkinSrc('face:abc123', 't3'), DOC.sheetUrl, 't3(원본)은 시트 그대로여야 한다');
assert.strictEqual(w._charSkinSrc('face:abc123', 't5'), DOC.sheetUrl, '없는 톤은 원본으로 폴백해야 한다');
// 기존 몸통은 하나도 안 바뀐다
assert.strictEqual(w._charSkinSrc('human', 't1'), 'char/skin/walk_t1.png?v=4', '기존 피부톤 경로가 바뀌었다');
assert.strictEqual(w._charSkinSrc('human', 't3'), w._CHAR_BODIES.human.src, '기존 t3 폴백이 깨졌다');

console.log('OK face-body 8항목');
```

- [ ] **Step 2: 실패를 확인한다**

```bash
node tools/tests/face-body.test.mjs
```

기대: FAIL — `index.html에서 _charFaceBodyDef를 찾지 못함`

- [ ] **Step 3: 구현 — `_CHAR_BODIES` 표가 닫히는 `};` 바로 다음(현 3812행)에 넣는다**

```js
// ===== 얼굴 커마 — 데이터 기반 몸통 (2026-09-05) =====
// ★위 표는 하드코딩이다. 고객이 한 명 생길 때마다 사람이 이 파일을 고치고 재배포해야 하니
//   "커마권 쓰면 바로 지급"이 원천적으로 불가능하다. 그래서 커마 몸통만 **문서로** 뺀다:
//   users/{uid}/faceChars/{charId} → 부팅 때 읽어 이 표에 주입한다(_charLoadMyFaceChars).
// ★키에 'face:' 를 **강제**한다. 접두사가 없으면 언젠가 charId 가 'human' 이거나 'jaejin' 이어서
//   기본 몸통을 통째로 덮어쓴다 — 전 유저가 남의 얼굴로 보인다.
// ★kin:'human' = 목 아래가 base 와 같은 몸이라 human 옷이 그대로 맞는다(_charFits 참고).
//   fixedHair = 머리카락이 시트에 구워져 있어 헤어·모자 슬롯을 잠근다(두 겹 방지).
window.FACE_BODY_PREFIX = 'face:';
window._charFaceBodyDef = function (charId, d, ownerUid) {
  if (!charId || !d || !d.sheetUrl) return null;   // 시트가 없으면 빈 캐릭터가 된다 — 아예 안 만든다
  return {
    key: window.FACE_BODY_PREFIX + charId,
    def: {
      name: String(d.name || '내 캐릭터').slice(0, 12),
      src: d.sheetUrl,
      skinBase: null,                    // 경로 조립 대신 아래 skinUrls 를 쓴다
      skinUrls: (d.skinUrls && typeof d.skinUrls === 'object') ? d.skinUrls : null,
      cw: 141, ch: 224,
      wearable: true, fixedHair: true, kin: 'human',
      tag: '커마',
      defaultTop: 'top_basic_tee', defaultBottom: 'bottom_basic_shorts',
      owner: ownerUid || null, dynamic: true,
      desc: '얼굴 커스터마이징으로 만든 나만의 캐릭터'
    },
    eyes: (d.eyes && typeof d.eyes.y === 'number' && Array.isArray(d.eyes.x) && d.eyes.x.length === 2) ? d.eyes : null
  };
};
window._charRegisterFaceBody = function (charId, d, ownerUid) {
  const r = window._charFaceBodyDef(charId, d, ownerUid);
  if (!r) return null;
  window._CHAR_BODIES[r.key] = r.def;
  // 눈 좌표가 없으면 넣지 않는다 — 소비처가 SQ_MG_EYES.human 으로 폴백한다(무궁화 하트눈).
  if (r.eyes && window.SQ_MG_EYES) window.SQ_MG_EYES[r.key] = r.eyes;
  return r.key;
};
```

- [ ] **Step 4: `_charSkinSrc` 에 URL 표 분기를 넣는다 (현 4009행) — 기존 본문을 이걸로 바꾼다**

```js
window._charSkinSrc = function (bodyKey, skin) {
  const b = window._CHAR_BODIES[bodyKey] || {};
  // 옛 데이터는 skin 에 색상값(#F0C9A0)이 들어 있다 — t1~t7 이 아니면 원본을 쓴다
  const ok = !!(skin && window.CHAR_SKINS.indexOf(skin) >= 0 && skin !== 't3');
  // ★동적 커마 몸통은 구운 톤 시트가 Storage 에 있다. 경로를 조립할 수 없으니 URL 표를 본다.
  //   표에 없는 톤은 원본(b.src)으로 떨어진다 — 깨진 이미지보다 원색이 낫다.
  if (ok && b.skinUrls) return b.skinUrls[skin] || b.src;
  if (!b.skinBase || !ok) return b.src;
  return 'char/skin/' + b.skinBase + '_' + skin + '.png?v=4';
};
```

- [ ] **Step 5: 테스트가 통과하는지 확인한다**

```bash
node tools/tests/face-body.test.mjs
```

기대: `OK face-body 8항목`

- [ ] **Step 6: 기존 스위트가 안 깨졌는지 확인한다**

```bash
node tools/module-syntax-check.mjs && node tools/dogam-syntax-check.mjs
for t in tools/tests/*.test.mjs; do node "$t" >/dev/null || echo "FAIL $t"; done; echo "끝"
```

기대: FAIL 줄 없음.

- [ ] **Step 7: 커밋**

```bash
git add index.html tools/tests/face-body.test.mjs && \
git commit -m "feat(face): 커마 몸통을 데이터로 — 문서 한 장을 _CHAR_BODIES 항목으로 바꾸는 순수 함수 + 피부톤 URL 분기"
```

---

### Task 2: 내 커마를 부팅 때 주입한다 + 착용하면 `characterSheet` 를 같이 남긴다

주입 **순서**가 중요하다. 유저 문서 로드 뒤에 성별 몸통 백필과 `_charEnsureDefaults` 가 돈다. 커마 몸통이 아직 표에 없으면 `_charEnsureDefaults` 가 `_CHAR_BODIES[bodyKey] || human` 으로 폴백해 **커마에 헤어를 채워 넣는다**(fixedHair 라 화면엔 안 보이지만 저장 데이터가 더러워진다). 그러니 백필보다 **먼저** 주입한다.

**Files:**
- Modify: `index.html` — Task 1 블록 끝, 유저 문서 로드 블록(현 22015행 `if (!d.character)` 직전), `_charPersistCharacter`(현 16529행)
- Test: `tools/tests/face-body.test.mjs`

**Interfaces:**
- Consumes: Task 1 의 `_charRegisterFaceBody`, `window.FACE_BODY_PREFIX`
- Produces:
  - `window._charState.faceChars` — `{ [charId]: docData }`
  - `window._charLoadMyFaceChars(uid)` — async, 서브컬렉션을 읽어 전부 등록 (모듈 블록)
  - `window._charSheetForBody(bodyKey)` → `string | null` (순수) — 저장할 `characterSheet` 값

- [ ] **Step 1: 실패하는 테스트를 추가한다**

`tools/tests/face-body.test.mjs` 의 `console.log` 줄 **앞에** 붙인다:

```js
// 9) 착용 저장 시 남길 characterSheet — 남이 나를 그릴 때 이 URL 하나만 본다
new Function('window', grab(/window\._charSheetForBody = function[\s\S]*?\n\};/, '_charSheetForBody'))(w);
assert.strictEqual(w._charSheetForBody('face:abc123'), DOC.sheetUrl, '커마 시트 URL 을 안 남긴다');
assert.strictEqual(w._charSheetForBody('human'), null, '기본 몸통인데 시트 URL 을 남긴다');
assert.strictEqual(w._charSheetForBody('heltori'), null, '고정 캐릭터인데 시트 URL 을 남긴다');
assert.strictEqual(w._charSheetForBody(undefined), null, '몸통이 없는데 시트 URL 을 남긴다');
```

마지막 줄을 `console.log('OK face-body 12항목');` 으로 바꾼다.

- [ ] **Step 2: 실패를 확인한다**

```bash
node tools/tests/face-body.test.mjs
```

기대: FAIL — `index.html에서 _charSheetForBody를 찾지 못함`

- [ ] **Step 3: `_charSheetForBody` 를 Task 1 블록 끝(`_charRegisterFaceBody` 다음)에 넣는다**

```js
// 착용 중인 몸통이 커마면 그 시트 URL 을 돌려준다. 유저 문서에 복사해 두면
// ★남이 나를 그릴 때 서브컬렉션까지 읽으러 갈 필요가 없다(피드·오버월드·채팅이 다 빨라진다).
// 커마가 아니면 null — 저장 쪽에서 필드를 지운다(옛 커마 시트가 남으면 남에게 옛 얼굴로 보인다).
window._charSheetForBody = function (bodyKey) {
  if (!bodyKey || String(bodyKey).indexOf(window.FACE_BODY_PREFIX) !== 0) return null;
  const b = window._CHAR_BODIES[bodyKey];
  return (b && b.src) ? b.src : null;
};
```

- [ ] **Step 4: 테스트 통과를 확인한다**

```bash
node tools/tests/face-body.test.mjs
```

기대: `OK face-body 12항목`

- [ ] **Step 5: 로더를 모듈 블록에 넣는다 — `_charPersistCharacter`(현 16529행) 바로 위**

```js
// 내 커마 캐릭터를 읽어 몸통 표에 꽂는다. 실패해도 앱은 그냥 돈다(기존 몸통으로 보인다).
// ★읽기 실패를 삼키는 이유 = 커마는 코스메틱이다. 여기서 던지면 로그인 전체가 멈춘다.
window._charState.faceChars = {};
window._charLoadMyFaceChars = async function (uid) {
  if (!uid) return 0;
  const snap = await getDocs(collection(db, 'users', uid, 'faceChars'));
  let n = 0;
  snap.forEach(function (s) {
    const d = s.data() || {};
    window._charState.faceChars[s.id] = d;
    if (window._charRegisterFaceBody(s.id, d, uid)) n++;
  });
  return n;
};
```

- [ ] **Step 6: 부팅 주입을 연결한다 — 유저 문서 로드 블록, `if (!d.character) {`(현 22015행) 바로 위**

```js
      // ★커마 몸통 주입은 **성별 백필·_charEnsureDefaults 보다 먼저** 와야 한다.
      //   표에 없으면 _charEnsureDefaults 가 human 으로 폴백해 커마에 헤어를 채워 넣는다
      //   (fixedHair 라 화면엔 안 보이지만 저장 데이터가 더러워진다).
      try { await window._charLoadMyFaceChars(ref.id); } catch (e) { console.warn('faceChars', e); }
```

`ref` 는 같은 블록이 이미 쓰는 유저 문서 참조다. 다른 이름이면 그 스코프의 uid 를 쓴다.

- [ ] **Step 7: 착용 저장에 `characterSheet` 를 같이 쓴다 — `_charPersistCharacter`(현 16541행)의 updateDoc 줄을 바꾼다**

```js
  try {
    // ★characterSheet 는 **남이 나를 그릴 때** 쓰는 단 하나의 값이다. 착용과 같은 쓰기에
    //   묶어야 "내 화면엔 커마인데 피드엔 기본 캐릭터" 같은 어긋남이 안 생긴다.
    //   커마가 아니면 필드를 지운다 — 남겨두면 옛 얼굴로 계속 보인다.
    const sheet = window._charSheetForBody(cfg && cfg.body);
    await updateDoc(doc(db, 'users', window.currentUser.uid),
      { character: cfg, characterSheet: sheet === null ? deleteField() : sheet, characterUpdatedAt: serverTimestamp() });
    return true;
  } catch (e) { console.error('char save', e); return false; }
};
```

`deleteField` 는 이미 import 되어 있다(14894행).

- [ ] **Step 8: 연결 확인 + 전체 스위트**

```bash
node -e "const s=require('fs').readFileSync('index.html','utf8'); for(const k of ['_charLoadMyFaceChars','_charSheetForBody','_charRegisterFaceBody']) if(!s.includes('window.'+k)) throw new Error('없다: '+k); if(!/_charLoadMyFaceChars\(/.test(s.split('window._charLoadMyFaceChars = ')[0])) throw new Error('부팅에서 로더를 안 부른다'); if(!/characterSheet/.test(s)) throw new Error('characterSheet 저장이 없다'); console.log('OK 주입 연결됨');"
node tools/module-syntax-check.mjs && node tools/dogam-syntax-check.mjs
for t in tools/tests/*.test.mjs; do node "$t" >/dev/null || echo "FAIL $t"; done; echo "끝"
```

기대: `OK 주입 연결됨` + FAIL 없음.

- [ ] **Step 9: 커밋**

```bash
git add index.html tools/tests/face-body.test.mjs && \
git commit -m "feat(face): 내 커마를 부팅 때 몸통 표에 주입 + 착용 시 characterSheet 동시 저장"
```

---

### Task 3: 남의 커마 캐릭터가 보이게 한다

`_charRenderTo` 는 `_CHAR_BODIES[cfg.body]` 를 본다. 남의 `cfg.body` 는 `face:xxx` 인데 내 표에는 그 사람 커마가 없다 → `|| _CHAR_BODIES.human` 으로 떨어져 **남의 얼굴이 기본 캐릭터로 보인다**. 그 사람 유저 문서의 `characterSheet` 로 임시 몸통을 등록해 주면 기존 렌더 경로가 그대로 돈다.

**Files:**
- Modify: `index.html` — Task 1 블록 끝, 남의 캐릭터를 그리는 호출부들
- Test: `tools/tests/face-body.test.mjs`

**Interfaces:**
- Consumes: `_charRegisterFaceBody`, `_CHAR_BODIES`, `window.FACE_BODY_PREFIX`
- Produces: `window._charEnsureFaceBody(bodyKey, sheetUrl)` → `bodyKey`(등록됨) 또는 `'human'`(폴백)

- [ ] **Step 1: 실패하는 테스트를 추가한다**

`console.log` 줄 앞에 붙인다:

```js
// 10) 남의 커마 — characterSheet 하나로 임시 몸통을 등록한다
new Function('window', grab(/window\._charEnsureFaceBody = function[\s\S]*?\n\};/, '_charEnsureFaceBody'))(w);
const other = w._charEnsureFaceBody('face:zzz', 'https://cdn/other.png');
assert.strictEqual(other, 'face:zzz', '남의 커마 키를 안 돌려준다');
assert.strictEqual(w._CHAR_BODIES['face:zzz'].src, 'https://cdn/other.png', '남의 시트가 안 꽂혔다');
assert.strictEqual(w._CHAR_BODIES['face:zzz'].owner, null, '남의 몸통에 주인이 찍혔다(내 로스터에 뜬다)');
// 시트가 없으면 기본 몸통으로 폴백 — 빈 화면 금지
assert.strictEqual(w._charEnsureFaceBody('face:none', null), 'human', '시트 없는 커마가 폴백을 안 한다');
// 이미 있는 몸통은 덮어쓰지 않는다 — 내 커마를 남의 캐시로 갈아치우면 안 된다
w._charEnsureFaceBody('face:abc123', 'https://cdn/WRONG.png');
assert.strictEqual(w._CHAR_BODIES['face:abc123'].src, DOC.sheetUrl, '이미 등록된 커마를 덮어썼다');
// 커마가 아닌 키는 그대로 통과
assert.strictEqual(w._charEnsureFaceBody('human', null), 'human');
assert.strictEqual(w._charEnsureFaceBody('heltori', null), 'heltori');

// 11) users 스냅샷 한 번 훑어 남의 커마를 전부 등록한다
new Function('window', grab(/window\._charRegisterFaceBodiesFrom = function[\s\S]*?\n\};/, '_charRegisterFaceBodiesFrom'))(w);
const fakeSnap = { forEach(f) { [
  { id: 'u1', data: () => ({ character: { body: 'face:aaa' }, characterSheet: 'https://cdn/a.png' }) },
  { id: 'u2', data: () => ({ character: { body: 'face:bbb' } }) },              // 시트 없음 → 등록 안 됨
  { id: 'u3', data: () => ({ character: { body: 'human' }, characterSheet: 'https://cdn/x.png' }) },
  { id: 'u4', data: () => ({}) }                                                 // 캐릭터 없음
].forEach(f); } };
assert.strictEqual(w._charRegisterFaceBodiesFrom(fakeSnap), 1, '등록 개수가 1이 아니다');
assert.strictEqual(w._CHAR_BODIES['face:aaa'].src, 'https://cdn/a.png', '남의 커마가 표에 안 들어갔다');
assert.strictEqual(w._CHAR_BODIES['face:bbb'], undefined, '시트 없는 커마를 등록했다');
assert.strictEqual(w._charRegisterFaceBodiesFrom(null), 0, '빈 스냅샷에 터진다');
```

마지막 줄을 `console.log('OK face-body 23항목');` 으로 바꾼다.

- [ ] **Step 2: 실패를 확인한다**

```bash
node tools/tests/face-body.test.mjs
```

기대: FAIL — `_charEnsureFaceBody를 찾지 못함`

- [ ] **Step 3: 구현 — Task 2 의 `_charSheetForBody` 다음에 넣는다**

```js
// 남의 커마 캐릭터를 그리기 **직전에** 부른다. 그 사람 유저 문서의 characterSheet 하나로
// 임시 몸통을 등록해 두면 _charRenderTo·오버월드·머피캠이 손 안 대고 그대로 그린다.
// ★owner 를 null 로 둔다 — 남의 몸통이 내 로스터(charRenderRoster)에 뜨면 안 된다.
// ★이미 있는 키는 절대 덮지 않는다. 내 커마를 남의 캐시로 갈아치우면 내 얼굴이 바뀐다.
// ★시트가 없으면(구버전 유저·URL 유실) 'human' 으로 폴백한다 — 빈 화면보다 기본 캐릭터가 낫다.
window._charEnsureFaceBody = function (bodyKey, sheetUrl) {
  if (!bodyKey || String(bodyKey).indexOf(window.FACE_BODY_PREFIX) !== 0) return bodyKey || 'human';
  if (window._CHAR_BODIES[bodyKey]) return bodyKey;
  if (!sheetUrl) return 'human';
  const charId = String(bodyKey).slice(window.FACE_BODY_PREFIX.length);
  return window._charRegisterFaceBody(charId, { name: '커마', sheetUrl: sheetUrl }, null) || 'human';
};
```

- [ ] **Step 4: 테스트 통과를 확인한다**

```bash
node tools/tests/face-body.test.mjs
```

기대: `OK face-body 23항목`

- [ ] **Step 5: 등록을 `_usersAll` 한 곳에 건다 (★계획 개정 9-05)**

원래는 캐릭터를 그리는 자리마다 한 줄씩 넣으려 했다. 실제 코드를 훑어 보니 **더 나은 자리가 있다.**

`window._usersAll`(23429행)은 users 컬렉션 **전체**를 읽어 5분 캐시하는 공통 경로다. 홈·매칭·인기 캐릭터·경매가 전부 이걸 쓴다. 여기서 한 번 훑어 커마 몸통을 등록해두면, 그리는 자리는 **한 곳도 안 고쳐도** 이미 등록된 표를 보고 그대로 그린다. 시트 URL 을 함수 6개에 인자로 꿰는 것보다 훨씬 적게 건드린다.

`_usersAll` 안에서 스냅샷을 캐시에 넣는 두 자리(`.then` 콜백과 캐시 히트 반환) **모두**를 지나도록, 스냅샷을 돌려주기 직전에 부르는 헬퍼를 만든다:

```js
// 남의 커마 몸통을 한 번에 등록한다. users 전체를 읽는 공통 경로에 걸어 두면
// ★그리는 자리를 한 곳도 안 고쳐도 된다 — 표에 이미 있으니 기존 렌더가 그대로 그린다.
// 이미 있는 키는 _charEnsureFaceBody 가 건너뛰므로 5분마다 다시 돌아도 싸다.
window._charRegisterFaceBodiesFrom = function (snap) {
  if (!snap || !snap.forEach) return 0;
  let n = 0;
  snap.forEach(function (s) {
    const d = s.data() || {};
    const key = d.character && d.character.body;
    if (key && String(key).indexOf(window.FACE_BODY_PREFIX) === 0 && d.characterSheet) {
      if (window._charEnsureFaceBody(key, d.characterSheet) === key) n++;
    }
  });
  return n;
};
```

`_usersAll` 의 반환 지점 두 곳에 `window._charRegisterFaceBodiesFrom(snap)` 를 끼운다(캐시 히트로 돌려주는 `return c.snap;` 앞에도 넣어야 새로고침 없이 켜 둔 앱에서 빠지지 않는다).

- [ ] **Step 6: 등록 안 된 커마는 기본 몸통으로 떨어뜨린다 — `_charSafe` 한 곳**

`window._charSafe(cfg)`(33303행)는 남의 캐릭터 설정이 지나는 공통 관문이고, 이미 `Object.assign({}, cfg)` 로 **복사본을 만든다**(원본 오염 걱정이 없다). 여기서 미등록 커마를 기본 몸통으로 바꾼다 — RTDB 로 오는 방·스쿼드 참가자처럼 유저 문서를 안 거친 경로까지 이 한 곳이 받아낸다.

`const c = Object.assign({}, cfg);` **다음**, `_charEnsureDefaults` 호출 **앞**에 넣는다(순서가 바뀌면 커마에 헤어가 채워진다):

```js
  // ★미등록 커마는 기본 몸통으로 떨어뜨린다. 표에 없는 'face:xxx' 를 그대로 두면
  //   _charRenderTo 가 human 으로 폴백해 그리기는 하지만, 여기서 데이터도 맞춰야
  //   _charEnsureDefaults 가 엉뚱한 몸통 기준으로 옷을 벗기지 않는다.
  if (c.body) c.body = window._charEnsureFaceBody(c.body, null);
```

- [ ] **Step 7: 연결 확인 + 전체 스위트**

```bash
node -e "const s=require('fs').readFileSync('index.html','utf8'); const n=(s.match(/_charEnsureFaceBody\(/g)||[]).length; console.log('_charEnsureFaceBody 호출 '+n+'곳'); if(n<3) throw new Error('정의 1 + 호출 2곳 미만 — _usersAll 헬퍼와 _charSafe 연결이 빠졌다'); if(!/_charRegisterFaceBodiesFrom\(snap\)/.test(s)) throw new Error('_usersAll 에 등록이 안 걸렸다');"
node tools/module-syntax-check.mjs && node tools/dogam-syntax-check.mjs
for t in tools/tests/*.test.mjs; do node "$t" >/dev/null || echo "FAIL $t"; done; echo "끝"
```

- [ ] **Step 8: 커밋**

```bash
git add index.html tools/tests/face-body.test.mjs && \
git commit -m "feat(face): 남의 커마 캐릭터 렌더 — characterSheet 로 임시 몸통 등록, 없으면 기본 몸통 폴백"
```

---

### Task 4: 커마권 — 보유·구매(1,000머피)와 규칙 잠금

머피는 규칙상 **클라이언트가 못 올린다**(감소만 가능, 8-31 무한증액 사고 대응). 커마권도 같은 급이다. 그런데 구매는 "머피 -1000 · 커마권 +1" 이 한 쓰기에서 같이 일어나므로, 규칙이 **그 짝을 강제**하면 서버 없이도 안전하다.

**Files:**
- Modify: `index.html` — 상수·순수 계산·`faceTickets()`·`faceBuyTicket()`·부팅 시 보유량 읽기
- Modify: `firestore.rules` — users update 규칙에 커마권 절, `faceChars` 서브컬렉션 절
- Test: `tools/tests/face-ticket.test.mjs` (새로 만든다)

**Interfaces:**
- Consumes: `window.murpyConfirm`, `window.showToast`, `window._creditState`, `runTransaction`
- Produces:
  - `window.FACE_TICKET_PRICE` = 1000
  - `window._faceTicketBuyTx(balance, tickets)` → `{ ok, reason, credits, faceTickets }` (순수)
  - `window.faceTickets()` → number
  - `window.faceBuyTicket()` → async boolean

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`tools/tests/face-ticket.test.mjs`:

```js
// 커마권 구매 계산 — 잔액 판정과 짝(머피 -1000 / 커마권 +1)이 맞는지 본다
// 실행: node tools/tests/face-ticket.test.mjs
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
function grab(re, name) { const m = src.match(re); assert(m, `index.html에서 ${name}를 찾지 못함`); return m[0]; }
const w = { _charState: {} };
new Function('window', grab(/window\.FACE_TICKET_PRICE = [\s\S]*?\n\};(?=\nwindow\.faceTickets)/, '_faceTicketBuyTx'))(w);
new Function('window', grab(/window\.faceTickets = function[\s\S]*?\n\};/, 'faceTickets'))(w);

// 1) 가격은 상수 한 곳에서만 온다 (정식 전환 때 여기만 고친다)
assert.strictEqual(w.FACE_TICKET_PRICE, 1000, '커마권 가격 상수가 1000머피가 아니다');

// 2) 잔액이 되면 정확히 -1000 / +1
const ok = w._faceTicketBuyTx(1000, 0);
assert.strictEqual(ok.ok, true, '딱 맞는 잔액인데 구매가 막혔다');
assert.strictEqual(ok.credits, 0, '머피가 정확히 안 빠졌다');
assert.strictEqual(ok.faceTickets, 1, '커마권이 정확히 한 장 안 늘었다');

// 3) 잔액이 모자라면 아무것도 안 바뀐다
const no = w._faceTicketBuyTx(999, 3);
assert.strictEqual(no.ok, false, '잔액 부족인데 통과했다');
assert.strictEqual(no.reason, 'insufficient');

// 4) 이미 가진 장수 위에 쌓인다 (여러 개 보유 = 스펙)
const more = w._faceTicketBuyTx(2500, 2);
assert.strictEqual(more.credits, 1500); assert.strictEqual(more.faceTickets, 3);

// 5) 더러운 값(없음·문자열·음수)이 와도 0 으로 본다 — 규칙이 정수만 받는다
assert.strictEqual(w._faceTicketBuyTx(1000, undefined).faceTickets, 1);
assert.strictEqual(w._faceTicketBuyTx(1000, '5').faceTickets, 1, '문자열 보유량을 그대로 더했다');
assert.strictEqual(w._faceTicketBuyTx(1000, -4).faceTickets, 1, '음수 보유량을 그대로 더했다');

// 6) 보유 조회도 더러운 값에 안 넘어간다
w._charState.faceTickets = '3'; assert.strictEqual(w.faceTickets(), 0, '문자열 보유량을 그대로 보여준다');
w._charState.faceTickets = -1; assert.strictEqual(w.faceTickets(), 0);
w._charState.faceTickets = 2;  assert.strictEqual(w.faceTickets(), 2);

// 7) 규칙이 짝을 강제하는지 (규칙은 여기서 실행할 수 없으니 문자열로 본다)
const rules = readFileSync(join(root, 'firestore.rules'), 'utf8');
assert(/faceTickets/.test(rules), 'firestore.rules 에 커마권 잠금이 없다 — 무한 발급된다');
assert(/faceChars/.test(rules), 'firestore.rules 에 faceChars 규칙이 없다');

console.log('OK face-ticket 7항목');
```

- [ ] **Step 2: 실패를 확인한다**

```bash
node tools/tests/face-ticket.test.mjs
```

기대: FAIL — `_faceTicketBuyTx를 찾지 못함`

- [ ] **Step 3: 상수 + 순수 계산 + 조회를 넣는다 — Task 3 의 `_charEnsureFaceBody` 다음**

```js
// ===== 커마권 =====
// ★가격은 여기 한 곳에서만 온다. 정식 전환(19,900원 실결제)때 이 상수만 바꾼다.
window.FACE_TICKET_PRICE = 1000;
// 구매 계산(순수). 트랜잭션 안에서 이 결과대로 쓴다 — 계산과 쓰기를 섞으면 검증을 못 한다.
// ★머피와 커마권을 **한 쓰기로** 묶는 게 핵심이다. 규칙이 그 짝을 강제하므로
//   "머피는 안 내고 커마권만 +1" 이 원천 차단된다(8-31 무한증액 사고와 같은 급의 자산).
window._faceTicketBuyTx = function (balance, tickets) {
  const bal = Number.isFinite(Number(balance)) ? Math.trunc(Number(balance)) : 0;
  const have = (typeof tickets === 'number' && Number.isFinite(tickets) && tickets > 0) ? Math.trunc(tickets) : 0;
  const price = window.FACE_TICKET_PRICE;
  if (bal < price) return { ok: false, reason: 'insufficient', credits: bal, faceTickets: have };
  return { ok: true, reason: '', credits: bal - price, faceTickets: have + 1 };
};
window.faceTickets = function () {
  const n = window._charState && window._charState.faceTickets;
  return (typeof n === 'number' && Number.isFinite(n) && n > 0) ? Math.trunc(n) : 0;
};
```

- [ ] **Step 4: 구매 흐름을 모듈 블록에 넣는다 — Task 2 의 `_charLoadMyFaceChars` 옆**

```js
// 커마권 구매. 시착 구매(charTryOnBuy)와 같은 모양이다 — 확인창 → 트랜잭션 → 토스트.
// ★spendCredit 을 쓰지 않는 이유 = 그건 머피만 깎는다. 커마권 +1 을 **같은 트랜잭션**에
//   묶어야 규칙이 짝을 검사할 수 있다(따로 쓰면 커마권 단독 증가라 규칙이 막는다).
window.faceBuyTicket = async function () {
  const u = window.currentUser;
  if (!u) { window.requireLogin && requireLogin('커마권은 로그인이 필요해요'); return false; }
  const price = window.FACE_TICKET_PRICE;
  const ok = await window.murpyConfirm({
    title: '얼굴 커마권 구매',
    desc: '<b style="color:#F5C24B">' + price + '머피</b>로 커마권 한 장을 사요',
    cost: true, confirmText: '구매'
  });
  if (!ok) return false;
  try {
    const res = await runTransaction(db, async tx => {
      const ref = doc(db, 'users', u.uid);
      const snap = await tx.get(ref);
      const d = snap.exists() ? snap.data() : {};
      const r = window._faceTicketBuyTx(d.credits, d.faceTickets);
      if (!r.ok) return r;
      tx.update(ref, { credits: r.credits, faceTickets: r.faceTickets });
      return r;
    });
    if (!res.ok) { window.showToast && showToast('머피가 모자라요'); return false; }
    window._creditState.credits = res.credits;
    window._charState.faceTickets = res.faceTickets;
    if (window.renderCreditUI) window.renderCreditUI();
    if (window.mwUpdateCoin) window.mwUpdateCoin();
    window.showToast && showToast('커마권을 받았어요');
    return true;
  } catch (e) {
    console.error('faceBuyTicket', e);
    window.showToast && showToast('구매에 실패했어요');
    return false;
  }
};
```

- [ ] **Step 5: 보유 장수를 부팅 때 읽는다 — Task 2 Step 6 의 로더 호출 바로 위**

```js
      window._charState.faceTickets = (typeof d.faceTickets === 'number' && d.faceTickets > 0) ? Math.trunc(d.faceTickets) : 0;
```

- [ ] **Step 6: 규칙을 잠근다 — `firestore.rules` 의 `match /users/{userId}` 안 `allow update:` 절 전체를 이걸로 바꾼다**

```
      // ★커마권(faceTickets) = 머피와 같은 급의 자산이다. 클라가 그냥 못 올린다.
      //   유일하게 허용하는 클라 증가 = **머피를 정확히 값만큼 깎으면서 한 장 늘리는** 짝.
      //   짝을 규칙이 강제하므로 "돈 안 내고 커마권만 +1" 이 원천 차단된다.
      //   소모(생성)는 서버가 하지만, 클라가 스스로 줄이는 것은 손해라 허용한다.
      allow update: if isAdmin() || (isOwner(userId) && (
          !request.resource.data.diff(resource.data).affectedKeys().hasAny(['credits', 'faceTickets'])
          || (!('credits' in resource.data) && request.resource.data.credits is int
              && request.resource.data.credits <= 30
              && !request.resource.data.diff(resource.data).affectedKeys().hasAny(['faceTickets']))
          || (request.resource.data.faceTickets is int
              && request.resource.data.credits is int
              && request.resource.data.faceTickets == (('faceTickets' in resource.data) ? resource.data.faceTickets : 0) + 1
              && request.resource.data.credits == resource.data.credits - 1000)
          || (request.resource.data.credits is int
              && request.resource.data.credits <= resource.data.credits
              && (!request.resource.data.diff(resource.data).affectedKeys().hasAny(['faceTickets'])
                  || (request.resource.data.faceTickets is int
                      && request.resource.data.faceTickets <= (('faceTickets' in resource.data) ? resource.data.faceTickets : 0))))
      ));
```

같은 `match /users/{userId}` 블록 안, `match /private/{docId}` 옆에 서브컬렉션 절을 더한다:

```
      // 얼굴 커마 캐릭터. ★읽기는 공개다 — characterSheet 가 없는 구버전 경로에서
      //   남이 나를 그릴 때 필요하다. 쓰기는 관리자/서버만. 유저가 스스로 만들면
      //   커마권을 안 내고 캐릭터를 갖는다.
      match /faceChars/{charId} {
        allow read: if true;
        allow write: if isAdmin();
      }
```

- [ ] **Step 7: 테스트 통과를 확인한다**

```bash
node tools/tests/face-ticket.test.mjs
node tools/module-syntax-check.mjs && node tools/dogam-syntax-check.mjs
for t in tools/tests/*.test.mjs; do node "$t" >/dev/null || echo "FAIL $t"; done; echo "끝"
```

기대: `OK face-ticket 7항목` + FAIL 없음.

- [ ] **Step 8: 커밋**

```bash
git add index.html firestore.rules tools/tests/face-ticket.test.mjs && \
git commit -m "feat(face): 커마권 보유·구매(1,000머피) — 머피 차감과 한 트랜잭션, 규칙이 짝을 강제해 무한 발급 차단"
```

**★배포 주의:** 규칙은 코드와 별개로 게시해야 한다. 이 브랜치를 배포할 때 `python tools/deploy_firestore_rules.py` 로 규칙을 같이 올린다. 안 올리면 구매가 규칙에 막혀 전부 실패한다.

---

### Task 5: 관리자 커마 등록 — 만들어서 바로 지급

지금은 커마 캐릭터를 주려면 index.html 을 고치고 재배포해야 한다. 관리자 화면에서 문서 한 장을 만들면 그 사람이 앱을 다시 켤 때 바로 캐릭터를 갖는 상태로 바꾼다. 서버 자가생성이 붙기 전까지 이게 지급 경로다.

**시트 URL:** 베타 초기에는 Storage 업로드 없이 **저장소 파일 URL**(`https://murpy.app/char/faces/{id}.png`)을 그대로 쓴다. 로컬 파이프라인(`tools/face_pipeline.py`) 산출물을 브랜치에 커밋해 배포하면 바로 URL 이 생긴다. 서버가 붙으면 그 자리에 Storage URL 이 들어올 뿐 구조는 같다.

**Files:**
- Modify: `index.html` — 커마권 블록 끝, 기존 관리자 영역
- Test: `tools/tests/face-ticket.test.mjs`

**Interfaces:**
- Consumes: `isAdmin()`, `setDoc`, `updateDoc`, `increment`, `_charRegisterFaceBody`, `charRenderRoster`
- Produces:
  - `window._faceCharDocFrom(form)` → `{ ok, error, doc }` (순수)
  - `window.faceAdminGrant(uid, charId, form)` → async boolean
  - `window.faceAdminGrantTicket(uid, n)` → async boolean (베타 무료권 지급)

- [ ] **Step 1: 실패하는 테스트를 추가한다 — `console.log` 앞에**

```js
// 8) 관리자 입력 → Firestore 문서 조립
new Function('window', grab(/window\._faceCharDocFrom = function[\s\S]*?\n\};/, '_faceCharDocFrom'))(w);
const good = w._faceCharDocFrom({ name: '현수', sheetUrl: 'https://murpy.app/char/faces/hyunsu.png', skinPrefix: 'https://murpy.app/char/skin/face_hyunsu' });
assert.strictEqual(good.ok, true, '정상 입력이 막혔다: ' + good.error);
assert.strictEqual(good.doc.name, '현수');
assert.strictEqual(good.doc.sheetUrl, 'https://murpy.app/char/faces/hyunsu.png');
// 톤 5종이 규칙(t3 는 원본이라 없다)대로 조립된다
assert.deepStrictEqual(Object.keys(good.doc.skinUrls).sort(), ['t1','t2','t4','t5','t6']);
assert.strictEqual(good.doc.skinUrls.t4, 'https://murpy.app/char/skin/face_hyunsu_t4.png');
assert.strictEqual(good.doc.retryCount, 0, '재생성 횟수가 0 으로 안 시작한다');
// 이름은 1~12자
assert.strictEqual(w._faceCharDocFrom({ name: '', sheetUrl: 'https://a/b.png' }).ok, false, '빈 이름이 통과했다');
assert.strictEqual(w._faceCharDocFrom({ name: '가'.repeat(13), sheetUrl: 'https://a/b.png' }).ok, false, '13자 이름이 통과했다');
// 시트 URL 은 필수 + http(s) 만
assert.strictEqual(w._faceCharDocFrom({ name: 'x' }).ok, false, '시트 없이 통과했다');
assert.strictEqual(w._faceCharDocFrom({ name: 'x', sheetUrl: 'javascript:alert(1)' }).ok, false, 'javascript: URL 이 통과했다');
// 톤 접두사가 없으면 skinUrls 는 null (피부톤 탭이 "바꿀 수 없어요"로 떨어진다)
assert.strictEqual(w._faceCharDocFrom({ name: 'x', sheetUrl: 'https://a/b.png' }).doc.skinUrls, null);
// 이름에 금칙어가 있으면 막는다 (기존 닉네임 필터 재사용 — 없으면 이 assert 를 지운다)
if (typeof w._textBlocked === 'function') {
  assert.strictEqual(w._faceCharDocFrom({ name: '씨발', sheetUrl: 'https://a/b.png' }).ok, false, '금칙어 이름이 통과했다');
}
```

마지막 줄을 `console.log('OK face-ticket 18항목');` 으로 바꾼다.

- [ ] **Step 2: 실패를 확인한다**

```bash
node tools/tests/face-ticket.test.mjs
```

기대: FAIL — `_faceCharDocFrom를 찾지 못함`

- [ ] **Step 3: 구현 — 커마권 블록 끝(`faceTickets` 다음)**

```js
// 관리자 입력 → faceChars 문서. ★검증을 순수 함수로 빼둔다 — 화면 코드에 섞으면
//   "왜 안 들어갔지"를 앱을 켜야만 알 수 있다.
// ★URL 은 http(s) 만 받는다. javascript: 가 들어오면 그대로 <img src> 에 박힌다.
window._faceCharDocFrom = function (form) {
  const f = form || {};
  const name = String(f.name || '').trim();
  const sheetUrl = String(f.sheetUrl || '').trim();
  if (name.length < 1 || name.length > 12) return { ok: false, error: '이름은 1~12자예요', doc: null };
  // ★금칙어는 **새로 만들지 않는다.** main 병합으로 들어온 광장 외치기/닉네임 필터를 재사용한다.
  //   함수 이름은 병합 후 `grep -n "금칙\|외치기" index.html` 로 확인해 여기에 맞춘다.
  //   필터가 없으면 이 두 줄을 지운다(길이 제한만 남는다).
  if (window._textBlocked && window._textBlocked(name)) return { ok: false, error: '쓸 수 없는 이름이에요', doc: null };
  if (!/^https?:\/\//i.test(sheetUrl)) return { ok: false, error: '시트 주소가 http(s) 가 아니에요', doc: null };
  const pre = String(f.skinPrefix || '').trim();
  // t3 = 원본이라 굽지 않는다(CHAR_SKINS 주석 참고). 나머지 5종만 표를 만든다.
  const skinUrls = /^https?:\/\//i.test(pre)
    ? ['t1', 't2', 't4', 't5', 't6'].reduce(function (o, t) { o[t] = pre + '_' + t + '.png'; return o; }, {})
    : null;
  const eyes = (f.eyeY && f.eyeXL && f.eyeXR)
    ? { y: Number(f.eyeY), x: [Number(f.eyeXL), Number(f.eyeXR)] } : null;
  return { ok: true, error: '', doc: {
    name: name, sheetUrl: sheetUrl, skinUrls: skinUrls, eyes: eyes,
    retryCount: 0, createdAt: Date.now(), updatedAt: Date.now()
  } };
};
```

- [ ] **Step 4: 관리자 쓰기를 모듈 블록에 넣는다 — `faceBuyTicket` 옆**

```js
// 관리자 전용 지급. 서버 자가생성이 붙기 전까지 이게 유일한 지급 경로다.
// ★규칙상 faceChars 쓰기는 isAdmin() 만 통과한다 — 유저 계정으로는 실패한다(정상).
window.faceAdminGrant = async function (uid, charId, form) {
  if (!isAdmin()) { window.showToast && showToast('관리자만 할 수 있어요'); return false; }
  const r = window._faceCharDocFrom(form);
  if (!r.ok) { window.showToast && showToast(r.error); return false; }
  const id = String(charId || '').trim();
  if (!/^[a-z0-9_-]{2,24}$/.test(id)) { window.showToast && showToast('charId 는 영문 소문자·숫자 2~24자예요'); return false; }
  const to = String(uid || '').trim();
  if (!to) { window.showToast && showToast('받는 사람 uid 가 없어요'); return false; }
  try {
    await setDoc(doc(db, 'users', to, 'faceChars', id), r.doc);
    window.showToast && showToast('커마 캐릭터를 지급했어요');
    if (to === (window.currentUser && window.currentUser.uid)) {
      window._charState.faceChars[id] = r.doc;
      window._charRegisterFaceBody(id, r.doc, to);
      if (window.charRenderRoster) window.charRenderRoster();
    }
    return true;
  } catch (e) { console.error('faceAdminGrant', e); window.showToast && showToast('지급에 실패했어요'); return false; }
};
// 베타 무료권 지급(스펙 9장). 근방단 스쿼드 참여·친구초대 차등은 **사람이 판단**하고
// 여기서 장수만 넣는다. 자동 집계는 친구초대 스펙 소관이다.
// ★관리자만 통과한다 — 규칙의 isAdmin() 절이 커마권 단독 증가를 허용하는 유일한 길이다.
window.faceAdminGrantTicket = async function (uid, n) {
  if (!isAdmin()) { window.showToast && showToast('관리자만 할 수 있어요'); return false; }
  const to = String(uid || '').trim();
  const cnt = Math.trunc(Number(n));
  if (!to || !Number.isFinite(cnt) || cnt < 1 || cnt > 10) { window.showToast && showToast('uid 와 1~10 사이 장수가 필요해요'); return false; }
  try {
    await updateDoc(doc(db, 'users', to), { faceTickets: increment(cnt) });
    window.showToast && showToast('커마권 ' + cnt + '장을 지급했어요');
    if (to === (window.currentUser && window.currentUser.uid)) {
      window._charState.faceTickets = window.faceTickets() + cnt;
      if (window.charRenderRoster) window.charRenderRoster();
    }
    return true;
  } catch (e) { console.error('faceAdminGrantTicket', e); window.showToast && showToast('지급에 실패했어요'); return false; }
};
```

- [ ] **Step 5: 관리자 카드를 기존 관리자 영역에 붙인다**

기존 관리자 도구가 모여 있는 자리를 찾는다(`charRenderRoster` 끝의 `mw-hidden-admtest` 블록이 가장 가깝다). **새 탭·새 화면을 만들지 않는다.** 그 블록 바로 뒤에:

```js
  // 관리자 전용: 커마 캐릭터 지급 (서버 자가생성 전까지의 지급 경로)
  let fadm = document.getElementById('mw-face-admin');
  if (typeof isAdmin === 'function' && isAdmin()) {
    if (!fadm) { fadm = document.createElement('div'); fadm.id = 'mw-face-admin'; (adm || grid).after(fadm); }
    fadm.style.cssText = 'margin-top:14px;display:grid;gap:6px';
    fadm.innerHTML = '<span style="width:100%;font-size:10px;color:#4a5266">관리자 커마 지급</span>'
      + ['fa-uid:받는 사람 uid', 'fa-id:charId (영문 소문자)', 'fa-name:캐릭터 이름 (1~12자)',
         'fa-sheet:시트 주소 https://murpy.app/char/faces/xxx.png', 'fa-skin:톤 접두사 (비우면 피부톤 없음)']
        .map(function (s) { const p = s.split(':'); const id = p.shift();
          return '<input id="' + id + '" placeholder="' + p.join(':') + '" style="background:none;border:1px solid rgba(255,255,255,0.18);border-radius:8px;padding:8px 10px;color:#cfd6e6;font-size:11.5px;font-family:inherit">'; }).join('')
      + '<button class="mw-btn mw-btn-sm" onclick="window.faceAdminGrant('
      + "document.getElementById('fa-uid').value,document.getElementById('fa-id').value,"
      + "{name:document.getElementById('fa-name').value,sheetUrl:document.getElementById('fa-sheet').value,skinPrefix:document.getElementById('fa-skin').value})\">캐릭터 지급</button>"
      // 베타 무료권(스펙 9장) — 스쿼드 참여·친구초대 차등은 대표가 보고 장수만 넣는다
      + '<button class="mw-btn mw-btn-sm mw-btn-ghost" onclick="window.faceAdminGrantTicket('
      + "document.getElementById('fa-uid').value, 1)\">커마권 1장 지급</button>";
  } else if (fadm) { fadm.remove(); }
```

입력창은 틴트 칩 금지 규칙대로 `background:none` + 테두리 + 글자색이다.

- [ ] **Step 6: 테스트 + 스위트 확인**

```bash
node tools/tests/face-ticket.test.mjs
node tools/module-syntax-check.mjs && node tools/dogam-syntax-check.mjs
for t in tools/tests/*.test.mjs; do node "$t" >/dev/null || echo "FAIL $t"; done; echo "끝"
```

기대: `OK face-ticket 18항목` + FAIL 없음.

- [ ] **Step 7: 커밋**

```bash
git add index.html tools/tests/face-ticket.test.mjs && \
git commit -m "feat(face): 관리자 커마 지급 — faceChars 문서 한 장으로 재배포 없이 즉시 지급"
```

---

### Task 6: 진입점과 광고 팝업 — 만들 수 있다는 걸 알린다

기능이 있어도 도달할 길이 없으면 죽은 코드다(센터 탭 전례). 로스터에 진입점을 두고, 기존 머피월드 홍보 팝업 패턴을 복제해 커마를 알린다.

**Files:**
- Modify: `index.html` — 커마권 블록 끝, `charRenderRoster`(현 8885행) 끝, `showMwPromo`(현 15886행) 옆
- Test: `tools/tests/face-ticket.test.mjs`

**Interfaces:**
- Consumes: `faceTickets()`, `faceBuyTicket()`, `_charState.faceChars`, `_cachedProfile`
- Produces: `window._faceEntryState(tickets, hasChar, faceVerified, hasPhoto)` → `{ mode, label, desc }` (순수)

- [ ] **Step 1: 실패하는 테스트를 추가한다 — `console.log` 앞에**

```js
// 9) 진입 버튼이 상황마다 뭘 말해야 하는가 (스펙 4장 흐름)
new Function('window', grab(/window\._faceEntryState = function[\s\S]*?\n\};/, '_faceEntryState'))(w);
assert.strictEqual(w._faceEntryState(0, false, true, true).mode, 'buy', '티켓 0장인데 상점으로 안 보낸다');
assert.strictEqual(w._faceEntryState(1, false, false, true).mode, 'verify', '인증 없이 생성으로 보낸다');
assert.strictEqual(w._faceEntryState(1, false, false, false).mode, 'photo', '사진 없이 인증으로 보낸다');
assert.strictEqual(w._faceEntryState(1, false, true, true).mode, 'create', '조건이 다 됐는데 생성으로 안 간다');
assert.strictEqual(w._faceEntryState(0, true, true, true).mode, 'buy', '이미 있어도 더 만들려면 티켓이 필요하다');
// 문구에 이모지가 없어야 한다 (머피 UI 규칙)
for (const m of [[0,false,true,true],[1,false,false,true],[1,false,false,false],[1,false,true,true]]) {
  const s = w._faceEntryState.apply(null, m);
  assert(!/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u.test(s.label + s.desc), '진입 문구에 이모지가 있다: ' + s.label);
}
```

마지막 줄을 `console.log('OK face-ticket 27항목');` 으로 바꾼다.

- [ ] **Step 2: 실패를 확인한다**

```bash
node tools/tests/face-ticket.test.mjs
```

기대: FAIL — `_faceEntryState를 찾지 못함`

- [ ] **Step 3: 구현 — 커마권 블록 끝(`_faceCharDocFrom` 다음)**

```js
// 로스터 진입 버튼이 지금 무엇을 해야 하는가. ★분기를 순수 함수로 빼는 이유 =
//   "티켓은 있는데 인증이 없다" 같은 조합이 화면 코드에 흩어지면 한 화면만 고쳐진다.
// 순서가 곧 이탈 방어다: 티켓 없음 → 상점 / 사진 없음 → 사진 등록 / 인증 없음 → 인증 / 다 되면 생성.
window._faceEntryState = function (tickets, hasChar, faceVerified, hasPhoto) {
  if (!(tickets > 0)) return { mode: 'buy', label: '커마권 사기',
    desc: '내 얼굴로 캐릭터를 만들 수 있어요 · ' + window.FACE_TICKET_PRICE + '머피' };
  if (!hasPhoto) return { mode: 'photo', label: '사진 먼저 등록하기',
    desc: '내 얼굴이 맞는지 확인하려면 사진이 한 장 필요해요' };
  if (!faceVerified) return { mode: 'verify', label: '얼굴 인증하기',
    desc: '본인만 만들 수 있어요 · 사진은 저장하지 않아요' };
  return { mode: 'create', label: '내 얼굴로 만들기',
    desc: '커마권 ' + tickets + '장 있어요' };
};
```

- [ ] **Step 4: 로스터에 진입 카드를 붙인다 — Task 5 의 관리자 블록 앞**

```js
  // 커마 진입 — ★새 화면을 만들지 않는다. 상황에 따라 기존 흐름으로 보낼 뿐이다.
  let fe = document.getElementById('mw-face-entry');
  if (!fe) { fe = document.createElement('div'); fe.id = 'mw-face-entry'; grid.after(fe); }
  const _prof = window._cachedProfile || {};
  const _hasPhoto = !!(_prof.photoURL || (_prof.photos || []).length);
  const _hasChar = Object.keys((window._charState || {}).faceChars || {}).length > 0;
  const _st = window._faceEntryState(window.faceTickets(), _hasChar, !!_prof.faceVerified, _hasPhoto);
  const _act = _st.mode === 'buy' ? 'window.faceBuyTicket().then(function(o){ if(o) window.charRenderRoster(); })'
             : _st.mode === 'photo' ? 'window.goEditProfile && window.goEditProfile()'
             : _st.mode === 'verify' ? 'window.startFaceVerify()'
             : 'window.faceStartCreate && window.faceStartCreate()';
  fe.style.cssText = 'margin-top:14px';
  fe.innerHTML = '<button class="mw-btn" style="width:100%" onclick="' + _act + '">' + _st.label + '</button>'
    + '<div style="margin-top:6px;font-size:11px;color:#4a5266;text-align:center">' + _st.desc + '</div>';
```

`goEditProfile` 이 없으면 프로필 편집으로 가는 기존 함수를 찾아 바꾼다:

```bash
grep -n "프로필 수정\|editProfile\|goProfileEdit" index.html | head
```

`faceStartCreate` 는 서버 계획(Phase A-2)에서 생긴다. 지금은 없으므로 `create` 모드에서 아무 일도 안 일어난다 — **의도된 상태다**(관리자 지급이 지급 경로다).

- [ ] **Step 5: 광고 팝업을 붙인다 — 기존 패턴을 복제한다**

```bash
sed -n '/function showMwPromo/,/^}/p' index.html | head -60
grep -n "_charMiniHTML" index.html | head -3
```

같은 구조로 `showFacePromo` 를 만든다:
- 히어로 = `window._charMiniHTML('jaejin', 96)` + `window._charMiniHTML('paesuhyun', 96)` 나란히 (실물을 보여줘 가치를 먼저 납득시킨다)
- CTA "내 얼굴로 만들기" → 꾸미기 로스터로 보낸다(위 진입 버튼이 나머지를 판단한다)
- **이미 커마 캐릭터가 있으면 안 뜬다**: 맨 위에 `if (Object.keys((window._charState||{}).faceChars||{}).length) return;`
- 트리거는 기존 홍보 팝업과 동일(탭 3번 이상·세션당 1회·최대 3회). 상태 키만 `facePromoSeen` 으로 분리한다
- 이모지 금지·틴트 칩 금지

- [ ] **Step 6: 테스트 + 스위트 확인**

```bash
node tools/tests/face-ticket.test.mjs
node tools/module-syntax-check.mjs && node tools/dogam-syntax-check.mjs
for t in tools/tests/*.test.mjs; do node "$t" >/dev/null || echo "FAIL $t"; done; echo "끝"
```

기대: `OK face-ticket 27항목` + FAIL 없음.

- [ ] **Step 7: 커밋**

```bash
git add index.html tools/tests/face-ticket.test.mjs && \
git commit -m "feat(face): 로스터 커마 진입점 + 광고 팝업 — 상황별로 상점·사진·인증·생성으로 보낸다"
```

---

### Task 7: 배포 준비 — 버전 올리기와 실기기 확인 목록

**Files:**
- Modify: `index.html`(`_SW_V`), `sw.js`(`murpy-vNNN` 3곳) — **손으로 고치지 말고 `tools/bump-version.mjs` 가 올린다**

- [ ] **Step 1: main 을 다시 병합한다 (반대 창이 계속 배포 중이다)**

```bash
git fetch origin && git merge origin/main
```

병합 후 이 브랜치의 커마 코드 5개 심볼이 살아 있는지 확인한다:

```bash
node -e "const s=require('fs').readFileSync('index.html','utf8'); for(const k of ['_charFaceBodyDef','_charRegisterFaceBody','_charEnsureFaceBody','_faceTicketBuyTx','_faceEntryState']) if(!s.includes('window.'+k)) throw new Error('병합이 지웠다: '+k); console.log('OK 커마 심볼 5종');"
```

- [ ] **Step 2: 문법 검사 2종 + 전체 테스트 (버전 올리기 전에)**

```bash
node tools/module-syntax-check.mjs && node tools/dogam-syntax-check.mjs
for t in tools/tests/*.test.mjs; do node "$t" >/dev/null || echo "FAIL $t"; done; echo "끝"
```

기대: 문법 검사 둘 다 통과 + FAIL 줄 없음.

- [ ] **Step 3: 버전을 올린다 — 도구가 세 곳을 한 번에 바꾼다**

현재 번호를 보고 +1 한다:

```bash
grep -n "_SW_V" index.html | head -3
node tools/bump-version.mjs <현재+1>
```

`_SW_V` 대입은 반드시 **한 곳**이어야 한다(두 곳이라 48개 빌드가 폰에 안 간 655 사고).

- [ ] **Step 4: 버전 검사**

```bash
PYTHONIOENCODING=utf-8 python tools/check_version.py
```

기대: 세 곳이 같은 숫자, 대입 1곳.

- [ ] **Step 5: 커밋**

```bash
git add index.html sw.js version.txt && git commit -m "chore: sw v<N> — 얼굴 커마권 클라이언트"
```

- [ ] **Step 6: 규칙 게시 (코드와 별개다)**

```bash
python tools/deploy_firestore_rules.py
```

OAuth 클릭이 한 번 필요하다(이 PC 의 firebase CLI 토큰은 만료돼 있다 — 대표가 `firebase login --reauth` 를 해 두면 `firebase deploy --only firestore:rules` 도 쓸 수 있다).
**안 올리면 커마권 구매가 전부 규칙에 막혀 실패한다.**

- [ ] **Step 7: 대표 확인 목록**

실기기(아이폰)에서 봐야 하는 것:
1. 꾸미기 로스터 아래 진입 버튼이 "커마권 사기 · 1,000머피"로 뜨는가
2. 구매 후 버튼이 "내 얼굴로 만들기 · 커마권 1장"으로 바뀌고 머피가 정확히 1,000 빠졌는가
3. 관리자 지급 후 앱을 다시 켜면 로스터에 커마 캐릭터가 뜨고 **착용이 되는가**
4. 착용한 커마가 **오버월드·피드·프로필 카드**에서 남에게도 커마로 보이는가
5. 커마를 입은 채 상의·하의·신발을 갈아입어도 몸이 안 깨지는가 (헤어·모자 탭은 잠겨 있어야 한다)
6. 피부톤 탭에서 5단계가 뜨고 눌리는가 (톤 접두사를 넣은 경우)

---

## 다음 계획 (Phase A-2, 별도 문서)

- 셀카 → 시트 자가생성 서버: Firebase Functions(제미나이 Pro 2K · `imageSize:2K` · `aspectRatio:9:16`) + Secret Manager
- 웹캠 캡처 흐름(`faceStartCreate`) — 파일 업로드 경로 없이 프로필 대조 통과 프레임만
- 티켓 선차감·실패 시 환불, `retryCount` 서버 강제(무료 재생성 2회)
- 눈 좌표 자동 실측(`tools/face_eyes.py` → 서버 포팅) — 지금은 없으면 human 좌표로 폴백한다
- **커마 캐릭터 삭제**(스펙 6장) — 삭제하면 착용 중인 사람을 base 몸통으로 되돌린다. Plan A 에는 삭제 UI 자체가 없어 미룬다(관리자가 문서를 지우는 것 외에 삭제 경로가 없다).
- **캐릭터 이름 욕설 필터**(스펙 6장) — 이 저장소엔 욕설 필터가 **없다**. Task 5 가 태운 `_hasContact` 는 연락처 필터(@·카톡·010·라인)라 욕설을 하나도 안 막는다. 유저가 직접 이름을 짓는 A-2 흐름과 같이 만들어야 한다.
- **죽은 시트 URL 방어**(스펙 6장) — 지금은 URL 이 **없을 때**만 base 로 폴백한다. URL 이 있는데 404 면 배경 이미지가 조용히 비므로, 시트를 `new Image()` 로 한 번 확인해 실패하면 몸통 등록을 취소하는 처리를 A-2 에서 붙인다.
- 피부톤 5종 서버 굽기 + Storage 업로드, `storage.rules` 에 `faces/{uid}/` 절 추가
- **선행 조건(대표 손):** `firebase login --reauth`(현재 토큰 만료), Blaze 요금제·Secret Manager 확인, 서버 언어 결정(Python 2차 코드베이스 vs 기존 Node 코드베이스 포팅)
