@echo off
setlocal enableextensions
rem ---------------------------------------------------------------------------
rem Tweety <-> SPASS DFG delivery-contract adapter -- Windows mirror (FP-18 #1241)
rem ---------------------------------------------------------------------------
rem Windows analogue of scripts/solvers/spass_eml_adapter.sh. Modal counterpart of
rem the eprover #1204 delivery-contract sentinel.
rem
rem PROBLEM (firsthand-diagnosed 2026-06-23): Tweety 1.29's SPASSMlReasoner writes
rem the modal special-formulae logic token in UPPERCASE:
rem     list_of_special_formulae(axioms,EML).
rem SPASS 3.9's DFG parser requires it in LOWERCASE and aborts with
rem     "got 'EML', expected special type (eml)"
rem so the modal axis cannot decide. A Tweety<->SPASS version mismatch, NOT a
rem reasoning failure.
rem
rem FIX (no contournement -- the real SOTA prover does ALL the work): rewrite ONLY
rem the keyword case in the DFG temp file Tweety passes as a file argument, then
rem exec the real SPASS unchanged. SPASS still performs the full EML->FOL
rem translation + saturation; this only repairs the interface token.
rem
rem INVOCATION: Tweety's NativeShell runs `Runtime.getRuntime().exec(cmd)` with no
rem shell. OpenJDK 17's ProcessImpl special-cases a .bat/.cmd first token and
rem routes it through cmd.exe (firsthand-verified), so this adapter is invocable.
rem jvm_setup.py registers it as EXTERNAL_TOOL_PATHS['spass'] when present beside
rem SPASS.exe. Build the real SPASS: scripts/setup/build_spass_windows.ps1
rem ---------------------------------------------------------------------------
set "HERE=%~dp0"
set "REAL=%HERE%SPASS.exe"
if not exist "%REAL%" (
  echo spass_eml_adapter: real SPASS.exe not found at "%REAL%" 1>&2
  exit /b 127
)

rem Repair the DFG keyword case in every file argument (Tweety passes exactly one
rem DFG temp file; switches like -PGiven=0 are not existing files and are skipped).
for %%A in (%*) do if exist "%%~A" (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$p='%%~A'; $t=[IO.File]::ReadAllText($p); $t=[Text.RegularExpressions.Regex]::Replace($t,'list_of_special_formulae\(([A-Za-z_]*),EML\)','list_of_special_formulae(${1},eml)'); [IO.File]::WriteAllText($p,$t)"
)

"%REAL%" %*
exit /b %ERRORLEVEL%
