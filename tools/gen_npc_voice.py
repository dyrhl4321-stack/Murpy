# -*- coding: utf-8 -*-
"""MURPY 게임 음성 제작 — 대표 전달 표준(코덱스본) 그대로 (2026-09-04).

    python tools/gen_npc_voice.py --char keeper --line "어서 오게, 우리 공원 좋지?" --out char/npc/voice/keeper_hi.wav

★표준 요약(feedback_murpy_voice_quality_standard / 대표 전달 오디오 표준)
  - 모델: 최신 최고 TTS (기본 gemini-3.1-flash-tts-preview, --model 로 교체)
  - 캐릭터당 prebuilt voice **고정**. 대사마다 voice 바꾸지 않는다.
  - **피치/속도 리샘플 절대 금지** (gen_voice.py --pitch 는 이 스크립트에 없다)
  - 프롬프트는 Character / Voice Age / Personality / Diction / Performance /
    Voice Consistency / Critical Negatives / Timing / TRANSCRIPT 로 분리
  - 후처리는 앞뒤 무음 제거 + 피크 방지만. 문턱 = peak*1.2% 또는 절댓값 160,
    앞뒤 35ms 는 남긴다. 문장 내부의 의도적 뜸은 보존한다.
  - 출력: PCM 24kHz mono s16le → WAV
  - 대표 승인 전 저장소 반영·배포 금지 (검수용 청취 페이지 먼저)
"""
import io, os, sys, json, base64, struct, array, urllib.request, argparse

sys.stdout.reconfigure(encoding='utf-8')

# ── 캐릭터 카드 (voice 고정 · 설명 고정 — 파일마다 동일하게 반복해 넣는다) ──
CHARS = {
    'keeper': {
        'voice': 'Charon',
        'card': """Character: 50대 후반 한국인 남성. 동네 공원을 40년째 쓸고 다니는 관리인.
  낡은 초록 모자와 카키색 조끼 차림이다. 사람 좋고 정 많은 동네 어른.
Voice Age: 50대 후반. 살짝 잠긴 목이지만 따뜻하고 편안하다.
Personality: 손주 대하듯 다정하고 느긋하다. 잔소리도 정겹게 한다. 서두르지 않는다.
Diction: 모든 음절과 받침을 또렷하게. 말끝을 부드럽게 내린다.
Performance: 빗자루 들고 서서 지나가는 사람에게 말 거는 톤. 편안한 대화 거리.""",
    },
    'trainer': {
        'voice': 'Puck',
        'card': """Character: 20대 후반 한국인 남성 피트니스 트레이너. 민소매 트레이닝복에 호루라기.
  에너지 넘치고 사람 챙기기 좋아하는 동네 형.
Voice Age: 20대 후반. 밝고 힘 있는 중고음.
Personality: 활기차고 긍정적이다. 밀어붙이되 기분 나쁘지 않게 응원한다.
Diction: 모든 음절과 받침을 또렷하게. 말끝에 힘이 실린다.
Performance: 헬스장에서 회원에게 말 걸듯 가깝고 경쾌하게. 소리 지르지는 않는다.""",
    },
    'grandma': {
        'voice': 'Kore',
        'card': """Character: 70대 한국인 할머니. 은발 쪽머리에 카디건, 손가방을 든 동네 어르신.
Voice Age: 70대. 나이 든 여성의 가늘고 부드러운 음색, 약간의 떨림.
Personality: 인자하고 조곤조곤하다. 재촉하지 않고 다독인다.
Diction: 모든 음절과 받침을 또렷하게. 천천히, 그러나 웅얼거리지 않는다.
Performance: 벤치에 앉아 손주에게 말하듯 낮고 따뜻하게.""",
    },
    'kid': {
        'voice': 'Leda',
        'card': """Character: 6살 한국인 남자아이. 노란 티셔츠에 반바지, 공원 놀이터 단골.
Voice Age: 6세. 높고 맑은 아이 목소리.
Personality: 밝고 들떠 있다. 신나서 말이 조금 빨라진다.
Diction: 모든 음절과 받침을 또렷하게. 혀 짧은 소리를 억지로 내지 않는다.
Performance: 놀이터에서 뛰어오며 반갑게 부르는 톤. 비명 지르듯 하지는 않는다.""",
    },
}

