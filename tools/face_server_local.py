# -*- coding: utf-8 -*-
"""서버 파이프라인(functions-py/facegen) 로컬 하네스 — 배포 없이 process() 를 통째로 돌려본다.

    python tools/face_server_local.py --raws <생성원본 폴더>            # 생성 대신 있는 원본을 순서대로 쓴다(무료)
    python tools/face_server_local.py --selfies <셀카> --gender 남      # 진짜 생성까지 (유료, 회당 ~$0.15)

산출: 스크래치 폴더에 sheet/hair/skin_t*/eyes.json + 대조 이미지. 서버 main.py 는 이 process() 결과를 올리기만 한다.
"""
import os, sys, io, glob, json, argparse
sys.stdout.reconfigure(encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__)); M = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(M, 'functions-py'))
sys.path.insert(0, HERE)
from facegen import pipeline
from face_pipeline import load_cfg
from PIL import Image

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--raws'); ap.add_argument('--selfies'); ap.add_argument('--gender', default='남')
    ap.add_argument('--out', default=os.path.join(os.environ.get('TEMP', '.'), 'face_server_local'))
    a = ap.parse_args()
    cfg = load_cfg()
    base_png = open(cfg[a.gender], 'rb').read()
    key = ''
    try: key = io.open(os.path.expanduser('~/.config/murpy/gemini.txt'), encoding='utf-8').read().strip()
    except Exception: pass
    gen_fn = None
    if a.raws:
        raws = sorted(p for p in glob.glob(os.path.join(a.raws, '*.png')) if not p.endswith('_ai.png') and not p.endswith('_hair.png'))
        print('원본 %d장으로 생성 대체' % len(raws))
        gen_fn = lambda i: open(raws[i % len(raws)], 'rb').read()
        selfies = []
    else:
        selfies = [('image/jpeg', open(a.selfies, 'rb').read())]
    res = pipeline.process(key, base_png, cfg['prompt'], selfies, a.out, attempts=3, gen_fn=gen_fn, base_path=pipeline.align_base(a.gender))
    print(json.dumps({k: v for k, v in res.items() if k != 'scores'}, ensure_ascii=False, indent=1))
    for s in res['scores']: print(' ', s.get('attempt'), s.get('verdict') or s.get('error'))
    # 대조 이미지: 시트 정면·뒤 + 헤어 + 톤 t1/t6
    cells = [Image.open(res['sheet']).convert('RGBA').crop((0, 0, 141, 224)), Image.open(res['sheet']).convert('RGBA').crop((0, 224, 141, 448))]
    if res['hair']: cells.append(Image.open(res['hair']).convert('RGBA').crop((0, 0, 141, 224)))
    for t in ('t1', 't6'):
        if t in res['skins']: cells.append(Image.open(res['skins'][t]).convert('RGBA').crop((0, 0, 141, 224)))
    W = 141 * len(cells) + 6 * (len(cells) - 1); out = Image.new('RGBA', (W, 224), (40, 40, 48, 255))
    for i, c in enumerate(cells): out.alpha_composite(c, (i * 147, 0))
    out.resize((W * 2, 448), Image.NEAREST).save(os.path.join(a.out, 'contact.png'))
    print('대조 이미지', os.path.join(a.out, 'contact.png'))
