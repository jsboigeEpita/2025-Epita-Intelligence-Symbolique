[CmdletBinding()]
param (
    [switch]$ForceReinstallAll,    # Pour forcer la réinstallation complète (outils et environnement)
    [switch]$ForceReinstallTools,  # Pour forcer la réinstallation des outils portables (JDK, Octave, etc.)
    [switch]$ForceReinstallEnv,    # Pour forcer la réinstallation de l'environnement Conda
    [switch]$Interactive,          # Pour activer le mode interactif (poser des questions)
    [switch]$SkipTools,            # Pour sauter l'installation/vérification des outils portables
    [switch]$SkipEnv,              # Pour sauter la création/mise à jour de l'environnement Conda
    [switch]$SkipCleanup,          # Pour sauter les étapes de nettoyage
    [switch]$SkipPipInstall        # Pour sauter l'étape `pip install -e .`
)

$ErrorActionPreference = "Stop"
Push-Location $PSScriptRoot # S'assurer qu'on est à la racine du projet

try {
    $pythonScriptPath = Join-Path $PSScriptRoot "scripts/setup_core/main_setup.py"

    if (-not (Test-Path $pythonScriptPath)) {
        Write-Error "Le script d'orchestration Python '$pythonScriptPath' est introuvable."
        exit 1
    }

    $pythonArgs = @()
    if ($ForceReinstallAll) {
        $pythonArgs += "--force-reinstall-tools"
        $pythonArgs += "--force-reinstall-env"
    } else {
        if ($ForceReinstallTools) { $pythonArgs += "--force-reinstall-tools" }
        if ($ForceReinstallEnv)   { $pythonArgs += "--force-reinstall-env" }
    }

    if ($Interactive)         { $pythonArgs += "--interactive" }
    if ($SkipTools)           { $pythonArgs += "--skip-tools" }
    if ($SkipEnv)             { $pythonArgs += "--skip-env" }
    if ($SkipCleanup)         { $pythonArgs += "--skip-cleanup" }
    if ($SkipPipInstall)      { $pythonArgs += "--skip-pip-install" }

    Write-Host "Lancement du script d'installation Python : $pythonScriptPath"
    if ($pythonArgs.Count -gt 0) {
        Write-Host "Avec les arguments: $($pythonArgs -join ' ')"
    } else {
        Write-Host "Sans arguments spécifiques."
    }

    # Tenter de trouver python.exe ou python
    $pythonExecutable = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonExecutable) {
        # Essayer python3 si python n'est pas trouvé (courant sur certains systèmes Linux/Mac via Conda)
        $pythonExecutable = Get-Command python3 -ErrorAction SilentlyContinue
    }

    if (-not $pythonExecutable) {
        Write-Error "Python (python ou python3) n'est pas trouvé dans le PATH. Veuillez l'installer, l'ajouter au PATH, ou activer l'environnement Conda approprié."
        exit 1
    }
    
    Write-Host "Utilisation de l'exécutable Python : $($pythonExecutable.Source)"

    # Exécuter le script Python
    & $pythonExecutable.Source $pythonScriptPath $pythonArgs
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -ne 0) {
        Write-Warning "Le script d'installation Python a terminé avec des erreurs (code: $exitCode)."
    } else {
        Write-Host "Le script d'installation Python a terminé avec succès."
    }
    exit $exitCode

}
catch {
    Write-Error "Une erreur PowerShell est survenue lors de la tentative d'exécution du script Python : $($_.Exception.Message)"
    # Tenter de retourner un code d'erreur générique si $LASTEXITCODE n'est pas pertinent ici
    if ($LASTEXITCODE -eq 0) { exit 1 } else { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}