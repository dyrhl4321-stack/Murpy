# 머피월드 v2 커스터마이징 제작 방식 — Bald Body Full Sprite Diff (확정 2026-07-09)

## 핵심
기준 body를 **빡빡이 v2(`char/v2/body_bald.png`, 846×1792, frame 282×448)** 로 고정.
나노바나나에는 **아이템 단독 레이어를 만들라고 하지 않는다.** 대신 **body_bald를 img2img 베이스로 넣어 "빡빡이가 [아이템] 착용한 full sprite"** 를 만들게 한다.
클코는 **착용본 − body_bald diff** 로 아이템 레이어만 기계적으로 추출한다.

왜 이게 정답인가: 색 마스킹 추측 없음 / 헤어·모자·옷 전부 같은 방식 / 모자-머리 충돌 없음(빡빡이) / 모든 아이템이 같은 body 기준 공유.

## 필수 조건 (검증됨)
- 착용본은 **반드시 body_bald를 img2img 베이스로** 생성. 별개 생성이면 몸통/머리 외곽이 달라져 diff에 노이즈가 낌(빡빡이 몸이 안 겹침). img2img면 캡만 바뀌어 diff가 순수해진다.
- diff는 (a) v2 846×1792로 정규화 정렬 + (b) 슬롯 영역 마스크 + (c) 임계 tolerance 로 몸통 노이즈 제거.
- 참고: 노이즈가 있어도 body_bald 위 재합성은 깨끗하게 보인다(노이즈가 몸과 겹침). 단 다른 캐릭터에 얹으려면 순수 레이어가 필요하므로 img2img 준수.
- row3/right는 **원본 착용본 그대로**. 좌우반전 금지. 원본 우향에 로고 없으면 없는 게 정상.

## 도구
```
python tools/character-customizer/customizer_cli.py extract-diff \
  --worn <착용_full_sprite.png> --slot {hair|hat|top|bottom|shoes|accessory} --item-id <id>
  [--base ../../char/v2/body_bald.png] [--threshold 85] [--manifest murpy_layers_v2.json]
```
자동 수행: 비표준 원본 → 정수격자 crop → v2 846×1792 정규화 → base와 diff → 슬롯영역 마스크 + 살색제외 → item 레이어 → **검수 큐 생성**:
`tools/character-customizer/review_queue/{itemId}_{ts}/` 에
source_original.png / source_normalized_v2.png / diff_mask.png / item.png / thumb.png / item_only_preview.png / body_plus_item_preview_4dir.png / validate_report.json / request.md

슬롯 영역(프레임 높이 비율): hair 0–0.42 / hat 0–0.40 / top 0.32–0.72 / bottom 0.55–0.93 / shoes 0.84–1.00 / accessory 0–1.

## 나노바나나 프롬프트 (착용 full sprite, img2img)
```
Create a full sprite sheet of this exact bald Murpy character wearing [ITEM].
Use the provided bald body sprite sheet as the exact base.
Do not redesign the character. Do not change body proportions, face, eyes, ears, skin color, pose, or frame layout. Only add [ITEM].
Keep the exact 3 columns × 4 rows. Rows: front/down, back/up, left, right. Columns: idle, walk1, walk2.
The result = the same bald character wearing [ITEM]. Do NOT create an item-only layer; create the full character wearing the item.
Transparent background. Pixel art. Sharp edges. No crop. No resize. No layout change. No extra character.
```

## 워크플로우 (검수 게이트 유지)
1. 김현수: body_bald img2img로 착용본 생성 → 클코에 전달
2. 클코: `extract-diff` 실행 → 검수 큐 자동 생성 (앱 등록 안 함, "잘 됐다" 자체승인 금지)
3. 김현수+코덱스: body_plus_item_preview 검수 → codex_review.md (APPROVED/NEEDS_FIX/REGENERATE)
4. APPROVED만 char/v2 배치 + 등록. 앱 렌더 v2 전환은 기본 착장 세트 준비 후 별도 단계.

## 레거시
기존 423×896 아이템·walk.png는 무손상 보관(프리셋). 상의/하의/신발은 v2 이식 가능성 테스트, 머리에 붙는 것(모자·헤어)은 이 diff 방식으로 새로.
