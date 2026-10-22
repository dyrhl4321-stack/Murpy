# 크루 아지트 같이 걷기·채팅 시험(10-22) — 실서비스 실시간 DB 에 아무것도 안 쓴다.
#   window._rt 를 메모리 가짜(같은 브라우저 안 탭끼리 BroadcastChannel 로 나눠 가짐)로 바꿔 두 사람을 띄우고 확인한다:
#   ① 서로 보인다 ② 걸으면 상대 화면에서 자리가 바뀐다 ③ 말하면 상대 화면 대화 줄·말풍선 ④ 나가면 사라지고 seen 이 남는다
#   ⑤ 정원 30 — 이미 30명이면 구경만(내 노드 안 씀) ⑥ 흐린 최근 방문자 = 7일 안 seen ⑦ 꾸미기 저장 실패(규칙 없음) 시 편집 상태 유지
#   사용: python tools/agit_live_test.py [캡처 폴더]
import sys, os, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else None
class _Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(_Q, directory=ROOT))
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

MOCK = r'''
() => {
  const bc = new BroadcastChannel('agit-mock'), tree = {}, subs = [];
  const parts = p => p.split('/').filter(Boolean);
  const getAt = p => parts(p).reduce((o, k) => (o && typeof o === 'object') ? o[k] : undefined, tree);
  const clone = v => v === undefined ? undefined : JSON.parse(JSON.stringify(v));
  const snap = (key, v) => ({ key, val: () => clone(v === undefined ? null : v), exists: () => v !== undefined && v !== null });
  function setAt(p, v) {
    const ks = parts(p); let o = tree;
    for (let i = 0; i < ks.length - 1; i++) { if (!o[ks[i]] || typeof o[ks[i]] !== 'object') o[ks[i]] = {}; o = o[ks[i]]; }
    if (v === null || v === undefined) delete o[ks[ks.length - 1]]; else o[ks[ks.length - 1]] = clone(v);
  }
  function apply(op, remote) {
    const before = subs.map(s => clone(getAt(s.path)));
    if (op.t === 'set') setAt(op.p, op.v);
    else if (op.t === 'update') Object.keys(op.v).forEach(k => setAt(op.p + '/' + k, op.v[k]));
    else if (op.t === 'remove') setAt(op.p, null);
    if (!remote) bc.postMessage(op);
    subs.forEach((s, i) => {
      const a = before[i] || {}, b = clone(getAt(s.path));
      if (s.kind === 'value') { if (JSON.stringify(a) !== JSON.stringify(b === undefined ? {} : b) || s.first) { s.first = false; } s.cb(snap(s.path, s.n ? lastN(b, s.n) : b)); return; }
      const bb = b || {};
      Object.keys(bb).forEach(k => { if (!(k in a)) s.kind === 'added' && s.cb(snap(k, bb[k])); else if (JSON.stringify(a[k]) !== JSON.stringify(bb[k])) s.kind === 'changed' && s.cb(snap(k, bb[k])); });
      Object.keys(a).forEach(k => { if (!(k in bb)) s.kind === 'removed' && s.cb(snap(k, a[k])); });
    });
  }
  const lastN = (v, n) => { if (!v) return v; const ks = Object.keys(v).sort().slice(-n), o = {}; ks.forEach(k => o[k] = v[k]); return o; };
  bc.onmessage = e => { if (e.data && e.data.t === 'sync?') bc.postMessage({ t: 'sync', tree }); else if (e.data && e.data.t === 'sync') { Object.assign(tree, clone(e.data.tree)); } else apply(e.data, true); };
  bc.postMessage({ t: 'sync?' });
  let seq = 0;
  const on = kind => (ref, cb) => {
    const s = { kind, path: ref.path, n: ref.n, cb }; subs.push(s);
    const v = getAt(ref.path);
    if (kind === 'added' && v) Object.keys(v).forEach(k => cb(snap(k, v[k])));
    if (kind === 'value') cb(snap(ref.path, ref.n ? lastN(v, ref.n) : v));
    return () => { const i = subs.indexOf(s); if (i >= 0) subs.splice(i, 1); };
  };
  const disc = {};
  window.__mockTree = tree;
  window.__mockDisconnect = () => Object.values(disc).forEach(f => f());
  window._rt = {
    db: {}, ref: (db, path) => ({ path }), set: (r, v) => apply({ t: 'set', p: r.path, v }), update: (r, v) => apply({ t: 'update', p: r.path, v }),
    remove: r => apply({ t: 'remove', p: r.path }), get: r => Promise.resolve(snap(r.path, getAt(r.path))),
    onChildAdded: on('added'), onChildChanged: on('changed'), onChildRemoved: on('removed'), onValue: on('value'),
    query: (r, q) => ({ path: r.path, n: q.n }), limitToLast: n => ({ n }),
    push: r => ({ path: r.path + '/m' + Date.now().toString(36) + (seq++) + Math.random().toString(36).slice(2, 6) }),
    onDisconnect: r => ({ remove: () => { disc[r.path] = () => apply({ t: 'remove', p: r.path }); }, set: v => { disc[r.path + '#'] = () => apply({ t: 'set', p: r.path, v }); },
      update: v => { disc[r.path + '#u'] = () => apply({ t: 'update', p: r.path, v }); }, cancel: () => { delete disc[r.path]; delete disc[r.path + '#']; delete disc[r.path + '#u']; } }),
  };
}
'''
PICK = r'''
async () => {
  for (let i = 0; i < 60 && typeof window.crewHotList !== 'function'; i++) await new Promise(r => setTimeout(r, 500));
  const list = await window.crewHotList(); const c = list.find(x => (x.name || '').includes('근손실')) || list[0];
  for (let i = 0; i < 4; i++) {   // 프로필 읽기가 가끔 늦게/비어서 온다 — 5명 다 올 때까지 다시
    window.__AG = await window.crewAgitLoad(c.id);
    if (Object.keys(window.__AG.profiles).length >= 4) break;
    await new Promise(r => setTimeout(r, 1500));
  }
  return Object.keys(window.__AG.profiles);
}
'''
def enter(pg, uid):
    pg.evaluate('''(uid) => { const d = window.__AG, P = d.profiles[uid];
      window.crewAgitMount(d, { uid, nick: P.nickname, cfg: P.character }); window._agLiveJoin(); }''', uid)
    pg.wait_for_timeout(500)

