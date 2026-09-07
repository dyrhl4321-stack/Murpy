# -*- coding: utf-8 -*-
"""얼굴 커스터마이징 — 신청(faceRequests/{uid}) 이 생기면 서버가 캐릭터를 만들어 바로 지급한다 (2026-09-06).

흐름: pending → working → (facegen.pipeline) → Storage faces/{uid}/{charId}/* 업로드
      → users/{uid}/faceChars/{charId} 문서 → faceRequests 'done' + 알림 face_done
      실패하면 'failed' + 만들기 횟수 환불 + 알림 face_failed. 신청 셀카(uploads/…/facereq_*)는 끝나면 지운다("만든 뒤에는 지워요").
비공개 재료(프롬프트·생성용 base 시트)는 Storage private/face/ 에서 읽는다 — 이 저장소는 공개라 여기 못 둔다.
제미나이 키 = Secret Manager GEMINI_API_KEY.
배포: firebase.json 의 codebase 'face' (python312). `firebase deploy --only functions:face`
"""
import os, time, uuid, json, tempfile, urllib.request, urllib.parse
from firebase_functions import firestore_fn, options
from firebase_functions.params import SecretParam
from firebase_admin import initialize_app, firestore, storage
from facegen.jobs import claim_request, complete_request, fail_request, request_photo_path

GEMINI = SecretParam('GEMINI_API_KEY')
initialize_app()
options.set_global_options(region='asia-northeast3')

BUCKET = 'murpyprototype.firebasestorage.app'

# 클라이언트가 보내는 건 아래 네 코드뿐이다. 자유문장을 프롬프트에 붙이지 않는다(프롬프트 주입 방지).
# 핵심 생성 프롬프트는 계속 비공개 Storage 에 두고, 여기서는 사용자가 고른 머리 방향만 좁게 덧붙인다.
HAIR_PREFS = {
    'as_photo': '',
    'forehead': ('Hairstyle requirement: keep the same person and hair color, but style the front hair up or swept back '
                 'so the forehead is clearly visible. Preserve that exact hairstyle consistently in all 12 cells and all four directions.'),
    'bangs': ('Hairstyle requirement: use natural front bangs covering part of the forehead. '
              'Preserve that exact hairstyle consistently in all 12 cells and all four directions.'),
    'tied': ('Hairstyle requirement: wear the hair tied up or tied back, with no loose long hair falling over the chest. '
             'The tied shape must remain visible and consistent from the front, back, left, and right in all 12 cells.')
}

def _prompt_with_hair(prompt, pref):
    """허용된 머리 프리셋만 비공개 기본 프롬프트 뒤에 붙인다."""
    extra = HAIR_PREFS.get(str(pref or 'as_photo'), '')
    return prompt if not extra else prompt.rstrip() + '\n\n' + extra

def _download(url, timeout=60):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        ctype = r.headers.get('Content-Type', 'image/jpeg').split(';')[0]
        return ctype, r.read()

def _upload(bucket, path, local, ctype='image/png'):
    """Firebase 다운로드 URL(토큰) 로 올린다 — 규칙과 무관하게 <img src> 로 바로 쓸 수 있다."""
    blob = bucket.blob(path); token = uuid.uuid4().hex
    blob.metadata = {'firebaseStorageDownloadTokens': token}
    blob.upload_from_filename(local, content_type=ctype)
    return 'https://firebasestorage.googleapis.com/v0/b/%s/o/%s?alt=media&token=%s' % (bucket.name, urllib.parse.quote(path, safe=''), token)

def _delete_by_url(bucket, url, uid):
    """uploads/{uid}/facereq_*.jpg 처럼 우리 버킷의 다운로드 URL 이면 지운다. 그 외(프로필 사진)는 손대지 않는다."""
    try:
        path = request_photo_path(url, uid, bucket.name)
        if not path: return
        bucket.blob(path).delete()
    except Exception: pass

@firestore_fn.on_document_written(document='faceRequests/{uid}', secrets=[GEMINI],
                                  memory=options.MemoryOption.GB_2, timeout_sec=540, cpu=2)
