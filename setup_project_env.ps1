# Raccourci vers le script de setup principal
$realScriptPath = Join-Path $PSScriptRoot "scripts\env\setup_project_env.ps1"
& $realScriptPath @PSBoundParameters
exit $LASTEXITCODE