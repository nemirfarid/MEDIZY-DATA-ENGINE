@echo off
REM Wrapper: run flutter/dart with git on PATH, redirecting output to a file.
REM Usage: run_fx.bat <flutter|dart> <outfile> <args...>
setlocal
set "PATH=C:\Program Files\Git\cmd;C:\Program Files\Git\bin;%PATH%"
set "EXE=%~1"
set "OUT=%~2"
shift
shift
set "ARGS="
:loop
if "%~1"=="" goto run
set "ARGS=%ARGS% %1"
shift
goto loop
:run
cd /d C:\SANTE_DZ_SCRAPER
%EXE% %ARGS% > %OUT% 2>&1
echo EXITCODE=%ERRORLEVEL% >> %OUT%
echo DONE >> %OUT%
