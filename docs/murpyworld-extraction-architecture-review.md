# MurpyWorld 장비 추출 파이프라인 — 아키텍처 전면 재검토

> 작성: 2026-07-09
> 대상: `C:\Users\won\Murpy`
> 성격: 실측 기반 아키텍처 리뷰. 모든 수치는 저장소의 실제 아티팩트를 측정한 값이며, 재현 스크립트를 부록에 첨부한다.
> 선행 문서: `docs/murpyworld-extraction-pipeline-reverse-engineered.md` (**이 문서가 그 문서의 오류 2건을 정정한다**)

---

## 1. Executive Summary

측정으로 확인된 결론 세 가지.

**첫째, `_fill_interior_holes()`가 몸 픽셀을 옷 색으로 칠하고 있다. 상의만이 아니라 전 슬롯에서.**

`customizer_cli.py:207`의 `_fill_interior_holes()`는 "가장자리에서 flood-fill로 도달 불가능한 투명 픽셀"을 전부 **옷 안쪽 구멍**으로 간주하고 최근접 옷 색으로 칠한다. 그런데 **2D 상의 둘러싸임 ≠ 옷 안쪽**이다. 팔과 몸통 사이의 겨드랑이 틈, 모자 밑 목덜미도 2D로는 둘러싸인 구멍이다. 코드는 그 틈을 옷 색으로 메운다.

실측 (`tools/asset-studio/compare_hole_policies.py` 로 재현):

| 아이템 | 슬롯 | legacy가 채운 구멍 | 그중 base·worn 둘 다 살색(=아직 몸) | 비율 |
|---|---|---|---|---|
| hat_ladodgers | hat | 8,796 | **2,822** | 32% |
| top_ringer | top | 7,825 | **1,982** | 25% |
| top_jersey | top | 7,121 | **1,762** | 25% |
| top_redhood | top | 8,708 | 941 | 11% |
| hat_beanie_v2 | hat | 6,318 | 95 | 1.5% |
| bottom_bermuda | bottom | 11,361 | 1 | ~0% |
| shoes_white | shoes | 1,100 | 0 | 0% |

시각적으로는 측면(left/right) 프레임에서 **팔과 몸통 사이 틈이 셔츠 색 세로 띠로 메워지는** 형태로 나타난다. 모자는 뒤통수/목덜미에서 같은 일이 일어난다.

**정정:** 이 문서 초안은 원인을 "`_is_skin`이 거부해 생긴 구멍"이라고 썼으나, 실제 메커니즘은 위와 같다. 또 "모자는 안전하다"고 썼으나 `hat_ladodgers`가 비율상 가장 심하다.

수정 규칙은 단순하다. **구멍을 구멍으로 남기는 유일한 조건은 `is_skin(base) ∧ is_skin(worn)`** — "원래 몸이었고 지금도 몸으로 보인다". 그 외에는 채운다. 이 규칙이 필요한 이유:

- `body_bald.png`는 **나체가 아니다.** 베이지색 탱크톱·반바지를 입고 있다. 회색 버뮤다가 그 베이지와 `diff = 80`(임계값 85 미만)이라 "안 변함"으로 오분류되므로, "안 변했으면 채우지 마라"는 규칙은 허리밴드를 점선 구멍으로 만든다(실측 확인).
- 모자 꼭지에는 worn 시트 자체에 `alpha=0` 구멍이 있다(`base=(241,174,145)`, `worn α=0`, `diff=729`). 여기는 채워야 한다.

**둘째, 알파 채널이 리샘플링으로 파괴되고 있다.** v2 diff가 뽑은 `item.png`는 반투명 픽셀이 1.1%로 매우 깨끗한데, 846×1792 → 423×896으로 LANCZOS 축소하는 순간 **36.6%**가 반투명이 되고 알파 1~20짜리 유령 픽셀이 5,274개 생긴다. NEAREST로 줄이면 1.1%가 유지된다. 실제 출시된 `char/items/bottom_bermuda.png`는 가시 픽셀의 **44.3%**가 반투명이다. 그동안 `_dilate`와 `_cover_tee`로 싸워온 "밑옷 삐짐"의 정체가 이것이다.

**셋째, 정렬(pose registration)은 문제가 아니다.** 프레임별 최적 정수 시프트를 ±6px 전수 탐색했더니 최대 1px, MAE는 4.22 → 4.04로 4.3% 개선에 그쳤다. `threshold=85`가 노이즈 바닥(채널당 MAE 약 4, 4채널 합 약 12~17)을 이미 5배 여유로 거른다.

**따라서 결론: 픽셀 diff는 버릴 필요가 없다. 버려야 할 것은 `_is_skin` 하드 거부, `_fill_interior_holes` 무조건 채우기, 그리고 LANCZOS다.** 그 위에 사람이 10~60초 안에 고치는 에디터를 얹으면 끝난다. AI 비전은 v0.1에 넣지 않는다.

---

## 2. What the Current Code Actually Does

### 2.1 파일과 함수

| 파일 | 역할 |
|---|---|
| `char/extract_item.py` | 레거시 색상 규칙 추출기. `build()`, `norm_cell()`, `_extract_region()`, `_extract_flood()`, `_remove_small()`, `_dilate()`, `_cover_tee()`, `_dominant()`, `detect_grid()`, `largest()` |
| `char/build_bermuda.py`, `char/build_shoes_black.py` | 위의 아이템별 래퍼. `gray_judge()`, `shoe_judge()` |
| `char/build_walk.py` | 베이스 캐릭터 시트 빌드. `fill_notches()` |
| `char/extract_top_v2.py`, `char/extract_basic_outfit_v2.py`, `char/extract_hair_layer.py` | v2 시드-앤-그로우 실험 |
| `char/normalize_sprite_sheet.py` | 체커보드 배경 제거 + 격자 리사이즈 |
| `tools/character-customizer/customizer_cli.py` | v2 diff 파이프라인. `cmd_extract_diff()`, `normalize_worn()`, `_is_skin()`, `_remove_small_fragments()`, `_fill_interior_holes()`, `inspect_png()`, `compose_sheet()` |
| `index.html:1610-1626` | `window._CHAR_BODIES`, `window.CHAR_ITEMS`, `window._ITEM_V = 42` |
| `index.html:1660` | `_CHAR_LAYER_ORDER = ['body','shoes','bottom','top','hair','hat','acc']` |

### 2.2 하드코딩된 상수 (실측 확인)

- `customizer_cli.py:160-167` — `SLOT_REGIONS`:
  `hair (0.00, 0.42)`, `hat (0.00, 0.40)`, `top (0.30, 0.84)`, `bottom (0.55, 0.93)`, `shoes (0.84, 1.00)`, `accessory (0.00, 1.00)`
- `customizer_cli.py:463` — `--threshold` 기본값 **85** (RGBA 4채널 절대차의 합)
- `customizer_cli.py:170-172` — `_is_skin`: `a > 0 and r > 150 and g > 80 and b < 150 and (r - b) > 30`
- `customizer_cli.py:313` — 아이템 채택 조건: `w[3] > 60 and not _is_skin(w)`
- `customizer_cli.py:251` — `_remove_small_fragments(min_size=22)`, 추가로 `thin and len < 140`, `len < 90 and cw <= 4`
- `extract_item.py:16-17` — `CW, CH = 141, 224`, `TARGET_H, PAD_BOTTOM = 214, 4`

### 2.3 문서와 코드의 불일치 (명시)

선행 문서 `murpyworld-extraction-pipeline-reverse-engineered.md`의 **두 군데가 사실과 다르다.**

