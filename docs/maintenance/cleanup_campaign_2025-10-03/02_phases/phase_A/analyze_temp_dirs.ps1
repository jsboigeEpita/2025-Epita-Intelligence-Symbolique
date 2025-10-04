# Script d'analyse dossiers temporaires - Phase A.2.4
# Date: 2025-10-04
# Analyse les dossiers temporaires pour validation utilisateur avant suppression

Write-Host "=== Analyse Dossiers Temporaires - Phase A.2.4 ===" -ForegroundColor Cyan
Write-Host ""

$tempDirs = @(
    "_temp_jdk_download",
    "_temp_prover9_install",
    "_temp_readme_restoration",
    "portable_jdk"
)

$results = @()
$totalSize = 0
$totalFiles = 0

foreach ($dir in $tempDirs) {
    Write-Host "📁 Analyse: $dir" -ForegroundColor Yellow
    
    if (Test-Path $dir) {
        # Compter fichiers et taille
        $items = Get-ChildItem -Path $dir -Recurse -File -ErrorAction SilentlyContinue
        $dirSize = ($items | Measure-Object -Property Length -Sum).Sum
        $fileCount = $items.Count
        
        # Vérifier tracking Git
        $gitTracked = $false
        try {
            $gitCheck = git ls-files $dir 2>&1
            if ($gitCheck -and ($gitCheck -notmatch "fatal")) {
                $gitTracked = $true
            }
        } catch {
            # Erreur Git ignorée
        }
        
        # Affichage
        Write-Host "  ✅ Existe" -ForegroundColor Green
        Write-Host "  📊 Fichiers: $fileCount"
        Write-Host "  💾 Taille: $([math]::Round($dirSize / 1MB, 2)) MB"
        Write-Host "  🔍 Git Tracking: $(if ($gitTracked) { 'OUI ⚠️' } else { 'Non ✅' })"
        
        # Lister premiers fichiers
        Write-Host "  📄 Contenu (10 premiers):" -ForegroundColor Gray
        $items | Select-Object -First 10 | ForEach-Object {
            $relativePath = $_.FullName.Replace("$PWD\", "")
            $sizeMB = [math]::Round($_.Length / 1MB, 2)
            Write-Host "    - $relativePath ($sizeMB MB)" -ForegroundColor DarkGray
        }
        
        if ($fileCount -gt 10) {
            Write-Host "    ... et $($fileCount - 10) autres fichiers" -ForegroundColor DarkGray
        }
        
        # Stocker résultats
        $results += [PSCustomObject]@{
            Directory = $dir
            Exists = $true
            FileCount = $fileCount
            SizeMB = [math]::Round($dirSize / 1MB, 2)
            GitTracked = $gitTracked
        }
        
        $totalSize += $dirSize
        $totalFiles += $fileCount
        
    } else {
        Write-Host "  ❌ N'existe pas" -ForegroundColor Green
        
        $results += [PSCustomObject]@{
            Directory = $dir
            Exists = $false
            FileCount = 0
            SizeMB = 0
            GitTracked = $false
        }
    }
    
    Write-Host ""
}

# Résumé global
Write-Host "=== Résumé Global ===" -ForegroundColor Cyan
Write-Host "Dossiers analysés: $($tempDirs.Count)"
Write-Host "Dossiers existants: $($results | Where-Object { $_.Exists } | Measure-Object).Count"
Write-Host "Fichiers totaux: $totalFiles"
Write-Host "Taille totale: $([math]::Round($totalSize / 1MB, 2)) MB"
Write-Host ""

# Vérification tracking Git critique
$trackedDirs = $results | Where-Object { $_.GitTracked }
if ($trackedDirs) {
    Write-Host "⚠️ ALERTE: $($trackedDirs.Count) dossier(s) tracké(s) par Git!" -ForegroundColor Red
    $trackedDirs | ForEach-Object {
        Write-Host "  - $($_.Directory)" -ForegroundColor Yellow
    }
    Write-Host ""
}

# Tableau récapitulatif
Write-Host "=== Tableau Récapitulatif ===" -ForegroundColor Cyan
$results | Format-Table -AutoSize

# Recommandations
Write-Host "=== Recommandations ===" -ForegroundColor Cyan
$existingDirs = $results | Where-Object { $_.Exists }

if ($existingDirs.Count -eq 0) {
    Write-Host "✅ Aucun dossier temporaire à supprimer" -ForegroundColor Green
} else {
    Write-Host "📋 Dossiers à examiner pour suppression:" -ForegroundColor Yellow
    $existingDirs | ForEach-Object {
        $status = if ($_.GitTracked) { "⚠️ TRACKÉ GIT" } else { "✅ Non tracké" }
        Write-Host "  - $($_.Directory) - $($_.FileCount) fichiers, $($_.SizeMB) MB - $status"
    }
    Write-Host ""
    Write-Host "⚠️ VALIDATION UTILISATEUR REQUISE avant toute suppression" -ForegroundColor Yellow
}

# Export JSON pour traçabilité
$jsonPath = "docs/maintenance/cleanup_campaign_2025-10-03/02_phases/phase_A/temp_dirs_analysis.json"
$results | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonPath -Encoding UTF8
Write-Host ""
Write-Host "💾 Analyse exportée: $jsonPath" -ForegroundColor Green