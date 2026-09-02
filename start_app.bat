@echo off
title Vadodara Price Predictor - Launcher
cd /d C:\Users\Photon\Downloads\files\files

echo [1/3] Starting MongoDB...
start "mongod" "C:\Users\Photon\Downloads\mongodb-win32-x86_64-windows-8.0.4\bin\mongod.exe" --dbpath "C:\Users\Photon\Downloads\files\files\mongodb-data" --port 27017 --bind_ip 127.0.0.1

echo [2/3] Starting Flask app...
start "flaskapp" "C:\Users\Photon\Downloads\files\files\.venv\Scripts\python.exe" real_state_app.py

echo [3/3] Waiting for app, then opening public tunnel...
timeout /t 6 /nobreak >nul

echo.
echo Public URL appears below (new one every time). Keep this window open.
echo Copy it and open it in your browser. Press Ctrl+C to stop hosting.
echo.
"C:\Users\Photon\Downloads\cloudflared.exe" tunnel --url http://127.0.0.1:5000 --no-autoupdate

pause
