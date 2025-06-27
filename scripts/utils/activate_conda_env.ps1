param(
    [string]$CommandToRun
)

# Activer l'environnement Conda pour le projet
conda activate projet-is-roo-new

if (-not ([string]::IsNullOrEmpty($CommandToRun))) {
    Write-Host "Executing command: $CommandToRun"
    Invoke-Expression $CommandToRun
}