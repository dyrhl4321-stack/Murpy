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
  // ★10-28 대표 10:49 실사용: AI 가 날짜를 '10.28'(점)로 돌려줘 정모 2개가 모두 '날짜 못 읽음'으로 버려졌다(우리는 '10-28' 만 받았다).
  //   → 구분자(- . / 월일)·괄호 요일·'오후 4:00'·'4시'까지 받는다. 프롬프트도 YYYY-MM-DD / MM-DD 로 다시 못 박았다.
  const ds = String(date || "").trim().replace(/\s+/g, "").replace(/\(.*?\)/g, "").replace(/[월.\/]/g, "-").replace(/일$/, "").replace(/-+$/, "");
  const d = ds.match(/^(?:(\d{4})-)?(\d{1,2})-(\d{1,2})$/);
  const ts = String(time || "").trim().replace(/\s+/g, ""), pm = /오후|PM|pm/.test(ts), am = /오전|AM|am/.test(ts);
  const t = ts.match(/(\d{1,2})(?::(\d{2})|시(?:(\d{1,2})분?)?)/);
  if (!d || !t) return null;
  let hh = +t[1]; const mi = +(t[2] || t[3] || 0);
  if (pm && hh < 12) hh += 12; if (am && hh === 12) hh = 0;
  const mo = +d[2], da = +d[3];
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

// ★10-28 대표: 참가비 = 소모임처럼 글도 받는다('용마>아차>두부?굴?', '전화 예약 필수', 이모티콘).
//   숫자만 있으면(10000 · 10,000 · 10,000원) feeAmount(금액 — 입금 체크·출첵앱 공금이 쓴다), 그 밖의 글은 feeText 에 그대로(금액 계산엔 안 씀).
//   비어 있으면 둘 다 비운다(feeAmount 0 · feeText ''). index.html window._sqFeeParse 와 같은 규칙.
function feeParse(text) {
  const t = String(text || "").trim().slice(0, 40);
  if (!t) return { feeAmount: 0, feeText: "" };
  const m = t.replace(/\s+/g, "").match(/^(\d{1,3}(?:,\d{3})+|\d+)원?$/);
  if (m) { const n = +m[1].replace(/,/g, ""); if (n <= 10000000) return { feeAmount: n, feeText: "" }; }
  return { feeAmount: 0, feeText: t };
}

// AI 응답(JSON 글) → { screen, meetings:[{title,startMs,place,cost,cap,joined,type,photoBox,names[]}], dropped:[{title,why}], cutTop, cutBottom }. 이상하면 null.
//   ★10-28 대표 첫 실사용: 정모 3개 중 1개가 조용히 빠졌다 → 못 올린 정모는 이유와 함께 돌려준다(잘린 카드 · 날짜·시각 못 읽음).
function parseCapture(text, nowMs) {
  let o; try { o = JSON.parse(String(text || "")); } catch (e) { return null; }
  if (!o || typeof o !== "object") return null;
  const screen = ["list", "attendees", "detail", "other"].includes(o.screen) ? o.screen : "other";
  const box = (b) => Array.isArray(b) && b.length === 4 && b.every((x) => Number.isFinite(x) && x >= 0 && x <= 1000) && b[2] - b[0] > 30 && b[3] - b[1] > 30 ? b.map(Math.round) : null;
  const all = (Array.isArray(o.meetings) ? o.meetings : []).slice(0, 12).map((m) => {
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
  });
  const meetings = all.filter((m) => m.startMs);   // 날짜·시각을 못 읽은 정모는 만들지 않는다(틀린 스쿼드보다 안 만드는 게 낫다) — 대신 이유를 남긴다
  const dropped = all.filter((m) => !m.startMs).map((m) => ({ title: m.title, why: "날짜·시각을 못 읽었어요" }));
  const cnt = (v) => (Number.isInteger(v) && v > 0 && v < 10 ? v : 0);
  return { screen, meetings, dropped, cutTop: cnt(o.cutTop), cutBottom: cnt(o.cutBottom) };
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
  if (m.cost && m.cost !== cur.smoCost) Object.assign(out, { smoCost: m.cost }, feeParse(m.cost));
  return out;
}

module.exports = { TYPES, WDS, wdOf, startMs, titleKey, smoId, feeParse, parseCapture, matchNames, mergeInto };
