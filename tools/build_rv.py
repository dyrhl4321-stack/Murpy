# -*- coding: utf-8 -*-
"""murpy.app/rv/audio-0904.html 을 **통째로** 만든다 (부분 치환 금지 — 9-04에 중첩 사고).
   오디오는 rv/a/*.mp3 상대경로. 고르면 RTDB rv/audio-0904/<슬롯> 에 자동 기록."""
import io, os, html

REPO = r"C:/Users/dyrhl/Murpy"
OUT = REPO + "/rv"
E = html.escape
AV = "3"   # 오디오 캐시버스터 — 음원을 다시 뽑으면 올린다

BGM = [
    # (id, 제목, 작곡/분위기, 내려받음, 파일, 현재적용?)
    ("C0", "지금까지 쓰던 곡", "Destin715 · 플루트·하프 / 잔잔", "160회", "bg_c0_current_calmtown.mp3", False),
    ("C1", "A New Town", "cynicmusic · 하프 솔로 / 고풍", "1,958회", "bg_c1_newtown_harp.mp3", False),
    ("C2", "Town 3", "Alex McCulloch · 클래식 기타 / 따뜻", "468회", "bg_c2_town3_guitar.mp3", True),
    ("C3", "Good Morning", "Cakeflaps · 밝은 소품 / 아침", "337회", "bg_c3_goodmorning.mp3", False),
    ("C4", "TOWN 1", "Geomancer · 정통 JRPG 마을", "224회", "bg_c4_town1_geomancer.mp3", False),
    ("C5", "TOWN 2", "Geomancer · JRPG 마을 / 더 조용", "199회", "bg_c5_town2_geomancer.mp3", False),
    ("C6", "Aug 1 Guitar", "Alex McCulloch · 클린 기타 / 재즈풍", "15회", "bg_c6_aug1_guitar.mp3", False),
    ("C7", "Aug 2 Guitar", "Alex McCulloch · 클린 기타 / 느긋", "5회", "bg_c7_aug2_guitar.mp3", False),
    ("C8", "Aug 3 Guitar", "Alex McCulloch · 클린 기타 / 산책", "6회", "bg_c8_aug3_guitar.mp3", False),
]

NPC = [
    {"name": "관리인 박씨", "age": "50대 후반 · 공원 관리인", "picked": "B",
     "quest": "공원 온 김에 운동 도장도 찍어야지. 근처 헬스장에서 체크인하고 오게!",
     "line": "어서 오게, 우리 공원 좋지?",
     "cands": [("A", "Charon", "3.1 Flash TTS", "keeper_A_charon_31flash.mp3", ""),
               ("B", "Charon", "2.5 Pro TTS", "keeper_B_charon_25pro.mp3", "")]},
    {"name": "강 코치", "age": "20대 후반 · 트레이너", "picked": "",
     "quest": "오늘 운동 인증 아직이지? 피드에 인증샷 한 장 올리고 와!",
     "line": "오! 운동하러 왔구나?",
     "note": "B가 “왓구아”로 뭉개진다는 지적 → 같은 Puck 목소리에 받침을 닫으라는 지시를 강화해 세 번 다시 뽑았습니다. B1~B3 중에 골라주세요.",
     "cands": [("B1", "Puck", "2.5 Pro TTS · 받침 강화", "trainer_B1_puck_fix.mp3", "교정"),
               ("B2", "Puck", "2.5 Pro TTS · 받침 강화", "trainer_B2_puck_fix.mp3", "교정"),
               ("B3", "Puck", "2.5 Pro TTS · 받침 강화", "trainer_B3_puck_fix.mp3", "교정"),
               ("A", "Zephyr", "3.1 Flash TTS", "trainer_A_zephyr.mp3", ""),
               ("B", "Puck", "2.5 Pro TTS · 원본", "trainer_B_puck_25pro.mp3", ""),
               ("C", "Fenrir", "3.1 Flash TTS", "trainer_C_fenrir.mp3", "")]},
    {"name": "순이 할매", "age": "70대 · 동네 어르신", "picked": "D",
     "quest": "속에 담아둔 얘기 있으면 대나무숲에 살짝 적어보게.",
     "line": "아이고, 젊은이 왔는가.",
     "cands": [("B", "Kore", "2.5 Pro TTS", "grandma_B_kore_25pro.mp3", ""),
               ("C", "Aoede", "2.5 Pro TTS", "grandma_C_aoede_25pro.mp3", ""),
               ("D", "Sulafat", "2.5 Pro TTS", "grandma_D_sulafat_25pro.mp3", "")]},
    {"name": "민준이", "age": "6살 · 놀이터 꼬마", "picked": "B",
     "quest": "오늘의 머피들 봤어? 매칭 탭에서 새 친구 구경하고 와!",
     "line": "형아! 누나! 나랑 놀자!",
     "cands": [("B", "Leda", "2.5 Pro TTS", "kid_B_leda_25pro.mp3", ""),
               ("C", "Zephyr", "2.5 Pro TTS", "kid_C_zephyr_25pro.mp3", ""),
               ("D", "Autonoe", "2.5 Pro TTS", "kid_D_autonoe_25pro.mp3", "")]},
]


