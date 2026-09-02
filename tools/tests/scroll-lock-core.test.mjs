// 패널 중복 열기와 동적 입력 모달이 스크롤 잠금 상태를 누수하지 않는지 검증한다.
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
const grab = (re, name) => {
  const m = src.match(re);
  assert(m, `index.html에서 ${name}을 찾지 못함`);
  return m[0];
};

// 같은 패널을 두 번 여는 호출은 깊이를 한 번만 올려야 한다.
{
  let open = false, locks = 0;
  const el = {
    style: {},
    classList: {
      contains(name) { return name === 'open' && open; },
      add(name) { if (name === 'open') open = true; },
    },
  };
  const doc = { getElementById(id) { return id === 'plain-panel' ? el : null; } };
  const w = {};
  const body = grab(/function openPanel\(id\) \{[\s\S]*?\n\}/, 'openPanel')
    + '\nwindow.__openPanel = openPanel;';
  new Function('window', 'document', 'lockBodyScroll', body)(w, doc, () => { locks++; });
  w.__openPanel('missing');
  w.__openPanel('plain-panel');
  w.__openPanel('plain-panel');
  assert.strictEqual(w._panelDepth, 1, '중복 openPanel 호출이 depth를 누수한다');
  assert.strictEqual(locks, 1, '본문 잠금이 중복 실행됐다');
}

// 동적 머피월드 입력 모달은 구조대가 알아볼 표식을 열 때 달고 닫을 때 지운다.
{
  const w = {};
  const body = 'let _bodyLocked=false, locks=0, unlocks=0;'
    + 'const lockBodyScroll=()=>{_bodyLocked=true;locks++;};'
    + 'const unlockBodyScroll=()=>{_bodyLocked=false;unlocks++;};'
    + grab(/window\._mwModalKbOpen = function[\s\S]*?\n\};/, '_mwModalKbOpen')
    + grab(/window\._mwModalKbClose = function[\s\S]*?\n\};/, '_mwModalKbClose')
    + 'window.__counts=()=>({locks,unlocks});';
  new Function('window', body)(w);
  const el = { dataset: {} };
  w._mwModalKbOpen(el);
  assert.strictEqual(el.dataset.mwScrollLock, '1');
  w._mwModalKbClose(el);
  assert.strictEqual(el.dataset.mwScrollLock, undefined);
  assert.deepStrictEqual(w.__counts(), { locks: 1, unlocks: 1 });
}

// 표식이 있는 동안 rescue는 정당한 잠금을 풀면 안 되고, 주인이 사라지면 풀어야 한다.
{
  let marker = true;
  const w = { _panelDepth: 3 };
  const doc = {
    querySelector(sel) { return sel === '[data-mw-scroll-lock="1"]' && marker ? {} : null; },
    getElementById() { return null; },
    body: { classList: { contains() { return false; } } },
  };
  const body = 'let _bodyLocked=true, unlocks=0; const unlockBodyScroll=()=>{unlocks++;};'
    + grab(/window\._scrollRescue = function[\s\S]*?\n\};/, '_scrollRescue')
    + 'window.__unlocks=()=>unlocks;';
  new Function('window', 'document', body)(w, doc);
  w._scrollRescue();
  assert.strictEqual(w.__unlocks(), 0, '열린 동적 모달의 잠금을 rescue가 풀었다');
  marker = false;
  w._scrollRescue();
  assert.strictEqual(w.__unlocks(), 1, '주인 없는 잠금을 rescue가 풀지 않았다');
  assert.strictEqual(w._panelDepth, 0);
}

console.log('scroll-lock-core: 중복 패널·동적 모달·rescue 통과');
