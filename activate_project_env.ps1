<#
.SYNOPSIS
Point d'entrée pour exécuter une commande de test via le nouvel exécuteur Python.

.DESCRIPTION
Ce script délègue l'exécution de la commande de test au script `scripts/test_executor.py`.
Il sert de simple point d'entrée pour maintenir la compatibilité avec les appels existants.

.PARAMETER CommandToRun
La commande complète à exécuter (ex: "pytest -m jvm_test").

.EXAMPLE
.\activate_project_env.ps1 -CommandToRun "pytest -m jvm_test"
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$CommandToRun
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$ExecutorScript = Join-Path $ProjectRoot "scripts/test_executor.py"

Write-Host "[INFO] Délégation de l'exécution au nouveau script : $ExecutorScript" -ForegroundColor Cyan

# Construit la commande pour appeler le script Python
# On passe la commande originale comme un seul argument entre guillemets.
$commandArgs = @(
    $ExecutorScript,
    "--original-command",
    "`"$CommandToRun`""
)

Write-Host "[DEBUG] Commande d'appel : python $($commandArgs -join ' ')" -ForegroundColor Gray

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
    $rawEnvName = python -m $moduleName get-env-name
    $envName = $rawEnvName.Trim()
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

Write-Host "[INFO] Exécution directe de la commande dans l'environnement Conda..." -ForegroundColor Cyan

# Construction de la commande `conda run`
$CommandArray = $CommandToRun.Split(" ")
$CondaArgs = @("run", "-n", $envName, "--no-capture-output", "--live-stream") + $CommandArray

Write-Host "[DEBUG] Invoking: conda $($CondaArgs -join ' ')" -ForegroundColor Gray

# Étape 3: Exécution et propagation du code de sortie
try {
    # Exécute la commande. La sortie sera capturée par l'appelant.
    conda $CondaArgs
    
    $exitCode = $LASTEXITCODE
}
catch {
    Write-Host "[ERREUR FATALE] Échec lors de l'exécution de la commande via 'conda run'." -ForegroundColor Red
    $_.Exception.ToString()
    $exitCode = 1
}

Write-Host "[INFO] Script terminé avec le code de sortie : $exitCode" -ForegroundColor Cyan
exit $exitCode
