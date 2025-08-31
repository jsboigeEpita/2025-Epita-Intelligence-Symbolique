# Ce script lance la suite de tests E2E en s'assurant que la session JVM globale
# de pytest est désactivée, ce qui est crucial pour éviter les conflits
# lorsque les serveurs E2E démarrent leur propre instance de JVM.

param(
    [string]$PytestArgs
)

Write-Host "Lancement des tests E2E avec la session JVM désactivée..."
$command = "python -m pytest tests/e2e/python/ --disable-jvm-session $PytestArgs"
Write-Host "Commande exécutée: $command"

Invoke-Expression $command