import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import vm from 'node:vm';
const src=readFileSync(new URL('../../index.html',import.meta.url),'utf8');
const grab=n=>{const m=src.match(new RegExp('window\\.'+n+' = (?:async )?function[\\s\\S]*?\\n\\};'));assert(m,n);return m[0];};
const s={id:'room',hostUid:'host'},mem={staff:{staff:true,status:'accepted'},left:{staff:true,status:'left'},pending:{staff:true,status:'invited'},member:{status:'accepted'}};
const window={_sqDoc:s,_sqMembers:mem};const auth={currentUser:{uid:'member'}};
let writes=0,toasts=0;
vm.runInNewContext(grab('_sqCanManagePaid')+grab('sqTogglePaid')+grab('sqPaidToggleIn'),{window,auth,db:{},doc:()=>({}),updateDoc:async()=>{writes++;},showToast:()=>toasts++,document:{querySelector:()=>null}});
for(const [uid,allow] of [['host',true],['staff',true],['left',false],['pending',false],['member',false],['outsider',false],[null,false]]){
 assert.equal(window._sqCanManagePaid(s,mem,uid),allow,uid);
 auth.currentUser={uid};const before=writes;
 await window.sqTogglePaid('room','member',false);await window.sqPaidToggleIn('room','member');
 assert.equal(writes-before,allow?2:0,'write guard '+uid);
}
auth.currentUser={uid:'staff'};const before=writes;await window.sqTogglePaid('other','member',false);assert.equal(writes,before);
let popup;
window._sqShowName=()=>'';
vm.runInNewContext(grab('sqPaidPicker'),{window,auth,showToast:()=>{},document:{getElementById:()=>null,createElement:()=>({style:{}}),body:{appendChild:e=>popup=e}}});
window.sqPaidPicker('room');assert(popup.innerHTML.includes('onclick="window.sqPaidToggleIn'));
auth.currentUser={uid:'member'};window.sqPaidPicker('room');assert(!popup.innerHTML.includes('onclick="window.sqPaidToggleIn'));
assert(src.includes('s.feeAmount>0 && window._sqCanManagePaid(s, mem, me) && !wait'));
let prior=null,saved,merged;
window._mwMyNick='test';window._charSafe=v=>v;
vm.runInNewContext(grab('joinSquad'),{window,auth,db:{},doc:(_db,...p)=>p.join('/'),serverTimestamp:()=>0,showToast:()=>{},runTransaction:async (_db,cb)=>cb({
 get:async ref=>ref.includes('/members/')?{exists:()=>prior!==null,data:()=>prior}:{exists:()=>true,data:()=>({status:'active',memberUids:[],capacity:10})},
 update:()=>{},set:(_ref,data,options)=>{saved=data;merged=options.merge;}
})});
await window.joinSquad('room');assert.equal(saved.paid,false);assert.equal(merged,true);
prior={status:'left',staff:true,paid:true};await window.joinSquad('room');
assert(!Object.hasOwn(saved,'paid'),'rejoin preserves paid');assert.equal(saved.staff,false,'rejoin drops stale staff');
prior={status:'left',paid:false};await window.joinSquad('room');assert(!Object.hasOwn(saved,'paid'));assert(!Object.hasOwn(saved,'staff'));
console.log('OK squad-paid: host/active staff allowed; ordinary/pending/left/foreign-room blocked; UI and action guards');
