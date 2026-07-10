# Murpy Asset Studio v0.1

MurpyWorld 장비(의상/아이템) 레이어를 **추출하고 사람이 손으로 마무리하는** 내부 프로덕션 도구.

```
python tools/asset-studio/server.py     →  http://localhost:8787
```

배경과 근거: `docs/murpyworld-extraction-architecture-review.md`

---

## 무엇이 달라졌나

기존 `tools/character-customizer/customizer_cli.py extract-diff` 의 `_fill_interior_holes()` 는
"가장자리에서 도달 불가능한 투명 픽셀"을 전부 옷 안쪽 구멍으로 보고 옷 색으로 칠했다.
그런데 **2D 상의 둘러싸임 ≠ 옷 안쪽**이다. 팔과 몸통 사이 겨드랑이 틈, 모자 밑 목덜미도
2D 로는 옷에 둘러싸인 구멍이다. 그래서 몸에 옷 색이 칠해졌다.

실측 (`compare_hole_policies.py`):

| 아이템 | 슬롯 | legacy가 채운 구멍 | 그중 아직 몸인 픽셀 |
|---|---|---|---|
| hat_ladodgers | hat | 8,796 | 2,822 |
| top_ringer | top | 7,825 | 1,982 |
| top_jersey | top | 7,121 | 1,762 |
| top_redhood | top | 8,708 | 941 |

수정 규칙: **구멍을 구멍으로 남기는 유일한 조건은 `is_skin(base) ∧ is_skin(worn)`**
— "원래 몸이었고 지금도 몸으로 보인다".

`base` 가 나체가 아니라 베이지 속옷을 입고 있어서 "안 변했으면 채우지 마라" 같은 단순 규칙은
버뮤다 허리밴드를 점선 구멍으로 만든다. 실제로 시도해 보고 폐기했다.

---

## 핵심 원칙

- **base 시트는 절대 수정하지 않는다.** 서버는 읽기 전용으로만 연다.
- **아이템 RGB 를 만들어내지 않는다.** 브라우저의 편집 상태는 마스크(`Uint8Array`) 하나뿐이고,
  아이템 픽셀은 언제나 worn 원본에서 복사된다. 브러시조차 worn 이 불투명한 곳에서만 칠한다.
- **모든 리샘플링은 정수배 NEAREST.** 비정수 배율이면 `IngestError` 로 중단한다.
  846×1792 → 423×896 을 LANCZOS 로 줄이면 반투명 픽셀이 1.1% → 36.6% 로 폭증한다(실측).
- **기계 검증 ≠ 시각 승인.** 리포트의 PASS 는 "명백한 사고가 없다"는 뜻일 뿐이다.

---

## 화면

| 영역 | 내용 |
|---|---|
| 보기 | body+item / item / worn / base / diff |
| **UNK 오버레이(주황)** | Gemini 가 살을 다시 그린 곳. 옷이면 브러시, 살이면 그대로 둔다 |
| 프레임 | 12개 썸네일 (3열 idle·walk1·walk2 × 4행 down·up·left·right) |
| 도구 | 브러시 `B` / 지우개 `E` / 연결성분 삭제 `C` |
| 편집 | Undo `Ctrl+Z`, Redo `Ctrl+Y`, 자동결과로 초기화, before/after 토글 |
| 이동 | `←` `→` 프레임 전환, `[` `]` 브러시 크기 |

---

## 검증 항목

`engine/validate.py`. 게이트(하나라도 실패하면 FAIL):

| 항목 | 기준 |
|---|---|
| `size_exact` | 846×1792 |
| `semi_alpha_ok` | 반투명 픽셀 ≤ 2% |
| `no_alpha_halo` | α 1~20 유령 픽셀 0개 |
| `no_body_overpaint` | 아직 몸인 픽셀 위에 칠한 수 0 |
| `frame_area_stable` | walk 3프레임 간 면적 변동계수 ≤ 0.15 |
| `components_ok` | 프레임당 연결성분 ≤ 12 |
| `no_empty_frame` | 12프레임 모두 내용 있음 |

회귀 테스트로 확인된 동작:

```
LEGACY(현행)  ok=False  실패=['no_body_overpaint']   bodyOverpaint=1762
TRIMAP(수정)  ok=True   실패=없음                    bodyOverpaint=0

bottom_bermuda.png (출시본)  ok=False  semiRatio=0.4428  halo=8052
top_redhood.png    (출시본)  ok=False  semiRatio=0.4074  halo=12234
acc_airpodsmax.png (출시본)  ok=True   semiRatio=0.0077  halo=0
```

---

## 내보내기

`tools/asset-studio/review_queue/<itemId>_<타임스탬프>/`

| 파일 | 용도 |
|---|---|
| `item.png` | 846×1792 투명 PNG. 최종 산출물 |
| `mask_auto.png` / `mask_final.png` | 자동 마스크 / 사람 보정 후 — **미래 학습 데이터의 핵심 쌍** |
| `trimap.png` | FG=255, UNK=128, BG=0. 어디가 어려웠는지의 기록 |
| `worn_ingested.png` | 정규화된 worn (재현용) |
| `thumb.png`, `preview.png` | 상점 아이콘, 4방향 합성 미리보기 |
| `validate.json` | 검증 리포트 |
| `metadata.json` | 엔진 버전, 파라미터, `tHumanSeconds` |
| `edits.jsonl` | 사람이 어디를 어떻게 고쳤는지 |
| `status.json` | 승인 여부 |

`tHumanSeconds` 가 이 프로젝트의 **1순위 지표**다. 목표는 아이템당 60초 이하.

---

## 앱 등록 (수동, 승인 후에만)

1. 사람이 `preview.png` 를 보고 시각 승인
2. 846×1792 그대로 쓰거나, 꼭 줄여야 하면 **NEAREST** 로만 423×896 축소
3. `char/items/` 에 배치 → `index.html` 의 `window.CHAR_ITEMS` 에 등록 → `window._ITEM_V` 증가
4. `git push`

---

## 보조 스크립트

```bash
# 기존 diff vs 수정본을 나란히 렌더링 (앱 파일 안 건드림)
python tools/asset-studio/compare_hole_policies.py
python tools/asset-studio/compare_legacy_vs_trimap.py
```

산출물은 `tools/asset-studio/out/` 에 저장된다.

---

## 아직 안 한 것 (의도적으로)

- AI 비전 / SAM 2 보조 분할 — Phase 2. `tHumanSeconds` 중앙값이 60초를 못 넘길 때만 검토
- 학습 모델 — Phase 3. 지금은 데이터 스키마만 확정
- 이미지 정합(registration) — **불필요함이 실측으로 확인됨**(최대 1px, MAE 4.22→4.04)
- 플러드필, 사각 선택, 레이어 시스템, 로그인, SaaS
