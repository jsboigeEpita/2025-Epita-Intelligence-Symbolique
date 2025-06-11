# Fonction pour calculer le chemin relatif manuellement
function Get-RelativePath {
    param(
        [string]$targetPath,
        [string]$basePath
    )

    try {
        $targetUri = [System.Uri]$targetPath
        $baseUri = [System.Uri]$basePath
        $relativeUri = $baseUri.MakeRelativeUri($targetUri)
        return [System.Uri]::UnescapeDataString($relativeUri.ToString())
    }
    catch {
        Write-Error "Impossible de calculer le chemin relatif de '$targetPath' à '$basePath'. Erreur: $($_.Exception.Message)"
        return $null
    }
}

# Définir le chemin de base du projet
$basePath = (Get-Location).Path
$testsPath = Join-Path $basePath "tests"

# Chemin vers le rapport CSV
$reportPath = Join-Path $basePath "scripts/corrections_report.csv"

# Chemin pour le nouveau rapport des erreurs non résolues
$unresolvedReportPath = Join-Path $basePath "scripts/unresolved_references_report.csv"

# Charger le rapport
try {
    $report = Import-Csv -Path $reportPath
}
catch {
    Write-Error "Impossible de lire le fichier CSV sur le chemin : $reportPath. Erreur: $_"
    exit 1
}

# Initialiser des listes pour les rapports
$unresolvedRefs = @()
$correctedRefs = @()

# Récupérer tous les fichiers markdown une seule fois
$markdownFiles = Get-ChildItem -Path $basePath -Recurse -Filter "*.md"

# Parcourir chaque ligne du rapport
foreach ($row in $report) {
    $obsoleteRef = $row.ObsoleteRef
    
    if ([string]::IsNullOrWhiteSpace($obsoleteRef)) {
        continue
    }

    # Fichiers Markdown contenant la référence obsolète
    $containingFiles = @($markdownFiles | Where-Object { (Get-Content $_.FullName -Raw) -match [regex]::Escape($obsoleteRef) })

    if ($containingFiles.Count -eq 0) {
        $unresolvedRefs += [PSCustomObject]@{
            ObsoleteRef = $obsoleteRef
            Reason      = "Aucun fichier markdown ne contient cette référence."
            Details     = ""
        }
        continue
    }

    # Extraire le nom du fichier de la référence obsolète
    $fileNameToFind = [System.IO.Path]::GetFileName($obsoleteRef)
    
    # Rechercher le fichier dans le répertoire /tests
    $foundFiles = @(Get-ChildItem -Path $testsPath -Recurse -Filter $fileNameToFind)
    
    if ($foundFiles.Count -ne 1) {
        foreach ($mdFile in $containingFiles) {
            $unresolvedRefs += [PSCustomObject]@{
                ObsoleteRef = $obsoleteRef
                Reason      = if ($foundFiles.Count -gt 1) { "Plusieurs fichiers de test trouvés" } else { "Fichier de test non trouvé" }
                Details     = "Dans le fichier markdown : $($mdFile.FullName)"
            }
        }
        continue
    }

    # Un seul fichier trouvé, on peut procéder à la correction
    $newTestPath = $foundFiles[0].FullName

    foreach ($mdFile in $containingFiles) {
        try {
            $markdownDir = Split-Path -Path $mdFile.FullName -Parent
            
            if (-not $markdownDir) {
                throw "Impossible d'obtenir le répertoire du fichier markdown: $($mdFile.FullName)"
            }

            # Calculer le chemin relatif
            $relativeNewPath = Get-RelativePath -targetPath $newTestPath -basePath $markdownDir
            
            if ($null -eq $relativeNewPath) {
                throw "Le calcul du chemin relatif a retourné null."
            }
            
            $relativeNewPath = $relativeNewPath.Replace("\", "/")

            # Lire le contenu du fichier markdown
            $markdownContent = Get-Content -Path $mdFile.FullName -Raw -Encoding UTF8
            
            # Remplacer l'ancienne référence par la nouvelle
            $newMarkdownContent = $markdownContent.Replace($obsoleteRef, $relativeNewPath)
            
            # Écrire les modifications dans le fichier markdown
            Set-Content -Path $mdFile.FullName -Value $newMarkdownContent -Encoding UTF8
            
            $correctedRefs += [PSCustomObject]@{
                MarkdownFile = $mdFile.FullName
                ObsoleteRef  = $obsoleteRef
                NewRef       = $relativeNewPath
            }
            Write-Host "Correction effectuée dans '$($mdFile.Name)': '$obsoleteRef' -> '$relativeNewPath'"
        }
        catch {
            $unresolvedRefs += [PSCustomObject]@{
                ObsoleteRef = $obsoleteRef
                Reason      = "Erreur lors du traitement du fichier markdown."
                Details     = "Fichier: $($mdFile.FullName) | Erreur: $($_.Exception.Message)"
            }
        }
    }
}

# Générer le rapport des références non résolues
if ($unresolvedRefs.Count -gt 0) {
    $unresolvedRefs | Export-Csv -Path $unresolvedReportPath -NoTypeInformation -Encoding UTF8
    Write-Host "Rapport des références non résolues généré : $unresolvedReportPath"
}

# Générer un rapport des corrections effectuées
if ($correctedRefs.Count -gt 0) {
    $correctedReportPath = Join-Path $basePath "scripts/applied_corrections_report.csv"
    $correctedRefs | Export-Csv -Path $correctedReportPath -NoTypeInformation -Encoding UTF8
    Write-Host "Rapport des corrections appliquées généré : $correctedReportPath"
}

if ($unresolvedRefs.Count -eq 0 -and $correctedRefs.Count -eq 0) {
    Write-Host "Aucune référence à corriger ou à signaler."
}