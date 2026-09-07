"""물 애니 = 원본 그림의 물 픽셀을 위상(phase)으로 흘린 완벽 루프 스트립.
9-07 대표: 제미나이 프레임은 서로 이어지지 않아 "끊겼다 생겼다" → 프레임 간 연속성이 보장되는 절차 애니로.
 사용: python tools/water_anim.py fount|pond
"""
import sys, numpy as np
from PIL import Image
N = 24
import json, os
BOX = json.load(open('char/fields/anim/water_boxes.json')) if os.path.exists('char/fields/anim/water_boxes.json') else None
def load(box):
    im = Image.open(BOX['src'] if BOX else 'char/fields/field_park2.png').convert('RGB'); W, H = im.size
    x0, y0, x1, y1 = box
    return np.array(im.crop((x0, y0, x1, y1))).astype(np.float32), (W, H)
def water_mask(a, kind):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    if kind == 'fount':   # 파랑·하늘색 물(회색 돌·베이지 바닥 제외)
        return (b > r + 35) & (b > g + 8) & (b > 120)
    # pond: 보라빛 파랑 물. 수련잎(초록)·오리(분홍/흰)·갈대(초록/갈색)·둑(갈색) 제외
    return (b > r + 15) & (b > g + 15) & (b > 110) & (g < 190)
def sample(a, mask, xs, ys):
    """(ys,xs) 실수 좌표에서 물 픽셀만 보간해 가져온다. 마스크 밖으로 나가면 제자리 값."""
    H, W = mask.shape
    xi = np.clip(np.round(xs).astype(int), 0, W - 1); yi = np.clip(np.round(ys).astype(int), 0, H - 1)
    ok = mask[yi, xi]
    out = a.copy()
    yy, xx = np.where(mask)
    out[yy, xx] = np.where(ok[yy, xx][:, None], a[yi[yy, xx], xi[yy, xx]], a[yy, xx])
    return out
def run(kind):
    if BOX: box = tuple(BOX[kind])
    elif kind == 'fount': box = (796, 850, 1120, 1207)
    else:
        W = H = 2048; box = (int(W * .1772), int(H * .1958), int(W * .1772) + int(W * .2114), int(H * .1958) + int(H * .1401))
    a, (W, H) = load(box); h, w = a.shape[:2]
    m = water_mask(a, kind)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    frames = []
    for k in range(N):
        t = 2 * np.pi * k / N
        if kind == 'fount':
            # 위(물줄기): 아래로 흐르는 파동 — y 방향 2px 흔들림 + 밝기 물결. 아래(수반): 잔물결 x 흔들림
            top = yy < h * 0.62
            dy = np.where(top, 2.0 * np.sin(2 * np.pi * yy / 14 - t * 2 + xx * 0.05), 0.0)
            dx = np.where(top, 0.0, 1.6 * np.sin(2 * np.pi * yy / 9 + t) + 0.8 * np.sin(2 * np.pi * xx / 23 - t))
            shade = np.where(top, 0.10 * np.sin(2 * np.pi * yy / 14 - t * 2 + xx * 0.05), 0.06 * np.sin(2 * np.pi * (xx + yy) / 26 - t))
        else:
            dx = 1.8 * np.sin(2 * np.pi * yy / 18 + t) + 0.9 * np.sin(2 * np.pi * xx / 31 - t * 1.0)
            dy = 0.9 * np.sin(2 * np.pi * xx / 22 - t)
            shade = 0.055 * np.sin(2 * np.pi * (0.8 * xx + yy) / 40 - t) + 0.03 * np.sin(2 * np.pi * xx / 13 + t * 2)
        f = sample(a, m, xx + dx, yy + dy)
        f = np.where(m[..., None], np.clip(f * (1 + shade[..., None]), 0, 255), f)
        frames.append(Image.fromarray(f.astype(np.uint8)))
    strip = Image.new('RGB', (w * N, h))
    for i, fr in enumerate(frames): strip.paste(fr, (i * w, 0))
    out = 'char/fields/anim/%s_loop.png' % kind
    strip.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE).save(out, optimize=True)
    print(out, strip.size, 'water px', int(m.sum()))
    # 미리보기 gif
    frames[0].save('char/fields/work/%s_loop.gif' % kind, save_all=True, append_images=frames[1:], duration=100, loop=0)
if __name__ == '__main__':
    run(sys.argv[1])
