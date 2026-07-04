# walk.png 격자에 정확히 맞는 임시 의상 시트 생성(엔진 정합 검증용).
# 각 슬롯은 반투명 색 띠 + 셀마다 col/row 마커(desync 시 어긋남이 보이도록).
from PIL import Image, ImageDraw

SRC = "walk.png"           # char/ 에서 실행
COLS, ROWS = 3, 3
base = Image.open(SRC)
CW, CH = base.width // COLS, base.height // ROWS   # 셀 픽셀(예: 137 x 224)

# 슬롯별: (색 RGBA, 세로 밴드 y비율 start~end, 가로 x비율)
SLOTS = {
    "hat_ph":    ((60, 90, 240, 190), 0.06, 0.18, 0.30, 0.70),
    "hair_ph":   ((30, 30, 40, 170),  0.12, 0.30, 0.28, 0.72),
    "top_ph":    ((240, 80, 80, 175), 0.42, 0.62, 0.24, 0.76),
    "bottom_ph": ((80, 200, 120, 175),0.60, 0.80, 0.30, 0.70),
    "shoes_ph":  ((210, 160, 60, 190),0.82, 0.96, 0.28, 0.72),
}

def build(name, rgba, y0, y1, x0, x1):
    img = Image.new("RGBA", (base.width, base.height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for r in range(ROWS):
        for c in range(COLS):
            ox, oy = c * CW, r * CH
            # 의상 밴드
            d.rectangle([ox + CW * x0, oy + CH * y0, ox + CW * x1, oy + CH * y1], fill=rgba)
            # 디버그 마커: 좌상단에 col개 세로점 + row개 가로점 (프레임 desync 감지)
            for i in range(c + 1):
                d.rectangle([ox + 4 + i * 6, oy + 4, ox + 8 + i * 6, oy + 8], fill=(255, 255, 0, 255))
            for i in range(r + 1):
                d.rectangle([ox + 4, oy + 12 + i * 6, ox + 8, oy + 16 + i * 6], fill=(0, 255, 255, 255))
    img.save(f"items/{name}.png")
    print("saved", name, img.size)

import os
os.makedirs("items", exist_ok=True)
for name, args in SLOTS.items():
    build(name, *args)
