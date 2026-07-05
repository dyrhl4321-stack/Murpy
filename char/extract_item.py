# -*- coding: utf-8 -*-
"""
의상 아이템 추출기 — AI가 뽑아준 "우리 캐릭터가 ○○ 착용한 전신 시트"에서
그 아이템만 잘라내어, 우리 격자(3열×4행, 셀 141×224)에 정합된 레이어 시트로 만든다.

흐름: 전신시트를 우리 격자로 정규화(같은 키·바닥선) → 아이템 영역/색으로만 추출 →
      char/items/<out>.png (walk.png와 동일 규격) 저장. index.html CHAR_ITEMS에 sheet로 등록.

새 아이템: 아래 CONFIG만 바꿔서 실행. (모자류=상단영역+검정/흰색 식으로 부위별 조정)
"""
from PIL import Image
from collections import deque
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CW, CH = 141, 224          # 우리 격자 셀(사람 기준). walk.png와 동일해야 함.
TARGET_H, PAD_BOTTOM = 214, 4

# ===== 아이템별 설정 =====
CONFIG = dict(
    src=r"C:\Users\won\Desktop\김현수 컴카드\머피브랜딩\머피월드 캐릭터\캐릭터스프라이트시트\GBD모자 2-Photoroom.png",
    out="hat_gbd",
    # 소스 그리드(알파 투영으로 측정한 4행×3열 밴드). 필요시 detect_grid()로 재측정.
    rows=[(9, 250), (266, 506), (525, 762), (780, 1018)],
    cols=[(1, 159), (162, 320), (323, 482)],
    region=(0.02, 0.33),   # 아이템이 있는 셀 세로 비율(모자=상단). 상의면 대략 0.45~0.78 등.
    frame_col=0,           # 어느 열(프레임)을 대표로 뽑을지(모자는 프레임 무관 → idle=0, 3열에 복제)
)

def detect_grid(im):
    W, H = im.size; px = im.load()
    def band(vals, t=3):
        segs=[]; a=None
        for i,v in enumerate(vals):
            if v>t and a is None: a=i
            elif v<=t and a is not None: segs.append((a,i-1)); a=None
        if a is not None: segs.append((a,len(vals)-1))
        return [b for b in segs if b[1]-b[0]>30]
    rb=band([sum(1 for x in range(W) if px[x,y][3]>30) for y in range(H)])
    cb=band([sum(1 for y in range(H) if px[x,y][3]>30) for x in range(W)])
    return rb, cb

def largest(px, x0, y0, x1, y1):
    seen=set(); best=[]
    for sy in range(y0,y1):
        for sx in range(x0,x1):
            if px[sx,sy][3]>=40 and (sx,sy) not in seen:
                comp=[]; q=deque([(sx,sy)]); seen.add((sx,sy))
                while q:
                    cx,cy=q.popleft(); comp.append((cx,cy))
                    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                        nx,ny=cx+dx,cy+dy
                        if x0<=nx<x1 and y0<=ny<y1 and px[nx,ny][3]>=40 and (nx,ny) not in seen:
                            seen.add((nx,ny)); q.append((nx,ny))
                if len(comp)>len(best): best=comp
    return best

