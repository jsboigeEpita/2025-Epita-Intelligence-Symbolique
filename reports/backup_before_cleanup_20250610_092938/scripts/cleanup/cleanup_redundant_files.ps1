# Script PowerShell pour supprimer les fichiers redondants après réorganisation
# Ce script identifie et supprime les fichiers qui ont été déplacés vers la nouvelle structure
# Options:
#   -DryRun : Affiche les actions sans les exécuter
#   -Verbose : Affiche des informations détaillées
#   -Force : Exécute la suppression sans demander de confirmation

param (
    [switch]$DryRun = $false,
    [switch]$Verbose = $false,
    [switch]$Force = $false
)

# Configuration
$ProjectRoot = (Get-Location).Path
$ResultsDir = Join-Path -Path $ProjectRoot -ChildPath "results"
$ReportPath = Join-Path -Path $ProjectRoot -ChildPath "rapport_suppression_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"

# Statistiques
$FilesDeleted = 0
$DirsDeleted = 0
$ActionsPerformed = @()
$FilesVerified = 0
$ErrorsEncountered = 0

# Fonction pour journaliser les actions
function Log-Action {
    param (
        [string]$Message,
        [string]$Type = "INFO"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Type] $Message"
    
    switch ($Type) {
        "INFO" { Write-Host $logMessage -ForegroundColor White }
        "SUCCESS" { Write-Host $logMessage -ForegroundColor Green }
        "WARNING" { Write-Host $logMessage -ForegroundColor Yellow }
        "ERROR" { Write-Host $logMessage -ForegroundColor Red }
        default { Write-Host $logMessage }
    }
    
    $script:ActionsPerformed += $logMessage
}

# Fonction pour vérifier si un fichier existe dans la nouvelle structure
function Test-FileExistsInNewStructure {
    param (
        [string]$OriginalPath,
        [string]$NewStructureRoot
    )
    
    $fileName = Split-Path -Path $OriginalPath -Leaf
    $fileHash = (Get-FileHash -Path $OriginalPath).Hash
    
    # Rechercher tous les fichiers avec le même nom dans la nouvelle structure
    $matchingFiles = Get-ChildItem -Path $NewStructureRoot -Recurse -File | Where-Object { $_.Name -eq $fileName }
    
    foreach ($file in $matchingFiles) {
        $newFileHash = (Get-FileHash -Path $file.FullName).Hash
        if ($newFileHash -eq $fileHash) {
            if ($Verbose) {
                Log-Action "Fichier vérifié: $OriginalPath -> $($file.FullName)" -Type "INFO"
            }
            $script:FilesVerified++
            return $true
        }
    }
    
    return $false
}

# Fonction pour supprimer un fichier
function Remove-RedundantFile {
    param (
        [string]$Path
    )
    
    if (Test-Path -Path $Path) {
        if (-not $DryRun) {
            try {
                Remove-Item -Path $Path -Force
                $script:FilesDeleted++
                Log-Action "Fichier supprimé: $Path" -Type "SUCCESS"
            }
            catch {
                $script:ErrorsEncountered++
                Log-Action "Erreur lors de la suppression du fichier: $Path - $_" -Type "ERROR"
            }
        }
        else {
            Log-Action "Simulation - Fichier à supprimer: $Path" -Type "INFO"
        }
    }
}

# Fonction pour vérifier si un dossier est vide
function Test-DirectoryEmpty {
    param (
        [string]$Path
    )
    
    return (-not (Get-ChildItem -Path $Path -Recurse -File))
}

# Fonction pour supprimer un dossier vide
function Remove-EmptyDirectory {
    param (
        [string]$Path
    )
    
    if (Test-Path -Path $Path) {
        if (Test-DirectoryEmpty -Path $Path) {
            if (-not $DryRun) {
                try {
                    Remove-Item -Path $Path -Force -Recurse
                    $script:DirsDeleted++
                    Log-Action "Dossier vide supprimé: $Path" -Type "SUCCESS"
                }
                catch {
                    $script:ErrorsEncountered++
                    Log-Action "Erreur lors de la suppression du dossier: $Path - $_" -Type "ERROR"
                }
            }
            else {
                Log-Action "Simulation - Dossier vide à supprimer: $Path" -Type "INFO"
            }
        }
        elseif ($Verbose) {
            Log-Action "Dossier non vide, conservation: $Path" -Type "INFO"
        }
    }
}

# Afficher le mode d'exécution
$mode = if ($DryRun) { "Mode simulation" } else { "Mode exécution" }
Write-Host "=== Démarrage de la suppression des fichiers redondants ($mode) ===" -ForegroundColor Cyan
Write-Host "Répertoire racine du projet: $ProjectRoot" -ForegroundColor Cyan

# Demander confirmation si -Force n'est pas spécifié
if (-not $Force -and -not $DryRun) {
    $confirmation = Read-Host "Cette opération va supprimer les fichiers redondants après réorganisation. Continuer? (O/N)"
    if ($confirmation -ne "O") {
        Write-Host "Opération annulée." -ForegroundColor Yellow
        exit
    }
}

# 1. Identifier les dossiers qui contiennent potentiellement des fichiers redondants
Write-Host "`n=== Identification des dossiers contenant des fichiers potentiellement redondants ===" -ForegroundColor Green

