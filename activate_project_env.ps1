<#
.SYNOPSIS
Point d'entrée pour exécuter une commande dans l'environnement projet correctement configuré.

.DESCRIPTION
Ce script exécute une commande donnée directement dans l'environnement Conda du projet,
en s'assurant que les variables d'environnement actuelles sont propagées.

.PARAMETER CommandToRun
La commande complète à exécuter (ex: "pytest tests/unit").

.PARAMETER RemainingArgs
Arguments supplémentaires pour la commande.

.EXAMPLE
# Exécute la suite de tests unitaires
.\activate_project_env.ps1 -CommandToRun "pytest tests/unit"
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$CommandToRun
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot

# --- Initialisation de Conda ---
# Trouve le chemin de Conda et l'initialise pour la session PowerShell actuelle.
# C'est essentiel pour les contextes d'exécution (comme `pwsh -c`) où le profil n'est pas chargé.
$condaExecutable = $null
$condaFound = $false

# 1. Tentative simple via le PATH
try {
    $condaExecutable = Get-Command conda.exe -ErrorAction Stop | Select-Object -ExpandProperty Source
    if ($condaExecutable) { $condaFound = $true }
    Write-Host "[DEBUG] Conda trouvé dans le PATH: $condaExecutable." -ForegroundColor DarkGray
} catch {
    # 2. Recherche exhaustive si non trouvé dans le PATH
    Write-Host "[DEBUG] Conda non trouvé dans le PATH. Recherche dans les emplacements standards..." -ForegroundColor DarkGray
    $commonPaths = @(
        (Join-Path $env:USERPROFILE "Anaconda3\Scripts\conda.exe"),
        (Join-Path $env:USERPROFILE "Miniconda3\Scripts\conda.exe"),
        (Join-Path $env:ProgramData "Anaconda3\Scripts\conda.exe"),
        (Join-Path $env:ProgramData "Miniconda3\Scripts\conda.exe"),
        (Join-Path "C:\tools" "miniconda3\Scripts\conda.exe")
    )
    if (Test-Path "D:\") {
        $commonPaths += (Join-Path "D:\tools" "miniconda3\Scripts\conda.exe")
    }
    foreach ($path in $commonPaths) {
        if (Test-Path $path) {
            $condaExecutable = $path
            $condaFound = $true
            Write-Host "[DEBUG] Conda trouvé à un emplacement standard: $condaExecutable" -ForegroundColor DarkGray
            
            # Ajout du répertoire de Conda au PATH pour la session en cours
            $condaDir = Split-Path $condaExecutable -Parent
            $env:Path = "$condaDir;$env:Path"
            Write-Host "[DEBUG] Ajout de '$condaDir' au PATH pour la session." -ForegroundColor DarkGray
            break
        }
    }
}

if (-not $condaFound) {
    Write-Host "[FATAL] 'conda.exe' est introuvable après une recherche exhaustive. Veuillez l'installer ou l'ajouter au PATH." -ForegroundColor Red
    exit 1
}

# La partie 'hook' est instable, on ne l'utilise pas. On se contente d'avoir ajouté Conda au PATH.
Write-Host "[INFO] Conda trouvé. L'initialisation via 'hook' est sautée pour plus de stabilité." -ForegroundColor Yellow

$ErrorActionPreference = "Stop"

# --- DEBUGGING START ---
$debugLogFile = Join-Path $PSScriptRoot "_temp/debug_activate_script.log"
"--- Starting activate_project_env.ps1 at $(Get-Date) ---" | Out-File -FilePath $debugLogFile -Encoding utf8 -Append
Get-Command conda | Out-File -FilePath $debugLogFile -Encoding utf8 -Append
$env:PATH | Out-File -FilePath $debugLogFile -Encoding utf8 -Append
# --- DEBUGGING END ---

# Le module Python est le SEUL responsable de la logique.
$moduleName = "project_core.core_from_scripts.environment_manager"

# Étape 1: Récupérer le nom de l'environnement Conda de manière fiable
Write-Host "[INFO] Récupération du nom de l'environnement Conda depuis .env..." -ForegroundColor Cyan
try {
    $envName = python -m $moduleName get-env-name
    if (-not $envName) {
        throw "Le nom de l'environnement Conda n'a pas pu être déterminé."
    }
    Write-Host "[INFO] Nom de l'environnement Conda détecté : '$envName'" -ForegroundColor Green
}
catch {
    Write-Host "[ERREUR FATALE] Impossible de récupérer le nom de l'environnement Conda." -ForegroundColor Red
    Write-Host $_
    exit 1
}

# Étape 2: Construire la commande finale pour l'exécuter avec `conda run`
# On utilise --no-capture-output pour s'assurer que stdout/stderr du processus enfant
# sont directement streamés, ce qui est crucial pour le logging des tests.
$condaCommand = "conda"
$commandToExecuteInsideEnv = "python -m $moduleName run `"$CommandToRun`""
# Correction: suppression du séparateur '--' qui n'est pas géré correctement par le shell sous-jacent.
$finalCommand = "$condaCommand run -n $envName --no-capture-output --live-stream $commandToExecuteInsideEnv"

Write-Host "[INFO] Délégation au gestionnaire d'environnement Python via Conda..." -ForegroundColor Cyan
Write-Host "[DEBUG] Commande finale: $finalCommand" -ForegroundColor Gray

# Étape 3: Exécution et propagation du code de sortie
try {
    Invoke-Expression -Command $finalCommand
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Host "[ERREUR FATALE] Échec lors de l'exécution de la commande via 'conda run'." -ForegroundColor Red
    Write-Host $_
    $exitCode = 1
}

Write-Host "[INFO] Script terminé avec le code de sortie : $exitCode" -ForegroundColor Cyan
exit $exitCode
