/* Murpy Asset Studio v0.1 — 마스크 편집기
 *
 * 편집 상태는 마스크(Uint8Array) 하나뿐이다. 아이템 RGB 는 항상 worn 에서 읽는다.
 * 색을 새로 만들지 않으므로 "재드로잉 금지" 원칙이 코드로 강제된다.
 */
const $ = (s) => document.querySelector(s);
const FRAME = { w: 282, h: 448, cols: 3, rows: 4 };
const DIRS = ["down", "up", "left", "right"];
const NAMES = ["idle", "walk1", "walk2"];

const S = {
  id: null, slot: null, itemId: null,
  W: 0, H: 0,
  base: null, worn: null, trimap: null, diff: null,   // ImageData
  mask: null, maskAuto: null,                          // Uint8Array (0/1)
  frame: 0,                                            // 0..11
  tool: "brush", brush: 2, zoom: 2,                    // brush 단위 = 블록
  tol: 24,                                             // 마술봉 색 허용오차 (|Δrgb| 합)
  rect: null,                                          // 드래그 중인 사각 선택
  view: "composite", showUnk: true, showMask: false, beforeAfter: false,
  undo: [], redo: [], stroke: null,
  edits: [], startedAt: null,
  painting: false,
};

const canvas = $("#canvas");
const ctx = canvas.getContext("2d", { willReadFrequently: true });
ctx.imageSmoothingEnabled = false;

/* ---------------------------------------------------------------- utils */

function toast(msg, bad) {
  const el = document.createElement("div");
  el.className = "toast" + (bad ? " bad" : "");
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), bad ? 6000 : 2600);
}

async function loadImageData(url) {
  const img = new Image();
  img.src = url;
  await img.decode();
  const c = document.createElement("canvas");
  c.width = img.width; c.height = img.height;
  const cx = c.getContext("2d", { willReadFrequently: true });
  cx.imageSmoothingEnabled = false;
  cx.drawImage(img, 0, 0);
  return cx.getImageData(0, 0, img.width, img.height);
}

const frameOrigin = (f) => ({ x: (f % FRAME.cols) * FRAME.w, y: Math.floor(f / FRAME.cols) * FRAME.h });
const frameLabel = (f) => `${DIRS[Math.floor(f / FRAME.cols)]}·${NAMES[f % FRAME.cols]}`;

/* 시트 2×2 블록 = 배포본(423×896)의 1픽셀.
 * 블록보다 잘게 찍은 획은 축소되며 사라지거나 반투명 잡티로 남는다.
 * 그래서 모든 편집은 블록 격자에 스냅한다. */
const BLOCK = 2;
const snap = (v) => Math.floor(v / BLOCK) * BLOCK;

/* ---------------------------------------------------------------- render */

/** 프레임 하나를 ImageData 로 합성한다. */
function renderFrame(f, mask, opts = {}) {
  const { x: ox, y: oy } = frameOrigin(f);
  const out = ctx.createImageData(FRAME.w, FRAME.h);
  const view = opts.view ?? S.view;

  for (let y = 0; y < FRAME.h; y++) {
    for (let x = 0; x < FRAME.w; x++) {
      const gi = ((oy + y) * S.W + (ox + x)) * 4;
      const li = (y * FRAME.w + x) * 4;
      const on = mask[(oy + y) * S.W + (ox + x)];

      let src = null, alpha = 0;
      if (view === "base") { src = S.base; alpha = S.base.data[gi + 3]; }
      else if (view === "worn") { src = S.worn; alpha = S.worn.data[gi + 3]; }
      else if (view === "diff") { src = S.worn; alpha = S.worn.data[gi + 3]; }
      else if (view === "item") { if (on) { src = S.worn; alpha = 255; } }
      else { // composite: base 위에 item
        if (on) { src = S.worn; alpha = 255; }
        else { src = S.base; alpha = S.base.data[gi + 3]; }
      }

      if (src) {
        out.data[li] = src.data[gi];
        out.data[li + 1] = src.data[gi + 1];
        out.data[li + 2] = src.data[gi + 2];
        out.data[li + 3] = alpha;
      }

      if (view === "diff" && S.diff.data[gi + 3] > 0) {
        out.data[li] = 255; out.data[li + 1] = 60; out.data[li + 2] = 60; out.data[li + 3] = 235;
      }

      // UNK 오버레이: trimap == 128 이고 아직 마스크에 안 들어간 곳
      if (opts.unk ?? S.showUnk) {
        const t = S.trimap.data[gi];
        if (t > 60 && t < 200 && !on) {
          out.data[li] = 255; out.data[li + 1] = 154; out.data[li + 2] = 60; out.data[li + 3] = 220;
        }
      }
    }
  }

  if (opts.maskEdge ?? S.showMask) {
    for (let y = 1; y < FRAME.h - 1; y++) {
      for (let x = 1; x < FRAME.w - 1; x++) {
        const i = (oy + y) * S.W + (ox + x);
        if (!mask[i]) continue;
        const edge = !mask[i - 1] || !mask[i + 1] || !mask[i - S.W] || !mask[i + S.W];
        if (edge) {
          const li = (y * FRAME.w + x) * 4;
          out.data[li] = 61; out.data[li + 1] = 126; out.data[li + 2] = 255; out.data[li + 3] = 255;
        }
      }
    }
  }
  return out;
}

