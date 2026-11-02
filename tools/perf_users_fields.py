# users 칸별 크기 측정(2026-11-02 속도 창) — users 컬렉션 칸별 크기(JSON 문자 수) — 손님으로 매칭 탭 열어 _usersAll 캐시를 읽는다(읽기만)
import sys, os, threading, http.server, socketserver, functools, json
from playwright.sync_api import sync_playwright
ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
class _Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(_Q, directory=ROOT)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
J = r'''() => { const d = window._usersAllCache.snap.docs; const F = {}; let tot = 0;
  d.forEach(x => { const v = x.data(); const all = JSON.stringify(v).length; tot += all;
    Object.keys(v).forEach(k => { const n = JSON.stringify(v[k] ?? null).length; const f = F[k] || (F[k] = { sum: 0, docs: 0, max: 0 }); f.sum += n; f.docs++; if (n > f.max) f.max = n; }); });
  return { users: d.length, total: tot, fields: Object.entries(F).sort((a, b) => b[1].sum - a[1].sum).slice(0, 25) }; }'''
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(service_workers='block'); pg = ctx.new_page()
    pg.goto('http://127.0.0.1:%d/index.html' % port, wait_until='load'); pg.wait_for_timeout(8000)
    pg.evaluate("window._usersAll()"); pg.wait_for_function("window._usersAllCache && window._usersAllCache.snap", timeout=60000)
    r = pg.evaluate(J); b.close()
srv.shutdown()
print('users', r['users'], 'total KB', r['total'] // 1024)
for k, f in r['fields']: print('%-22s %6dKB %5.1f%% docs=%-4d max=%dKB' % (k, f['sum'] // 1024, 100 * f['sum'] / r['total'], f['docs'], f['max'] // 1024))
