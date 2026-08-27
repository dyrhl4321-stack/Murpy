// 캐릭터 겹 순서를 **손으로 적은 배열**이 남아 있는지 찾는다.
//
// 왜 필요한가: 순서를 적은 사본이 여섯 곳이었고, 그중 하나가 overShoes(버뮤다 밑단이
// 신발 목을 덮는 규칙)를 빠뜨릴 때마다 그 화면에서만 신발이 바지 위로 올라왔다.
// 8-10 미리보기 · 8-26 홈 인기 카드/방 썸네일 · 8-27 머피캠 — 같은 사고가 세 번 났다.
// 정답은 window._charLayerOrder(cfg) 하나로 물어보는 것이다.
import fs from 'fs';
const src = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const lines = src.split('\n');
const re = /\[\s*'body'\s*,\s*'bottom'\s*,\s*'shoes'\s*,\s*'top'/;
const bad = [];
lines.forEach((l, i) => {
  if (!re.test(l)) return;
  // 허용: 상수 정의 자체와, 헬퍼가 없을 때를 위한 폴백(_charLayerOrder 를 같이 부르는 줄)
  if (l.includes('_CHAR_LAYER_ORDER =')) return;
  if (l.includes('_charLayerOrder')) return;
  const prev = (lines[i - 1] || '');
  if (prev.includes('_charLayerOrder')) return;
  bad.push((i + 1) + ': ' + l.trim().slice(0, 100));
});
if (bad.length) {
  console.error('겹 순서를 손으로 적은 곳이 남아 있다 — window._charLayerOrder(cfg) 를 쓸 것:');
  bad.forEach(b => console.error('  ' + b));
  process.exit(1);
}
console.log('OK 겹 순서 사본 없음');
