# 크루 화면 캡처 하네스(10-19) — 라이브 DB 에 아무것도 쓰지 않는다.
#   로컬 서버로 index.html 을 띄우고, 화면 조각 함수(crewPageHtml·crewRowHtml·runScanFx)에 가짜 데이터를 넣어 찍는다.
#   사용: python tools/crew_shot.py <출력폴더> [이미지폴더(card_strava.jpg·card_nrc.jpg, 출력폴더 기준 상대 경로 가능)]
import sys, os, json, time, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'crew_shots')
os.makedirs(OUT, exist_ok=True)
IMG = os.path.relpath(os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else OUT), ROOT).replace(os.sep, "/")

Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
Handler.log_message = lambda *a: None
srv = socketserver.TCPServer(('127.0.0.1', 0), Handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

ym = time.strftime('%Y%m')
day = time.strftime('%Y%m%d')
fake = {
  'crew': {'id': 'demo', 'name': '런어스', 'school': '연세대', 'sport': 'running', 'intro': '매주 화·목 저녁 신촌 한 바퀴',
           'stats': {'members': 18, 'km': 132.4, 'runs': 21, 'pKm': 41.2, 'pRuns': 8, 'monthKey': ym, 'monthKm': 64.1, 'weekKey': 'X', 'weekActive': 0},
           'milestones': [100]},
  'members': [{'uid': 'u%d' % i, 'nickname': n, 'monthKey': ym, 'monthKm': k} for i, (n, k) in enumerate(
      [('지훈', 21.3), ('서연', 15.0), ('민재', 12.4), ('나', 9.8), ('하은', 5.6)])],
  'runs': [{'id': 'r1', 'uid': 'u0', 'img': '/' + IMG + '/card_strava.jpg', 'km': 5.02, 'paceSec': 305, 'runDay': day, 'status': 'unverified'},
           {'id': 'r2', 'uid': 'u3', 'img': '/' + IMG + '/card_nrc.jpg', 'km': 10.03, 'paceSec': 331, 'runDay': day, 'status': 'verified'}],
  'challenge': {'kind': 'run_km', 'start': int(time.time() * 1000) - 3 * 864e5, 'end': int(time.time() * 1000) + 11 * 864e5, 'target': 270, 'progress': 96.4, 'status': 'active'},
  'past': [{'kind': 'gym_attend', 'start': int(time.time() * 1000) - 30 * 864e5, 'target': 90, 'status': 'done'}],
  'myStats': {'runs': 6, 'km': 38.2, 'vRuns': 2, 'monthKey': ym, 'monthKm': 9.8, 'weekStreak': 3, 'bestKm': 10.03, 'bestPaceSec': 305},
  'isMember': True,
}

with sync_playwright() as p:
    b = p.chromium.launch()
    for (w, h, tag) in [(390, 844, 'phone'), (1280, 800, 'pc')]:
        pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=3 if tag == 'phone' else 1)
        pg.goto('http://127.0.0.1:%d/index.html' % port, wait_until='domcontentloaded')
        pg.wait_for_function('typeof window.crewPageHtml === "function"', timeout=60000)
        pg.wait_for_timeout(6000)   # 부팅 스플래시·첫 화면 전환이 끝난 뒤 — 그 전에 붙이면 부팅이 몸통을 갈아 끼운다
        pg.add_style_tag(content='body > *:not(#crw-shot){display:none!important}')
        pg.evaluate('''([d, u]) => {
          window._crewCss();
          const me = { uid: 'u3', admin: true };
          d.members[3].uid = 'u3';
          const el = document.createElement('div'); el.id = 'crw-shot';
          el.style.cssText = 'position:fixed;inset:0;z-index:99999;background:#0a0a0a;overflow-y:auto;display:flex;justify-content:center';
          el.innerHTML = '<div style="width:100%;max-width:480px;padding:16px 18px 30px;color:#fff;font-family:Pretendard,sans-serif">' + window.crewPageHtml(d, me) + '</div>';
          document.body.appendChild(el);
        }''', [fake, None])
        pg.wait_for_timeout(1200)
        pg.screenshot(path=os.path.join(OUT, 'crew_page_%s.png' % tag), full_page=False)
        if tag == 'phone':
            pg.evaluate("document.getElementById('crw-shot').firstChild.scrollTop=0; document.getElementById('crw-shot').scrollTop=900")
            pg.wait_for_timeout(300)
            pg.screenshot(path=os.path.join(OUT, 'crew_page_phone_2.png'))
            pg.evaluate('''(d) => {
              const el = document.getElementById('crw-shot');
              el.firstChild.innerHTML = '<div style="font-size:17px;font-weight:800;margin-bottom:12px">스쿼드 탭 맨 위</div>' + window.crewRowHtml([d.crew, Object.assign({}, d.crew, {id:'g', name:'근손실방지단', sport:'gym', stats:{members:247, monthKey: d.crew.stats.monthKey, monthAttends: 412}})]);
              el.scrollTop = 0;
            }''', fake)
            pg.screenshot(path=os.path.join(OUT, 'crew_row_phone.png'))
            # 스캔 연출: 시작 → 결과
            pg.evaluate('''(img) => {
              const el = document.getElementById('crw-shot');
              el.firstChild.innerHTML = '<div class="crw-scan" id="run-scan-box"><img src="' + img + '"><div class="ln"></div></div><div style="margin-top:12px">'
                + ['거리','페이스','날짜'].map((t,i) => '<div class="crw-chk" id="run-chk-' + i + '"><i><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><path d="M5 12.5l4.2 4.2L19 7"/></svg></i>' + t + ' 확인<em></em></div>').join('')
                + '</div><div id="run-scan-out" style="margin-top:10px"></div>';
            }''', '/' + IMG + '/card_strava.jpg')
            pg.wait_for_timeout(700)
            pg.screenshot(path=os.path.join(OUT, 'scan_1_start.png'))
            pg.evaluate("window.runScanFx({ok:true, reward:0, run:{km:5.02, sec:1531, paceSec:305, runDay:'%s', dayFromCard:true, status:'unverified'}}, '')" % day)
            pg.wait_for_timeout(1800)
            pg.screenshot(path=os.path.join(OUT, 'scan_2_ok.png'))
            pg.evaluate("document.getElementById('run-scan-box').classList.remove('done'); ['0','1','2'].forEach(i=>document.getElementById('run-chk-'+i).classList.remove('on')); window.runScanFx({ok:false, why:'not_card'}, '')")
            pg.wait_for_timeout(900)
            pg.screenshot(path=os.path.join(OUT, 'scan_3_fail.png'))
        pg.close()
    b.close()
srv.shutdown()
print('saved to', OUT)
