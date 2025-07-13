<#
.SYNOPSIS
Lance les tests Pytest pour le projet, en configurant l'environnement nécessaire.

.DESCRIPTION
Ce script est le point d'entrée pour l'exécution des tests e2e. Il reçoit les URLs des
services, les configure comme variables d'environnement, active l'environnement Conda
et lance ensuite pytest avec les arguments fournis.

.PARAMETER TestPath
Chemin vers un fichier ou un répertoire de test spécifique.

.PARAMETER BackendUrl
URL du serveur backend.

.PARAMETER FrontendUrl
URL du serveur frontend.

.PARAMETER PytestArgs
Arguments supplémentaires à passer directement à pytest.
#>
param(
    [string]$TestPath = "tests/e2e/python",
    [string]$BackendUrl,
    [string]$FrontendUrl,
    [string]$PytestArgs
)

$ErrorActionPreference = 'Stop'

Write-Host "[Run Tests] Début de l'exécution des tests..." -ForegroundColor Cyan
Write-Host "[Run Tests] TestPath: $TestPath"
Write-Host "[Run Tests] BackendUrl: $BackendUrl"
Write-Host "[Run Tests] FrontendUrl: $FrontendUrl"
Write-Host "[Run Tests] PytestArgs: $PytestArgs"

# Vérification de la présence des URLs requises
if ([string]::IsNullOrEmpty($BackendUrl) -or [string]::IsNullOrEmpty($FrontendUrl)) {
    throw "[Run Tests] ERREUR: Les paramètres -BackendUrl et -FrontendUrl sont obligatoires."
}

# Configurer les variables d'environnement pour que les tests Playwright puissent les utiliser
Write-Host "[Run Tests] Configuration des variables d'environnement..."
$env:BACKEND_URL = $BackendUrl
$env:FRONTEND_URL = $FrontendUrl

# Définir le répertoire de travail à la racine du projet
Set-Location $PSScriptRoot

# Lire le fichier .env pour obtenir le nom de l'environnement Conda
$envFile = Join-Path $PSScriptRoot ".env"
$condaEnvName = $null
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*CONDA_ENV_NAME\s*=\s*(.*)") {
            $condaEnvName = $Matches[1].Trim()
            # Supprimer les guillemets si présents
            if ($condaEnvName.StartsWith('"') -and $condaEnvName.EndsWith('"')) {
                $condaEnvName = $condaEnvName.Substring(1, $condaEnvName.Length - 2)
            }
        }
    }
}

if ([string]::IsNullOrEmpty($condaEnvName)) {
    throw "[Run Tests] ERREUR: La variable CONDA_ENV_NAME n'est pas définie dans le fichier .env."
}

Write-Host "[Run Tests] Nom de l'environnement Conda détecté: $condaEnvName" -ForegroundColor Green

# Construction de la commande pytest finale
$pytestCommand = @(
    "conda", "run", "-n", $condaEnvName, "--no-capture-output",
    "python", "-m", "pytest", $TestPath,
    "-p", "no:playwright", # Désactive le chargement du plugin pytest-playwright
    "--verbose",
    "--html=reports/e2e_test_report.html",
    "--self-contained-html"
)

# Ajouter les arguments pytest supplémentaires s'ils sont fournis
if (-not [string]::IsNullOrEmpty($PytestArgs)) {
    $additionalArgs = $PytestArgs.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
    $pytestCommand += $additionalArgs
}

# Ajout des répertoires nécessaires au PYTHONPATH
$env:PYTHONPATH = "$PSScriptRoot;$PSScriptRoot\project_core;$env:PYTHONPATH"


$finalCommandString = $pytestCommand -join " "
Write-Host "[Run Tests] Commande complète à exécuter : $finalCommandString" -ForegroundColor DarkGray

# Exécution directe de la commande Conda
try {
    Invoke-Expression -Command $finalCommandString
    $exitCode = $LASTEXITCODE
    Write-Host "[Run Tests] L'exécution de Conda a terminé avec le code de sortie: $exitCode"

    # Propager le code de sortie
    exit $exitCode
} catch {
    Write-Host "[Run Tests] [ERREUR FATALE] L'exécution via Conda a échoué." -ForegroundColor Red
    Write-Host $_.Exception.Message
    exit 1
}

Write-Host "[Run Tests] Exécution des tests terminée." -ForegroundColor Green
