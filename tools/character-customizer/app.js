const FRAME = { width: 141, height: 224, cols: 3, rows: 4 };
const DIRECTIONS = { down: 0, up: 1, left: 2, right: 3 };
const FRAME_NAMES = ["idle", "walk1", "walk2"];

const LAYERS = [
  { id: "body", label: "Body", hint: "기본 몸", path: "../../char/walk.png", required: true },
  { id: "bottom", label: "Bottom", hint: "하의", path: "../../char/items/bottom_bermuda.png" },
  { id: "shoes", label: "Shoes", hint: "신발", path: "../../char/items/shoes_black.png" },
  { id: "top", label: "Top", hint: "상의", path: "../../char/items/top_jersey.png" },
  { id: "hair", label: "Hair", hint: "헤어", path: "../../char/items/hair_default_extracted.png" },
  { id: "hat", label: "Hat", hint: "모자", path: "../../char/items/hat_ladodgers.png" },
  { id: "accessory", label: "Accessory", hint: "악세사리", path: "../../char/items/acc_airpodsmax.png" },
];

const state = {
  direction: "down",
  frame: 0,
  zoom: 2.5,
  layers: new Map(),
};

const canvas = document.querySelector("#previewCanvas");
const ctx = canvas.getContext("2d", { willReadFrequently: true });
ctx.imageSmoothingEnabled = false;

const stage = document.querySelector("#stage");
const guide = document.querySelector("#guide");
const layerList = document.querySelector("#layerList");
const reportList = document.querySelector("#reportList");
const frameLabel = document.querySelector("#frameLabel");
const currentStateText = document.querySelector("#currentStateText");

function makeLayerState(layer) {
  return {
    ...layer,
    image: null,
    fileName: "",
    objectUrl: "",
    enabled: true,
    valid: false,
    dx: 0,
    dy: 0,
    status: "비어 있음",
    statusKind: layer.required ? "bad" : "warn",
  };
}

function init() {
  LAYERS.forEach((layer) => state.layers.set(layer.id, makeLayerState(layer)));
  renderLayerControls();
  bindControls();
  updateZoom();
  draw();
  validateAll();
}

function bindControls() {
  document.querySelector("#loadDefaultsBtn").addEventListener("click", loadDefaultAssets);
  document.querySelector("#exportFrameBtn").addEventListener("click", exportCurrentFrame);
  document.querySelector("#exportSheetBtn").addEventListener("click", exportFullSheet);
  document.querySelector("#validateAllBtn").addEventListener("click", validateAll);
  document.querySelector("#clearNudgeBtn").addEventListener("click", clearNudges);
  document.querySelector("#zoomRange").addEventListener("input", (event) => {
    state.zoom = Number(event.target.value);
    updateZoom();
  });
  document.querySelector("#checkerToggle").addEventListener("change", (event) => {
    stage.classList.toggle("checker", event.target.checked);
  });
  document.querySelector("#guideToggle").addEventListener("change", (event) => {
    guide.hidden = !event.target.checked;
  });

  document.querySelector("#directionTabs").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-dir]");
    if (!button) return;
    state.direction = button.dataset.dir;
    setActive("#directionTabs", button);
    draw();
  });

  document.querySelector("#frameTabs").addEventListener("click", (event) => {
    const button = event.target.closest("button[data-frame]");
    if (!button) return;
    state.frame = Number(button.dataset.frame);
    setActive("#frameTabs", button);
    draw();
  });
}

function renderLayerControls() {
  layerList.innerHTML = "";
  for (const layer of state.layers.values()) {
    const card = document.createElement("article");
    card.className = "layer-card";
    card.innerHTML = `
      <div class="layer-title">
        <div>
          <strong>${layer.label}</strong>
          <span>${layer.hint}</span>
        </div>
        <label class="checkbox">
          <input type="checkbox" data-field="enabled" data-layer="${layer.id}" ${layer.enabled ? "checked" : ""}>
          보기
        </label>
      </div>
      <div class="layer-row">
        <input class="file-input" type="file" accept="image/png,image/webp,image/jpeg" data-field="file" data-layer="${layer.id}">
        <button type="button" data-field="clear" data-layer="${layer.id}">비우기</button>
      </div>
      <div class="layer-row nudge">
        <input type="number" step="1" data-field="dx" data-layer="${layer.id}" value="${layer.dx}" aria-label="${layer.label} X 보정">
        <input type="number" step="1" data-field="dy" data-layer="${layer.id}" value="${layer.dy}" aria-label="${layer.label} Y 보정">
        <button type="button" data-field="reset" data-layer="${layer.id}">0</button>
      </div>
      <p id="status-${layer.id}" class="status ${layer.statusKind}">${layer.status}</p>
    `;
    layerList.appendChild(card);
  }

  layerList.addEventListener("change", onLayerControlChange);
  layerList.addEventListener("click", onLayerControlClick);
}

