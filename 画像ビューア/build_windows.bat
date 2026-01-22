\
@echo off
setlocal

REM Simple Windows build helper (requires Python + pip + PyInstaller)

python -m pip install -r requirements.txt
python -m pip install pyinstaller

REM Build one-file exe (no console)
pyinstaller --noconsole --onefile -n NimbleView -m nimbleview

echo.
echo Done. See dist\NimbleView.exe
pause
