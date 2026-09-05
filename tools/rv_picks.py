# -*- coding: utf-8 -*-
"""검수 페이지(murpy.app/rv/*)에서 대표가 고른 것을 읽어온다 (2026-09-04).

    python tools/rv_picks.py                # 기본: audio-0904
    python tools/rv_picks.py --page audio-0904 --watch

대표는 카페에서 폰으로 검수한다 — '고르기' 를 누르면 RTDB `rv/<page>/<슬롯>` 에 바로 기록되고
이 스크립트가 그걸 읽는다. 대표가 복사·붙여넣기 하거나 타이핑할 필요가 없다.
읽기는 firebase CLI 로그인 토큰(관리자)으로 하므로 규칙의 auth 조건을 통과한다.
"""
import io, os, sys, json, time, argparse, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding='utf-8')

CID = '563584335869-fgrhgmd47bqnekij5i8b5pr03ho849e6.apps.googleusercontent.com'
CSEC = 'j9iVZfS8kkCEFUPaAeJV0sAi'
DB = 'https://murpyprototype-default-rtdb.asia-southeast1.firebasedatabase.app'


def token():
    cfg = json.load(io.open(os.path.expanduser('~/.config/configstore/firebase-tools.json'), encoding='utf-8'))
    return json.loads(urllib.request.urlopen(urllib.request.Request(
        'https://oauth2.googleapis.com/token',
        urllib.parse.urlencode({'client_id': CID, 'client_secret': CSEC,
                                'refresh_token': cfg['tokens']['refresh_token'],
                                'grant_type': 'refresh_token'}).encode())).read())['access_token']


def read(page, tok):
    url = '%s/rv/%s.json?access_token=%s' % (DB, urllib.parse.quote(page), tok)
    return json.loads(urllib.request.urlopen(url, timeout=20).read().decode() or 'null')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--page', default='audio-0904')
    ap.add_argument('--watch', action='store_true', help='20초마다 다시 읽어 변화만 출력')
    a = ap.parse_args()
    tok = token()
    last = None
    while True:
        d = read(a.page, tok)
        if d != last:
            if not d:
                print('아직 고른 게 없다')
            else:
                for k, v in d.items():
                    print('%s → %s' % (k, v))
            last = d
        if not a.watch:
            break
        time.sleep(20)
