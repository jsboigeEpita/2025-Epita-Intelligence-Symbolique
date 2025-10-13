$sourceFile = "tests/unit/all_tests.txt"
$destinationFile = "tests/unit/targeted_test_list.txt"
$startIndex = 749 # Index de base 0 pour la 750ème ligne
$endIndex = 789   # Index de base 0 pour la 790ème ligne

# Charger et nettoyer la liste initiale
$allTests = Get-Content -Path $sourceFile | Where-Object { $_ -notlike "*==*" -and $_ -notlike "*warnings summary*" -and $_.Trim() -ne "" }
if ($allTests.Length -gt 0 -and $allTests[0] -like "*[INFO]*") {
    $allTests = $allTests | Select-Object -Skip 1
}

$targetedTests = $allTests[$startIndex..$endIndex]

Set-Content -Path $destinationFile -Value $targetedTests

Write-Host "Liste de tests ciblée créée à l'emplacement : $destinationFile avec $($targetedTests.Count) tests."