1. 문서: *"v2 diff 출력은 앱 미연결, review_queue에만 쌓임"* → **틀림.**
   출시된 `char/items/top_ringer.png`(423×896)와 `review_queue/top_ringer_20260709-155747/item.png`(846×1792)를 2배 축소해 비교하면 마스크 IoU가 **0.90**이다. v2 diff 결과가 축소되어 실제로 배포되고 있다. `top_ringer_prebeard.png`, `top_ringer_preholefill.png`가 남아 있는 것으로 보아 중간에 손으로 수정한 단계도 있다.

2. 문서: *"포즈 불일치가 셔츠 실패의 원인"* → **근거 없음.**
   8절 실측 참조. diff_mask의 세로 줄무늬를 보고 성급하게 추론한 것이었다.

또한 `tools/character-customizer/murpy_layers.json`의 hair 기본값이 `char/items/hair_default_extracted.png`인데, 이 파일은 **1408×2982**로 423×896도 846×1792도 아니다. `inspect_png()`가 `size_mismatch`를 반환하고 `compose_sheet()`가 이 레이어를 **조용히 건너뛴다**(`load_valid_image()`가 `None` 반환 → `continue`). 검수 툴이 머리카락 없이 합성하고 있었다는 뜻이다.

---

## 3. Current Pipeline Strengths

diff 방식은 생각보다 잘 만들어져 있다.

- **픽셀 보존이 기본이다.** `customizer_cli.py:314`의 `ip[ox+x, oy+y] = w`로 worn의 원본 픽셀을 그대로 복사한다. 재생성이 없다. 아키텍처적으로 옳은 선택.
- **threshold 85가 잘 잡혀 있다.** 실측 노이즈 바닥(채널당 MAE 4.2 → 4채널 합 약 12~17)의 5배 여유. 머리 영역 오탐 1.2%.
- **안쪽 경계가 자동으로 하드엣지가 된다.** 옷과 피부의 경계는 둘 다 불투명하므로 알파 리샘플링을 타지 않고, 마스크의 이진 판정이 곧 경계가 된다. 그래서 `item.png`의 반투명 비율이 1.1%다. 레거시 `norm_cell()`이 캐릭터 전체를 LANCZOS로 리사이즈해 모든 경계를 뭉개는 것과 정반대.
- **`review_queue/`가 이미 데이터셋 구조를 갖췄다.** `source_original / source_normalized_v2 / diff_mask / item / thumb / preview / validate_report / request.md`. 그대로 벤치마크·회귀 테스트가 된다.

---

## 4. Current Pipeline Weaknesses

1. **`_is_skin`이 하드 거부(reject)다.** 살색 판정된 픽셀을 그냥 버린다. 버려진 색을 실제로 뽑아보니 `(192,160,128)`, `(208,176,144)`, `(176,144,112)` — 진짜 살색이다. 판정 자체는 맞다. 문제는 **버린 자리에 구멍이 남는다**는 것.

2. **`_fill_interior_holes()`가 그 구멍을 옷 색으로 칠한다.** 이 함수는 "가장자리에서 flood-fill로 도달 불가능한 투명 픽셀"을 구멍으로 정의한다. 팔뚝의 살색 구멍은 옷 픽셀에 둘러싸여 있으므로 도달 불가능 → 구멍으로 오인 → `found = px[ox+nx, oy+ny]` (반경 7 이내 최근접 불투명 픽셀 = 옷 색)으로 채운다. **base가 살색인지 아닌지 전혀 보지 않는다.**

   상의는 버린 살색의 약 75%가 다시 옷 색으로 칠해진다. 하의는 다리 사이가 가장자리에서 도달 가능해 대부분 살아남고, 모자는 애초에 슬롯 영역에 살이 거의 없다. **"모자는 되고 셔츠는 안 된다"의 완전한 설명이다.**

3. **`normalize_worn()`이 비등방 LANCZOS를 건다.** `1123×2400` → crop `1122×2400` → LANCZOS `846×1792`.
   x배율 `846/1122 = 0.75401`, y배율 `1792/2400 = 0.74667`. 약 1% 종횡비 왜곡. 영향은 작지만(정렬 실측 ≤1px) 픽셀아트에 스무딩 필터를 쓰는 건 원칙 위반.

4. **`_remove_small_fragments(min_size=22)`가 작은 파츠를 삭제한다.** 에어팟 이어컵, 안경 다리, 모자 로고 같은 얇은 요소가 `thin and len < 140` 규칙에 걸린다. 커밋 `e4e07f5`("에어팟 옆 이어컵 복원")가 그 흔적.

5. **`normalize_worn()`의 "빈 쪽에서 crop" 휴리스틱이 위험하다.** `char/v2/body_bald.png`의 프레임 bbox를 재보니 row0c0 = `(0, 0, 261, 443)`, row3c2 = `(40, 22, 282, 448)` — **내용이 셀 경계에 닿아 있다.** 여백이 있다는 전제가 이미 깨져 있다.

6. **다운스케일이 알파를 파괴한다.** (5절)

7. **`validate_report.json`이 아무것도 검증하지 않는다.** (18절)

---

## 5. The Largest Hidden Failure Sources

### 1위 — `_fill_interior_holes()`의 살색 무시 (상의 전용 재앙)

1절 표 참조. 이것이 상의 재시도 5~6회의 원인이다.

인과 사슬:
```
Gemini가 팔/어깨 음영을 미세하게 다시 그림
  → 그 살색 픽셀이 base와 달라짐 → diff > 85
  → _is_skin(worn)이 True → 아이템에서 제외
  → 옷 픽셀에 둘러싸인 "구멍"이 됨
  → _fill_interior_holes()가 외곽에서 도달 불가 판정 → 구멍으로 오인
  → 반경 7 이내 최근접 불투명 픽셀(= 옷 색)으로 채움
  → 팔에 셔츠 색이 칠해짐
```

### 2위 — 846×1792 → 423×896 다운스케일의 알파 파괴

| 필터 | opaque | semi | semi% | halo(α≤20) |
|---|---|---|---|---|
| 원본 v2 `item.png` (846×1792) | 115,128 | 1,241 | 1.1% | 0 |
| LANCZOS ↓ | 22,926 | 13,234 | **36.6%** | 5,274 |
| BICUBIC ↓ | 25,843 | 6,866 | 21.0% | 1,802 |
| BOX ↓ | 27,620 | 2,876 | 9.4% | 12 |
| **NEAREST ↓** | 28,800 | 323 | **1.1%** | **0** |
| 실제 출시된 `top_ringer.png` | 27,059 | 7,718 | 22.2% | 4,919 |

출시된 레거시 아이템의 반투명 비율:

| 파일 | opaque | semi | semi% |
|---|---|---|---|
| `bottom_bermuda.png` | 23,949 | 19,030 | **44.3%** |
| `top_redhood.png` | 38,139 | 26,222 | **40.7%** |
| `hat_beanie.png` | 51,992 | 24,997 | 32.5% |
| `shoes_black.png` | 11,153 | 4,115 | 27.0% |
| `top_ringer.png` | 27,059 | 7,718 | 22.2% |
| `hat_gbd.png` | 82,605 | 11,943 | 12.6% |
| `acc_airpodsmax.png` | 21,678 | 168 | **0.8%** ← 한 번도 문제 없던 아이템 |

상관이 명확하다.

반투명 픽셀의 공간 분포도 측정했다. `bottom_bermuda`의 가시 반투명(α 61~249) 픽셀 중 10%가 불투명 영역에서 **15px 이상** 떨어져 있다(`top_redhood`는 29px, 최대 60.9px). 1px 테두리가 아니라 **떠다니는 유령 영역**이다. LANCZOS 링잉의 결과.

### 3위 — 베이스 자체가 픽셀아트가 아니다

