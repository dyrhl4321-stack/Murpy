# -*- coding: utf-8 -*-
"""
Murpy Asset Studio v0.1 — 로컬 서버.

브라우저는 로컬 파이썬을 직접 부를 수 없으므로 얇은 HTTP 서버를 둔다.
표준 라이브러리 + Pillow/numpy/scipy 만 쓴다. 외부 의존성 없음.

    python tools/asset-studio/server.py
    → http://localhost:8765

원칙
  - base 시트는 절대 쓰기 위해 열지 않는다. 읽기 전용.
  - 아이템 RGB 는 항상 worn 원본에서 복사한다. 재드로잉 없음.
    브라우저도 마스크(Uint8) 하나만 편집한다.
  - 모든 리샘플링은 정수배 NEAREST. 비정수면 에러.
"""
from __future__ import annotations

import base64
import datetime
import io
import json
import mimetypes
import re
import shutil
import sys
import traceback
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
STATIC = HERE / "static"
SESSIONS = HERE / "sessions"
EXPORTS = HERE / "review_queue"

sys.path.insert(0, str(HERE))
from engine import trimap as T  # noqa: E402
from engine import validate as V  # noqa: E402

PORT = 8787
DEFAULT_BASE = ROOT / "char" / "v2" / "body_bald.png"
LEGACY_QUEUE = ROOT / "tools" / "character-customizer" / "review_queue"


# ---------------------------------------------------------------- helpers

def _resolve(p: str) -> Path:
    path = Path(p)
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    return path


def _png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _mask_to_image(mask: np.ndarray) -> Image.Image:
    return Image.fromarray((mask.astype(np.uint8) * 255), mode="L")


def _image_to_mask(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("L")) > 127


def _diff_overlay(base: Image.Image, worn: Image.Image, slot: str, threshold: int) -> Image.Image:
    b = np.asarray(base.convert("RGBA"), dtype=np.int16)
    w = np.asarray(worn.convert("RGBA"), dtype=np.int16)
    fh = T.FRAME_H
    y0 = int(T.SLOT_REGIONS[slot][0] * fh)
    y1 = int(T.SLOT_REGIONS[slot][1] * fh)
    H, W = b.shape[:2]
    out = np.zeros((H, W, 4), dtype=np.uint8)
    for _r, _c, rs, cs in T._frames():
        band = slice(rs.start + y0, rs.start + y1)
        d = np.abs(b[band, cs] - w[band, cs]).sum(axis=2)
        m = d > threshold
        sub = out[band, cs]
        sub[m] = [255, 40, 40, 190]
        out[band, cs] = sub
    return Image.fromarray(out, mode="RGBA")


def _item_from_mask(worn: Image.Image, mask: np.ndarray) -> Image.Image:
    """마스크가 켜진 곳에 worn 의 원본 픽셀을 복사한다. RGB 를 만들어내지 않는다."""
    w = np.asarray(worn.convert("RGBA"))
    item = np.zeros_like(w)
    item[mask] = w[mask]
    item[mask, 3] = 255
    return Image.fromarray(item, mode="RGBA")


def _thumb(item: Image.Image) -> Image.Image:
    front = item.crop((0, 0, T.FRAME_W, T.FRAME_H))
    bb = front.getbbox()
    t = front.crop(bb) if bb else front
    if max(t.size) > 256:
        s = 256 / max(t.size)
        t = t.resize((round(t.width * s), round(t.height * s)), Image.NEAREST)
    return t


def _preview_4dir(base: Image.Image, item: Image.Image) -> Image.Image:
    fw, fh = T.FRAME_W, T.FRAME_H
    pad, bg = 16, (30, 34, 44, 255)
    cells = []
    for r in range(T.ROWS):
        cell = base.crop((0, r * fh, fw, r * fh + fh)).copy()
        cell.alpha_composite(item.crop((0, r * fh, fw, r * fh + fh)))
        holder = Image.new("RGBA", (fw, fh), bg)
        holder.alpha_composite(cell)
        cells.append(holder)
    w = sum(c.width for c in cells) + pad * (len(cells) + 1)
    canvas = Image.new("RGBA", (w, fh + pad * 2), bg)
    x = pad
    for c in cells:
        canvas.alpha_composite(c, (x, pad))
        x += c.width + pad
    return canvas


# ---------------------------------------------------------------- api

def _slot_of(item_id: str) -> str:
    for p in ("hat", "top", "bottom", "shoes", "hair"):
        if item_id.startswith(p):
            return p
    return "accessory"


# 렌더 z순서 (index.html 의 _CHAR_LAYER_ORDER 와 같아야 한다)
Z_ORDER = ["body", "bottom", "shoes", "top", "hair", "hat", "acc"]


