@echo off
cd /d "%~dp0"
set APP_NAME=GSG3_Live_Captioner

echo Cleaning old builds...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q *.spec 2>nul

echo Building EXE folder...
python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --windowed ^
  --name "%APP_NAME%" ^
  --collect-all numpy ^
  --collect-all sounddevice ^
  --collect-all faster_whisper ^
  --collect-all ctranslate2 ^
  --hidden-import keyboard ^
  --hidden-import numpy.core._multiarray_umath ^
  main.py

echo.
echo Build complete.
echo Run: dist\%APP_NAME%\%APP_NAME%.exe
echo Do not move the EXE by itself. Keep the whole folder together.
pause