`char/v2/body_bald.png`의 평평한 볼 8×8 패치 (x=120..127, y=150..157):
```
245,167,120  245,167,120  245,168,124  246,169,125  246,168,124  245,168,124  244,167,123  244,168,124
246,168,122  246,168,122  246,168,123  245,168,125  246,168,125  246,168,126  245,169,125  243,170,125
246,168,122  246,168,122  246,168,122  244,167,122  245,168,124  245,169,126  245,169,125  244,169,124
246,167,121  245,167,121  246,168,122  244,167,122  245,168,125  243,169,124  244,167,124  245,167,124
245,166,120  245,167,123  245,168,123  244,167,122  244,167,123  245,168,124  244,168,125  245,169,125
245,167,121  243,166,122  243,166,122  244,167,121  245,168,122  245,168,124  243,168,123  242,168,124
244,167,121  245,167,121  245,167,121  243,166,121  245,168,124  244,167,123  244,167,123  244,167,123
244,167,121  245,167,121  244,166,121  244,167,122  244,167,123  243,169,124  244,168,124  245,168,123
```
채널당 ±3 흔들린다. 불투명 고유색 **102,549개**, 수평 런렝스는 길이 1이 101,201개로 압도적(길이 2는 5,005개).
도트처럼 보이지만 실제로는 연속톤 노이즈 이미지다.

또한 base와 worn의 **피부 대표색 자체가 다르다**: base `(245,168,124)` vs worn `(246,164,124)`. 즉 Gemini가 몸도 미세하게 다시 렌더링했다.

**함의: 팔레트 인덱스 분류 접근(색 스와치 라벨링)은 이 데이터에서 양자화 없이는 불가능하다.**

### 4위 — 검증 부재

`"ok": true`가 위 모든 것을 통과시킨다. (18절)

---

## 6. Is Pixel Diff Fundamentally Necessary?

**아니다. 하지만 문제 정의를 바꾸면 diff는 훌륭한 사전 확률(prior)이다.**

핵심 재정의: **아무것도 생성할 필요가 없다. worn 시트에 이미 정답 RGB가 들어 있다. 필요한 건 worn 위의 이진 마스크 하나뿐이다.**

이건 생성(generation) 문제가 아니라 **분할(segmentation)** 문제다. 그리고 diff가 답하는 질문은 "무엇이 변했는가"이지 "무엇이 옷인가"가 아니다. 둘의 차이는 정확히 **생성 모델이 옷 이외의 것을 얼마나 다시 그렸는가**이고, 실측하면 그 양이 상의 기준 diff의 8.1%다. 작다.

옳은 구조는 diff를 **결정자가 아니라 시드 생성기**로 쓰는 것:

```
diff → 3분류 트라이맵(trimap)
   FG (확실한 전경): d > thr ∧ α_worn > 60 ∧ ¬is_skin(worn)
   UNK (미확정)    : d > thr ∧ is_skin(worn)      ← Gemini가 살을 다시 그린 곳
   BG (확실한 배경): d ≤ thr
→ UNK만 사람 클릭 / 영역성장으로 판정
→ hole fill은 base가 살색이 아닌 구멍에만 적용
```

현재 코드는 UNK를 **무조건 BG로 버렸다가**(`_is_skin`) **무조건 FG로 되칠한다**(`_fill_interior_holes`). 최악의 조합이다. UNK를 UNK로 두는 것만으로 상의 문제의 대부분이 사라진다.

---

## 7. Can Pure Vision Replace Diff?

**오늘 기술로는 "AI가 직접 투명 장비 레이어를 만들어낸다"는 아키텍처는 작동하지 않는다.**

**Claude Vision / GPT-4o vision** — 마스크를 출력할 수 없다. 텍스트, 좌표, bbox만 낸다. 282×448 프레임에서 1px 단위 경계를 좌표로 받아쓰는 건 비현실적. **점 프롬프트나 bbox 생성기로는 유용하고, 마스크 생산자로는 부적합.** 비결정적이라 같은 입력에 같은 출력을 보장하지 않는다 — 프로덕션 파이프라인에 치명적.

**Gemini / GPT Image 등 생성 모델** — 픽셀을 다시 그린다. 11절 대원칙("가능하면 원본 픽셀 보존")과 정면 충돌. 지금 겪는 문제(팔을 다시 그림)가 생성 모델을 신뢰한 결과인데, 해결책으로 또 생성 모델을 부르는 건 순환이다. 알파 채널을 정확히 내는 것도 못 한다.

**SAM / SAM 2 / Grounded-SAM** — 다르다. 마스크만 내고 픽셀은 안 건드리므로 11절 원칙을 지킨다. 라이선스도 Apache-2.0으로 상용 가능. 다만 정직하게:
- SAM 계열은 자연 사진으로 학습됐다. 282×448 픽셀아트, 특히 **1px 검정 외곽선이 옷에 속하는지 몸에 속하는지**는 SAM이 판단할 근거가 없다. 경계가 ±1~2px 흔들린다. 도트에서 1px은 치명적.
- 대응책: SAM을 **거친 영역 제안기**로 쓰고, 최종 경계는 결정론적으로 스냅(연결성분 경계, diff 경계).
- 12프레임 × 6슬롯이면 SAM ViT-B CPU로 프레임당 수 초, 아이템당 1분 안쪽. GPU 없으면 느리지만 불가능하진 않다. `torch` 의존성(수 GB)이 Windows 로컬 툴에 추가된다.

**판단: v0.1에 넣지 않는다.** 5절의 1·2위 원인을 고치면 상의 초기 마스크 품질이 극적으로 오르고, 그러면 SAM이 벌어줄 이득이 사람이 클릭 3번 하는 것보다 작아진다. SAM은 Phase 2에서 **에디터 안의 "클릭하면 영역 선택"** 기능으로 들어가는 게 맞다.

---

## 8. Image Registration Analysis

**결론: 지금은 불필요하다.**

`top_jersey`의 머리 영역(상의가 없는 곳, 프레임 상단 25%)에서 프레임별 최적 정수 시프트를 ±6px 전수 탐색:

| 프레임 | 최적 (dx,dy) | MAE @(0,0) | MAE @best | 개선 |
|---|---|---|---|---|
| r0c0 | (+1, 0) | 5.01 | 4.48 | 10.7% |
| r0c1 | (0, 0) | 4.11 | 4.11 | 0.0% |
| r0c2 | (0, 0) | 3.68 | 3.68 | 0.0% |
| r1c0 | (+1, 0) | 5.06 | 4.51 | 10.9% |
| r1c1 | (0, 0) | 4.39 | 4.39 | 0.0% |
| r1c2 | (0, 0) | 3.66 | 3.66 | 0.0% |
| r2c0 | (+1, 0) | 4.69 | 4.05 | 13.7% |
| r2c1 | (0, 0) | 4.47 | 4.47 | 0.0% |
| r2c2 | (0, 0) | 3.63 | 3.63 | 0.0% |
| r3c0 | (+1, 0) | 4.50 | 4.10 | 8.9% |
| r3c1 | (0, 0) | 3.95 | 3.95 | 0.0% |
| r3c2 | (0, 0) | 3.46 | 3.46 | 0.0% |
| **평균** | | **4.22** | **4.04** | **4.3%** |

1열만 x축으로 1px 밀려 있고 나머지는 완벽 정렬. 잔차 MAE 4.04는 **정렬 오차가 아니라 생성 노이즈 바닥**이다(base 자체가 평평한 면에서 ±3 흔들리므로).

슬롯 외부 diff 비율 (threshold 85, `top_jersey`):

| 영역 | 비어있지 않은 픽셀 | diff > 85 | 비율 |
|---|---|---|---|
| HEAD (상의 없음) | 184,460 | 2,126 | 1.2% |
| FEET (상의 없음) | 72,084 | 3,523 | 4.9% |
| TORSO (상의 영역) | 486,502 | 181,691 | 37.3% |

### 질문별 답

