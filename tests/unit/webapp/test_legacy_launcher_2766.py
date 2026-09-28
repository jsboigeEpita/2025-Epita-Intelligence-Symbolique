"""Exercise the PowerShell launcher with synthetic jobs and HTTP readiness."""

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = ROOT / "config" / "clean" / "web_application_launcher.ps1"


@pytest.mark.parametrize(
    ("mode", "expected_jobs", "expected_urls"),
    [
        ("BackendOnly", ("Backend",), ("http://localhost:8095/health",)),
        ("FrontendOnly", ("Frontend",), ("http://localhost:3000",)),
        (
            "",
            ("Backend", "Frontend"),
            ("http://localhost:8095/health", "http://localhost:3000"),
        ),
    ],
)
def test_launcher_uses_supported_services_without_starting_them(
    tmp_path: Path,
    mode: str,
    expected_jobs: tuple[str, ...],
    expected_urls: tuple[str, ...],
) -> None:
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell 7 is not installed")
    harness = tmp_path / "harness.ps1"
    harness.write_text(
        r"""
param([string]$Launcher, [string]$Mode)
$ErrorActionPreference = 'Stop'
$global:fakeJobs = [System.Collections.ArrayList]::new()
function Start-Job {
    param($ScriptBlock, $ArgumentList, $Name)
    Write-Host "JOB:${Name}:$($ArgumentList -join '|'):$ScriptBlock"
    $job = [pscustomobject]@{ Id = 1; Name = $Name; State = 'Running' }
    $null = $global:fakeJobs.Add($job)
    $job
}
function Invoke-WebRequest {
    param($Uri, $TimeoutSec, $ErrorAction)
    Write-Host "PROBE:$Uri"
}
function npm { Write-Host "NPM:$args"; $global:LASTEXITCODE = 0 }
function Test-Path {
    param($Path)
    if ($Path -eq 'node_modules') { return $false }
    Microsoft.PowerShell.Management\Test-Path $Path
}
function Start-Sleep { foreach ($job in $global:fakeJobs) { $job.State = 'Stopped' } }
function Stop-Job { param($InputObject, [switch]$Force) Write-Host "STOP:$($InputObject.Name)" }
function Remove-Job { param($InputObject, [switch]$Force) Write-Host "REMOVE:$($InputObject.Name)" }
if ($Mode -eq 'BackendOnly') { & $Launcher -BackendOnly }
elseif ($Mode -eq 'FrontendOnly') { & $Launcher -FrontendOnly }
else { & $Launcher }
exit $LASTEXITCODE
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [pwsh, "-NoProfile", "-File", str(harness), str(LAUNCHER), mode],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for job in ("Backend", "Frontend"):
        assert (f"JOB:{job}:" in result.stdout) == (job in expected_jobs)
        assert (f"REMOVE:{job}" in result.stdout) == (job in expected_jobs)
    for url in ("http://localhost:8095/health", "http://localhost:3000"):
        assert (f"PROBE:{url}" in result.stdout) == (url in expected_urls)
    if "Backend" in expected_jobs:
        assert "-m uvicorn api.main:app --host 127.0.0.1 --port 8095" in result.stdout
        assert str(ROOT) in result.stdout
    if "Frontend" in expected_jobs:
        assert (
            str(ROOT / "services" / "web_api" / "interface-web-argumentative")
            in result.stdout
        )
        assert "npm start" in result.stdout
        assert "NPM:install" in result.stdout
    assert "SUCCESS" in result.stdout


@pytest.mark.parametrize("stopped_early", [False, True])
def test_launcher_fails_when_service_is_not_ready(
    tmp_path: Path, stopped_early: bool
) -> None:
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell 7 is not installed")
    harness = tmp_path / "unready.ps1"
    harness.write_text(
        """
param([string]$Launcher, [string]$JobState)
function Start-Job { param($ScriptBlock, $ArgumentList, $Name)
    [pscustomobject]@{ Id = 1; Name = $Name; State = $JobState }
}
function Invoke-WebRequest {
    if ($JobState -eq 'Running') { throw 'Synthetic service unavailable' }
}
function Start-Sleep { }
function Stop-Job { param($InputObject) Write-Output "STOP:$($InputObject.Name)" }
function Remove-Job { param($InputObject, [switch]$Force) Write-Output "REMOVE:$($InputObject.Name)" }
& $Launcher -BackendOnly
exit $LASTEXITCODE
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [
            pwsh,
            "-NoProfile",
            "-File",
            str(harness),
            str(LAUNCHER),
            "Stopped" if stopped_early else "Running",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert ("STOP:Backend" in result.stdout) is (not stopped_early)
    assert "REMOVE:Backend" in result.stdout
    assert "SUCCESS" not in result.stdout


def test_launcher_cleans_backend_if_frontend_install_fails(tmp_path: Path) -> None:
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell 7 is not installed")
    harness = tmp_path / "failed_install.ps1"
    harness.write_text(
        r"""
param([string]$Launcher)
function Start-Job {
    param($ScriptBlock, $ArgumentList, $Name)
    Write-Host "JOB:$Name"
    [pscustomobject]@{ Id = 1; Name = $Name; State = 'Running' }
}
function Test-Path {
    param($Path)
    if ($Path -eq 'node_modules') { return $false }
    Microsoft.PowerShell.Management\Test-Path $Path
}
function npm { $global:LASTEXITCODE = 1 }
function Stop-Job { param($InputObject) Write-Host "STOP:$($InputObject.Name)" }
function Remove-Job { param($InputObject, [switch]$Force) Write-Host "REMOVE:$($InputObject.Name)" }
& $Launcher
exit $LASTEXITCODE
""",
        encoding="utf-8",
    )
    result = subprocess.run(
        [pwsh, "-NoProfile", "-File", str(harness), str(LAUNCHER)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "JOB:Backend" in result.stdout
    assert "JOB:Frontend" not in result.stdout
    assert "STOP:Backend" in result.stdout
    assert "REMOVE:Backend" in result.stdout
    assert "SUCCESS" not in result.stdout
