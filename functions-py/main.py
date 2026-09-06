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

GEMINI = SecretParam('GEMINI_API_KEY')
initialize_app()
options.set_global_options(region='asia-northeast3')

BUCKET = 'murpyprototype.firebasestorage.app'

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

def _delete_by_url(bucket, url):
    """uploads/{uid}/facereq_*.jpg 처럼 우리 버킷의 다운로드 URL 이면 지운다. 그 외(프로필 사진)는 손대지 않는다."""
    try:
        m = urllib.parse.urlparse(url)
        if 'firebasestorage' not in m.netloc: return
        path = urllib.parse.unquote(m.path.split('/o/', 1)[1])
        if '/facereq_' not in path: return
        bucket.blob(path).delete()
    except Exception: pass

@firestore_fn.on_document_created(document='faceRequests/{uid}', secrets=[GEMINI],
                                  memory=options.MemoryOption.GB_2, timeout_sec=540, cpu=2)
def face_generate(event):
    uid = event.params['uid']
    data = event.data.to_dict() if event.data else None
    if not data or data.get('status') != 'pending': return
    db = firestore.client(); ref = db.collection('faceRequests').document(uid)
    ref.update({'status': 'working', 'startedAt': int(time.time() * 1000)})
    bucket = storage.bucket(BUCKET)
    from facegen import pipeline
    try:
        gender = '여' if str(data.get('gender', '')).startswith('여') else '남'
        prompt = bucket.blob('private/face/prompt.txt').download_as_text()
        base_png = bucket.blob('private/face/base_%s.png' % ('f' if gender == '여' else 'm')).download_as_bytes()
        urls = [data.get('photoUrl')] + [u for u in (data.get('photos') or []) if u][:7]
        selfies = []
        for u in urls:
            if not u: continue
            try: selfies.append(_download(u))
            except Exception as e: print('사진 실패', u[:80], e)
        if not selfies: raise RuntimeError('셀카를 하나도 못 받았다')
        with tempfile.TemporaryDirectory() as td:
            res = pipeline.process(GEMINI.value, base_png, prompt, selfies, td, attempts=3, log=print, base_path=pipeline.align_base(gender))
            char_id = 'f%d' % int(time.time())
            pre = 'faces/%s/%s/' % (uid, char_id)
            sheet_url = _upload(bucket, pre + 'sheet.png', res['sheet'])
            hair_url = _upload(bucket, pre + 'hair.png', res['hair']) if res.get('hair') else None
            skin_urls = {t: _upload(bucket, pre + 'skin_%s.png' % t, p) for t, p in res['skins'].items()}
        nick = str(data.get('nick') or '내 캐릭터')[:12]
        db.collection('users').document(uid).collection('faceChars').document(char_id).set({
            'name': nick, 'sheetUrl': sheet_url, 'hairUrl': hair_url, 'skinUrls': skin_urls, 'eyes': res['eyes'],
            'retryCount': res['attempts'], 'verdict': res['verdict'], 'createdAt': int(time.time() * 1000), 'updatedAt': int(time.time() * 1000)})
        ref.update({'status': 'done', 'charId': char_id, 'doneAt': int(time.time() * 1000), 'verdict': res['verdict'],
                    'scores': json.dumps(res['scores'], ensure_ascii=False)[:4000]})
        db.collection('notifications').add({'toUid': uid, 'type': 'face_done', 'charId': char_id, 'fromUid': '', 'fromNickname': '머피',
                                            'read': False, 'createdAt': firestore.SERVER_TIMESTAMP})
        _delete_by_url(bucket, data.get('photoUrl'))
        print('완료', uid, char_id, res['verdict'], '시도', res['attempts'])
    except Exception as e:
        print('실패', uid, repr(e)[:400])
        ref.update({'status': 'failed', 'error': str(e)[:300], 'doneAt': int(time.time() * 1000)})
        # 만들기 횟수 환불 — 신청 때 한 트랜잭션으로 뺀 1회를 돌려준다
        try: db.collection('users').document(uid).update({'faceTickets': firestore.Increment(1)})
        except Exception as e2: print('환불 실패', e2)
        db.collection('notifications').add({'toUid': uid, 'type': 'face_failed', 'fromUid': '', 'fromNickname': '머피',
                                            'read': False, 'createdAt': firestore.SERVER_TIMESTAMP})
        _delete_by_url(bucket, data.get('photoUrl'))
