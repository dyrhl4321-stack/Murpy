# 좌표 없는 센터를 카카오 로컬 API로 찾아 좌표를 채운다.
#
# 왜 필요한가
#   운영 DB 의 센터 중 상당수가 lat/lng 이 없다(6월 프로토타입 시절 데이터).
#   index.html 의 mwCheckin 은 `.filter(c => c && c.lat && c.lng)` 로 좌표 없는 센터를
#   **판정에서 통째로 제외**한다. 즉 목록엔 보이는데 체크인은 영영 안 되는 상태다.
#
# 왜 카카오인가
#   OSM Nominatim 으로 시험해봤더니 한국 헬스장 POI 는 하나도 안 나온다(2026-08-07 실측, 6/6 실패).
#   구·동 중심 좌표로 대충 채우는 것은 **하면 안 된다** — 체크인 반경이 200m 라
#   엉뚱한 자리에서 체크인이 되고 정작 그 헬스장에서는 안 된다. 없는 것보다 나쁘다.
#
# 준비물: 카카오 REST API 키 (JS 키와 다르다)
#   developers.kakao.com → 내 애플리케이션 → 앱 키 → **REST API 키** 복사
#   실행 전 환경변수로 넣는다:  $env:KAKAO_REST_KEY = "붙여넣기"
#
# 쓰는 법
#   python tools/centers/geocode_missing.py
#     → docs/seeds/geocode_review.txt   (사람이 눈으로 검수하는 후보 목록)
#     → docs/seeds/geocode_inbox.txt    (검수 통과분을 centers_inbox.txt 에 옮겨 붙이면 끝)
#
# ★자동으로 DB 에 쓰지 않는다. 이름만 비슷한 다른 지점이 잡히는 일이 흔해서,
#   반드시 사람이 한 번 보고 넘겨야 한다(대표 승인 규칙).
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SEEDS = os.path.join(ROOT, "docs", "seeds")
REVIEW = os.path.join(SEEDS, "geocode_review.txt")
OUTBOX = os.path.join(SEEDS, "geocode_inbox.txt")

FB_KEY = "AIzaSyBvMB4T-ApzHDsfmBx4f5HpPmgkqlcZ7VQ"
FB_URL = ("https://firestore.googleapis.com/v1/projects/murpyprototype"
          "/databases/(default)/documents/centers?key=%s&pageSize=300" % FB_KEY)

KAKAO = os.environ.get("KAKAO_REST_KEY", "").strip()


def fetch_centers():
    docs, token = [], None
    while True:
        url = FB_URL + ("&pageToken=" + token if token else "")
        with urllib.request.urlopen(url, timeout=20) as r:
            j = json.load(r)
        docs.extend(j.get("documents", []))
        token = j.get("nextPageToken")
        if not token:
            break
    out = []
    for d in docs:
        f = d.get("fields", {})
        def v(k):
            x = f.get(k)
            if not x:
                return None
            for t in ("stringValue", "doubleValue", "integerValue"):
                if t in x:
                    return x[t]
            return None
        out.append({"name": v("name") or "", "addr": v("addr") or "",
                    "loc": v("loc") or "", "type": v("type") or "헬스",
                    "lat": v("lat"), "lng": v("lng")})
    return out


def kakao_search(query):
    url = ("https://dapi.kakao.com/v2/local/search/keyword.json?size=5&query="
           + urllib.parse.quote(query))
    req = urllib.request.Request(url, headers={"Authorization": "KakaoAK " + KAKAO})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r).get("documents", [])


def norm(s):
    return re.sub(r"[\s()·\-]", "", s or "")


def main():
    if not KAKAO:
        print("KAKAO_REST_KEY 환경변수가 없습니다.")
        print('  PowerShell:  $env:KAKAO_REST_KEY = "REST API 키"')
        print("  키 위치: developers.kakao.com > 내 애플리케이션 > 앱 키 > REST API 키")
        return 1

    centers = fetch_centers()
    missing = [c for c in centers if not c["lat"] or not c["lng"]]
    print("전체 %d곳 · 좌표 없음 %d곳" % (len(centers), len(missing)))

    rows = []
    for i, c in enumerate(missing, 1):
        # loc(동네)을 붙여 검색 정확도를 올린다. 붙여서 못 찾으면 이름만으로 한 번 더.
        cands = []
        for qy in ([c["name"] + " " + c["loc"], c["name"]] if c["loc"] else [c["name"]]):
            try:
                cands = kakao_search(qy)
            except Exception as e:
                print("  ! %s 검색 실패: %s" % (c["name"], e))
                cands = []
            time.sleep(0.25)
            if cands:
                break
        rows.append({"center": c, "cands": cands})
        print("  [%d/%d] %-26s 후보 %d개" % (i, len(missing), c["name"], len(cands)))

    os.makedirs(SEEDS, exist_ok=True)
    rv, ib = io.StringIO(), io.StringIO()
    ib.write("# geocode_missing.py 결과. **눈으로 확인한 것만** centers_inbox.txt 로 옮기세요.\n")
    ib.write("# 이름이 비슷한 다른 지점이 잡히는 일이 흔합니다.\n\n")

    auto = 0
    for r in rows:
        c, cands = r["center"], r["cands"]
        rv.write("=" * 60 + "\n")
        rv.write("DB 이름 : %s   (지역 %s / 주소 %s)\n" % (c["name"], c["loc"] or "-", c["addr"] or "-"))
        if not cands:
            rv.write("  → 후보 없음. 직접 찾아 넣어야 합니다.\n\n")
            continue
        for k, d in enumerate(cands, 1):
            mark = ""
            # 이름이 사실상 같고 지역 힌트가 주소에 들어 있으면 '확실'로 본다
            if k == 1 and norm(c["name"]) == norm(d.get("place_name")) and \
               (not c["loc"] or c["loc"] in (d.get("address_name") or "") + (d.get("road_address_name") or "")):
                mark = "  ★이름 완전일치"
            rv.write("  %d) %s%s\n" % (k, d.get("place_name"), mark))
            rv.write("     %s\n" % (d.get("road_address_name") or d.get("address_name")))
            rv.write("     위도 %s / 경도 %s\n" % (d.get("y"), d.get("x")))
        rv.write("\n")

        d = cands[0]
        if norm(c["name"]) == norm(d.get("place_name")):
            auto += 1
        ib.write("센터명 : %s\n" % c["name"])
        ib.write("주소 : %s\n" % (d.get("road_address_name") or d.get("address_name")))
        ib.write("위도 : %s\n" % d.get("y"))
        ib.write("경도 : %s\n\n" % d.get("x"))

    io.open(REVIEW, "w", encoding="utf-8").write(rv.getvalue())
    io.open(OUTBOX, "w", encoding="utf-8").write(ib.getvalue())
    print("\n검수용 : %s" % REVIEW)
    print("옮길 것 : %s  (이름 완전일치 %d곳)" % (OUTBOX, auto))
    print("→ 검수 후 centers_inbox.txt 에 붙여넣고 python tools/centers/seed_centers.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
