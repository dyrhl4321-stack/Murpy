# 좋아요 목록(관심 패널) 속도 비교(10-22) — 실서비스에 아무것도 안 쓴다.
#   ① 이 PC → Firestore 실제 왕복 시간을 공개 문서(crewsV2 하나) REST 로 잰다.
#   ② 옛 코드(origin/main)와 새 코드의 _loadInterestPanel·_renderInterestList 를 같은 가짜 DB 에 올린다.
#      가짜 DB = 읽기 한 번마다 ①의 왕복만큼 기다림, 개수는 대표 계정 실측(받은 24·그중 매칭 안 된 1, 보낸 46·대기 23, 대숲 알림 5·1명)
#      + 좋아요 많은 가상 계정(받은 100·보낸 100, 매칭 안 된 60/70, 대숲 10명).
#   ③ Chromium CPU 4배 느리게(갤럭시 가정) · 그대로 두 번. 측정 = 패널 열고 → 프로필 카드 첫 줄이 보일 때까지, 읽기 수.
#   사용: python tools/perf_interest_bench.py <옛 코드 파일> <새 코드 파일> [왕복 ms]
import sys, os, json, statistics
from playwright.sync_api import sync_playwright

OLD, NEW = sys.argv[1], sys.argv[2]
PAGE = r'''<!doctype html><meta charset="utf-8"><body>
<div id="interest-panel" class="open"><span id="itab-received-cnt"></span><span id="itab-sent-cnt"></span><div id="interest-badge"></div><svg id="interest-heart-svg"></svg><div id="interest-list"></div></div>
<script>
window.__reads = 0;
const RTT = window.__RTT || 90;
const wait = () => new Promise(r => setTimeout(r, RTT * (0.85 + Math.random() * 0.3)));
const S = window.__SCEN;   // {me, recv:[uid], recvMatched:Set, sent:[uid], sentMatched, bam:[uid], bamConn}
const ME = S.me, mset = new Set(S.matched);
const user = uid => ({ nickname: '닉' + uid.slice(-3), age: 27, district: '강남구', photoURL: '', pad: 'x'.repeat(2900) });
const docOf = (id, v) => ({ id, data: () => v, exists: () => !!v, ref: {} });
const snapOf = arr => ({ docs: arr, size: arr.length, forEach: f => arr.forEach(f), empty: !arr.length });
window.auth = { currentUser: { uid: ME } }; window.currentUser = { uid: ME };
window.db = {};
window.collection = (db, name) => ({ name });
window.where = (f, op, v) => ({ w: [f, op, v] }); window.orderBy = () => ({}); window.limit = n => ({ lim: n });
window.query = (c, ...cl) => ({ name: c.name, w: cl.filter(x => x.w).map(x => x.w) });
window.doc = (db, name, id) => ({ name, id });
window.documentId = () => '__id';
window.getDocs = async q => {
  await wait(); const W = Object.fromEntries(q.w.map(x => [x[0] + x[1], x[2]]));
  let out = [];
  if (q.name === 'likes' && W['to==']) out = S.recv.map((u, i) => docOf('l' + i, { from: u, to: ME, createdAt: i }));
  else if (q.name === 'likes' && W['from==']) out = S.sent.map((u, i) => docOf('s' + i, { from: ME, to: u, createdAt: i }));
  else if (q.name === 'notifications') out = S.bamN.map((u, i) => docOf('n' + i, { fromUid: u, toUid: ME, type: 'bamboo_request', postText: '글' }));
  else if (q.name === 'matches') out = S.matched.map(u => docOf([ME, u].sort().join('_'), { users: [ME, u] }));
  else if (q.name === 'users') out = (W['__idin'] || []).map(u => docOf(u, user(u)));
  window.__reads += Math.max(1, out.length); return snapOf(out);
};
window.getDoc = async d => {
  await wait(); window.__reads++;
  if (d.name === 'matches') { const u = d.id.split('_').find(x => x !== ME); return docOf(d.id, mset.has(u) ? { users: [ME, u] } : null); }
  if (d.name === 'chats') { const u = d.id.split('_').find(x => x !== ME); if (!S.bamConn.includes(u)) throw new Error('permission'); return docOf(d.id, { participants: [ME, u] }); }
  if (d.name === 'users') return docOf(d.id, user(d.id));
  return docOf(d.id, null);
};
window._pairKey = (a, b) => [a, b].sort().join('_');
window._escHtml = s => String(s).replace(/</g, '&lt;');
window._cdnImg = u => u;
window.isMatched = async o => { try { const m = await getDoc(doc(db, 'matches', _pairKey(ME, o))); return m.exists(); } catch (e) { return false; } };
window._isConnected = async o => { const k = _pairKey(ME, o); try { const [m, c] = await Promise.all([getDoc(doc(db, 'matches', k)), getDoc(doc(db, 'chats', k))]); return m.exists() || c.exists(); } catch (e) { return false; } };
window._userDocCache = new Map();
window._usersByIds = async function (uids) {   // 앱과 같은 방식(캐시 없을 때 30명씩 in)
  const out = {}, miss = Array.from(new Set(uids));
  for (let i = 0; i < miss.length; i += 30) { const sn = await getDocs(query(collection(db, 'users'), where(documentId(), 'in', miss.slice(i, i + 30)))); sn.forEach(d => { out[d.id] = d.data(); }); }
  return out;
};
var _interestTab = 'received';
</script>
<script src="CODE.js"></script>'''

