import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const src=readFileSync(new URL('../../index.html',import.meta.url),'utf8');
function grab(name){const m=src.match(new RegExp('window\\.'+name+' = function[\\s\\S]*?\\n\\};'));assert(m,name);return m[0];}
// DOM 일부가 유실되어도 슬롯 플래그 때문에 다시 생성을 건너뛰면 안 된다.
function host(){return {style:{},children:[],appendChild(e){this.children.push(e);e.parent=this;},
 querySelector(s){const slot=s.match(/data-slot="([^"]+)"/);return this.children.find(e=>slot?e.dataset.slot===slot[1]:s.includes('.'+e.className));},
 querySelectorAll(s){return this.children.filter(e=>s.split(', ').includes('.'+e.className));}};}
const av=host(),ui=host();
const document={getElementById:id=>id==='charworld-avatar'?av:id==='charworld-headui'?ui:null,
 createElement:()=>({style:{},dataset:{},remove(){this.parent.children=this.parent.children.filter(e=>e!==this);}})};
const window={_CHAR_LAYER_ORDER:['body','bottom','shoes','top','hair','acc','hat']};
vm.runInNewContext(grab('_charBuildLayers'),{window,document});
window._charBuildLayers();assert.equal(av.children.length,8);assert.equal(ui.children.length,3);
av.children=[];window._charBuildLayers();assert.equal(av.children.length,8);assert.equal(ui.children.length,3);
av.children.find(e=>e.dataset.slot==='body').remove();window._charBuildLayers();assert.equal(av.children.length,8);
const old=av.children;window._charBuildLayers();assert.equal(av.children,old,'정상 DOM은 매번 갈아끼우지 않는다');

// 정지된 진입 애니메이션은 유한 시간 안에 취소한다. 옛 timer가 새 animation을 지우면 안 된다.
let timers=[],reduced=false,open=false,animations=[];
window.matchMedia=()=>({matches:reduced});window._mwIsOpenField=()=>open;
const room={animate(){const a={cancel(){this.cancelled=true;}};animations.push(a);return a;}};
vm.runInNewContext(grab('_mwRoomEnterFx'),{window,setTimeout:f=>timers.push(f),console});
window._mwRoomEnterFx(room);const first=animations[0];assert.equal(first.cancelled,undefined);
window._mwRoomEnterFx(room);const second=animations[1];assert.equal(first.cancelled,true);
timers[0]();assert.equal(window._mwRoomEnterAnimation,second);assert.equal(second.cancelled,undefined);
timers[1]();assert.equal(second.cancelled,true);assert.equal(window._mwRoomEnterAnimation,null);
reduced=true;window._mwRoomEnterFx(room);assert.equal(animations.length,2);
reduced=false;open=true;window._mwRoomEnterFx(room);assert.equal(animations.length,2,'카메라 transform을 쓰는 공개 필드는 진입 scale로 덮지 않는다');

// 이전 방 이미지의 늦은 onerror가 현재 공원 배경을 덮으면 안 된다.
let probes=[],active=true;
const stage={style:{},dataset:{}},page={classList:{contains:()=>active}};
const doc={getElementById:id=>id==='page-char'?page:id==='charworld-room'?stage:null};
window._FIELDS={home:{src:'home.png'},park:{src:'park.png'}};window._curField='home';window._SW_V='test';
vm.runInNewContext(grab('_mwRepairStage'),{window,document:doc,Image:class{constructor(){probes.push(this);}},console});
window._mwRepairStage();const stale=probes[0];
window._curField='park';stage.style.backgroundImage="url('park.png')";stale.onerror();
assert.equal(stage.style.backgroundImage,"url('park.png')");
window._mwRepairStage();probes[1].onerror();assert.equal(stage.style.backgroundImage,"url('park.png?repair=test')");
active=false;stage.style.backgroundImage='unchanged';probes[1].onerror();assert.equal(stage.style.backgroundImage,'unchanged');
console.log('OK world-stage-recovery: stale/partial DOM rebuild, bounded entry animation, reduced motion, camera protection, stale image guard');
