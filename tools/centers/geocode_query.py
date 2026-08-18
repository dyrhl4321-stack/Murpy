# 헬스장 이름/주소를 카카오 로컬 API로 찾아 좌표 후보를 뽑는다 (DB 에 안 쓴다).
#
# 왜 이 도구가 따로 있나
#   geocode_missing.py 는 **이미 운영 DB 에 있는데 좌표만 없는** 센터를 채우는 도구다.
#   새로 추가할 곳은 아직 DB 에 없어서 그걸로는 못 찾는다. 그래서 이름/주소를 직접 넣는 판이 필요하다.
#
# ★왜 카카오여야 하나 (2026-08-07·08-19 두 번 실측)
#   OSM Nominatim 은 한국 헬스장 POI 를 하나도 못 찾는다(6/6 실패). 도로명도 건물 단위로는 안 나온다.
#   MapTiler 키는 도메인 제한이 걸려 지오코딩이 막혀 있다.
#   ★구·동 중심 좌표로 대충 채우면 **안 된다** — 체크인 반경이 200m 라 엉뚱한 자리에서 체크인이 되고
#     정작 그 헬스장에서는 안 된다. 없는 것보다 나쁘다.
#
# 준비물: 카카오 REST API 키 (JS 키와 다르다)
#   developers.kakao.com → 내 애플리케이션 → 앱 키 → **REST API 키**
#   $env:KAKAO_REST_KEY = "붙여넣기"          (PowerShell)
#   export KAKAO_REST_KEY="붙여넣기"          (bash)
#
# 쓰는 법
#   python tools/centers/geocode_query.py "바디메이트짐 면목점" "에이블짐 신논현역점"
#   python tools/centers/geocode_query.py --addr "서울 중랑구 상봉로 7"
#
# ★자동으로 DB 에 쓰지 않는다. 이름만 비슷한 다른 지점이 잡히는 일이 흔해서
#   반드시 사람이 한 번 보고 넘겨야 한다(대표 승인 규칙).
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

KAKAO = os.environ.get("KAKAO_REST_KEY", "").strip()


def _get(path, params):
    url = "https://dapi.kakao.com/v2/local/" + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": "KakaoAK " + KAKAO})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def search_keyword(q):
    return _get("search/keyword.json", {"query": q, "size": 5}).get("documents", [])


def search_address(q):
    return _get("search/address.json", {"query": q, "size": 5}).get("documents", [])


def show(q, by_addr=False):
    print("=" * 72)
    print("검색: %s   (%s)" % (q, "주소" if by_addr else "키워드"))
    try:
        docs = search_address(q) if by_addr else search_keyword(q)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:200]
        print("  ! HTTP %s — %s" % (e.code, body))
        if e.code == 401:
            print("  ! REST API 키가 틀렸거나 안 넣었다. JS 키가 아니라 **REST API 키** 여야 한다.")
        return
    except Exception as e:
        print("  ! 실패:", e)
        return
    if not docs:
        print("  결과 없음")
        return
    for i, d in enumerate(docs, 1):
        if by_addr:
            name = d.get("address_name", "")
            road = (d.get("road_address") or {}).get("address_name", "")
            cat = ""
        else:
            name = d.get("place_name", "")
            road = d.get("road_address_name") or d.get("address_name", "")
            cat = d.get("category_name", "").split(">")[-1].strip()
        # 카카오는 x=경도(lng), y=위도(lat) 다. 뒤집으면 지구 반대편이 된다.
        lat, lng = d.get("y"), d.get("x")
        print("  %d) %s  [%s]" % (i, name, cat))
        print("     %s" % road)
        print("     lat: %s, lng: %s" % (lat, lng))
        if d.get("phone"):
            print("     %s" % d["phone"])


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    args = sys.argv[1:]
    if not KAKAO:
        print("KAKAO_REST_KEY 환경변수가 없다.")
        print("  developers.kakao.com → 내 애플리케이션 → 앱 키 → REST API 키")
        print('  PowerShell:  $env:KAKAO_REST_KEY = "키"')
        print('  bash:        export KAKAO_REST_KEY="키"')
        sys.exit(2)
    if not args:
        print("쓰는 법: python tools/centers/geocode_query.py \"헬스장 이름\" [...]")
        print("        python tools/centers/geocode_query.py --addr \"도로명 주소\"")
        sys.exit(2)
    by_addr = False
    for a in args:
        if a == "--addr":
            by_addr = True
            continue
        show(a, by_addr)
        time.sleep(0.3)
    print("=" * 72)
    print("★눈으로 확인한 것만 index.html 의 window._ADD_CENTERS 에 옮길 것.")
    print("  지점명이 비슷한 다른 곳이 잡히는 일이 흔하다. 주소가 맞는지 꼭 대조할 것.")


if __name__ == "__main__":
    main()
