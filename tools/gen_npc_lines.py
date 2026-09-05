# -*- coding: utf-8 -*-
"""공원 NPC 게임 대사 12개를 뽑고, 뽑은 음성을 **기계로 검수**한다 (2026-09-05).

    python tools/gen_npc_lines.py                    # 4명 12줄 전부
    python tools/gen_npc_lines.py --only trainer     # 한 명만

★왜 만들었나 — 대표 지적은 대사 내용이 아니라 **발음**이다("왓구아"처럼 받침이 씹힌다).
  표준대로 속도를 늦추지 않고 Diction 지시를 강화(DICTION)해서 다시 뽑는다.

★기계 검수 — 뽑은 음성을 다시 들려주고 **발음 또렷함**을 심사한다(judge).
  받아쓰기(STT)만으로는 못 잡는다 — 받아쓰기 모델은 들려야 할 말을 알아서 채우기 때문에
  뭉개진 기존 12줄이 전부 만점으로 통과했다(9-05 실측). 그래서 맞춤법 교정 없이
  **들린 소리 그대로** 적게 하고 뭉갠 자리를 지목하게 한다. 실제로 강 코치의
  "꾸준한 → 구준한", "보자고 → 부자고" 를 이 방식이 잡아냈다.
  합격선은 --min-clarity(기본 9) · 뭉갠 자리 0 · 끊김 없음.

★기존 파일 우선 — 이미 있는 mp3 를 먼저 심사해 합격이면 **그대로 둔다**.
  멀쩡한 테이크를 새로 뽑아 더 나빠지는 걸 막는다. 새 테이크는 기존보다
  나을 때만 교체한다. 전부 다시 뽑으려면 --force.

★화자 고정 — 캐릭터당 voice·모델·설명을 gen_npc_voice.CHARS 에 고정해두고 그대로 쓴다.
  temperature 는 0.2(--temp). 기본값 1.0 은 연기 폭이 커서 파일마다 다른 사람처럼 들린다.
  ※세 대사를 한 요청에 이어 읽히는 방식도 시도했으나 2.5-pro-tts 가 10분짜리 음성을
    뱉거나(무한 무음) finishReason=OTHER 로 죽어서 폐기했다. 대사별 생성이 안전하다.

출력: rv/a/line_<char>_<kind>.mp3 (검수 페이지용) + 같은 이름 .wav (원본 보관)
대표 승인 전 app 반영·배포 금지 — 검수 페이지 먼저 (오디오 표준).
"""
import io, os, sys, json, time, base64, subprocess, argparse, urllib.request, re

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_npc_voice import CHARS, MODEL, build_prompt, synth, trim, to_wav

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, 'rv', 'a')
FFMPEG = (r"C:/Users/dyrhl/AppData/Local/Microsoft/WinGet/Packages"
          r"/Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
          r"/ffmpeg-9.0.1-full_build/bin/ffmpeg.exe")
STT_MODEL = 'gemini-3.8-flash'   # 2.5-flash 는 신규 키에 404 — 받아쓰기는 최신 flash 로

# 앱(_MW_NPCS)의 대사 전문과 반드시 같아야 한다 — 말과 음성이 어긋나면 안 된다.
LINES = {
    'keeper': [
        ('hi',   '어서 오게. 우리 동네 공원, 마음에 드는가? 공원 온 김에 운동 도장도 찍어야지. 근처 헬스장에서 체크인하고 오게!'),
        ('done', '오, 도장 찍고 왔구먼! 부지런한 게 최고야.'),
        ('idle', '오늘 부탁은 다 끝났네. 내일 또 들르라고!')],
    'trainer': [
        ('hi',   '오! 운동하러 왔구나? 오늘 운동 인증 아직이지? 피드에 인증샷 한 장 올리고 와!'),
        ('done', '그래, 그 기세야! 꾸준한 놈이 이긴다.'),
        ('idle', '오늘은 여기까지! 내일 또 보자고.')],
    'grandma': [
        ('hi',   '아이고, 젊은이 왔는가. 속에 담아둔 얘기 있으면 대나무숲에 살짝 적어보게. 속이 후련해져.'),
        ('done', '잘했네. 마음도 근육처럼 풀어줘야 해.'),
        ('idle', '오늘 할 일은 다 했네. 살펴 가시게.')],
    'kid': [
        ('hi',   '형아! 누나! 나랑 놀자! 오늘의 머피들 봤어? 매칭 탭에서 새 친구 구경하고 와!'),
        ('done', '우와, 친구 많아지겠다!'),
        ('idle', '내일 또 놀러 와! 약속!')],
}


