# Script PowerShell pour le nettoyage global du projet
# Ce script effectue des actions ciblées pour nettoyer et réorganiser le projet
# Options:
#   -DryRun : Affiche les actions sans les exécuter
#   -Verbose : Affiche des informations détaillées
#   -Force : Exécute le nettoyage sans demander de confirmation

param (
    [switch]$DryRun = $false,
    [switch]$Verbose = $false,
    [switch]$Force = $false
)

# Configuration
$ProjectRoot = (Get-Location).Path
$ResultsDir = Join-Path -Path $ProjectRoot -ChildPath "results"
$ArchivesDir = Join-Path -Path $ProjectRoot -ChildPath "_archives"
$BackupDir = Join-Path -Path $ArchivesDir -ChildPath "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
$ReportPath = Join-Path -Path $ProjectRoot -ChildPath "rapport_nettoyage_$(Get-Date -Format 'yyyyMMdd_HHmmss').md"

# Statistiques
$FilesDeleted = 0
$FilesMoved = 0
$DirsCreated = 0
$DirsDeleted = 0
$ActionsPerformed = @()

# Fonction pour journaliser les actions
function Log-Action {
    param (
        [string]$Message
    )
    
    Write-Host $Message
    $script:ActionsPerformed += $Message
}

# Fonction pour créer un dossier s'il n'existe pas
function Create-DirectoryIfNotExists {
    param (
        [string]$Path
    )
    
    if (-not (Test-Path -Path $Path)) {
        if (-not $DryRun) {
            New-Item -Path $Path -ItemType Directory -Force | Out-Null
            $script:DirsCreated++
        }
        Log-Action "Création du dossier: $Path"
    }
}

# Fonction pour déplacer un fichier
function Move-FileIfDifferent {
    param (
        [string]$Source,
        [string]$Destination
    )
    
    if (Test-Path -Path $Source) {
        $destDir = Split-Path -Path $Destination -Parent
        Create-DirectoryIfNotExists -Path $destDir
        
        if (-not (Test-Path -Path $Destination) -or 
            (Get-FileHash -Path $Source).Hash -ne (Get-FileHash -Path $Destination).Hash) {
            
            if (-not $DryRun) {
                Move-Item -Path $Source -Destination $Destination -Force
                $script:FilesMoved++
            }
            Log-Action "Déplacement du fichier: $Source -> $Destination"
        }
        elseif ($Verbose) {
            Log-Action "Fichier identique, ignoré: $Source"
        }
    }
}

# Fonction pour supprimer un fichier
function Remove-FileIfExists {
    param (
        [string]$Path
    )
    
    if (Test-Path -Path $Path) {
        if (-not $DryRun) {
            Remove-Item -Path $Path -Force
            $script:FilesDeleted++
        }
        Log-Action "Suppression du fichier: $Path"
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
                Remove-Item -Path $Path -Force -Recurse
                $script:DirsDeleted++
            }
            Log-Action "Suppression du dossier vide: $Path"
        }
    }
}

# Afficher le mode d'exécution
$mode = if ($DryRun) { "Mode simulation" } else { "Mode exécution" }
Write-Host "=== Démarrage du nettoyage global du projet ($mode) ===" -ForegroundColor Cyan
Write-Host "Répertoire racine du projet: $ProjectRoot" -ForegroundColor Cyan

# Demander confirmation si -Force n'est pas spécifié
if (-not $Force -and -not $DryRun) {
    $confirmation = Read-Host "Cette opération va réorganiser les fichiers du projet. Continuer? (O/N)"
    if ($confirmation -ne "O") {
        Write-Host "Opération annulée." -ForegroundColor Yellow
        exit
    }
}

# 1. Créer une sauvegarde du dossier results
Write-Host "`n=== Création d'une sauvegarde du dossier results ===" -ForegroundColor Green

