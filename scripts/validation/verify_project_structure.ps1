# Script PowerShell pour vérifier la structure du projet d'analyse d'argumentation
# Auteur: Roo
# Date: 30/04/2025

# Définition des couleurs pour une meilleure lisibilité
$colorSuccess = "Green"
$colorWarning = "Yellow"
$colorError = "Red"
$colorInfo = "Cyan"

# Chemin du projet
$projectPath = ".\argumentiation_analysis"

# Fonction pour afficher un message formaté
function Write-FormattedMessage {
    param (
        [string]$Message,
        [string]$Type = "INFO"
    )
    
    $color = switch ($Type) {
        "SUCCESS" { $colorSuccess }
        "WARNING" { $colorWarning }
        "ERROR" { $colorError }
        "INFO" { $colorInfo }
        default { "White" }
    }
    
    Write-Host "$(Get-Date -Format 'HH:mm:ss') [$Type] $Message" -ForegroundColor $color
}

# Fonction pour créer un rapport HTML
function Create-HtmlReport {
    param (
        [string]$ReportPath,
        [array]$Issues
    )
    
    $htmlHeader = @"
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport de vérification de structure</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .success { color: green; }
        .warning { color: orange; }
        .error { color: red; }
        .info { color: blue; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        tr:nth-child(even) { background-color: #f9f9f9; }
    </style>
</head>
<body>
    <h1>Rapport de vérification de structure du projet</h1>
    <p>Date: $(Get-Date -Format 'dd/MM/yyyy HH:mm:ss')</p>
    
    <h2>Résumé des problèmes identifiés</h2>
    <table>
        <tr>
            <th>Type</th>
            <th>Description</th>
            <th>Chemin</th>
        </tr>
"@

    $htmlRows = ""
    foreach ($issue in $Issues) {
        $cssClass = switch ($issue.Type) {
            "SUCCESS" { "success" }
            "WARNING" { "warning" }
            "ERROR" { "error" }
            "INFO" { "info" }
            default { "" }
        }
        
        $htmlRows += @"
        <tr class="$cssClass">
            <td>$($issue.Type)</td>
            <td>$($issue.Description)</td>
            <td>$($issue.Path)</td>
        </tr>
"@
    }

    $htmlFooter = @"
    </table>
    
    <h2>Recommandations</h2>
    <ul>
        <li>Assurez-vous que tous les packages Python contiennent un fichier __init__.py</li>
        <li>Ajoutez un fichier README.md dans chaque dossier pour documenter son contenu</li>
        <li>Supprimez les fichiers temporaires (.pyc, __pycache__, etc.)</li>
        <li>Éliminez les duplications de code et les fichiers redondants</li>
        <li>Corrigez les imports non utilisés ou manquants dans les fichiers Python</li>
    </ul>
</body>
</html>
"@

    $htmlContent = $htmlHeader + $htmlRows + $htmlFooter
    $htmlContent | Out-File -FilePath $ReportPath -Encoding UTF8
    Write-FormattedMessage "Rapport HTML généré: $ReportPath" "SUCCESS"
}

# Initialisation du rapport
$issues = @()

Write-FormattedMessage "Début de la vérification de la structure du projet..." "INFO"

# 1. Vérifier la cohérence de l'arborescence (fichiers __init__.py présents dans tous les packages)
Write-FormattedMessage "1. Vérification des fichiers __init__.py dans tous les packages..." "INFO"

$pythonDirs = Get-ChildItem -Path $projectPath -Directory -Recurse | 
    Where-Object { 
        (Get-ChildItem -Path $_.FullName -Filter "*.py" -File | Measure-Object).Count -gt 0 -and 
        $_.FullName -notlike "*\__pycache__*" -and 
        $_.FullName -notlike "*\.venv*" -and
        $_.FullName -notlike "*\venv*"
    }

$missingInitCount = 0
foreach ($dir in $pythonDirs) {
    $initPath = Join-Path -Path $dir.FullName -ChildPath "__init__.py"
    if (-not (Test-Path -Path $initPath)) {
        $missingInitCount++
        $relativePath = $dir.FullName.Replace((Get-Location).Path + "\", "")
        Write-FormattedMessage "Package sans fichier __init__.py: $relativePath" "ERROR"
        $issues += @{
            Type = "ERROR"
            Description = "Package sans fichier __init__.py"
            Path = $relativePath
        }
    }
}

if ($missingInitCount -eq 0) {
    Write-FormattedMessage "Tous les packages contiennent un fichier __init__.py" "SUCCESS"
    $issues += @{
        Type = "SUCCESS"
        Description = "Tous les packages contiennent un fichier __init__.py"
        Path = $projectPath
    }
} else {
    Write-FormattedMessage "$missingInitCount packages sans fichier __init__.py" "ERROR"
}

# 2. Vérifier les fichiers README.md dans chaque dossier
Write-FormattedMessage "2. Vérification des fichiers README.md dans chaque dossier..." "INFO"

$allDirs = Get-ChildItem -Path $projectPath -Directory -Recurse | 
    Where-Object { 
        $_.FullName -notlike "*\__pycache__*" -and 
        $_.FullName -notlike "*\.venv*" -and
        $_.FullName -notlike "*\venv*"
    }

$missingReadmeCount = 0
foreach ($dir in $allDirs) {
    $readmePath = Join-Path -Path $dir.FullName -ChildPath "README.md"
    if (-not (Test-Path -Path $readmePath)) {
        $missingReadmeCount++
        $relativePath = $dir.FullName.Replace((Get-Location).Path + "\", "")
        Write-FormattedMessage "Dossier sans fichier README.md: $relativePath" "WARNING"
        $issues += @{
            Type = "WARNING"
            Description = "Dossier sans fichier README.md"
            Path = $relativePath
        }
    }
}

if ($missingReadmeCount -eq 0) {
    Write-FormattedMessage "Tous les dossiers contiennent un fichier README.md" "SUCCESS"
    $issues += @{
        Type = "SUCCESS"
        Description = "Tous les dossiers contiennent un fichier README.md"
        Path = $projectPath
    }
} else {
    Write-FormattedMessage "$missingReadmeCount dossiers sans fichier README.md" "WARNING"
}

# 3. Rechercher les éventuelles duplications de code ou fichiers redondants
Write-FormattedMessage "3. Recherche des duplications de code ou fichiers redondants..." "INFO"

$pythonFiles = Get-ChildItem -Path $projectPath -Filter "*.py" -File -Recurse | 
    Where-Object { 
        $_.FullName -notlike "*\__pycache__*" -and 
        $_.FullName -notlike "*\.venv*" -and
        $_.FullName -notlike "*\venv*"
    }

$fileHashes = @{}
$duplicateFiles = @()

foreach ($file in $pythonFiles) {
    $fileContent = Get-Content -Path $file.FullName -Raw
    $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash([System.Text.Encoding]::UTF8.GetBytes($fileContent))
    $hashString = [System.BitConverter]::ToString($hash)
    
    if ($fileHashes.ContainsKey($hashString)) {
        $duplicateFiles += @{
            Original = $fileHashes[$hashString]
            Duplicate = $file.FullName
        }
    } else {
        $fileHashes[$hashString] = $file.FullName
    }
}

if ($duplicateFiles.Count -eq 0) {
    Write-FormattedMessage "Aucun fichier dupliqué détecté" "SUCCESS"
    $issues += @{
        Type = "SUCCESS"
        Description = "Aucun fichier dupliqué détecté"
        Path = $projectPath
    }
} else {
    Write-FormattedMessage "$($duplicateFiles.Count) fichiers dupliqués détectés" "WARNING"
    
    foreach ($duplicate in $duplicateFiles) {
        $originalRelative = $duplicate.Original.Replace((Get-Location).Path + "\", "")
        $duplicateRelative = $duplicate.Duplicate.Replace((Get-Location).Path + "\", "")
        Write-FormattedMessage "Fichier dupliqué: $duplicateRelative (identique à $originalRelative)" "WARNING"
        $issues += @{
            Type = "WARNING"
            Description = "Fichier dupliqué (identique à $originalRelative)"
            Path = $duplicateRelative
        }
    }
}

# 4. Identifier les fichiers temporaires (.pyc, __pycache__, etc.)
Write-FormattedMessage "4. Identification des fichiers temporaires..." "INFO"

$tempFiles = Get-ChildItem -Path $projectPath -Recurse | 
    Where-Object { 
        $_.Name -like "*.pyc" -or 
        $_.Name -like "*.pyo" -or 
        $_.Name -eq "__pycache__" -or
        $_.Name -like "*.tmp" -or
        $_.Name -like "*.bak" -or
        $_.Name -like "*.swp" -or
        $_.Name -like ".DS_Store"
    }

if ($tempFiles.Count -eq 0) {
    Write-FormattedMessage "Aucun fichier temporaire détecté" "SUCCESS"
    $issues += @{
        Type = "SUCCESS"
        Description = "Aucun fichier temporaire détecté"
        Path = $projectPath
    }
} else {
    Write-FormattedMessage "$($tempFiles.Count) fichiers temporaires détectés" "WARNING"
    
    foreach ($tempFile in $tempFiles) {
        $relativePath = $tempFile.FullName.Replace((Get-Location).Path + "\", "")
        Write-FormattedMessage "Fichier temporaire: $relativePath" "WARNING"
        $issues += @{
            Type = "WARNING"
            Description = "Fichier temporaire"
            Path = $relativePath
        }
    }
}

# 5. Vérifier les imports non utilisés ou manquants dans les fichiers Python
Write-FormattedMessage "5. Vérification des imports dans les fichiers Python..." "INFO"
Write-FormattedMessage "Installation de pylint si nécessaire..." "INFO"

# Vérifier si pylint est installé
$pylintInstalled = $false
try {
    $pylintVersion = python -c "import pylint; print(pylint.__version__)" 2>$null
    if ($pylintVersion) {
        $pylintInstalled = $true
        Write-FormattedMessage "pylint version $pylintVersion est déjà installé" "SUCCESS"
    }
} catch {
    Write-FormattedMessage "pylint n'est pas installé, tentative d'installation..." "INFO"
}

if (-not $pylintInstalled) {
    try {
        python -m pip install pylint
        Write-FormattedMessage "pylint installé avec succès" "SUCCESS"
        $pylintInstalled = $true
    } catch {
        Write-FormattedMessage "Échec de l'installation de pylint: $_" "ERROR"
    }
}

if ($pylintInstalled) {
    $unusedImports = @()
    $missingImports = @()
    
    foreach ($file in $pythonFiles) {
        $relativePath = $file.FullName.Replace((Get-Location).Path + "\", "")
        Write-FormattedMessage "Analyse de $relativePath..." "INFO"
        
        $pylintOutput = python -m pylint $file.FullName --disable=all --enable=unused-import,import-error --output-format=json 2>$null
        
        if ($pylintOutput) {
            $pylintResults = $pylintOutput | ConvertFrom-Json
            
            foreach ($result in $pylintResults) {
                if ($result.message -like "*Unused import*") {
                    $unusedImports += @{
                        File = $relativePath
                        Line = $result.line
                        Message = $result.message
                    }
                    Write-FormattedMessage "Import non utilisé dans $relativePath (ligne $($result.line)): $($result.message)" "WARNING"
                    $issues += @{
                        Type = "WARNING"
                        Description = "Import non utilisé: $($result.message)"
                        Path = "$relativePath (ligne $($result.line))"
                    }
                }
                elseif ($result.message -like "*No module named*" -or $result.message -like "*Unable to import*") {
                    $missingImports += @{
                        File = $relativePath
                        Line = $result.line
                        Message = $result.message
                    }
                    Write-FormattedMessage "Import manquant dans $relativePath (ligne $($result.line)): $($result.message)" "ERROR"
                    $issues += @{
                        Type = "ERROR"
                        Description = "Import manquant: $($result.message)"
                        Path = "$relativePath (ligne $($result.line))"
                    }
                }
            }
        }
    }
    
    if ($unusedImports.Count -eq 0 -and $missingImports.Count -eq 0) {
        Write-FormattedMessage "Aucun problème d'import détecté" "SUCCESS"
        $issues += @{
            Type = "SUCCESS"
            Description = "Aucun problème d'import détecté"
            Path = $projectPath
        }
    } else {
        if ($unusedImports.Count -gt 0) {
            Write-FormattedMessage "$($unusedImports.Count) imports non utilisés détectés" "WARNING"
        }
        if ($missingImports.Count -gt 0) {
            Write-FormattedMessage "$($missingImports.Count) imports manquants détectés" "ERROR"
        }
    }
} else {
    Write-FormattedMessage "Impossible de vérifier les imports sans pylint" "ERROR"
    $issues += @{
        Type = "ERROR"
        Description = "Impossible de vérifier les imports (pylint non disponible)"
        Path = $projectPath
    }
}

# Génération du rapport HTML
$reportPath = "rapport_verification_structure.html"
Create-HtmlReport -ReportPath $reportPath -Issues $issues

Write-FormattedMessage "Vérification de la structure du projet terminée" "SUCCESS"
Write-FormattedMessage "Consultez le rapport détaillé: $reportPath" "INFO"