def norm(t):
    return re.sub(r'[^가-힣a-zA-Z0-9]', '', t)


def judge(wav_bytes, txt, key):
    """음성을 듣고 **발음 또렷함**을 심사한다. 반환 {heard, mush, clarity} · 실패하면 None.

    ★왜 받아쓰기(STT)만으로는 안 되나 — 받아쓰기 모델은 '들려야 할 말'을 알아서 채운다.
      실제로 기존 12줄을 받아쓰기 시키니 뭉개진 것까지 전부 1.00 으로 통과했다(9-05 실측).
      그래서 **맞춤법 교정 없이 들린 소리 그대로** 적게 하고, 뭉개진 자리를 짚게 한다.
    """
    ask = ('한국어 게임 캐릭터 음성의 발음을 심사한다. 이 대사의 원문은 다음과 같다:\n'
           + txt + '\n\n아래 JSON 만 출력한다. 설명·코드블록 금지.\n'
           '{"heard": "<들리는 소리 그대로. 맞춤법으로 고쳐 쓰지 말고, 뭉개져 들리면 뭉개진 대로 적는다>",\n'
           ' "mush": ["<받침이 삼켜지거나 음절이 붙어 뭉개진 부분을 원문 단어로 지목. 없으면 빈 배열>"],\n'
           ' "clarity": <0~10 정수. 10 = 모든 음절과 받침이 또렷하다. 6 이하 = 다시 뽑아야 한다>,\n'
           ' "cut": <true 면 대사가 중간에 끊겼다>}')
    body = {'contents': [{'parts': [
        {'text': ask},
        {'inline_data': {'mime_type': 'audio/wav', 'data': base64.b64encode(wav_bytes).decode()}}]}],
        'generationConfig': {'temperature': 0}}
    req = urllib.request.Request(
        'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s' % (STT_MODEL, key),
        data=json.dumps(body).encode(), headers={'Content-Type': 'application/json'})
    try:
        r = json.loads(urllib.request.urlopen(req, timeout=180).read().decode())
        t = ''.join(p.get('text', '') for p in r['candidates'][0]['content']['parts']).strip()
        t = re.sub(r'^```(?:json)?|```$', '', t.strip(), flags=re.M).strip()
        d = json.loads(t)
        return {'heard': str(d.get('heard', '')), 'mush': list(d.get('mush') or []),
                'clarity': int(d.get('clarity', 0)), 'cut': bool(d.get('cut'))}
    except Exception as e:
        print('   (발음 심사 실패 — 건너뜀: %s)' % str(e)[:90])
        return None


def similarity(a, b):
    """받아쓴 글자가 원문에 얼마나 남았나 — 0~1. 순서를 보는 LCS 비율."""
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            cur[j] = prev[j - 1] + 1 if a[i - 1] == b[j - 1] else max(prev[j], cur[j - 1])
        prev = cur
    return prev[len(b)] / max(len(a), len(b))


def mp3(wav_path, mp3_path):
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', wav_path,
                    '-codec:a', 'libmp3lame', '-b:a', '96k', mp3_path], check=True)


