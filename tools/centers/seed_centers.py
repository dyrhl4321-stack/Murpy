# 헬스장 시딩 관리 — 카톡으로 받은 블록을 그대로 붙여넣으면 시딩 파일이 나온다.
#
# 대표가 실제로 받는 양식 (2026-08-06 확인):
#     🏋️ 센터명 : 머슬마인드 강남구청5호점
#     📍 주소 : 서울 강남구 논현동 119-2
#     🌍 위도(Latitude)  : 37.5176875888336
#     🌎 경도(Longitude) : 127.04075806738
# 여러 개가 이어 붙어 있어도 되고, 이모지·공백·라벨 표기가 조금 달라도 읽는다.
#
# 쓰는 법
#     1) docs/seeds/centers_inbox.txt 에 카톡 내용을 그대로 붙여넣는다 (몇 개든)
#     2) python tools/centers/seed_centers.py
#     3) docs/seeds/centers.csv 가 갱신되고 docs/seeds/centers-seed.js 가 새로 만들어진다
#     4) 배포 앱을 PC 브라우저에서 열고 관리자로 로그인 → F12 콘솔에 seed.js 전체 붙여넣기
#
# ★좌표가 왜 반드시 필요한가: centers 문서에 lat/lng 이 없으면 GPS 200m 체크인 판정도,
#   지도 핀도 동작하지 않는다. index.html 의 등록 폼(registerCenter)은 좌표를 안 받기 때문에
#   그쪽으로 만든 센터는 반쪽짜리가 된다. 그래서 시딩은 이 경로로만 한다.
import csv
import os
import re
import sys
from datetime import date

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SEEDS = os.path.join(ROOT, "docs", "seeds")
INBOX = os.path.join(SEEDS, "centers_inbox.txt")
MASTER = os.path.join(SEEDS, "centers.csv")
OUT_JS = os.path.join(SEEDS, "centers-seed.js")

FIELDS = ["name", "type", "loc", "addr", "lat", "lng"]

# 한국 안인지 (좌표를 뒤집어 적는 실수가 제일 흔하다)
LAT_RANGE = (33.0, 39.0)
LNG_RANGE = (124.0, 132.0)

LABEL = {
    "name": re.compile(r"(센터\s*명|센터이름|이름|상호|헬스장)\s*[:：]\s*(.+)"),
    "addr": re.compile(r"(주소|도로명|소재지)\s*[:：]\s*(.+)"),
    "lat":  re.compile(r"(위도|latitude|lat)\b[^:：]*[:：]\s*([-\d.]+)", re.I),
    "lng":  re.compile(r"(경도|longitude|lng|lon)\b[^:：]*[:：]\s*([-\d.]+)", re.I),
}


def parse_inbox(text):
    """카톡 블록들을 읽는다. '센터명' 줄이 보이면 새 레코드로 친다."""
    recs, cur = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = LABEL["name"].search(line)
        if m:
            if cur:
                recs.append(cur)
            cur = {"name": m.group(2).strip()}
            continue
        if cur is None:
            continue
        for key in ("addr", "lat", "lng"):
            m = LABEL[key].search(line)
            if m:
                cur[key] = m.group(2).strip()
                break
    if cur:
        recs.append(cur)
    return recs


def guess_loc(addr):
    """주소에서 지역 라벨을 뽑는다 (강남구 -> 강남). 원하면 csv 에서 직접 고치면 된다."""
    m = re.search(r"([가-힣]+)(구|시|군)\s", addr + " ")
    return m.group(1) if m else ""


def normalize(rec, problems):
    name = (rec.get("name") or "").strip()
    if not name:
        return None
    addr = (rec.get("addr") or "").strip()
    try:
        lat = float(rec["lat"]); lng = float(rec["lng"])
    except (KeyError, ValueError):
        problems.append(f"[좌표없음] {name} — 위도/경도를 못 읽었습니다. 건너뜁니다.")
        return None

    # 위/경도를 바꿔 적은 경우 자동 교정 (한국은 경도가 항상 위도보다 크다)
    if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1]) and (LAT_RANGE[0] <= lng <= LAT_RANGE[1]):
        lat, lng = lng, lat
        problems.append(f"[교정] {name} — 위도/경도가 뒤바뀌어 있어 서로 바꿨습니다.")

    if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LNG_RANGE[0] <= lng <= LNG_RANGE[1]):
        problems.append(f"[범위밖] {name} — ({lat}, {lng}) 는 한국 밖입니다. 건너뜁니다.")
        return None

    return {"name": name, "type": rec.get("type") or "헬스",
            "loc": rec.get("loc") or guess_loc(addr), "addr": addr,
            "lat": f"{lat:.10f}".rstrip("0").rstrip("."),
            "lng": f"{lng:.10f}".rstrip("0").rstrip(".")}


