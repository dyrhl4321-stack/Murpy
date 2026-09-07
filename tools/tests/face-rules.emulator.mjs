// Manual integration test. Requires a local demo-murpyface Firestore emulator on 127.0.0.1:8788.
// Never accepts a production project/host; no real credentials or real user data.
import assert from 'node:assert/strict';
const project = 'demo-murpyface';
const prefix = `projects/${project}/databases/(default)/documents`;
const root = `http://127.0.0.1:8788/v1/${prefix}`;
const encode = v => typeof v === 'string' ? { stringValue:v } : typeof v === 'number' ? { integerValue:String(v) }
  : typeof v === 'boolean' ? { booleanValue:v } : Array.isArray(v) ? { arrayValue:{values:v.map(encode)} }
  : { mapValue:{fields:Object.fromEntries(Object.entries(v).map(([k,x]) => [k,encode(x)]))} };
const write = (path, data, mask) => ({ update:{name:`${prefix}/${path}`,fields:encode(data).mapValue.fields},
  ...(mask ? {updateMask:{fieldPaths:mask}} : {}) });
function token(uid) {
  const now = Math.floor(Date.now()/1000);
  const part = v => Buffer.from(JSON.stringify(v)).toString('base64url');
  return part({alg:'none',typ:'JWT'}) + '.' + part({sub:uid,user_id:uid,aud:project,
    iss:`https://securetoken.google.com/${project}`,iat:now,exp:now+3600,firebase:{sign_in_provider:'custom'}}) + '.';
}
let checks=0;
async function commit(writes, user='owner', expected=200) {
  const response=await fetch(root+':commit',{method:'POST',headers:{'Content-Type':'application/json',
    Authorization:'Bearer '+(user==='owner'?'owner':token(user))},body:JSON.stringify({writes})});
  const text=await response.text();
  assert.equal(response.status,expected,text); checks++;
}
await commit([
  write('users/alice',{gender:'여성',credits:100,faceTickets:2,character:{body:'human_f'}}),
  write('users/bob',{gender:'남성',credits:100,faceTickets:1,character:{body:'human'}}),
  write('users/alice/faceChars/one',{sheetUrl:'alice-sheet',name:'mine'}),
  write('users/bob/faceChars/two',{sheetUrl:'bob-sheet',name:'theirs'})
]);
await commit([write('users/alice',{character:{body:'face:one'},characterSheet:'alice-sheet'},['character','characterSheet'])],'alice');
await commit([write('users/alice',{character:{body:'face:two'},characterSheet:'bob-sheet'},['character','characterSheet'])],'alice',403);
await commit([write('users/alice',{character:{body:'face:one'},characterSheet:'bob-sheet'},['character','characterSheet'])],'alice',403);
await commit([{delete:`${prefix}/users/alice/faceChars/one`}],'alice',403);
await commit([write('faceAppeals/alice_two',{uid:'alice',charId:'two',sheetUrl:'bob-sheet',reasons:[],text:'',status:'open'})],'alice',403);
await commit([
  write('users/alice',{character:{body:'human_f'}},['character','characterSheet']),
  write('faceAppeals/alice_one',{uid:'alice',charId:'one',sheetUrl:'alice-sheet',reasons:['quality'],text:'',status:'open'}),
  {delete:`${prefix}/users/alice/faceChars/one`}
],'alice');
await commit([write('users/alice',{character:{body:'face:one'},characterSheet:'alice-sheet'},['character','characterSheet'])],'alice',403);
const request={uid:'alice',status:'pending',photoUrl:'own-source',t:100};
await commit([write('faceRequests/alice',request)],'alice',403);
await commit([write('users/alice',{faceTickets:1},['faceTickets']),write('faceRequests/alice',request)],'alice');
await commit([write('users/alice',{faceTickets:0},['faceTickets']),write('faceRequests/alice',{...request,t:200})],'alice',403);
await commit([write('faceRequests/bob',{...request,uid:'bob'})],'alice',403);
await commit([write('users/alice',{nickname:'changed'},['nickname'])],'alice');
console.log(`OK Firestore emulator ${checks} checks: owned face, atomic deletion, paid request, busy/cross-user denial`);