def _interior_holes(alpha: np.ndarray, fw: int, fh: int) -> np.ndarray:
    """프레임마다, 가장자리에서 도달 불가능한 투명 픽셀. 옷에 뚫린 구멍이다."""
    from scipy import ndimage
    solid = alpha > 128
    out = np.zeros_like(solid)
    for r in range(alpha.shape[0] // fh):
        for c in range(alpha.shape[1] // fw):
            sl = (slice(r * fh, (r + 1) * fh), slice(c * fw, (c + 1) * fw))
            m = solid[sl]
            if not m.any():
                continue
            lab, n = ndimage.label(~m)
            if n == 0:
                continue
            border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
            border = border[border > 0]
            out[sl] = (~np.isin(lab, border)) & (~m)
    return out


def _registered_items() -> set[str]:
    """index.html 의 CHAR_ITEMS 에 실제로 등록된 아이템 id.

    char/items/ 에는 실험 중간본도 굴러다닌다. 앱이 겹쳐 그리지 않는 파일을
    '아래 깔린 옷'으로 세면 유령 비침이 잡힌다.
    """
    src = (ROOT / "index.html").read_text(encoding="utf-8", errors="replace")
    start = src.find("window.CHAR_ITEMS")
    if start < 0:
        return set()
    end = src.find("];", start)
    return set(re.findall(r"id:\s*'([^']+)'", src[start:end]))


def _lower_layer_union(slot: str, exclude: str, shape: tuple[int, int]) -> np.ndarray | None:
    """이 슬롯보다 아래에 그려지는, 앱에 등록된 아이템들의 합집합 마스크."""
    if slot not in Z_ORDER:
        return None
    below = set(Z_ORDER[:Z_ORDER.index(slot)])
    acc = None
    for item_id in sorted(_registered_items()):
        if item_id == exclude or _slot_of(item_id) not in below:
            continue
        p = ROOT / "char" / "items" / f"{item_id}.png"
        if not p.exists():
            continue
        a = np.asarray(Image.open(p).convert("RGBA"))[..., 3] > 128
        if a.shape != shape:
            continue
        acc = a if acc is None else (acc | a)
    return acc


def _shipped_problem(item_id: str) -> dict | None:
    """배포본 char/items/<id>.png 을 검사해 사람이 봐야 할 이유를 찾는다.

    반투명/halo 는 알파를 굳히면 사라지는 축소 사고이고, 사람 손이 필요한 건
    '구멍'과 '빈 프레임'이다. 그 둘을 분리해서 보고한다.
    """
    p = ROOT / "char" / "items" / f"{item_id}.png"
    if not p.exists():
        return None
    a = np.asarray(Image.open(p).convert("RGBA"))[..., 3]
    h, w = a.shape
    fw, fh = w // T.COLS, h // T.ROWS
    visible = int((a > 40).sum())
    if visible == 0:
        return {"severity": 3, "reasons": ["빈 파일"], "holes": 0}

    hole_mask = _interior_holes(a, fw, fh)
    holes = int(hole_mask.sum())

    # 구멍 자체는 정상일 수 있다 (모자 챙 밑으로 머리가 보여야 한다).
    # 진짜 버그는 그 구멍 아래에 다른 아이템이 깔려 비치는 것이다.
    lower = _lower_layer_union(_slot_of(item_id), exclude=item_id, shape=a.shape)
    leak = int((hole_mask & lower).sum()) if lower is not None else 0

    semi = int(((a > 0) & (a < 255)).sum())
    opaque = int((a == 255).sum())
    semi_ratio = semi / max(opaque + semi, 1)

    reasons = []
    severity = 0
    # 시트 2×2 블록 = 앱 1픽셀. 16px 미만이면 앱에서 4픽셀도 안 되니 사람을 부르지 않는다.
    if leak >= 16:
        reasons.append(f"구멍으로 아래 옷이 비침 {leak:,}px")
        severity = 2
    elif holes:
        reasons.append(f"구멍 {holes:,}px (아래 옷 안 비침, 정상)")
    if semi_ratio > 0.02:
        reasons.append(f"반투명 {semi_ratio * 100:.0f}% (알파 굳힘으로 자동 해결)")
        severity = max(severity, 1)
    return {"severity": severity, "reasons": reasons, "holes": holes, "leak": leak}


def api_queue() -> dict:
    """worn 시트 목록. 아이템별로 최신 것 하나만 남기고, 문제 있는 것을 위로 올린다."""
    newest: dict[str, tuple[str, Path]] = {}
    if LEGACY_QUEUE.exists():
        for d in sorted(LEGACY_QUEUE.iterdir()):
            src = d / "source_normalized_v2.png"
            if not src.exists():
                continue
            item_id = d.name.rsplit("_", 1)[0]
            stamp = d.name.rsplit("_", 1)[-1]
            if item_id not in newest or stamp > newest[item_id][0]:
                newest[item_id] = (stamp, src)

    items = []
    for item_id, (stamp, src) in newest.items():
        prob = _shipped_problem(item_id)
        items.append({
            "itemId": item_id,
            "slot": _slot_of(item_id),
            "worn": str(src.relative_to(ROOT)).replace("\\", "/"),
            "stamp": f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]} {stamp[9:11]}:{stamp[11:13]}",
            "shipped": prob is not None,
            "severity": prob["severity"] if prob else 0,
            "holes": prob["holes"] if prob else 0,
            "leak": prob.get("leak", 0) if prob else 0,
            "reasons": prob["reasons"] if prob else ["앱에 없음"],
        })

    # 심각도 높은 것 먼저, 같으면 구멍 큰 것 먼저, 그다음 최근 것 먼저
    items.sort(key=lambda i: (-i["severity"], -i["leak"], i["stamp"]))
    return {"base": str(DEFAULT_BASE.relative_to(ROOT)).replace("\\", "/"), "items": items}


