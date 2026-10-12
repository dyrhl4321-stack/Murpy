# -*- coding: utf-8 -*-
"""원본 index.html 과 압축본을 같은 조건으로 띄워 비교한다 — minify-index.mjs 를 고쳤을 때 돌린다.

    node tools/build/minify-index.mjs index.html _site_test/index.html
    python tools/build/verify-build.py . _site_test/index.html

  보는 것: 버전 표식 · 요소/속성/텍스트 · 브라우저가 읽은 CSS 규칙 · window 전역 이름 · 탭 이동 · 콘솔 오류.
  (playwright 필요. 서비스워커는 막고 띄운다.)

"""
import sys, os, json, threading, http.server, functools, time
sys.stdout.reconfigure(encoding='utf-8')
from playwright.sync_api import sync_playwright

ROOT, MIN = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])


def make_handler(index_path):
    class H(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **k):
            super().__init__(*a, directory=ROOT, **k)

        def translate_path(self, path):
            p = path.split('?', 1)[0].split('#', 1)[0]
            if p in ('/', '/index.html'):
                return index_path
            return super().translate_path(path)

        def log_message(self, *a):
            pass
    return H


def serve(index_path, port):
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', port), make_handler(index_path))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


STATIC_JS = r"""
async () => {
  const t = await (await fetch('/index.html', {cache: 'no-store'})).text();
  const d = new DOMParser().parseFromString(t, 'text/html');
  const els = [...d.querySelectorAll('*')];
  const sig = els.map(e => e.tagName + '|' + [...e.attributes].map(a => a.name + '=' + a.value).join('\u0001'));
  // 텍스트 노드(스크립트·스타일 제외) — 공백 포함 그대로
  const texts = [];
  const w = d.createTreeWalker(d, NodeFilter.SHOW_TEXT);
  while (w.nextNode()) {
    const n = w.currentNode, p = n.parentNode && n.parentNode.nodeName;
    if (p === 'SCRIPT' || p === 'STYLE') continue;
    texts.push(n.nodeValue);
  }
  return {count: els.length, sig, text: texts.join('')};   // 주석이 빠지면 앞뒤 텍스트 노드가 붙는다 → 이어 붙여 비교
}
"""

LIVE_JS = r"""
() => {
  const rules = [];
  for (const s of document.styleSheets) {
    let rs; try { rs = s.cssRules; } catch (e) { continue; }
    if (s.href) continue;                     // 인라인 <style> 만
    // 압축기는 본문이 같은 이웃 규칙을 `A,B{…}` 로 합친다 → 선택자 하나씩 풀어 (선택자, 본문) 순서열로 비교한다.
    const splitSel = s => { const o = []; let d = 0, cur = ''; for (const ch of s) { if (ch === '(' || ch === '[') d++; else if (ch === ')' || ch === ']') d--; if (ch === ',' && d === 0) { o.push(cur.trim()); cur = ''; } else cur += ch; } o.push(cur.trim()); return o; };
    const norm = t => t.replace(/,\s+/g, ',');   // var()/env() 가 든 선언은 브라우저가 원문 공백을 그대로 둔다 → 쉼표 뒤 공백만 무시
    const walk = (list, prefix) => { for (const r of list) {
      if (r.selectorText !== undefined && r.style) { for (const s of splitSel(r.selectorText)) rules.push(prefix + s + ' { ' + norm(r.style.cssText) + ' }'); }
      else if (r.cssRules && r.cssRules.length !== undefined && r.type !== 1) {
        const head = prefix + r.cssText.slice(0, r.cssText.indexOf('{')).trim() + ' >> ';
        if (r.type === 7) rules.push(norm(r.cssText)); else walk(r.cssRules, head);
      } else rules.push(prefix + norm(r.cssText));
    } };
    walk(rs, '');
  }
  const globals = {};
  for (const k of Object.getOwnPropertyNames(window)) {
    let v; try { v = window[k]; } catch (e) { continue; }
    globals[k] = typeof v;
  }
  return {rules, globals, ver: window._SW_V, title: document.title};
}
"""


