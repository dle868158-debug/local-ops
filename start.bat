@echo off
rem 总控台 Windows 启动器：优先 py 启动器（Python 3.12+），回退 python。
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 server.py --launcher %*
) else (
  python server.py --launcher %*
)