if (Test-Path -Path $ResultsDir) {
    Log-Action "Sauvegarde du dossier results dans $BackupDir"
    
    if (-not $DryRun) {
        Create-DirectoryIfNotExists -Path $BackupDir
        
        # Copier le contenu du dossier results
        Get-ChildItem -Path $ResultsDir -Recurse -File | ForEach-Object {
            $relativePath = $_.FullName.Substring($ResultsDir.Length + 1)
            $backupPath = Join-Path -Path $BackupDir -ChildPath $relativePath
            $backupDir = Split-Path -Path $backupPath -Parent
            
            if (-not (Test-Path -Path $backupDir)) {
                New-Item -Path $backupDir -ItemType Directory -Force | Out-Null
            }
            
            Copy-Item -Path $_.FullName -Destination $backupPath -Force
            if ($Verbose) {
                Write-Host "Sauvegardé: $($_.FullName) -> $backupPath"
            }
        }
        
        # Créer un fichier metadata.json pour la sauvegarde
        $metadata = @{
            date = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
            description = "Sauvegarde avant nettoyage global du projet"
            source_dir = $ResultsDir
        } | ConvertTo-Json
        
        Set-Content -Path (Join-Path -Path $BackupDir -ChildPath "metadata.json") -Value $metadata
    }
}
else {
    Write-Host "Le dossier $ResultsDir n'existe pas, aucune sauvegarde nécessaire." -ForegroundColor Yellow
}

# 2. Supprimer les fichiers temporaires
Write-Host "`n=== Suppression des fichiers temporaires ===" -ForegroundColor Green

$tempPatterns = @(
    "__pycache__",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".ipynb_checkpoints",
    "*.swp",
    "*.swo",
    "*~",
    "Thumbs.db",
    ".DS_Store"
)

foreach ($pattern in $tempPatterns) {
    $tempFiles = Get-ChildItem -Path $ProjectRoot -Include $pattern -Recurse -ErrorAction SilentlyContinue | 
                 Where-Object { $_.FullName -notlike "*\.git\*" -and $_.FullName -notlike "*\venv\*" -and $_.FullName -notlike "*\env\*" }
    
    foreach ($file in $tempFiles) {
        if (-not $DryRun) {
            if ($file.PSIsContainer) {
                Remove-Item -Path $file.FullName -Force -Recurse
            }
            else {
                Remove-Item -Path $file.FullName -Force
            }
            $script:FilesDeleted++
        }
        
        $fileType = if ($file.PSIsContainer) { "dossier" } else { "fichier" }
        Log-Action "Suppression du $fileType temporaire: $($file.FullName)"
    }
}

# 3. Créer la structure cible pour le dossier results
Write-Host "`n=== Création de la structure cible pour le dossier results ===" -ForegroundColor Green

$targetStructure = @(
    "analyses/basic",
    "analyses/advanced",
    "summaries/Débats_Lincoln-Douglas",
    "summaries/Discours_Hitler",
    "comparisons/metrics",
    "comparisons/visualizations",
    "reports/comprehensive",
    "reports/performance",
    "visualizations"
)

foreach ($dir in $targetStructure) {
    $dirPath = Join-Path -Path $ResultsDir -ChildPath $dir
    Create-DirectoryIfNotExists -Path $dirPath
}

# 4. Organiser les fichiers par type
Write-Host "`n=== Organisation des fichiers par type ===" -ForegroundColor Green

# Déplacer les fichiers JSON d'analyse
Get-ChildItem -Path $ResultsDir -Filter "advanced_rhetorical_analysis_*.json" -ErrorAction SilentlyContinue | 
    ForEach-Object { 
        $destPath = Join-Path -Path $ResultsDir -ChildPath "analyses/advanced/$($_.Name)"
        Move-FileIfDifferent -Source $_.FullName -Destination $destPath
    }

Get-ChildItem -Path $ResultsDir -Filter "rhetorical_analysis_*.json" -ErrorAction SilentlyContinue | 
    ForEach-Object { 
        $destPath = Join-Path -Path $ResultsDir -ChildPath "analyses/basic/$($_.Name)"
        Move-FileIfDifferent -Source $_.FullName -Destination $destPath
    }

