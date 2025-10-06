# Script PowerShell pour analyser les fichiers à la racine du projet et générer un inventaire Markdown.

# Définir le répertoire racine du projet
$rootDir = "d:/2025-Epita-Intelligence-Symbolique"

# Définir le chemin de sortie pour le rapport Markdown
$outputDir = "$rootDir/.temp/cleanup_campaign_2025-10-03/02_phases/phase_B"
$outputPath = "$outputDir/inventaire_racine.md"

# Créer le répertoire de sortie si inexistant
if (-not (Test-Path $outputDir)) {
    New-Item -Path $outputDir -ItemType Directory -Force | Out-Null
}

# Fonction pour catégoriser un fichier
function Get-FileCategory {
    param (
        [string]$filePath
    )

    $fileName = Split-Path $filePath -Leaf
    $extension = [System.IO.Path]::GetExtension($fileName).ToLower()

    # Catégories
    $scriptExtensions = @(".ps1", ".py", ".sh", ".bat")
    $docExtensions = @(".md", ".txt", ".pdf")
    $configExtensions = @(".json", ".yaml", ".yml", ".ini", ".toml")
    $buildLogExtensions = @(".log", ".diff", ".patch")
    $imageExtensions = @(".png", ".jpg", ".jpeg")

    # Fichiers à conserver à la racine (essentiels)
    $essentialRootFiles = @(
        "README.md", "LICENSE", ".gitignore", "pyproject.toml",
        "requirements.txt", "pytest.ini", "activate_project_env.ps1",
        "activate_project_env.sh", "conda-lock.yml"
    )

    # Obsolètes/Temporaires
    $obsoleteTempPatterns = @(
        "_temp_readme_restoration", "empty_pytest.ini", "patch.diff"
    )

    # Vérifier les fichiers essentiels
    if ($essentialRootFiles -contains $fileName) {
        return "Fichiers à conserver à la racine (essentiels)"
    }

    # Vérifier les obsolètes/temporaires
    if ($obsoleteTempPatterns -contains $fileName -or ($extension -eq ".log" -and $fileName -notlike "*.gitignore")) { # Simplifié pour l'exemple, un vrai check Git serait plus complexe
        return "Obsolètes/Temporaires"
    }

    # Vérifier les scripts
    if ($scriptExtensions -contains $extension) {
        return "Scripts"
    }

    # Vérifier la documentation
    if ($docExtensions -contains $extension) {
        return "Documentation"
    }

    # Vérifier la configuration
    if ($configExtensions -contains $extension) {
        return "Configuration"
    }

    # Vérifier les builds/logs
    if ($buildLogExtensions -contains $extension) {
        return "Builds/Logs"
    }

    # Vérifier les images
    if ($imageExtensions -contains $extension) {
        return "Screenshots/Images"
    }

    return "Autres"
}

# Fonction pour proposer une destination
function Suggest-Destination {
    param (
        [string]$category,
        [string]$fileName
    )

    switch ($category) {
        "Scripts" {
            if ($fileName -like "run_*.ps1" -or $fileName -like "setup_*.ps1") {
                return "scripts/utils/"
            }
            return "scripts/maintenance/"
        }
        "Documentation" {
            return "docs/maintenance/"
        }
        "Configuration" {
            return "config/"
        }
        "Builds/Logs" {
            return ".temp/logs/"
        }
        "Screenshots/Images" {
            return ".temp/screenshots/"
        }
        "Obsolètes/Temporaires" {
            return "à supprimer"
        }
        "Fichiers à conserver à la racine (essentiels)" {
            return "à conserver à la racine"
        }
        "Autres" {
            return "à examiner"
        }
        default {
            return "destination inconnue"
        }
    }
}

# Lister les fichiers à la racine
$rootFiles = Get-ChildItem -Path $rootDir -File -Depth 0

# Initialiser le contenu Markdown
$markdownContent = @()
$markdownContent += "# Inventaire des Fichiers Racine"
$markdownContent += ""
$markdownContent += "Date de l'inventaire : $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")"
$markdownContent += ""
$markdownContent += "Nombre total de fichiers racine : $($rootFiles.Count)"
$markdownContent += ""
$markdownContent += "## Détails des Fichiers"
$markdownContent += ""
$markdownContent += "| Nom du Fichier | Catégorie | Proposition de Destination |"
$markdownContent += "|---|---|---|"

# Traiter chaque fichier
foreach ($file in $rootFiles) {
    $category = Get-FileCategory -filePath $file.FullName
    $destination = Suggest-Destination -category $category -fileName $file.Name
    $markdownContent += "| $($file.Name) | $($category) | $($destination) |"
}

# Écrire le contenu dans le fichier Markdown
$markdownContent | Out-File -FilePath $outputPath -Encoding UTF8

Write-Host "Inventaire généré avec succès : $outputPath"