function draw() {
  if (!S.mask) return;
  const mask = S.beforeAfter ? S.maskAuto : S.mask;
  const img = renderFrame(S.frame, mask);
  const off = document.createElement("canvas");
  off.width = FRAME.w; off.height = FRAME.h;
  off.getContext("2d").putImageData(img, 0, 0);

  canvas.width = FRAME.w * S.zoom;
  canvas.height = FRAME.h * S.zoom;
  ctx.imageSmoothingEnabled = false;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(off, 0, 0, canvas.width, canvas.height);
  drawRectOverlay();
}

function drawThumbs() {
  const host = $("#thumbs");
  host.innerHTML = "";
  for (let f = 0; f < FRAME.cols * FRAME.rows; f++) {
    const b = document.createElement("button");
    b.className = "thumb" + (f === S.frame ? " active" : "");
    b.title = frameLabel(f);
    const c = document.createElement("canvas");
    c.width = FRAME.w; c.height = FRAME.h;
    c.getContext("2d").putImageData(renderFrame(f, S.mask, { view: "composite", unk: false, maskEdge: false }), 0, 0);
    const tag = document.createElement("span");
    tag.textContent = frameLabel(f);
    b.append(c, tag);
    b.onclick = () => { S.frame = f; draw(); drawThumbs(); };
    host.appendChild(b);
  }
}

/* ---------------------------------------------------------------- editing */

function beginStroke() {
  S.stroke = new Map();   // index -> 이전 값
  S.redo.length = 0;
  if (!S.startedAt) { S.startedAt = Date.now(); tickTimer(); }
}

function setPixel(i, v) {
  if (S.mask[i] === v) return;
  if (!S.stroke.has(i)) S.stroke.set(i, S.mask[i]);
  S.mask[i] = v;
}

function endStroke(op) {
  if (!S.stroke || S.stroke.size === 0) { S.stroke = null; return; }
  S.undo.push({ op, changes: S.stroke });
  if (S.undo.length > 80) S.undo.shift();
  S.edits.push({ op, frame: frameLabel(S.frame), pixels: S.stroke.size, ts: new Date().toISOString() });
  S.stroke = null;
  drawThumbs();
}

function undo() {
  const e = S.undo.pop();
  if (!e) return;
  const redoChanges = new Map();
  for (const [i, prev] of e.changes) { redoChanges.set(i, S.mask[i]); S.mask[i] = prev; }
  S.redo.push({ op: e.op, changes: redoChanges });
  draw(); drawThumbs();
}

function redo() {
  const e = S.redo.pop();
  if (!e) return;
  const undoChanges = new Map();
  for (const [i, prev] of e.changes) { undoChanges.set(i, S.mask[i]); S.mask[i] = prev; }
  S.undo.push({ op: e.op, changes: undoChanges });
  draw(); drawThumbs();
}

/** 캔버스 좌표 → 시트 전역 인덱스 */
function hit(ev) {
  const r = canvas.getBoundingClientRect();
  const px = Math.floor((ev.clientX - r.left) / S.zoom);
  const py = Math.floor((ev.clientY - r.top) / S.zoom);
  if (px < 0 || py < 0 || px >= FRAME.w || py >= FRAME.h) return null;
  const { x: ox, y: oy } = frameOrigin(S.frame);
  return { x: ox + px, y: oy + py, lx: px, ly: py };
}