COMMON_TAIL = """Voice Consistency: 이 캐릭터의 모든 파일은 반드시 동일한 한 명의 화자다.
  같은 방, 같은 마이크, 같은 입-마이크 거리, 같은 기본 음량으로 연속 녹음한 세션처럼 들려야 한다.
Critical Negatives: 방송·광고 성우 톤, 아나운서, 판소리, 뮤지컬, 가수, 로봇처럼 일정한 억양,
  과장된 연기, 잘생긴 저음 금지. 지시문을 읽지 말 것.
Timing: 대사 앞뒤 무음은 최소화한다. 마지막 음절이 끝나는 즉시 오디오를 끝낸다.
  원문 외 웃음·기침·감탄사를 추가하지 않는다."""


def build_prompt(char_key, line):
    c = CHARS[char_key]
    return ("한국어 게임 캐릭터 음성 녹음이다. 지시문은 읽지 말고 TRANSCRIPT 한 줄만 정확히 발화한다.\n\n"
            + c['card'] + "\n" + COMMON_TAIL + "\n\nTRANSCRIPT:\n" + line)


def synth(prompt, voice, model, key, timeout=180):
    body = {'contents': [{'parts': [{'text': prompt}]}],
            'generationConfig': {'responseModalities': ['AUDIO'],
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}}}}
    req = urllib.request.Request(
        'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s' % (model, key),
        data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit('API %s %s' % (e.code, e.read().decode()[:400]))
    for p in r.get('candidates', [{}])[0].get('content', {}).get('parts', []):
        if 'inlineData' in p:
            d = p['inlineData']
            rate = 24000
            for kv in d.get('mimeType', '').split(';'):
                if kv.strip().startswith('rate='):
                    rate = int(kv.split('=')[1])
            return base64.b64decode(d['data']), rate
    raise SystemExit('오디오가 안 왔다: ' + json.dumps(r)[:300])


def trim(pcm, rate):
    """앞뒤 무음만 제거. 문턱 = peak*1.2% 또는 160 중 큰 값, 앞뒤 35ms 는 남긴다."""
    s = array.array('h'); s.frombytes(pcm)
    if not len(s): return pcm
    peak = max(abs(v) for v in s)
    th = max(int(peak * 0.012), 160)
    i = 0
    while i < len(s) and abs(s[i]) < th: i += 1
    j = len(s) - 1
    while j > i and abs(s[j]) < th: j -= 1
    pad = int(rate * 0.035)
    i = max(0, i - pad); j = min(len(s) - 1, j + pad)
    return s[i:j + 1].tobytes()


def to_wav(pcm, rate):
    return (b'RIFF' + struct.pack('<I', 36 + len(pcm)) + b'WAVE' + b'fmt '
            + struct.pack('<IHHIIHH', 16, 1, 1, rate, rate * 2, 2, 16)
            + b'data' + struct.pack('<I', len(pcm)) + pcm)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--char', required=True, choices=sorted(CHARS.keys()))
    ap.add_argument('--line', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--model', default='gemini-3.1-flash-tts-preview')
    ap.add_argument('--voice', default='', help='캐릭터 기본 voice 를 덮어쓴다(후보 비교용에만)')
    a = ap.parse_args()

    key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not key:
        key = io.open(os.path.expanduser('~/.config/murpy/gemini.txt'), encoding='utf-8').read().strip()

    voice = a.voice or CHARS[a.char]['voice']
    pcm, rate = synth(build_prompt(a.char, a.line), voice, a.model, key)
    pcm = trim(pcm, rate)
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    open(a.out, 'wb').write(to_wav(pcm, rate))
    print('저장 %s  (%s / %s, %d Hz, %.2f초)' % (a.out, a.model, voice, rate, len(pcm) / 2 / rate))
