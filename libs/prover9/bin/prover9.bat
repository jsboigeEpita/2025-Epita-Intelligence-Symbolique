@echo off
set LOG_FILE="C:\Users\jsboi\AppData\Local\Temp\prover9_debug.log"
echo ================================= >> %LOG_FILE%
echo Batch script started at %TIME% >> %LOG_FILE%
echo Current directory (start): %cd% >> %LOG_FILE%
echo Script path (%%~dp0): %~dp0 >> %LOG_FILE%
echo Arguments received: %* >> %LOG_FILE%

cd /d "%~dp0"
echo Current directory (after cd): %cd% >> %LOG_FILE%

if [%1]==[] (
    echo Running: prover9.exe --help >> %LOG_FILE%
    prover9.exe --help
) else (
    echo Running: prover9.exe %* >> %LOG_FILE%
    prover9.exe %*
)
echo Batch script finished at %TIME% >> %LOG_FILE%
