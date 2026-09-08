// Local demo emulator only. Does not accept production host or credentials.
import assert from 'node:assert/strict';
const project='demo-murpyface',prefix=`projects/${project}/databases/(default)/documents`,root=`http://127.0.0.1:8793/v1/${prefix}`;
const enc=v=>typeof v==='boolean'?{booleanValue:v}:typeof v==='string'?{stringValue:v}:{mapValue:{fields:Object.fromEntries(Object.entries(v).map(([k,x])=>[k,enc(x)]))}};
const write=(p,d,mask)=>({update:{name:`${prefix}/${p}`,fields:enc(d).mapValue.fields},...(mask?{updateMask:{fieldPaths:mask}}:{})});
function jwt(uid){const now=Math.floor(Date.now()/1000),part=v=>Buffer.from(JSON.stringify(v)).toString('base64url');return part({alg:'none',typ:'JWT'})+'.'+part({sub:uid,user_id:uid,aud:project,iss:`https://securetoken.google.com/${project}`,iat:now,exp:now+3600,firebase:{sign_in_provider:'custom'}})+'.';}
let checks=0;
async function commit(w,user='owner',code=200){const r=await fetch(root+':commit',{method:'POST',headers:{'Content-Type':'application/json',Authorization:'Bearer '+(user==='owner'?'owner':jwt(user))},body:JSON.stringify({writes:w})});assert.equal(r.status,code,await r.text());checks++;}
await commit([write('squads/paid-test',{hostUid:'host'}),...Object.entries({host:{status:'accepted'},staff:{status:'accepted',staff:true},left:{status:'left',staff:true},member:{status:'accepted',paid:false},other:{status:'accepted',paid:false}}).map(([u,d])=>write('squads/paid-test/members/'+u,d))]);
const member='squads/paid-test/members/member',staff='squads/paid-test/members/staff';
await commit([write(member,{paid:true},['paid'])],'staff');
await commit([write(member,{paid:false},['paid'])],'staff');
await commit([write(member,{paid:true},['paid'])],'host');
await commit([write(member,{paid:false},['paid'])],'member',403);
await commit([write(member,{paid:false},['paid'])],'left',403);
await commit([write('squads/paid-test/members/left',{status:'accepted'},['status'])],'left',403);
await commit([write('squads/paid-test/members/left',{status:'accepted'},['status'])],'staff',403);
await commit([write('squads/paid-test/members/left',{status:'accepted',staff:false},['status','staff'])],'left');
await commit([write(member,{paid:false},['paid'])],'left',403);
await commit([write(member,{paid:false},['paid'])],'outsider',403);
await commit([write(member,{staff:true},['staff'])],'member',403);
await commit([write(member,{staff:true},['staff'])],'staff',403);
await commit([write('squads/paid-test/members/new',{status:'accepted',staff:true,paid:false})],'new',403);
await commit([write('squads/paid-test/members/new',{status:'accepted',paid:true})],'new',403);
await commit([write('squads/paid-test/members/new',{status:'invited',paid:false})],'new');
await commit([write(member,{nickname:'updated'},['nickname'])],'member');
await commit([write(member,{paid:'yes'},['paid'])],'staff',403);
await commit([{delete:`${prefix}/${member}`}],'member',403);
await commit([write(member,{staff:true},['staff'])],'host');
await commit([write(staff,{staff:false},['staff'])],'host');
await commit([write(member,{paid:false},['paid'])],'staff',403);
await commit([write(member,{status:'left'},['status'])],'member');
await commit([write('squads/paid-test/members/other',{paid:true},['paid'])],'member',403);
console.log('OK squad payment rules emulator',checks,'checks');
