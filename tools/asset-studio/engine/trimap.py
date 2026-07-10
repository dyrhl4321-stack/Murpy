# -*- coding: utf-8 -*-
"""
Trimap diff 추출 엔진 (Murpy Asset Studio).

기존 customizer_cli.cmd_extract_diff 의 두 버그를 고친다:

1. _is_skin 이 diff 픽셀을 "버리면" 옷 안에 구멍이 남고,
   _fill_interior_holes 가 그 구멍을 옷 색으로 칠해 팔에 셔츠를 페인트했다.
   → 살색 diff 를 UNK(미확정)로 분리하고, base 가 살색인 구멍은 채우지 않는다.

2. 비정수 배율 LANCZOS 리사이즈가 알파를 파괴했다.
   → ingest 는 정수배 NEAREST 만 허용한다 (legacy 모드로만 우회).

산출: mask(FG 이진) / trimap(FG255·UNK128·BG0) / item(worn 픽셀 복사).
worn 의 RGB 는 절대 재생성하지 않는다. 마스크만 정한다.
"""
from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

# 기본 프레임 규격 (v2)
FRAME_W, FRAME_H, COLS, ROWS = 282, 448, 3, 4

DIFF_THRESHOLD = 85          # customizer_cli.py 와 동일
WORN_ALPHA_MIN = 60          # customizer_cli.py:313 과 동일

# 슬롯별 프레임-로컬 세로 영역 (customizer_cli.SLOT_REGIONS 와 동일)
SLOT_REGIONS = {
    "hair": (0.00, 0.42),
    "hat": (0.00, 0.40),
    "top": (0.30, 0.84),
    "bottom": (0.55, 0.93),
    "shoes": (0.84, 1.00),
    "accessory": (0.00, 1.00),
}

# 슬롯별 파편 제거 최소 크기. accessory/hair 는 얇은 파츠(이어컵·머리끝)를 지키려고 0.
SLOT_MIN_COMPONENT = {
    "hair": 0,
    "hat": 22,
    "top": 22,
    "bottom": 22,
    "shoes": 12,
    "accessory": 0,
}

TRIMAP_BG, TRIMAP_UNK, TRIMAP_FG = 0, 128, 255


def is_skin(rgba: np.ndarray) -> np.ndarray:
    """customizer_cli._is_skin 과 완전히 동일한 판정을 벡터화한 것.

    r > 150 and g > 80 and b < 150 and (r - b) > 30, alpha > 0
    """
    r, g, b, a = rgba[..., 0], rgba[..., 1], rgba[..., 2], rgba[..., 3]
    return (a > 0) & (r > 150) & (g > 80) & (b < 150) & ((r - b) > 30)


class IngestError(RuntimeError):
    pass


def ingest_worn(worn: Image.Image, target_size: tuple[int, int], legacy: bool = False) -> tuple[Image.Image, dict]:
    """worn 시트를 base 규격으로 맞춘다.

    엄격 모드: 크기가 같거나 정수배일 때만 NEAREST 로 축소. 그 외에는 에러.
    legacy=True 는 기존 산출물 재현/비교용 탈출구이며 알파를 파괴한다.
    """
    tw, th = target_size
    w, h = worn.size
    info = {"original": [w, h], "mode": None, "resized_to": [tw, th]}

    if (w, h) == (tw, th):
        info["mode"] = "identity"
        return worn.copy(), info

    if w % tw == 0 and h % th == 0 and (w // tw) == (h // th):
        factor = w // tw
        info["mode"] = f"nearest_1/{factor}"
        return worn.resize((tw, th), Image.NEAREST), info

    if not legacy:
        raise IngestError(
            f"worn {w}x{h} 는 base {tw}x{th} 의 정수배가 아닙니다. "
            f"비정수 리사이즈는 픽셀아트의 알파 경계를 파괴합니다. "
            f"Gemini 캔버스를 {tw}x{th} 또는 {tw*2}x{th*2} 로 고정하세요. "
            f"(기존 산출물 비교용으로만 legacy=True 사용)"
        )

    info["mode"] = "legacy_lanczos"
    return worn.resize((tw, th), Image.LANCZOS), info


def _frames(cols: int = COLS, rows: int = ROWS, fw: int = FRAME_W, fh: int = FRAME_H):
    for r in range(rows):
        for c in range(cols):
            yield r, c, slice(r * fh, (r + 1) * fh), slice(c * fw, (c + 1) * fw)


def _exterior_transparent(opaque: np.ndarray) -> np.ndarray:
    """가장자리에서 도달 가능한 투명 영역. 나머지 투명 영역이 '내부 구멍'."""
    transparent = ~opaque
    labels, n = ndimage.label(transparent)
    if n == 0:
        return transparent
    border = np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])
    outside = np.unique(border)
    outside = outside[outside > 0]
    return np.isin(labels, outside)


