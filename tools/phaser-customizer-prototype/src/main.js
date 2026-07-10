import Phaser from 'phaser';
import {
  FRAME_W, FRAME_H, COLS, ROWS, DIRS, STEPS,
  LAYER_ORDER, V2_ASSETS, frameIndex,
} from './assets.js';

const state = {
  dirIndex: 0,   // 0 down, 1 up, 2 left, 3 right
  stepIndex: 0,  // 0 idle, 1 walk1, 2 walk2
  zoom: 2,
  visible: {},   // slot -> bool
  selected: {},  // slot -> asset id currently shown (first available by default)
};

// 기본 선택: body/hair/top만 에셋이 있으므로 그것만 켠다. 나머지는 에셋 없음.
LAYER_ORDER.forEach(slot => {
  const list = V2_ASSETS[slot];
  if (list && list.length) {
    state.selected[slot] = list[0].id;
    state.visible[slot] = true;
  } else {
    state.selected[slot] = null;
    state.visible[slot] = false;
  }
});

let scene, playerContainer;
const layerSprites = {}; // slot -> Phaser.Sprite (only created for slots with an asset loaded)

class MainScene extends Phaser.Scene {
  preload() {
    LAYER_ORDER.forEach(slot => {
      (V2_ASSETS[slot] || []).forEach(asset => {
        this.load.spritesheet(asset.id, asset.path + '?v=' + Date.now(), {
          frameWidth: FRAME_W,
          frameHeight: FRAME_H,
        });
      });
    });
  }

  create() {
    scene = this;
    this.cameras.main.setBackgroundColor('rgba(0,0,0,0)');

    playerContainer = this.add.container(this.scale.width / 2, this.scale.height / 2);

    // 요구사항: 모든 레이어 Sprite는 같은 x/y 기준점(0,0, origin 0.5/0.5)에 배치.
    // 같은 frame crop 영역(282x448)을 그대로 쓰므로 별도 offset 계산이 필요 없다.
    LAYER_ORDER.forEach(slot => {
      const assetId = state.selected[slot];
      if (!assetId) return; // 에셋 없는 슬롯은 스프라이트 자체를 만들지 않음
      const spr = this.add.sprite(0, 0, assetId, 0);
      spr.setOrigin(0.5, 0.5);
      spr.setVisible(!!state.visible[slot]);
      playerContainer.add(spr);
      layerSprites[slot] = spr;
    });

    this.cameras.main.centerOn(this.scale.width / 2, this.scale.height / 2);
    this.cameras.main.setZoom(state.zoom);

    this.input.keyboard.on('keydown-DOWN',  () => setDirection(0));
    this.input.keyboard.on('keydown-UP',    () => setDirection(1));
    this.input.keyboard.on('keydown-LEFT',  () => setDirection(2));
    this.input.keyboard.on('keydown-RIGHT', () => setDirection(3));
    this.input.keyboard.on('keydown-SPACE', () => cycleStep());

    updateFrames();
    wireUI();
    updateDebug();
  }
}

function setDirection(i) {
  state.dirIndex = i;
  updateFrames();
  syncDirButtons();
  updateDebug();
}

function setStep(i) {
  state.stepIndex = i;
  updateFrames();
  syncStepButtons();
  updateDebug();
}

function cycleStep() {
  setStep((state.stepIndex + 1) % STEPS.length);
}

function updateFrames() {
  const f = frameIndex(state.dirIndex, state.stepIndex);
  LAYER_ORDER.forEach(slot => {
    const spr = layerSprites[slot];
    if (spr) spr.setFrame(f);
  });
}

function setLayerVisible(slot, vis) {
  state.visible[slot] = vis;
  const spr = layerSprites[slot];
  if (spr) spr.setVisible(vis);
}

function applyPreset(name) {
  LAYER_ORDER.forEach(slot => {
    const hasAsset = !!layerSprites[slot];
    if (!hasAsset) return;
    let vis = false;
    if (name === 'body-only') vis = slot === 'body';
    else if (name === 'body-hair') vis = slot === 'body' || slot === 'hair';
    else if (name === 'full') vis = true;
    setLayerVisible(slot, vis);
  });
  syncLayerCheckboxes();
}

// ---------------- UI wiring ----------------

function wireUI() {
  document.querySelectorAll('.dir-btn').forEach(btn => {
    btn.addEventListener('click', () => setDirection(parseInt(btn.dataset.dir, 10)));
  });
  document.querySelectorAll('.step-btn').forEach(btn => {
    btn.addEventListener('click', () => setStep(parseInt(btn.dataset.step, 10)));
  });
  syncDirButtons();
  syncStepButtons();

  // layer visibility toggles (모든 슬롯, 에셋 없으면 disabled)
  const layerDiv = document.getElementById('layerToggles');
  LAYER_ORDER.forEach(slot => {
    const hasAsset = !!layerSprites[slot];
    const wrap = document.createElement('label');
    wrap.className = 'toggle-row';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = !!state.visible[slot];
    cb.disabled = !hasAsset;
    cb.addEventListener('change', () => setLayerVisible(slot, cb.checked));
    wrap.appendChild(cb);
    const span = document.createElement('span');
    span.textContent = ' ' + slot + (hasAsset ? '' : ' (에셋 없음)');
    wrap.appendChild(span);
    layerDiv.appendChild(wrap);
    wrap.dataset.slot = slot;
  });

  document.getElementById('presetBodyOnly').addEventListener('click', () => applyPreset('body-only'));
  document.getElementById('presetBodyHair').addEventListener('click', () => applyPreset('body-hair'));
  document.getElementById('presetFull').addEventListener('click', () => applyPreset('full'));

  document.querySelectorAll('.bg-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const stageWrap = document.getElementById('stageWrap');
      stageWrap.classList.remove('bg-dark', 'bg-gray', 'bg-checker');
      stageWrap.classList.add('bg-' + btn.dataset.bg);
    });
  });

  document.querySelectorAll('.zoom-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      state.zoom = parseInt(btn.dataset.zoom, 10);
      if (scene) scene.cameras.main.setZoom(state.zoom);
      document.querySelectorAll('.zoom-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      updateDebug();
    });
  });
}

function syncDirButtons() {
  document.querySelectorAll('.dir-btn').forEach(b => {
    b.classList.toggle('active', parseInt(b.dataset.dir, 10) === state.dirIndex);
  });
}
function syncStepButtons() {
  document.querySelectorAll('.step-btn').forEach(b => {
    b.classList.toggle('active', parseInt(b.dataset.step, 10) === state.stepIndex);
  });
}
function syncLayerCheckboxes() {
  document.querySelectorAll('#layerToggles .toggle-row').forEach(row => {
    const slot = row.dataset.slot;
    const cb = row.querySelector('input');
    cb.checked = !!state.visible[slot];
  });
}

function updateDebug() {
  const f = frameIndex(state.dirIndex, state.stepIndex);
  const cropX = state.stepIndex * FRAME_W;
  const cropY = state.dirIndex * FRAME_H;
  document.getElementById('debugOut').textContent =
`direction : ${DIRS[state.dirIndex]} (row ${state.dirIndex})
step      : ${STEPS[state.stepIndex]} (col ${state.stepIndex})
frameIndex: ${f}
cropX,cropY: ${cropX}, ${cropY}
cropW,cropH: ${FRAME_W}, ${FRAME_H}
zoom      : ${state.zoom}x`;
}

new Phaser.Game({
  type: Phaser.AUTO,
  parent: 'stage',
  width: 700,
  height: 700,
  transparent: true,
  pixelArt: true,
  scene: MainScene,
});
