"""얼굴 방향 검사(score.facing_*) + 재시도 교정 프롬프트(pipeline.retry_hint). API·실데이터 없음.
Run: python -m unittest discover -s tests -v
★왜: 운영 커마 '윤이형' 이 왼쪽 걷기 행의 3번째 칸만 오른쪽을 봐서 걸을 때 좌우가 번갈아 뒤집혔다(9-14).
  기존 채점(칸 수·정합·잔상·옷)은 전부 통과시켰다 — 방향은 아무도 안 봤다."""
import unittest
import numpy as np
from facegen import score, pipeline

CW, CH = 141, 224
SKIN = (222, 176, 140, 255)   # _skin 판정에 걸리는 살색 (R>150, R>G+20, G>B, G−B<45)
HAIR = (40, 30, 25, 255)


def cell(direction):
    """합성 칸: 머리 = 검은 덩어리, 얼굴(살) = 그 안에서 한쪽으로 쏠린 사각형."""
    a = np.zeros((CH, CW, 4), np.uint8)
    a[20:100, 40:100] = HAIR
    if direction == 'front': a[40:95, 50:90] = SKIN
    elif direction == 'left': a[40:95, 40:66] = SKIN
    elif direction == 'right': a[40:95, 74:100] = SKIN
    return a


def sheet(rows):
    """rows = 행 4개, 각 행은 칸 3개의 방향 문자열('front'|'left'|'right'|'back')."""
    A = np.zeros((CH * 4, CW * 3, 4), np.uint8)
    for r, row in enumerate(rows):
        for c, d in enumerate(row):
            A[r*CH:(r+1)*CH, c*CW:(c+1)*CW] = cell(d)
    return A


class Facing(unittest.TestCase):
    def test_offset_sign(self):
        self.assertLess(score.facing_offset(cell('left')), -score.SIDE_MIN)
        self.assertGreater(score.facing_offset(cell('right')), score.SIDE_MIN)
        self.assertLess(abs(score.facing_offset(cell('front'))), score.FRONT_MAX)
        self.assertIsNone(score.facing_offset(cell('back')))   # 살이 없으면 판정 불가

    def test_good_sheet_passes(self):
        A = sheet([['front'] * 3, ['back'] * 3, ['left'] * 3, ['right'] * 3])
        self.assertEqual(score.facing_errors(A), [])

    def test_one_mirrored_walking_frame_is_caught(self):
        # 윤이형 사고 재현: 왼쪽 행의 3번째 칸만 오른쪽을 본다
        A = sheet([['front'] * 3, ['back'] * 3, ['left', 'left', 'right'], ['right'] * 3])
        errs = score.facing_errors(A)
        self.assertEqual(len(errs), 1); self.assertTrue(errs[0].startswith('r2c2+'), errs)
        v = score.verdict({'cells': 12, 'dy_max': 0, 'dx_max': 0, 'h_min': 1, 'h_max': 1, 'semi': 0, 'mag': 0,
                           'crown': 999, 'backface': 0, 'outfit': 0, 'clipped': 0, 'facing': errs})
        self.assertIn('방향r2c2', v)

    def test_swapped_rows_are_caught(self):
        A = sheet([['front'] * 3, ['back'] * 3, ['right'] * 3, ['left'] * 3])
        self.assertEqual(len(score.facing_errors(A)), 6)

    def test_missing_face_in_side_row_is_caught(self):
        A = sheet([['front'] * 3, ['back'] * 3, ['left', 'back', 'left'], ['right'] * 3])
        self.assertEqual(score.facing_errors(A), ['r2c1?'])


class RetryHint(unittest.TestCase):
    def test_ok_gives_no_hint(self):
        self.assertEqual(pipeline.retry_hint({'verdict': 'OK'}, 1), '')

    def test_facing_error_names_the_cells(self):
        h = pipeline.retry_hint({'verdict': '방향r2c2+16', 'facing': ['r2c2+16'], 'cells': 12}, 2)
        self.assertIn('RETRY #2', h); self.assertIn('LEFT profile', h); self.assertIn('r2c2+16', h)

    def test_hint_reaches_generator_and_plain_gen_fn_still_works(self):
        # 인자 2개짜리 gen_fn 은 hint 를 받고, 1개짜리(로컬 하네스)는 그대로 돈다 — 둘 다 '생성 실패' 로 끝나도 호출 형태만 본다
        import tempfile, os
        calls = []
        def gen2(i, hint=''):
            calls.append(('gen2', i, hint)); raise RuntimeError('stop')
        def gen1(i):
            calls.append(('gen1', i)); raise RuntimeError('stop')
        with tempfile.TemporaryDirectory() as td:
            for fn in (gen2, gen1):
                try: pipeline.process('k', b'', 'p', [], td, attempts=2, log=lambda *a: None, gen_fn=fn, base_path=os.path.join(pipeline.ASSETS, 'walk.png'))
                except RuntimeError: pass
        self.assertEqual([c[:2] for c in calls], [('gen2', 0), ('gen2', 1), ('gen1', 0), ('gen1', 1)])


if __name__ == '__main__': unittest.main()
