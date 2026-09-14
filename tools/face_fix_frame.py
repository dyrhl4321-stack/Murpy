# -*- coding: utf-8 -*-
"""운영 커마 시트의 **한 칸**을 반대쪽 행의 같은 칸 좌우반전으로 갈아끼운다 — 걷기 행에서 한 프레임만 거꾸로 본 시트 수술용.

    PYTHONIOENCODING=utf-8 python tools/face_fix_frame.py --uid <uid> --cid <charId> --row 2 --col 2            # 드라이런(파일만 저장)
    PYTHONIOENCODING=utf-8 python tools/face_fix_frame.py --uid <uid> --cid <charId> --row 2 --col 2 --write    # 재업로드 + 문서 URL 갱신

★9-14 '윤이형'(왼쪽 걷기 행2 3번째 칸이 오른쪽을 봄). 이제는 서버 채점(score.facing_errors)이 이런 시트를 내보내지 않지만,
  이미 나간 시트는 재생성 없이 이걸로 고친다. sheet + hair + skin_t* 전부 같은 수술(같은 dx). 같은 객체 이름·같은 토큰으로 올리고
  faceChars 문서 URL 에 &r=<시각> 을 붙여 폰 SW 캐시 키를 바꾼다(face_reprocess_demagenta 와 같은 방식).
  행 번호: 0 아래(정면) · 1 위(뒷모습) · 2 왼쪽 · 3 오른쪽. --src-row 기본값 = 반대쪽 옆 행(2↔3).
"""
import sys, os, json, time, argparse, urllib.request, urllib.parse
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(ROOT, 'functions-py'))
from gcloud_oauth import get_token
from face_reprocess_demagenta import api, reupload, FS
from facegen import score
CW, CH = 141, 224


def cx(m):
    xs = np.where(m.any(0))[0]
    return (xs.min() + xs.max()) / 2.0 if len(xs) else None


def fix(A, row, col, src_row, dx=None):
    """행 row 칸 col ← 행 src_row 칸 col 좌우반전 + 중심 보정. dx 를 주면 그대로(헤어·스킨은 시트에서 잰 값 재사용)."""
    A = A.copy(); op = A[..., 3] > 128
    if dx is None:
        shifts = []
        for c in range(3):
            if c == col: continue
            l = cx(op[row*CH+100:row*CH+150, c*CW:(c+1)*CW]); r = cx(op[src_row*CH+100:src_row*CH+150, c*CW:(c+1)*CW])
            if l is not None and r is not None: shifts.append(l - (CW - 1 - r))
        dx = int(round(sum(shifts) / len(shifts))) if shifts else 0
    src = A[src_row*CH:(src_row+1)*CH, col*CW:(col+1)*CW][:, ::-1]
    dst = np.zeros_like(src)
    if dx >= 0: dst[:, dx:] = src[:, :CW-dx]
    else: dst[:, :CW+dx] = src[:, -dx:]
    A[row*CH:(row+1)*CH, col*CW:(col+1)*CW] = dst
    return A, dx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--uid', required=True); ap.add_argument('--cid', required=True)
    ap.add_argument('--row', type=int, required=True); ap.add_argument('--col', type=int, required=True)
    ap.add_argument('--src-row', type=int); ap.add_argument('--write', action='store_true')
    ap.add_argument('--out', default=os.path.join(os.environ.get('TEMP', '.'), 'face_fix_frame'))
    a = ap.parse_args()
    src_row = a.src_row if a.src_row is not None else {2: 3, 3: 2}.get(a.row)
    if src_row is None: sys.exit('--src-row 를 주세요(옆 행이 아니면 자동으로 못 정한다)')
    os.makedirs(a.out, exist_ok=True)
    tok = get_token()
    doc = api(tok, FS + 'users/%s/faceChars/%s' % (a.uid, a.cid))['fields']
    urls = {'sheetUrl': doc['sheetUrl']['stringValue'], 'hairUrl': doc.get('hairUrl', {}).get('stringValue')}
    for t, v in (doc.get('skinUrls', {}).get('mapValue', {}).get('fields') or {}).items(): urls['skinUrls.' + t] = v['stringValue']
    patch = {'fields': {}}; sheet_dx = None
    for fld, url in urls.items():
        if not url: continue
        name = urllib.parse.unquote(url.split('/o/')[1].split('?')[0]); token = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get('token', [''])[0]
        raw = np.array(Image.open(urllib.request.urlopen(url)).convert('RGBA'))
        fixed, dx = fix(raw, a.row, a.col, src_row, sheet_dx)
        if fld == 'sheetUrl': sheet_dx = dx
        errs = score.facing_errors(fixed) if fld != 'hairUrl' else []
        out = os.path.join(a.out, fld.replace('.', '_') + '.png'); Image.fromarray(fixed).save(out)
        print('%-14s dx=%+d  방향 검사: %s  %s' % (fld, dx, errs or 'OK', '→ 재업로드' if a.write else '(드라이런)'))
        if errs: sys.exit('수술 뒤에도 방향 검사에 걸린다 — 손으로 봐야 한다')
        if a.write:
            reupload(tok, name, open(out, 'rb').read(), token)
            newurl = url.split('&r=')[0] + '&r=' + str(int(time.time()))
            if fld.startswith('skinUrls.'):
                patch['fields'].setdefault('skinUrls', {'mapValue': {'fields': {}}})['mapValue']['fields'][fld.split('.')[1]] = {'stringValue': newurl}
            else: patch['fields'][fld] = {'stringValue': newurl}
    if a.write and patch['fields']:
        mask = '&'.join('updateMask.fieldPaths=' + k for k in patch['fields'])
        api(tok, FS + 'users/%s/faceChars/%s?%s' % (a.uid, a.cid, mask), json.dumps(patch).encode(), 'PATCH')
        print('faceChars 문서 URL 갱신(&r=)', list(patch['fields'].keys()))
        # 지금 입고 있으면 users 문서의 사본도 같이(남이 나를 그릴 때 쓰는 주소)
        u = api(tok, FS + 'users/%s?mask.fieldPaths=character&mask.fieldPaths=characterSheet' % a.uid).get('fields', {})
        body = ((u.get('character') or {}).get('mapValue', {}).get('fields', {}).get('body') or {}).get('stringValue', '')
        if body == 'face:' + a.cid:
            up = {'fields': {}}
            if patch['fields'].get('sheetUrl'): up['fields']['characterSheet'] = patch['fields']['sheetUrl']
            if patch['fields'].get('hairUrl'): up['fields']['characterHair'] = patch['fields']['hairUrl']
            if up['fields']:
                api(tok, FS + 'users/%s?%s' % (a.uid, '&'.join('updateMask.fieldPaths=' + k for k in up['fields'])), json.dumps(up).encode(), 'PATCH')
                print('users 문서 characterSheet/characterHair 도 갱신')
    print('저장 위치', a.out)


if __name__ == '__main__':
    main()
