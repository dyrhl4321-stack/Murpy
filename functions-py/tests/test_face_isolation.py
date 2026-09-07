"""No API calls or real user data. Run: python -m unittest discover -s tests -v"""
import copy
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from facegen import skin, jobs


class Ref:
    def __init__(self, value=None): self.value = copy.deepcopy(value or {})
    def get(self, transaction=None): return self
    def to_dict(self): return copy.deepcopy(self.value)


class Tx:
    def __init__(self): self.writes = []
    def update(self, ref, value):
        self.writes.append((ref, value)); ref.value.update(value)
    def set(self, ref, value):
        self.writes.append((ref, value)); ref.value = copy.deepcopy(value)


class FaceIsolation(unittest.TestCase):
    def test_source_and_cleanup_are_bound_to_request_owner(self):
        prefix = 'https://firebasestorage.googleapis.com/v0/b/my-bucket/o/'
        good = prefix + 'uploads%2Falice%2Ffacereq_123.jpg?alt=media&token=test'
        self.assertEqual(jobs.request_photo_path(good, 'alice', 'my-bucket'), 'uploads/alice/facereq_123.jpg')
        for invalid in [good.replace('alice', 'bob'), good.replace('my-bucket', 'other-bucket'),
                        good.replace('facereq_', 'profile_'), good.replace('https:', 'http:'),
                        good.replace('.googleapis.com', '.googleapis.com.evil.example')]:
            self.assertIsNone(jobs.request_photo_path(invalid, 'alice', 'my-bucket'))

    def test_parallel_skin_files_belong_to_their_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sources = []
            for i, color in enumerate([(245, 169, 125, 255), (30, 80, 210, 255)]):
                src = root / ('source%d.png' % i)
                Image.new('RGBA', (8, 12), color).save(src); sources.append(src)
                skin.bake(src, 'skin', out_dir=root / ('expected%d' % i))
            save = Image.Image.save
            barrier = threading.Barrier(2, timeout=5)
            def synchronized_save(im, fp, *args, **kwargs):
                barrier.wait()  # both jobs reach each tone with the exact same output basename
                return save(im, fp, *args, **kwargs)
            with patch.object(Image.Image, 'save', synchronized_save), ThreadPoolExecutor(2) as pool:
                futures = [pool.submit(skin.bake, src, 'skin', out_dir=root / ('actual%d' % i))
                           for i, src in enumerate(sources)]
                for f in futures: f.result(timeout=15)
            for i in range(2):
                for tone in skin.TONES:
                    name = 'skin_%s.png' % tone
                    self.assertEqual((root / ('expected%d' % i) / name).read_bytes(),
                                     (root / ('actual%d' % i) / name).read_bytes())

    def test_duplicate_event_cannot_claim_twice(self):
        ref = Ref({'status': 'pending', 't': 10, 'photoUrl': 'my-photo'})
        first = jobs.claim_request(Tx(), ref, 10, 'worker-a', 11)
        self.assertEqual(first['photoUrl'], 'my-photo')
        tx = Tx()
        self.assertIsNone(jobs.claim_request(tx, ref, 10, 'worker-b', 12))
        self.assertEqual(tx.writes, [])

    def test_old_event_cannot_claim_new_request(self):
        ref = Ref({'status': 'pending', 't': 20})
        tx = Tx()
        self.assertIsNone(jobs.claim_request(tx, ref, 10, 'old-worker', 21))
        self.assertEqual(tx.writes, [])

    def test_stale_worker_cannot_deliver_or_refund(self):
        ref = Ref({'status': 'working', 't': 20, 'claimId': 'new'})
        for fn in (jobs.complete_request, jobs.fail_request):
            tx = Tx()
            self.assertFalse(fn(tx, ref, {'t': 10}, 'old', Ref(), {}, Ref(), {}, {}))
            self.assertEqual(tx.writes, [])

    def test_success_cannot_refund_after_notification_error(self):
        ref = Ref({'status': 'working', 't': 10, 'claimId': 'a'})
        char, notice = Ref(), Ref()
        tx = Tx()
        self.assertTrue(jobs.complete_request(tx, ref, {'t': 10}, 'a', char,
            {'gender': '여', 'kin': 'human_f'}, notice, {'type': 'face_done'}, {'status': 'done'}))
        self.assertEqual(len(tx.writes), 3)
        self.assertEqual(char.value['kin'], 'human_f')
        tx = Tx()
        self.assertFalse(jobs.fail_request(tx, ref, {'t': 10}, 'a', Ref(), {}, Ref(), {}, {'status': 'failed'}))
        self.assertEqual(tx.writes, [])

    def test_failure_refunds_only_once(self):
        ref = Ref({'status': 'working', 't': 10, 'claimId': 'a'})
        user, notice, tx = Ref(), Ref(), Tx()
        self.assertTrue(jobs.fail_request(tx, ref, {'t': 10}, 'a', user, {'faceTickets': 'increment'},
            notice, {'type': 'face_failed'}, {'status': 'failed'}))
        self.assertEqual(len(tx.writes), 3)
        tx = Tx()
        self.assertFalse(jobs.fail_request(tx, ref, {'t': 10}, 'a', user, {}, notice, {}, {}))
        self.assertEqual(tx.writes, [])


if __name__ == '__main__': unittest.main()