# ★대표가 목소리를 고른 뒤 뽑은 **실제 게임 대사 전문**(승인 전 앱 배포 금지 — 오디오 표준)
LINES = [
    ("관리인 박씨", "Charon", [
        ("처음 만났을 때", "어서 오게. 우리 동네 공원, 마음에 드는가? 공원 온 김에 운동 도장도 찍어야지. 근처 헬스장에서 체크인하고 오게!", "line_keeper_hi.mp3"),
        ("퀘스트 완료", "오, 도장 찍고 왔구먼! 부지런한 게 최고야.", "line_keeper_done.mp3"),
        ("보상까지 받은 뒤", "오늘 부탁은 다 끝났네. 내일 또 들르라고!", "line_keeper_idle.mp3")]),
    ("강 코치", "Puck (B1 교정본과 같은 세팅)", [
        ("처음 만났을 때", "오! 운동하러 왔구나? 오늘 운동 인증 아직이지? 피드에 인증샷 한 장 올리고 와!", "line_trainer_hi.mp3"),
        ("퀘스트 완료", "그래, 그 기세야! 꾸준한 놈이 이긴다.", "line_trainer_done.mp3"),
        ("보상까지 받은 뒤", "오늘은 여기까지! 내일 또 보자고.", "line_trainer_idle.mp3")]),
    ("순이 할매", "Sulafat", [
        ("처음 만났을 때", "아이고, 젊은이 왔는가. 속에 담아둔 얘기 있으면 대나무숲에 살짝 적어보게. 속이 후련해져.", "line_grandma_hi.mp3"),
        ("퀘스트 완료", "잘했네. 마음도 근육처럼 풀어줘야 해.", "line_grandma_done.mp3"),
        ("보상까지 받은 뒤", "오늘 할 일은 다 했네. 살펴 가시게.", "line_grandma_idle.mp3")]),
    ("민준이", "Leda", [
        ("처음 만났을 때", "형아! 누나! 나랑 놀자! 오늘의 머피들 봤어? 매칭 탭에서 새 친구 구경하고 와!", "line_kid_hi.mp3"),
        ("퀘스트 완료", "우와, 친구 많아지겠다!", "line_kid_done.mp3"),
        ("보상까지 받은 뒤", "내일 또 놀러 와! 약속!", "line_kid_idle.mp3")]),
]


def row(slot, cid, main, sub, meta, src, tag="", pick=True):
    badge = ' <b class="tag">%s</b>' % E(tag) if tag else ''
    pickbtn = '<button class="pick" type="button">고르기</button>' if pick else ''
    return ('<div class="row" data-slot="%s" data-cid="%s">'
            '<button class="play" type="button" aria-label="%s 재생" data-src="a/%s?v=' + AV + '">'
            '<span class="ico-play"></span><span class="ico-pause"></span></button>'
            '<div class="info"><div class="ttl">%s%s</div><div class="sub">%s</div>'
            '<div class="bar"><i></i></div></div>'
            '<div class="meta">%s</div>%s'
            '</div>') % (E(slot), E(cid), E(main), E(src), E(main), badge, E(sub), E(meta), pickbtn)


bgm_html = "".join(
    row("브금", b[0], b[0] + " · " + b[1], b[2], "내려받음 " + b[3], b[4], "적용중" if b[5] else "")
    for b in BGM)

