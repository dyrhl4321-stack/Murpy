# -*- coding: utf-8 -*-
"""제미나이 이미지 생성 호출 (tools/face_pipeline.gen 과 같은 요청, 파일 대신 바이트).

★모델 gemini-3-pro-image · aspectRatio 9:16 · imageSize 2K 는 실측으로 굳어진 값이다 — 낮추면 파츠가 끊기고
  4열로 나온다(9-04). 프롬프트는 비공개 저장소 파일(Storage private/face/prompt.txt)에서 온다.
"""
import base64, json, urllib.request, urllib.error

def generate(key, base_png, selfies, prompt, model='gemini-3-pro-image', aspect='9:16', size='2K', timeout=300):
    """base_png: bytes · selfies: [(mime, bytes)] (최대 8장) · 돌려주는 값 = PNG/JPEG 바이트."""
    parts = [{'inlineData': {'mimeType': 'image/png', 'data': base64.b64encode(base_png).decode()}}]
    for mime, data in selfies[:8]:
        parts.append({'inlineData': {'mimeType': mime or 'image/jpeg', 'data': base64.b64encode(data).decode()}})
    parts.append({'text': prompt})
    body = {'contents': [{'parts': parts}],
            'generationConfig': {'responseModalities': ['IMAGE'],
                                 'imageConfig': {'aspectRatio': aspect, 'imageSize': size}}}
    req = urllib.request.Request(
        'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s' % (model, key),
        data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError('gemini %s %s' % (e.code, e.read().decode()[:300]))
    for p in r.get('candidates', [{}])[0].get('content', {}).get('parts', []):
        if 'inlineData' in p:
            return base64.b64decode(p['inlineData']['data'])
    raise RuntimeError('gemini: 이미지가 안 왔다 ' + json.dumps(r)[:300])