def norm_cell(px, cb, rb, r, c):
    """소스 (r,c) 셀의 캐릭터를 우리 셀(141×224, 키 214, 바닥정렬)로 정규화."""
    comp=largest(px, cb[c][0]-4, rb[r][0]-4, cb[c][1]+4, rb[r][1]+4)
    xs=[p[0] for p in comp]; ys=[p[1] for p in comp]
    bx0,bx1,by0,by1=min(xs),max(xs),min(ys),max(ys)
    im=Image.new("RGBA",(bx1-bx0+1,by1-by0+1),(0,0,0,0)); ip=im.load()
    for (x,y) in comp: ip[x-bx0,y-by0]=px[x,y]
    sc=min(TARGET_H/im.height,(CW-2)/im.width)
    im=im.resize((max(1,round(im.width*sc)),max(1,round(im.height*sc))),Image.LANCZOS)
    cell=Image.new("RGBA",(CW,CH),(0,0,0,0)); cell.alpha_composite(im,((CW-im.width)//2, CH-PAD_BOTTOM-im.height))
    return cell

def is_item_cap(px):
    """모자(검정 캡+흰 브림/글자) 판정. 갈색 머리는 제외(r>b 큼)."""
    r,g,b,a=px
    if a<60: return False
    br=max(r,g,b); mn=min(r,g,b)
    if br<98 and (br-mn)<24: return True   # 중성 어두움(검정)
    if mn>148: return True                  # 흰/크림
    return False

def _extract_region(cp, judge, y0f, y1f):
    item=Image.new("RGBA",(CW,CH),(0,0,0,0)); ip=item.load()
    for y in range(int(CH*y0f), int(CH*y1f)):
        for x in range(CW):
            if judge(cp[x,y]): ip[x,y]=cp[x,y]
    return item

def _extract_flood(cp, judge, y1f):
    """상단에서부터 judge 조건으로 연결된 덩어리만 채움 → 밑단이 실제 모양(아치)을 따라감.
    갈색머리·피부는 judge에서 걸러지고, 아래로 연결 안 된 외곽선 조각도 제외됨."""
    ycut=int(CH*y1f); filled=[[False]*CW for _ in range(CH)]; dq=deque()
    for y in range(0,8):
        for x in range(CW):
            if judge(cp[x,y]) and not filled[y][x]: filled[y][x]=True; dq.append((x,y))
    while dq:
        x,y=dq.popleft()
        for dx in(-1,0,1):
            for dy in(-1,0,1):
                nx,ny=x+dx,y+dy
                if 0<=nx<CW and 0<=ny<ycut and not filled[ny][nx] and judge(cp[nx,ny]):
                    filled[ny][nx]=True; dq.append((nx,ny))
    item=Image.new("RGBA",(CW,CH),(0,0,0,0)); ip=item.load()
    for y in range(ycut):
        for x in range(CW):
            if filled[y][x]: ip[x,y]=cp[x,y]
    return item

def _remove_small(item, minsz):
    """작은 연결덩어리(눈 하이라이트 등 잔여도트) 제거. 큰 파츠는 유지."""
    p=item.load(); seen=[[False]*CW for _ in range(CH)]; keep=Image.new("RGBA",(CW,CH),(0,0,0,0)); kp=keep.load()
    for sy in range(CH):
        for sx in range(CW):
            if p[sx,sy][3]>40 and not seen[sy][sx]:
                comp=[]; q=deque([(sx,sy)]); seen[sy][sx]=True
                while q:
                    x,y=q.popleft(); comp.append((x,y))
                    for dx in(-1,0,1):
                        for dy in(-1,0,1):
                            nx,ny=x+dx,y+dy
                            if 0<=nx<CW and 0<=ny<CH and not seen[ny][nx] and p[nx,ny][3]>40:
                                seen[ny][nx]=True; q.append((nx,ny))
                if len(comp)>=minsz:
                    for (x,y) in comp: kp[x,y]=p[x,y]
    return keep

def _dilate(item, r, ymin=0):
    """아이템을 r px 팽창(주변색으로 채움) → 밑옷 삐짐 덮기. ymin 아래(가슴~)만 팽창=얼굴 안 건드림."""
    out=item.copy()
    for _ in range(r):
        cur=out.copy(); cp=cur.load(); op=out.load()
        for y in range(ymin, CH):
            for x in range(CW):
                if cp[x,y][3]<40:
                    done=False
                    for dx in(-1,0,1):
                        for dy in(-1,0,1):
                            nx,ny=x+dx,y+dy
                            if 0<=nx<CW and 0<=ny<CH and cp[nx,ny][3]>=40:
                                op[x,y]=cp[nx,ny]; done=True; break
                        if done: break
    return out

def build(cfg, judge=is_item_cap):
    im=Image.open(cfg["src"]).convert("RGBA"); px=im.load()
    rb, cb = cfg["rows"], cfg["cols"]
    y0f,y1f=cfg["region"]
    mode=cfg.get("mode","region")   # 'region'=영역내 색추출 / 'flood'=상단연결덩어리(밑단 아치형)
    per_frame=cfg.get("per_frame", False)   # 상의류: 팔 움직여서 프레임별 추출(복제X)
    sheet=Image.new("RGBA",(CW*3, CH*4),(0,0,0,0))
    dil=cfg.get("dilate",0); minc=cfg.get("min_component",0)
    dil_ymin=int(CH*cfg.get("dilate_ymin",0))
    def extract(cp):
        it=_extract_flood(cp, judge, y1f) if mode=="flood" else _extract_region(cp, judge, y0f, y1f)
        if minc: it=_remove_small(it, minc)
        if dil:  it=_dilate(it, dil, dil_ymin)
        return it
    for r in range(4):
        if per_frame:
            for c in range(3):
                cell=norm_cell(px, cb, rb, r, c)
                sheet.alpha_composite(extract(cell.load()), (c*CW, r*CH))
        else:
            item=extract(norm_cell(px, cb, rb, r, cfg["frame_col"]).load())
            for c in range(3):   # 모자·악세: 걸음 중 안 움직임 → 동일 복제
                sheet.alpha_composite(item, (c*CW, r*CH))
    outp=os.path.join(HERE,"items",cfg["out"]+".png")
    sheet.save(outp); print("saved", outp, sheet.size)
    # 꾸미기 목록용 썸네일: 정면 프레임에서 아이템 내용만 잘라냄
    front=sheet.crop((0,0,CW,CH)); bb=front.getbbox()
    if bb:
        thumbp=os.path.join(HERE,"items",cfg["out"]+"_thumb.png")
        front.crop(bb).save(thumbp); print("saved", thumbp)

if __name__ == "__main__":
    build(CONFIG)
