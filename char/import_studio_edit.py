# -*- coding: utf-8 -*-
"""대표가 에셋 스튜디오로 고친 수정본을 검증하고 반영한다.

수정본 위치: Desktop\\머피브랜딩\\머피월드 캐릭터\\커스터마이징 3차\\머피에셋스튜디오 수정본\\...

■ 무엇을 검사하나
1. 규격이 base 시트와 같은가 (423x896)
2. 반투명 픽셀 (알파 하드룰 = 128 이진화). 리터치 툴이 남기면 여기서 잡아 이진화한다.
3. 현재 배포본과 **합성 화면**이 얼마나 달라지는가 (알파로 재면 속는다 — 7-31 교훈)

■ 살색은 지우지 않는다 (7-31 교훈)
"헤어 레이어에 살색 금지" 규칙으로 살색을 일괄 제거했다가 세미리프컷 정면에
M자 탈모를 만들었다. base 와 같은 색을 덮고 있던 살색은 지워도 화면이 안 변하고,
그 사이에 섞인 진짜 머리카락만 잃는다. **대표가 그린 대로 반영한다.**

    python char/import_studio_edit.py 여자헤어/hair_f_basic.png human_f
    python char/import_studio_edit.py 여자헤어/hair_f_basic.png human_f --apply
"""
import os
import shutil
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ITEMS = os.path.join(HERE, "items")
STUDIO = os.path.join(os.path.expanduser("~"), "Desktop", "머피브랜딩", "머피월드 캐릭터",
                      "커스터마이징 3차", "머피에셋스튜디오 수정본")
CW, CH = 141, 224
ALPHA_BIN = 128
ROWS = ["정면", "후면", "좌", "우"]
BASE = {"human": "walk.png", "human_f": "walk_female.png"}


def cell(s, r, c):
    return s[r * CH:(r + 1) * CH, c * CW:(c + 1) * CW]


def over(dst, src):
    out = dst.copy()
    m = src[:, :, 3] >= ALPHA_BIN
    out[m] = src[m]
    out[m, 3] = 255
    return out


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    rel, body = sys.argv[1], sys.argv[2]
    apply = "--apply" in sys.argv
    name = os.path.basename(rel)

    src_p = os.path.join(STUDIO, rel.replace("/", os.sep))
    cur_p = os.path.join(ITEMS, name)
    if not os.path.exists(src_p):
        print(f"!! 수정본 없음 {src_p}")
        return

    base = np.asarray(Image.open(os.path.join(HERE, BASE[body])).convert("RGBA")).astype(int)
    new = np.asarray(Image.open(src_p).convert("RGBA")).astype(int)
    cur = (np.asarray(Image.open(cur_p).convert("RGBA")).astype(int)
           if os.path.exists(cur_p) else None)

    print(f"■ {name}  ({body} / {BASE[body]})")
    print(f"  수정본 {new.shape[1]}x{new.shape[0]}   base {base.shape[1]}x{base.shape[0]}")
    if new.shape[:2] != base.shape[:2]:
        print("  !! 규격 불일치 — 반영 중단")
        return

    semi = int(((new[:, :, 3] > 0) & (new[:, :, 3] < 255)).sum())
    print(f"  반투명 {semi}px {'→ 128 기준 이진화한다' if semi else '(없음)'}")
    out = new.copy()
    out[:, :, 3] = np.where(out[:, :, 3] >= ALPHA_BIN, 255, 0)
    out[out[:, :, 3] == 0] = 0                      # 투명 픽셀의 RGB 도 비운다

    if cur is not None:
        print("  현재 배포본 대비:")
        for r in range(4):
            da = dv = 0
            for c in range(3):
                bc = cell(base, r, c)
                a1 = cell(cur, r, c)[:, :, 3] >= ALPHA_BIN
                a2 = cell(out, r, c)[:, :, 3] >= ALPHA_BIN
                da += int((a1 ^ a2).sum())
                c1, c2 = over(bc, cell(cur, r, c)), over(bc, cell(out, r, c))
                dv += int((np.abs(c1[:, :, :3] - c2[:, :, :3]).sum(axis=2) > 24).sum())
            print(f"    {ROWS[r]:2s}  알파 {da:5d}px   화면 {dv:5d}px")

    # 눈으로 볼 비교 렌더 (현재 위 / 수정본 아래)
    canvas = Image.new("RGB", (CW * 4, CH * 2 + 8), (250, 250, 250))
    for r in range(4):
        bc = cell(base, r, 0)
        if cur is not None:
            im = over(bc, cell(cur, r, 0))
            canvas.paste(Image.fromarray(im.astype(np.uint8), "RGBA").convert("RGB"),
                         (r * CW, 0))
        im = over(bc, cell(out, r, 0))
        canvas.paste(Image.fromarray(im.astype(np.uint8), "RGBA").convert("RGB"),
                     (r * CW, CH + 8))
    p = os.path.join(HERE, "_diag", f"import_{name}")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    canvas.resize((canvas.width * 3, canvas.height * 3), Image.NEAREST).save(p)
    print(f"  -> 비교 렌더 {p}  (위=현재 / 아래=수정본)")

    if apply:
        if cur is not None:
            shutil.copy2(cur_p, os.path.join(HERE, "_diag", f"before_{name}"))
        Image.fromarray(out.astype(np.uint8), "RGBA").save(cur_p)
        print(f"  -> 적용됨 {cur_p}")
    else:
        print("  (적용하려면 --apply)")


if __name__ == "__main__":
    main()