npc_html = []
for n in NPC:
    note = '<p class="note">%s</p>' % E(n["note"]) if n.get("note") else ''
    done = '<span class="done">선택 완료 · %s</span>' % E(n["picked"]) if n.get("picked") else ''
    rows = "".join(row(n["name"], c[0], c[0] + " · " + c[1], c[2], "", c[3], c[4]) for c in n["cands"])
    npc_html.append(
        '<section class="npc">'
        '<header class="nhd"><h3>%s</h3><span class="age">%s</span>%s</header>'
        '<p class="quest"><span class="qlab">퀘스트</span>%s</p>'
        '<p class="line">&ldquo;%s&rdquo;</p>%s'
        '<div class="rows">%s</div>'
        '</section>' % (E(n["name"]), E(n["age"]), done, E(n["quest"]), E(n["line"]), note, rows))

lines_html = []
for who, voice, items in LINES:
    rows = "".join(
        row(who + " 대사", str(i), it[0], it[1], "", it[2], pick=False)
        for i, it in enumerate(items))
    lines_html.append(
        '<section class="npc"><header class="nhd"><h3>%s</h3><span class="age">%s</span></header>'
        '<div class="rows">%s</div></section>' % (E(who), E(voice), rows))

DOC = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#0B0F19">
<title>머피 오디오 검수실</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Jua&family=Noto+Sans+KR:wght@400;500;700&display=swap">
<style>
:root{
  --ground:#0B0F19; --panel:#141A29; --panel2:#1A2133; --line:#2B3350;
  --ink:#E8EDF7; --ink2:#98A1B8; --ink3:#5C6683;
  --gold:#F5C24B; --gold-dim:#8A6A25; --blue:#4C86FF;
  --shadow:0 0 0 2px var(--line);
}
*{box-sizing:border-box}
body{margin:0;background:var(--ground);color:var(--ink);
  font-family:'Noto Sans KR',-apple-system,BlinkMacSystemFont,'Malgun Gothic',sans-serif;
  font-size:15px;line-height:1.6;-webkit-text-size-adjust:100%;padding-bottom:120px}
.wrap{max-width:620px;margin:0 auto;padding:26px 16px 0}
h1{font-family:'Jua',sans-serif;font-weight:400;font-size:27px;margin:0 0 7px;letter-spacing:.5px}
.lede{color:var(--ink2);font-size:13.5px;margin:0;max-width:52ch}
.lede b{color:var(--ink)}
.howto{margin:16px 0 30px;padding:11px 13px;background:var(--panel);border-left:3px solid var(--gold);
  font-size:12.5px;color:var(--ink2);line-height:1.7}
.howto b{color:var(--gold)}
h2{font-family:'Jua',sans-serif;font-weight:400;font-size:20px;margin:34px 0 3px;letter-spacing:.4px}
.h2note{color:var(--ink3);font-size:12.5px;margin:0 0 14px}
.h2note b{color:var(--gold)}
.rows{display:flex;flex-direction:column;gap:7px}
.row{display:grid;grid-template-columns:auto 1fr auto auto;align-items:center;gap:11px;
  background:var(--panel);box-shadow:var(--shadow);padding:10px 11px;transition:background .15s,box-shadow .15s}
.row.sel{background:var(--panel2);box-shadow:0 0 0 2px var(--gold)}
.play{width:42px;height:42px;background:var(--panel2);border:2px solid var(--line);
  color:var(--ink);cursor:pointer;display:grid;place-items:center;padding:0;transition:border-color .15s,background .15s}