/** 프레임 로컬 좌표 (lx,ly) 를 마스크에 쓴다. add=true 면 채우기. */
function put(lx, ly, add) {
  if (lx < 0 || ly < 0 || lx >= FRAME.w || ly >= FRAME.h) return;
  const { x: ox, y: oy } = frameOrigin(S.frame);
  const i = (oy + ly) * S.W + (ox + lx);
  // 채우기는 worn 이 불투명한 곳에서만 복원한다 (없는 픽셀을 만들지 않는다)
  if (add && S.worn.data[i * 4 + 3] <= 60) return;
  setPixel(i, add ? 1 : 0);
}

/** 격자에 스냅한 정사각 브러시. 크기 단위는 블록(1블록 = 2×2 px). */
function paint(p) {
  const add = S.tool === "brush";
  const side = Math.max(1, S.brush) * BLOCK;
  const x0 = snap(p.lx - Math.floor(side / 2));
  const y0 = snap(p.ly - Math.floor(side / 2));
  for (let y = y0; y < y0 + side; y++)
    for (let x = x0; x < x0 + side; x++) put(x, y, add);
}

/** 사각 선택 영역을 블록 격자로 정렬해 채우거나 지운다. */
function applyRect(add) {
  if (!S.rect) return;
  const { x0, y0, x1, y1 } = S.rect;
  const ax = snap(Math.min(x0, x1)), ay = snap(Math.min(y0, y1));
  const bx = snap(Math.max(x0, x1)) + BLOCK, by = snap(Math.max(y0, y1)) + BLOCK;
  for (let y = ay; y < by; y++)
    for (let x = ax; x < bx; x++) put(x, y, add);
}

const rgbAt = (i) => [S.worn.data[i * 4], S.worn.data[i * 4 + 1], S.worn.data[i * 4 + 2]];

/** 마술봉: 클릭한 지점과 worn 색이 비슷하게 이어진 영역을 통째로 넣거나 뺀다.
 *
 * worn 의 고유색이 9만 개라 완전 일치 플러드필은 작동하지 않는다. 허용오차가 필수다.
 * 투명한 구멍을 클릭하면 그 구멍 전체가 선택된다 (알파도 비교 대상).
 */
function wand(p, add) {
  const { x: ox, y: oy } = frameOrigin(S.frame);
  const i0 = (oy + p.ly) * S.W + (ox + p.lx);
  const seed = rgbAt(i0);
  const seedA = S.worn.data[i0 * 4 + 3];
  const tol = S.tol;
  const seen = new Uint8Array(FRAME.w * FRAME.h);
  const stack = [[p.lx, p.ly]];
  seen[p.ly * FRAME.w + p.lx] = 1;
  let n = 0;
  while (stack.length) {
    const [lx, ly] = stack.pop();
    put(lx, ly, add);
    n++;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = lx + dx, ny = ly + dy;
      if (nx < 0 || ny < 0 || nx >= FRAME.w || ny >= FRAME.h) continue;
      const li = ny * FRAME.w + nx;
      if (seen[li]) continue;
      const gi = (oy + ny) * S.W + (ox + nx);
      const a = S.worn.data[gi * 4 + 3];
      if ((seedA > 60) !== (a > 60)) continue;          // 불투명/투명 경계는 넘지 않는다
      const [r, g, b] = rgbAt(gi);
      if (Math.abs(r - seed[0]) + Math.abs(g - seed[1]) + Math.abs(b - seed[2]) > tol) continue;
      seen[li] = 1;
      stack.push([nx, ny]);
    }
  }
  return n;
}

/** 현재 프레임의 내부 구멍(가장자리에서 못 닿는 투명 영역)을 전부 채운다. */
function fillHoles() {
  const { x: ox, y: oy } = frameOrigin(S.frame);
  const at = (lx, ly) => S.mask[(oy + ly) * S.W + (ox + lx)];
  const outside = new Uint8Array(FRAME.w * FRAME.h);
  const stack = [];
  for (let x = 0; x < FRAME.w; x++) { stack.push([x, 0], [x, FRAME.h - 1]); }
  for (let y = 0; y < FRAME.h; y++) { stack.push([0, y], [FRAME.w - 1, y]); }
  while (stack.length) {
    const [lx, ly] = stack.pop();
    if (lx < 0 || ly < 0 || lx >= FRAME.w || ly >= FRAME.h) continue;
    const li = ly * FRAME.w + lx;
    if (outside[li] || at(lx, ly)) continue;
    outside[li] = 1;
    stack.push([lx + 1, ly], [lx - 1, ly], [lx, ly + 1], [lx, ly - 1]);
  }
  let n = 0;
  for (let ly = 0; ly < FRAME.h; ly++)
    for (let lx = 0; lx < FRAME.w; lx++)
      if (!at(lx, ly) && !outside[ly * FRAME.w + lx]) { put(lx, ly, true); n++; }
  return n;
}

