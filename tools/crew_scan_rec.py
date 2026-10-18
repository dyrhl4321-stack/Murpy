# 스캔 연출 녹화(10-19) — 앱을 띄워 window.runScanDemo 로 가짜 결과를 넣고 화면을 동영상으로 찍는다. 서버 호출·DB 쓰기 없음.
#   사용: python tools/crew_scan_rec.py <출력폴더> <카드 이미지 폴더(card_strava.jpg·card_nrc.jpg)>
#   결과: scan_ok.mp4(미인증 '기록' 도장) · scan_verified.mp4('인증' 도장) · scan_fail.mp4(거절) — ffmpeg 로 webm → mp4
import sys, os, glob, shutil, subprocess, threading, http.server, socketserver, functools
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.abspath(sys.argv[1]); os.makedirs(OUT, exist_ok=True)
IMG = '/' + os.path.relpath(os.path.abspath(sys.argv[2]), ROOT).replace(os.sep, '/')
H = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT); H.log_message = lambda *a: None
srv = socketserver.TCPServer(('127.0.0.1', 0), H); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

TAKES = [
  ('scan_ok', 'card_strava.jpg', "{ok:true, reward:0, run:{km:5.02, sec:1531, paceSec:305, runDay:'20261019', dayFromCard:true, status:'unverified', boxes:{km:[385,76,516,273], pace:[383,527,517,727], date:[64,344,89,864]}}}", 1400),
  ('scan_verified', 'card_nrc.jpg', "{ok:true, reward:10, run:{km:10.03, sec:3318, paceSec:331, runDay:'20261018', dayFromCard:true, status:'verified', boxes:{km:[334,93,479,788], pace:[693,75,735,524], date:[848,72,874,581]}}}", 1400),
  ('scan_fail', 'card_strava.jpg', "{ok:false, why:'dup_image'}", 1400),
]
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, img, res, delay in TAKES:
        vdir = os.path.join(OUT, '_v_' + name); shutil.rmtree(vdir, ignore_errors=True)
        ctx = b.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2,
                            record_video_dir=vdir, record_video_size={'width': 780, 'height': 1688})
        pg = ctx.new_page()
        pg.goto('http://127.0.0.1:%d/index.html' % port, wait_until='domcontentloaded')
        pg.wait_for_function('typeof window.runScanDemo === "function"', timeout=60000)
        pg.wait_for_timeout(6000)
        pg.add_style_tag(content='body > *:not(#run-scan){visibility:hidden!important} #run-scan, #run-scan *{visibility:visible}')
        pg.evaluate("window._crewCss()")
        pg.evaluate("document.fonts && document.fonts.load('16px Galmuri14')")
        pg.wait_for_timeout(600)
        pg.evaluate("window.runScanDemo('%s/%s', %s, %d)" % (IMG, img, res, delay))
        pg.wait_for_timeout(6200)
        ctx.close()
        webm = glob.glob(os.path.join(vdir, '*.webm'))[0]
        mp4 = os.path.join(OUT, name + '.mp4')
        # 앞 6.6초(부팅 대기)는 잘라 낸다
        subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-ss', '6.6', '-i', webm, '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-r', '30', mp4], check=True)
        shutil.rmtree(vdir, ignore_errors=True)
        print('saved', mp4)
    b.close()
srv.shutdown()