1. **정렬로 Gemini 재드로잉 차이를 없앨 수 있는가?** 아니다. 재드로잉은 기하 변환이 아니라 **내용 변경**이다. 팔 음영이 달라진 걸 warp로 되돌릴 수 없다.
2. **정렬이 추출을 크게 개선하는가?** 이 데이터에서는 아니다(4.3%).
3. **정렬이 픽셀아트 기하를 망칠 수 있는가?** 그렇다, 심각하게. **서브픽셀 warp는 반드시 보간을 수반하고, 보간은 하드 엣지를 파괴한다.** 정수 시프트가 아니면 하지 말 것.
4. **전역 vs 프레임별?** 필요해지면 프레임별 **정수 시프트만**. 스케일/회전/국소 변형 금지.
5. **NEAREST vs LANCZOS?** 5절 표. NEAREST 압도적.
6. **현재 LANCZOS가 프로덕션 픽셀아트에 적절한가?** 아니다.
7. **현재 정규화가 거짓 차이를 만드는가?** 만든다. 다만 threshold 85가 대부분 흡수한다. 비등방 배율(0.75401 vs 0.74667)은 즉시 고칠 가치가 있으나, **상의 실패의 주원인은 아니다.**

**정합에 쓸 예산을 `_fill_interior_holes` 수정과 NEAREST 전환에 쓸 것. ROI가 10배 이상 차이 난다.**

---

## 9. Pixel-Art-Specific Technical Issues

- **NEAREST vs LANCZOS**: 5절 표. 알파 반투명 1.1% → 36.6%. 논쟁의 여지 없음.
- **하드 경계 보존**: diff의 안쪽 경계는 이진 판정이라 자동으로 하드하다. 이 성질을 리샘플링으로 날리지 말 것.
- **리사이즈가 도입하는 안티앨리어싱**: `norm_cell()`(레거시)이 캐릭터 전체를 LANCZOS로 리사이즈한다. 레거시 아이템의 12~44% 반투명이 여기서 나온다.
- **색 오염**: LANCZOS 링잉은 옷 경계 바깥에 옷 색이 α 1~20으로 번진 유령을 만든다(`bottom_bermuda` 8,052px). `getbbox()`가 망가지고 썸네일에 여백이 붙는다.
- **threshold 불안정성**: base가 팔레트화돼 있지 않아(고유색 102,549) 같은 "회색"이 수백 가지 값을 갖는다. 레거시의 `chroma <= 24 and 92 <= br <= 216` 같은 규칙이 아이템마다 재튜닝돼야 하는 근본 이유.
- **1px 실루엣 오차**: 도트에서 1px은 실루엣의 5~10%. SAM류 자연영상 모델이 이 정밀도를 못 낸다.
- **알파 프린지**: 게임 런타임에서 반투명 옷 아래로 몸이 비친다. `_dilate()`와 `_cover_tee()`는 이 증상을 덮는 반창고였다.
- **연결성분 파편화**: `_remove_small_fragments`의 `thin and len<140` 규칙이 안경 다리·이어컵·모자 로고를 지운다.
- **결정적 원칙**: **모든 리샘플링은 정수배 NEAREST이거나, 아예 없어야 한다.** 비정수 배율이 필요하면 소스를 잘못 받은 것이다.

---

## 10. Slot-by-Slot Analysis

| 슬롯 | 최적 아키텍처 | 주요 실패 모드 | diff 적합? | 비전 필요? | 수동 보정 |
|---|---|---|---|---|---|
| **Hat** | diff 그대로 | 챙이 머리카락/이마 경계에서 1px 흔들림 | 매우 적합 | 불필요 | 거의 불필요 (실측 `holesFilled=0`) |
| **Hair** | diff + 얇은 성분 보존 | 머리카락 끝 파편이 `min_size=22`에 삭제. 두피/이마 경계 모호 | 조건부 | 불필요 | 가끔 |
| **Accessory** | diff + **파편 제거 완전 비활성** | 이어컵·안경다리 소실(`thin<140` 규칙) | 적합 | 불필요 | 성분 선택 도구 필요 |
| **Top** | **trimap diff** (UNK를 채우지 말 것) | ★`_fill_interior_holes`가 팔에 옷 색 페인트. 소매 경계. 로고 | 적합 (수정 후) | Phase2 도움됨 | **필수, 여기가 병목** |
| **Bottom** | trimap diff + top과의 슬롯 충돌 해소 | 긴 상의가 bottom 영역 침범. 다리 사이 구멍 | 적합 | 불필요 | 가끔 |
| **Shoes** | diff + 영역 제한(0.84~1.00) | 어두운 바지와 색 유사. 면적 작아 파편 규칙에 취약 | 적합 | 불필요 | 가끔 |

**결론: 슬롯별 엔진(Architecture F)은 과설계다.** 필요한 건 단일 엔진 + **슬롯별 파라미터 3개**:
`fill_holes_when_base_is_skin` (top만 false), `min_component` (accessory는 0), `slot_region_y`.

---

## 11. Architecture Options

| | 구조 | 픽셀 보존 | 결정론 | GPU | 이 프로젝트 적합도 |
|---|---|---|---|---|---|
| **A** | 현행 순수 diff | O | O | X | 상의에서 붕괴 |
| **B** | 순수 비전 분할 | 마스크만이면 O | X | 필요 | 1px 정밀도 부족 |
| **C** | diff 후보 + 비전 정리 | O | X | 필요 | Phase 2 후보 |
| **D** | 비전 영역 + 원본 픽셀 복사 | O | X | 필요 | C와 사실상 동일 |
| **E** | 정합 + diff | O | O | X | **불필요** (8절 실측) |
| **F** | 슬롯별 엔진 | O | O | X | 과설계 (10절) |
| **G** | 사람 개입 에디터 | O | O | X | **정답** |
| **H** | 머피 전용 학습 모델 | O | 학습 후 O | 필요 | 시기상조 (19절) |

추가 제안:

**A′ — Trimap Diff (수정된 diff).** A와 코드 변경량이 200줄 미만인데 상의 문제의 핵심을 제거한다.
```
FG  = diff>thr ∧ α_worn>60 ∧ ¬is_skin(worn)
BG  = diff≤thr
UNK = diff>thr ∧ is_skin(worn)          ← 버리지도 채우지도 않음
holes_fill: base가 살색인 구멍은 채우지 않음
min_component: 슬롯별
```

---

## 12. Decision Matrix

10점 만점. 이 프로젝트의 실측 데이터 기준.

| | 정확도 | 픽셀보존 | 견고성 | 구현난이도(낮을수록↑) | 유지비(↑) | 런타임비용(↑) | 속도 | 재현성 | Hat | Top | Bottom | Shoes | 확장성 | 상용성 |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1. 레거시 색상 | 3 | 4 | 2 | 6 | 2 | 10 | 9 | 10 | 6 | 2 | 3 | 3 | 2 | 1 |
| 2. 현행 diff | 6 | 9 | 5 | 8 | 6 | 10 | 9 | 10 | **9** | **3** | 6 | 6 | 6 | 4 |
| 3. 정합 + diff | 6 | 8 | 6 | 5 | 5 | 10 | 7 | 9 | 9 | 4 | 6 | 6 | 6 | 4 |
| **3′. Trimap diff** | **8** | **10** | **8** | **8** | **8** | **10** | **9** | **10** | **9** | **7** | **8** | **8** | **8** | **6** |
| 4. 순수 비전 | 4 | 6 | 5 | 3 | 4 | 3 | 3 | 2 | 6 | 5 | 5 | 4 | 7 | 6 |
| 5. 비전 마스크 + 픽셀 복사 | 6 | 10 | 6 | 4 | 5 | 4 | 4 | 3 | 7 | 6 | 6 | 5 | 8 | 7 |
| 6. diff + 비전 정리 | 8 | 10 | 7 | 4 | 4 | 4 | 4 | 3 | 8 | 8 | 7 | 6 | 8 | 7 |
| 7. 슬롯별 엔진 | 7 | 9 | 6 | 3 | 2 | 9 | 8 | 9 | 9 | 6 | 7 | 7 | 4 | 3 |
| **8. 사람 개입 에디터** | **10** | **10** | **10** | **7** | **9** | **10** | **7** | **10** | **10** | **10** | **10** | **10** | **7** | **8** |
| 9. 학습 모델 | ? | 10 | ? | 1 | 3 | 6 | 6 | 8 | ? | ? | ? | ? | 9 | 9 |