def load_master():
    if not os.path.exists(MASTER):
        return []
    with open(MASTER, encoding="utf-8-sig", newline="") as f:
        return [dict(r) for r in csv.DictReader(f)]


def save_master(rows):
    os.makedirs(SEEDS, exist_ok=True)
    rows.sort(key=lambda r: (r.get("loc") or "", r["name"]))
    with open(MASTER, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})


def write_seed_js(rows):
    def esc(s):
        return str(s).replace("\\", "\\\\").replace("'", "\\'")
    lines = []
    for r in rows:
        lines.append(
            "    { name: '%s', type: '%s', loc: '%s',\n"
            "      addr: '%s',\n"
            "      lat: %s, lng: %s }" % (esc(r["name"]), esc(r["type"]), esc(r["loc"]),
                                          esc(r["addr"]), r["lat"], r["lng"]))
    body = ",\n".join(lines)
    js = f"""// 헬스장 도감 시딩 — tools/centers/seed_centers.py 가 만든 파일입니다. 직접 고치지 마세요.
// 원본은 docs/seeds/centers.csv (거기를 고치고 스크립트를 다시 돌리면 이 파일이 갱신됩니다)
// 생성일 {date.today().isoformat()} · 총 {len(rows)}곳
//
// 사용법: 배포 앱(https://murpy.app)을 PC 브라우저에서 열고 관리자 계정으로 로그인 →
//        F12 콘솔에 이 파일 전체를 붙여넣고 Enter.
//        이미 등록된 이름은 건너뛰므로 여러 번 붙여넣어도 중복 생성되지 않습니다.
(async () => {{
  const CENTERS = [
{body}
  ];
  await window.loadCentersFirestore();
  const have = new Set((window.centersData || []).map(c => c.name));
  const list = CENTERS.filter(c => !have.has(c.name));
  console.log(`전체 ${{CENTERS.length}}곳 · 이미 등록 ${{CENTERS.length - list.length}}곳 · 새로 넣을 것 ${{list.length}}곳`);
  if (!list.length) {{ console.log('시딩할 것이 없습니다.'); return; }}
  await window.seedCenters(list);
  console.log('완료. 체크인 탭에서 확인하세요.');
}})();
"""
    with open(OUT_JS, "w", encoding="utf-8", newline="\n") as f:
        f.write(js)


def main():
    master = load_master()
    by_name = {r["name"]: r for r in master}
    problems, added, dup = [], [], []

    if os.path.exists(INBOX):
        with open(INBOX, encoding="utf-8-sig") as f:
            raw = f.read()
        for rec in parse_inbox(raw):
            n = normalize(rec, problems)
            if not n:
                continue
            if n["name"] in by_name:
                dup.append(n["name"])
            else:
                by_name[n["name"]] = n
                added.append(n)
    else:
        print(f"※ {INBOX} 가 없습니다. 카톡 내용을 그 파일에 붙여넣고 다시 돌리세요.")

    rows = list(by_name.values())
    save_master(rows)
    write_seed_js(rows)

    print(f"\n마스터: {len(rows)}곳  ({MASTER})")
    if added:
        print(f"\n새로 추가 {len(added)}곳")
        for r in added:
            print(f"  + {r['name']}  [{r['loc']}]  ({r['lat']}, {r['lng']})")
    if dup:
        print(f"\n이미 있음 {len(dup)}곳 — 건너뜀")
        for n in dup:
            print(f"  = {n}")
    if problems:
        print("\n확인 필요")
        for p in problems:
            print("  ! " + p)
    print(f"\n시딩 파일: {OUT_JS}")
    if added:
        print("→ 배포 앱 F12 콘솔에 붙여넣으면 등록됩니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
