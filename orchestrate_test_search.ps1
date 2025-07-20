# Ce script orchestre une recherche dichotomique pour trouver le test qui plante.

param(
    [string]$InitialTestList = "tests/unit/all_tests.txt",
    [string]$TempTestListPrefix = "tests/unit/test_list"
)

function Invoke-PytestOnList {
    param(
        [string]$TestListFile
    )
    
    Write-Host "--- Exécution de pytest sur la liste: $TestListFile ---"
    # On ignore le test déjà connu pour planter pour ne pas fausser la recherche
    # On exécute maintenant les tests pour trouver les blocages à l'exécution.
    # -rP affiche un résumé des tests passés, ce qui est utile.
    $command = "pytest -q --ignore=tests/unit/argumentation_analysis/test_modal_logic_agent.py @`"$TestListFile`""
    
    Write-Host "Commande: $command"

    $job = Start-Job -ScriptBlock {
        param($cmd)
        $process = Start-Process pwsh -ArgumentList "-NoProfile -Command `"$cmd`"" -Wait -PassThru -NoNewWindow
        return $process.ExitCode
    } -ArgumentList $command

    $job | Wait-Job -Timeout 60 # Timeout de 60 secondes

    if ($job.State -eq 'Running') {
        Write-Warning "Le job a dépassé le timeout de 60 secondes. Il est considéré comme bloqué."
        Stop-Job $job
        Remove-Job $job
        return 1 # Code d'erreur pour indiquer un blocage
    }

    $exitCode = Receive-Job $job
    Remove-Job $job
    
    Write-Host "--- Pytest terminé avec le code de sortie: $exitCode ---"
    return $exitCode
}

# Charger et nettoyer la liste initiale
$allTests = Get-Content -Path $InitialTestList | Where-Object { $_ -notlike "*==*" -and $_ -notlike "*warnings summary*" -and $_.Trim() -ne "" }
if ($allTests.Length -gt 0 -and $allTests[0] -like "*[INFO]*") {
    $allTests = $allTests | Select-Object -Skip 1
}

$testsToSearch = $allTests
$iteration = 1

while ($testsToSearch.Count -gt 1) {
    $half = [math]::Ceiling($testsToSearch.Count / 2)
    $firstHalf = $testsToSearch[0..($half - 1)]
    
    $currentTestListFile = "$TempTestListPrefix`_$($testsToSearch.Count).txt"
    $firstHalf | Set-Content -Path $currentTestListFile

    Write-Host "========================================================================"
    Write-Host "Itération ${iteration}: Recherche dans un bloc de $($testsToSearch.Count) tests."
    Write-Host "Test de la première moitié ($half tests) dans $currentTestListFile"
    Write-Host "========================================================================"

    $exitCode = Invoke-PytestOnList -TestListFile $currentTestListFile
    
    if ($exitCode -ne 0) {
        # Le crash est dans la première moitié
        Write-Host "-> Problème détecté dans la première moitié. Réduction de la recherche."
        $testsToSearch = $firstHalf
    } else {
        # Le crash est dans la seconde moitié
        Write-Host "-> Première moitié OK. Le problème est dans la seconde moitié."
        $secondHalf = $testsToSearch[$half..($testsToSearch.Count - 1)]
        $testsToSearch = $secondHalf
    }
    $iteration++
}

Write-Host "========================================================================"
Write-Host "Recherche terminée."
if ($testsToSearch.Count -eq 1) {
    $culprit = $testsToSearch[0]
    Write-Host "Test potentiellement coupable: $culprit"
    Set-Content -Path "$TempTestListPrefix`_culprit.txt" -Value $culprit
} else {
    Write-Warning "La recherche n'a pas pu isoler un seul test. Les candidats restants sont :"
    $testsToSearch | Out-Host
    Set-Content -Path "$TempTestListPrefix`_culprits.txt" -Value $testsToSearch
}
Write-Host "========================================================================"