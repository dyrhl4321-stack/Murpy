import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';
const src = readFileSync(new URL('../../index.html', import.meta.url), 'utf8');
const discard = src.match(/window\._faceDiscardTx = async function[\s\S]*?\n\};/)[0];
const grant = src.match(/window\.faceAdminAppealDone = async function[\s\S]*?\n\};/)[0];
const del = { deleteField: true };
function harness(gender = '여성', wearing = true) {
  const store = { 'users/alice': { gender, faceTickets: 2, character: { body: wearing ? 'face:one' : 'human_f', skin: 't2' }, characterSheet: 'url' },
    'users/alice/faceChars/one': { name: '내 얼굴', sheetUrl: 'url' } };
  let queue = Promise.resolve();
  const w = { currentUser: { uid: 'alice' }, faceAdminAppeals() {} };
  const db = { fail: false };
  const transaction = (_, fn) => {
    const work = queue.then(async () => {
      const writes = [];
      const tx = { get: async ref => ({ exists: () => !!store[ref], data: () => structuredClone(store[ref]) }),
        update: (ref, data) => writes.push(['update', ref, data]), set: (ref, data) => writes.push(['set', ref, data]),
        delete: ref => writes.push(['delete', ref]) };
      const result = await fn(tx);
      if (db.fail) throw new Error('simulated commit rejection');
      for (const [kind, ref, data] of writes) {
        if (kind === 'delete') delete store[ref];
        else {
          store[ref] = kind === 'set' ? {} : store[ref];
          for (const [key, value] of Object.entries(data)) {
            if (value === del) delete store[ref][key]; else store[ref][key] = structuredClone(value);
          }
        }
      }
      return result;
    });
    queue = work.catch(() => {}); return work;
  };
  new Function('window','db','doc','runTransaction','deleteField','serverTimestamp','isAdmin','showToast', discard + '\n' + grant)(
    w, db, (_, ...parts) => parts.join('/'), transaction, () => del, () => 'server-time', () => true, () => {});
  return { w, db, store };
}
for (const gender of ['여성', '남성']) {
  const { w, store } = harness(gender);
  await Promise.all([w._faceDiscardTx('alice','one','appeal',{ reasons:['quality'],text:'' }),
    w._faceDiscardTx('alice','one','appeal',{ reasons:['quality'],text:'' })]);
  assert.equal(store['users/alice'].character.body, gender === '여성' ? 'human_f' : 'human');
  assert.equal(store['users/alice'].character.skin, 't2');
  assert.equal(store['users/alice'].faceTickets, 2, '폐기만으로 이용권을 환불한다');
  assert(!store['users/alice/faceChars/one']); assert(!('characterSheet' in store['users/alice']));
  assert.equal(store['faceAppeals/alice_one'].status, 'open');
  await Promise.all([w.faceAdminAppealDone('alice_one','alice',true), w.faceAdminAppealDone('alice_one','alice',true)]);
  assert.equal(store['users/alice'].faceTickets, 3, '중복 처리로 이용권이 두 번 지급된다');
  assert.equal(store['faceAppeals/alice_one'].status, 'granted');
}
{
  const { w, db, store } = harness(); const before = structuredClone(store); db.fail = true;
  await assert.rejects(w._faceDiscardTx('alice','one','appeal',{reasons:['quality'],text:''}));
  assert.deepEqual(store, before, '트랜잭션 실패 후 일부 데이터만 삭제됐다');
}
{
  const { w, store } = harness('여성',false); const before = structuredClone(store['users/alice']);
  await w._faceDiscardTx('alice','one','remake',{reasons:['style'],text:''});
  assert.deepEqual(store['users/alice'], before, '착용하지 않은 커마 삭제가 현재 옷을 바꿨다');
  await w.faceAdminAppealDone('alice_one','alice',true);
  assert.equal(store['users/alice'].faceTickets, 2, '단순 재제작 설문을 환불 처리했다');
}
{
  const { w, store } = harness(); await w._faceDiscardTx('alice','one','appeal',{reasons:['quality'],text:''});
  await w.faceAdminAppealDone('alice_one','bob',true);
  assert.equal(store['users/alice'].faceTickets,2); assert.equal(store['faceAppeals/alice_one'].status,'open');
}
console.log('OK face-discard: 원자적 폐기/착용해제·실패 롤백·중복/다른 대상 환불 차단');