**3′ + 8의 조합이 모든 열에서 지배적(dominant)이다.**

---

## 13. Recommended Architecture

### Phase 1 (즉시, 1~2일) — Trimap Diff + Human-in-the-Loop Editor

```
base(846×1792, 불변)  +  worn(원본 해상도)  +  slot
        │
        ├─ ingest: 정수배 NEAREST만 허용. 비정수면 에러로 중단(조용한 LANCZOS 금지)
        │
        ├─ trimap diff
        │     FG  = d>85 ∧ α_worn>60 ∧ ¬is_skin(worn)
        │     UNK = d>85 ∧ is_skin(worn)              ← 보존, 채우지 않음
        │     BG  = 나머지
        │
        ├─ cleanup (슬롯별 파라미터)
        │     min_component: top/bottom 22, accessory/hair 0
        │     fill_holes: base가 살색인 구멍은 스킵
        │
        ├─ Murpy Asset Studio (브라우저 에디터)
        │     5뷰 + 12썸네일 + 브러시/지우개/성분선택 + undo/redo
        │     UNK 영역을 주황색으로 오버레이 → 사람이 클릭 몇 번으로 판정
        │
        └─ export: item.png(846×1792) + mask.png + preview.png + thumb.png + metadata.json
              앱용 423×896은 NEAREST 축소, 또는 846×1792 그대로 쓰고 CSS로 축소
```

**핵심 UX: 자동 결과가 80~95%, 사람이 10~60초.** AI 재생성 루프(현재 5~6회)를 없애는 게 목표.

### Phase 2 (Phase 1이 2주 굴러간 뒤) — 상호작용 분할 보조

에디터 안에 **"클릭하면 영역 선택"** 추가. 먼저 순수 결정론(연결성분 + 색 유사도 영역성장)으로 구현하고, 그걸로 부족할 때만 SAM 2를 붙인다. 로컬, `torch` + `sam2`(Apache-2.0), CPU 가능/GPU 권장.

### Phase 3 (아이템 100개 이상 축적 후) — 판단 유보

학습 모델은 지금 결정하지 않는다(19절). **단, 데이터 스키마는 Phase 1에서 확정한다.**

---

## 14. Murpy Asset Studio v0.1

### 아키텍처

브라우저는 로컬 Python을 못 부른다. **얇은 로컬 서버**가 정답(표준 라이브러리만 사용).

```
tools/asset-studio/
  server.py            # http.server 기반. customizer_cli를 import해서 재사용
  static/
    index.html
    studio.js          # 캔버스 편집 (image-rendering: pixelated)
    studio.css
  engine/
    trimap.py          # 새 추출기
    validate.py        # 새 검증기
  benchmark/
    gold/              # 손으로 만든 정답 마스크
```

```
python tools/asset-studio/server.py   →  http://localhost:8765
```

### API (4개면 충분)

| 엔드포인트 | 입력 | 출력 |
|---|---|---|
| `POST /api/extract` | base, worn 경로, slot, threshold | 세션 id, base/worn/diff/item/trimap PNG 참조 |
| `POST /api/export` | 세션 id, 편집된 마스크 | item.png, mask.png, preview.png, thumb.png, metadata.json → `review_queue/` |
| `GET /api/img/<id>/<name>` | | PNG 스트림 |
| `GET /api/validate/<id>` | | 검증 리포트 JSON |

**서버는 `base`를 절대 쓰기 위해 열지 않는다.** 읽기 전용 경로로 강제.

### v0.1 기능 (최소)

**넣을 것**
- 5뷰 토글: base / worn / diff / item / body+item 합성
- 12프레임 썸네일, 클릭 시 해당 프레임으로 이동
- 줌 (1×/2×/4×/8×), `image-rendering: pixelated`, `ctx.imageSmoothingEnabled = false`
- **브러시(worn에서 복원)** — 마스크에 픽셀 추가. 색은 항상 worn 원본에서 복사(재드로잉 없음)
- **지우개** — 마스크에서 제거
- **연결성분 클릭 선택/삭제** — 이어컵, 떠다니는 유령 조각을 한 방에
- **UNK 오버레이 토글** — 주황색. Gemini가 살을 다시 그린 곳을 표시. **v0.1의 킬러 기능**
- undo/redo (마스크 스냅샷 스택, 프레임 단위, 깊이 50)
- before/after 토글
- export

**빼는 것 (v0.1에서)**
- 레이어 시스템, 플러드필, 사각선택, 로그인, AI 기능

**데이터 모델**: 편집 상태는 `Uint8Array(846*1792)` 마스크 하나. 아이템 RGB는 항상 `worn`에서 조회. **RGB를 저장하지 않는다.** 이것이 "재드로잉 금지" 원칙을 코드 레벨에서 강제한다.

---

## 15. Proof-of-Concept Experiments

전부 기존 `review_queue/`로 실행 가능.

**POC 0 — 골드 마스크 만들기 (선행 필수)**
- 입력: `top_jersey`, `top_ringer`, `top_redhood`, `hat_ladodgers`, `hat_beanie`, `acc_airpodsmax`, `bottom_bermuda`, `bottom_trainpt`, `shoes_black`, `shoes_white` 각 12프레임
- 출력: `benchmark/gold/<item>/mask.png` (846×1792, 이진)
- 방법: 현행 `item.png`를 시작점으로 손 보정. **약 4시간 예상**
- 성공 기준: 10개 × 12프레임 = 120 프레임 골드 확보

**POC 1 — 현행 diff 베이스라인**
- 출력: 골드 대비 IoU, FP픽셀, FN픽셀
- 난이도: 낮음 (반나절)
- 예측: hat ≈ 0.97, top ≈ 0.82 (hole-fill이 팔을 칠하므로 FP 급증)

**POC 2 — Trimap diff**
- 변경: `customizer_cli.py` 약 30줄
- 예측: **top IoU 0.82 → 0.93**, FP 대폭 감소. UNK 픽셀 수를 리포트에 노출
- 성공 기준: 모든 슬롯 IoU ≥ 0.90 이고 **FP < FN** (과잉 칠하기보다 덜 칠하는 쪽이 사람 보정이 쉬움)

**POC 3 — 리샘플링 감사**
- 변경: `normalize_worn()`에서 비정수 배율이면 예외. 앱 축소는 NEAREST
- 출력: 반투명 비율 before/after
- 예측: 12~44% → 1~2%. **반나절, 효과 최대**

**POC 4 — 정합 + diff** *(반증용으로만)*
- 8절에서 이미 4.3% 개선으로 측정됨. 다른 아이템 2개만 스팟체크

**POC 5 — SAM 2 클릭 분할**
- 입력: worn 프레임 + 사람 클릭 1~3점
- 출력: 마스크 → 골드 대비 IoU, **경계 오차 히스토그램(몇 px 벗어나는가)**
- 난이도: 중 (torch 설치, 2일)
- 성공 기준: IoU ≥ 0.95 **그리고** 경계의 90%가 ±1px 이내. **못 넘으면 채택하지 않는다**
- 예측: IoU는 넘고 경계 조건에서 탈락 (가설, 미검증)

**POC 6 — 사람 개입 에디터**
- 측정: 아이템당 보정 시간(초), 최종 IoU
- 성공 기준: **중앙값 60초 이하로 IoU 1.0 도달**