async function onLayerControlChange(event) {
  const target = event.target;
  const layer = state.layers.get(target.dataset.layer);
  if (!layer) return;

  if (target.dataset.field === "enabled") {
    layer.enabled = target.checked;
    draw();
  }

  if (target.dataset.field === "file" && target.files?.[0]) {
    await loadLayerFile(layer, target.files[0]);
  }

  if (target.dataset.field === "dx" || target.dataset.field === "dy") {
    layer[target.dataset.field] = Number(target.value) || 0;
    draw();
  }
}

function onLayerControlClick(event) {
  const target = event.target.closest("button[data-field]");
  if (!target) return;
  const layer = state.layers.get(target.dataset.layer);
  if (!layer) return;

  if (target.dataset.field === "clear") {
    clearLayer(layer);
  }

  if (target.dataset.field === "reset") {
    layer.dx = 0;
    layer.dy = 0;
    syncLayerInputs(layer);
    draw();
  }
}

function setActive(parentSelector, activeButton) {
  document.querySelectorAll(`${parentSelector} button`).forEach((button) => {
    button.classList.toggle("active", button === activeButton);
  });
}

function updateZoom() {
  stage.style.setProperty("--zoom", state.zoom);
}

async function loadDefaultAssets() {
  for (const layer of state.layers.values()) {
    if (!layer.path) continue;
    try {
      await loadLayerUrl(layer, layer.path, layer.path.split("/").pop());
    } catch {
      layer.status = "기본 파일을 불러오지 못함";
      layer.statusKind = layer.required ? "bad" : "warn";
      updateLayerStatus(layer);
    }
  }
  validateAll();
  draw();
}

function loadLayerFile(layer, file) {
  if (layer.objectUrl) URL.revokeObjectURL(layer.objectUrl);
  layer.objectUrl = URL.createObjectURL(file);
  return loadLayerUrl(layer, layer.objectUrl, file.name);
}

function loadLayerUrl(layer, url, fileName) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      layer.image = img;
      layer.fileName = fileName;
      validateLayer(layer);
      updateLayerStatus(layer);
      draw();
      resolve();
    };
    img.onerror = reject;
    img.src = url;
  });
}

function clearLayer(layer) {
  if (layer.objectUrl) URL.revokeObjectURL(layer.objectUrl);
  layer.image = null;
  layer.fileName = "";
  layer.objectUrl = "";
  layer.status = layer.required ? "필수 레이어가 비어 있음" : "비어 있음";
  layer.statusKind = layer.required ? "bad" : "warn";
  updateLayerStatus(layer);
  draw();
}

function validateAll() {
  for (const layer of state.layers.values()) {
    validateLayer(layer);
    updateLayerStatus(layer);
  }
  updateReport();
}

function validateLayer(layer) {
  if (!layer.image) {
    layer.status = layer.required ? "필수 레이어가 비어 있음" : "비어 있음";
    layer.statusKind = layer.required ? "bad" : "warn";
    layer.valid = false;
    return;
  }

  const expectedW = FRAME.width * FRAME.cols;
  const expectedH = FRAME.height * FRAME.rows;
  const problems = [];
  if (layer.image.naturalWidth !== expectedW || layer.image.naturalHeight !== expectedH) {
    problems.push(`크기 ${layer.image.naturalWidth}x${layer.image.naturalHeight}, 기준 ${expectedW}x${expectedH}`);
  }

  const alpha = inspectAlpha(layer.image);
  if (!alpha.hasTransparent) {
    problems.push("투명 영역 없음");
  }
  if (!alpha.hasVisible) {
    problems.push("보이는 픽셀 없음");
  }

  if (problems.length) {
    layer.status = `${layer.fileName}: ${problems.join(" / ")}`;
    layer.statusKind = "bad";
    layer.valid = false;
    return;
  }

  layer.status = `${layer.fileName}: 통과`;
  layer.statusKind = "good";
  layer.valid = true;
}

