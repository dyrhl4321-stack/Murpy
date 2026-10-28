// ★10-27 소모임 캡처 → 근방단 스쿼드 — 순수 로직(시험: test/gbdcapture_logic.test.js)
//   AI 결과 다듬기 · 날짜(연도 없는 '10.31')를 한국 시각 ms 로 · 스쿼드 id · 이름 맞추기 · 비용 숫자 · 같은 정모 합치기.
const G = require("./gbdsync_logic.js");
const crypto = require("crypto");

const TYPES = ["gym", "running", "golf", "tennis", "climbing", "hyrox", "hiking", "yoga", "dance"];   // index.html SQUAD_TYPES 와 같게
const KST = 9 * 3600 * 1000;

// 'YYYY-MM-DD' 또는 'MM-DD' + 'HH:MM' → 한국 시각 ms. 연도가 없으면 오늘에서 가까운 쪽(30일 넘게 지난 날짜면 내년).
//   wd = 캡처에 찍힌 요일 글자('토') — 연도가 없으면 그 요일이 맞는 해를 먼저 고른다. 요일은 늘 날짜로 계산해 보여 준다(AI 글자를 쓰지 않는다).
const WDS = ["일", "월", "화", "수", "목", "금", "토"];
const wdOf = (ms) => WDS[new Date(ms + KST).getUTCDay()];
function startMs(date, time, nowMs, wd) {
  const d = String(date || "").match(/^(?:(\d{4})-)?(\d{1,2})-(\d{1,2})$/), t = String(time || "").match(/^(\d{1,2}):(\d{2})$/);
  if (!d || !t) return null;
  const mo = +d[2], da = +d[3], hh = +t[1], mi = +t[2];
  if (mo < 1 || mo > 12 || da < 1 || da > 31 || hh > 23 || mi > 59) return null;
  const at = (y) => Date.UTC(y, mo - 1, da, hh, mi) - KST;
  if (d[1]) return at(+d[1]);
  const y0 = new Date(nowMs + KST).getUTCFullYear();
  let ms = at(y0);
  if (ms < nowMs - 30 * 86400000) ms = at(y0 + 1);
  if (wd && WDS.includes(wd) && wdOf(ms) !== wd) {   // 찍힌 요일과 맞는 해(1년 안쪽)가 있으면 그쪽
    const alt = [at(y0 + 1), at(y0), at(y0 - 1)].find((x) => wdOf(x) === wd && x >= nowMs - 200 * 86400000 && x <= nowMs + 330 * 86400000);
    if (alt) ms = alt;
  }
  return ms;
}

// 같은 정모 = 제목(띄어쓰기·기호 무시) + 시작 시각. 문서 id 로 박아 두 번 보내도 하나만 생긴다(정기반 cls_ 와 같은 방식).
const titleKey = (s) => G.nrm(s).replace(/[^0-9a-z가-힣]/g, "");
const smoId = (title, ms) => "smo_" + crypto.createHash("sha1").update(titleKey(title) + "|" + ms).digest("hex").slice(0, 16);

// 비용 글자에서 원 단위 숫자만(없으면 0). '1만원'·'10,000원'·'5천원' 정도만 — 나머지('전화 예약 필수')는 0 이고 글은 메모로 남긴다.
function feeOf(text) {
  const s = String(text || "").replace(/\s+/g, "");
  let m = s.match(/(\d+(?:\.\d+)?)만(\d+)?천?원?/); if (m) return Math.round(+m[1] * 10000 + (m[2] ? +m[2] * 1000 : 0));
  m = s.match(/(\d+)천원/); if (m) return +m[1] * 1000;
  m = s.match(/(\d{1,3}(?:,\d{3})+|\d{3,})원/); if (m) return +m[1].replace(/,/g, "");
  return 0;
}

// AI 응답(JSON 글) → { screen, meetings:[{title,startMs,place,cost,cap,joined,type,photoBox,names[]}] }. 이상하면 null.
function parseCapture(text, nowMs) {
  let o; try { o = JSON.parse(String(text || "")); } catch (e) { return null; }
  if (!o || typeof o !== "object") return null;
  const screen = ["list", "attendees", "detail", "other"].includes(o.screen) ? o.screen : "other";
  const box = (b) => Array.isArray(b) && b.length === 4 && b.every((x) => Number.isFinite(x) && x >= 0 && x <= 1000) && b[2] - b[0] > 30 && b[3] - b[1] > 30 ? b.map(Math.round) : null;
  const meetings = (Array.isArray(o.meetings) ? o.meetings : []).slice(0, 12).map((m) => {
    const names = (Array.isArray(m && m.attendees) ? m.attendees : []).map((x) => String(x || "").trim().slice(0, 30)).filter(Boolean);
    const wd = WDS.includes(m && m.weekday) ? m.weekday : "", st = startMs(m && m.date, m && m.time, nowMs, wd);
    return {
      title: String((m && m.title) || "").trim().slice(0, 40),
      startMs: st,
      dateCheck: !!(st && wd && wdOf(st) !== wd),   // 찍힌 요일과 계산한 요일이 다르다 = 날짜를 잘못 읽었을 수 있다
      place: String((m && m.place) || "").trim().slice(0, 40),
      cost: String((m && m.cost) || "").trim().slice(0, 40),
      cap: Number.isInteger(m && m.capacity) && m.capacity > 0 && m.capacity <= 300 ? m.capacity : null,
      joined: Number.isInteger(m && m.joined) && m.joined >= 0 && m.joined <= 300 ? m.joined : null,
      type: TYPES.includes(m && m.type) ? m.type : "gym",   // 모르면 헬스(대표 10-27)
      photoBox: box(m && m.photoBox),
      names: Array.from(new Set(names)).slice(0, 100),
    };
  }).filter((m) => m.startMs);   // 날짜·시각을 못 읽은 정모는 만들지 않는다(틀린 스쿼드보다 안 만드는 게 낫다)
  return { screen, meetings };
}

// 소모임 이름 → 근방단 명부 → 머피 계정. 실명·소모임 닉네임(년도 접두 '92김준성' 무시) 중 하나와 정확히 같고, 명부에서 하나뿐일 때만.
//   → [{ name, uid|null, gbd|null }]  (uid 없음 = 회색 이름만, 정원 계산엔 넣는다)
function matchNames(names, gbdList) {
  const live = (gbdList || []).filter((g) => g && g.status !== "removed");
  return names.map((name) => {
    const k = G.core(name); if (!k) return { name, uid: null, gbd: null };
    const hit = live.filter((g) => G.core(g.name) === k || (g.nickname && G.core(g.nickname) === k));
    const g = hit.length === 1 ? hit[0] : null;
    return { name, uid: (g && g.murpyUid) || null, gbd: g ? g.name : null };
  });
}

// 같은 정모를 이미 올렸으면 고친다 — 사람은 더하기만(빼지 않는다), 장소·정원·비용은 새 값이 있을 때만.
function mergeInto(cur, m) {
  const out = {};
  if (m.place && m.place !== cur.location) out.location = m.place;
  if (m.cap && m.cap !== cur.capacity) out.capacity = m.cap;
  if (m.cost && m.cost !== cur.smoCost) { out.smoCost = m.cost; out.feeAmount = feeOf(m.cost); }
  return out;
}

module.exports = { TYPES, WDS, wdOf, startMs, titleKey, smoId, feeOf, parseCapture, matchNames, mergeInto };