# ★발음 강화 지시 — 표준: 발음이 씹히면 속도를 늦추지 말고 Diction 지시를 강화한다.
DICTION = ('모든 받침(ㄱ ㄴ ㄹ ㅁ ㅂ ㅅ ㅇ)을 끝까지 닫아서 발음한다. 음절을 붙여 흘리지 말고 하나씩 또렷하게 낸다. '
           '말끝을 삼키지 않는다. 조사와 어미까지 다 들리게 발음한다. '
           '그러면서도 또박또박 읽는 낭독 톤이 되지는 않는다 — 동네 사람이 편하게 하는 말투 그대로다.')


def take(ck, txt, key, temp, model, mushed=()):
    """한 테이크 생성 + 발음 심사. API 500 은 테이크 횟수로 세지 않고 잠깐 쉬었다 다시 친다.

    mushed = 직전 테이크에서 뭉갰다고 지목된 단어들. 그 단어를 이름 대서 다시 시킨다
    (표준: 속도를 늦추지 말고 Diction 지시를 강화한다)."""
    extra = DICTION
    if mushed:
        extra += (' 특히 다음 단어는 첫 음절과 받침을 하나도 흘리지 말고 정확히 발음한다: '
                  + ', '.join('「%s」' % m for m in mushed) + '.')
    for att in range(3):
        try:
            pcm, rate = synth(build_prompt(ck, txt, extra), CHARS[ck]['voice'], model, key,
                              timeout=600, temp=temp)
            break
        except BaseException as e:                 # synth 는 SystemExit 로 죽는다
            print('     생성 실패(%d/3): %s' % (att + 1, str(e)[:100].replace(chr(10), ' ')))
            time.sleep(6)
    else:
        return None
    w = to_wav(trim(pcm, rate), rate)
    r = judge(w, txt, key) or {'heard': '', 'mush': [], 'clarity': -1, 'cut': False}
    # 심사가 못 잡는 통짜 끊김은 글자 대조로 한 번 더 본다
    if r['heard'] and similarity(txt, r['heard']) < 0.75:
        r['cut'] = True
    r['wav'] = w; r['rate'] = rate
    r['dur'] = (len(w) - 44) / 2.0 / rate
    return r


def score(r):
    """고를 때 순서 — 끊기지 않은 것 > 또렷한 것 > 뭉갠 자리가 적은 것"""
    return (0 if r['cut'] else 1, r['clarity'], -len(r['mush']))


def judge_file(path, txt, key, rounds=2):
    """이미 있는 mp3 를 심사한다. 심사에 편차가 있어 여러 번 듣고 **제일 나쁜 결과**를 쓴다."""
    if not os.path.exists(path):
        return None
    tmp = path + '.judge.wav'
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', path, '-ar', '24000', '-ac', '1', tmp], check=True)
    w = open(tmp, 'rb').read()
    os.remove(tmp)
    worst = None
    for _ in range(rounds):
        r = judge(w, txt, key)
        if not r:
            continue
        if r['heard'] and similarity(txt, r['heard']) < 0.75:
            r['cut'] = True
        if worst is None or score(r) < score(worst):
            worst = r
    if worst is None:
        return None
    worst['wav'] = None                       # 기존 파일은 다시 쓸 필요가 없다
    worst['rate'] = 24000
    worst['dur'] = 0.0
    return worst


def passes(r, min_clarity):
    return bool(r) and not r['cut'] and r['clarity'] >= min_clarity and not r['mush']


