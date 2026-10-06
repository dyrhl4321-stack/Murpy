// ─────────────────────────────────────────────────────────────────────────────
// ★10-06 스쿼드 → 근방단 출첵앱 자동 연동 — 계산만 하는 부분(입출력 없음, 테스트용으로 분리).
//   대표: "스쿼드 개설 이후 그냥 전부 다 연동이 되어야 한다" — 끝나고 옮기는 게 아니라 여는 순간부터.
//   근방단 앱 모임 문서: members[실명] + status[같은 순서]{attend,late,cancel,absent,pay}.
//   ★3갈래 합치기: 머피가 지난번에 보낸 값(murpySent)을 모임 문서에 같이 적어 두고,
//     머피 값이 그때와 달라졌을 때만 덮는다. 근방단 앱에서 손으로 고친 칸(QR 출석 등)은
//     머피 쪽 그 사람 상태가 다시 바뀌기 전까지 그대로 둔다.
// ─────────────────────────────────────────────────────────────────────────────
const FLAGS = ["attend", "late", "cancel", "absent", "pay"];
const BLANK = "00000";
const code = (st) => FLAGS.map((k) => (st && st[k] ? "1" : "0")).join("");
const decode = (c) => { const o = {}; FLAGS.forEach((k, i) => { o[k] = String(c || BLANK)[i] === "1"; }); return o; };

// 머피 스쿼드 멤버 문서 → 근방단 칸. 앱의 _sqCheckState·SQ2GBD 와 같은 규칙.
const SQ2GBD = { present: { attend: true }, late: { late: true }, cancel: { cancel: true }, absent: { absent: true } };
function checkState(m) {
  const t = m.checkinType;
  if (t === "late" || t === "cancel" || t === "absent" || t === "present") return t;
  return m.checkedIn ? "present" : "none";
}
// 명단에 들어갈 사람 = 실제 참여자. 나간 사람·초대만 받은 사람·승인 대기는 뺀다.
const OUT = { left: 1, invited: 1, pending: 1, waitlist: 1, rejected: 1 };
const isLive = (m) => !!m && !OUT[m.status];

// 시간은 한국 기준으로(서버는 UTC 로 돈다)
const KST = 9 * 3600 * 1000;
const p2 = (n) => String(n).padStart(2, "0");
function kstDate(ms) { const d = new Date(ms + KST); return d.getUTCFullYear() + "-" + p2(d.getUTCMonth() + 1) + "-" + p2(d.getUTCDate()); }
function kstTime(ms) { const d = new Date(ms + KST); return p2(d.getUTCHours()) + ":" + p2(d.getUTCMinutes()); }

// 스쿼드 → 모임 기본 정보
function squadMeta(s) {
  const at = Number(s.scheduledAt) || 0;
  return {
    date: kstDate(at), startTime: kstTime(at),
    gym: String(s.location || s.title || ""),
    fee: Math.max(0, Number(s.feeAmount) || 0),
    type: /정모/.test(String(s.title || "")) ? "jeongmo" : "beong",
  };
}

// 머피 쪽 현재 값: { 근방단실명: code }. nameOf = { murpyUid: 근방단실명 }.
//   같은 실명에 두 계정이 걸려 있으면(합치기 전 중복) 체크가 된 쪽을 쓴다.
function oursFromMembers(members, nameOf) {
  const out = {};
  Object.keys(members || {}).forEach((uid) => {
    const m = members[uid];
    const name = nameOf[uid];
    if (!name || !isLive(m)) return;
    const st = Object.assign({ pay: !!m.paid }, SQ2GBD[checkState(m)] || {});
    const c = code(st);
    if (!(name in out) || out[name] === BLANK) out[name] = c;
  });
  return out;
}

// 3갈래 합치기. prev = 근방단 모임 문서(없으면 null), ours = oursFromMembers, meta = squadMeta.
//   돌려주는 것 = 바꿀 칸만 담은 객체(없으면 null = 바꿀 게 없음).
function mergeMeeting(prev, ours, meta, sid) {
  const base = (prev && prev.murpySent) || {};
  const baseMeta = (prev && prev.murpyMeta) || {};
  const members = ((prev && prev.members) || []).slice();
  const status = members.map((_, i) => code(((prev && prev.status) || [])[i]));
  let changed = !prev;

  Object.keys(ours).forEach((name) => {
    const oc = ours[name], bc = base[name];
    const i = members.indexOf(name);
    if (i < 0) {
      // 근방단 앱에서 손으로 뺀 사람은 머피 값이 바뀌기 전까지 다시 넣지 않는다
      if (bc !== undefined && oc === bc) return;
      members.push(name); status.push(oc); changed = true;
      return;
    }
    if (oc === bc) return;                          // 머피 값 그대로 → 근방단 앱 쪽 값 존중
    if (bc === undefined && oc === BLANK && status[i] !== BLANK) return;   // 근방단 앱이 먼저 체크해 둔 사람을 빈칸으로 덮지 않는다
    if (status[i] !== oc) { status[i] = oc; changed = true; }
  });
  // 머피에서 빠진 사람(스쿼드 나감·짝 해제): 근방단 앱에서 손대지 않았을 때만 같이 뺀다
  Object.keys(base).forEach((name) => {
    if (name in ours) return;
    const i = members.indexOf(name);
    if (i >= 0 && status[i] === base[name]) { members.splice(i, 1); status.splice(i, 1); changed = true; }
  });

  const out = {};
  Object.keys(meta).forEach((k) => {
    if (!prev || (meta[k] !== baseMeta[k] && prev[k] !== meta[k])) { out[k] = meta[k]; changed = true; }
  });
  const sentSame = JSON.stringify(sortKeys(ours)) === JSON.stringify(sortKeys(base));
  const metaSame = JSON.stringify(sortKeys(meta)) === JSON.stringify(sortKeys(baseMeta));
  if (!changed && sentSame && metaSame && prev && prev.murpySquad === sid) return null;

  out.members = members;
  out.status = status.map(decode);
  out.murpySent = ours;
  out.murpyMeta = meta;
  out.murpySquad = sid;
  return out;
}
function sortKeys(o) { const r = {}; Object.keys(o || {}).sort().forEach((k) => { r[k] = o[k]; }); return r; }

// 스쿼드가 취소·삭제됐을 때 근방단 모임을 지워도 되나 = 근방단 앱에서 아무도 손대지 않았나
function untouched(prev) {
  if (!prev) return false;
  const base = prev.murpySent || {};
  const members = prev.members || [];
  if ((prev.guests || []).length) return false;
  if (members.length !== Object.keys(base).length) return false;
  return members.every((n, i) => base[n] !== undefined && base[n] === code((prev.status || [])[i]));
}

module.exports = { FLAGS, BLANK, code, decode, checkState, isLive, kstDate, kstTime, squadMeta, oursFromMembers, mergeMeeting, untouched };
