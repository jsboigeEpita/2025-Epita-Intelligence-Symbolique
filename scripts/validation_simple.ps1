# Script simple de validation post-pull
# Encodage UTF-8, pas de dépendances complexes

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "=== VALIDATION POST-PULL ===" -ForegroundColor Cyan
Write-Host ""

# 1. Vérification Git
Write-Host "1. Etat Git:" -ForegroundColor Yellow
git status --short
Write-Host ""

# 2. Vérification fichiers clés
Write-Host "2. Fichiers clés:" -ForegroundColor Yellow
$files = @(
    "../roo-extensions/mcps/internal/servers/roo-state-manager/src/utils/hierarchy-reconstruction-engine.ts",
    "../roo-extensions/mcps/internal/servers/roo-state-manager/src/utils/roo-storage-detector.ts"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        $lines = (Get-Content $file).Count
        Write-Host "  ✓ $file ($lines lignes)" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file (manquant)" -ForegroundColor Red
    }
}
Write-Host ""

# 3. Test simple avec MCP
Write-Host "3. Test MCP:" -ForegroundColor Yellow
try {
    # Test simple de détection
    $result = node -e "
        const { RooStorageDetector } = require('./dist/src/utils/roo-storage-detector.js');
        console.log('MCP OK');
    " 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ MCP accessible" -ForegroundColor Green
    } else {
        Write-Host "  ✗ MCP non compilé" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ Erreur MCP" -ForegroundColor Red
}
Write-Host ""

# 4. Vérification package.json
Write-Host "4. Package.json:" -ForegroundColor Yellow
Set-Location "../roo-extensions/mcps/internal/servers/roo-state-manager"
if (Test-Path "package.json") {
    $pkg = Get-Content "package.json" | ConvertFrom-Json
    Write-Host "  ✓ Version: $($pkg.version)" -ForegroundColor Green
    Write-Host "  ✓ Scripts: $($pkg.scripts.PSObject.Properties.Count)" -ForegroundColor Green
} else {
    Write-Host "  ✗ package.json manquant" -ForegroundColor Red
}
Set-Location "../../../"

Write-Host ""
Write-Host "=== FIN VALIDATION ===" -ForegroundColor Cyan