# Raccourci vers le script d'activation principal
param (
    [string]$CommandToRun = $null # Rendre le paramètre explicite dans le wrapper
)

# Correction: Le script réel est maintenant setup_project_env.ps1 dans le même répertoire
$realScriptPath = Join-Path $PSScriptRoot "setup_project_env.ps1"

if ($PSBoundParameters.ContainsKey('CommandToRun')) {
    & $realScriptPath -CommandToRun $CommandToRun
} else {
    & $realScriptPath # Appeler sans le paramètre si non fourni au wrapper
}

exit $LASTEXITCODE