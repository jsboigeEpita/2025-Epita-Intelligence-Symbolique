<#
.SYNOPSIS
    Live re-verify orchestrator wrapper (Windows).

.DESCRIPTION
    PowerShell wrapper around run_live_reverify.py.
    Supports --live, --mock, and --aggregate-only modes.

.EXAMPLE
    # Mock test (no LLM):
    .\scripts\run_live_reverify.ps1 -Mock

    # Aggregate existing results:
    .\scripts\run_live_reverify.ps1 -AggregateOnly

    # Full live run:
    .\scripts\run_live_reverify.ps1 -Live
#>

param(
    [switch]$Live,
    [switch]$Mock,
    [switch]$AggregateOnly,
    [string]$CondaEnv = "projet-is-roo-new"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

# Determine mode
$modeArg = ""
if ($Live) { $modeArg = "--live" }
elseif ($Mock) { $modeArg = "--mock" }
elseif ($AggregateOnly) { $modeArg = "--aggregate-only" }
else {
    Write-Host "Usage: run_live_reverify.ps1 -Live|-Mock|-AggregateOnly [-CondaEnv <name>]"
    Write-Host ""
    Write-Host "  -Live           Run live benchmark (requires funded LLM key)"
    Write-Host "  -Mock           Use synthetic data (no LLM, testing only)"
    Write-Host "  -AggregateOnly  Aggregate existing JSON outputs (no re-run)"
    exit 2
}

Write-Host "[reverify.ps1] Starting with mode: $modeArg"
Write-Host "[reverify.ps1] Conda env: $CondaEnv"
Write-Host "[reverify.ps1] Repo: $RepoRoot"

# Run via conda
$cmd = @(
    "conda", "run", "-n", $CondaEnv, "--no-capture-output",
    "python", (Join-Path $RepoRoot "scripts" "run_live_reverify.py"),
    $modeArg,
    "--conda-env", $CondaEnv
)

& $cmd[0] $cmd[1..($cmd.Length - 1)]

$exitCode = $LASTEXITCODE
if ($exitCode -eq 0) {
    Write-Host "[reverify.ps1] SUCCESS - all corpora passed"
} else {
    Write-Host "[reverify.ps1] COMPLETED WITH ERRORS (exit=$exitCode)"
}

exit $exitCode
