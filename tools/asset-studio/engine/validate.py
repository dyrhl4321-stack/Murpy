# -*- coding: utf-8 -*-
"""
아이템 레이어 검증.

기존 customizer_cli 의 validate_report.json 은 크기·투명존재·살색없음·빈프레임없음만 봤다.
그런데 skinPixels 는 _fill_interior_holes 가 살색을 옷 색으로 덮어버린 뒤를 검사하므로
버그가 지운 자리를 검사하는 꼴이었다. 실패가 항상 "ok": true 로 통과했다.

여기서는 기계적으로 판정 가능한 것만 게이트로 삼고,
사람이 봐야 할 프레임을 지목하는 정보 지표를 따로 낸다.
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

FRAME_W, FRAME_H, COLS, ROWS = 282, 448, 3, 4

# 게이트 임계값
MAX_SEMI_ALPHA_RATIO = 0.02     # 반투명 픽셀 비율
MAX_HALO_PX = 0                 # alpha 1~20 유령 픽셀
MAX_BODY_OVERPAINT = 0          # 몸을 옷 색으로 칠한 픽셀
MAX_FRAME_AREA_CV = 0.15        # walk 3프레임 간 면적 변동계수
MAX_COMPONENTS = 12             # 프레임당 연결성분 수


def _frame_slices(fw=FRAME_W, fh=FRAME_H, cols=COLS, rows=ROWS):
    for r in range(rows):
        for c in range(cols):
            yield r, c, slice(r * fh, (r + 1) * fh), slice(c * fw, (c + 1) * fw)


def validate(
    item: Image.Image,
    stats: dict | None = None,
    frame: tuple[int, int, int, int] = (FRAME_W, FRAME_H, COLS, ROWS),
) -> dict:
    fw, fh, cols, rows = frame
    expected = (fw * cols, fh * rows)
    arr = np.asarray(item.convert("RGBA"))
    alpha = arr[..., 3]

    visible = int((alpha > 40).sum())
    opaque = int((alpha == 255).sum())
    semi = int(((alpha > 0) & (alpha < 255)).sum())
    halo = int(((alpha > 0) & (alpha <= 20)).sum())
    semi_ratio = semi / max(opaque + semi, 1)

    areas = []
    comps = []
    empty = []
    for r, c, rs, cs in _frame_slices(fw, fh, cols, rows):
        m = alpha[rs, cs] > 40
        a = int(m.sum())
        areas.append(a)
        if a == 0:
            empty.append(f"r{r}c{c}")
        _lab, n = ndimage.label(m, structure=np.ones((3, 3)))
        comps.append(int(n))

    # walk 3프레임(같은 행)의 면적 변동계수 — 프레임 간 실루엣이 널뛰는지
    row_cv = []
    for r in range(rows):
        row_areas = np.array(areas[r * cols:(r + 1) * cols], dtype=float)
        if row_areas.mean() > 0:
            row_cv.append(float(row_areas.std() / row_areas.mean()))
    frame_area_cv = max(row_cv) if row_cv else 0.0

    body_overpaint = int((stats or {}).get("bodyOverpaintPx", 0))
    unk_px = int((stats or {}).get("unkPixels", 0))

    checks = {
        "size_exact": item.size == expected,
        "has_visible": visible > 0,
        "has_transparency": int((alpha == 0).sum()) > 0,
        "no_empty_frame": not empty,
        "semi_alpha_ok": semi_ratio <= MAX_SEMI_ALPHA_RATIO,
        "no_alpha_halo": halo <= MAX_HALO_PX,
        "no_body_overpaint": body_overpaint <= MAX_BODY_OVERPAINT,
        "frame_area_stable": frame_area_cv <= MAX_FRAME_AREA_CV,
        "components_ok": max(comps) <= MAX_COMPONENTS,
    }

    # 사람이 먼저 봐야 할 프레임 (게이트 아님, 안내용)
    attention = []
    if comps:
        worst = int(np.argmax(comps))
        if comps[worst] > 4:
            attention.append({"frame": f"r{worst // cols}c{worst % cols}",
                              "reason": f"연결성분 {comps[worst]}개 — 파편화 의심"})
    if unk_px > 0:
        attention.append({"frame": "all", "reason": f"UNK {unk_px}px — Gemini가 살을 다시 그린 영역"})

    return {
        "ok": all(checks.values()),
        "checks": checks,
        "metrics": {
            "size": list(item.size),
            "visiblePixels": visible,
            "opaquePixels": opaque,
            "semiAlphaPixels": semi,
            "semiAlphaRatio": round(semi_ratio, 4),
            "haloPixels": halo,
            "bodyOverpaintPx": body_overpaint,
            "unkPixels": unk_px,
            "frameAreaCV": round(frame_area_cv, 4),
            "componentsPerFrame": comps,
            "areaPerFrame": areas,
            "emptyFrames": empty,
        },
        "needsHumanAttention": attention,
    }
