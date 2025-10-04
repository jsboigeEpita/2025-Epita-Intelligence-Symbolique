# Script de suppression dossiers temporaires - Phase A.2.4
# Date: 2025-10-04
# Suppression validée utilisateur : 4 dossiers (306.36 MB)

Write-Host "=== Suppression Dossiers Temporaires - Phase A.2.4 ===" -ForegroundColor Cyan
Write-Host ""

$tempDirs = @(
    "_temp_jdk_download",
    "_temp_prover9_install",
    "_temp_readme_restoration",
    "portable_jdk"
)

$totalDeleted = 0
$totalSize = 0

foreach ($dir in $tempDirs) {
    if (Test-Path $dir) {
        Write-Host "🗑️  Suppression: $dir" -ForegroundColor Yellow
        
        # Calculer taille avant suppression
        $items = Get-ChildItem -Path $dir -Recurse -File -ErrorAction SilentlyContinue
        $dirSize = ($items | Measure-Object -Property Length -Sum).Sum
        $fileCount = $items.Count
        
        Write-Host "   Fichiers: $fileCount"
        Write-Host "   Taille: $([math]::Round($dirSize / 1MB, 2)) MB"
        
        # Suppression
        try {
            Remove-Item -Path $dir -Recurse -Force -ErrorAction Stop
            Write-Host "   ✅ Supprimé avec succès" -ForegroundColor Green
            $totalDeleted++
            $totalSize += $dirSize
        } catch {
            Write-Host "   ❌ Erreur: $($_.Exception.Message)" -ForegroundColor Red
        }
        
    } else {
        Write-Host "⚠️  $dir n'existe pas (déjà supprimé?)" -ForegroundColor Gray
    }
    
    Write-Host ""
}

Write-Host "=== Résumé Suppression ===" -ForegroundColor Cyan
Write-Host "Dossiers supprimés: $totalDeleted / $($tempDirs.Count)"
Write-Host "Espace récupéré: $([math]::Round($totalSize / 1MB, 2)) MB"
Write-Host ""

if ($totalDeleted -eq $tempDirs.Count) {
    Write-Host "✅ Tous les dossiers temporaires supprimés avec succès" -ForegroundColor Green
} else {
    Write-Host "⚠️ Certains dossiers n'ont pas pu être supprimés" -ForegroundColor Yellow
}