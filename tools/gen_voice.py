# -*- coding: utf-8 -*-
"""제미나이 TTS 로 게임 대사를 뽑는다 (2026-09-02).

    python tools/gen_voice.py "무궁화꽃이 피었습니다~" char/game/voice_mugung.wav
    python tools/gen_voice.py "무궁화꽃이 피었습니다~" char/game/voice_mugung.wav --voice Puck --style "장난기 있게, 느리게 끌면서"

키: ~/.config/murpy/gemini.txt (gen_asset.py 와 같은 키)
모델: gemini-2.5-flash-preview-tts — PCM 16bit 24kHz mono 로 온다. 여기서 WAV 로 감싼다.
목소리: Kore(여, 차분) · Puck(남, 활발) · Charon(남, 낮음) · Fenrir(남, 힘있음) · Aoede(여, 밝음) 등.
★효과음(타격·휘슬)은 TTS 로 안 된다 — 그건 앱 안 WebAudio(window.sfx) 로 합성한다.
"""
import io, os, sys, json, base64, struct, urllib.request, argparse

sys.stdout.reconfigure(encoding='utf-8')
ap = argparse.ArgumentParser()
ap.add_argument('text'); ap.add_argument('out')
ap.add_argument('--voice', default='Fenrir')
ap.add_argument('--style', default='')
ap.add_argument('--model', default='gemini-2.5-flash-preview-tts')
a = ap.parse_args()

KEY = os.environ.get('GEMINI_API_KEY', '').strip()
if not KEY:
    KEY = io.open(os.path.expanduser('~/.config/murpy/gemini.txt'), encoding='utf-8').read().strip()

prompt = (a.style + ': ' if a.style else '') + a.text
body = {'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'responseModalities': ['AUDIO'],
                             'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': a.voice}}}}}
req = urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s' % (a.model, KEY),
                             data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
try:
    r = json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
except urllib.error.HTTPError as e:
    raise SystemExit('API %s %s' % (e.code, e.read().decode()[:400]))
part = None
for p in r.get('candidates', [{}])[0].get('content', {}).get('parts', []):
    if 'inlineData' in p: part = p['inlineData']; break
if not part:
    raise SystemExit('오디오가 안 왔다: ' + json.dumps(r)[:300])
mime = part.get('mimeType', ''); pcm = base64.b64decode(part['data'])
rate = 24000
for kv in mime.split(';'):
    if kv.strip().startswith('rate='): rate = int(kv.split('=')[1])
# PCM → WAV
wav = b'RIFF' + struct.pack('<I', 36 + len(pcm)) + b'WAVE' + b'fmt ' + struct.pack('<IHHIIHH', 16, 1, 1, rate, rate * 2, 2, 16) + b'data' + struct.pack('<I', len(pcm)) + pcm
os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
open(a.out, 'wb').write(wav)
print('저장 %s  (%s, %d Hz, %.2f초, %s 목소리)' % (a.out, mime.split(';')[0], rate, len(pcm) / 2 / rate, a.voice))
