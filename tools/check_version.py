# -*- coding: utf-8 -*-
import sys as _sys
try: _sys.stdout.reconfigure(encoding='utf-8')   # 8-29: cp949 콘솔에서 마지막 print 가 크래시해 exit 1 로 오탐
except Exception: pass
"""배포 전 버전 검사 — 세 곳이 같은 숫자인지, 대입이 하나뿐인지 본다.

    python tools/check_version.py

★왜 있나 (2026-08-25)
  index.html 에 `window._SW_V = ...` 대입이 **두 곳** 있었다. 맨 위 것을 배포마다 올렸는데
  아래쪽에 655 가 남아 있어서 나중에 실행되는 그것이 늘 이겼다. 그 결과
    · 서비스워커를 항상 `sw.js?v=655` 라는 같은 주소로 등록 -> CDN 이 옛 파일을 계속 줌
    · 48개 빌드가 대표 폰에 안 갔다 ("예전 버전에서 업데이트가 1도 안 됨")
  ?diag=1 이 `★어긋남` 으로 내내 알려주고 있었는데 눈으로 훑느라 못 봤다.
  -> 눈으로 보지 말고 **검사로 막는다.**
"""
import io, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')


def read(name):
    return io.open(os.path.join(ROOT, name), encoding='utf-8').read()


bad = []
html = read('index.html')

hits = re.findall(r"window\._SW_V\s*=\s*'(\d+)'", html)
if len(hits) != 1:
    bad.append('index.html 의 _SW_V 대입이 %d 곳이다 (딱 1곳이어야 한다): %s'
               % (len(hits), ', '.join(hits) or '없음'))

idx = hits[0] if len(hits) == 1 else None

# ★sw.js 에는 버전이 **세 자리**다 (2026-08-26에 데임).
#   CACHE_NAME 만 올리고 STATIC_CACHE/CDN_CACHE 를 두면 옛 캐시가 안 지워진다.
_swtxt = read('sw.js')
_names = ['murpy-v', 'murpy-static-v', 'murpy-cdn-v']
_vals = {}
for _n in _names:
    _m = re.search(re.escape(_n) + r'(\d+)', _swtxt)
    if not _m:
        bad.append('sw.js 에서 %sNNN 을 못 찾았다' % _n)
    else:
        _vals[_n] = _m.group(1)
sw = _vals.get('murpy-v')
if len(set(_vals.values())) > 1:
    bad.append('sw.js 안에서 버전이 서로 다르다 — ' +
               ', '.join('%s%s' % (k, v) for k, v in _vals.items()))

ver = read('version.txt').strip()

if idx and sw and ver:
    if not (idx == sw == ver):
        bad.append('버전이 어긋난다 — index.html=%s / sw.js=%s / version.txt=%s' % (idx, sw, ver))

if bad:
    print('배포 불가:')
    for b in bad:
        print('  x ' + b)
    sys.exit(1)

print('버전 OK — index.html / sw.js(3곳) / version.txt 모두 v%s, 대입 1곳' % idx)

# ★9-07 사고: 충돌 마커(<<<<<<<)가 index.html 에 남은 채 v1058 로 배포돼 실서비스가 잠깐 깨졌다.
#   버전 검사에 같이 건다 — 마커가 하나라도 있으면 실패.
import io as _io, sys as _sys
_bad = [f for f in ('index.html', 'sw.js', 'version.txt')
        if any(l.startswith(('<<<<<<< ', '>>>>>>> ')) for l in _io.open(f, encoding='utf-8', errors='ignore'))]
if _bad:
    print('  x 충돌 마커(<<<<<<< / >>>>>>>)가 남아 있다:', ', '.join(_bad)); _sys.exit(1)

# ★9-07: 모든 <script> 블록 파싱 검사(클래식 블록 포함). 쉼표 하나로 머피월드가 통째로 죽었다.
import subprocess as _sp
_r = _sp.run(['node', '--experimental-vm-modules', 'tools/all-scripts-syntax-check.mjs'], capture_output=True, text=True, encoding='utf-8', errors='ignore')
if _r.returncode != 0:
    print(_r.stdout.strip()); print('  x 스크립트 블록 문법 오류 — 배포 금지'); _sys.exit(1)
