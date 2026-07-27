// 참조 사본 — index.html의 window.mwEvalHidden 와 '동일 로직'(로직 검증용).
// index.html 본체를 고치면 이 파일도 같이 맞춰야 테스트가 의미 있다.
export function evalHidden(checkins, now) {
  now = now || new Date();
  const out = [];
  const at = (k) => (k.at && k.at.toDate) ? k.at.toDate() : (k.at instanceof Date ? k.at : new Date());
  // 교주: 최근 8주(56일) 체크인 ≥6, 최다 요일 비중 ≥0.58
  const cut = new Date(now); cut.setDate(cut.getDate() - 56);
  const recent = checkins.filter(k => at(k) >= cut);
  if (recent.length >= 6) {
    const dow = [0, 0, 0, 0, 0, 0, 0];
    recent.forEach(k => dow[at(k).getDay()]++);
    let mi = 0; for (let i = 1; i < 7; i++) if (dow[i] > dow[mi]) mi = i;
    if (dow[mi] / recent.length >= 0.58) out.push({ id: 'cult', weekday: '일월화수목금토'[mi] });
  }
  // 소믈리에: 서로 다른 센터 ≥5
  if (new Set(checkins.map(k => String(k.centerId))).size >= 5) out.push({ id: 'somm' });
  // 좀비: day 오름차순, 가장 최근-직전 간격 ≥14일(복귀 순간)
  const days = checkins.map(k => k.day).filter(Boolean).sort();
  if (days.length >= 2) {
    const toD = (s) => new Date(+s.slice(0, 4), +s.slice(4, 6) - 1, +s.slice(6, 8));
    const gap = (toD(days[days.length - 1]) - toD(days[days.length - 2])) / 86400000;
    if (gap >= 14) out.push({ id: 'zombie' });
  }
  return out;
}
