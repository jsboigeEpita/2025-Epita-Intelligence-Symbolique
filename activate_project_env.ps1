<#
.SYNOPSIS
Point d'entrée pour exécuter une commande dans l'environnement projet correctement configuré.

.DESCRIPTION
Ce script délègue la gestion de l'environnement et l'exécution de commandes
à un gestionnaire Python centralisé (`project_core/core_from_scripts/environment_manager.py`).
C'est la méthode à privilégier pour garantir que toutes les commandes (tests, scripts, etc.)
s'exécutent avec le bon environnement Conda, le bon PYTHONPATH, et les bonnes variables
d'environnement (comme JAVA_HOME).

.PARAMETER CommandToRun
La commande complète à exécuter (ex: "pytest tests/unit").

.EXAMPLE
# Exécute la suite de tests unitaires
.\activate_project_env.ps1 pytest tests/unit
#>
param(
    [string]$CommandToRun,
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$RemainingArgs
)

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

# Étape 2: Construire la commande à exécuter
$fullCommand = ($CommandToRun + " " + ($RemainingArgs -join ' ')).Trim()
if (-not $fullCommand) {
    Write-Host "[ERREUR] Aucune commande fournie." -ForegroundColor Red
    exit 1
}

# Étape 3: Exécution via Start-Process pour plus de robustesse
Write-Host "[INFO] Délégation au gestionnaire d'environnement Python via Conda..." -ForegroundColor Cyan

# La construction de la liste d'arguments est délicate à cause de la double interprétation.
# On la reconstruit en une seule chaîne, en s'assurant que la commande finale est bien passée.
# On ne peut pas utiliser le double tiret `--` de manière fiable ici.
# On passe la commande à exécuter comme un seul gros argument.
$commandForPythonManager = "run `"$fullCommand`""
$argumentList = "run -n $envName --no-capture-output --live-stream python -m $moduleName $commandForPythonManager"

Write-Host "[DEBUG] Commande d'exécution via Start-Process :" -ForegroundColor Gray
Write-Host "conda.exe $argumentList" -ForegroundColor Gray

try {
    $condaExecutable = Get-Command conda.exe | Select-Object -ExpandProperty Source
    # Solution de la dernière chance: on hardcode le chemin vers Python car `where` ne fonctionne pas.
    $envName = (python -m project_core.core_from_scripts.environment_manager get-env-name).Trim()
    $pythonInCondaEnv = "C:\tools\miniconda3\envs\$envName\python.exe"
    
    if (-not (Test-Path $pythonInCondaEnv)) {
        Write-Host "[FATAL] L'exécutable Python n'a pas été trouvé au chemin hardcodé: $pythonInCondaEnv" -ForegroundColor Red
        exit 1
    }
    
    $finalCommand = "$pythonInCondaEnv -m project_core.test_runner --type e2e"
    $process = Start-Process -FilePath "pwsh.exe" -ArgumentList "-Command", $finalCommand -Wait -PassThru -NoNewWindow
    $exitCode = $process.ExitCode
}
catch {
    Write-Host "[FATAL] L'exécution de la commande via conda a échoué." -ForegroundColor Red
    Write-Host $_ -ForegroundColor Red
    $exitCode = 1
}

exit $exitCode