.play:hover{border-color:var(--blue)}
.play:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.row.playing .play{background:var(--blue);border-color:var(--blue)}
.ico-play{width:0;height:0;border-left:11px solid currentColor;border-top:7px solid transparent;border-bottom:7px solid transparent;margin-left:3px}
.ico-pause{display:none;width:11px;height:13px;border-left:4px solid currentColor;border-right:4px solid currentColor}
.row.playing .ico-play{display:none}
.row.playing .ico-pause{display:block}
.info{min-width:0}
.ttl{font-size:14px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ttl .tag{font-size:10px;font-weight:700;color:var(--gold);border:1px solid var(--gold-dim);
  padding:0 5px;margin-left:6px;vertical-align:2px}
.sub{font-size:11.5px;color:var(--ink2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar{height:2px;background:var(--line);margin-top:7px;overflow:hidden}
.bar i{display:block;height:100%;width:0;background:var(--blue)}
.meta{font-size:11px;color:var(--ink3);font-variant-numeric:tabular-nums;white-space:nowrap}
.pick{background:none;border:1px solid var(--line);color:var(--ink2);font-family:inherit;font-size:12px;
  padding:8px 11px;cursor:pointer;white-space:nowrap;transition:border-color .15s,color .15s,background .15s}
.pick:hover{border-color:var(--gold);color:var(--gold)}
.pick:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.row.sel .pick{background:var(--gold);border-color:var(--gold);color:#171203;font-weight:700}
.npc{margin:22px 0 0;padding:15px 14px 14px;background:rgba(20,26,41,.55);box-shadow:var(--shadow)}
.nhd{display:flex;align-items:baseline;gap:9px;flex-wrap:wrap;margin-bottom:7px}
.nhd h3{font-family:'Jua',sans-serif;font-weight:400;font-size:18px;margin:0;letter-spacing:.3px}
.age{font-size:11.5px;color:var(--ink3)}
.done{font-size:11px;color:var(--gold);border:1px solid var(--gold-dim);padding:1px 6px;margin-left:auto}
.quest{font-size:12.5px;color:var(--ink2);margin:0 0 8px;line-height:1.65}
.qlab{font-size:10px;color:var(--gold);border:1px solid var(--gold-dim);padding:0 5px;margin-right:7px;vertical-align:1px}
.line{font-family:'Jua',sans-serif;font-size:15.5px;color:var(--ink);margin:0 0 12px;letter-spacing:.3px}
.note{font-size:12px;color:var(--gold);margin:0 0 11px;line-height:1.65;padding-left:9px;border-left:2px solid var(--gold-dim)}
.okbox{margin:26px 0 0;padding:16px 15px;background:var(--panel);box-shadow:var(--shadow);
  display:flex;flex-direction:column;gap:9px}
.ok{background:var(--gold);border:none;color:#171203;font-family:inherit;font-weight:700;font-size:14px;
  padding:14px;cursor:pointer}
.ng{background:none;border:1px solid var(--line);color:var(--ink2);font-family:inherit;font-size:12.5px;
  padding:11px;cursor:pointer}
.ok:focus-visible,.ng:focus-visible{outline:2px solid var(--blue);outline-offset:2px}
.okmsg{font-size:12.5px;color:var(--gold);min-height:1.4em;line-height:1.5}
.tail{margin:40px 0 0;padding:16px 0 30px;border-top:1px solid var(--line);color:var(--ink3);font-size:12.5px;line-height:1.85}
.tail b{color:var(--ink2)}
.dock{position:fixed;left:0;right:0;bottom:0;background:rgba(11,15,25,.96);border-top:1px solid var(--line);
  padding:10px 16px calc(12px + env(safe-area-inset-bottom))}
.dock-in{max-width:620px;margin:0 auto;display:flex;align-items:center;gap:12px}
.picks{flex:1;min-width:0;font-size:12px;color:var(--ink2);line-height:1.55}
.picks span{color:var(--ink3)}
.picks b{color:var(--gold);font-weight:700}
.copy{background:var(--blue);border:none;color:#fff;font-family:inherit;font-weight:700;font-size:13px;
  padding:12px 15px;cursor:pointer}
.copy:disabled{background:var(--panel2);color:var(--ink3);cursor:default}
.copy:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
@media (prefers-reduced-motion:reduce){*{transition:none!important}}
@media (max-width:430px){
  .row{grid-template-columns:auto 1fr auto;gap:9px}
  .meta{display:none}
}
</style>
</head>
<body>
<div class="wrap">
  <h1>머피 오디오 검수실</h1>
  <p class="lede">우리 동네 공원에 깔 <b>브금</b>과 공원 NPC 네 명의 <b>목소리</b>입니다. 전부 CC0(퍼블릭 도메인)이거나 우리가 직접 뽑은 음성이라 저작권 걸릴 게 없습니다.</p>
  <div class="howto">이어폰 끼고 들어보시고 마음에 드는 것 옆의 <b>고르기</b>만 누르세요. 누르는 순간 저한테 바로 넘어옵니다 &mdash; 복사도 타이핑도 안 하셔도 됩니다.</div>

  <h2>공원 브금</h2>
  <p class="h2note">각 45초 미리듣기 · <b>C6~C8은 C2와 같은 작곡가의 기타 곡</b> · 내려받음이 적을수록 남들이 안 쓴 곡</p>
  <div class="rows">__BGM__</div>

  <h2>NPC 목소리</h2>
  <p class="h2note">고른 목소리로 그 캐릭터의 모든 대사를 같은 화자·같은 마이크 세팅으로 다시 뽑습니다</p>
  __NPC__

  <h2>게임에 넣을 대사 전문</h2>
  <p class="h2note">대표님이 고르신 목소리로 뽑은 <b>실제 대사 12개</b>입니다 · 들어보시고 아래 버튼만 눌러주세요</p>
  __LINES__

  <div class="okbox">
    <button class="ok" id="okall" type="button">전부 좋아요 &mdash; 앱에 넣어주세요</button>
    <button class="ng" id="okng" type="button">다시 뽑을 게 있어요</button>
    <div class="okmsg" id="okmsg"></div>
  </div>

  <div class="tail">
    <b>고르실 때 기준</b> &mdash; 브금은 오래 켜두는 화면에 깔립니다. 한 곡당 1분쯤 틀어두고 다른 일 하면서 거슬리는지 보시면 확실합니다. 목소리는 &ldquo;성우처럼 잘생겼나&rdquo;가 아니라 <b>동네에 진짜 있을 법한가</b>로 보시면 됩니다.<br><br>
    피치 조작(리샘플링)은 쓰지 않았습니다 &mdash; 원본 그대로 뽑고 앞뒤 무음만 정리했습니다. 최신 3.1 TTS는 쓸 수 있는 목소리가 제한적이라(여성·아이 목소리를 거부합니다) 할매와 민준이는 2.5 Pro TTS로 뽑았습니다.
  </div>
</div>

<div class="dock"><div class="dock-in">
  <div class="picks" id="picks"><span>아직 고른 게 없어요</span></div>
  <button class="copy" id="copy" type="button" disabled>선택 복사</button>
</div></div>

<script>
(function () {
  var RVDB = 'https://murpyprototype-default-rtdb.asia-southeast1.firebasedatabase.app/rv/audio-0904/';
  var cur = null, curRow = null, picks = {};
  try { picks = JSON.parse(localStorage.getItem('murpy_audio_picks') || '{}'); } catch (e) { picks = {}; }

  function stop() {
    if (cur) { try { cur.pause(); } catch (e) {} }
    if (curRow) {
      curRow.classList.remove('playing');
      var b = curRow.querySelector('.bar i'); if (b) b.style.width = '0';
    }
    cur = null; curRow = null;
  }

  var rows = Array.prototype.slice.call(document.querySelectorAll('.row'));
  rows.forEach(function (row) {
    try { bind(row); } catch (e) { console.warn('row bind', e); }   // 한 줄이 죽어도 나머지는 산다
  });
  function bind(row) {
    var btn = row.querySelector('.play'), bar = row.querySelector('.bar i');
    var slot = row.getAttribute('data-slot'), cid = row.getAttribute('data-cid');
    if (picks[slot] === cid) row.classList.add('sel');
    var au = null;
    btn.addEventListener('click', function (ev) {
      ev.stopPropagation();
      if (curRow === row) { stop(); return; }
      stop();
      if (!au) {
        au = new Audio(btn.getAttribute('data-src'));
        au.addEventListener('timeupdate', function () {
          if (au.duration) bar.style.width = (au.currentTime / au.duration * 100) + '%';
        });
        au.addEventListener('ended', function () { stop(); });
        au.addEventListener('error', function () {
          row.querySelector('.sub').textContent = '재생 실패 — 새로고침 후 다시 눌러보세요';
          stop();
        });
      }
      cur = au; curRow = row; row.classList.add('playing');
      var p = au.play(); if (p && p.catch) p.catch(function () { stop(); });
    });
    var pickBtn = row.querySelector('.pick');
    if (!pickBtn) return;   // ★대사 행에는 고르기 버튼이 없다 — 없는 걸 찾다 죽으면
                            //   그 아래 행들의 재생 연결이 통째로 끊긴다(9-04 사고)
    pickBtn.addEventListener('click', function (ev) {
      ev.stopPropagation();
      rows.forEach(function (r) { if (r.getAttribute('data-slot') === slot) r.classList.remove('sel'); });
      if (picks[slot] === cid) { delete picks[slot]; }
      else { picks[slot] = cid; row.classList.add('sel'); }
      try { localStorage.setItem('murpy_audio_picks', JSON.stringify(picks)); } catch (e) {}
      try {
        fetch(RVDB + encodeURIComponent(slot) + '.json',
              { method: 'PUT', body: JSON.stringify(picks[slot] || null) }).catch(function () {});
      } catch (e) {}
      render();
    });
  }

  function text() {
    var order = ['브금', '관리인 박씨', '강 코치', '순이 할매', '민준이'], out = [];
    order.forEach(function (k) { if (picks[k]) out.push(k + ' ' + picks[k]); });
    return out.join(', ');
  }
  function render() {
    var t = text(), el = document.getElementById('picks'), btn = document.getElementById('copy');
    if (!t) { el.innerHTML = '<span>아직 고른 게 없어요</span>'; btn.disabled = true; return; }
    el.textContent = '';
    var lab = document.createElement('span'); lab.textContent = '내 선택 ';
    var b = document.createElement('b'); b.textContent = t;
    el.appendChild(lab); el.appendChild(b);
    btn.disabled = false;
  }
  document.getElementById('copy').addEventListener('click', function () {
    var t = text(); if (!t) return;
    var msg = '오디오 골랐어 — ' + t;
    var btn = document.getElementById('copy');
    var done = function () { btn.textContent = '복사됨'; setTimeout(function () { btn.textContent = '선택 복사'; }, 1600); };
    var fallback = function () {
      var ta = document.createElement('textarea');
      ta.value = msg; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); done(); } catch (e) {}
      document.body.removeChild(ta);
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(msg).then(done, fallback);
    else fallback();
  });
  function verdict(v, msg) {
    try {
      fetch(RVDB + encodeURIComponent('대사확인') + '.json',
            { method: 'PUT', body: JSON.stringify(v) }).catch(function () {});
    } catch (e) {}
    document.getElementById('okmsg').textContent = msg;
  }
  document.getElementById('okall').addEventListener('click', function () {
    verdict('OK', '전달했습니다 — 바로 앱에 넣겠습니다.');
  });
  document.getElementById('okng').addEventListener('click', function () {
    verdict('NG', '전달했습니다 — 어느 대사가 이상했는지만 말씀해 주세요.');
  });
  render();
})();
</script>
</body>
</html>
"""

DOC = (DOC.replace("__BGM__", bgm_html)
          .replace("__NPC__", "".join(npc_html))
          .replace("__LINES__", "".join(lines_html)))
io.open(OUT + "/audio-0904.html", "w", encoding="utf-8", newline="\n").write(DOC)

# 무결성 자가검사 — 부분 치환 사고 재발 방지
n_rows = DOC.count('class="row"')
n_play = DOC.count('class="play"')
n_pick = DOC.count('class="pick"')
missing = [b[4] for b in BGM if not os.path.exists(OUT + "/a/" + b[4])]
for n in NPC:
    for c in n["cands"]:
        if not os.path.exists(OUT + "/a/" + c[3]):
            missing.append(c[3])
n_lines = sum(len(x[2]) for x in LINES)
print("rows=%d play=%d  (같아야 정상) / pick=%d (대사 %d개는 고르기 없음: %d + %d = %d)"
      % (n_rows, n_play, n_pick, n_lines, n_pick, n_lines, n_pick + n_lines))
assert n_rows == n_play == n_pick + n_lines, "행/버튼 개수 불일치 — 페이지가 깨졌다"

print("빠진 오디오 파일:", missing if missing else "없음")
print("bytes:", os.path.getsize(OUT + "/audio-0904.html"))
