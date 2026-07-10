# -*- coding: utf-8 -*-
"""
Murpy World character customization automation tool.

This is the Claude/Codex-friendly companion to the browser preview tool.
It validates layer PNG files and can export composited preview/sheet files
without touching the main app.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[1]
MANIFEST = HERE / "murpy_layers.json"
OUT_DIR = HERE / "out"


def load_manifest(manifest_path: str | None = None) -> dict:
    path = resolve_path(manifest_path) if manifest_path else MANIFEST
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return (HERE / path).resolve()


def expected_size(manifest: dict) -> Tuple[int, int]:
    frame = manifest["frame"]
    return frame["width"] * frame["cols"], frame["height"] * frame["rows"]


def inspect_png(path: Path, expected: Tuple[int, int]) -> dict:
    result = {
        "path": str(path),
        "exists": path.exists(),
        "ok": False,
        "issues": [],
        "size": None,
        "visiblePixels": 0,
        "transparentPixels": 0,
    }
    if not path.exists():
        result["issues"].append("file_missing")
        return result

    try:
        image = Image.open(path).convert("RGBA")
    except Exception as exc:
        result["issues"].append(f"open_failed:{exc}")
        return result

    result["size"] = list(image.size)
    if image.size != expected:
        result["issues"].append(f"size_mismatch:{image.size[0]}x{image.size[1]}_expected_{expected[0]}x{expected[1]}")

    alpha = image.getchannel("A")
    hist = alpha.histogram()
    total = image.size[0] * image.size[1]
    visible = total - sum(hist[:9])
    transparent = sum(hist[:250])
    result["visiblePixels"] = visible
    result["transparentPixels"] = transparent

    if visible == 0:
        result["issues"].append("no_visible_pixels")
    if transparent == 0:
        result["issues"].append("no_transparency")

    result["ok"] = len(result["issues"]) == 0
    return result


def read_layers(args, manifest: dict) -> Dict[str, Path]:
    layers = {slot: resolve_path(path) for slot, path in manifest["defaults"].items()}
    for pair in args.layer or []:
        if "=" not in pair:
            raise SystemExit(f"--layer must be slot=path, got: {pair}")
        slot, value = pair.split("=", 1)
        if slot not in manifest["layerOrder"]:
            raise SystemExit(f"Unknown layer slot: {slot}")
        layers[slot] = resolve_path(value)
    if args.no_defaults:
        layers = {}
        for pair in args.layer or []:
            slot, value = pair.split("=", 1)
            layers[slot] = resolve_path(value)
    return layers


def validate_layers(layers: Dict[str, Path], manifest: dict) -> dict:
    expected = expected_size(manifest)
    report = {
        "expectedSize": list(expected),
        "layers": {},
        "ok": True,
    }
    for slot in manifest["layerOrder"]:
        path = layers.get(slot)
        if not path:
            continue
        result = inspect_png(path, expected)
        report["layers"][slot] = result
        if not result["ok"]:
            report["ok"] = False
    return report


def load_valid_image(path: Path, expected: Tuple[int, int]) -> Image.Image | None:
    result = inspect_png(path, expected)
    if not result["ok"]:
        return None
    return Image.open(path).convert("RGBA")


def compose_sheet(layers: Dict[str, Path], manifest: dict) -> Image.Image:
    expected = expected_size(manifest)
    out = Image.new("RGBA", expected, (0, 0, 0, 0))
    for slot in manifest["layerOrder"]:
        path = layers.get(slot)
        if not path:
            continue
        image = load_valid_image(path, expected)
        if image is None:
            continue
        out.alpha_composite(image)
    return out


def compose_frame(sheet: Image.Image, manifest: dict, direction: str, frame_name: str) -> Image.Image:
    frame = manifest["frame"]
    if direction not in frame["directions"]:
        raise SystemExit(f"Unknown direction: {direction}")
    if frame_name not in frame["frames"]:
        raise SystemExit(f"Unknown frame: {frame_name}")

    col = frame["frames"].index(frame_name)
    row = frame["directions"].index(direction)
    w = frame["width"]
    h = frame["height"]
    return sheet.crop((col * w, row * h, col * w + w, row * h + h))


def write_report(report: dict, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


# ===== Bald-body full-sprite DIFF extraction (v2) =====
# 슬롯별 프레임-로컬 세로 영역(프레임 높이 대비 비율). diff를 이 영역으로 제한해 몸통 노이즈 제거.
SLOT_REGIONS = {
    "hair": (0.00, 0.42),
    "hat": (0.00, 0.40),
    "top": (0.30, 0.84),
    "bottom": (0.55, 0.93),
    "shoes": (0.84, 1.00),
    "accessory": (0.00, 1.00),
}


def _is_skin(p) -> bool:
    r, g, b, a = p
    return a > 0 and r > 150 and g > 80 and b < 150 and (r - b) > 30


def _alpha_sum(image: Image.Image, box) -> int:
    return sum(px[3] for px in image.crop(box).getdata())


def normalize_worn(im: Image.Image, base_size, cols: int, rows: int):
    """비표준 착용본을 base_size로 정규화: 빈 여백만 정수격자로 crop → resize."""
    W, H = im.size
    info = {"original": [W, H]}
    if (W, H) == tuple(base_size):
        info["cropped"] = [W, H]
        info["resized_to"] = list(base_size)
        return im.copy(), info
    dw, dh = W % cols, H % rows
    left = right = top = bottom = 0
    if dw:
        # 왼/오른쪽 중 더 빈 쪽에서 crop
        if _alpha_sum(im, (0, 0, dw, H)) <= _alpha_sum(im, (W - dw, 0, W, H)):
            left = dw
        else:
            right = dw
    if dh:
        if _alpha_sum(im, (0, 0, W, dh)) <= _alpha_sum(im, (0, H - dh, W, H)):
            top = dh
        else:
            bottom = dh
    grid = im.crop((left, top, W - right, H - bottom))
    info["cropped"] = list(grid.size)
    norm = grid.resize(tuple(base_size), Image.LANCZOS)
    info["resized_to"] = list(base_size)
    return norm, info


def _fill_interior_holes(item: Image.Image, FW: int, FH: int, cols: int, rows: int) -> int:
    """옷 안쪽 투명 구멍(가장자리서 도달 불가)을 최근접 아이템색으로 채움. 다리사이 등 외부 틈은 유지."""
    from collections import deque
    px = item.load()
    filled = 0
    for r in range(rows):
        for c in range(cols):
            ox, oy = c * FW, r * FH
            opaque = [[px[ox + x, oy + y][3] > 40 for x in range(FW)] for y in range(FH)]
            ext = [[False] * FW for _ in range(FH)]
            q = deque()
            for x in range(FW):
                for yy in (0, FH - 1):
                    if not opaque[yy][x] and not ext[yy][x]:
                        ext[yy][x] = True; q.append((x, yy))
            for y in range(FH):
                for xx in (0, FW - 1):
                    if not opaque[y][xx] and not ext[y][xx]:
                        ext[y][xx] = True; q.append((xx, y))
            while q:
                x, y = q.popleft()
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < FW and 0 <= ny < FH and not opaque[ny][nx] and not ext[ny][nx]:
                        ext[ny][nx] = True; q.append((nx, ny))
            for y in range(FH):
                for x in range(FW):
                    if not opaque[y][x] and not ext[y][x]:
                        found = None
                        for rad in range(1, 8):
                            for dy in range(-rad, rad + 1):
                                for dx in range(-rad, rad + 1):
                                    nx, ny = x + dx, y + dy
                                    if 0 <= nx < FW and 0 <= ny < FH and opaque[ny][nx]:
                                        found = px[ox + nx, oy + ny]; break
                                if found:
                                    break
                            if found:
                                break
                        if found:
                            px[ox + x, oy + y] = found; filled += 1
    return filled


def _remove_small_fragments(item: Image.Image, FW: int, FH: int, cols: int, rows: int, min_size: int = 22) -> int:
    """분리된 작은 조각(diff 노이즈: 목/머리 주변 stray 픽셀, 실 조각)을 제거."""
    from collections import deque
    px = item.load()
    removed = 0
    for r in range(rows):
        for c in range(cols):
            ox, oy = c * FW, r * FH
            seen = [[False] * FW for _ in range(FH)]
            for sy in range(FH):
                for sx in range(FW):
                    if px[ox + sx, oy + sy][3] > 40 and not seen[sy][sx]:
                        q = deque([(sx, sy)]); seen[sy][sx] = True; comp = [(sx, sy)]
                        while q:
                            x, y = q.popleft()
                            for dx in (-1, 0, 1):
                                for dy in (-1, 0, 1):
                                    nx, ny = x + dx, y + dy
                                    if 0 <= nx < FW and 0 <= ny < FH and px[ox + nx, oy + ny][3] > 40 and not seen[ny][nx]:
                                        seen[ny][nx] = True; q.append((nx, ny)); comp.append((nx, ny))
                        xs = [p[0] for p in comp]; ys = [p[1] for p in comp]
                        cw = max(xs) - min(xs) + 1; ch = max(ys) - min(ys) + 1
                        thin = (cw <= 2 or ch <= 2)  # 가느다란 선(diff 스캔 노이즈)
                        if len(comp) < min_size or (thin and len(comp) < 140) or (len(comp) < 90 and cw <= 4):
                            for x, y in comp:
                                px[ox + x, oy + y] = (0, 0, 0, 0); removed += 1
    return removed


def cmd_extract_diff(args) -> None:
    import datetime
    manifest = load_manifest(getattr(args, "manifest", None) or "murpy_layers_v2.json")
    fr = manifest["frame"]
    FW, FH, cols, rows = fr["width"], fr["height"], fr["cols"], fr["rows"]
    base_size = (FW * cols, FH * rows)
    slot = args.slot
    if slot not in SLOT_REGIONS:
        raise SystemExit(f"Unknown slot: {slot}. Use one of {list(SLOT_REGIONS)}")

    base = Image.open(resolve_path(args.base)).convert("RGBA")
    if base.size != base_size:
        raise SystemExit(f"base size {base.size} != expected {base_size}")
    worn_orig = Image.open(resolve_path(args.worn)).convert("RGBA")
    worn, norm_info = normalize_worn(worn_orig, base_size, cols, rows)

    y0 = int(SLOT_REGIONS[slot][0] * FH)
    y1 = int(SLOT_REGIONS[slot][1] * FH)
    thr = args.threshold
    bp, wp = base.load(), worn.load()
    item = Image.new("RGBA", base_size, (0, 0, 0, 0))
    diffmask = Image.new("RGBA", base_size, (0, 0, 0, 0))
    ip, dp = item.load(), diffmask.load()
    for r in range(rows):
        for c in range(cols):
            ox, oy = c * FW, r * FH
            for y in range(y0, y1):
                for x in range(FW):
                    b = bp[ox + x, oy + y]
                    w = wp[ox + x, oy + y]
                    d = abs(b[0] - w[0]) + abs(b[1] - w[1]) + abs(b[2] - w[2]) + abs(b[3] - w[3])
                    if d > thr:
                        dp[ox + x, oy + y] = (255, 0, 0, 180)
                        if w[3] > 60 and not _is_skin(w):
                            ip[ox + x, oy + y] = w

    frags_removed = _remove_small_fragments(item, FW, FH, cols, rows)
    holes_filled = _fill_interior_holes(item, FW, FH, cols, rows)

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    qdir = HERE / "review_queue" / f"{args.item_id}_{ts}"
    qdir.mkdir(parents=True, exist_ok=True)
    worn_orig.save(qdir / "source_original.png")
    worn.save(qdir / "source_normalized_v2.png")
    diffmask.save(qdir / "diff_mask.png")
    item.save(qdir / "item.png")
    # thumb: 제공된 썸네일 있으면 그걸 쓰고, 없으면 아이템 앞프레임 오토크롭
    if getattr(args, "thumb", None):
        thumb = Image.open(resolve_path(args.thumb)).convert("RGBA")
        tb = thumb.split()[3].point(lambda v: 255 if v > 50 else 0).getbbox()
        if tb:
            thumb = thumb.crop(tb)
    else:
        front = item.crop((0, 0, FW, FH))
        bb = front.getbbox()
        thumb = front.crop(bb) if bb else front
    if max(thumb.size) > 256:
        s = 256 / max(thumb.size)
        thumb = thumb.resize((round(thumb.width * s), round(thumb.height * s)), Image.LANCZOS)
    thumb.save(qdir / "thumb.png")
    # body+item 4방향 미리보기
    comp = base.copy(); comp.alpha_composite(item)
    dirs = manifest["frame"]["directions"]
    cells = []
    for r, _name in enumerate(dirs):
        cell = comp.crop((0, r * FH, FW, r * FH + FH))
        bg = Image.new("RGBA", (FW, FH), (30, 34, 44, 255)); bg.alpha_composite(cell); cells.append(bg)
    pw = sum(c.width for c in cells) + 20 * (len(cells) + 1)
    canvas = Image.new("RGBA", (pw, FH + 20), (30, 34, 44, 255)); xx = 20
    for c in cells:
        canvas.alpha_composite(c, (xx, 10)); xx += c.width + 20
    canvas.save(qdir / "body_plus_item_preview_4dir.png")
    # item_only
    io_cells = []
    for r, _name in enumerate(dirs):
        cell = item.crop((0, r * FH, FW, r * FH + min(FH, 200)))
        bg = Image.new("RGBA", cell.size, (255, 0, 255, 255)); bg.alpha_composite(cell); io_cells.append(bg)
    iw = sum(c.width for c in io_cells) + 20 * (len(io_cells) + 1)
    io = Image.new("RGBA", (iw, io_cells[0].height + 20), (255, 0, 255, 255)); xx = 20
    for c in io_cells:
        io.alpha_composite(c, (xx, 10)); xx += c.width + 20
    io.save(qdir / "item_only_preview.png")
    # validate_report
    vis = sum(1 for a in item.getchannel("A").getdata() if a > 40)
    trans = sum(1 for a in item.getchannel("A").getdata() if a < 10)
    skin = sum(1 for p in item.getdata() if _is_skin(p))
    empty = []
    for r in range(rows):
        for c in range(cols):
            v = sum(1 for a in item.crop((c * FW, r * FH, c * FW + FW, r * FH + FH)).getchannel("A").getdata() if a > 40)
            if v == 0:
                empty.append(f"r{r}c{c}")
    report = {
        "itemId": args.item_id, "slot": slot, "method": "bald_body_full_sprite_diff",
        "base": str(args.base), "size": list(item.size), "sizeOK": item.size == base_size,
        "normalize": norm_info, "diffThreshold": thr, "slotRegionY": [y0, y1],
        "visiblePixels": vis, "transparentPresent": trans > 0, "skinPixels": skin,
        "skinOK": skin == 0, "emptyFrames": empty, "holesFilled": holes_filled,
        "ok": item.size == base_size and vis > 0 and trans > 0 and skin == 0 and not empty,
    }
    write_report(report, qdir / "validate_report.json")
    (qdir / "request.md").write_text(
        f"# DIFF 추출 검수 요청 — {args.item_id} ({slot})\n\n"
        f"- 방식: Bald-body full-sprite diff (base={args.base})\n"
        f"- 원본 크기: {norm_info['original']} → crop {norm_info.get('cropped')} → v2 {norm_info['resized_to']}\n"
        f"- diff threshold: {thr}, slot 영역 y: {y0}-{y1}\n"
        f"- visible {vis}px / skin {skin} / empty {empty}\n"
        f"- row3/right: 원본 착용본 그대로(반전 안 함)\n\n"
        f"**아직 앱 등록 안 함.** Codex codex_review.md 판정 대기.\n",
        encoding="utf-8",
    )
    print(f"QUEUE: {qdir}")
    print(f"ok={report['ok']} vis={vis} skin={skin} empty={empty}")


def cmd_validate(args) -> None:
    manifest = load_manifest(getattr(args, "manifest", None))
    layers = read_layers(args, manifest)
    report = validate_layers(layers, manifest)
    output = Path(args.output) if args.output else OUT_DIR / "validation-report.json"
    write_report(report, output)
    print(f"saved {output}")
    print("OK" if report["ok"] else "FAILED")


def cmd_compose(args) -> None:
    manifest = load_manifest(getattr(args, "manifest", None))
    layers = read_layers(args, manifest)
    report = validate_layers(layers, manifest)
    output = Path(args.output) if args.output else OUT_DIR / "composited-sheet.png"
    report_output = OUT_DIR / "validation-report.json"

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sheet = compose_sheet(layers, manifest)
    sheet.save(output)
    write_report(report, report_output)
    print(f"saved {output}")
    print(f"saved {report_output}")
    print("OK" if report["ok"] else "COMPOSED_WITH_INVALID_LAYERS_SKIPPED")


def cmd_preview(args) -> None:
    manifest = load_manifest(getattr(args, "manifest", None))
    layers = read_layers(args, manifest)
    sheet = compose_sheet(layers, manifest)
    frame = compose_frame(sheet, manifest, args.direction, args.frame)
    output = Path(args.output) if args.output else OUT_DIR / f"preview-{args.direction}-{args.frame}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.save(output)
    print(f"saved {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Murpy World customization automation tool")
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p):
        p.add_argument("--layer", action="append", help="Override a layer. Example: --layer hair=C:\\path\\hair.png")
        p.add_argument("--no-defaults", action="store_true", help="Use only explicitly provided --layer values")
        p.add_argument("--manifest", help="Manifest JSON to use (default legacy murpy_layers.json). Use murpy_layers_v2.json for the 846x1792 v2 standard.")

    p_validate = sub.add_parser("validate", help="Validate layer PNG files")
    common(p_validate)
    p_validate.add_argument("--output", help="Report JSON output path")
    p_validate.set_defaults(func=cmd_validate)

    p_compose = sub.add_parser("compose", help="Export a full composited sprite sheet")
    common(p_compose)
    p_compose.add_argument("--output", help="PNG output path")
    p_compose.set_defaults(func=cmd_compose)

    p_preview = sub.add_parser("preview", help="Export one composited frame")
    common(p_preview)
    p_preview.add_argument("--direction", default="down", choices=["down", "up", "left", "right"])
    p_preview.add_argument("--frame", default="idle", choices=["idle", "walk1", "walk2"])
    p_preview.add_argument("--output", help="PNG output path")
    p_preview.set_defaults(func=cmd_preview)

    p_diff = sub.add_parser("extract-diff", help="Bald-body full-sprite diff → item layer + review queue")
    p_diff.add_argument("--base", default="../../char/v2/body_bald.png", help="기준 body_bald 시트")
    p_diff.add_argument("--worn", required=True, help="착용 완료 full sprite (body_bald img2img)")
    p_diff.add_argument("--slot", required=True, choices=list(SLOT_REGIONS), help="아이템 슬롯")
    p_diff.add_argument("--item-id", required=True, dest="item_id", help="아이템 id (큐 폴더명)")
    p_diff.add_argument("--threshold", type=int, default=85, help="diff 임계(픽셀 채널합)")
    p_diff.add_argument("--thumb", help="제공 썸네일 PNG (없으면 아이템에서 자동 생성)")
    p_diff.add_argument("--manifest", default="murpy_layers_v2.json", help="프레임 규격 매니페스트")
    p_diff.set_defaults(func=cmd_extract_diff)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