$potentialRedundantDirs = @(
    (Join-Path -Path $ResultsDir -ChildPath "comprehensive_report"),
    (Join-Path -Path $ResultsDir -ChildPath "performance_comparison"),
    (Join-Path -Path $ResultsDir -ChildPath "performance_tests")
)

# Ajouter les fichiers à la racine du dossier results qui pourraient avoir été déplacés
$potentialRedundantFiles = @()
$potentialRedundantFiles += Get-ChildItem -Path $ResultsDir -File | Where-Object {
    $_.Name -match "advanced_rhetorical_analysis_.*\.json" -or
    $_.Name -match "rhetorical_analysis_.*\.json" -or
    $_.Name -match "rhetorical_analyses_.*\.json" -or
    $_.Name -match "rapport_synthese_global_.*\.md"
}

# 2. Vérifier chaque fichier potentiellement redondant
Write-Host "`n=== Vérification des fichiers potentiellement redondants ===" -ForegroundColor Green

foreach ($file in $potentialRedundantFiles) {
    if (Test-FileExistsInNewStructure -OriginalPath $file.FullName -NewStructureRoot $ResultsDir) {
        Remove-RedundantFile -Path $file.FullName
    }
    else {
        Log-Action "Fichier non trouvé dans la nouvelle structure, conservation: $($file.FullName)" -Type "WARNING"
    }
}

# 3. Vérifier les fichiers dans les dossiers potentiellement redondants
foreach ($dir in $potentialRedundantDirs) {
    if (Test-Path -Path $dir) {
        Write-Host "`n=== Traitement du dossier: $dir ===" -ForegroundColor Green
        
        # Traiter les fichiers dans ce dossier
        Get-ChildItem -Path $dir -Recurse -File | ForEach-Object {
            if (Test-FileExistsInNewStructure -OriginalPath $_.FullName -NewStructureRoot $ResultsDir) {
                Remove-RedundantFile -Path $_.FullName
            }
            else {
                Log-Action "Fichier non trouvé dans la nouvelle structure, conservation: $($_.FullName)" -Type "WARNING"
            }
        }
    }
}

# 4. Supprimer les dossiers vides
Write-Host "`n=== Suppression des dossiers vides ===" -ForegroundColor Green

# Commencer par les sous-dossiers les plus profonds
$allDirs = Get-ChildItem -Path $ResultsDir -Recurse -Directory | 
           Where-Object { $_.FullName -like "*comprehensive_report*" -or 
                         $_.FullName -like "*performance_comparison*" -or 
                         $_.FullName -like "*performance_tests*" } |
           Sort-Object -Property FullName -Descending

foreach ($dir in $allDirs) {
    Remove-EmptyDirectory -Path $dir.FullName
}

# Supprimer les dossiers principaux s'ils sont vides
foreach ($dir in $potentialRedundantDirs) {
    Remove-EmptyDirectory -Path $dir
}

# 5. Générer un rapport de suppression
Write-Host "`n=== Génération du rapport de suppression ===" -ForegroundColor Green

$reportContent = @"
# Rapport de Suppression des Fichiers Redondants
Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Résumé des actions

- **Fichiers vérifiés:** $FilesVerified
- **Fichiers supprimés:** $FilesDeleted
- **Dossiers supprimés:** $DirsDeleted
- **Erreurs rencontrées:** $ErrorsEncountered

## Détails des actions effectuées

$(($ActionsPerformed | ForEach-Object { "$_" }) -join "`n")

## Recommandations

1. Vérifiez que tous les fichiers nécessaires sont bien présents dans la nouvelle structure
2. Si vous constatez des erreurs, consultez les messages d'erreur ci-dessus
3. Pour les fichiers conservés (non trouvés dans la nouvelle structure), évaluez s'ils doivent être intégrés manuellement

## Prochaines étapes

1. Exécutez périodiquement le script de nettoyage principal pour maintenir la structure du projet
2. Mettez à jour la documentation si de nouveaux types de fichiers sont ajoutés
3. Assurez-vous que tous les membres de l'équipe utilisent la nouvelle structure pour les futurs résultats
"@

if (-not $DryRun) {
    Set-Content -Path $ReportPath -Value $reportContent
    Write-Host "Rapport de suppression généré: $ReportPath" -ForegroundColor Green
}
else {
    Write-Host "Mode simulation: le rapport de suppression n'a pas été généré." -ForegroundColor Yellow
}

# Afficher le résumé
Write-Host "`n=== Résumé des actions ===" -ForegroundColor Cyan
Write-Host "Fichiers vérifiés: $FilesVerified" -ForegroundColor White
Write-Host "Fichiers supprimés: $FilesDeleted" -ForegroundColor White
Write-Host "Dossiers supprimés: $DirsDeleted" -ForegroundColor White
Write-Host "Erreurs rencontrées: $ErrorsEncountered" -ForegroundColor White

Write-Host "`n=== Suppression des fichiers redondants terminée ===" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "`nPour exécuter réellement ces actions, relancez le script sans l'option -DryRun" -ForegroundColor Yellow
}
else {
    Write-Host "`nLes fichiers redondants ont été supprimés avec succès." -ForegroundColor Green
    Write-Host "Un rapport détaillé a été généré: $ReportPath" -ForegroundColor Green
}