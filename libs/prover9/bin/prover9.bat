@echo off
rem Wrapper pour prover9.exe pour gérer le cas sans arguments qui cause un deadlock.
set "PROVER9_CMD=prover9.exe.original"
set "PROVER9_DIR=D:\2025-Epita-Intelligence-Symbolique\libs\prover9\bin"

set "LOG_FILE=D:\2025-Epita-Intelligence-Symbolique-4\_temp\prover9_log.txt"
echo. > "%LOG_FILE%"
echo [%date% %time%] Wrapper Prover9 démarré. >> "%LOG_FILE%"
echo Arguments reçus: %* >> "%LOG_FILE%"

rem Vérifie si des arguments ont été passés
if [%1]==[] (
    rem Aucun argument, appel avec --help pour une sortie rapide et éviter le blocage
    echo "Wrapper: Prover9 appelé sans arguments. Appel de --help pour éviter le blocage." >> "%LOG_FILE%"
    "%PROVER9_DIR%\%PROVER9_CMD%" --help 2>> "%LOG_FILE%"
) else (
    rem Des arguments sont présents, les passer à l'exécutable original
    echo "Wrapper: Prover9 appelé avec des arguments. Transmission..." >> "%LOG_FILE%"
    "%PROVER9_DIR%\%PROVER9_CMD%" %* 2>> "%LOG_FILE%"
)
echo [%date% %time%] Wrapper Prover9 terminé. >> "%LOG_FILE%"
