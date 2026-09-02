# 얼굴 커마 시트 만들기 — ★AI 시트를 통째로 쓰지 않는다.
#
# 대표 8-26: "재진이도 옷을 입게해줘야지 ;; 얼굴영역만 자르고 나머지 몸통은 기본 base 그대로 쓸 거라고"
# AI 시트를 몸통까지 쓰면 실루엣이 base 와 미세하게 달라 옷 시트가 어긋난다.
# → **목 아래는 base 원본을 그대로** 쓰고, 목 위(머리)만 AI 시트에서 가져온다.
#   그러면 몸 실루엣이 base 와 픽셀 단위로 동일해져 human 옷이 전부 그대로 맞는다.
#
# 컷 라인은 고정값이 아니라 **셀마다 실측**한다 — 걸음 프레임마다 목 높이가 1~3px 다르다.
# 목 = 머리(넓다)와 어깨(넓다) 사이에서 폭이 최소인 y.
import sys, os
import numpy as np
from PIL import Image

M = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CW, CH = 141, 224

def neck_y(alpha_cell):
    w = (alpha_cell > 128).sum(axis=1)
    ys = np.where(w > 0)[0]
    if not len(ys): return 118
    top = ys.min()
    seg = w[top + 95:top + 120]
    return int(np.argmin(np.where(seg > 0, seg, 9999))) + top + 95

def graft(base_path, face_path, out_path):
    b = np.array(Image.open(base_path).convert("RGBA"))
    f = np.array(Image.open(face_path).convert("RGBA"))
    if b.shape != f.shape:
        raise SystemExit("시트 크기가 다르다: %s vs %s" % (b.shape, f.shape))
    out = b.copy()
    rep = []
    for r in range(4):
        for c in range(3):
            ys, xs = slice(r * CH, (r + 1) * CH), slice(c * CW, (c + 1) * CW)
            cut = neck_y(b[ys, xs, 3])
            out[r * CH:r * CH + cut, xs] = f[r * CH:r * CH + cut, xs]
            rep.append("r%dc%d:y%d" % (r, c, cut))
    Image.fromarray(out, "RGBA").save(out_path)
    print("graft -> %s   컷라인 %s" % (os.path.basename(out_path), " ".join(rep)))

if __name__ == "__main__":
    # 9-02 커마권 정형화 — 고객마다 경로를 인자로. 인자 없이 돌리면 재진(1호) 그대로.
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.path.join(M, "char", "walk.png"))
    ap.add_argument("--face", default=os.path.join(M, "char", "faces", "jaejin_src.png"))
    ap.add_argument("--out", default=os.path.join(M, "char", "faces", "jaejin.png"))
    a = ap.parse_args()
    graft(a.base, a.face, a.out)
