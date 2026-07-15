// 2026-07-15 헬스장 도감 시딩 — 대표 제공 8곳 (스포애니 구의역점 중복 1건 제거)
// 사용법: 배포 앱(https://dyrhl4321-stack.github.io/Murpy)을 PC 브라우저에서 열고
//        관리자 구글계정(dyrhl4321@gmail.com)으로 로그인 → F12 콘솔에 전체 붙여넣기 → Enter
// 이미 등록된 이름은 건너뛰므로 두 번 붙여넣어도 중복 생성되지 않음.
(async () => {
  const NEW_CENTERS = [
    { name: '요가바이아터스', type: '요가', loc: '송파',
      addr: '서울 송파구 송파대로 410 송연빌딩 2층',
      lat: 37.5040057855066, lng: 127.108752885848 },
    { name: '짐박스피트니스 송파점 (오픈예정)', type: '헬스', loc: '송파',
      addr: '서울 송파구 송파대로 393 짐박스 송파점 1-5층',
      lat: 37.5024149618841, lng: 127.109250676592 },
    { name: '머슬마인드 강남구청5호점', type: '헬스', loc: '논현',
      addr: '서울 강남구 논현동 119-2',
      lat: 37.5176875888336, lng: 127.04075806738 },
    { name: '스포애니 구의역점', type: '헬스', loc: '구의',
      addr: '서울 광진구 아차산로 362 3층~5층',
      lat: 37.5363778870111, lng: 127.082909138888 },
    { name: '휘트니스엠 천호점', type: '헬스', loc: '천호',
      addr: '서울 강동구 천호동 425-5',
      lat: 37.540602361470334, lng: 127.12485069635034 },
    { name: '엠케이휘트니스', type: '헬스', loc: '논현',
      addr: '서울 강남구 논현동 203',
      lat: 37.50608274357699, lng: 127.02808243085744 },
    { name: '짐박스피트니스 구로디지털단지점', type: '헬스', loc: '구로디지털',
      addr: '서울 구로구 구로동 188-25',
      lat: 37.4850671499381, lng: 126.89654361011 },
    { name: '신사 라이크짐 1호점', type: '헬스', loc: '잠원',
      addr: '서울 서초구 잠원동 20-5',
      lat: 37.51555316498836, lng: 127.01927446990018 }
  ];
  await window.loadCentersFirestore();
  const have = new Set((window.centersData || []).map(c => c.name));
  const list = NEW_CENTERS.filter(c => !have.has(c.name));
  const skipped = NEW_CENTERS.length - list.length;
  if (skipped) console.log(`이미 등록된 ${skipped}곳은 건너뜀`);
  if (!list.length) { console.log('전부 이미 등록되어 있어요. 시딩할 것 없음.'); return; }
  await window.seedCenters(list);
})();