/** 클릭한 연결성분 전체를 마스크에서 제거 (떠다니는 조각, 잘못 잡힌 팔 등) */
function removeComponent(p) {
  const i0 = p.y * S.W + p.x;
  if (!S.mask[i0]) return;
  const { x: ox, y: oy } = frameOrigin(S.frame);
  const stack = [i0];
  const seen = new Set([i0]);
  while (stack.length) {
    const i = stack.pop();
    setPixel(i, 0);
    const x = i % S.W, y = (i - x) / S.W;
    for (let dy = -1; dy <= 1; dy++) {
      for (let dx = -1; dx <= 1; dx++) {
        const nx = x + dx, ny = y + dy;
        if (nx < ox || ny < oy || nx >= ox + FRAME.w || ny >= oy + FRAME.h) continue;
        const ni = ny * S.W + nx;
        if (!seen.has(ni) && S.mask[ni]) { seen.add(ni); stack.push(ni); }
      }
    }
  }
}

const RECT_TOOLS = { rectFill: true, rectErase: false };

canvas.addEventListener("pointerdown", (ev) => {
  if (!S.mask || S.beforeAfter) return;
  const p = hit(ev); if (!p) return;
  canvas.setPointerCapture(ev.pointerId);

  if (S.tool in RECT_TOOLS) {
    S.rect = { x0: p.lx, y0: p.ly, x1: p.lx, y1: p.ly };
    draw();
    return;
  }

  beginStroke();
  if (S.tool === "component") { removeComponent(p); endStroke("component"); draw(); return; }
  if (S.tool === "wandFill" || S.tool === "wandErase") {
    const n = wand(p, S.tool === "wandFill");
    endStroke(S.tool); draw();
    toast(`${n.toLocaleString()}px ${S.tool === "wandFill" ? "채움" : "지움"}`);
    return;
  }
  S.painting = true;
  paint(p); draw();
});

canvas.addEventListener("pointermove", (ev) => {
  if (S.rect) { const p = hit(ev); if (p) { S.rect.x1 = p.lx; S.rect.y1 = p.ly; draw(); } return; }
  if (!S.painting) return;
  const p = hit(ev); if (!p) return;
  paint(p); draw();
});

const stop = () => {
  if (S.rect) {
    beginStroke();
    applyRect(RECT_TOOLS[S.tool]);
    endStroke(S.tool);
    S.rect = null;
    draw();
    return;
  }
  if (S.painting) { S.painting = false; endStroke(S.tool); draw(); }
};
canvas.addEventListener("pointerup", stop);
canvas.addEventListener("pointerleave", stop);

/** 드래그 중인 사각 선택을 캔버스 위에 그린다 (블록 격자에 스냅된 실제 범위). */
function drawRectOverlay() {
  if (!S.rect) return;
  const { x0, y0, x1, y1 } = S.rect;
  const ax = snap(Math.min(x0, x1)), ay = snap(Math.min(y0, y1));
  const bx = snap(Math.max(x0, x1)) + BLOCK, by = snap(Math.max(y0, y1)) + BLOCK;
  ctx.save();
  ctx.strokeStyle = S.tool === "rectFill" ? "#3d7eff" : "#ff5b5b";
  ctx.lineWidth = 2;
  ctx.setLineDash([6, 4]);
  ctx.strokeRect(ax * S.zoom, ay * S.zoom, (bx - ax) * S.zoom, (by - ay) * S.zoom);
  ctx.restore();
}

/* ---------------------------------------------------------------- timer */

