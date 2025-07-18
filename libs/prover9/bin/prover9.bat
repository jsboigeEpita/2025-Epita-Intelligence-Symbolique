@echo off
rem Wrapper pour prover9.exe pour gerer le cas sans arguments qui cause un deadlock.
rem Version simplifiee pour eviter les problemes de guillemets.
if [%1]==[] (
    "%~dp0\prover9.exe" --help
) else (
    "%~dp0\prover9.exe" %*
)
