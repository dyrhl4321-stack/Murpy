// 머피월드 v2 레이어 규격 — 절대 하드코딩 값 임의 변경 금지
// 전체 시트 846x1792, 프레임 282x448, 3 columns(idle,walk1,walk2) x 4 rows(down,up,left,right)

export const SHEET_W = 846;
export const SHEET_H = 1792;
export const FRAME_W = 282;
export const FRAME_H = 448;
export const COLS = 3; // idle, walk1, walk2
export const ROWS = 4; // down, up, left, right

export const DIRS = ['down', 'up', 'left', 'right'];
export const STEPS = ['idle', 'walk1', 'walk2'];

// 레이어 순서 (아래 -> 위)
export const LAYER_ORDER = ['body', 'bottom', 'shoes', 'top', 'hair', 'hat', 'accessory'];

// 현재 준비된 v2 후보 에셋만 등록. 없는 슬롯은 빈 배열로 둔다(임의 채우기 금지).
export const V2_ASSETS = {
  body:      [{ id: 'body_bald',   name: '빡빡이 기본', path: '/char-v2/body_bald.png' }],
  hair:      [{ id: 'hair_default', name: '기본 헤어',   path: '/char-v2/hair_default.png' }],
  top:       [{ id: 'top_basic',   name: '기본 상의',   path: '/char-v2/top_basic.png' }],
  bottom:    [],
  shoes:     [],
  hat:       [],
  accessory: [],
};

export function frameIndex(dirIndex, stepIndex) {
  return dirIndex * COLS + stepIndex;
}