Get-ChildItem -Path $ResultsDir -Filter "rhetorical_analyses_*.json" -ErrorAction SilentlyContinue | 
    ForEach-Object { 
        $destPath = Join-Path -Path $ResultsDir -ChildPath "analyses/basic/$($_.Name)"
        Move-FileIfDifferent -Source $_.FullName -Destination $destPath
    }

# Déplacer les rapports de synthèse
Get-ChildItem -Path $ResultsDir -Filter "rapport_synthese_global_*.md" -ErrorAction SilentlyContinue | 
    ForEach-Object { 
        $destPath = Join-Path -Path $ResultsDir -ChildPath "reports/comprehensive/$($_.Name)"
        Move-FileIfDifferent -Source $_.FullName -Destination $destPath
    }

# 5. Organiser les fichiers du rapport complet
Write-Host "`n=== Organisation des fichiers du rapport complet ===" -ForegroundColor Green

$compReportDir = Join-Path -Path $ResultsDir -ChildPath "comprehensive_report"
if (Test-Path -Path $compReportDir) {
    # Déplacer les fichiers MD vers reports/comprehensive
    Get-ChildItem -Path $compReportDir -Filter "*.md" -ErrorAction SilentlyContinue | 
        ForEach-Object { 
            $destPath = Join-Path -Path $ResultsDir -ChildPath "reports/comprehensive/$($_.Name)"
            Move-FileIfDifferent -Source $_.FullName -Destination $destPath
        }
    
    # Déplacer les fichiers HTML vers reports/comprehensive
    Get-ChildItem -Path $compReportDir -Filter "*.html" -ErrorAction SilentlyContinue | 
        ForEach-Object { 
            $destPath = Join-Path -Path $ResultsDir -ChildPath "reports/comprehensive/$($_.Name)"
            Move-FileIfDifferent -Source $_.FullName -Destination $destPath
        }
    
    # Déplacer les visualisations
    $visDir = Join-Path -Path $compReportDir -ChildPath "visualizations"
    if (Test-Path -Path $visDir) {
        Get-ChildItem -Path $visDir -Filter "*.png" -ErrorAction SilentlyContinue | 
            ForEach-Object { 
                $destPath = Join-Path -Path $ResultsDir -ChildPath "visualizations/$($_.Name)"
                Move-FileIfDifferent -Source $_.FullName -Destination $destPath
            }
    }
}

# 6. Organiser les fichiers de comparaison de performance
Write-Host "`n=== Organisation des fichiers de comparaison de performance ===" -ForegroundColor Green

$perfCompDir = Join-Path -Path $ResultsDir -ChildPath "performance_comparison"
if (Test-Path -Path $perfCompDir) {
    # Déplacer les fichiers MD vers reports/performance
    Get-ChildItem -Path $perfCompDir -Filter "*.md" -ErrorAction SilentlyContinue | 
        ForEach-Object { 
            $destPath = Join-Path -Path $ResultsDir -ChildPath "reports/performance/$($_.Name)"
            Move-FileIfDifferent -Source $_.FullName -Destination $destPath
        }
    
    # Déplacer les fichiers CSV vers comparisons/metrics
    Get-ChildItem -Path $perfCompDir -Filter "*.csv" -ErrorAction SilentlyContinue | 
        ForEach-Object { 
            $destPath = Join-Path -Path $ResultsDir -ChildPath "comparisons/metrics/$($_.Name)"
            Move-FileIfDifferent -Source $_.FullName -Destination $destPath
        }
    
    # Déplacer les visualisations
    Get-ChildItem -Path $perfCompDir -Filter "*.png" -ErrorAction SilentlyContinue | 
        ForEach-Object { 
            $destPath = Join-Path -Path $ResultsDir -ChildPath "comparisons/visualizations/$($_.Name)"
            Move-FileIfDifferent -Source $_.FullName -Destination $destPath
        }
}

