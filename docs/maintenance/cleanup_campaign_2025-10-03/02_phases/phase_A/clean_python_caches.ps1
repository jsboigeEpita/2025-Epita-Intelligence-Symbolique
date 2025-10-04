# Script de Nettoyage des Caches Python - Phase A.2.2
# Date: 2025-10-03
# Description: Liste et supprime les répertoires __pycache__ du projet

param(
    [switch]$DryRun = $false,
    [switch]$Verbose = $false
)

Write-Host "=== Nettoyage Caches Python - Phase A.2.2 ===" -ForegroundColor Cyan
Write-Host "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Gray
Write-Host ""

# Configuration
$projectRoot = "d:\2025-Epita-Intelligence-Symbolique"
Set-Location $projectRoot

# Étape 1: Lister les répertoires __pycache__
Write-Host "Étape 1: Recherche des répertoires __pycache__..." -ForegroundColor Yellow
$pycacheDirs = Get-ChildItem -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue

$count = $pycacheDirs.Count
Write-Host "Trouvé: $count répertoires __pycache__" -ForegroundColor Green
Write-Host ""

if ($count -eq 0) {
    Write-Host "Aucun répertoire __pycache__ trouvé. Nettoyage déjà effectué." -ForegroundColor Green
    exit 0
}

# Étape 2: Afficher les 10 premiers pour validation
Write-Host "Échantillon (10 premiers):" -ForegroundColor Yellow
$pycacheDirs | Select-Object -First 10 | ForEach-Object {
    $relativePath = $_.FullName.Replace($projectRoot, ".")
    Write-Host "  - $relativePath" -ForegroundColor Gray
}

if ($count -gt 10) {
    Write-Host "  ... et $($count - 10) autres" -ForegroundColor Gray
}
Write-Host ""

# Étape 3: Vérifier le statut Git (ne doivent pas être trackés)
Write-Host "Étape 2: Vérification statut Git..." -ForegroundColor Yellow
$tracked = git ls-files | Select-String "__pycache__"
if ($tracked) {
    Write-Host "ATTENTION: Des fichiers __pycache__ sont trackés par Git!" -ForegroundColor Red
    $tracked | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    Write-Host ""
    Write-Host "Arrêt du script. Veuillez d'abord retirer ces fichiers du tracking Git." -ForegroundColor Red
    exit 1
}
Write-Host "OK: Aucun __pycache__ tracké par Git." -ForegroundColor Green
Write-Host ""

# Étape 4: Suppression
if ($DryRun) {
    Write-Host "MODE DRY-RUN: Simulation de suppression (aucune modification)" -ForegroundColor Magenta
    Write-Host "Répertoires qui seraient supprimés: $count" -ForegroundColor Magenta
} else {
    Write-Host "Étape 3: Suppression des répertoires __pycache__..." -ForegroundColor Yellow
    
    $successCount = 0
    $errorCount = 0
    
    foreach ($dir in $pycacheDirs) {
        try {
            if ($Verbose) {
                $relativePath = $dir.FullName.Replace($projectRoot, ".")
                Write-Host "  Suppression: $relativePath" -ForegroundColor Gray
            }
            Remove-Item -Path $dir.FullName -Recurse -Force -ErrorAction Stop
            $successCount++
        } catch {
            Write-Host "  ERREUR: $($dir.FullName) - $_" -ForegroundColor Red
            $errorCount++
        }
    }
    
    Write-Host ""
    Write-Host "Résultat:" -ForegroundColor Cyan
    Write-Host "  - Supprimés avec succès: $successCount répertoires" -ForegroundColor Green
    if ($errorCount -gt 0) {
        Write-Host "  - Erreurs: $errorCount répertoires" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "=== Script terminé ===" -ForegroundColor Cyan

# Génération du rapport
$reportPath = ".temp\cleanup_campaign_2025-10-03\02_phases\phase_A\report_A22_python_caches.txt"
$reportContent = @"
Rapport Nettoyage Caches Python - Phase A.2.2
Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
Mode: $(if ($DryRun) { "DRY-RUN" } else { "RÉEL" })

Répertoires __pycache__ trouvés: $count
$(if (-not $DryRun) { "Répertoires supprimés: $successCount" })
$(if ($errorCount -gt 0) { "Erreurs: $errorCount" })

Statut: $(if ($DryRun) { "SIMULATION" } elseif ($errorCount -eq 0) { "SUCCÈS" } else { "PARTIEL" })
"@

$reportContent | Out-File -FilePath $reportPath -Encoding UTF8
Write-Host "Rapport sauvegardé: $reportPath" -ForegroundColor Gray