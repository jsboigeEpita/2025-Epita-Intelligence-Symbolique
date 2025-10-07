# Analyser les cibles Phase C
# 1. Lister api/*_simple.py avec taille et contenu
# 2. Analyser hello_world_plugin/ structure
# 3. Vérifier existence dossiers fantômes (logs/, reports/, results/, dummy_opentelemetry/, argumentation_analysis.egg-info/)
# 4. Analyser .gitignore actuel (~50 entrées restantes)

$outputFile = ".temp/cleanup_campaign_2025-10-03/02_phases/phase_C/analyse_cibles.md"
Clear-Content $outputFile

Add-Content $outputFile "# Analyse des Cibles Phase C`n`n"

Add-Content $outputFile "## 1. Fichiers api/*_simple.py`n"
Get-ChildItem -Path "api/*_simple.py" | ForEach-Object {
    $filePath = $_.FullName
    $fileName = $_.Name
    $fileSize = (Get-Item $filePath).Length / 1KB | Tee-Object -Variable sizeKB
    Add-Content $outputFile "### Fichier : $fileName (`$($sizeKB | Format-Number -DecimalDigits 2) KB)`n"
    Add-Content $outputFile "```python`n"
    Add-Content $outputFile (Get-Content $filePath | Out-String)
    Add-Content $outputFile "`n````n`n"
}

Add-Content $outputFile "## 2. Analyse hello_world_plugin/ structure`n"
$helloWorldPluginPath = Get-ChildItem -Path "plugins/hello_world_plugin" -Directory -ErrorAction SilentlyContinue
if ($helloWorldPluginPath) {
    Add-Content $outputFile "Le répertoire 'hello_world_plugin/' existe à : $($helloWorldPluginPath.FullName)`n"
    Add-Content $outputFile "Contenu :`n"
    Add-Content $outputFile "````n"
    Get-ChildItem -Path $helloWorldPluginPath.FullName -Recurse | Select-Object FullName, Length | Format-Table -AutoSize | Out-String | Add-Content $outputFile
    Add-Content $outputFile "`n````n`n"
} else {
    Add-Content $outputFile "Le répertoire 'hello_world_plugin/' n'a pas été trouvé.`n`n"
}

Add-Content $outputFile "## 3. Vérification des dossiers fantômes`n"
$ghostDirs = @("logs/", "reports/", "results/", "dummy_opentelemetry/", "argumentation_analysis.egg-info/")
foreach ($dir in $ghostDirs) {
    $fullPath = Join-Path (Get-Location) $dir
    if (Test-Path $fullPath -PathType Container) {
        $isGitTracked = git ls-files --error-unmatch $fullPath 2>$null
        if ($LASTEXITCODE -eq 0) {
            Add-Content $outputFile "- Dossier '$dir' existe et est TRACKÉ par Git. (Validation utilisateur requise pour suppression)`n"
        } else {
            Add-Content $outputFile "- Dossier '$dir' existe et n'est PAS TRACKÉ par Git. (Peut être supprimé)`n"
        }
    } else {
        Add-Content $outputFile "- Dossier '$dir' n'existe pas.`n"
    }
}
Add-Content $outputFile "`n"

Add-Content $outputFile "## 4. Analyse .gitignore actuel`n"
if (Test-Path ".gitignore") {
    Add-Content $outputFile "````n"
    Add-Content $outputFile (Get-Content ".gitignore" | Out-String)
    Add-Content $outputFile "`n````n`n"
} else {
    Add-Content $outputFile "Le fichier .gitignore n'existe pas.`n`n"
}

Add-Content $outputFile "Analyse terminée. Le rapport est disponible dans '$outputFile'`n"