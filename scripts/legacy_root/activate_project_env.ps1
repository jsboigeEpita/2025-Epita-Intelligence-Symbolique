# Raccourci vers le script d'activation principal
param (
    [string]$CommandToRun = $null # Rendre le paramètre explicite dans le wrapper
)

$realScriptPath = Join-Path $PSScriptRoot "scripts\env\activate_project_env.ps1"

if ($PSBoundParameters.ContainsKey('CommandToRun')) {
    & $realScriptPath -CommandToRun $CommandToRun
} else {
    & $realScriptPath # Appeler sans le paramètre si non fourni au wrapper
}

exit $LASTEXITCODE