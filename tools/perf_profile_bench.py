# 상대 프로필 열기 속도 비교(10-23) — 실서비스에 아무것도 안 쓴다(가짜 DB).
#   옛 코드(HEAD 의 index.html)와 새 코드의 openUserProfile 을 같은 가짜 DB 에 올려 잰다.
#   가짜 DB = 읽기 한 번마다 왕복(RTT)만큼 기다림 + 문서 하나당 전송 시간(LTE 약 10Mbps, 1KB 문서 ≈ 0.8ms).
#   장면: ① 받은 좋아요 목록에서(문서 캐시 있음·매칭 안 됨·상대가 먼저 보냄·인증 40개)
#         ② 매칭된 사람(캐시 없음·인증 120개) ③ 처음 보는 사람(캐시 없음·인증 10개)
#   측정 = 이름·사진이 보일 때까지(첫 화면) / 버튼까지 다 그려질 때까지(완성) / 읽기 수 / 완성 화면 글자가 옛 코드와 같은지.
#   사용: python tools/perf_profile_bench.py [옛 index.html] [새 index.html] [RTT ms(기본 150 = LTE 80 + 서버)]
import sys, os, json, re, subprocess
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def src(path):
    if path.startswith('git:'): return subprocess.run(['git', 'show', path[4:] + ':index.html'], cwd=ROOT, capture_output=True).stdout.decode('utf-8')
    return open(path, encoding='utf-8').read()
OLD = src(sys.argv[1] if len(sys.argv) > 1 else 'git:HEAD')
NEW = src(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'index.html'))
RTT = int(sys.argv[3]) if len(sys.argv) > 3 else 150
def cut(h):
    a = h.index('window.openUserProfile = async function'); b = h.index('function setFvStatus', a)
    return h[a:b]

PAGE = r'''<!doctype html><meta charset="utf-8"><body>
<div id="user-profile-name"></div><div id="user-profile-tools"></div><div id="user-profile-body"></div>
<script>
window.__reads = 0;
const RTT = window.__RTT, S = window.__SCEN, ME = 'me000';
const wait = n => new Promise(r => setTimeout(r, RTT * (0.85 + Math.random() * 0.3) + (n || 0) * 0.8));
const docOf = (id, v) => ({ id, data: () => v, exists: () => !!v });
const snapOf = arr => ({ docs: arr, size: arr.length, forEach: f => arr.forEach(f), empty: !arr.length });
const USER = { nickname: '상대닉', age: 29, gender: '여성', district: '강남구', gym: '머피짐', career: '3년', purpose: '근력', workoutTime: ['저녁'],
  photoURL: 'p0.jpg', photos: ['p1.jpg', 'p2.jpg'], bio: '같이 운동해요', character: { body: 'human_f' }, room: [], pad: 'x'.repeat(2500) };
window.currentUser = { uid: ME }; window._cachedProfile = { photoURL: 'me.jpg', photos: ['m1.jpg'] };
window.db = {};
window.collection = (db, name) => ({ name }); window.where = (f, op, v) => ({ w: [f, op, v] });
window.query = (c, ...cl) => ({ name: c.name, w: cl.filter(x => x.w).map(x => x.w) });
window.doc = (db, name, id) => ({ name, id });
window.getDocs = async q => {
  const out = q.name === 'feed' ? Array.from({ length: S.posts }, (_, i) => docOf('f' + i, { userId: S.uid, photoURL: 'f' + i + '.jpg', createdAt: { seconds: 1760000000 - i * 86400 }, likes: i % 3 })) : [];
  await wait(out.length); window.__reads += Math.max(1, out.length); return snapOf(out);
};
window.getDoc = async d => {
  await wait(1); window.__reads++;
  if (d.name === 'users') return docOf(d.id, USER);
  if (d.name === 'matches') return docOf(d.id, S.matched ? { users: [] } : null);
  if (d.name === 'likes') return docOf(d.id, (d.id === S.uid + '_' + ME && S.theyLiked) ? { from: S.uid } : null);
  return docOf(d.id, null);
};
window.isMatched = async o => { try { const m = await getDoc(doc(db, 'matches', [ME, o].sort().join('_'))); return m.exists(); } catch (e) { return false; } };
window._userDocCache = new Map(); if (S.cached) window._userDocCache.set(S.uid, { d: USER, at: Date.now() });
window.openPanel = () => {}; window.closePanel = () => {}; window.showToast = () => {};
window._isBlocked = () => false; window.mIcon = () => ''; window._cdnImg = u => u;
window._visiblePosts = a => a; window._feedPostCache = {}; window._SHIELD_SVG = '';
window._milestoneBadge = () => ''; window.relMark = () => {}; window.crewBadgeFill = () => {};
window.mwFurnHtml = () => ''; window.mwMiniCharHtml = () => '<i></i>';
</script>
<script src="code.js"></script>'''

SCENES = [('좋아요 목록에서', dict(uid='u1', cached=True, matched=False, theyLiked=True, posts=40)),
          ('매칭된 사람', dict(uid='u2', cached=False, matched=True, theyLiked=False, posts=120)),
          ('처음 보는 사람', dict(uid='u3', cached=False, matched=False, theyLiked=False, posts=10))]

def run(b, code, sc, cpu):
    ctx = b.new_context(viewport={'width': 360, 'height': 780})
    pg = ctx.new_page()
    ctx.new_cdp_session(pg).send('Emulation.setCPUThrottlingRate', {'rate': cpu})
    pg.route('**/bench.html', lambda r: r.fulfill(body=PAGE, content_type='text/html'))
    pg.route('**/code.js', lambda r: r.fulfill(body=code, content_type='application/javascript'))
    pg.add_init_script('window.__RTT = %d; window.__SCEN = %s;' % (RTT, json.dumps(sc)))
    pg.goto('http://bench.local/bench.html')
    r = pg.evaluate('''async (uid) => {
      const body = document.getElementById('user-profile-body');
      const t0 = performance.now(); let first = 0, full = 0;
      const mo = new MutationObserver(() => {
        if (!first && body.textContent.includes('상대닉') && body.querySelector('#up-track img')) first = performance.now() - t0;
        if (!full && /채팅하기|매칭 수락하기|같이 운동해요|수락 기다리는 중/.test(body.textContent) && body.querySelector('button')) full = performance.now() - t0;
      });
      mo.observe(body, { childList: true, subtree: true, characterData: true });
      await window.openUserProfile(uid, '상대닉', 'p0.jpg');
      await new Promise(r => setTimeout(r, 50)); mo.disconnect();
      return [Math.round(first), Math.round(full), window.__reads, body.textContent.replace(/\\s+/g, ' ').trim()]; }''', sc['uid'])
    ctx.close()
    return r

with sync_playwright() as p:
    b = p.chromium.launch()
    o_code, n_code = cut(OLD), cut(NEW)
    print('왕복 %d ms + 문서당 0.8 ms' % RTT)
    for name, sc in SCENES:
        for cpu in (1, 4):
            o = run(b, o_code, sc, cpu); n = run(b, n_code, sc, cpu)
            print('%-10s CPU x%d  옛 첫 화면 %5d ms 완성 %5d ms 읽기 %3d  →  새 첫 화면 %5d ms 완성 %5d ms 읽기 %3d  완성 화면 같음 %s'
                  % (name, cpu, o[0], o[1], o[2], n[0], n[1], n[2], o[3] == n[3]))
            if o[3] != n[3]: print('   옛:', o[3][:300], '\n   새:', n[3][:300])
    b.close()
