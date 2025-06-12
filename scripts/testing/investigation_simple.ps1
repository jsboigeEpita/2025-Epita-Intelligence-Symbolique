# Script PowerShell Simple - Investigation Playwright
# Version sans emojis pour eviter les problemes d'encodage

param(
    [string]$Mode = "investigation"
)

$ErrorActionPreference = "Continue"

Write-Host "INVESTIGATION PLAYWRIGHT - TEXTES VARIES" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Configuration
$PROJECT_ROOT = "c:\dev\2025-Epita-Intelligence-Symbolique"
$PLAYWRIGHT_DIR = "$PROJECT_ROOT\tests_playwright"
$TEMP_DIR = "$PROJECT_ROOT\_temp\investigation_playwright"

# Creer repertoire temporaire
if (-not (Test-Path $TEMP_DIR)) {
    New-Item -ItemType Directory -Path $TEMP_DIR -Force | Out-Null
}

Write-Host "Repertoire: $PLAYWRIGHT_DIR" -ForegroundColor Green
Write-Host "Resultats: $TEMP_DIR" -ForegroundColor Green

# Verification des services
Write-Host "`nVERIFICATION DES SERVICES" -ForegroundColor Yellow

$services = @(
    @{ Name = "API Backend"; Url = "http://localhost:5003/api/health" },
    @{ Name = "Interface Web"; Url = "http://localhost:3000/status" }
)

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri $service.Url -TimeoutSec 3 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "OK - $($service.Name) - Operationnel" -ForegroundColor Green
        } else {
            Write-Host "WARNING - $($service.Name) - Status $($response.StatusCode)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "ERROR - $($service.Name) - Non accessible" -ForegroundColor Red
    }
}

# Preparation Playwright
Write-Host "`nPREPARATION PLAYWRIGHT" -ForegroundColor Yellow

Set-Location $PLAYWRIGHT_DIR

if (-not (Test-Path "node_modules")) {
    Write-Host "Installation des dependances npm..." -ForegroundColor Yellow
    npm install
}

# Execution du test principal
Write-Host "`nEXECUTION DES TESTS" -ForegroundColor Yellow

$testCommand = "npx playwright test investigation-textes-varies.spec.js --reporter=list"

Write-Host "Commande: $testCommand" -ForegroundColor Cyan

try {
    # Executer le test
    $process = Start-Process -FilePath "cmd" -ArgumentList "/c", $testCommand -WorkingDirectory $PLAYWRIGHT_DIR -Wait -PassThru -WindowStyle Normal
    
    $exitCode = $process.ExitCode
    
    if ($exitCode -eq 0) {
        Write-Host "SUCCES - Tests termines avec succes" -ForegroundColor Green
    } else {
        Write-Host "ECHEC - Tests termines avec erreurs (Code: $exitCode)" -ForegroundColor Red
    }
    
} catch {
    Write-Host "ERREUR - Exception lors de l'execution: $($_.Exception.Message)" -ForegroundColor Red
    $exitCode = -1
}

# Verification des resultats
$reportPath = "$PLAYWRIGHT_DIR\playwright-report\index.html"
if (Test-Path $reportPath) {
    Write-Host "`nRapport HTML genere: $reportPath" -ForegroundColor Green
    Write-Host "Ouverture du rapport..." -ForegroundColor Yellow
    Start-Process $reportPath
} else {
    Write-Host "`nAucun rapport HTML trouve" -ForegroundColor Yellow
}

# Resume final
Write-Host "`nRESUME FINAL" -ForegroundColor Cyan
Write-Host "=============" -ForegroundColor Cyan
Write-Host "Mode: $Mode" -ForegroundColor White
Write-Host "Code de sortie: $exitCode" -ForegroundColor $(if ($exitCode -eq 0) { "Green" } else { "Red" })
Write-Host "Repertoire resultats: $TEMP_DIR" -ForegroundColor White

Write-Host "`nInvestigation terminee!" -ForegroundColor Green

exit $exitCode