def run_char(ck, key, tries, temp, model, min_clarity, force=False, kinds=(), rounds=2):
    """기존 파일을 먼저 심사하고, 합격이면 그대로 둔다(멀쩡한 걸 새로 뽑아 나빠지는 걸 막는다).
    불합격이면 다시 뽑되, 새 테이크가 기존보다 확실히 나을 때만 교체한다."""
    ok_all = True
    for kind, txt in LINES[ck]:
        if kinds and kind not in kinds:
            continue
        base = os.path.join(OUT, 'line_%s_%s' % (ck, kind))
        best = None if force else judge_file(base + '.mp3', txt, key, rounds)
        if best:
            print('   %-7s %-4s 기존 또렷함 %2d%s%s' % (ck, kind, best['clarity'],
                  ' · 끊김!' if best['cut'] else '',
                  (' · 뭉갬: ' + ', '.join(best['mush'])) if best['mush'] else ''))
            if passes(best, min_clarity):
                print('   = line_%s_%s.mp3 그대로 둠 (합격)' % (ck, kind))
                continue
            print('        들린 소리: %s' % best['heard'][:80])
        mushed = list(best['mush']) if best else []
        for t in range(1, tries + 1):
            r = take(ck, txt, key, temp, model, mushed)
            if not r:
                print('   %s %s %d회 — 생성 자체가 실패' % (ck, kind, t)); continue
            print('   %-7s %-4s %d회 또렷함 %2d · %.2f초%s%s'
                  % (ck, kind, t, r['clarity'], r['dur'],
                     ' · 끊김!' if r['cut'] else '',
                     (' · 뭉갬: ' + ', '.join(r['mush'])) if r['mush'] else ''))
            if r['mush'] or r['cut']:
                print('        들린 소리: %s' % r['heard'][:80])
            if r['mush']:
                mushed = list(dict.fromkeys(mushed + r['mush']))[:6]
            if best is None or score(r) > score(best):
                best = r
            if not r['cut'] and r['clarity'] >= min_clarity and not r['mush']:
                break
        if not best:
            print('  x %s %s — 전부 실패, 기존 파일 유지' % (ck, kind)); ok_all = False; continue
        if best['wav'] is None:
            print('  = %s %s — 새로 뽑은 게 기존보다 낫지 않아 기존 파일을 그대로 둔다(또렷함 %d)'
                  % (ck, kind, best['clarity'])); ok_all = False; continue
        if best['cut'] or best['clarity'] < min_clarity or best['mush']:
            print('  * %s %s 합격선 미달 — 제일 나은 테이크 채택(또렷함 %d)' % (ck, kind, best['clarity']))
            print('     원문     : %s' % txt)
            print('     들린 소리: %s' % best['heard'])
            ok_all = False
        os.makedirs(OUT, exist_ok=True)
        open(base + '.wav', 'wb').write(best['wav'])
        mp3(base + '.wav', base + '.mp3')
        print('   -> line_%s_%s.mp3  %.2f초  또렷함 %d' % (ck, kind, best['dur'], best['clarity']))
    return ok_all


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='', help='한 캐릭터만 (keeper/trainer/grandma/kid)')
    ap.add_argument('--tries', type=int, default=3)
    ap.add_argument('--temp', type=float, default=0.2, help='낮을수록 화자가 고정된다')
    ap.add_argument('--model', default=MODEL)
    ap.add_argument('--min-clarity', type=int, default=9, help='발음 또렷함 합격선(0~10)')
    ap.add_argument('--force', action='store_true', help='기존 파일 심사를 건너뛰고 무조건 다시 뽑는다')
    ap.add_argument('--kinds', default='', help='특정 대사만 (hi,done,idle 중 쉼표로)')
    ap.add_argument('--judge-rounds', type=int, default=2,
                    help='기존 파일을 몇 번 들어보고 판정할지. 심사에 편차가 있어 여러 번 듣고 제일 나쁜 결과를 쓴다')
    a = ap.parse_args()

    key = os.environ.get('GEMINI_API_KEY', '').strip()
    if not key:
        key = io.open(os.path.expanduser('~/.config/murpy/gemini.txt'), encoding='utf-8').read().strip()

    todo = [a.only] if a.only else ['keeper', 'trainer', 'grandma', 'kid']
    kinds = tuple(x.strip() for x in a.kinds.split(',') if x.strip())
    ok = [run_char(c, key, a.tries, a.temp, a.model, a.min_clarity, a.force, kinds, a.judge_rounds)
          for c in todo]
    print('\n끝 — 성공 %d / %d' % (sum(ok), len(ok)))
