# Script de vérification structure libs/
Write-Host "=== Vérification Structure libs/ ===" -ForegroundColor Cyan
Write-Host ""

# Vérifier existence libs/
if (-not (Test-Path "libs")) {
    Write-Host "❌ Répertoire libs/ n'existe pas!" -ForegroundColor Red
    exit 1
}

Write-Host "📁 Contenu libs/ (répertoires principaux):" -ForegroundColor Yellow
Get-ChildItem -Path "libs" -Directory | ForEach-Object {
    Write-Host "  - $($_.Name)" -ForegroundColor Gray
}
Write-Host ""

Write-Host "🔍 Recherche Prover9 dans libs/:" -ForegroundColor Yellow
$prover9Files = Get-ChildItem -Path "libs" -Recurse -Filter "*prover*" -ErrorAction SilentlyContinue
if ($prover9Files) {
    $prover9Files | ForEach-Object {
        Write-Host "  ✅ $($_.FullName)" -ForegroundColor Green
    }
} else {
    Write-Host "  ❌ Aucun fichier Prover9 trouvé dans libs/" -ForegroundColor Red
}
Write-Host ""

Write-Host "🔍 Recherche JDK dans libs/:" -ForegroundColor Yellow
$jdkFiles = Get-ChildItem -Path "libs" -Recurse -Filter "*jdk*" -ErrorAction SilentlyContinue
if ($jdkFiles) {
    $jdkFiles | ForEach-Object {
        Write-Host "  ✅ $($_.FullName)" -ForegroundColor Green
    }
} else {
    Write-Host "  ❌ Aucun fichier JDK trouvé dans libs/" -ForegroundColor Red
}
Write-Host ""

Write-Host "📊 Taille libs/:" -ForegroundColor Yellow
$libsSize = (Get-ChildItem -Path "libs" -Recurse -File | Measure-Object -Property Length -Sum).Sum
Write-Host "  Total: $([math]::Round($libsSize / 1MB, 2)) MB" -ForegroundColor Gray