채점은 **동일한 10개 아이템**에 대해서만 한다.

---

## 16. Benchmark and Success Metrics

### 벤치마크 구성

| 케이스 | 아이템 | 검증하려는 것 |
|---|---|---|
| 쉬움 | `hat_ladodgers`, `hat_beanie` | 회귀 방지 |
| 얇은 성분 | `acc_airpodsmax` | 파편 제거 규칙 |
| 로고/패턴 | `top_jersey` (LEGEND/77/방패) | 경계 안정성 |
| 살 재드로잉 | `top_ringer` | trimap 핵심 케이스 |
| 오버사이즈 | `top_redhood` | 슬롯 침범 |
| 유사색 | `shoes_black` vs 남색 반바지 | 색 충돌 |
| 무채색 충돌 | `bottom_bermuda` vs 회색 챙 | 레거시 실패 재현 |
| 다리 움직임 | `bottom_trainpt` | 프레임 간 일관성 |

### 지표 (우선순위 순)

**1위 — `T_human`: 자동 결과를 프로덕션 품질로 만드는 데 드는 사람 시간(초).**
유일하게 사업적으로 의미 있는 지표. 현재 값: 아이템당 AI 재생성 5~6회 × (생성 대기 + 검수) ≈ **30~90분**. 목표: **60초 이하.**

**2위 — 1차 통과율.** 자동 결과가 손 안 대고 통과하는 비율. 현재 사실상 0%(상의 기준). 목표 40%.

**3위 — 기계 지표 (자동 측정, 회귀 방지용)**
- 마스크 IoU (골드 대비), 슬롯별
- FP 픽셀 / FN 픽셀 (**분리해서** 볼 것. FP=몸에 옷 칠함=치명적, FN=옷 덜 뽑음=브러시로 5초)
- `semi_alpha_ratio` (α 1~254 / 가시픽셀) — **목표 < 2%**
- `skin_overpaint_px` — hole-fill이 base 살색 위에 칠한 픽셀 수 — **목표 0**
- `frame_area_cv` — walk 3프레임 간 아이템 면적의 변동계수 — **목표 < 0.15**
- `component_count` — 프레임당 연결성분 수 (급증 = 파편화)

**측정하지 말 것**: "보기 좋다", API 비용(Phase 1에 API 없음), 지연시간(로컬 수 초).

---

## 17. Manual Correction Workflow

```
1. 사람: Gemini로 worn 시트 생성 (1회, 재생성 루프 없음)
2. 스튜디오: python server.py → 브라우저 자동 오픈
3. base/worn/slot 지정 → [추출] (1~3초)
4. 화면: item 오버레이 + UNK(주황) 오버레이
   → "주황색이 옷이면 브러시, 살이면 그냥 둔다"
5. 12썸네일 훑기. 문제 프레임만 클릭해 4× 줌
6. 브러시/지우개/성분삭제 (평균 10~60초)
7. [검증] → 기계 리포트 (semi_alpha, skin_overpaint, frame_area_cv)
8. [내보내기] → review_queue/<item>_<ts>/ 에 전부 기록 + status: approved
9. 앱 등록: NEAREST 축소 → char/items/ → CHAR_ITEMS + _ITEM_V++
```

**핵심은 4번.** 현재 파이프라인은 UNK를 사람에게 안 보여주고 몰래 옷 색으로 칠한다. 그걸 주황색으로 드러내는 것만으로 판단 시간이 수십 분에서 수십 초로 떨어진다.

---

## 18. Validation Improvements

### 지금 `"ok": true`가 나오는 이유

`cmd_extract_diff()`가 확인하는 것은 `sizeOK`, `vis > 0`, `trans > 0`, `skin == 0`, `not empty` 다섯 개뿐이다. 그런데 `skinPixels`는 **최종 item에 살색이 남아 있는지**를 본다. `_fill_interior_holes()`가 살색 구멍을 **옷 색으로 칠해버렸으니 당연히 0**이다.

**검증 지표가 버그를 지워버린 자리를 검사하고 있다. 완벽하게 통과하는 완벽한 실패다.**

### 기계적으로 자동화 가능한 검증

```python
checks = {
  "size_exact":        item.size == (846, 1792),
  "semi_alpha_ratio":  semi / visible < 0.02,
  "no_alpha_halo":     count(0 < a <= 20) == 0,
  "skin_overpaint":    filled_holes_where_base_is_skin == 0,      # 신규
  "unk_reported":      unk_pixel_count,                           # 실패 아님, 정보
  "frame_area_cv":     std(area_per_frame)/mean < 0.15,           # 신규
  "component_count":   max_components_per_frame < 12,
  "outside_slot_diff": diff_outside_slot_region / total < 0.03,   # 생성기 드리프트 경보
  "no_empty_frame":    all 12 frames non-empty,
  "boundary_hardness": fraction of edge pixels with a in {0,255} > 0.95,
}
```

`skin_overpaint`와 `frame_area_cv` 둘만 있었어도 `top_jersey` 5회 재시도는 1회로 끝났을 것이다.

### 자동화 불가능한 것 (정직하게)

- "소매 길이가 어색하다", "실루엣이 캐릭터답지 않다" — **사람이 봐야 한다.** VLM은 이 수준의 도트 판정을 못 한다.
- 대신 사람이 봐야 할 프레임을 **기계가 지목**하게 할 것: `frame_area_cv` 이상치, UNK 밀집 프레임.

**기계 검증 = 통과/실패 게이트. 지각 검증 = 사람. 둘을 리포트에서 분리 표기.**

---

## 19. Dataset / Future Learning Strategy

**정직한 답: 지금 학습 모델을 만들지 말 것. 하지만 데이터는 오늘부터 정확한 스키마로 모을 것.**

- **몇 개가 필요한가?** 도메인이 극단적으로 좁으니(캐릭터 1종, 포즈 12개 고정) 소형 U-Net을 **~200 프레임(아이템 약 17개)** + 증강으로 학습하는 건 기술적으로 가능하다. 하지만 **손 보정이 60초라면 아이템 17개 = 17분이다.** 학습·튜닝·유지에 드는 수십 시간을 회수하지 못한다.
- **머피 전용 모델이 범용 모델을 이길까?** 이 좁은 도메인에서는 거의 확실히 이긴다(가설이지만 근거 있음: 배경 고정, 포즈 고정, 캐릭터 고정). 문제는 ROI.
- **파인튜닝은 현실적인가?** SAM 2 파인튜닝보다 처음부터 작은 U-Net이 낫다. 입력 6채널(base RGB + worn RGB)로 주면 diff 정보를 모델이 알아서 쓴다.
- **처음부터 학습은 비현실적인가?** 아니다. 위 구조면 현실적이다. 다만 **필요가 없다.**
- **지금 데이터 수집을 시작해야 하는가?** **반드시.** 재수집이 불가능하기 때문.

### 오늘 확정해야 할 스키마

```
review_queue/<item_id>_<ts>/
  meta.json          # engine_version, threshold, slot, params, git_sha,
                     # source_hash(base), source_hash(worn), operator, timestamp
  base_ref.txt       # base 파일 경로 + sha256 (사본 저장 금지, 불변이므로)
  worn_original.png  # 원본 그대로. 리사이즈 금지
  worn_ingested.png  # 정수배 NEAREST 결과 (또는 원본과 동일)
  mask_auto.png      # 자동 추출 이진 마스크 (846×1792, 1ch)
  mask_final.png     # 사람 보정 후 ★ 학습 타깃
  trimap.png         # FG=255, UNK=128, BG=0  ★ 어디가 어려웠는지의 기록
  item.png           # mask_final ∧ worn 픽셀
  edits.jsonl        # {op, frame, tool, pixels, ts} — 보정 행동 로그 ★
  validate.json      # 위 checks
  status.json        # {approved: bool, reviewer, t_human_seconds} ★
```

