# 크루 아지트 캡처 하네스(10-22) — 라이브 DB 는 **읽기만** 한다(크루 문서·크루원·프로필).
#   로컬 서버로 index.html 을 띄우고 crewAgitLoad(실데이터) → crewAgitMount 로 그린다. 로그인·쓰기 없음.
#   같이 있는 사람·흐린 최근 방문자는 실제 크루원 캐릭터로 자리만 정해 얹는다(실시간 접속을 흉내 낸 것).
#   사용: python tools/agit_shot.py <출력폴더> [크루 이름 일부(기본 근손실)]
#   아이폰 = WebKit 390×844 · 375×812, 갤럭시 = Chromium 320×690
import sys, os, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'agit_shots')
NAME = sys.argv[2] if len(sys.argv) > 2 else '근손실'
os.makedirs(OUT, exist_ok=True)
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
class _Q(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
Handler = functools.partial(_Q, directory=ROOT)
srv = socketserver.TCPServer(('127.0.0.1', 0), Handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

PICK = r'''
async (NAME) => {
  for (let i = 0; i < 60 && typeof window.crewHotList !== 'function'; i++) await new Promise(r => setTimeout(r, 500));
  const list = await window.crewHotList();
  const c = list.find(x => (x.name || '').includes(NAME)) || list[0];
  const data = await window.crewAgitLoad(c.id);
  const ms = data.members.filter(m => data.profiles[m.uid] && data.profiles[m.uid].character);
  window.__AG = { data, ms: ms.map(m => m.uid) };
  return { id: c.id, name: data.crew.name, members: data.members.length, withChar: ms.length,
           leader: data.crew.leaderUid || data.crew.createdBy || '', hideout: !!data.hideout, logo: data.crew.logo || '' };
}
'''
MOUNT = r'''
(edit) => {
  const { data, ms } = window.__AG, P = data.profiles;
  const lead = data.crew.leaderUid || data.crew.createdBy || '';
  const meUid = edit ? (lead || ms[0]) : (ms.find(u => u !== lead && !(data.crew.staff || []).includes(u)) || ms[0]);   // edit=크루장 시점, 아니면 일반 크루원 시점
  const meP = P[meUid] || P[ms[0]];
  window.crewAgitMount(data, { uid: meUid, nick: meP.nickname, cfg: meP.character });
  try { localStorage.setItem('ag_coach', '1'); } catch (e) {}
  document.querySelectorAll('.ag-coach').forEach(e => e.remove());
  // 같이 있는 사람(라운지·탁자 둘레, 방향 섞기) + 흐린 최근 방문자
  const live = [[6, 12, 'right', '오늘 하체 누구?'], [9, 12, 'left', ''], [14, 10, 'down', ''], [18, 10, 'down', '깃발 멋지다'], [22, 12, 'right', ''], [27, 12, 'left', '']];
  const ghost = [[4, 16, 'down', '3시간 전'], [12, 15, 'right', '어제'], [25, 15, 'down', '2일 전']];
  const others = {}; const pool = ms.filter(u => u !== meUid);
  live.forEach((s, i) => { const u = pool[i]; if (!u) return; others[u] = { tc: s[0], tr: s[1], face: s[2], msg: s[3], cfg: P[u].character, nick: P[u].nickname }; });
  ghost.forEach((s, i) => { const u = pool[live.length + i]; if (!u) return; others[u] = { tc: s[0], tr: s[1], face: s[2], ghost: true, ago: s[3], cfg: P[u].character, nick: P[u].nickname }; });
  const S = window._agit; S.me = { tc: 16, tr: 11, face: 'down' };
  // 막힌 칸이면 가장 가까운 빈칸으로(실제 접속자는 걸어서 오므로 막힌 칸에 설 수 없다)
  Object.values(others).forEach(o => { for (let r = 0; r < 6 && !window.crewAgitWalkable(o.tc, o.tr); r++) { if (window.crewAgitWalkable(o.tc, o.tr + 1)) o.tr++; else if (window.crewAgitWalkable(o.tc + 1, o.tr)) o.tc++; else o.tr++; } });
  S.others = others;
  S.lastLog = { text: window.crewAgitLogText({ act: 'place', item: 'cz_flag', n: 1, nick: (P[lead] || meP).nickname }) };
  window.crewAgitStep(0, 0); window.crewAgitTest.fit();   // 처음 들어올 때와 같은 자리 맞추기
  const n = 1 + Object.keys(others).filter(k => !others[k].ghost).length;
  document.querySelector('.ag-tt span').innerHTML = '아지트 · 지금 <i>' + n + '</i>명';
  document.querySelector('.ag-log').innerHTML = '<span>' + S.lastLog.text + '</span>';
}
'''

CHAT = r'''
() => {
  const S = window._agit, ks = Object.keys(S.others).filter(k => !S.others[k].ghost), now = Date.now();
  S.chat = [{ uid: ks[0], nick: S.others[ks[0]].nick, text: '오늘 저녁 8시 하체 갑니다', t: now - 90000 },
            { uid: ks[1], nick: S.others[ks[1]].nick, text: '저 갈게요 스쿼트 100 찍어봄', t: now - 30000 },
            { uid: S.uid, nick: S.nick, text: '깃발 바꿔 놨어요 어때요', t: now - 5000 }];
  S.myMsg = '깃발 바꿔 놨어요 어때요'; window.crewAgitStep(0, 0); window.crewAgitTest.chatPaint();
}
'''
EDIT = r'''
() => { window.crewAgitEdit(); window.crewAgitAdd('cz_cork'); }
'''

def shoot(b, w, h, tag, edit=False, full=False):
    pg = b.new_page(viewport={'width': w, 'height': h}, device_scale_factor=3)
    pg.goto('http://127.0.0.1:%d/index.html' % port, wait_until='domcontentloaded')
    pg.wait_for_function('typeof window.crewAgitMount === "function" && typeof window.mwMiniCharHtml === "function" && typeof window.crewHotList === "function"', timeout=60000)
    pg.wait_for_timeout(6000)
    info = pg.evaluate(PICK, NAME)
    print(tag, info)
    pg.add_style_tag(content='body > *:not(#crew-agit){visibility:hidden!important} #crew-agit, #crew-agit *{visibility:visible}')
    pg.evaluate(MOUNT, edit)
    pg.wait_for_timeout(1500)
    pg.screenshot(path=os.path.join(OUT, 'agit_%s.png' % tag))
    pg.evaluate(CHAT); pg.wait_for_timeout(600)
    pg.screenshot(path=os.path.join(OUT, 'agit_%s_chat.png' % tag))
    pg.evaluate("() => window.crewAgitMembers()"); pg.wait_for_timeout(700)
    pg.screenshot(path=os.path.join(OUT, 'agit_%s_members.png' % tag))
    pg.evaluate("() => { const w = document.querySelector('.ag-shw'); if (w) w.remove(); }")
    if edit:
        pg.evaluate(EDIT); pg.wait_for_timeout(900)
        pg.screenshot(path=os.path.join(OUT, 'agit_%s_edit.png' % tag))
        pg.evaluate("() => window.crewAgitEditDone(false)"); pg.wait_for_timeout(300)
    if full:   # 방 전체(카메라 없이) — 배치 검수용
        pg.evaluate("() => { const w = document.querySelector('.ag-world'); w.classList.add('snap'); w.style.transform = 'none'; document.querySelector('.ag-stage').style.overflow = 'visible'; }")
        pg.set_viewport_size({'width': 768, 'height': 960})
        pg.wait_for_timeout(600)
        pg.screenshot(path=os.path.join(OUT, 'agit_full.png'), clip={'x': 0, 'y': 0, 'width': 768, 'height': 960})
    pg.close()

with sync_playwright() as p:
    wk = p.webkit.launch()
    shoot(wk, 390, 844, 'iphone390', edit=True, full=True)
    shoot(wk, 375, 812, 'iphone375')
    wk.close()
    ch = p.chromium.launch()
    shoot(ch, 320, 690, 'galaxy320', edit=True)
    ch.close()
srv.shutdown()
print('saved to', OUT)