def _remove_small_fragments(mask: np.ndarray, min_size: int) -> int:
    """작은/가느다란 연결성분을 제거. customizer_cli._remove_small_fragments 규칙 유지."""
    if min_size <= 0:
        return 0
    labels, n = ndimage.label(mask, structure=np.ones((3, 3)))
    if n == 0:
        return 0
    removed = 0
    for sl, idx in zip(ndimage.find_objects(labels), range(1, n + 1)):
        comp = labels[sl] == idx
        size = int(comp.sum())
        ch, cw = comp.shape
        thin = cw <= 2 or ch <= 2
        if size < min_size or (thin and size < 140) or (size < 90 and cw <= 4):
            region = mask[sl]
            region[comp] = False
            removed += size
    return removed


def _fill_interior_holes(
    mask: np.ndarray,
    still_body: np.ndarray,
    legacy: bool,
) -> dict:
    """아이템 마스크에 2D로 둘러싸인 투명 구멍을 메운다.

    구멍이 '옷 안쪽'을 뜻하지는 않는다. 팔과 몸통 사이의 겨드랑이 틈도 2D 상으로는
    옷에 둘러싸인 구멍이다. 기존 코드는 그 틈까지 옷 색으로 칠했다.

    구멍을 그대로 남겨야 하는 유일한 경우는
        base 도 살색이고 worn 도 살색일 때
    즉 "원래 몸이었고 지금도 몸으로 보이는" 곳이다 (겨드랑이 틈, 모자 밑 목덜미).

    그 외에는 채운다:
      - worn 이 투명 (모자 꼭지의 소스 구멍)
      - base 가 속옷 (body_bald 는 나체가 아니라 베이지 탱크톱·반바지를 입고 있다.
        회색 버뮤다가 그 베이지와 diff 80 으로 임계값 85 아래라 '안 변함'으로 오분류되지만,
        그 위를 옷이 덮는 게 맞다)
    """
    exterior = _exterior_transparent(mask)
    holes = (~mask) & (~exterior)
    if not holes.any():
        return {"filled": 0, "bodyHolesSkipped": 0}

    if legacy:
        filled = int(holes.sum())
        mask[holes] = True
        return {"filled": filled, "bodyHolesSkipped": 0,
                "_legacy_bodyPainted": int((holes & still_body).sum())}

    keep = holes & still_body
    fillable = holes & ~still_body

    filled = int(fillable.sum())
    if filled:
        mask[fillable] = True
    return {"filled": filled, "bodyHolesSkipped": int(keep.sum())}


