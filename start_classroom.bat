@echo off
rem ==========================================================
rem  ClassSpeaker - standalone launcher (normal version)
rem  Runs in background, tray icon stays in the taskbar.
rem  Launcher: run.py     Args: --settings  open settings now
rem ==========================================================
setlocal
cd /d "%~dp0"

where pythonw >nul 2>nul
if %ERRORLEVEL%==0 (
    start "" pythonw "%~dp0run.py" %*
    exit /b 0
)

where pyw >nul 2>nul
if %ERRORLEVEL%==0 (
    start "" pyw -3 "%~dp0run.py" %*
    exit /b 0
)

echo [ERROR] pythonw.exe not found in PATH.
echo         Install Python 3.8+ (64-bit), then run:  pip install PyQt5
pause
exit /b 1
