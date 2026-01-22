@echo off
title MP4 to GIF Converter
cd /d "c:\Users\souto\Desktop\claude-fighting\mp4-to-gif"
echo Starting MP4 to GIF Converter...
echo.
echo Opening browser in 3 seconds...
start "" cmd /c "timeout /t 3 >nul && start http://localhost:5173"
npm run dev