function tickTimer() {
  if (!S.startedAt) return;
  const s = Math.floor((Date.now() - S.startedAt) / 1000);
  $("#timer").textContent = `보정 시간 ${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
  setTimeout(tickTimer, 1000);
}

/* ---------------------------------------------------------------- report */

const CHECK_LABEL = {
  size_exact: "크기 846×1792",
  has_visible: "보이는 픽셀 있음",
  has_transparency: "투명 영역 있음",
  no_empty_frame: "빈 프레임 없음",
  semi_alpha_ok: "반투명 ≤ 2%",
  no_alpha_halo: "알파 유령 없음",
  no_fabricated_pixels: "없는 픽셀 안 지어냄",
  frame_area_stable: "프레임 면적 안정",
  components_ok: "연결성분 정상",
};

function showReport(rep) {
  const m = rep.metrics;
  const rows = Object.entries(rep.checks).map(([k, v]) =>
    `<div class="k"><span>${CHECK_LABEL[k] || k}</span><span class="${v ? "pass" : "fail"}">${v ? "통과" : "실패"}</span></div>`).join("");
  const mets = [
    ["반투명 비율", (m.semiAlphaRatio * 100).toFixed(2) + "%"],
    ["알파 유령", m.haloPixels],
    ["지어낸 픽셀", m.fabricatedPx],
    ["구멍 메운 살색", m.bodyMaskPx],
    ["UNK 픽셀", m.unkPixels],
    ["프레임 면적 CV", m.frameAreaCV],
    ["보이는 픽셀", m.visiblePixels.toLocaleString()],
  ].map(([k, v]) => `<div class="k"><span>${k}</span><span>${v}</span></div>`).join("");
  const attn = rep.needsHumanAttention?.length
    ? `<h3>사람이 볼 것</h3><ul>${rep.needsHumanAttention.map(a => `<li>${a.frame}: ${a.reason}</li>`).join("")}</ul>`
    : "";
  $("#report").innerHTML =
    `<div class="k"><span><b>기계 검증</b></span><span class="${rep.ok ? "pass" : "fail"}">${rep.ok ? "PASS" : "FAIL"}</span></div>` +
    rows + `<h3>지표</h3>` + mets + attn +
    `<p class="hint">기계 검증 통과 ≠ 보기 좋음. 시각 승인은 사람이.</p>`;
}

/* ---------------------------------------------------------------- api */

function maskToPngDataUrl() {
  const c = document.createElement("canvas");
  c.width = S.W; c.height = S.H;
  const cx = c.getContext("2d");
  const img = cx.createImageData(S.W, S.H);
  for (let i = 0; i < S.mask.length; i++) {
    const v = S.mask[i] ? 255 : 0;
    img.data[i * 4] = v; img.data[i * 4 + 1] = v; img.data[i * 4 + 2] = v; img.data[i * 4 + 3] = 255;
  }
  cx.putImageData(img, 0, 0);
  return c.toDataURL("image/png");
}

async function post(url, body) {
  const r = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || "요청 실패");
  return j;
}

async function doExtract() {
  const opt = $("#queue").selectedOptions[0];
  if (!opt?.dataset.worn) return;
  $("#extract").disabled = true;
  try {
    const res = await post("/api/extract", {
      worn: opt.dataset.worn, slot: $("#slot").value,
      itemId: opt.dataset.itemId, threshold: +$("#threshold").value,
    });
    S.id = res.id; S.slot = res.slot; S.itemId = res.itemId;
    S.undo = []; S.redo = []; S.edits = []; S.startedAt = null;
    $("#timer").textContent = "보정 시간 00:00";

    const u = (n) => `/api/session/${res.id}/${n}`;
    const [base, worn, trimap, diff, maskImg] = await Promise.all(
      ["base.png", "worn.png", "trimap.png", "diff.png", "mask_auto.png"].map((n) => loadImageData(u(n))));
    S.base = base; S.worn = worn; S.trimap = trimap; S.diff = diff;
    S.W = base.width; S.H = base.height;

    S.mask = new Uint8Array(S.W * S.H);
    for (let i = 0; i < S.mask.length; i++) S.mask[i] = maskImg.data[i * 4] > 127 ? 1 : 0;
    S.maskAuto = S.mask.slice();

    $("#stage").classList.add("loaded");
    S.frame = 0;
    draw(); drawThumbs(); showReport(res.validate);
    if (res.ingest.mode === "legacy_lanczos") toast("경고: worn 이 정수배가 아니라 LANCZOS 로 리사이즈됨. 알파가 뭉갤 수 있음.", true);
  } catch (e) {
    toast(e.message, true);
  } finally {
    $("#extract").disabled = false;
  }
}

async function doValidate() {
  if (!S.id) return;
  try { showReport(await post("/api/validate", { id: S.id, mask: maskToPngDataUrl() })); toast("검증 완료"); }
  catch (e) { toast(e.message, true); }
}

async function doExport() {
  if (!S.id) return;
  try {
    const secs = S.startedAt ? Math.round((Date.now() - S.startedAt) / 1000) : 0;
    const res = await post("/api/export", {
      id: S.id, mask: maskToPngDataUrl(), tHumanSeconds: secs,
      editCount: S.edits.length, edits: S.edits,
    });
    showReport(res.validate);
    toast(`내보냄 → ${res.dir}`);
  } catch (e) { toast(e.message, true); }
}

/* ---------------------------------------------------------------- wiring */

document.querySelectorAll(".tool").forEach((b) => b.onclick = () => {
  document.querySelectorAll(".tool").forEach((x) => x.classList.remove("active"));
  b.classList.add("active"); S.tool = b.dataset.tool;
});
document.querySelectorAll(".view").forEach((b) => b.onclick = () => {
  document.querySelectorAll(".view").forEach((x) => x.classList.remove("active"));
  b.classList.add("active"); S.view = b.dataset.view; draw();
});

$("#brushSize").oninput = (e) => {
  S.brush = +e.target.value;
  $("#brushSizeV").textContent = `${S.brush}블록 (${S.brush * BLOCK}px)`;
};
$("#tol").oninput = (e) => { S.tol = +e.target.value; $("#tolV").textContent = S.tol; };
$("#fillHoles").onclick = () => {
  if (!S.mask) return;
  beginStroke();
  const n = fillHoles();
  endStroke("fillHoles");
  draw();
  toast(n ? `구멍 ${n.toLocaleString()}px 채움` : "이 프레임엔 구멍이 없습니다");
};
$("#zoom").onchange = (e) => { S.zoom = +e.target.value; draw(); };
$("#showUnk").onchange = (e) => { S.showUnk = e.target.checked; draw(); };
$("#showMask").onchange = (e) => { S.showMask = e.target.checked; draw(); };
$("#beforeAfter").onmousedown = () => { S.beforeAfter = true; draw(); };
$("#beforeAfter").onmouseup = $("#beforeAfter").onmouseleave = () => { if (S.beforeAfter) { S.beforeAfter = false; draw(); } };
$("#undo").onclick = undo;
$("#redo").onclick = redo;
$("#reset").onclick = () => {
  if (!S.maskAuto) return;
  beginStroke();
  for (let i = 0; i < S.mask.length; i++) setPixel(i, S.maskAuto[i]);
  endStroke("reset"); draw();
};
$("#extract").onclick = doExtract;
$("#validate").onclick = doValidate;
$("#export").onclick = doExport;

addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.key.toLowerCase() === "z") { e.preventDefault(); undo(); return; }
  if (e.ctrlKey && e.key.toLowerCase() === "y") { e.preventDefault(); redo(); return; }
  const map = { b: "brush", e: "eraser", c: "component", r: "rectFill", t: "rectErase", w: "wandFill", q: "wandErase" };
  const t = map[e.key.toLowerCase()];
  if (t) document.querySelector(`.tool[data-tool="${t}"]`).click();
  if (e.key.toLowerCase() === "h") $("#fillHoles").click();
  if (e.key === "[") $("#brushSize").value = Math.max(1, S.brush - 1), $("#brushSize").oninput({ target: $("#brushSize") });
  if (e.key === "]") $("#brushSize").value = Math.min(12, S.brush + 1), $("#brushSize").oninput({ target: $("#brushSize") });
  if (e.key === "ArrowRight") { S.frame = (S.frame + 1) % 12; draw(); drawThumbs(); }
  if (e.key === "ArrowLeft") { S.frame = (S.frame + 11) % 12; draw(); drawThumbs(); }
});

const SEV_MARK = { 3: "■ 재추출", 2: "● 손봐야 함", 1: "· 기계가 고침", 0: "  정상" };

(async function init() {
  const q = await (await fetch("/api/queue")).json();
  const sel = $("#queue");
  sel.innerHTML = "";
  q.items.forEach((it) => {
    const o = document.createElement("option");
    o.textContent = `${SEV_MARK[it.severity]}  ${it.itemId}  —  ${it.reasons.join(", ")}  (${it.stamp})`;
    o.dataset.worn = it.worn; o.dataset.itemId = it.itemId; o.dataset.slot = it.slot;
    o.dataset.severity = it.severity;
    sel.appendChild(o);
  });
  sel.onchange = () => { const o = sel.selectedOptions[0]; if (o?.dataset.slot) $("#slot").value = o.dataset.slot; };
  sel.onchange();

  // 사람 손이 필요한 첫 아이템(구멍 있음)을 자동으로 열어준다. 찾아 헤맬 일이 없다.
  const first = q.items.find((i) => i.severity === 2);
  if (first) {
    toast(`손봐야 할 아이템 ${q.items.filter(i => i.severity === 2).length}개. ${first.itemId} 부터 엽니다.`);
    await doExtract();
  }
})();