# 7. Organiser les résumés par corpus
Write-Host "`n=== Organisation des résumés par corpus ===" -ForegroundColor Green

$summariesDir = Join-Path -Path $ResultsDir -ChildPath "summaries"
if (Test-Path -Path $summariesDir) {
    # Déplacer les résumés des débats Lincoln-Douglas
    Get-ChildItem -Path $summariesDir -Filter "*Débats_Lincoln-Douglas*" -ErrorAction SilentlyContinue | 
        ForEach-Object { 
            $destPath = Join-Path -Path $ResultsDir -ChildPath "summaries/Débats_Lincoln-Douglas/$($_.Name)"
            Move-FileIfDifferent -Source $_.FullName -Destination $destPath
        }
    
    # Déplacer les résumés des discours d'Hitler
    Get-ChildItem -Path $summariesDir -Filter "*Discours_d'Hitler*" -ErrorAction SilentlyContinue | 
        ForEach-Object { 
            $destPath = Join-Path -Path $ResultsDir -ChildPath "summaries/Discours_Hitler/$($_.Name)"
            Move-FileIfDifferent -Source $_.FullName -Destination $destPath
        }
}

# 8. Supprimer les dossiers vides
Write-Host "`n=== Suppression des dossiers vides ===" -ForegroundColor Green

$emptyDirs = @(
    (Join-Path -Path $ResultsDir -ChildPath "comprehensive_report"),
    (Join-Path -Path $ResultsDir -ChildPath "performance_comparison"),
    (Join-Path -Path $ResultsDir -ChildPath "performance_tests")
)

foreach ($dir in $emptyDirs) {
    if (Test-Path -Path $dir) {
        if (Test-DirectoryEmpty -Path $dir) {
            Remove-EmptyDirectory -Path $dir
        }
        else {
            Write-Host "Le dossier $dir n'est pas vide, conservation." -ForegroundColor Yellow
        }
    }
}

# 9. Générer un README.md pour le dossier results
Write-Host "`n=== Génération du README.md pour le dossier results ===" -ForegroundColor Green

$readmePath = Join-Path -Path $ResultsDir -ChildPath "README.md"
Log-Action "Génération du fichier README.md: $readmePath"

$readmeContent = @"
# Résultats d'Analyse Rhétorique

Ce répertoire contient les résultats des analyses rhétoriques effectuées sur différents corpus de textes. Il est organisé de manière à faciliter l'accès aux différents types de résultats et leur interprétation.

## Structure du Répertoire

```
results/
├── analyses/
│   ├── basic/          # Analyses effectuées par l'agent de base
│   └── advanced/       # Analyses effectuées par l'agent avancé
├── summaries/
│   ├── Débats_Lincoln-Douglas/  # Résumés des débats Lincoln-Douglas
│   └── Discours_Hitler/         # Résumés des discours d'Hitler
├── comparisons/
│   ├── metrics/        # Métriques de comparaison (CSV)
│   └── visualizations/ # Visualisations des comparaisons
├── reports/
│   ├── comprehensive/  # Rapports d'analyse complets
│   └── performance/    # Rapports de performance
├── visualizations/     # Visualisations globales
└── README.md           # Ce fichier
```

## Description des Dossiers

### analyses/
Contient les résultats bruts des analyses rhétoriques au format JSON, séparés par type d'agent (basic ou advanced).

### summaries/
Contient les résumés des analyses par corpus et par agent. Chaque fichier présente une synthèse des sophismes détectés dans un texte spécifique.

### comparisons/
Contient les comparaisons de performance entre les différents agents d'analyse rhétorique, incluant des métriques quantitatives et des visualisations.

### reports/
Contient les rapports de synthèse globaux et les rapports de performance détaillés.

### visualizations/
Contient les visualisations graphiques des analyses, permettant une compréhension visuelle des résultats.

