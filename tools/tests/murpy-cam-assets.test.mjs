import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
import vm from 'node:vm';
const src = readFileSync(new URL('../../index.html', import.meta.url), 'utf8');
const extract = name => {
  const m = src.match(new RegExp('window\\.' + name + ' = (?:async )?function[\\s\\S]*?\\n\\};'));
  assert(m, name); return m[0];
};
const drawn = [], loaded = [];
const ctx = { imageSmoothingEnabled: true, drawImage: im => drawn.push(im.id) };
const window = {
  _charEquippedSheets: () => ({body:'face',top:'shirt',hair:'overlay'}),
  _charLayerOrder: () => ['body','top','hair'],
  _mcamLoadSheet: async id => { loaded.push(id); return {id,width:423,height:896}; }
};
vm.runInNewContext(extract('_mcamDrawChar'), {window});
const box = {x:0,y:0,w:141,h:224};
assert.equal(await window._mcamDrawChar(ctx, {}, box), true);
assert.deepEqual(drawn, ['face','shirt','overlay']);
assert.equal(ctx.imageSmoothingEnabled, true);
drawn.length=0;
window._mcamLoadSheet = async id => { if(id==='face') throw new Error('CORS'); return {id}; };
await assert.rejects(window._mcamDrawChar(ctx, {}, box), /CORS/);
assert.deepEqual(drawn, [], '몸통 실패 후 옷만 그려서는 안 된다');
window._charEquippedSheets = () => ({top:'shirt'});
await assert.rejects(window._mcamDrawChar(ctx, {}, box), e => e.code==='MCAM_ASSET');
assert.deepEqual(drawn, []);

// CORS 요청, CSS 캐시 분리, 토큰 보존, timeout 및 onerror 정리.
let image, timer, cleared=0;
class FakeImage {
  constructor(){ image=this; this.naturalWidth=423; this.naturalHeight=896; }
  set src(v){this.url=v;} get src(){return this.url;}
}
vm.runInNewContext(extract('_mcamLoadSheet'), {window, Image:FakeImage, URL, location:{href:'https://murpy.app/'},
  setTimeout:f => {timer=f;return 1;}, clearTimeout:()=>cleared++});
let result=window._mcamLoadSheet('https://firebasestorage.googleapis.com/v0/b/example/o/a?alt=media&token=fixture');
assert.equal(image.crossOrigin,'anonymous');
assert.equal(new URL(image.src).searchParams.get('token'),'fixture');
assert.equal(new URL(image.src).searchParams.get('mcam'),'2');
image.onload(); assert.equal(await result,image); assert.equal(image.onload,null);
result=window._mcamLoadSheet('char/walk.png?v=1');
assert.equal(image.src,'https://murpy.app/char/walk.png?v=1');
timer(); await assert.rejects(result,e=>e.code==='MCAM_ASSET'); assert.equal(image.src,'');
result=window._mcamLoadSheet('char/walk.png?v=1'); image.onerror();
await assert.rejects(result,e=>e.code==='MCAM_ASSET'); assert.equal(cleared,3);

// 합성 본문도 실패를 삼키지 않고 호출자까지 전파한다.
const canvasCtx = new Proxy({}, {get:(_,k)=>k==='drawImage'?()=>{}:()=>{},set:()=>true});
const document = {fonts:{load:async()=>{}},createElement:()=>({getContext:()=>canvasCtx,toDataURL:()=>{throw Error('must not export');}})};
window.getMyCharacter=()=>({body:'face:new'});
window._charEquippedSheets=()=>({body:'face'});
window._mcamDrawChar=async()=>{const e=new Error('asset');e.code='MCAM_ASSET';throw e;};
vm.runInNewContext(extract('_mwBuildStamp'),{window,document,console:{warn:()=>{}},Date});
await assert.rejects(window._mwBuildStamp({width:1080,height:1350},null,''),e=>e.code==='MCAM_ASSET');

// 카메라 탭 실패 시 이전 사진을 다시 공유하지 않는다.
let shown=0, notice='';
window._mwStampData='old-photo'; window.mwCloseCam=()=>{}; window.mwShowStampResult=()=>shown++;
vm.runInNewContext(extract('mwCompose'),{window,showToast:t=>notice=t});
await window.mwCompose({width:1080,height:1350});
assert.equal(window._mwStampData,null); assert.equal(shown,0); assert.equal(notice,'asset');
console.log('OK murpy-cam-assets: full-layer atomic draw, CORS URL, failures/timeouts, export rejection, stale photo guard');
