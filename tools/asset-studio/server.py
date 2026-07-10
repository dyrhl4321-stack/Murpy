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

def api_queue() -> dict:
    """편의: 기존 review_queue 에서 worn 시트가 있는 폴더 목록."""
    items = []
    if LEGACY_QUEUE.exists():
        for d in sorted(LEGACY_QUEUE.iterdir(), reverse=True):
            src = d / "source_normalized_v2.png"
            if src.exists():
                item_id = d.name.rsplit("_", 1)[0]
                slot = ("hat" if item_id.startswith("hat") else
                        "top" if item_id.startswith("top") else
                        "bottom" if item_id.startswith("bottom") else
                        "shoes" if item_id.startswith("shoes") else
                        "hair" if item_id.startswith("hair") else "accessory")
                items.append({"itemId": item_id, "slot": slot,
                              "worn": str(src.relative_to(ROOT)).replace("\\", "/"),
                              "dir": d.name})
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


def api_validate(body: dict) -> dict:
    sdir, meta = _load_session(body["id"])
    worn = Image.open(sdir / "worn.png").convert("RGBA")
    mask = _mask_from_payload(body["mask"])
    item = _item_from_mask(worn, mask)

    # 사람이 손댄 뒤에는 몸 페인팅 여부를 다시 계산한다.
    base = Image.open(sdir / "base.png").convert("RGBA")
    still_body = T.is_skin(np.asarray(base, dtype=np.int16)) & T.is_skin(np.asarray(worn, dtype=np.int16))
    stats = dict(meta["stats"])
    stats["bodyOverpaintPx"] = int((mask & still_body).sum())
    return V.validate(item, stats)


def api_export(body: dict) -> dict:
    sdir, meta = _load_session(body["id"])
    worn = Image.open(sdir / "worn.png").convert("RGBA")
    base = Image.open(sdir / "base.png").convert("RGBA")
    mask = _mask_from_payload(body["mask"])
    item = _item_from_mask(worn, mask)

    still_body = T.is_skin(np.asarray(base, dtype=np.int16)) & T.is_skin(np.asarray(worn, dtype=np.int16))
    stats = dict(meta["stats"])
    stats["bodyOverpaintPx"] = int((mask & still_body).sum())
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
