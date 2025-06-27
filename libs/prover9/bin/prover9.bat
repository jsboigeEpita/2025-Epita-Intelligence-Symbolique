@echo off
rem Wrapper pour prover9.exe pour gérer le cas sans arguments qui cause un deadlock.
set "PROVER9_CMD=prover9.exe.original"
set "PROVER9_DIR=D:\2025-Epita-Intelligence-Symbolique\libs\prover9\bin"

rem Vérifie si des arguments ont été passés
if [%1]==[] (
    rem Aucun argument, appel avec --help pour une sortie rapide et éviter le blocage
    rem echo "Wrapper: Prover9 appelé sans arguments. Appel de --help pour éviter le blocage."
    "%PROVER9_DIR%\%PROVER9_CMD%" --help
) else (
    rem Des arguments sont présents, les passer à l'exécutable original
    rem echo "Wrapper: Prover9 appelé avec des arguments. Transmission..."
    "%PROVER9_DIR%\%PROVER9_CMD%" %*
)