def others(pg):
    return pg.evaluate("() => Object.fromEntries(Object.entries(window._agit.others).map(([k, v]) => [k, [v.tc, v.tr, v.face, !!v.ghost, v.msg || '']]))")

ok = True
def check(name, cond, extra=''):
    global ok
    print(('PASS ' if cond else 'FAIL ') + name + (('  ' + str(extra)) if extra else ''))
    ok = ok and bool(cond)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
    pages = []
    for i in range(2):
        pg = ctx.new_page()
        pg.goto('http://127.0.0.1:%d/index.html' % port, wait_until='domcontentloaded')
        pg.wait_for_function('typeof window.crewAgitMount === "function"', timeout=60000)
        pages.append(pg)
    for pg in pages:
        pg.wait_for_timeout(5000)
        pg.evaluate(MOCK)
    uids = pages[0].evaluate(PICK); pages[1].evaluate(PICK)
    A, B = uids[0], uids[1]
    pa, pb = pages
    # 지난주 다녀간 사람(흐린 방문자 후보) — 세 번째 크루원
    pa.evaluate("([u]) => window._rt.set(window._rt.ref(0, 'crewLive/' + window.__AG.crew.id + '/seen/' + u), Date.now() - 3 * 3600e3)", [uids[2]])
    pa.evaluate("([u]) => window._rt.set(window._rt.ref(0, 'crewLive/' + window.__AG.crew.id + '/seen/' + u), Date.now() - 9 * 864e5)", [uids[3]])
    pa.wait_for_timeout(200)
    enter(pa, A); enter(pb, B)
    pa.wait_for_timeout(600)
    oa, ob = others(pa), others(pb)
    check('① A 화면에 B 가 보인다', B in oa and not oa[B][3], oa.get(B))
    check('① B 화면에 A 가 보인다', A in ob and not ob[A][3], ob.get(A))
    check('⑥ 3시간 전 방문자는 흐리게 보인다', uids[2] in oa and oa[uids[2]][3], oa.get(uids[2]))
    check('⑥ 9일 전 방문자는 안 보인다', uids[3] not in oa)
    # 걷기
    before = ob[A][:2]
    for _ in range(3): pa.evaluate('() => window.crewAgitStep(1, 0)'); pa.wait_for_timeout(170)
    pb.wait_for_timeout(500)
    ob = others(pb)
    check('② A 가 오른쪽으로 걸으면 B 화면에서 자리가 바뀐다', ob[A][0] > before[0] and ob[A][2] == 'right', (before, ob[A]))
    # 말하기
    pa.evaluate("() => window.crewAgitSay('오늘 하체 누구?')"); pb.wait_for_timeout(400)
    ob = others(pb)
    lines = pb.evaluate("() => [...document.querySelectorAll('.ag-lines p')].map(p => p.textContent)")
    check('③ B 화면 A 머리 위 말풍선', ob[A][4] == '오늘 하체 누구?', ob[A])
    check('③ B 화면 대화 줄', any('오늘 하체 누구?' in l for l in lines), lines)
    xss = "<img src=x onerror=window.__x=1>"
    pa.evaluate("(t) => window.crewAgitSay(t)", xss); pb.wait_for_timeout(400)
    check('③ 대화·말풍선 글자는 HTML 로 안 들어간다', pb.evaluate('() => !window.__x && !document.querySelector(".ag-lines img, .ag-ch .bb img")'))
    if OUT:
        os.makedirs(OUT, exist_ok=True); pb.screenshot(path=os.path.join(OUT, 'live_B.png'))
    pb.wait_for_timeout(6300)
    ob = others(pb)
    check('③ 말풍선은 6초 뒤 사라진다', ob[A][4] == '', ob[A])
    # 정원 30
    pb.evaluate('''() => { const id = window.__AG.crew.id, now = Date.now();
      for (let i = 0; i < 29; i++) window._rt.set(window._rt.ref(0, 'crewLive/' + id + '/players/fake' + i), { tc: 3 + i % 20, tr: 20, face: 'down', t: now, nick: 'f' + i }); }''')
    pc = ctx.new_page(); pc.goto('http://127.0.0.1:%d/index.html' % port, wait_until='domcontentloaded')
    pc.wait_for_function('typeof window.crewAgitMount === "function"', timeout=60000); pc.wait_for_timeout(5000); pc.evaluate(MOCK); pc.wait_for_timeout(400); pc.evaluate(PICK)
    enter(pc, uids[4] if len(uids) > 4 else uids[2]); pc.wait_for_timeout(500)
    full = pc.evaluate("() => [!!window._agit.full, !window._agit.meRef, document.querySelector('.ag-tt span').textContent]")
    check('⑤ 31번째는 구경만(내 노드 안 씀)', full[0] and full[1], full)
    pc.close()
    pb.evaluate('''() => { const id = window.__AG.crew.id; for (let i = 0; i < 29; i++) window._rt.remove(window._rt.ref(0, 'crewLive/' + id + '/players/fake' + i)); }''')
    # 나가기
    pa.evaluate('() => window.crewAgitClose()'); pb.wait_for_timeout(400)
    ob = others(pb)
    check('④ A 가 나가면 B 화면에서 사라지고 흐린 방문자로 남는다', A in ob and ob[A][3], ob.get(A))
    # 꾸미기 저장 실패(규칙이 아직 없다 = 모두 거부) → 편집 상태 유지
    pb.evaluate('''() => { const S = window._agit; S.canEdit = true; window.crewAgitEdit(); window.crewAgitAdd('cz_flag'); }''')
    pb.evaluate('() => window.crewAgitEditDone(true)'); pb.wait_for_timeout(2500)
    st = pb.evaluate("() => [!!window._agit.editing, !!document.querySelector('.ag-tray')]")
    check('⑦ 저장이 거부되면 꾸미던 상태가 그대로 남는다', st[0] and st[1], st)
    pb.evaluate('() => window.crewAgitEditDone(false)')
    st = pb.evaluate("() => [!!window._agit.editing, window._agit.room.f.filter(x => x.id === 'cz_flag').length]")
    check('⑦ 취소하면 놓았던 깃발이 빠진다(원래 2개)', (not st[0]) and st[1] == 2, st)
    # 역할 — 크루장(leaderUid, 없으면 createdBy)·운영진(staff)만 꾸미기. 관리자 아님 상태에서.
    r = pb.evaluate('''() => { const f = window.crewAgitCanEdit;
      return [f({ createdBy: 'L', staff: ['S'] }, 'L'), f({ createdBy: 'L', staff: ['S'] }, 'S'), f({ createdBy: 'L', staff: ['S'] }, 'M'),
              f({ leaderUid: 'N', createdBy: 'L' }, 'L'), f({ leaderUid: 'N', createdBy: 'L' }, 'N'), f({ createdBy: 'L' }, '')]; }''')
    check('역할: 크루장·운영진 O / 크루원 X / leaderUid 가 createdBy 보다 먼저 / 로그인 전 X', r == [True, True, False, False, True, False], r)
    # 입장 판정 — 크루 없음(크루원 아님)·크루원·승인 대기·닫힘·관리자
    g = pb.evaluate('''() => { const G = window.crewAgitGate;
      return [G({ crew: {}, isMember: false }, false), G({ crew: {}, isMember: true }, false), G({ crew: { status: 'approved' }, isMember: true }, false),
              G({ crew: { status: 'pending' }, isMember: true }, false), G({ crew: { status: 'closed' }, isMember: true }, false),
              G({ crew: { status: 'closed' }, isMember: false }, true)]; }''')
    check('입장: 크루원 아님 X · 크루원 O · 승인 O · 승인 대기 X · 닫힘 X · 관리자 O',
          g == ['크루원만 들어갈 수 있어요', '', '', '승인된 크루만 아지트가 열려요', '닫힌 크루예요', ''], g)
    # 잘못된 입력 — 대화
    cnt = "() => Object.keys(((window.__mockTree.crewLive || {})[window.__AG.crew.id] || {}).chat || {}).length"
    n0 = pb.evaluate(cnt)
    pb.evaluate("() => { window._agit.lastSay = 0; window.crewAgitSay(''); window.crewAgitSay('    '); }")
    check('입력: 빈 말·공백만은 안 보낸다', pb.evaluate(cnt) == n0)
    pb.evaluate("() => { window._agit.lastSay = 0; window.crewAgitSay('가'.repeat(200)); }")
    last = pb.evaluate("() => { const c = window.__mockTree.crewLive[window.__AG.crew.id].chat; return Object.values(c).sort((a, b) => a.t - b.t).pop().text.length; }")
    check('입력: 긴 말은 60자로 자른다', last == 60, last)
    n1 = pb.evaluate(cnt)
    pb.evaluate("() => { window.crewAgitSay('연타1'); window.crewAgitSay('연타2'); }")
    check('입력: 1.2초 안 연타는 막는다', pb.evaluate(cnt) == n1, pb.evaluate(cnt) - n1)
    # 잘못된 입력 — 크루 이름(배너)·저장된 배치
    r = pb.evaluate('''() => { const d = window.__AG, P = d.profiles, u = Object.keys(P)[0];
      const bad = Object.assign({}, d, { crew: Object.assign({}, d.crew, { name: '<img src=x onerror=window.__y=1>아주아주긴크루이름입니다' }),
        hideout: { theme: 'nope', v: 3, f: [{ id: 'bogus', x: 1, y: 1 }, { id: 'cz_flag', x: 'abc', y: 5 }, { id: 'cz_flag', x: 99999, y: -500 }, null,
          { id: 'cz_banner', x: 600, y: 900 }].concat(Array.from({ length: 300 }, (_, i) => ({ id: 'pi_plant', x: (i * 50) % 1400, y: 300 + (i % 20) * 70 }))) } });
      window.crewAgitMount(bad, { uid: u, nick: P[u].nickname, cfg: P[u].character });
      const f = window._agit.room.f, lbl = document.querySelector('.ag-lbl');
      const ban = f.find(x => x.id === 'cz_banner'), fl = f.find(x => x.id === 'cz_flag');
      return [f.length, f.some(x => x.id === 'bogus'), !!document.querySelector('.ag-lbl img') || !!window.__y, lbl ? lbl.textContent : '',
              ban ? ban.y + 160 <= 176 : null, fl ? (fl.x <= 1536 - 92 && fl.y >= 0) : null, window._agit.room.theme]; }''')
    check('입력: 배치 120개 상한 · 모르는 소품 버림', r[0] <= 120 and not r[1], r[:2])
    check('입력: 크루 이름 HTML 은 글자로만 · 8자 넘으면 자름', (not r[2]) and r[3].endswith('…'), r[2:4])
    check('입력: 벽걸이는 벽 안으로 · 바닥 물건은 판 안으로 · 모르는 테마는 클럽하우스', r[4] is True and r[5] is True and r[6] == 'club', r[4:])
    # 크루원 목록·변경 기록 목록(규칙이 아직 없어 기록 읽기는 거부 → 안내 문장)
    pb.evaluate('''() => { const d = window.__AG, P = d.profiles, u = Object.keys(P)[1];
      window.crewAgitMount(Object.assign({}, d, { crew: Object.assign({}, d.crew, { staff: [u] }) }), { uid: u, nick: P[u].nickname, cfg: P[u].character }); window.crewAgitMembers(); }''')
    m = pb.evaluate("() => [...document.querySelectorAll('.ag-mr .nm small')].map(e => e.textContent)")
    check('크루원 목록: 크루장·운영진 표시', '크루장' in m and '운영진' in m, m)
    if OUT: pb.screenshot(path=os.path.join(OUT, 'members.png'))
    pb.evaluate('() => window.crewAgitHistory()'); pb.wait_for_timeout(2500)
    h = pb.evaluate("() => (document.querySelector('.ag-shw .ls') || {}).textContent || ''")
    check('변경 기록 목록: 읽기 실패해도 안내 문장', h in ('기록을 불러오지 못했어요', '아직 꾸민 기록이 없어요') or '님이' in h, h)
    # 로그인 전 — 아지트를 안 열고 로그인 안내로
    pd = ctx.new_page(); pd.goto('http://127.0.0.1:%d/index.html' % port, wait_until='domcontentloaded')
    pd.wait_for_function('typeof window.crewAgitOpen === "function"', timeout=60000); pd.wait_for_timeout(5000)
    pd.evaluate("() => window.crewAgitOpen('anything')"); pd.wait_for_timeout(800)
    check('로그인 전에는 아지트가 안 열린다', pd.evaluate("() => !document.getElementById('crew-agit') && !document.getElementById('crew-agit-wait')"))
    pd.close()
    b.close()
srv.shutdown()
print('ALL PASS' if ok else 'SOME FAILED')
