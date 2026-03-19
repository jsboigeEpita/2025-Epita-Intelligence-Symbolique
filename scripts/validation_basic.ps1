# Script basic de validation post-pull
Write-Host "=== VALIDATION POST-PULL ===" -ForegroundColor Cyan

# 1. Etat Git
Write-Host "1. Etat Git:" -ForegroundColor Yellow
git status --short
Write-Host ""

# 2. Fichiers clés
Write-Host "2. Fichiers clés:" -ForegroundColor Yellow
$file1 = "../roo-extensions/mcps/internal/servers/roo-state-manager/src/utils/hierarchy-reconstruction-engine.ts"
$file2 = "../roo-extensions/mcps/internal/servers/roo-state-manager/src/utils/roo-storage-detector.ts"

if (Test-Path $file1) {
    $lines1 = (Get-Content $file1).Count
    Write-Host "  OK: $file1 ($lines1 lignes)" -ForegroundColor Green
} else {
    Write-Host "  ERREUR: $file1 manquant" -ForegroundColor Red
}

if (Test-Path $file2) {
    $lines2 = (Get-Content $file2).Count
    Write-Host "  OK: $file2 ($lines2 lignes)" -ForegroundColor Green
} else {
    Write-Host "  ERREUR: $file2 manquant" -ForegroundColor Red
}

# 3. Package.json
Write-Host ""
Write-Host "3. Package.json:" -ForegroundColor Yellow
Set-Location "../roo-extensions/mcps/internal/servers/roo-state-manager"
if (Test-Path "package.json") {
    $pkg = Get-Content "package.json" -Raw | ConvertFrom-Json
    Write-Host "  Version: $($pkg.version)" -ForegroundColor Green
    Write-Host "  Scripts disponibles: $($pkg.scripts.PSObject.Properties.Count)" -ForegroundColor Green
} else {
    Write-Host "  ERREUR: package.json manquant" -ForegroundColor Red
}
Set-Location "../../../"

Write-Host ""
Write-Host "=== FIN VALIDATION ===" -ForegroundColor Cyan