# 머피월드 필드(맵) 아트 스펙 & 생성 프롬프트

머피월드 "무대"에 캐릭터가 서서 걸어다니는 **종목별 필드 배경**. 싸이월드 미니홈피 감성 +
캐릭터(탑다운 4방향)와 맞는 탑다운 시점. **모든 필드 = 같은 사이즈·같은 스타일/톤** 필수.

## 규격 (전 필드 공통)
- **크기**: 1024 × 1024 (정사각 1:1). 전부 동일 크기로 생성.
- **시점**: **정투상(orthographic) 똑바로 내려다본 탑다운** (포켓몬 GBA풍). 카메라 각도 전 필드 동일.
  ⚠️ **아이소메트릭/3-4 시점 금지 → 마름모(다이아몬드) 바닥 나옴.** 캐릭터가 정투상이라 필드도 정투상.
- **바닥**: **직사각형 바닥이 화면 전체를 꽉 채움**(edge-to-edge, 마름모 판 아님). 걸어다닐 **빈 바닥을
  가운데에 넓게** 두고, 가구·소품·벽·풍경은 **가장자리(테두리)** 로 배치(캐릭터 이동 공간 확보).
- **스케일(2026-07-07 갱신 — 캐릭터 확대 반영)**: 캐릭터를 ~1.5배 키우면서 화면 대비 **약 1/4 높이**가 됨.
  → 필드도 **더 줌인된 느낌**으로: 타일/가구 디테일을 **크게**(≈64px 타일감), 소품 개수는 줄이고 큼직하게.
  (구 스펙은 1/6·32~48px였음 — 이제 캐릭터가 커져서 배경도 같이 커져야 이질감 없음.)
- **스타일**: 진짜 픽셀아트, 하드 픽셀, **안티에일리어싱 없음**, 제한 팔레트(전 필드 공유),
  밝고 따뜻한 낮 조명(어둡지 않게 → 검은 스프라이트도 잘 읽힘), 아늑/노스탤직(미니홈피 감성).
- **금지**: 사람/캐릭터, 글자·텍스트, UI, 워터마크. 배경은 깔끔·플랫.

## 일관성 워크플로우 (핵심)
1. **집(home) 필드 먼저** 생성 → 마음에 들 때까지 반복해 "마스터 스타일" 확정.
2. 나머지 필드는 **집 이미지를 첨부**하고 "같은 스타일·각도·스케일·팔레트·조명 유지, 장소만 교체" 로 생성.
   → 캐릭터 4방향 때 쓴 것과 같은 방식(레퍼런스 고정)이라 톤·크기 안 튐.
3. 전부 1024×768로 저장. 파일명: field_home.png / field_gym.png / field_hangang.png / field_tennis.png / field_golf.png

## 베이스 프롬프트 (영문, 모델용 — 2026-07-07 갱신, 큰 캐릭터 스케일)
```
Top-down orthographic RPG map background, Pokemon GameBoy-Advance overworld style,
straight bird's-eye view, cozy nostalgic personal-space vibe.
IMPORTANT: NOT isometric, NO diamond/rhombus shape, no 3D perspective, no vanishing point.
The ground/floor is grid-aligned and FILLS THE ENTIRE RECTANGULAR FRAME edge to edge.
SCENE: <장소>.
Zoomed-in scale: chunky LARGE tiles (~64px feel), big readable furniture/props, few objects
(not a busy cluttered scene) — sized so a chibi character standing on it would be about
ONE QUARTER of the frame height. Keep a WIDE open walkable floor in the center
(absolutely no characters, no people); place the big props / furniture / scenery around the EDGES.
True pixel art, hard pixels, NO anti-aliasing, limited cohesive palette, bright warm daytime light.
No text, no letters, no UI, no watermark, clean. 1024x1024 square.
```

## 장소별 SCENE 문구
- **집 field_home**: `a cozy small studio room — wooden floor, a bed, a rug, a desk with a plant, a small window, a fitness poster on the wall`
- **헬스장 field_gym**: `an indoor gym floor — rubber flooring, a dumbbell rack, a weight bench, a mirror wall, treadmills along the edges`
- **한강 러닝존 field_hangang**: `a riverside running path — a wide river, green grass banks, a running track, benches, a bridge and a distant city skyline`
- **테니스존 field_tennis**: `an outdoor tennis court — green court with white lines, a net across, a surrounding fence, a bench and a ball basket at the side`
- **골프존 field_golf**: `a golf putting green / driving range — neat turf, a flag hole, driving mats, a few trees and hills in the distance`

## 레퍼런스 기반 프롬프트 (2번째부터, 집 이미지 첨부)
```
Attached is my field style reference. Keep the EXACT same pixel-art style, straight top-down
orthographic view (NOT isometric, NO diamond, floor fills the whole rectangular frame),
tile scale, color palette and lighting. Only change the LOCATION to: <장소 SCENE 문구>.
Keep the wide empty walkable floor in the center, props only around the edges.
Same 1024x1024 square, no characters, no text, no watermark.
```

## 코드 연결(예정)
- 필드는 `char/fields/<name>.png` 로 저장. 무대 배경 = 선택된 필드 이미지(캐릭터는 그 위에서 이동).
- 필드 전환 UI는 추후 '지도' 탭과 연결(집→헬스장→한강… 이동). MVP는 기본 필드 1~2개로 시작.
