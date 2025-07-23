# Exécution de tous les tests en mode séquentiel pour éviter les conflits avec la JVM.
# Exécution de tous les tests en mode séquentiel pour éviter les conflits.
Write-Host "--- Running all tests sequentially ---"
pytest
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests failed."
    exit $LASTEXITCODE
}

Write-Host "All tests passed successfully!"
exit 0
