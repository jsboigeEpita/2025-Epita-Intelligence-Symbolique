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
# Exécute la suite de tests unitaires et fonctionnels
.\activate_project_env.ps1 "pytest tests/unit tests/functional"

.EXAMPLE
# Affiche la version de python de l'environnement
.\activate_project_env.ps1 "python --version"
#>
param(
    [Parameter(Mandatory=$true, ValueFromRemainingArguments=$true)]
    [string[]]$CommandArgs
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot

# --- Initialisation de Conda pour les sessions non-interactives ---
# Tente de trouver la commande 'conda'. Si elle n'est pas dans le PATH,
# une recherche exhaustive est effectuée.
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

# --- Exécution de la commande ---
# Configuration pour la compatibilité des tests et l'import de modules locaux
$env:PYTHONPATH = "$PSScriptRoot;$env:PYTHONPATH"

# Environnement conda cible
$condaEnvName = "projet-is"

# Construit la liste d'arguments pour `conda run`.
# --no-capture-output est crucial pour que les logs des tests soient visibles en temps réel.
$condaArgs = @("run", "--no-capture-output", "--live-stream", "-n", $condaEnvName) + $CommandArgs

Write-Host "[DEBUG] Calling Conda with: & '$condaExecutable' $($condaArgs -join ' ')" -ForegroundColor Gray

# Exécute la commande directement en utilisant l'opérateur d'appel `&`.
# C'est la méthode la plus propre et la plus robuste, qui évite Invoke-Expression et le hook.
& $condaExecutable $condaArgs

# Propage le code de sortie du script python
$exitCode = $LASTEXITCODE

Write-Host "[INFO] Script terminé avec le code de sortie : $exitCode" -ForegroundColor Cyan
exit $exitCode
