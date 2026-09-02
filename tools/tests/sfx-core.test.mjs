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
assert.strictEqual(pendingFetches.length, 3, '무궁화 preload가 훈수 음성까지 전부 받는다');
w.sfx.voice('mugung_go_1', 0.9, 'mugung');
assert.strictEqual(voiceStarts, 0, '디코드 전 음성이 재생됐다');
pendingFetches.forEach(x => x.resolve({ ok: true, arrayBuffer: () => Promise.resolve(new ArrayBuffer(8)) }));
await new Promise(resolve => setTimeout(resolve, 0));
await new Promise(resolve => setTimeout(resolve, 0));
assert.strictEqual(voiceStarts, 1, 'preload 중 들어온 시작 음성이 디코드 뒤 재생되지 않았다');

w.sfx.play('start');
assert(toneStarts > 0, '스쿼드 시작 효과음이 재생되지 않았다');
console.log('sfx-core: preload 경합·시작 효과음 통과');
