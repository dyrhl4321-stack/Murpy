"""Transaction bodies, independent of the Firebase runtime for regression tests."""
from urllib.parse import urlparse, unquote


def request_photo_path(url, uid, bucket):
    """Only the requesting user's uploaded source is a valid generation input."""
    parsed = urlparse(str(url or ''))
    prefix = '/v0/b/%s/o/' % bucket
    if parsed.scheme != 'https' or parsed.netloc != 'firebasestorage.googleapis.com' or not parsed.path.startswith(prefix):
        return None
    path = unquote(parsed.path[len(prefix):])
    if not path.startswith('uploads/%s/facereq_' % uid) or '..' in path.split('/'):
        return None
    return path


def claim_request(tx, ref, expected_t, claim_id, now):
    current = ref.get(transaction=tx).to_dict() or {}
    if current.get('status') != 'pending' or current.get('t') != expected_t:
        return None
    tx.update(ref, {'status': 'working', 'claimId': claim_id, 'startedAt': now})
    return current


def owns_claim(current, data, claim_id):
    return (current.get('status') == 'working'
            and current.get('t') == data.get('t')
            and current.get('claimId') == claim_id)


def complete_request(tx, ref, data, claim_id, char_ref, char_doc, notice_ref, notice, result):
    current = ref.get(transaction=tx).to_dict() or {}
    if not owns_claim(current, data, claim_id):
        return False
    tx.set(char_ref, char_doc)
    tx.update(ref, result)
    tx.set(notice_ref, notice)
    return True


def fail_request(tx, ref, data, claim_id, user_ref, refund, notice_ref, notice, result):
    current = ref.get(transaction=tx).to_dict() or {}
    if not owns_claim(current, data, claim_id):
        return False
    tx.update(user_ref, refund)
    tx.update(ref, result)
    tx.set(notice_ref, notice)
    return True


def recover_request(tx, ref, user_ref, notice_ref, now, refund, notice):
    """Use Firestore update time, not a client timestamp, to recover hard-crashed jobs."""
    snap = ref.get(transaction=tx)
    current = snap.to_dict() or {}
    if current.get('status') not in ('pending', 'working'):
        return {'status': 'finished'}
    updated = getattr(snap, 'update_time', None)
    if not updated or now - updated.timestamp() * 1000 < 15 * 60 * 1000:
        return {'status': 'active'}
    user = user_ref.get(transaction=tx).to_dict()
    if not user or user.get('deleted'): return {'status': 'missing_user'}
    tx.update(user_ref, refund)
    tx.update(ref, {'status': 'failed', 'error': '생성 시간이 초과되어 만들기 횟수를 돌려드렸어요',
                    'errorCode': 'timeout_recovered', 'doneAt': now})
    tx.set(notice_ref, notice)
    photos = current.get('photos') if isinstance(current.get('photos'), list) else []
    return {'status': 'recovered', 'sourceUrls': [current.get('photoUrl')] + photos}