def scen(kind):
    me = 'me000'
    if kind == 'owner':
        recv = ['r%03d' % i for i in range(24)]; sent = ['s%03d' % i for i in range(46)]
        matched = recv[1:] + sent[23:]; bamN = ['b000'] * 5; bamConn = []
    else:
        recv = ['r%03d' % i for i in range(100)]; sent = ['s%03d' % i for i in range(100)]
        matched = recv[60:] + sent[70:]; bamN = ['b%03d' % (i % 10) for i in range(20)]; bamConn = ['b000', 'b001']
    return dict(me=me, recv=recv, sent=sent, matched=matched, bamN=bamN, bamConn=bamConn)

def run(b, code, sc, rtt, cpu, tab):
    ctx = b.new_context(viewport={'width': 360, 'height': 780})
    pg = ctx.new_page()
    cdp = ctx.new_cdp_session(pg)
    cdp.send('Emulation.setCPUThrottlingRate', {'rate': cpu})
    pg.route('**/bench.html', lambda r: r.fulfill(body=PAGE.replace('CODE.js', 'code.js'), content_type='text/html'))
    pg.route('**/code.js', lambda r: r.fulfill(body=open(code, encoding='utf-8').read() + ('\n_interestTab = "%s";' % tab), content_type='application/javascript'))
    pg.add_init_script('window.__RTT = %d; window.__SCEN = %s;' % (rtt, json.dumps(sc)))
    pg.goto('http://bench.local/bench.html')
    ms = pg.evaluate('''async () => {
      const t0 = performance.now(); window._loadInterestPanel();
      await new Promise(res => { const ok = () => document.querySelector('#interest-list .card[onclick*="openUserProfile"]');
        const t = setInterval(() => { if (ok()) { clearInterval(t); res(); } }, 5); });
      const ids = a => (a || []).map(x => x.uid || x.fromUid).sort().join(',');
      return [Math.round(performance.now() - t0), window.__reads, document.querySelectorAll('#interest-list .card[onclick*="openUserProfile"]').length,
              [ids(window._interestLikeDocs), ids(window._interestSentDocs), ids(window._interestBambooDocs)].join('|')]; }''')
    ctx.close()
    return ms

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto('https://firestore.googleapis.com/')
    rt = pg.evaluate('''async () => { const u = 'https://firestore.googleapis.com/v1/projects/murpyprototype/databases/(default)/documents/crewsV2/FSuECLq2EanaXSrBQxdz';
      const xs = []; for (let i = 0; i < 9; i++) { const t = performance.now(); await fetch(u, { cache: 'no-store' }).then(r => r.text()); xs.push(performance.now() - t); } return xs; }''')
    rtt = int(statistics.median(rt[1:]))
    if len(sys.argv) > 3: rtt = int(sys.argv[3])   # 폰 LTE 가정 등 왕복을 직접 줄 때
    print('Firestore 왕복(이 PC, REST 중간값) = %d ms  (전체 %s)' % (rtt, [int(x) for x in rt]))
    pg.close()
    for kind in ['owner', 'heavy']:
        sc = scen(kind)
        for tab in ['received', 'sent']:
            for cpu in [1, 4]:
                o = run(b, OLD, sc, rtt, cpu, tab); n = run(b, NEW, sc, rtt, cpu, tab)
                print('%-6s %-8s CPU x%d  옛 %5d ms 읽기 %3d 카드 %3d  →  새 %5d ms 읽기 %3d 카드 %3d  목록 같음 %s' % (kind, tab, cpu, o[0], o[1], o[2], n[0], n[1], n[2], o[3] == n[3]))
    b.close()
