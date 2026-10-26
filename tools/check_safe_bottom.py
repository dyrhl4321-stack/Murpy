# 하단 안전 여백 검사(10-26 대표 "입력창이 아이폰 둥근 모서리에 갈린다 — 몇 번이나 말했다") — 배포 전 필수.
#   1) 코드: index.html 의 env(safe-area-inset-bottom) 은 :root 의 --safe-b 정의 안이나 max(var(--safe-b), …) 안에서만 쓴다.
#      맨몸으로 쓴 줄은 실패(앱 웹뷰는 viewport-fit=cover 가 없어 env()=0 → 바닥에 붙는다). 키보드 위 계산처럼 일부러 쓴 줄은 'safe-b-ok' 표시.
#   2) 화면: 입력 줄이 있는 화면을 열어 입력칸·버튼이 화면 아래 46px·좌우 16px 안에 들어오면 실패.
#      아이폰13 390×844 · 아이폰SE 375×667 · 갤럭시 320×690(Chromium). 라이브 DB 는 읽기만(아지트 실데이터).
#   사용: python tools/check_safe_bottom.py [캡처 폴더]   → 종료코드 0 = 통과
import sys, os, re, json, threading, http.server, socketserver, functools
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = sys.argv[1] if len(sys.argv) > 1 else None
B, X = 46, 16
fails = []

# ── 1) 코드 ──
src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read().split('\n')
for i, line in enumerate(src, 1):
    if 'safe-area-inset-bottom' not in line: continue
    if '--safe-b:' in line or 'safe-b-ok' in line or line.strip().startswith(('/*', '//', '*', '검사:')) or 'max(var(--safe-b)' in line: continue
    fails.append(('코드', 'index.html:%d' % i, 'env(safe-area-inset-bottom) 맨몸 사용 — max(var(--safe-b), …) 로 감쌀 것', line.strip()[:120]))
print('코드 검사', '통과' if not fails else '실패 %d' % len(fails))

# ── 2) 화면 ──
from playwright.sync_api import sync_playwright
class _Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
class TS(socketserver.ThreadingMixIn, socketserver.TCPServer): daemon_threads = True
srv = TS(('127.0.0.1', 0), functools.partial(_Q, directory=ROOT)); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
ag = open(os.path.join(ROOT, 'tools', 'agit_shot.py'), encoding='utf-8').read()
PICK = ag.split("PICK = r'''", 1)[1].split("'''", 1)[0]; MOUNT = ag.split("MOUNT = r'''", 1)[1].split("'''", 1)[0]
# 화면 열기 — (이름, 여는 코드, 입력 줄 선택자)
SCREENS = [
    ('대숲 댓글', "document.getElementById('comment-panel').classList.add('open')", '#comment-panel .safe-in'),
    ('DM', "document.getElementById('chat-detail-panel').classList.add('open')", '#dm-input-row'),
    ('크루 톡', "document.getElementById('crew-detail-panel').classList.add('open'); document.getElementById('crew-chat-tab').style.display='flex'", '#crew-chat-input-row'),
    ('크루 글 댓글', "document.getElementById('crew-post-detail-panel').classList.add('open')", '#crew-post-detail-panel .safe-in'),
    ('방 톡', "window.mwRTalkOpen()", '#mw-rtalk .rt-row'),
    ('스쿼드 톡', "window._sqChatSid='safe-check'; window._sqDoc={hostUid:'x',memberUids:[]}; window._sqTalkCanRead=()=>true; window._sqTalkOpen()", '#sq-chat-row'),
    ('아지트', None, '.ag-bar'),
]
MEAS = r"""(sel) => { const row = document.querySelector(sel); if (!row) return { missing: true };
  const els = [...row.querySelectorAll('input,textarea,button')].filter(e => { const r = e.getBoundingClientRect(), cs = getComputedStyle(e); return r.width > 0 && r.height > 0 && cs.display !== 'none' && cs.visibility !== 'hidden'; });
  if (!els.length) return { empty: true };
  const rs = els.map(e => e.getBoundingClientRect());
  return { bottom: Math.round(Math.max(...rs.map(r => r.bottom))), left: Math.round(Math.min(...rs.map(r => r.left))), right: Math.round(Math.max(...rs.map(r => r.right))), H: innerHeight, W: innerWidth }; }"""
DEVS = [('아이폰13', 390, 844), ('아이폰SE', 375, 667), ('갤럭시320', 320, 690)]
rows = []
with sync_playwright() as p:
    br = p.chromium.launch()
    for dn, W, H in DEVS:
        for name, js, sel in SCREENS:
            pg = br.new_page(viewport={'width': W, 'height': H}, device_scale_factor=2, has_touch=True)
            try:
                pg.goto('http://127.0.0.1:%d/index.html' % port, wait_until='domcontentloaded', timeout=300000)
                pg.wait_for_function("typeof window.crewAgitMount === 'function' && typeof window.mwRTalkOpen === 'function'", timeout=300000)
                pg.wait_for_timeout(3500)
                pg.evaluate("try{closeSplash()}catch(e){}; document.querySelectorAll('.modal-overlay.open').forEach(m=>m.classList.remove('open')); ['store-nudge','mw-promo'].forEach(i=>{const e=document.getElementById(i); if(e) e.remove();})")
                if js: pg.evaluate("() => { try { " + js + " } catch (e) { console.warn(e); } }")
                else: pg.evaluate(PICK, '근손실'); pg.evaluate(MOUNT, False)
                pg.wait_for_timeout(1200)
                m = pg.evaluate(MEAS, sel)
            except Exception as e:
                m = {'error': str(e)[:120]}
            ok = bool(m.get('bottom')) and m['bottom'] <= H - B + 0.5 and m['left'] >= X - 0.5 and m['right'] <= W - X + 0.5
            if not ok: fails.append(('화면', dn + ' ' + name, '아래 %dpx·좌우 %dpx 안에 들어옴' % (B, X), json.dumps(m, ensure_ascii=False)))
            rows.append((dn, name, m, ok))
            print(('통과 ' if ok else '실패 ') + dn + ' ' + name, json.dumps(m, ensure_ascii=False))
            if SHOTS and m.get('bottom'):
                os.makedirs(SHOTS, exist_ok=True); pg.screenshot(path=os.path.join(SHOTS, 'safe_%s_%s.png' % (dn, name.replace(' ', ''))))
            pg.close()
    br.close()
srv.shutdown()
print('\n결과:', '통과' if not fails else '실패 %d건' % len(fails))
for f in fails: print(' -', *f)
sys.exit(1 if fails else 0)
