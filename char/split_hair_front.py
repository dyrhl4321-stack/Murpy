# -*- coding: utf-8 -*-
"""헤어를 '귀 앞 / 귀 뒤'로 갈라 앞쪽만 지운다 = 옆머리를 귀 뒤로 넘긴 모습.

★왜 이렇게 하는가 (2026-08-03)
모자 조합 시트를 AI로 헤어6×모자2=12장 뽑으면 로고·골지·재질이 12가지로 갈린다.
생성형 AI라 매번 다르게 그리기 때문이고 이건 프롬프트로 못 잡는다.

스프라이트 제작 정석은 헤어를 **몸 앞 레이어 / 몸 뒤 레이어**로 나눠 그리는 것이다.
"옆머리를 귀 뒤로 넘긴다" = 얼굴 앞쪽 머리를 빼고 뒤쪽은 남기는 것이므로,
귀를 경계로 세로로 한 번 가르면 AI 없이 계산만으로 만들 수 있다.

  · 뒷머리 길이가 안 변한다(잘라내는 게 아니라 앞쪽만 빼므로)
  · 매번 똑같이 나온다. 로고·재질 불일치가 원천적으로 없다
  · 헤어를 새로 뽑아도 이 스크립트만 다시 돌리면 된다

★전에 폐기된 자동생성(311818f)과 다른 점: 그건 모자 밑단 기준 **가로** 자르기였다.
  이건 귀 기준 **세로** 가르기다.

경계는 base(고정 파일)에서 실측한 char/base_regions.py 상수를 그대로 쓴다.

    python char/split_hair_front.py hair_f_long human_f
    python char/split_hair_front.py hair_f_long human_f --apply
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
from base_regions import EAR_TOP_FB, EAR_BOX_PROF, ALPHA_BIN, CW, CH, largest  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ITEMS = HERE / "items"
BASEW = {"human": "walk.png", "human_f": "walk_female.png"}
ROW_KO = ["정면", "후면", "좌", "우"]
COL_KO = ["정지", "걸음A", "걸음B"]


def head_ref(bc: np.ndarray) -> tuple[int, int]:
    """base 셀에서 머리 최상단 y 와 두상 중심 x. 걸음 프레임마다 움직여서 열별로 잰다."""
    bm = largest(bc[:, :, 3] >= ALPHA_BIN)
    ys = np.nonzero(bm.any(axis=1))[0]
    top = int(ys.min())
    xs = np.nonzero(bm[top:top + 78].any(axis=0))[0]
    mid = (int(xs.min()) + int(xs.max())) // 2
    return top, mid


def front_zone(r: int, top: int, mid: int, base_name: str) -> np.ndarray:
    """이 셀에서 '귀 앞'에 해당하는 영역. 여기 있는 머리카락을 귀 뒤로 넘긴다(=지운다)."""
    z = np.zeros((CH, CW), bool)
    if r == 1:
        return z                                   # 후면은 옆머리가 안 보인다 — 손대지 않는다
    if r == 0:
        # 정면: 귀 높이 아래로 내려온 옆머리 다발. 그 위(정수리·이마)는 모자가 덮는다.
        z[top + EAR_TOP_FB[base_name][0]:] = True
        return z
    # 프로필: 귀 상자보다 얼굴 쪽. 눈썹 아래부터라야 앞머리가 안 깎인다.
    dx0, dx1, y0, _y1 = EAR_BOX_PROF[r]
    if r == 2:                                     # 왼쪽을 본다 → 얼굴이 왼쪽(x 작은 쪽)
        z[top + y0:, :mid + dx0] = True
    else:                                          # 오른쪽을 본다 → 얼굴이 오른쪽
        z[top + y0:, mid + dx1 + 1:] = True
    return z


def split(item_id: str, body: str, apply: bool) -> Path:
    base = np.asarray(Image.open(HERE / BASEW[body]).convert("RGBA")).astype(int)
    hair = np.asarray(Image.open(ITEMS / f"{item_id}.png").convert("RGBA")).copy()
    base_name = BASEW[body]

    total = 0
    for r in range(4):
        for c in range(3):
            top, mid = head_ref(base[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW])
            zone = front_zone(r, top, mid, base_name)
            cell = hair[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
            m = (cell[:, :, 3] >= ALPHA_BIN) & zone
            n = int(m.sum())
            if n:
                cell[m] = [0, 0, 0, 0]
                total += n
            print(f"   {ROW_KO[r]:2s} {COL_KO[c]:3s}  귀 앞 머리 {n:4d}px 넘김")

    # 넘긴 뒤 남은 고립 조각 정리 — 다발이 끊겨 점처럼 남으면 지저분하다
    for r in range(4):
        for c in range(3):
            cell = hair[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]
            a = cell[:, :, 3] >= ALPHA_BIN
            lab, n = ndimage.label(a, np.ones((3, 3), bool))
            if n <= 1:
                continue
            sizes = ndimage.sum(a, lab, range(1, n + 1))
            for i, s in enumerate(sizes, start=1):
                if s < 12:
                    cell[lab == i] = [0, 0, 0, 0]

    dst = ITEMS / (f"{item_id}.png" if apply else f"{item_id}__hat.png")
    Image.fromarray(hair, mode="RGBA").save(dst)
    print(f"{item_id}: 총 {total:,}px 을 귀 뒤로 넘김 → {dst.name}")
    return dst


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("item")
    ap.add_argument("body", choices=list(BASEW))
    ap.add_argument("--apply", action="store_true",
                    help="원본을 덮어쓴다. 기본은 <item>__hat.png 로 따로 저장")
    a = ap.parse_args()
    split(a.item, a.body, a.apply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
