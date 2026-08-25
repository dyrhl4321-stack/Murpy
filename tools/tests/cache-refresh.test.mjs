import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import assert from 'assert';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const html = readFileSync(join(root, 'index.html'), 'utf8');
const sw = readFileSync(join(root, 'sw.js'), 'utf8');
const version = readFileSync(join(root, 'version.txt'), 'utf8').trim();

// ★버전 숫자를 **박아두지 않는다** (2026-08-26). 배포할 때마다 이 테스트가 깨져서,
//   진짜 회귀인지 버전만 올라간 건지 구분이 안 됐다.
//   지켜야 할 진짜 규칙은 "네 곳이 서로 같다" 이다.
const idx = (html.match(/window\._SW_V = '(\d+)'/) || [])[1];
assert(idx, 'index.html 에서 _SW_V 를 못 찾았다');
assert.equal(version, idx, `version.txt(${version}) 가 index _SW_V(${idx}) 와 다르다`);
for (const name of ['murpy-v', 'murpy-static-v', 'murpy-cdn-v']) {
  const at = sw.indexOf(name);
  const got = at < 0 ? undefined
    : (sw.slice(at + name.length).match(/^[0-9]+/) || [])[0];
  assert.equal(got, idx, `sw.js 의 ${name} 가 v${idx} 가 아니다 (v${got})`);
}
assert(/Cache-Control" content="no-cache, no-store, must-revalidate/.test(html),
  '모바일 HTML 캐시 금지 메타가 없다');
assert(/version\.txt\?force=' \+ Date\.now\(\)/.test(html),
  '서버 버전 확인 주소가 매번 새 주소가 아니다');
assert(/mw_heal_attempt_/.test(html) && !/sessionStorage\.getItem\('mw_healed'\)/.test(html),
  '한 번 실패하면 영원히 업데이트를 막는 옛 self-heal 잠금이 남아 있다');
assert(/ks\.filter\(_mwCodeCache\)/.test(html), '강제 갱신이 실행 코드 캐시를 지우지 않는다');
assert(/controllerchange/.test(html) && /SKIP_WAITING/.test(html),
  '새 서비스워커 즉시 활성화와 제어권 전환 새로고침이 없다');
assert(/endsWith\('\/version\.txt'\)[\s\S]*endsWith\('\/sw\.js'\)[\s\S]*cache: 'no-store'/.test(sw),
  '서비스워커가 버전 표식과 자기 본체를 캐시에서 제외하지 않는다');
assert(/MURPY_SW_ACTIVATED/.test(sw) && /MURPY_SW_ACTIVATED/.test(html),
  '활성화된 서비스워커 버전을 열린 폰 화면에 알리지 않는다');

console.log('cache-refresh.test.mjs: 모바일 코드 캐시 강제 교체·즉시 활성화·1회 재진입 통과 OK');
