import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import vm from 'node:vm';
const src=readFileSync(new URL('../../index.html',import.meta.url),'utf8');
const grab=n=>{const m=src.match(new RegExp('window\\.'+n+' = (?:async )?function[\\s\\S]*?\\n\\};'));assert(m,n);return m[0];};
// Emotes: static squad title already belongs to parent height. Floating world title does not.
for(const [top,hostHeight,titleTop,scale,expected] of [[100,100,100,1,4],[100,100,86,1,18],[100,100,72,2,18]]){
 let emote;
 const te={textContent:'title',style:{},offsetHeight:12,getBoundingClientRect:()=>({top:titleTop})};
 const host={offsetHeight:hostHeight,getBoundingClientRect:()=>({top,height:hostHeight*scale}),querySelector:q=>q.includes('.cw-title')?te:null,appendChild:e=>emote=e};
 const window={_MW_EMOTES:['smile']};
 vm.runInNewContext(grab('_mwEmotePop'),{window,document:{createElement:()=>({style:{}})},setTimeout:()=>{}});
 window._mwEmotePop(host,'smile');assert.equal(emote.style.bottom,`calc(100% + ${expected}px)`);
}
// Dodge: changing direction never detaches loaded body/hair nodes. Late definition refreshes even facing same way.
let replacements=0,html='avatar-A',layers=[{style:{}},{style:{}}];
const me={style:{},classList:{toggle:()=>{}},querySelectorAll:()=>layers,set innerHTML(v){replacements++;layers=[{style:{}},{style:{}}];}};
const field={clientWidth:360,clientHeight:640};
const window={DODGE:{W:100,PLAYER_H:20,PLAYER_Y:88},_charState:{character:{}},getMyCharacter:()=>({}),mwMiniCharHtml:()=>html};
const document={getElementById:id=>id==='dodge-field'?field:id==='dodge-me'?me:null};
vm.runInNewContext(grab('_dodgePaint'),{window,document,auth:{currentUser:{}}});
const s={items:[],face:'down',x:50,t:0,slowUntil:0,score:0};
window._dodgePaint(s);const original=layers;
for(const dir of ['left','right','left','down']){s.face=dir;window._dodgePaint(s);assert.equal(layers,original);assert.equal(layers[0].style.backgroundPositionY,`${-(dir==='left'?2:dir==='right'?3:0)*128}px`);}
assert.equal(replacements,1);html='avatar-B';window._dodgePaint(s);assert.equal(replacements,2);
// Composer: asset failure retains requested filter/caption and never publishes an unstamped fallback.
const el={
 'mcam-toggle':{checked:true,style:{}},'mcam-busy':{style:{}},'compose-preview':{src:'old-preview'},
 'mcam-caption':{value:'오늘도 완료',style:{}},'caption-row':{style:{}},'feed-post-input':{value:'',style:{}}
};
const cam={cropData:{plainBlob:{},croppedBlob:'old-photo'},_mwBuildStamp:async()=>{throw Error('CORS');},showToast:()=>{}};
class Img{set src(v){queueMicrotask(()=>this.onload());}}
let made=0,revoked=0,notice='';
vm.runInNewContext(grab('toggleMurpyCam'),{window:cam,document:{getElementById:id=>el[id]},Image:Img,URL:{createObjectURL:()=>`blob:${++made}`,revokeObjectURL:()=>revoked++},fetch:async()=>({blob:async()=>({})}),showToast:t=>notice=t,console:{warn:()=>{}},requestAnimationFrame:()=>{},setTimeout:()=>{}});
await cam.toggleMurpyCam();assert.equal(el['mcam-toggle'].checked,true);assert.equal(el['mcam-caption'].value,'오늘도 완료');assert.equal(cam.cropData.croppedBlob,'old-photo');assert.equal(cam.cropData.mcamError,'CORS');assert.equal(cam.cropData.mcamPending,false);assert.equal(revoked,1);
// Turning it off deliberately remains supported.
el['mcam-toggle'].checked=false;await cam.toggleMurpyCam();assert.equal(cam.cropData.croppedBlob,cam.cropData.plainBlob);assert.equal(cam.cropData.mcamError,null);
// A late preview must not update a newly selected photo.
let finish;cam._mwBuildStamp=()=>new Promise(r=>finish=r);el['mcam-toggle'].checked=true;
const pending=cam.toggleMurpyCam();await new Promise(r=>setImmediate(r));cam.cropData={plainBlob:{},croppedBlob:'new-photo'};finish('data:fixture');await pending;assert.equal(cam.cropData.croppedBlob,'new-photo');
const submit=grab('submitFeedPost');assert(submit.includes('if (_mcamOn)'));assert(!submit.includes('_mcamOn && camText'));assert(submit.includes('cropData.mcamPending'));
// Actual submit: even a blank caption recomposes; failed or pending composition never reaches upload.
let builds=0,uploads=0,fail=false;
const posting={cropData:{plainBlob:{},croppedBlob:'preview'},_mwBuildStamp:async()=>{builds++;if(fail)throw Error('asset');return 'data:complete';}};
el['mcam-toggle'].checked=true;el['mcam-caption'].style.display='';el['mcam-caption'].value='';
vm.runInNewContext(submit,{window:posting,document:{getElementById:id=>el[id]},auth:{currentUser:{uid:'fixture'}},showToast:()=>{},Image:Img,
 URL:{createObjectURL:()=> 'blob:plain',revokeObjectURL:()=>{}},getDoc:async()=>({exists:()=>false}),doc:()=>({}),db:{},FormData:class{append(){}},
 fetch:async u=>{if(u==='data:complete')return {blob:async()=>({})};uploads++;throw Error('stop before real upload');},console:{warn:()=>{},error:()=>{}},setTimeout:()=>{},clearTimeout:()=>{}});
await posting.submitFeedPost();assert.equal(builds,1);assert.equal(uploads,1);
fail=true;await posting.submitFeedPost();assert.equal(builds,2);assert.equal(uploads,1);
posting.cropData.mcamPending=true;await posting.submitFeedPost();assert.equal(builds,2);assert.equal(uploads,1);
console.log('OK reports 44/45: title geometry, persistent dodge layers, late asset refresh, failed/stale composer guard, captionless final compose');
