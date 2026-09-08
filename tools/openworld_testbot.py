# -*- coding: utf-8 -*-
"""오픈월드 멀티 실검증용 테스트봇 — 관리자 토큰으로 RTDB plaza/players/<field>/murpy_testbot 에 '가짜 접속자'를 두고
길 위를 좌우로 걷게 한다. 대표 폰에서 그 맵에 들어가면 남의 캐릭터가 걷는 게 보여야 정상(수신 경로·규칙·렌더 검증).
홈 '지금 머피월드' 카드에도 1명으로 잡혀야 한다.

    PYTHONIOENCODING=utf-8 python tools/openworld_testbot.py --field park --minutes 15
    PYTHONIOENCODING=utf-8 python tools/openworld_testbot.py --clean          # 즉시 제거

끝나면(시간 만료·Ctrl+C) 노드를 지운다. 관리자 REST 라 규칙을 안 타므로 '쓰기 규칙' 검증은 아니다 — 그건 두 계정 실접속으로만.
"""
import io, os, sys, json, time, argparse, urllib.request
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from gcloud_oauth import get_token
BASE = 'https://murpyprototype-default-rtdb.asia-southeast1.firebasedatabase.app/'
UID = 'murpy_testbot'
# 공원 시작점(tc22,tr43) 근처 가로 벽돌길. 산책로/야외헬스장은 start 근처만 오간다.
PATH = { 'park': [(18, 43), (26, 43)], 'walk': [(2, 23), (8, 23)], 'outgym': [(40, 23), (45, 23)] }

def api(tok, path, data=None, method='GET'):
    req = urllib.request.Request(BASE + path + '.json', data=(json.dumps(data).encode() if data is not None else None), method=method,
                                 headers={'Authorization': 'Bearer ' + tok, 'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req).read().decode() or 'null')

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--field', default='park'); ap.add_argument('--minutes', type=float, default=15); ap.add_argument('--clean', action='store_true')
    a = ap.parse_args(); tok = get_token()
    if a.clean:
        for f in PATH: api(tok, 'plaza/players/%s/%s' % (f, UID), method='DELETE')
        print('테스트봇 제거'); return
    (c0, r0), (c1, r1) = PATH[a.field]
    node = 'plaza/players/%s/%s' % (a.field, UID)
    meta = { 'nick': '테스트봇', 'title': '', 'aura': '', 'frame': 'heart', 'emote': None, 'companion': 'butterfly',
             'character': { 'skin': '#F0C9A0', 'hair': 'hair_m_basic', 'hairColor': '#2B2B2B', 'top': 'top_basic_tee', 'topColor': '#3D7EFF', 'bottom': 'bottom_basic_shorts', 'shoes': None, 'acc': None, 'hat': None, 'mask': None, 'body': 'human' },
             'characterSheet': None, 'msg': { 'text': '멀티 테스트 중!', 't': int(time.time() * 1000) } }
    end = time.time() + a.minutes * 60; step = 0; tc, tr, d = c0, r0, 1
    try:
        while time.time() < end:
            face = 'right' if d > 0 else 'left'
            api(tok, node, dict(meta, tc=tc, tr=tr, face=face, t=int(time.time() * 1000)), 'PUT')
            if step % 10 == 0: print(time.strftime('%H:%M:%S'), a.field, tc, tr, face)
            time.sleep(2.6)                       # 한 칸 걷는 시간에 맞춰 천천히
            tc += d
            if tc >= c1 or tc <= c0: d = -d
            step += 1
    except KeyboardInterrupt: pass
    finally:
        api(tok, node, method='DELETE'); print('테스트봇 제거(종료)')

if __name__ == '__main__':
    main()