def run(pw, port, label):
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2,
                        service_workers='block', locale='ko-KR')
    page = ctx.new_page()
    errors, warns = [], []
    page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)[:300]))
    page.on('console', lambda m: errors.append('console.error: ' + m.text[:300]) if m.type == 'error' else None)
    t0 = time.time()
    page.goto(f'http://127.0.0.1:{port}/', wait_until='load')
    page.wait_for_timeout(9000)
    static = page.evaluate(STATIC_JS)
    live = page.evaluate(LIVE_JS)
    # 탭을 한 바퀴 돈다 — 렌더 함수들이 실제로 실행되게
    nav = page.evaluate(r"""
    async () => {
      const out = [];
      const tabs = ['home', 'match', 'bamboo', 'crew', 'char', 'home'];
      for (const t of tabs) {
        try { window.goPage(t); out.push(t + ':ok'); } catch (e) { out.push(t + ':ERR ' + e.message); }
        await new Promise(r => setTimeout(r, 1500));
      }
      return out;
    }
    """)
    page.wait_for_timeout(1500)
    b.close()
    return dict(static=static, live=live, errors=errors, nav=nav, secs=round(time.time() - t0, 1))


with sync_playwright() as pw:
    s1 = serve(os.path.join(ROOT, 'index.html'), 8931)
    s2 = serve(MIN, 8932)
    a = run(pw, 8931, 'orig')
    b = run(pw, 8932, 'min')

ok = True
def check(name, cond, detail=''):
    global ok
    ok = ok and cond
    print(('PASS ' if cond else 'FAIL ') + name + (' — ' + detail if detail else ''))

check('버전 표식', a['live']['ver'] == b['live']['ver'], f"{a['live']['ver']} / {b['live']['ver']}")
check('요소 개수', a['static']['count'] == b['static']['count'], f"{a['static']['count']} / {b['static']['count']}")
diff_sig = [i for i, (x, y) in enumerate(zip(a['static']['sig'], b['static']['sig'])) if x != y]
check('요소·속성 전부 동일', not diff_sig and len(a['static']['sig']) == len(b['static']['sig']),
      f"다른 요소 {len(diff_sig)}개" + (': ' + a['static']['sig'][diff_sig[0]][:120] + '  ≠  ' + b['static']['sig'][diff_sig[0]][:120] if diff_sig else ''))
check('마크업 텍스트(공백 포함) 동일', a['static']['text'] == b['static']['text'],
      f"{len(a['static']['text'])} / {len(b['static']['text'])} 자")
ra, rb = a['live']['rules'], b['live']['rules']
diff_rules = [i for i, (x, y) in enumerate(zip(ra, rb)) if x != y]
check('CSS 규칙 수', len(ra) == len(rb), f"{len(ra)} / {len(rb)}")
check('CSS 규칙 내용(브라우저 정규화 뒤) 동일', not diff_rules, f"다른 규칙 {len(diff_rules)}개")
for i in diff_rules[:8]:
    print('   원본:', ra[i][:220]); print('   압축:', rb[i][:220])
ga, gb = a['live']['globals'], b['live']['globals']
missing = sorted(k for k in ga if k not in gb)
extra = sorted(k for k in gb if k not in ga)
typed = sorted(k for k in ga if k in gb and ga[k] != gb[k])
check('전역 이름 동일', not missing and not extra, f"원본 {len(ga)}개 / 압축 {len(gb)}개 · 빠짐 {missing[:10]} · 늘어남 {extra[:10]}")
check('전역 타입 동일', not typed, str(typed[:10]))
check('탭 이동', a['nav'] == b['nav'] and all(x.endswith(':ok') for x in b['nav']), str(b['nav']))
ea, eb = sorted(set(a['errors'])), sorted(set(b['errors']))
only_min = [e for e in eb if e not in ea]
check('압축본에서만 나는 오류 없음', not only_min, f"원본 오류 {len(ea)}종 / 압축 {len(eb)}종")
for e in only_min[:10]: print('   압축만:', e)
for e in ea[:6]: print('   (원본에도 있는 오류)', e)
print('부팅~탭 순회 시간(초): 원본', a['secs'], '/ 압축', b['secs'])
print('RESULT', 'OK' if ok else 'FAILED')
sys.exit(0 if ok else 1)
