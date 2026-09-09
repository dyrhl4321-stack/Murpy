import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const src=readFileSync(new URL('../../index.html',import.meta.url),'utf8');
const grab=n=>{const m=src.match(new RegExp('window\\.'+n+' = function[\\s\\S]*?\\n\\};'));assert(m,n);return m[0];};
let images=[],timers=new Map(),timerId=0,decodes=0;
class Image {
  constructor(){images.push(this);this.naturalWidth=100;this.naturalHeight=200;}
  decode(){decodes++;return Promise.resolve();}
}
const furniture={style:{}},window={_mwWarmCache:new Map()};
const ctx={window,Image,Promise,Map,setTimeout:f=>{timers.set(++timerId,f);return timerId;},clearTimeout:id=>timers.delete(id),document:{getElementById:()=>null}};
const flush=async()=>{for(let i=0;i<6;i++)await Promise.resolve();};
vm.runInNewContext(grab('_mwWarmImage')+grab('_mwWarmField')+grab('_mwFieldReveal'),ctx);
const p=window._mwWarmImage('field.png');assert.equal(window._mwWarmImage('field.png'),p);assert.equal(images.length,1);
images[0].onload();assert.equal(await p,images[0]);assert.equal(decodes,1);assert.equal(window._mwWarmImage('field.png'),p);
const failed=window._mwWarmImage('bad.png');images.at(-1).onerror();assert.equal(await failed,null);
assert(!window._mwWarmCache.has('bad.png'));const retry=window._mwWarmImage('bad.png');assert.notEqual(retry,failed);images.at(-1).onload();await retry;
const hung=window._mwWarmImage('hang.png');timers.get(timerId)();assert.equal(await hung,null);assert(!window._mwWarmCache.has('hang.png'));
// 이미 로드된 필드는 교체/오브젝트 표시가 같은 decode 결과를 재사용한다. 옛 필드 콜백은 무시.
window._FIELDS={home:{src:'field.png'},park:{src:'park.png'}};window._MW_FIELD_SPRITES={home:[]};window._mwFieldTok=2;
ctx.document.getElementById=()=>furniture;
const before=images.length;window._mwWarmField('home');window._mwFieldReveal('home',2);await flush();
assert.equal(images.length,before);assert.equal(furniture.style.visibility,'visible');
furniture.style.visibility='hidden';window._mwFieldReveal('park',2);window._mwFieldTok=3;images.at(-1).onload();await flush();assert.equal(furniture.style.visibility,'hidden');
// 게임 진입 연타/필드 프리로드와 게임 오픈은 동일 파일 요청만 공유한다.
ctx.document.getElementById=()=>null;
for(const game of ['dodge','golf','tennis','run']){
  window._mwWarmCache.clear();images=[];window['_'+game+'Art']=null;
  window['_'+game+'PaintStart']=()=>{};
  vm.runInNewContext(grab('_'+game+'CheckArt'),ctx);
  const check=window['_'+game+'CheckArt'];check();const n=images.length;check();check();assert.equal(images.length,n,game+' pending dedupe');
  for(const im of images)im.onload();await flush();assert.equal(window['_'+game+'Art'],true);check();assert.equal(images.length,n,game+' warm reuse');
}
for(let i=0;i<30;i++){window._mwWarmImage('bounded-'+i);images.at(-1).onload();await flush();}
assert(window._mwWarmCache.size<=16,'decoded images bounded');
assert(!src.includes("golf_title.png?v=6"));assert(!src.includes("tennis_title.png?v=10"));assert(!src.includes("run_title.png?v=5"));
assert(grab('_mwFmGo').indexOf('_mwWarmField(k)')<grab('_mwFmGo').indexOf('window._mwFmBusy = 1'));
assert(grab('charSetField').indexOf('_mwWarmField(key)')<grab('charSetField').indexOf('_mwParkAmbient'));
assert(grab('sqMugungJoin').includes('_sqMgWarmArt()'));
console.log('OK game-field-loading: request/decode dedupe, failure/timeout retry, bounded cache, field token safety, 4 game warm starts, matching URLs, participant preload');
