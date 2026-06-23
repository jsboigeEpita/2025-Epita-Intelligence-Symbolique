<#
.SYNOPSIS
    Build & install a native Windows SPASS 3.9 CLI (modal theorem prover) for the
    modal axis (FP-18 #1241). Windows counterpart of scripts/setup/build_spass_modal.sh.

.DESCRIPTION
    The Windows analogue of the "énorme régression" reported 2026-06-23:
      * The modal axis defaulted to TWEETY/SimpleMlReasoner (naive Kripke
        enumeration) which OOMs at ~12 atoms (FP-16 #1231) — real KBs never decided.
      * The previously-vendored SPASS.exe was a GUI/InstallShield elevation build
        (requireAdministrator in the PE's embedded manifest) — never a runnable CLI.
      * A stock SPASS 3.9 source tarball does not build out-of-the-box with MinGW:
        top.c uses POSIX SIGALRM/alarm() (SPASS's internal soft time-limit) which
        MinGW-w64 lacks. We remove those 3 references (a subprocess-level timeout
        guards runaway search instead, exactly like core/prover9_runner.py) and
        enable C99 %z formatting via -D__USE_MINGW_ANSI_STDIO=1.

    The resulting SPASS.exe is a genuine V 3.9 CLI that DECIDES modal consistency
    (firsthand-verified via the production ModalHandler — it decides the 12-atom KB
    that OOMs SimpleMlReasoner). The Tweety<->SPASS DFG delivery-contract adapter
    (ext_tools/spass/spass_eml_adapter.bat) rewrites the uppercase EML keyword Tweety
    emits to the lowercase eml SPASS 3.9 requires; SPASS does ALL modal reasoning.

    Toolchain (conda-forge, sudo-free, firsthand build env ai-01 / MyIA-AI-01):
      m2w64-gcc 5.3.0  m2-flex 2.6.0  m2-bison 3.0.4  m2-make 4.1

    The native binary is vendored (tracked in git the eprover way) so CI does not
    need this toolchain; this script documents provenance and rebuilds on demand.

.PARAMETER BuildDir
    Scratch build directory. Default: $HOME\spass_build.

.PARAMETER SrcTgz
    Path to spass39.tgz (554633 bytes) from https://www.spass-prover.org/.
    Default: <BuildDir>\spass39.tgz (downloaded if absent).

.EXAMPLE
    pwsh -File scripts/setup/build_spass_windows.ps1
#>
[CmdletBinding()]
param(
    [string]$BuildDir = (Join-Path $HOME "spass_build"),
    [string]$SrcTgz   = "",
    [string]$CondaEnv = "spass-build"
)
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$DestDir  = Join-Path $RepoRoot "ext_tools\spass"
$AdapterSrc = Join-Path $RepoRoot "ext_tools\spass\spass_eml_adapter.bat"
if (-not $SrcTgz) { $SrcTgz = Join-Path $BuildDir "spass39.tgz" }

Write-Host "== SPASS 3.9 native Windows build (FP-18 #1241) =="
Write-Host "  repo root : $RepoRoot"
Write-Host "  build dir : $BuildDir"
Write-Host "  source    : $SrcTgz"
Write-Host "  install to: $DestDir"

# 1. MinGW toolchain via a dedicated conda env (sudo-free, reproducible).
$conda = (Get-Command conda -ErrorAction SilentlyContinue)
if (-not $conda) { throw "conda not found on PATH — install Miniconda/Mambaforge first." }
$envList = conda env list
if (-not ($envList -match [regex]::Escape($CondaEnv))) {
    Write-Host "== creating conda env '$CondaEnv' (m2w64-gcc + flex + bison + make) =="
    conda create -y -n $CondaEnv -c conda-forge m2w64-gcc m2-flex m2-bison m2-make
    if ($LASTEXITCODE -ne 0) { throw "conda env creation failed." }
}
$envPrefix = (conda run -n $CondaEnv python -c "import sys,os;print(os.path.dirname(sys.executable))" 2>$null)
if (-not $envPrefix) { $envPrefix = Join-Path $HOME "miniconda3\envs\$CondaEnv" }
$mingwBin = Join-Path $envPrefix "Library\mingw-w64\bin"
$msysBin  = Join-Path $envPrefix "Library\usr\bin"
$env:PATH = "$mingwBin;$msysBin;$env:PATH"

# 2. Obtain the source tarball.
New-Item -ItemType Directory -Force -Path $BuildDir | Out-Null
if (-not (Test-Path $SrcTgz)) {
    Write-Host "== downloading spass39.tgz from the official SPASS distribution =="
    Invoke-WebRequest -Uri "https://www.spass-prover.org/download/sources/spass39.tgz" -OutFile $SrcTgz
}

# 3. Extract (the tarball expands flat: analyze.c, approx.c, ..., top.c at top level).
Push-Location $BuildDir
& tar xzf $SrcTgz
if ($LASTEXITCODE -ne 0) { Pop-Location; throw "tar extraction failed." }

# 4. Patch top.c: remove the POSIX SIGALRM/alarm() soft time-limit (MinGW lacks it).
#    A subprocess-level timeout guards runaway search instead (cf. prover9_runner.py).
$topc = Join-Path $BuildDir "top.c"
if (-not (Test-Path $topc)) { Pop-Location; throw "top.c not found after extraction." }
$src = [IO.File]::ReadAllText($topc)
$src = $src.Replace(
    "if (Signal == SIGINT || Signal == SIGTERM || (Signal == SIGALRM && top_NoAlarm == 0)) {",
    "if (Signal == SIGINT || Signal == SIGTERM) {")
$src = $src.Replace(
    "signal(SIGALRM, top_SigHandler);",
    "/* SIGALRM unavailable on Windows/MinGW; subprocess-level timeout used instead (FP-18) */")
$src = [regex]::Replace($src,
    "alarm\(flag_GetFlagIntValue\(Flags,flag_TIMELIMIT\)\+1\);[^\r\n]*",
    "; /* alarm() unavailable on Windows/MinGW; subprocess-level timeout used instead (FP-18) */")
[IO.File]::WriteAllText($topc, $src, [Text.UTF8Encoding]::new($false))
Write-Host "== patched top.c (SIGALRM/alarm removed) =="

# 5. Build the CLI. MinGW gcc needs a writable TEMP and C99 %z formatting.
$tmp = Join-Path $BuildDir "tmp"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
$env:TEMP = $tmp; $env:TMP = $tmp
& make SPASS CC="gcc -D__USE_MINGW_ANSI_STDIO=1"
$mk = $LASTEXITCODE
$exe = Join-Path $BuildDir "SPASS.exe"
if ($mk -ne 0 -and -not (Test-Path $exe)) { Pop-Location; throw "make SPASS failed (rc=$mk)." }
# MinGW may emit 'SPASS' without the .exe suffix depending on make rules.
if (-not (Test-Path $exe)) {
    $bare = Join-Path $BuildDir "SPASS"
    if (Test-Path $bare) { Copy-Item $bare $exe -Force }
}
if (-not (Test-Path $exe)) { Pop-Location; throw "SPASS build produced no binary." }
Pop-Location

# 6. Smoke-test: the binary must self-report as a CLI (not a GUI/elevation build).
$ver = & $exe 2>&1 | Select-String -Pattern "V 3\.9|SPASS" | Select-Object -First 1
Write-Host "== built: $ver =="

# 7. Install binary + adapter side by side (jvm_setup registers the adapter).
New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
Copy-Item $exe (Join-Path $DestDir "SPASS.exe") -Force
if (Test-Path $AdapterSrc) {
    Write-Host "  adapter already present: $AdapterSrc"
} else {
    Write-Warning "spass_eml_adapter.bat missing at $AdapterSrc — restore from git."
}

Write-Host ""
Write-Host "== Installed =="
Write-Host "  real binary : $DestDir\SPASS.exe"
Write-Host "  adapter     : $DestDir\spass_eml_adapter.bat  (EXTERNAL_TOOL_PATHS['spass'])"
Write-Host ""
Write-Host "Verify firsthand:"
Write-Host "  pytest tests/integration/argumentation_analysis/agents/core/logic/test_spass_real.py -v"
Write-Host "  pytest tests/integration/argumentation_analysis/agents/core/logic/test_external_provers_wired.py -k spass -v"
