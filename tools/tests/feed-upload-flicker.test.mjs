import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const html = fs.readFileSync(new URL('../../index.html', import.meta.url), 'utf8');

function functionSource(name) {
  const start = html.indexOf('function ' + name + '(');
  assert.ok(start >= 0, name + ' 함수를 찾을 수 없음');
  const brace = html.indexOf('{', start);
  let depth = 0;
  let quote = '';
  let escaped = false;
  for (let i = brace; i < html.length; i++) {
    const ch = html[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (ch === '\\') escaped = true;
      else if (ch === quote) quote = '';
      continue;
    }
    if (ch === "'" || ch === '"' || ch === '`') { quote = ch; continue; }
    if (ch === '{') depth++;
    if (ch === '}' && --depth === 0) return html.slice(start, i + 1);
  }
  throw new Error(name + ' 함수 끝을 찾을 수 없음');
}

// 1) 큰 사진의 FileReader가 끝나기 전에도 홈을 크롭 모달이 덮어야 한다.
{
  const els = {
    'crop-modal': { style: {} },
    'crop-image': { style: {}, removeAttribute() {}, onload: null, onerror: null },
    'crop-loading': { style: {} },
    'feed-photo-input': { value: 'picked' }
  };
  let readStarted = false;
  let locked = false;
  class Reader {
    readAsDataURL() { readStarted = true; }
  }
  const context = {
    window: { _exifShotAt: () => Promise.resolve(null), cropData: {} },
    document: { getElementById: id => els[id] || null },
    FileReader: Reader,
    closeModal() {},
    lockBodyScroll() { locked = true; },
    unlockBodyScroll() {},
    _setCropStep() {},
    requestAnimationFrame() {},
    console
  };
  vm.runInNewContext(functionSource('openCropModal') + ';openCropModal({});', context);
  assert.equal(readStarted, true, 'FileReader 시작');
  assert.equal(els['crop-modal'].style.display, 'flex', '디코딩 전 모달 표시');
  assert.equal(els['crop-loading'].style.display, 'flex', '디코딩 전 로딩판 표시');
  assert.equal(locked, true, '배경 스크롤 잠금');
}

// 2) 닫을 때는 모달이 덮인 채 스크롤을 먼저 복원하고 다음 프레임에 숨긴다.
{
  const modal = { style: { display: 'flex' } };
  const els = {
    'crop-modal': modal,
    'crop-loading': { style: { display: 'flex' } },
    'feed-photo-input': { value: 'picked' },
    'feed-post-input': { value: 'memo' },
    'mcam-caption': { value: 'caption', style: {} },
    'caption-row': { style: {} }
  };
  const frames = [];
  let displayAtUnlock = '';
  const context = {
    window: { cropData: {}, _composePreviewUrl: null },
    document: { getElementById: id => els[id] || null },
    unlockBodyScroll() { displayAtUnlock = modal.style.display; },
    requestAnimationFrame(fn) { frames.push(fn); },
    clearTimeout() {},
    URL: { revokeObjectURL() {} }
  };
  vm.runInNewContext(functionSource('closeCropModal') + ';closeCropModal();', context);
  assert.equal(displayAtUnlock, 'flex', '스크롤 복원 중 모달 유지');
  assert.equal(modal.style.display, 'flex', '같은 프레임에 모달을 숨기지 않음');
  frames.shift()();
  assert.equal(modal.style.display, 'none', '다음 프레임에 모달 숨김');
}

// 3) 게시 성공 뒤에는 새 글 한 장만 준비한 후 닫고, 전체 피드 loadFeed를 호출하지 않는다.
{
  const submit = html.slice(html.indexOf('window.submitFeedPost = async function()'), html.indexOf('// 댓글 저장 (Firestore)'));
  const warm = submit.indexOf('await _warmFeedPhoto');
  const prepend = submit.indexOf('_prependUploadedFeedPost');
  const close = submit.indexOf('closeCropModal()');
  assert.ok(warm >= 0 && prepend > warm && close > prepend, '사진 예열 → 한 장 추가 → 모달 닫기 순서');
  assert.equal(/\bloadFeed\s*\(/.test(submit), false, '업로드 완료 경로에서 전체 피드 재렌더 금지');
}

console.log('OK feed upload flicker regression (3)');
