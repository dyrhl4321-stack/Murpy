# 피부톤 굽기 v2 — ★이진 마스크를 버리고 **부드러운 가중치**로 바꾼다.
#
# v1 의 문제(대표 8-26): "이마쪽 가로선 기준으로 하단부만 피부색이 바뀜, 얼룩덜룩"
#   채도 0.35 로 **딱 잘라서** 생긴 경계다. 이마 하이라이트는 밝아 채도가 낮은데
#   그 줄에서 마스크가 꺼지니 위아래가 다른 색이 됐다.
# → 색상 근접도와 채도를 각각 0~1 가중치로 만들어 곱한다. 경계가 없어진다.
from PIL import Image
import numpy as np
import colorsys, io, os

M = r"C:\Users\allys\Murpy"
OUT = os.path.join(M, "char", "skin")
os.makedirs(OUT, exist_ok=True)

REF = (0xF5, 0xA9, 0x7D)
# ★어두울수록 **채도를 낮춘다**. 실제 어두운 피부는 채도가 낮은데, 주황빛 그대로 어둡게만
#   하면 적갈색으로 읽힌다(대표 8-26: "6,7단계 눈 깔 아직 빨간 빛 도는데").
#   실측으로 확인: t7 의 대표 색이 #874927 로 목표 톤 그 자체였다 — 튄 게 아니라 색이 붉었다.
TONES = {"t1": 0xFBD3B4, "t2": 0xF8BE97, "t4": 0xD9946A,
         "t5": 0xBC7F58, "t6": 0x96654A, "t7": 0x6B4835}

H_MID, H_HALF = 0.072, 0.085      # 피부 색상대 중심과 반경
S_LO, S_HI = 0.12, 0.38           # 채도 가중치가 0→1 로 오르는 구간

def rgb2hsl(a):
    rgb = a[..., :3].astype(np.float32) / 255.0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(2), rgb.min(2)
    L = (mx + mn) / 2
    d = mx - mn
    S = np.zeros_like(L)
    nz = d > 1e-6
    den = np.where(L < 0.5, mx + mn, 2.0 - mx - mn)
    S[nz] = d[nz] / np.maximum(den[nz], 1e-6)
    H = np.zeros_like(L)
    rm = nz & (mx == r); gm = nz & (mx == g) & ~rm; bm = nz & (mx == b) & ~rm & ~gm
    H[rm] = ((g - b)[rm] / d[rm]) % 6
    H[gm] = ((b - r)[gm] / d[gm]) + 2
    H[bm] = ((r - g)[bm] / d[bm]) + 4
    return H / 6.0, S, L

def hsl2rgb(H, S, L):
    C = (1 - np.abs(2 * L - 1)) * S
    X = C * (1 - np.abs(((H * 6) % 2) - 1))
    m = L - C / 2
    h6 = np.clip((H * 6).astype(np.int32) % 6, 0, 5)
    z = np.zeros_like(C)
    sel = [h6 == i for i in range(6)]
    R = np.select(sel, [C, X, z, z, X, C]) + m
    G = np.select(sel, [X, C, C, X, z, z]) + m
    B = np.select(sel, [z, z, X, C, C, X]) + m
    return R, G, B

log = io.open("skin_bake2.txt", "w", encoding="utf-8")

def bake(src, pre):
    im = Image.open(src).convert("RGBA")
    a = np.array(im)
    H, S, L = rgb2hsl(a)
    alpha = a[..., 3]

    # ★부드러운 가중치 — 딱 자르지 않는다
    hd = np.abs(((H - H_MID + 0.5) % 1.0) - 0.5)          # 색상 거리(원형)
    wH = np.clip(1.0 - hd / H_HALF, 0, 1)
    wH = wH * wH * (3 - 2 * wH)                            # smoothstep
    wS = np.clip((S - S_LO) / (S_HI - S_LO), 0, 1)
    wS = wS * wS * (3 - 2 * wS)
    # ★어두운 픽셀(눈·외곽선)을 보호한다. 예전엔 L 0.06 부터 열려 있어 눈 테두리까지 물들었고,
    #   어두운 톤에서 그 라인이 적갈색으로 튀어 "눈이 빨개진다"가 됐다(대표 8-26).
    wL = np.clip((L - 0.20) / 0.16, 0, 1) * np.clip((0.985 - L) / 0.06, 0, 1)
    w = wH * wS * wL
    w = np.where(alpha > 128, w, 0)
    log.write("  %-22s 가중치>0.5 인 픽셀 %.1f%%  (평균 %.2f)\n"
              % (os.path.basename(src), (w > 0.5).mean() * 100, w[w > 0].mean() if (w > 0).any() else 0))

    rh, rl, rs = colorsys.rgb_to_hls(REF[0] / 255, REF[1] / 255, REF[2] / 255)
    for name, hexv in TONES.items():
        t = ((hexv >> 16) & 255, (hexv >> 8) & 255, hexv & 255)
        th, tl, ts = colorsys.rgb_to_hls(t[0] / 255, t[1] / 255, t[2] / 255)
        dh, dl, sr = th - rh, tl - rl, ts / max(rs, 1e-6)

        H2 = (H + dh * w) % 1.0
        # ★★밝기는 **중앙만 옮기고 명암 차이는 유지**한다 (대표 8-26: "6단계부터 이목구비가 이상").
        #   비율(L*lr)로 하면 어두워질 때 **편차도 같은 비율로 줄어** 이목구비가 뭉개진다.
        #   실측: 피부 L 은 0.38~0.75, 중앙 0.72. t7 은 lr 0.44 라 편차가 0.37 -> 0.16 이 됐다.
        #   -> 중앙을 목표 밝기로 옮기고 편차는 k 배만 남긴다. k 는 아래가 0 으로 잘리지 않는 선.
        LM = 0.72                       # 기준 시트 피부 중앙 밝기(실측)
        k = min(0.95, max(0.55, tl / 0.36))   # 어두운 톤일수록 살짝만 눌러 클램프를 피한다
        Lt = np.clip(tl + (L - LM) * k, 0, 1)
        L2 = np.clip(L + (Lt - L) * w, 0, 1)
        # ★채도 상한 — 그림자처럼 원래 채도가 높은 픽셀이 어두운 톤에서 **적갈색으로 튄다**.
        St = np.minimum(S * sr, ts * 1.25)
        S2 = np.clip(S + (St - S) * w, 0, 1)
        R, G, B = hsl2rgb(H2, S2, L2)
        o = a.copy()
        o[..., 0] = np.clip(R * 255, 0, 255)
        o[..., 1] = np.clip(G * 255, 0, 255)
        o[..., 2] = np.clip(B * 255, 0, 255)
        o[..., 3] = np.where(alpha >= 128, 255, 0)
        Image.fromarray(o.astype(np.uint8), "RGBA").save(os.path.join(OUT, pre + "_" + name + ".png"))

for src, pre in [(os.path.join(M, "char", "walk.png"), "walk"),
                 (os.path.join(M, "char", "walk_female.png"), "walk_female"),
                 (os.path.join(M, "char", "faces", "jaejin.png"), "face_jaejin")]:
    bake(src, pre)
log.close()
print("ok")
