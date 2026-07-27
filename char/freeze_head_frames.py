# -*- coding: utf-8 -*-
"""3x4 걷기 시트에서 '머리(윗부분)'를 기준 프레임 하나로 고정한다.

왜 필요한가:
  AI가 만든 도트 시트는 프레임마다 머리카락을 조금씩 다르게 그린다. 삐친 머리 한 가닥이
  생겼다 없어지면서 재생 시 머리가 왔다갔다 한다(대표 지적 7-27, 좀비). 게다가 extract_hidden.py는
  셀마다 자기 bbox로 중앙정렬하므로, 그 한 가닥 때문에 프레임 전체가 좌우로 밀리기까지 한다.
  → 머리 영역만 한 프레임으로 통일하면 흔들림이 사라지고, 아래(팔·다리)는 그대로 움직인다.

자르는 높이(cut)는 행마다 다르게 준다:
  정면(row0)은 팔이 y95 아래에서 흔들리므로 얕게(95), 뒤·옆(row1~3)은 팔 움직임이 y150부터라
  깊게(130) 잘라도 손해가 없다. 깊게 자를수록 잔여 흔들림이 준다.
  좀비 실측: 머리부 불일치 [1186,3900,2354,2312] → cut[95,130,130,130]에서 [896,168,110,94].
  (row0의 896은 정면 팔 흔들림 = 정상 애니메이션이라 남겨야 한다)

사용:
  python char/freeze_head_frames.py char/hidden_zombie.png 142 --cuts 95,130,130,130 --ref 1
  --dry 를 붙이면 저장하지 않고 수치만 본다.

주의: 이 파일을 PowerShell로 고치지 말 것 — 한글 주석이 깨진다(Write 도구로 편집).
"""
import argparse

from PIL import Image

CH = 224          # 한 행(캐릭터) 높이. build_walk.py와 동일 규격
COLS, ROWS = 3, 4


def mismatch(img, cw, r, y0, y1):
    """행 r의 y0~y1에서 세 프레임 실루엣이 서로 다른 픽셀 수(= 흔들림 지표)."""
    px = img.load()
    d = 0
    for y in range(y0, y1):
        for x in range(cw):
            a = px[x, r * CH + y]
            b = px[cw + x, r * CH + y]
            c = px[2 * cw + x, r * CH + y]
            for p, q in ((a, b), (a, c), (b, c)):
                if (p[3] > 80) != (q[3] > 80):
                    d += 1
    return d


def freeze(img, cw, cuts, ref):
    out = img.copy()
    for r in range(ROWS):
        cut = cuts[r]
        if cut <= 0:
            continue
        head = img.crop((ref * cw, r * CH, ref * cw + cw, r * CH + cut))
        for c in range(COLS):
            if c == ref:
                continue
            # 대상 프레임의 머리 영역을 비우고 기준 머리를 얹는다(알파를 덮어써야 잔상이 안 남는다)
            out.paste((0, 0, 0, 0), (c * cw, r * CH, c * cw + cw, r * CH + cut))
            out.paste(head, (c * cw, r * CH))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('sheet')
    ap.add_argument('cw', type=int, help='셀 가로 폭(index.html _CHAR_BODIES의 cw와 같아야 함)')
    ap.add_argument('--cuts', default='95,130,130,130', help='행별 고정 높이(4개, 0이면 그 행은 건드리지 않음)')
    ap.add_argument('--ref', type=int, default=1, help='기준 프레임 인덱스(기본 1=가운데)')
    ap.add_argument('--dry', action='store_true')
    a = ap.parse_args()

    cuts = [int(v) for v in a.cuts.split(',')]
    assert len(cuts) == ROWS, 'cuts는 4개여야 합니다'

    im = Image.open(a.sheet).convert('RGBA')
    w, h = im.size
    assert h == CH * ROWS, '시트 높이가 %d가 아닙니다: %d' % (CH * ROWS, h)
    assert w >= a.cw * COLS, '시트 폭(%d)이 cw*3(%d)보다 작습니다' % (w, a.cw * COLS)

    before = [mismatch(im, a.cw, r, 0, 140) for r in range(ROWS)]
    out = freeze(im, a.cw, cuts, a.ref)
    after = [mismatch(out, a.cw, r, 0, 140) for r in range(ROWS)]
    legs = [mismatch(out, a.cw, r, 140, 220) for r in range(ROWS)]
    print('머리부 불일치  전: %s' % before)
    print('머리부 불일치  후: %s   (0에 가까울수록 안 흔들림)' % after)
    print('다리부 움직임 유지: %s   (이 값은 그대로여야 정상)' % legs)

    if a.dry:
        print('--dry 이므로 저장하지 않음')
        return
    # 원본 백업은 두지 않는다 — git이 곧 백업이다(되돌리려면 git checkout).
    out.save(a.sheet)
    print('저장: %s  → index.html의 ?v= 를 올려야 앱에 반영됩니다' % a.sheet)


if __name__ == '__main__':
    main()