function inspectAlpha(img) {
  const temp = document.createElement("canvas");
  temp.width = img.naturalWidth;
  temp.height = img.naturalHeight;
  const tempCtx = temp.getContext("2d", { willReadFrequently: true });
  tempCtx.imageSmoothingEnabled = false;
  tempCtx.drawImage(img, 0, 0);
  const data = tempCtx.getImageData(0, 0, temp.width, temp.height).data;
  let hasTransparent = false;
  let hasVisible = false;
  for (let i = 3; i < data.length; i += 4) {
    if (data[i] < 250) hasTransparent = true;
    if (data[i] > 8) hasVisible = true;
    if (hasTransparent && hasVisible) break;
  }
  return { hasTransparent, hasVisible };
}

function updateLayerStatus(layer) {
  const el = document.querySelector(`#status-${layer.id}`);
  if (!el) return;
  el.className = `status ${layer.statusKind}`;
  el.textContent = layer.status;
  updateReport();
}

function updateReport() {
  const items = [];
  for (const layer of state.layers.values()) {
    if (layer.statusKind === "bad") items.push({ kind: "bad", text: `${layer.label}: ${layer.status}` });
    if (layer.statusKind === "warn") items.push({ kind: "warn", text: `${layer.label}: ${layer.status}` });
  }
  if (!items.length) items.push({ kind: "good", text: "현재 올라온 레이어는 기본 검사를 통과했다." });

  reportList.innerHTML = "";
  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = item.kind;
    li.textContent = item.text;
    reportList.appendChild(li);
  });
}

function syncLayerInputs(layer) {
  document.querySelectorAll(`[data-layer="${layer.id}"][data-field="dx"]`).forEach((input) => {
    input.value = layer.dx;
  });
  document.querySelectorAll(`[data-layer="${layer.id}"][data-field="dy"]`).forEach((input) => {
    input.value = layer.dy;
  });
}

function clearNudges() {
  for (const layer of state.layers.values()) {
    layer.dx = 0;
    layer.dy = 0;
    syncLayerInputs(layer);
  }
  draw();
}

function draw(targetCtx = ctx, direction = state.direction, frame = state.frame, clear = true) {
  targetCtx.imageSmoothingEnabled = false;
  if (clear) targetCtx.clearRect(0, 0, FRAME.width, FRAME.height);

  const row = DIRECTIONS[direction];
  const sx = frame * FRAME.width;
  const sy = row * FRAME.height;

  for (const layer of state.layers.values()) {
    if (!layer.enabled || !layer.image || !layer.valid) continue;
    targetCtx.drawImage(
      layer.image,
      sx,
      sy,
      FRAME.width,
      FRAME.height,
      layer.dx,
      layer.dy,
      FRAME.width,
      FRAME.height
    );
  }

  frameLabel.textContent = `${direction} / ${FRAME_NAMES[frame]}`;
  const dirKo = { down: "정면", up: "뒤", left: "좌", right: "우" }[direction];
  const frameKo = ["기본", "걷기 1", "걷기 2"][frame];
  currentStateText.textContent = `${dirKo} ${frameKo} 프레임을 보고 있다.`;
}

function exportCurrentFrame() {
  draw();
  downloadCanvas(canvas, `murpy-frame-${state.direction}-${FRAME_NAMES[state.frame]}.png`);
}

function exportFullSheet() {
  const sheet = document.createElement("canvas");
  sheet.width = FRAME.width * FRAME.cols;
  sheet.height = FRAME.height * FRAME.rows;
  const sheetCtx = sheet.getContext("2d");
  sheetCtx.imageSmoothingEnabled = false;

  const dirs = ["down", "up", "left", "right"];
  dirs.forEach((dir, row) => {
    for (let frame = 0; frame < FRAME.cols; frame += 1) {
      const cell = document.createElement("canvas");
      cell.width = FRAME.width;
      cell.height = FRAME.height;
      const cellCtx = cell.getContext("2d");
      draw(cellCtx, dir, frame, true);
      sheetCtx.drawImage(cell, frame * FRAME.width, row * FRAME.height);
    }
  });

  downloadCanvas(sheet, "murpy-composited-sheet.png");
}

function downloadCanvas(sourceCanvas, filename) {
  const link = document.createElement("a");
  link.download = filename;
  link.href = sourceCanvas.toDataURL("image/png");
  link.click();
}

init();