## Guide d'Interprétation des Résultats

### Analyses Rhétoriques
Les analyses rhétoriques sont stockées au format JSON et contiennent les informations suivantes :
- **Type de sophisme** : Classification selon la taxonomie standard
- **Extrait de texte** : Le passage contenant le sophisme
- **Niveau de confiance** : Estimation de la certitude de la détection
- **Explication** : Description de la nature du sophisme et de son impact sur l'argument

### Résumés
Les résumés sont organisés par corpus et par agent. Ils fournissent une synthèse des sophismes détectés et des structures argumentatives identifiées dans chaque texte analysé.

### Comparaisons
Les comparaisons permettent d'évaluer les performances des différents agents d'analyse rhétorique. Elles incluent des métriques quantitatives et des visualisations graphiques.

## Maintenance

Pour maintenir ce répertoire organisé :
1. Placez les nouvelles analyses dans le dossier approprié selon le type d'agent
2. Organisez les nouveaux résumés par corpus
3. Mettez à jour les rapports de synthèse lorsque de nouvelles analyses sont effectuées
4. Conservez une nomenclature cohérente incluant la date (format YYYYMMDD) dans les noms de fichiers
"@

if (-not $DryRun) {
    Set-Content -Path $readmePath -Value $readmeContent
}

# 10. Générer un rapport de nettoyage
Write-Host "`n=== Génération du rapport de nettoyage ===" -ForegroundColor Green

$reportContent = @"
# Rapport de Nettoyage Global du Projet
Date: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Actions effectuées

### 1. Suppression des fichiers temporaires
- Suppression des fichiers __pycache__ et .pyc
- Nettoyage des checkpoints Jupyter
- Suppression des fichiers temporaires d'éditeur

### 2. Réorganisation du dossier results/
- Création d'une structure de dossiers logique
- Organisation des analyses par type d'agent (basic/advanced)
- Classification des résumés par corpus
- Regroupement des rapports par type
- Centralisation des visualisations

### 3. Documentation
- Création d'un README.md pour le dossier results/
- Documentation de la structure et du contenu

## Statistiques
- Fichiers temporaires supprimés: $FilesDeleted
- Fichiers déplacés: $FilesMoved
- Dossiers créés: $DirsCreated
- Dossiers supprimés: $DirsDeleted

## Actions détaillées
$(($ActionsPerformed | ForEach-Object { "- $_" }) -join "`n")

## Recommandations
1. Utiliser la nouvelle structure pour tous les futurs résultats d'analyse
2. Maintenir une nomenclature cohérente incluant la date dans les noms de fichiers
3. Mettre à jour régulièrement le README.md lorsque de nouveaux types de résultats sont ajoutés
4. Exécuter périodiquement un nettoyage des fichiers temporaires
"@

if (-not $DryRun) {
    Set-Content -Path $ReportPath -Value $reportContent
    Write-Host "Rapport de nettoyage généré: $ReportPath" -ForegroundColor Green
}
else {
    Write-Host "Mode simulation: le rapport de nettoyage n'a pas été généré." -ForegroundColor Yellow
}

# Afficher le résumé
Write-Host "`n=== Résumé des actions ===" -ForegroundColor Cyan
Write-Host "Fichiers temporaires supprimés: $FilesDeleted" -ForegroundColor White
Write-Host "Fichiers déplacés: $FilesMoved" -ForegroundColor White
Write-Host "Dossiers créés: $DirsCreated" -ForegroundColor White
Write-Host "Dossiers supprimés: $DirsDeleted" -ForegroundColor White

Write-Host "`n=== Nettoyage global terminé ===" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host "`nPour exécuter réellement ces actions, relancez le script sans l'option -DryRun" -ForegroundColor Yellow
}
else {
    Write-Host "`nLe projet a été nettoyé et réorganisé avec succès." -ForegroundColor Green
    Write-Host "Un rapport détaillé a été généré: $ReportPath" -ForegroundColor Green
}