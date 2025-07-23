<#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Exécute une liste de tests pytest de manière isolée pour éviter les crashs en cascade.
.DESCRIPTION
    Ce script lit une liste de tests (un par ligne) à partir d'un fichier et
    exécute chaque test dans un processus `pytest` distinct.
    Il est conçu pour contourner les problèmes où un test fait planter toute la suite,
    notamment avec des intégrations instables comme JPype.
    La sortie de chaque test est enregistrée dans un fichier de log.
.NOTES
    Auteur: Roo
    Date: 23/07/2025
#>

$ErrorActionPreference = 'Continue'

# --- Configuration ---
$TestListFile = "tests_jvm.txt"
$LogFile = "test_results.log"
$ActivationScript = ".\activate_project_env.ps1"

# --- Validation ---
if (-not (Test-Path $TestListFile)) {
    Write-Host "[ERREUR] Le fichier de liste de tests '$TestListFile' est introuvable." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ActivationScript)) {
    Write-Host "[ERREUR] Le script d'activation '$ActivationScript' est introuvable." -ForegroundColor Red
    exit 1
}

# --- Initialisation ---
if (Test-Path $LogFile) {
    Remove-Item $LogFile
}
"--- Début de l'exécution des tests isolés le $(Get-Date) ---`n" | Out-File -FilePath $LogFile -Encoding utf8 -Append

$testsToRun = Get-Content $TestListFile

# --- Boucle d'exécution ---
foreach ($test in $testsToRun) {
    if ([string]::IsNullOrWhiteSpace($test)) {
        continue
    }

    $testIdentifier = $test.Trim()
    
    Write-Host "`n--- Exécution du test: $testIdentifier ---" -ForegroundColor Cyan
    "======================================================================`n" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    "EXECUTING TEST: $testIdentifier`n" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    "======================================================================`n" | Out-File -FilePath $LogFile -Encoding utf8 -Append

    $commandToRun = "pytest -v -rA $testIdentifier"
    
    try {
        # Exécute la commande et redirige toute la sortie (stdout et stderr) vers le fichier de log
        # Le `*>&1` est la syntaxe PowerShell pour fusionner tous les flux de sortie vers le flux de succès (1)
        # qui est ensuite redirigé par `Out-File`.
        & $ActivationScript -CommandToRun $commandToRun *>&1 | Out-File -FilePath $LogFile -Encoding utf8 -Append -NoNewline
        
        $exitCode = $LASTEXITCODE
        if ($exitCode -eq 0) {
            Write-Host "[SUCCÈS] Le test s'est terminé avec le code 0." -ForegroundColor Green
            "`n---> RÉSULTAT: SUCCÈS (Code: $exitCode)`n" | Out-File -FilePath $LogFile -Encoding utf8 -Append
        } else {
            Write-Host "[ÉCHEC] Le test s'est terminé avec le code $exitCode." -ForegroundColor Yellow
            "`n---> RÉSULTAT: ÉCHEC (Code: $exitCode)`n" | Out-File -FilePath $LogFile -Encoding utf8 -Append
        }
    }
    catch {
        Write-Host "[CRASH] Une erreur critique est survenue lors de l'exécution du test." -ForegroundColor Red
        $_.Exception | Out-File -FilePath $LogFile -Encoding utf8 -Append
        "`n---> RÉSULTAT: CRASH (Erreur du script)`n" | Out-File -FilePath $LogFile -Encoding utf8 -Append
    }
    
    "`n" | Out-File -FilePath $LogFile -Encoding utf8 -Append
}

Write-Host "`n--- Exécution des tests terminée. Résultats dans '$LogFile'. ---" -ForegroundColor Green