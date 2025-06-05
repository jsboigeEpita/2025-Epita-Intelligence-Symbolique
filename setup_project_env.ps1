param (
    [string]$CommandToRun = "" # Commande à exécuter après activation
)

# Raccourci vers le script de setup principal
$realScriptPath = Join-Path $PSScriptRoot "scripts\env\activate_project_env.ps1"
& $realScriptPath -CommandToRun $CommandToRun
exit $LASTEXITCODE