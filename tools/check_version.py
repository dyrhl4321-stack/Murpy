# -*- coding: utf-8 -*-
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

m = re.search(r"murpy-v(\d+)", read('sw.js'))
sw = m.group(1) if m else None
if not sw:
    bad.append('sw.js 에서 murpy-vNNN 을 못 찾았다')

ver = read('version.txt').strip()

if idx and sw and ver:
    if not (idx == sw == ver):
        bad.append('버전이 어긋난다 — index.html=%s / sw.js=%s / version.txt=%s' % (idx, sw, ver))

if bad:
    print('배포 불가:')
    for b in bad:
        print('  x ' + b)
    sys.exit(1)

print('버전 OK — index.html / sw.js / version.txt 모두 v%s, 대입 1곳' % idx)