def face_generate(event):
    # ★'생성' 트리거는 두 번째 신청(같은 uid 문서 갱신)에 안 깨어난다(9-07 대표 신청이 '만드는 중'에 멈춤).
    #   '쓰기'로 받고, status 가 pending 이면서 신청 시각 t 가 바뀐 경우만 새 신청으로 본다.
    uid = event.params['uid']
    after = event.data.after.to_dict() if (event.data and event.data.after and event.data.after.exists) else None
    before = event.data.before.to_dict() if (event.data and event.data.before and event.data.before.exists) else None
    if not after or after.get('status') != 'pending': return
    if before and before.get('status') == 'pending' and before.get('t') == after.get('t'): return
    db = firestore.client(); ref = db.collection('faceRequests').document(uid)
    claim_id = uuid.uuid4().hex
    # Firestore events may be delivered twice. Only one worker may own this exact request.
    data = firestore.transactional(claim_request)(db.transaction(), ref, after.get('t'), claim_id, int(time.time() * 1000))
    if data is None: return
    deadline = time.monotonic() + 450   # Leave time to upload/commit or atomically refund before the 540s hard timeout.
    bucket = None
    try:
        bucket = storage.bucket(BUCKET)
        from facegen import pipeline
        # 신청 화면의 캐시는 로그인 직후 비어 있을 수 있다. 몸통 선택은 신청값을 믿지 않고
        # users/{uid}.gender 를 다시 읽어 확정한다 — 빈 값이 남성 베이스로 떨어지는 사고 방지.
        profile = db.collection('users').document(uid).get().to_dict() or {}
        raw_gender = str(profile.get('gender') or data.get('gender') or '')
        if not raw_gender.startswith(('여', '남')):
            raise RuntimeError('프로필 성별을 확인한 뒤 다시 신청해주세요')
        gender = '여' if raw_gender.startswith('여') else '남'
        prompt = _prompt_with_hair(bucket.blob('private/face/prompt.txt').download_as_text(), data.get('hairPref'))
        base_png = bucket.blob('private/face/base_%s.png' % ('f' if gender == '여' else 'm')).download_as_bytes()
        urls = []
        for u in [data.get('photoUrl')] + [u for u in (data.get('photos') or []) if u]:
            if u and u not in urls: urls.append(u)
        urls = urls[:8]
        if any(not request_photo_path(u, uid, BUCKET) for u in urls):
            raise RuntimeError('본인 계정에서 올린 사진으로 다시 신청해주세요')
        selfies = []
        for u in urls:
            if not u: continue
            try: selfies.append(_download(u, timeout=20))
            except Exception as e: print('사진 실패', u[:80], e)
        if not selfies: raise RuntimeError('셀카를 하나도 못 받았다')
        with tempfile.TemporaryDirectory() as td:
            res = pipeline.process(GEMINI.value, base_png, prompt, selfies, td, attempts=4, log=print, base_path=pipeline.align_base(gender), deadline=deadline)
            # Global client registry keys must not collide for users finishing in the same second.
            char_id = 'f' + claim_id
            pre = 'faces/%s/%s/' % (uid, char_id)
            sheet_url = _upload(bucket, pre + 'sheet.png', res['sheet'])
            hair_url = _upload(bucket, pre + 'hair.png', res['hair']) if res.get('hair') else None
            skin_urls = {t: _upload(bucket, pre + 'skin_%s.png' % t, p) for t, p in res['skins'].items()}
        nick = '새 캐릭터'   # 이름은 유저가 도착 팝업에서 짓는다(닉네임을 그대로 쓰니 대표가 '마음대로 패수현' 이라 함, 9-07)
        char_doc = {
            'name': nick, 'sheetUrl': sheet_url, 'hairUrl': hair_url, 'skinUrls': skin_urls, 'eyes': res['eyes'],
            'gender': gender, 'kin': 'human_f' if gender == '여' else 'human', 'requestT': data.get('t'),
            'retryCount': res['attempts'], 'verdict': res['verdict'], 'createdAt': int(time.time() * 1000), 'updatedAt': int(time.time() * 1000)}
        committed = firestore.transactional(complete_request)(db.transaction(), ref, data, claim_id,
            db.collection('users').document(uid).collection('faceChars').document(char_id), char_doc,
            db.collection('notifications').document(),
            {'toUid': uid, 'type': 'face_done', 'charId': char_id, 'fromUid': '', 'fromNickname': '머피',
             'read': False, 'createdAt': firestore.SERVER_TIMESTAMP},
            {'status': 'done', 'charId': char_id, 'resolvedGender': gender, 'doneAt': int(time.time() * 1000),
             'verdict': res['verdict'], 'scores': json.dumps(res['scores'], ensure_ascii=False)[:4000]})
        if not committed:
            print('stale face completion ignored', uid, claim_id)
            return
        for u in [data.get('photoUrl')] + list(data.get('photos') or []): _delete_by_url(bucket, u, uid)   # 본인 신청용 사진만 지운다
        print('완료', uid, char_id, res['verdict'], '시도', res['attempts'])
    except Exception as e:
        print('실패', uid, repr(e)[:400])
        # Status + refund + notice are atomic; a duplicate event or post-success exception cannot refund twice.
        refunded = firestore.transactional(fail_request)(db.transaction(), ref, data, claim_id,
            db.collection('users').document(uid), {'faceTickets': firestore.Increment(1)},
            db.collection('notifications').document(),
            {'toUid': uid, 'type': 'face_failed', 'fromUid': '', 'fromNickname': '머피',
             'read': False, 'createdAt': firestore.SERVER_TIMESTAMP},
            {'status': 'failed', 'error': str(e)[:300], 'doneAt': int(time.time() * 1000)})
        if not refunded: return
        if bucket:
            for u in [data.get('photoUrl')] + list(data.get('photos') or []): _delete_by_url(bucket, u, uid)
