// 헬스장 도감 시딩 — tools/centers/seed_centers.py 가 만든 파일입니다. 직접 고치지 마세요.
// 원본은 docs/seeds/centers.csv (거기를 고치고 스크립트를 다시 돌리면 이 파일이 갱신됩니다)
// 생성일 2026-08-07 · 총 12곳
//
// 사용법: 배포 앱(https://murpy.app)을 PC 브라우저에서 열고 관리자 계정으로 로그인 →
//        F12 콘솔에 이 파일 전체를 붙여넣고 Enter.
//        이미 등록된 이름은 건너뛰므로 여러 번 붙여넣어도 중복 생성되지 않습니다.
(async () => {
  const CENTERS = [
    { name: '짐박스피트니스 일원역점', type: '헬스', loc: '강남',
      addr: '서울 강남구 일원동 717',
      lat: 37.4840740343, lng: 127.0844520898 },
    { name: '짐박스피트니스 사당2호점', type: '헬스', loc: '관악',
      addr: '서울 관악구 남현동 1059-16',
      lat: 37.4761293317, lng: 126.9790624656 },
    { name: '짐박스피트니스 구로디지털단지점', type: '헬스', loc: '구로디지털',
      addr: '서울 구로구 구로동 188-25',
      lat: 37.4850671499381, lng: 126.89654361011 },
    { name: '스포애니 구의역점', type: '헬스', loc: '구의',
      addr: '서울 광진구 아차산로 362 3층~5층',
      lat: 37.5363778870111, lng: 127.082909138888 },
    { name: '머슬마인드 강남구청5호점', type: '헬스', loc: '논현',
      addr: '서울 강남구 논현동 119-2',
      lat: 37.5176875888336, lng: 127.04075806738 },
    { name: '엠케이휘트니스', type: '헬스', loc: '논현',
      addr: '서울 강남구 논현동 203',
      lat: 37.50608274357699, lng: 127.02808243085744 },
    { name: '짐박스피트니스 사당1호점', type: '헬스', loc: '동작',
      addr: '서울 동작구 사당동 1030-20',
      lat: 37.4804095268, lng: 126.9814581452 },
    { name: '요가바이아터스', type: '요가', loc: '송파',
      addr: '서울 송파구 송파대로 410 송연빌딩 2층',
      lat: 37.5040057855066, lng: 127.108752885848 },
    { name: '짐박스피트니스 송파점 (오픈예정)', type: '헬스', loc: '송파',
      addr: '서울 송파구 송파대로 393 짐박스 송파점 1-5층',
      lat: 37.5024149618841, lng: 127.109250676592 },
    { name: '신사 라이크짐 1호점', type: '헬스', loc: '잠원',
      addr: '서울 서초구 잠원동 20-5',
      lat: 37.51555316498836, lng: 127.01927446990018 },
    { name: '휘트니스엠 천호점', type: '헬스', loc: '천호',
      addr: '서울 강동구 천호동 425-5',
      lat: 37.540602361470334, lng: 127.12485069635034 },
    { name: '짐맥스', type: '헬스', loc: '하남',
      addr: '경기 하남시 망월동 1129-1',
      lat: 37.5632074735, lng: 127.1942108156 }
  ];
  await window.loadCentersFirestore();
  const have = new Set((window.centersData || []).map(c => c.name));
  const list = CENTERS.filter(c => !have.has(c.name));
  console.log(`전체 ${CENTERS.length}곳 · 이미 등록 ${CENTERS.length - list.length}곳 · 새로 넣을 것 ${list.length}곳`);
  if (!list.length) { console.log('시딩할 것이 없습니다.'); return; }
  await window.seedCenters(list);
  console.log('완료. 체크인 탭에서 확인하세요.');
})();
