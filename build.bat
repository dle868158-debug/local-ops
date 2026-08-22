@echo off
rem Console Windows onefile packaging script (ASCII-safe, CRLF, no BOM).
rem Prefers the isolated .buildenv. NOTE: PyPI PySide6 wheels are built
rem against official CPython; building inside an Anaconda base env can fail
rem with "DLL load failed while importing QtCore", hence the isolated env.
setlocal
cd /d "%~dp0"

set "PY="
if exist "%~dp0.buildenv\Scripts\python.exe" set "PY=%~dp0.buildenv\Scripts\python.exe"
if defined PY goto havepy

echo [0/5] Creating isolated build env .buildenv ...
py -3.13 -m venv "%~dp0.buildenv" 2>nul
if not exist "%~dp0.buildenv\Scripts\python.exe" py -3 -m venv "%~dp0.buildenv" 2>nul
if not exist "%~dp0.buildenv\Scripts\python.exe" python -m venv "%~dp0.buildenv" 2>nul
if exist "%~dp0.buildenv\Scripts\python.exe" set "PY=%~dp0.buildenv\Scripts\python.exe"
if defined PY goto havepy

where python >nul 2>nul
if errorlevel 1 goto nopy
set "PY=python"
goto havepy

:nopy
echo [ERROR] Python not found. Install Python 3.12+ and add it to PATH.
exit /b 1

:havepy
%PY% --version

echo [1/5] Installing locked packaging dependencies...
%PY% -m pip install --disable-pip-version-check -r requirements-build.txt
if errorlevel 1 goto faildeps

echo [2/5] Generating EXE icon and version resource...
%PY% tools\gen_ico.py
if errorlevel 1 goto failico

echo [3/5] Building onefile EXE per spec (may take minutes)...
set "SPECFILE="
for %%F in (*.spec) do set "SPECFILE=%%F"
if not defined SPECFILE goto nospec
%PY% -m PyInstaller "%SPECFILE%" --noconfirm --clean
if errorlevel 1 goto failbuild

echo [4/5] Removing intermediate build\ (spec file is kept)...
if exist build rmdir /s /q build

echo [5/5] Done:
dir /b dist\*.exe
for %%A in (dist\*.exe) do echo   %%~fA  %%~zA bytes

echo.
echo Double-click the EXE under dist\ to run (no console window).
echo Note: first launch extracts to a temp dir, so a few seconds delay is normal.
echo Note: if SmartScreen blocks it, pick "More info" - "Run anyway".
goto eof

:nospec
echo [ERROR] No .spec file found in this directory.
exit /b 1

:failico
echo [ERROR] Failed to generate icon/version resource.
exit /b 1

:faildeps
echo [ERROR] Failed to install locked build dependencies.
exit /b 1

:failbuild
echo [ERROR] PyInstaller build failed. See log above.
exit /b 1

:eof
endlocal