★ 표시가 미래 학습의 전부다. 특히 `mask_auto` ↔ `mask_final` 쌍과 `t_human_seconds`.
`edits.jsonl`은 "사람이 어디를 고쳤나"를 알려주므로 능동학습(active learning) 신호가 된다.

---

## 20. Implementation Plan

### Phase 0 — 벤치마크 (0.5일)
- **목표**: 골드 마스크 확보. 없으면 모든 후속 판단이 취향 싸움이 된다
- **파일**: `tools/asset-studio/benchmark/gold/<item>/mask.png`, `benchmark/manifest.json`
- **출력**: 10개 아이템 × 12프레임 이진 마스크
- **중단 조건**: 10개 완료
- **성공 기준**: 두 사람이 같은 프레임을 봤을 때 IoU ≥ 0.98

### Phase 1 — 리샘플링 감사 (0.5일) ← **가장 먼저**
- **목표**: 알파 파괴 제거
- **파일**: `customizer_cli.py:normalize_worn()`, 신설 `char/downscale_nearest.py`
- **변경**: 비정수 배율이면 `raise SystemExit`. 앱용 축소는 `Image.NEAREST` 고정
- **출력**: 기존 아이템 9종 재생성
- **중단 조건**: 모든 아이템 `semi_alpha_ratio < 2%`
- **성공 기준**: `bottom_bermuda` 44.3% → < 2%, 육안으로 밑옷 삐짐 소멸

### Phase 2 — Trimap Diff (1일)
- **목표**: 상의 hole-fill 재앙 제거
- **파일**: `tools/asset-studio/engine/trimap.py` (신설, `customizer_cli`에서 함수 재사용)
- **변경**: UNK 클래스 도입. `_fill_interior_holes(skip_if_base_is_skin=True)`. 슬롯별 `min_component`
- **출력**: `mask_auto.png`, `trimap.png`, 갱신된 `validate.json`
- **중단 조건**: 벤치마크 10종 전부에서 `skin_overpaint == 0`
- **성공 기준**: top 슬롯 IoU ≥ 0.90, **FP < FN**

### Phase 3 — Asset Studio v0.1 (2~3일)
- **목표**: `T_human` 중앙값 ≤ 60초
- **파일**: `tools/asset-studio/server.py`, `static/{index.html,studio.js,studio.css}`
- **출력**: 14절의 4개 API + 에디터
- **중단 조건**: 벤치마크 10종을 스튜디오만으로 IoU 1.0까지 보정 완료
- **성공 기준**: 중앙값 60초, 최악 3분

### Phase 4 — 검증 강화 + 데이터 수집 (0.5일)
- **파일**: `tools/asset-studio/engine/validate.py`, 19절 스키마
- **성공 기준**: 과거 `top_jersey_20260709-154511/item.png`를 넣으면 **자동으로 FAIL**

### Phase 5 — SAM 2 평가 (2일, **선택**)
- **진입 조건**: Phase 3 이후에도 `T_human` 중앙값이 60초를 못 넘길 때만
- **탈락 기준**: 경계의 90%가 ±1px 이내가 아니면 폐기

**총 4~5일. Phase 1과 2만으로도 오늘의 병목 대부분이 사라진다.**

---

## 21. Risks

- **골드 마스크 자체가 틀릴 수 있다.** 두 번 만들어 IoU로 교차검증할 것.
- **`_is_skin` 임계값이 다른 피부톤에 안 맞는다.** 현재 `r>150 ∧ g>80 ∧ b<150 ∧ (r-b)>30`은 밝은 살색 전용. 어두운 피부 캐릭터를 넣으면 UNK가 폭증한다. 지금은 캐릭터가 1종이라 괜찮지만, **다인종 캐릭터를 계획한다면 이 함수는 재설계 대상.**
- **NEAREST 축소가 얇은 디테일(모자 로고 1px 선)을 지운다.** 그래서 권고는 **애초에 846×1792를 그대로 배포하고 CSS로 축소**하는 것. 파일 크기는 압축 후 큰 차이 없다(투명 영역이 대부분).
- **`normalize_worn`을 엄격하게 바꾸면 기존 워크플로가 깨진다.** Gemini가 1123×2400을 주면 이제 에러가 난다. 대응: **Gemini에 요청할 캔버스 크기를 846×1792 또는 1692×3584(정확히 2배)로 고정**할 것. 프롬프트 한 줄이다.
- **에디터를 만들면 사람이 자동화 개선을 안 하게 된다.** `t_human_seconds`를 계속 기록해, 이 값이 늘면 자동 추출을 손보라는 신호로 쓸 것.
- **`hair_default_extracted.png` (1408×2982)가 조용히 스킵되고 있다.** 검수 툴이 지금 거짓 결과를 보여주고 있을 가능성이 크다. Phase 1에서 같이 잡을 것.

---

## 22. Final Recommendation

**픽셀 diff를 유지하라. AI 비전은 넣지 마라. 정합은 하지 마라.**

오늘의 병목은 알고리즘 선택이 아니라 세 개의 구체적 버그다.

1. `_fill_interior_holes()`가 base의 살색을 보지 않고 옷 색으로 칠한다 → 상의 전멸
2. LANCZOS가 알파를 파괴한다 → 밑옷 삐짐 → `_dilate`/`_cover_tee`라는 반창고 → 더 큰 혼란
3. `validate_report.json`이 1번을 검사할 수 없는 지표(`skinPixels`)를 본다 → 실패가 `ok: true`로 통과

이 셋을 고치면 자동 추출 품질이 올라가고, 남는 5~20%는 **에디터에서 사람이 30초에 처리**한다.
완벽한 자동화를 쫓다가 재생성 루프에 갇히는 것보다, **80% 자동 + 20% 초고속 수동**이 프로덕션에서 항상 이긴다.

**5년 뒤에도 이 구조가 맞다.** `mask_final`과 `edits.jsonl`이 쌓이고, 그때 학습 모델을 붙이면 에디터는 그대로 두고 자동 추출만 교체하면 된다. 에디터는 **모델의 정확도가 무엇이든 상관없이** 필요하다.

---

## 23. Exact First Five Actions To Take

1. **`char/downscale_nearest.py`를 만들고 `Image.NEAREST`로 아이템 9종을 846×1792 → 423×896 재생성.**
   또는 아예 846×1792를 그대로 배포하고 `_CHAR_BODIES.human.cw/ch`를 282/448로 올린 뒤 CSS로 축소.
   **반나절, 효과 최대.** `bottom_bermuda`의 반투명 44.3% → 1~2%.

2. ~~`_fill_interior_holes()` 수정~~ → **완료.** `tools/asset-studio/engine/trimap.py` 에 구현했다.
   구멍을 남기는 조건은 `is_skin(base) ∧ is_skin(worn)`. 처음 제안한 `is_skin(base)` 단독 가드는
   모자 꼭지에 구멍을 만들었고, "안 변했으면 채우지 마라"는 버뮤다 허리밴드를 점선으로 만들었다.
   둘 다 렌더링으로 반증하고 폐기했다. 비교 렌더는 `python tools/asset-studio/compare_hole_policies.py`.

3. ~~검증 강화~~ → **완료.** `tools/asset-studio/engine/validate.py`.
   실측 결과: LEGACY 추출은 `no_body_overpaint` 로 FAIL, TRIMAP 은 PASS.
   출시된 `bottom_bermuda.png`(반투명 44.3%)·`top_redhood.png`(40.7%)는 FAIL,
   문제없던 `acc_airpodsmax.png`(0.8%)만 PASS. 검증기가 실제 실패를 구별한다.

4. **`normalize_worn()`에서 비정수 배율이면 예외를 던지도록 바꾸고, Gemini 프롬프트의 캔버스 지정을 846×1792 또는 1692×3584로 고정.**

