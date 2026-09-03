// 공용 사운드 — preload 중 들어온 음성 요청이 버려지지 않는지 검증
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const src = readFileSync(join(root, 'index.html'), 'utf8');
const hit = src.match(/window\.sfx = \(function \(\) \{[\s\S]*?\n\}\)\(\);/);
assert(hit, 'index.html에서 window.sfx 모듈을 찾지 못함');

let voiceStarts = 0, toneStarts = 0;
class AudioContextMock {
  constructor() { this.state = 'running'; this.currentTime = 0; this.sampleRate = 24000; this.destination = {}; }
  resume() { this.state = 'running'; return Promise.resolve(); }
  createBufferSource() { return { connect() {}, start() { voiceStarts++; }, stop() {}, onended: null, buffer: null }; }
  createGain() { return { connect() {}, gain: { value: 0, setValueAtTime() {}, linearRampToValueAtTime() {}, exponentialRampToValueAtTime() {} } }; }
  createOscillator() { return { connect() {}, start() { toneStarts++; }, stop() {}, frequency: { setValueAtTime() {}, exponentialRampToValueAtTime() {} } }; }
  createBiquadFilter() { return { connect() {}, type: '', frequency: { setValueAtTime() {}, exponentialRampToValueAtTime() {} } }; }
  createBuffer() { return { getChannelData() { return new Float32Array(2); } }; }
  decodeAudioData() { return Promise.resolve({ decoded: true }); }
}

const pendingFetches = [];
const fetchMock = url => new Promise(resolve => pendingFetches.push({ url, resolve }));
const doc = { hidden: false, addEventListener() {}, removeEventListener() {}, createElement() { return { setAttribute() {}, play() { return Promise.resolve(); }, volume: 0, src: '' }; } };
const storage = { getItem() { return null; }, setItem() {} };
const w = { AudioContext: AudioContextMock };
new Function('window', 'document', 'localStorage', 'fetch', hit[0])(w, doc, storage, fetchMock);

w.sfx.preload('mugung_go_');
assert.strictEqual(pendingFetches.length, 7, '무궁화 7패턴 preload가 훈수 음성까지 전부 받는다');
w.sfx.voice('mugung_go_1', 0.9, 'mugung');
assert.strictEqual(voiceStarts, 0, '디코드 전 음성이 재생됐다');
pendingFetches.forEach(x => x.resolve({ ok: true, arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)) }));
await new Promise(resolve => setTimeout(resolve, 0));
await new Promise(resolve => setTimeout(resolve, 0));
assert.strictEqual(voiceStarts, 1, 'preload 중 들어온 시작 음성이 디코드 뒤 재생되지 않았다');

w.sfx.preloadFx();
assert.strictEqual(pendingFetches.length, 11, '골프 생물 효과음 4개를 미리 받지 않는다');
const fxUrls = pendingFetches.slice(7).map(x => x.url).sort();
assert.deepStrictEqual(fxUrls, [
  'char/game/sfx/golf_crow_ambient.wav?v=1',
  'char/game/sfx/golf_crow_hit.wav?v=1',
  'char/game/sfx/golf_mole_dig.wav?v=1',
  'char/game/sfx/golf_mole_hit.wav?v=1'
]);
assert(src.includes("crow: 'crowHit', mole: 'moleHit'"), '까마귀·두더지 충돌음이 각각 별도 파일 효과음으로 연결되지 않았다');
assert(src.includes("S().play('crowAmbient')"), '까마귀 배경 울음 예약이 없다');
assert(src.includes("S().play('moleDig')"), '두더지 등장 흙파기 소리가 없다');
assert(!src.includes("window.sfx && window.sfx.play('mole')"), '두더지 충돌음이 본문과 래퍼에서 중복 재생된다');

w.sfx.play('start');
assert(toneStarts > 0, '스쿼드 시작 효과음이 재생되지 않았다');
console.log('sfx-core: preload 경합·시작음·골프 생물음 분리 통과');
