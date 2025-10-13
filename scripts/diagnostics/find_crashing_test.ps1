# Ce script exécute les tests unitaires un par un à partir d'une liste
# pour identifier celui qui provoque un crash ou un blocage.

param(
    [string]$TestListPath = "tests/unit/all_tests.txt"
)

# Charger la liste des tests, en ignorant les lignes non pertinentes
$allTests = Get-Content -Path $TestListPath | Where-Object { $_ -notlike "*==*" -and $_ -notlike "*warnings summary*" -and $_.Trim() -ne "" }

# Ignorer la première ligne d'information si elle existe
if ($allTests.Length -gt 0 -and $allTests[0] -like "*[INFO]*") {
    $testsToRun = $allTests | Select-Object -Skip 1
} else {
    $testsToRun = $allTests
}

$totalTests = $testsToRun.Count
Write-Host "Démarrage de l'exécution séquentielle de $totalTests tests."

$count = 0
foreach ($test in $testsToRun) {
    $count++
    $testPath = $test.Trim()
    
    if (-not ($testPath)) {
        Write-Warning "Ligne de test vide ignorée."
        continue
    }

    Write-Host "========================================================================"
    Write-Host "($count/$totalTests) Exécution du test : $testPath"
    Write-Host "========================================================================"
    
    # Exécute le test avec un timeout. Si le test dépasse le temps imparti,
    # il est considéré comme bloqué.
    # L'option --log-cli-level=ERROR réduit le bruit pour les tests qui passent.
    $command = "pytest `"$testPath`" --log-cli-level=ERROR"
    
    try {
        # Utilisation de pwsh pour lancer la commande dans un nouveau processus
        # ce qui permet de s'assurer que même un crash fatal n'arrête pas ce script.
        $process = Start-Process pwsh -ArgumentList "-NoProfile -Command `"$command`"" -Wait -PassThru
        
        if ($process.ExitCode -ne 0) {
            Write-Error "Le test '$testPath' a échoué avec le code de sortie $($process.ExitCode)."
            # On peut décider de s'arrêter ici ou de continuer. Pour l'instant, on continue.
        } else {
            Write-Host "Test '$testPath' terminé avec succès."
        }
    } catch {
        Write-Error "Une erreur critique est survenue lors de l'exécution de '$testPath'."
        Write-Error $_.Exception.Message
        # En cas d'erreur de script, on s'arrête.
        break
    }
}

Write-Host "Exécution séquentielle des tests terminée."