5. **`murpy_layers.json`의 `hair` 기본값이 1408×2982라 `compose_sheet()`가 조용히 스킵하는 문제를 수정.**
   지금 검수 툴이 머리카락 없는 합성을 보여주고 있다.

**순서가 중요하다.** 이 다섯 개를 끝낸 뒤에 Asset Studio를 지으면 에디터는 "망가진 결과를 고치는 도구"가 아니라 "좋은 결과를 마무리하는 도구"가 된다. 순서를 바꾸면 에디터가 버그를 손으로 지우는 데 쓰이게 된다.

---

## 부록 A — 측정 재현 스크립트

모든 수치는 아래 스크립트로 재현 가능하다. 저장소 루트(`C:\Users\won\Murpy`)에서 실행.

### A.1 알파 품질 측정

```python
import numpy as np, os
from PIL import Image
for p in ['char/items/top_ringer.png','char/items/hat_beanie.png','char/items/hat_gbd.png',
          'char/items/shoes_black.png','char/items/acc_airpodsmax.png','char/items/top_redhood.png',
          'char/items/bottom_bermuda.png',
          'tools/character-customizer/review_queue/top_ringer_20260709-155747/item.png']:
    a = np.asarray(Image.open(p).convert('RGBA')); al = a[...,3]
    op = int((al==255).sum()); semi = int(((al>0)&(al<255)).sum())
    print("%-34s opaque=%7d semi=%7d (%.1f%%)" % (os.path.basename(p), op, semi, 100*semi/max(op+semi,1)))
```

### A.2 다운스케일 필터 비교

```python
import numpy as np
from PIL import Image
src = Image.open('tools/character-customizer/review_queue/top_ringer_20260709-155747/item.png').convert('RGBA')
def stats(im, name):
    al = np.asarray(im)[...,3]
    op = int((al==255).sum()); semi = int(((al>0)&(al<255)).sum()); halo = int(((al>0)&(al<=20)).sum())
    print("%-24s opaque=%6d semi=%6d (%.1f%%)  halo=%5d" % (name, op, semi, 100*semi/max(op+semi,1), halo))
stats(src, 'v2 item.png 846x1792')
for f, nm in [(Image.LANCZOS,'LANCZOS'), (Image.BICUBIC,'BICUBIC'), (Image.BOX,'BOX'), (Image.NEAREST,'NEAREST')]:
    stats(src.resize((423,896), f), 'down 423x896 ' + nm)
stats(Image.open('char/items/top_ringer.png').convert('RGBA'), 'SHIPPED top_ringer')
```

### A.3 `_is_skin` 거부량 측정

```python
import numpy as np
from PIL import Image
FW, FH, cols, rows = 282, 448, 3, 4
SLOT = {'top': (0.30, 0.84), 'bottom': (0.55, 0.93)}

def run(qdir, slot):
    b = np.asarray(Image.open('char/v2/body_bald.png').convert('RGBA'), dtype=np.int16)
    w = np.asarray(Image.open(qdir + '/source_normalized_v2.png').convert('RGBA'), dtype=np.int16)
    y0, y1 = int(SLOT[slot][0]*FH), int(SLOT[slot][1]*FH)
    d_tot = skin_rej = kept = 0
    for r in range(rows):
        for c in range(cols):
            B = b[r*FH+y0:r*FH+y1, c*FW:(c+1)*FW]; W = w[r*FH+y0:r*FH+y1, c*FW:(c+1)*FW]
            diff = np.abs(B-W).sum(axis=2) > 85
            d_tot += int(diff.sum())
            R, G, Bc, A = W[...,0], W[...,1], W[...,2], W[...,3]
            skin = (A>0) & (R>150) & (G>80) & (Bc<150) & ((R-Bc)>30)
            aok = A > 60
            kept += int((diff & aok & ~skin).sum())
            skin_rej += int((diff & aok & skin).sum())
    print("%s (%s): diff=%d kept=%d REJECTED_by_is_skin=%d (%.1f%%)"
          % (qdir.split('/')[-1], slot, d_tot, kept, skin_rej, 100*skin_rej/max(d_tot,1)))

run('tools/character-customizer/review_queue/top_ringer_20260709-155747', 'top')
run('tools/character-customizer/review_queue/top_jersey_20260709-154511', 'top')
run('tools/character-customizer/review_queue/bottom_trainpt_20260709-154335', 'bottom')
```

### A.4 프레임별 정렬 잔차 측정

```python
import numpy as np
from PIL import Image
b = np.asarray(Image.open('char/v2/body_bald.png').convert('RGBA'), dtype=np.int16)
w = np.asarray(Image.open('tools/character-customizer/review_queue/top_jersey_20260709-154511/source_normalized_v2.png').convert('RGBA'), dtype=np.int16)
FW, FH, R = 282, 448, 6
for r in range(4):
    for c in range(3):
        B = b[r*FH:(r+1)*FH, c*FW:(c+1)*FW][0:112]      # 머리 영역 = 상의 없음
        W = w[r*FH:(r+1)*FH, c*FW:(c+1)*FW][0:112]
        best = None
        for dy in range(-R, R+1):
            for dx in range(-R, R+1):
                sw = np.roll(np.roll(W, dy, axis=0), dx, axis=1)
                m = (B[...,3]>200) & (sw[...,3]>200)
                if m.sum() < 500: continue
                mae = float(np.abs(B[...,:3][m] - sw[...,:3][m]).mean())
                if best is None or mae < best[0]: best = (mae, dx, dy)
        m0 = (B[...,3]>200) & (W[...,3]>200)
        mae0 = float(np.abs(B[...,:3][m0] - W[...,:3][m0]).mean())
        print("r%dc%d best=(%+d,%+d)  MAE %.2f -> %.2f" % (r, c, best[1], best[2], mae0, best[0]))
```

### A.5 base가 픽셀아트인지 검사

```python
from PIL import Image
from collections import Counter
b = Image.open('char/v2/body_bald.png').convert('RGBA'); px = b.load(); W, H = b.size
print('unique opaque colors:', len({px[x,y] for y in range(H) for x in range(W) if px[x,y][3] > 200}))
runs = Counter()
for y in range(0, H, 7):
    x = 0
    while x < W:
        c = px[x,y]; n = 1
        while x+n < W and px[x+n,y] == c: n += 1
        if c[3] > 40: runs[n] += 1
        x += n
print('horizontal run-length dist:', runs.most_common(5))
```

### A.6 v2 출력이 실제로 배포되는지 확인

```python
import numpy as np
from PIL import Image
v2 = Image.open('tools/character-customizer/review_queue/top_ringer_20260709-155747/item.png').convert('RGBA')
ship = np.asarray(Image.open('char/items/top_ringer.png').convert('RGBA'))
for f, nm in [(Image.LANCZOS,'LANCZOS'), (Image.BICUBIC,'BICUBIC'), (Image.BOX,'BOX'), (Image.NEAREST,'NEAREST')]:
    d = np.asarray(v2.resize((423,896), f))
    A = ship[...,3] > 128; B = d[...,3] > 128
    print("shipped vs v2-down(%-8s) IoU = %.4f" % (nm, (A&B).sum()/max((A|B).sum(),1)))
```

---

## 부록 B — 측정 환경

- Python, Pillow, numpy 2.5.0, scipy 1.18.0 (OpenCV 미설치)
- 측정 대상 커밋: `70a95e2` (main), 작업 트리에 미커밋 변경 포함
- `char/v2/body_bald.png` = 846×1792 RGBA
- `review_queue/top_jersey_20260709-154511/source_original.png` = 1123×2400 RGBA
- `char/walk.png` = 423×896 (앱 런타임 베이스). `body_bald`와 정면 idle 실루엣 IoU = **0.991** → 같은 캐릭터, 정합 문제 없음
