# 크루 화면 캡처 하네스(10-19) — 라이브 DB 에 아무것도 쓰지 않는다.
#   로컬 서버로 index.html 을 띄우고, 화면 조각 함수(crewPageHtml·crewRowHtml·crewInviteHtml·runScanHtml/runScanFx·crewSkeletonHtml)에
#   가짜 데이터를 넣어 찍는다. 캐릭터는 앱의 mwMiniCharHtml 로 그린다.
#   사용: python tools/crew_shot.py <출력폴더> [카드 이미지 폴더(card_strava.jpg·card_nrc.jpg)]
import sys, os, time, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'crew_shots')
os.makedirs(OUT, exist_ok=True)
IMG = '/' + os.path.relpath(os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else OUT), ROOT).replace(os.sep, '/')

Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
Handler.log_message = lambda *a: None
srv = socketserver.TCPServer(('127.0.0.1', 0), Handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

FAKE = r'''
(IMG) => {
  const t = new Date(), day = t.getFullYear() + String(t.getMonth() + 1).padStart(2, '0') + String(t.getDate()).padStart(2, '0'), ym = day.slice(0, 6), now = Date.now();
  const C = (o) => Object.assign({}, window.CHAR_DEFAULT, o);
  const people = [
    ['u1', '은솔', C({body:'human_f', hair:'hair_f_ponytail', hairColor:'#3a2a20', top:'top_f_basic_tee', topColor:'#2f6b57', bottom:'bottom_f_leggings'}), 21.7, 9],
    ['u2', '도윤', C({hair:'hair_m_semileaf', topColor:'#d9d4c7', bottom:'bottom_trainpt'}), 15.3, 7],
    ['u3', '신촌곰', C({hair:'hair_ivyleague', top:'top_redhood'}), 12.4, 5],
    ['me', '나', C({hair:'hair_m_basic'}), 9.6, 4],
    ['u5', '하람', C({body:'human_f', hair:'hair_f_bob_bang', top:'top_f_zipup', bottom:'bottom_f_leggings'}), 7.9, 3],
    ['u6', '쩡이', C({body:'human_f', hair:'hair_f_long', top:'top_f_yellowtee', bottom:'bottom_f_basic_shorts'}), 5.2, 6],
    ['u7', '민초', C({hair:'hair_short', top:'top_yellowtee', bottom:'bottom_bermuda'}), 3.8, 2],
    ['u8', '재원', C({hair:'hair_m_basic', top:'top_ringer', bottom:'bottom_trainpt'}), 0, 1],
  ];
  const profiles = {}; people.forEach(p => { profiles[p[0]] = { nickname: p[1], character: p[2] }; });
  const members = people.map(p => ({ uid: p[0], nickname: p[1], monthKey: ym, monthKm: p[3], monthAttends: p[4], attends: p[4] + 11 }));
  const running = {
    crew: { id: 'demo', name: '런어스', school: '연세대', sport: 'running', intro: '화요일과 목요일 저녁 8시, 신촌에서 한강까지',
            stats: { members: 18, km: 213.6, runs: 31, pKm: 41.2, pRuns: 8, monthKey: ym, monthKm: 61.8, weekKey: window._crewWeekKey(), weekActive: 7 }, milestones: [100] },
    members, profiles,
    runs: [{ id: 'r1', uid: 'me', img: IMG + '/card_nrc.jpg', km: 10.03, runDay: day, status: 'verified' },
           { id: 'r2', uid: 'u1', img: IMG + '/card_strava.jpg', km: 5.02, runDay: day, status: 'unverified' },
           { id: 'r3', uid: 'u2', img: IMG + '/card_strava.jpg', km: 7.41, runDay: day, status: 'unverified' }],
    challenge: { kind: 'run_km', start: now - 3 * 864e5, end: now + 11 * 864e5, target: 270, progress: 96.4, status: 'active' },
    past: [{ kind: 'gym_attend', start: now - 30 * 864e5, target: 90, status: 'done' }],
    myStats: { runs: 6, km: 38.2, vRuns: 2, monthKey: ym, monthKm: 9.6, weekStreak: 3, bestKm: 10.03, bestPaceSec: 305 },
    isMember: true,
  };
  const mixed = Object.assign({}, running, {
    crew: { id: 'gbd', name: '근손실방지단', school: '서울', sport: 'mixed', stats: { members: 247, km: 0, attends: 1288, monthKey: ym, monthKm: 0, monthAttends: 412, weekKey: window._crewWeekKey(), weekActive: 63 } },
    challenge: { kind: 'gym_attend', start: now - 5 * 864e5, end: now + 9 * 864e5, target: 378, progress: 217, status: 'active' }, runs: [], past: [], myStats: null,
  });
  const empty = { crew: { id: 'new', name: '달리샤', school: '서울대', sport: 'running', stats: { members: 1 } },
    members: [{ uid: 'me', nickname: '나' }], profiles: { me: profiles.me }, runs: [], challenge: null, past: [], myStats: null, isMember: true };
  return { running, mixed, empty, me: { uid: 'me', admin: true } };
}
'''

def mount(pg, html):
    pg.evaluate('''(h) => { let el = document.getElementById('crw-shot'); if (el) el.remove();
      el = document.createElement('div'); el.id = 'crw-shot'; el.className = 'cw'; el.innerHTML = '<div class="cw-sc">' + h + '</div>'; document.body.appendChild(el); }''', html)
    pg.wait_for_timeout(900)

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=3)
    pg.goto('http://127.0.0.1:%d/index.html' % port, wait_until='domcontentloaded')
    pg.wait_for_function('typeof window.crewPageHtml === "function" && typeof window.mwMiniCharHtml === "function"', timeout=60000)
    pg.wait_for_timeout(6000)   # 부팅 스플래시·첫 화면 전환이 끝난 뒤 — 그 전에 붙이면 부팅이 몸통을 갈아 끼운다
    pg.add_style_tag(content='body > *:not(#crw-shot){display:none!important}')
    pg.evaluate('window._crewCss(); window.CREW_CFG.RUN_UPLOAD_ON = true')   # 하네스에서만 버튼을 켜서 본다
    pg.evaluate('([f, img]) => { window.__F = (eval(f))(img); }', [FAKE, IMG])
    shots = [
        ('crew_page', 'window.crewPageHtml(__F.running, __F.me)'),
        ('crew_page_mixed', 'window.crewPageHtml(__F.mixed, __F.me)'),
        ('crew_page_empty', 'window.crewPageHtml(__F.empty, {uid:"me", admin:false})'),
        ('crew_loading', 'window.crewSkeletonHtml()'),
        ('crew_invite', 'window.crewInviteHtml(__F.running.crew, __F.running.profiles, __F.running.members, "demo", "k")'),
    ]
    for name, expr in shots:
        mount(pg, pg.evaluate(expr))
        pg.screenshot(path=os.path.join(OUT, name + '.png'))
        if name == 'crew_page':
            h = pg.evaluate("document.querySelector('#crw-shot .cw-sc').scrollHeight")
            pg.set_viewport_size({'width': 390, 'height': h + 20})
            pg.add_style_tag(content='#crw-shot .cw-bar{position:absolute!important}')
            pg.wait_for_timeout(500)
            pg.screenshot(path=os.path.join(OUT, name + '_full.png'))
            pg.set_viewport_size({'width': 390, 'height': 844})
    # 오류
    mount(pg, '<div class="cw-hd"><div><b>크루</b></div><button class="cw-x">✕</button></div><div class="cw-err">크루를 불러오지 못했어요<br><button class="cw-pbtn">다시 불러오기</button></div>')
    pg.screenshot(path=os.path.join(OUT, 'crew_error.png'))
    # 스캔: 성공(미인증) → 거절
    mount(pg, pg.evaluate("window.runScanHtml('%s/card_strava.jpg')" % IMG))
    pg.wait_for_timeout(500)
    pg.screenshot(path=os.path.join(OUT, 'scan_1_start.png'))
    pg.evaluate("window.runScanFx({ok:true, reward:0, run:{km:5.02, sec:1531, paceSec:305, runDay:'20261019', dayFromCard:true, status:'unverified'}}, '')")
    pg.wait_for_timeout(1900)
    pg.screenshot(path=os.path.join(OUT, 'scan_2_ok.png'))
    mount(pg, pg.evaluate("window.runScanHtml('%s/card_nrc.jpg')" % IMG))
    pg.evaluate("window.runScanFx({ok:false, why:'not_card'}, '')")
    pg.wait_for_timeout(700)
    pg.screenshot(path=os.path.join(OUT, 'scan_3_fail.png'))
    # 스쿼드 탭 '내 크루' 줄
    mount(pg, '<div style="padding:16px 20px;font-family:Pretendard,sans-serif">' + pg.evaluate("window.crewRowHtml([__F.running.crew, __F.mixed.crew])") + '</div>')
    pg.screenshot(path=os.path.join(OUT, 'crew_row.png'), clip={'x': 0, 'y': 0, 'width': 390, 'height': 200})
    b.close()
srv.shutdown()
print('saved to', OUT)