def api_extract(body: dict) -> dict:
    base_path = _resolve(body.get("base") or str(DEFAULT_BASE))
    worn_path = _resolve(body["worn"])
    slot = body["slot"]
    item_id = body.get("itemId") or worn_path.parent.name
    threshold = int(body.get("threshold", T.DIFF_THRESHOLD))

    base = Image.open(base_path).convert("RGBA")          # 읽기 전용
    worn_raw = Image.open(worn_path).convert("RGBA")
    legacy_ingest = bool(body.get("legacyIngest", False))
    worn, ingest_info = T.ingest_worn(worn_raw, base.size, legacy=legacy_ingest)

    res = T.extract(base, worn, slot, threshold=threshold)
    report = V.validate(res["item"], res["stats"])

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    sid = f"{item_id}_{ts}"
    sdir = SESSIONS / sid
    sdir.mkdir(parents=True, exist_ok=True)

    base.save(sdir / "base.png")
    worn.save(sdir / "worn.png")
    res["item"].save(sdir / "item_auto.png")
    _mask_to_image(res["mask"]).save(sdir / "mask_auto.png")
    res["trimap"].save(sdir / "trimap.png")
    _diff_overlay(base, worn, slot, threshold).save(sdir / "diff.png")
    (sdir / "meta.json").write_text(json.dumps({
        "itemId": item_id, "slot": slot, "threshold": threshold,
        "base": str(base_path), "worn": str(worn_path),
        "ingest": ingest_info, "stats": res["stats"], "created": ts,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "id": sid,
        "itemId": item_id,
        "slot": slot,
        "threshold": threshold,
        "ingest": ingest_info,
        "frame": {"w": T.FRAME_W, "h": T.FRAME_H, "cols": T.COLS, "rows": T.ROWS},
        "stats": res["stats"],
        "validate": report,
    }


def _load_session(sid: str) -> tuple[Path, dict]:
    sdir = SESSIONS / sid
    if not sdir.exists():
        raise FileNotFoundError(f"session {sid} 없음")
    meta = json.loads((sdir / "meta.json").read_text(encoding="utf-8"))
    return sdir, meta


def _mask_from_payload(payload: str) -> np.ndarray:
    raw = base64.b64decode(payload.split(",", 1)[-1])
    return _image_to_mask(Image.open(io.BytesIO(raw)))


def _human_stats(meta: dict, mask: np.ndarray, worn: Image.Image, still_body: np.ndarray) -> dict:
    """사람이 손댄 마스크의 지표.

    fabricatedPx 가 진짜 위험이다 — worn 이 투명한 자리에 마스크를 켜면
    아이템에 없는 픽셀을 지어내는 것이 된다. 게이트로 잡는다.
    bodyMaskPx 는 정보 지표일 뿐이다. 구멍을 채우면 살색이 마스크에 들어가는데
    그건 올바른 수정이다 (아래 옷이 비치지 않게 막는다).
    """
    wa = np.asarray(worn)[..., 3]
    stats = dict(meta["stats"])
    stats["fabricatedPx"] = int((mask & (wa <= 60)).sum())
    stats["bodyOverpaintPx"] = int((mask & still_body).sum())
    return stats


def api_validate(body: dict) -> dict:
    sdir, meta = _load_session(body["id"])
    worn = Image.open(sdir / "worn.png").convert("RGBA")
    mask = _mask_from_payload(body["mask"])
    item = _item_from_mask(worn, mask)

    # 사람이 손댄 뒤에는 몸 페인팅 여부를 다시 계산한다.
    base = Image.open(sdir / "base.png").convert("RGBA")
    still_body = T.is_skin(np.asarray(base, dtype=np.int16)) & T.is_skin(np.asarray(worn, dtype=np.int16))
    stats = _human_stats(meta, mask, worn, still_body)
    return V.validate(item, stats)


def api_export(body: dict) -> dict:
    sdir, meta = _load_session(body["id"])
    worn = Image.open(sdir / "worn.png").convert("RGBA")
    base = Image.open(sdir / "base.png").convert("RGBA")
    mask = _mask_from_payload(body["mask"])
    item = _item_from_mask(worn, mask)

    still_body = T.is_skin(np.asarray(base, dtype=np.int16)) & T.is_skin(np.asarray(worn, dtype=np.int16))
    stats = _human_stats(meta, mask, worn, still_body)
    report = V.validate(item, stats)

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = EXPORTS / f"{meta['itemId']}_{ts}"
    out.mkdir(parents=True, exist_ok=True)

    item.save(out / "item.png")
    _mask_to_image(mask).save(out / "mask_final.png")
    shutil.copy2(sdir / "mask_auto.png", out / "mask_auto.png")
    shutil.copy2(sdir / "trimap.png", out / "trimap.png")
    shutil.copy2(sdir / "worn.png", out / "worn_ingested.png")
    _thumb(item).save(out / "thumb.png")
    _preview_4dir(base, item).save(out / "preview.png")

    (out / "validate.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "metadata.json").write_text(json.dumps({
        "itemId": meta["itemId"], "slot": meta["slot"], "threshold": meta["threshold"],
        "engine": "trimap-v0.1", "base": meta["base"], "worn": meta["worn"],
        "ingest": meta["ingest"], "size": list(item.size),
        "frame": {"w": T.FRAME_W, "h": T.FRAME_H, "cols": T.COLS, "rows": T.ROWS},
        "autoStats": meta["stats"], "finalStats": stats,
        "tHumanSeconds": body.get("tHumanSeconds"),
        "editCount": body.get("editCount"),
        "exported": ts,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    edits = body.get("edits") or []
    if edits:
        with (out / "edits.jsonl").open("w", encoding="utf-8") as f:
            for e in edits:
                f.write(json.dumps(e, ensure_ascii=False) + "\n")

    (out / "status.json").write_text(json.dumps({
        "approved": bool(report["ok"]),
        "tHumanSeconds": body.get("tHumanSeconds"),
        "note": "기계 검증만 통과. 시각 승인은 사람이 별도로.",
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"dir": str(out), "validate": report}


ROUTES = {
    "/api/queue": lambda body: api_queue(),
    "/api/extract": api_extract,
    "/api/validate": api_validate,
    "/api/export": api_export,
}


# ---------------------------------------------------------------- http

class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # 조용히
        pass

    def _send(self, code: int, payload: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path in ("/", "/index.html"):
                self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
                return
            if path == "/favicon.ico":
                self._send(204, b"", "image/x-icon")
                return
            if path.startswith("/static/"):
                f = STATIC / path[len("/static/"):]
                if not f.is_file():
                    self._json(404, {"error": "not found"})
                    return
                ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
                self._send(200, f.read_bytes(), ctype)
                return
            if path.startswith("/api/session/"):
                _, _, _, sid, name = path.split("/", 4)
                f = SESSIONS / sid / name
                if not f.is_file():
                    self._json(404, {"error": "not found"})
                    return
                self._send(200, f.read_bytes(), "image/png")
                return
            if path == "/api/queue":
                self._json(200, api_queue())
                return
            self._json(404, {"error": "not found"})
        except Exception as exc:
            traceback.print_exc()
            self._json(500, {"error": str(exc)})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        fn = ROUTES.get(path)
        if fn is None:
            self._json(404, {"error": "not found"})
            return
        try:
            n = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(n) or b"{}")
            self._json(200, fn(body))
        except T.IngestError as exc:
            self._json(400, {"error": str(exc), "kind": "ingest"})
        except Exception as exc:
            traceback.print_exc()
            self._json(500, {"error": str(exc)})


def main() -> None:
    SESSIONS.mkdir(parents=True, exist_ok=True)
    EXPORTS.mkdir(parents=True, exist_ok=True)
    url = f"http://localhost:{PORT}"
    print(f"Murpy Asset Studio v0.1  →  {url}")
    print(f"  base(읽기전용): {DEFAULT_BASE}")
    print(f"  세션:           {SESSIONS}")
    print(f"  내보내기:       {EXPORTS}")
    if "--no-open" not in sys.argv:
        webbrowser.open(url)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