def extract(
    base_img: Image.Image,
    worn_img: Image.Image,
    slot: str,
    threshold: int = DIFF_THRESHOLD,
    frame: tuple[int, int, int, int] = (FRAME_W, FRAME_H, COLS, ROWS),
    min_component: int | None = None,
    legacy_holes: bool = False,
) -> dict:
    """base 와 worn 을 비교해 아이템 마스크/트라이맵/아이템 레이어를 만든다.

    legacy_holes=True 는 기존(버그 있는) 동작을 그대로 재현해 비교하기 위한 것.
    """
    if slot not in SLOT_REGIONS:
        raise ValueError(f"unknown slot: {slot}")

    fw, fh, cols, rows = frame
    size = (fw * cols, fh * rows)
    if base_img.size != size:
        raise ValueError(f"base size {base_img.size} != expected {size}")
    if worn_img.size != size:
        raise ValueError(f"worn size {worn_img.size} != expected {size}")

    if min_component is None:
        min_component = SLOT_MIN_COMPONENT.get(slot, 22)

    base = np.asarray(base_img.convert("RGBA"), dtype=np.int16)
    worn = np.asarray(worn_img.convert("RGBA"), dtype=np.int16)

    y0 = int(SLOT_REGIONS[slot][0] * fh)
    y1 = int(SLOT_REGIONS[slot][1] * fh)

    H, W = size[1], size[0]
    fg = np.zeros((H, W), dtype=bool)
    unk = np.zeros((H, W), dtype=bool)
    changed_all = np.zeros((H, W), dtype=bool)

    # base 도 살색, worn 도 살색 → 여전히 몸. 구멍으로 남겨야 하는 유일한 조건.
    still_body = is_skin(base) & is_skin(worn)

    # --- 1. trimap ---
    for _r, _c, rs, cs in _frames(cols, rows, fw, fh):
        band = slice(rs.start + y0, rs.start + y1)
        b = base[band, cs]
        w = worn[band, cs]
        d = np.abs(b - w).sum(axis=2)
        changed = d > threshold
        alpha_ok = w[..., 3] > WORN_ALPHA_MIN
        skin = is_skin(w)

        changed_all[band, cs] = changed
        fg[band, cs] = changed & alpha_ok & ~skin
        unk[band, cs] = changed & alpha_ok & skin

    diff_px = int(changed_all.sum())
    unk_px = int(unk.sum())

    # --- 2. cleanup (프레임 단위) ---
    frags_removed = 0
    holes_filled = 0
    body_holes_skipped = 0
    legacy_body_painted = 0
    for _r, _c, rs, cs in _frames(cols, rows, fw, fh):
        sub = fg[rs, cs]
        frags_removed += _remove_small_fragments(sub, min_component)
        res = _fill_interior_holes(sub, still_body[rs, cs], legacy=legacy_holes)
        holes_filled += res["filled"]
        body_holes_skipped += res["bodyHolesSkipped"]
        legacy_body_painted += res.get("_legacy_bodyPainted", 0)
        fg[rs, cs] = sub

    # --- 3. item = mask ∧ worn 픽셀 (RGB 재생성 없음) ---
    item = np.zeros((H, W, 4), dtype=np.uint8)
    item[fg] = worn[fg].astype(np.uint8)
    # 마스크가 켜졌는데 worn 이 반투명이면 불투명으로 승격 (하드 엣지 유지)
    item[fg, 3] = 255

    trimap = np.zeros((H, W), dtype=np.uint8)
    trimap[unk] = TRIMAP_UNK
    trimap[fg] = TRIMAP_FG

    return {
        "mask": fg,
        "trimap": Image.fromarray(trimap, mode="L"),
        "item": Image.fromarray(item, mode="RGBA"),
        "stats": {
            "slot": slot,
            "threshold": threshold,
            "slotRegionY": [y0, y1],
            "diffPixels": diff_px,
            "unkPixels": unk_px,
            "fgPixels": int(fg.sum()),
            "fragmentsRemoved": frags_removed,
            "holesFilled": holes_filled,
            "bodyHolesSkipped": body_holes_skipped,
            # 아직 몸인 픽셀(base·worn 둘 다 살색)을 아이템 색으로 칠한 수. 0 이어야 정상.
            "bodyOverpaintPx": legacy_body_painted,
            "legacyHoles": legacy_holes,
            "minComponent": min_component,
        },
    }
