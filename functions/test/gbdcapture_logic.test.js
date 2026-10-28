// 소모임 캡처 순수 로직 시험 — `cd functions && node --test test/gbdcapture_logic.test.js`
const test = require("node:test");
const assert = require("node:assert/strict");
const L = require("../gbdcapture_logic.js");
const NOW = Date.parse("2026-10-27T20:00:00+09:00");

test("startMs — 연도 없는 날짜는 가까운 쪽, 30일 넘게 지났으면 내년", () => {
  assert.equal(L.startMs("10-31", "15:00", NOW), Date.parse("2026-10-31T15:00:00+09:00"));
  assert.equal(L.startMs("11-6", "19:30", NOW), Date.parse("2026-11-06T19:30:00+09:00"));
  assert.equal(L.startMs("10-28", "16:00", NOW), Date.parse("2026-10-28T16:00:00+09:00"));
  assert.equal(L.startMs("01-03", "09:00", NOW), Date.parse("2027-01-03T09:00:00+09:00"));
  assert.equal(L.startMs("10-20", "09:00", NOW), Date.parse("2026-10-20T09:00:00+09:00"));   // 1주 전 = 올해(지난 정모)
  assert.equal(L.startMs("2026-12-24", "20:00", NOW), Date.parse("2026-12-24T20:00:00+09:00"));
  assert.equal(L.startMs("13-01", "09:00", NOW), null);
  assert.equal(L.startMs("10-31", "25:00", NOW), null);
  assert.equal(L.startMs(null, "15:00", NOW), null);
});

test("smoId — 제목 띄어쓰기·기호 무시, 시각이 다르면 다른 정모", () => {
  const t = Date.parse("2026-10-31T15:00:00+09:00");
  assert.equal(L.smoId("메이플스토리", t), L.smoId(" 메이플 스토리! ", t));
  assert.notEqual(L.smoId("메이플스토리", t), L.smoId("메이플스토리", t + 3600000));
  assert.match(L.smoId("x", t), /^smo_[0-9a-f]{16}$/);
});

test("feeOf — 원 단위만, 나머지 글은 0", () => {
  assert.equal(L.feeOf("1만원"), 10000);
  assert.equal(L.feeOf("1만5천원"), 15000);
  assert.equal(L.feeOf("10,000원"), 10000);
  assert.equal(L.feeOf("5천원"), 5000);
  assert.equal(L.feeOf("전화 예약 필수"), 0);
  assert.equal(L.feeOf("용마>아차>두부?굴?"), 0);
});

test("parseCapture — 날짜 못 읽은 정모 빼기 · 종목 모르면 헬스 · 상자 검사", () => {
  const r = L.parseCapture(JSON.stringify({ screen: "list", meetings: [
    { title: "메이플스토리", date: "10-31", time: "15:00", place: "용마산역 2출", cost: "용마>아차", capacity: 10, joined: 3, type: "hiking", photoBox: [300, 650, 400, 960], attendees: [] },
    { title: "하이록스 악귀 출몰", date: "11-06", time: "19:30", capacity: 6, joined: 3, type: "spaceship", photoBox: [1, 2, 3] },
    { title: "잘린 카드", date: null, time: "10:00" },
  ] }), NOW);
  assert.equal(r.meetings.length, 2);
  assert.equal(r.meetings[0].type, "hiking");
  assert.deepEqual(r.meetings[0].photoBox, [300, 650, 400, 960]);
  assert.equal(r.meetings[1].type, "gym");
  assert.equal(r.meetings[1].photoBox, null);
  assert.equal(L.parseCapture("not json", NOW), null);
  assert.equal(L.parseCapture(JSON.stringify({ screen: "chat", meetings: [] }), NOW).screen, "other");
});

test("matchNames — 실명·소모임 닉네임(년도 접두 무시), 하나뿐일 때만 계정", () => {
  const gbd = [
    { name: "김준성", nickname: "92김준성", murpyUid: "u1" },
    { name: "안효정", nickname: "효정", murpyUid: "" },
    { name: "임준규", nickname: "임준규", murpyUid: "u3" }, { name: "임준규", nickname: "88임준규", murpyUid: "u4" },
    { name: "탈퇴자", murpyUid: "u5", status: "removed" },
  ];
  const r = L.matchNames(["김준성", "효정", "임준규", "sss", "탈퇴자"], gbd);
  assert.deepEqual(r.map((x) => x.uid), ["u1", null, null, null, null]);
  assert.equal(r[1].gbd, "안효정");   // 명부엔 있지만 머피 계정 미연결 → 회색 이름
  assert.equal(r[2].gbd, null);        // 동명이인 = 고르지 않는다
});

test("mergeInto — 새 값만, 비용 바뀌면 숫자도", () => {
  assert.deepEqual(L.mergeInto({ location: "A", capacity: 10, smoCost: "" }, { place: "A", cap: 12, cost: "1만원" }), { capacity: 12, smoCost: "1만원", feeAmount: 10000 });
  assert.deepEqual(L.mergeInto({ location: "A", capacity: 10 }, { place: "", cap: null, cost: "" }), {});
});

test("요일 — 날짜로 계산 · 찍힌 요일로 해 고르기 · 다르면 dateCheck", () => {
  assert.equal(L.wdOf(Date.parse("2026-10-28T16:00:00+09:00")), "수");
  assert.equal(L.startMs("10-31", "15:00", NOW, "토"), Date.parse("2026-10-31T15:00:00+09:00"));      // 2026-10-31 = 토
  assert.equal(L.startMs("01-03", "09:00", NOW, "일"), Date.parse("2027-01-03T09:00:00+09:00"));      // 2027-01-03 = 일
  const r = L.parseCapture(JSON.stringify({ screen: "list", meetings: [
    { title: "a", date: "10-28", time: "16:00", weekday: "수" }, { title: "b", date: "10-28", time: "16:00", weekday: "화" }, { title: "c", date: "10-28", time: "16:00" } ] }), NOW);
  assert.deepEqual(r.meetings.map((m) => m.dateCheck), [false, true, false]);
});
