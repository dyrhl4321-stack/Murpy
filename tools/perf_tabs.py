# 탭별 속도 기준표(10-22) — 손님(로그인 전) 상태로 로컬 서버에 띄워 잰다. 실서비스에 쓰기 없음(로그인 안 함).
#   탭 = 홈·매칭·대숲·스쿼드·머피월드(내 방)·공원·크루 화면. 처음 들어갈 때와 다시 들어갈 때.
#   잰 것: 조용해질 때까지 시간(마지막 요청이 끝난 시각, 1.5초 조용하면 끝), 요청 수(같은 출처·Firestore 따로),
#          그림·JS 받은 양(같은 출처만 정확), JS 힙.
#   ★손님이라 Firestore 읽기는 로그인 상태보다 적다 — 그림·JS·메모리 비교용. 로그인 읽기 수는 코드 경로로 따로 센다.
#   사용: python tools/perf_tabs.py [CPU 배수(기본 4)] [반복(기본 1)]
import sys, os, json, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CPU = int(sys.argv[1]) if len(sys.argv) > 1 else 4
class _Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
srv = socketserver.ThreadingTCPServer(('127.0.0.1', 0), functools.partial(_Q, directory=ROOT))
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

SNAP = r'''() => { const es = performance.getEntriesByType('resource'); return es.map(e => [e.name, e.initiatorType, e.transferSize || e.encodedBodySize || 0, e.startTime, e.responseEnd]); }'''
TABS = [
    ('홈', "goPage('home')"), ('매칭', "goPage('match')"), ('대숲', "goPage('bamboo')"), ('스쿼드', "goPage('crew')"),
    ('머피월드·방', "goPage('char')"), ('공원', "window.charSetField && window.charSetField('park')"),
    ('크루 화면', "window.crewHotList().then(l => window.openCrewPage((l.find(x => (x.name||'').includes('근손실')) || l[0]).id))"),
]
def kind(url, init):
    if 'firestore.googleapis' in url or 'firebasedatabase' in url or 'googleapis.com' in url: return 'fb'
    if url.split('?')[0].endswith(('.png', '.jpg', '.jpeg', '.webp', '.gif')) or init in ('img', 'css') and '/char/' in url: return 'img'
    if url.split('?')[0].endswith(('.js', '.mjs')): return 'js'
    return 'other'

def settle(pg, t_start, quiet=1500, cap=20000):
    last = t_start; n0 = -1
    while True:
        pg.wait_for_timeout(250)
        es = pg.evaluate(SNAP); now = pg.evaluate('performance.now()')
        new = [e for e in es if e[3] >= t_start]
        if new: last = max(last, max(e[4] or e[3] for e in new))
        if now - last > quiet and len(new) == n0: return last, new
        n0 = len(new)
        if now - t_start > cap: return last, new

with sync_playwright() as p:
    b = p.chromium.launch()
    # 서비스워커는 막는다 — 첫 방문에 설치되며 controllerchange 로 한 번 새로고침해 측정이 끊긴다(재방문 캐시 효과는 따로)
    ctx = b.new_context(viewport={'width': 360, 'height': 780}, device_scale_factor=3, service_workers='block')
    pg = ctx.new_page()
    cdp = ctx.new_cdp_session(pg); cdp.send('Emulation.setCPUThrottlingRate', {'rate': CPU})
    cdp.send('Performance.enable')
    pg.goto('http://127.0.0.1:%d/index.html' % port, wait_until='domcontentloaded')
    last, new = settle(pg, 0, quiet=2500, cap=40000)
    def heap(): return round(next(m['value'] for m in cdp.send('Performance.getMetrics')['metrics'] if m['name'] == 'JSHeapUsedSize') / 1048576, 1)
    rows = []; tops = []; DRAW = {}
    def row(name, t0, last, new):
        agg = {'fb': [0, 0], 'img': [0, 0], 'js': [0, 0], 'other': [0, 0]}
        for e in new: k = kind(e[0], e[1]); agg[k][0] += 1; agg[k][1] += e[2]
        rows.append((name, int(last - t0), DRAW.get('ms', 0), len(new), agg['fb'][0], agg['img'][0], agg['img'][1] // 1024, agg['js'][1] // 1024, heap()))
        tops.append((name, sorted([(e[2] // 1024, e[0].split('/')[-1].split('?')[0]) for e in new if kind(e[0], e[1]) == 'img'], reverse=True)[:4]))
    row('첫 실행(부팅)', 0, last, new)
    pg.add_style_tag(content='#coach-overlay,.coach-overlay{display:none!important}')
    for rnd in ['처음', '다시']:
        for name, js in TABS:
            if rnd == '다시' and name == '크루 화면':
                pg.evaluate("document.getElementById('crew-page') && document.getElementById('crew-page').remove()")
            t0 = pg.evaluate('performance.now()')
            # 그리기 = 탭 함수 실행 + 다음 두 프레임이 그려질 때까지(다시 들어갈 때 체감과 같다)
            try: DRAW['ms'] = pg.evaluate('async () => { const t = performance.now(); ' + js + '; await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); return Math.round(performance.now() - t); }')
            except Exception as ex: print('!', name, ex); DRAW['ms'] = -1
            last, new = settle(pg, t0)
            row('%s %s' % (name, rnd), t0, last, new)
            if name == '크루 화면': pg.evaluate("document.getElementById('crew-page') && document.getElementById('crew-page').remove()")
    print('CPU x%d · 360×780 · 손님' % CPU)
    print('%-16s %7s %7s %5s %5s %5s %8s %7s %7s' % ('구간', '조용(ms)', '그리기', '요청', 'FB', '그림', '그림KB', 'JS KB', '힙MB'))
    for r in rows: print('%-16s %7d %7d %5d %5d %5d %8d %7d %7.1f' % r)
    for n, t in tops:
        if t: print('  큰 그림', n, t)
    b.close()
srv.shutdown()
