# Murpy World v2 Basic Set — Review Criteria & Decisions

> ★ 방향 (2026-07-09): **v2 레이어 전면 전환은 장기 보류. 하이브리드로 운영.**
> 단기=나노바나나 착장 전체 스프라이트를 레거시 방식으로 앱에 빠르게 적용 → 중기=잘 나온 것만 아이템 레이어 추출 → 장기=세트 안정 후 v2 기본 전환.
> 아래 v2 자산/기준은 **폐기하지 말고 보관**. 앱 연결만 보류. 다음에 v2부터 다시 파지 말 것.

(2026-07 확정. v2 = 846×1792 / 프레임 282×448 / 3열 idle·walk1·walk2 × 4행 down·up·left·right. 레거시 423×896·현 앱 렌더는 무손상, 앱 연결은 보류.)

## 승인/유지
- `char/v2/body_bald.png` — 유지 (워터마크 제거본, 검수 OK)
- `char/v2/top_basic.png` — 유지 (nanobanana sian2 후보, 검수 OK)
- `char/v2/hair_default.png` — 유지하되 재검수 대상 (아래 참고)

## 폐기 (등록 금지, out/ 참고용으로만)
- top 실험 변형 전부: top_up2, backcollar, upshift → 폐기
  - 사유: top_up2는 목/턱이 답답, backcollar(뒤목 파란패치)·목 억지 올림은 어색

## top_basic 수정 규칙 (건드릴 경우에만)
- 전체 위치를 위/아래로 이동 금지
- 목 주변을 더 올리기 금지
- 뒤 목에 파란 패치 추가 금지
- 셔츠 형태 재생성 금지
- 현재 top_basic 기준 **아주 작은 픽셀 단위 보정만** 허용
- 기본 방침은 "현재 유지". 완벽해서가 아니라, reference 대비 가장 덜 어색하고 더 손대면 망가질 위험이 크기 때문.

## 남은 실제 문제 (top 아님)
1. hair_default 재검수
   - 검수 결과(2026-07): 뒷머리 실루엣 폭 ref 259px vs current 260px = 사실상 동일. near-white 노이즈 0.
   - "헬멧/둥글게 큼" 체감의 실제 원인 = 텍스처가 약간 매끈 + **하의·신발 부재로 인한 상하 불균형 착시**.
   - 결론: 헤어 단독 억지 수정보다 하의/신발 채운 뒤 전체 균형에서 재판단.
2. 하의/신발 미완성
   - 현재 v2 조합에 하의·신발 없어 하체가 비어 실루엣 어색.
   - Codex 자동추출 후보는 퀄리티 미흡 → 정식 등록 금지.
   - 대안: reference 캐릭터(out/v2_original_full_reference.png)에 이미 반바지+신발 존재 → 거기서 레이어 추출이 정합성 최선.

## 다음 검수 대상
- hair_default (back/up row) 또는 bottom/shoes. 우선순위: 하의/신발 → 균형 확인 → 헤어 재판단.
- 비교 기준 이미지: out/v2_reference_current_top_compare_4dir.png (reference | current | top_up2)

## 불변 원칙
- 나노바나나/Gemini 재생성 중단. 현재 v2 후보로 세트 구성.
- 앱 렌더러(index.html) 변경 보류 — 사용자 승인 후 별도 단계.
- 레거시 423×896 아이템·walk.png 무손상.
