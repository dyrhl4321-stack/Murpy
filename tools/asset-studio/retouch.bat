@echo off
rem 머피 에셋 리터치 — 더블클릭해서 여세요.
rem 브라우저는 file:// 로 열면 픽셀 읽기를 막기 때문에 작은 서버를 띄웁니다.
cd /d "%~dp0..\.."
start "" http://localhost:8777/tools/asset-studio/retouch.html
python -m http.server 8777
