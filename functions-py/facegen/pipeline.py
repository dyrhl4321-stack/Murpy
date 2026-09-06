# -*- coding: utf-8 -*-
"""얼굴 커스터마이징 서버 파이프라인 — 셀카 → 시트·헤어·피부톤·눈 좌표 (2026-09-06).

process(...) 한 번이 유저 한 명이다:
  1) 생성(제미나이) → 2) 칸 단위 규격화 + 배경 잔상 수술(grid) → 3) 헤어 레이어 자동(hair)
  → 4) 채점(score). OK 가 아니면 1) 부터 다시, 최대 attempts 회. 끝까지 OK 가 없으면 결함이 가장 적은 것.
  → 5) 피부톤 5종(skin) → 6) 눈 좌표(eyes)
★한 번에 잘 뽑히는 비율이 1/3(기준 프롬프트)~3/3(개정 프롬프트, 9-06 백테스트)라 재시도가 곧 품질이다.
  대표 손을 하나도 안 거치는 게 목적(대표 9-06: "그냥 자동으로 다 해야 해").
"""
import os, io, json
from PIL import Image
from . import grid, hair, eyes, score, skin
from .gen import generate

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')

def align_base(gender):
    """정합·채점 기준 = **앱의 base 시트**(char/walk.png). 생성 참고용 시트(마젠타 배경)와 다르다 —
    그걸 기준으로 맞추면 11px 어긋나고 채점이 전부 '옷바뀜'으로 나온다(9-06 로컬 하네스 실측)."""
    return os.path.join(ASSETS, 'walk_female.png' if gender == '여' else 'walk.png')

def process(key, base_png, prompt, selfies, out_dir, attempts=3, log=print, gen_fn=None, base_path=None):
    """base_png = 생성 참고용 시트(제미나이에 첨부) · base_path = 정합/채점 기준 앱 시트(기본 남성 walk.png).
    돌려주는 값 = dict(sheet, hair, skins{t:path}, eyes, verdict, attempts, scores[]). 파일은 out_dir 아래."""
    os.makedirs(out_dir, exist_ok=True)
    base_path = base_path or align_base('남')
    gen_fn = gen_fn or (lambda i: generate(key, base_png, selfies, prompt))
    best = None; scores = []
    for i in range(attempts):
        raw_path = os.path.join(out_dir, 'raw_%d.png' % (i + 1))
        try:
            data = gen_fn(i)
            Image.open(io.BytesIO(data)).convert('RGBA').save(raw_path)
        except Exception as e:
            log('  생성 %d 실패: %s' % (i + 1, e)); scores.append({'attempt': i + 1, 'error': str(e)[:200]}); continue
        ai_path = os.path.join(out_dir, 'ai_%d.png' % (i + 1))
        try:
            grid.regrid_cells(raw_path, base_path, ai_path)
        except SystemExit as e:
            log('  규격화 %d 실패: %s' % (i + 1, e)); scores.append({'attempt': i + 1, 'error': 'regrid ' + str(e)[:200]}); continue
        hair_path = os.path.join(out_dir, 'hair_%d.png' % (i + 1))
        kind, hair_px = hair.extract_auto(ai_path, hair_path)          # 헤어는 **이식 전** AI 시트에서(긴 머리 포함)
        if not hair_px: hair_path = None
        # ★얼굴만 바꾼다: 목선 위 = AI, 목선 아래 = base 픽셀 그대로 → 속옷·몸이 바뀔 길이 없다(대표 9-07)
        grafted = os.path.join(out_dir, 'sheet_%d.png' % (i + 1))
        grid.graft_head(ai_path, base_path, grafted)
        s = score.score(grafted, base_path, hair_px, fringe_src=ai_path); v = score.verdict(s)
        s.update({'attempt': i + 1, 'verdict': v, 'hairKind': kind}); scores.append(s)
        log('  시도 %d: %s' % (i + 1, v))
        bad = 0 if v == 'OK' else len(v.split())
        if best is None or bad < best['bad']:
            best = {'bad': bad, 'ai': grafted, 'hair': hair_path, 'verdict': v, 'attempt': i + 1}
        if v == 'OK': break
    if best is None:
        raise RuntimeError('생성이 전부 실패했다: ' + json.dumps(scores, ensure_ascii=False)[:500])
    # ★채점을 통과한 게 하나도 없으면 **내보내지 않는다** — '덜 나쁜 것'을 줬다가 흰 바지가 나갔다(9-07 대표: "제대로 걸러줘야 함").
    #   실패로 올리면 서버가 횟수를 환불하고 알림을 보낸다. 유저는 다시 신청하면 된다.
    if best['bad'] > 0:
        raise RuntimeError('품질 검사 통과 못 함(%d회): %s' % (len(scores), best['verdict']))
    # 피부톤 5종 — skin 모듈은 전역 OUT 에 쓴다(도구 시절 관례). 임시폴더로 돌려 쓴다.
    skin.OUT = out_dir
    skin.bake(best['ai'], 'skin')
    skins = {t: os.path.join(out_dir, 'skin_%s.png' % t) for t in ('t1', 't2', 't4', 't5', 't6')}
    skins = {t: p for t, p in skins.items() if os.path.exists(p)}
    ey = eyes.detect(best['ai'])
    return {'sheet': best['ai'], 'hair': best['hair'], 'skins': skins, 'eyes': ey,
            'verdict': best['verdict'], 'attempts': best['attempt'], 'scores': scores}
