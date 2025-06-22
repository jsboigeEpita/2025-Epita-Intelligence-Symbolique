<#
.SYNOPSIS
    Point d'entrée unifié pour lancer tous les types de tests du projet.

.DESCRIPTION
    Ce script orchestre l'exécution des tests en utilisant l'orchestrateur Python centralisé.
    Il gère l'activation de l'environnement Conda et transmet les arguments à l'orchestrateur.

.PARAMETER Type
    Spécifie le type de tests à exécuter.
    Valeurs possibles : "unit", "functional", "e2e", "all".

.PARAMETER Path
    (Optionnel) Spécifie un chemin vers un fichier ou un répertoire de test spécifique.

.PARAMETER Browser
    (Optionnel) Spécifie le navigateur à utiliser pour les tests Playwright (e2e).
    Valeurs possibles : "chromium", "firefox", "webkit".

.EXAMPLE
    # Lancer les tests End-to-End avec Chromium
    .\run_tests.ps1 -Type e2e -Browser chromium

.EXAMPLE
    # Lancer les tests unitaires
    .\run_tests.ps1 -Type unit

.EXAMPLE
    # Lancer un test fonctionnel spécifique
    .\run_tests.ps1 -Type functional -Path "tests/functional/specific_feature"
#>
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("unit", "functional", "e2e", "all", "validation")]
    [string]$Type,

    [string]$Path,

    [ValidateSet("chromium", "firefox", "webkit")]
    [string]$Browser
)

$ProjectRoot = $PSScriptRoot
$ActivationScript = Join-Path $ProjectRoot "activate_project_env.ps1"
$TestRunnerScript = Join-Path $ProjectRoot "project_core/test_runner.py"

if (-not (Test-Path $ActivationScript)) {
    Write-Host "[ERREUR] Le script d'activation '$ActivationScript' est introuvable." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $TestRunnerScript)) {
    Write-Host "[ERREUR] L'orchestrateur de test '$TestRunnerScript' est introuvable." -ForegroundColor Red
    exit 1
}

# Construire la liste d'arguments pour le test_runner.py
$runnerArgs = @(
    $TestRunnerScript,
    "--type", $Type
)
if ($PSBoundParameters.ContainsKey('Path')) {
    $runnerArgs += "--path", $Path
}
if ($PSBoundParameters.ContainsKey('Browser')) {
    $runnerArgs += "--browser", $Browser
}

$CommandToRun = "python $($runnerArgs -join ' ')"

if ($Type -eq "validation") {
    $CommandToRun = "python tests/e2e/web_interface/validate_jtms_web_interface.py; python -m tests.functional.test_phase3_web_api_authentic"
}

Write-Host "[INFO] Commande à exécuter : $CommandToRun" -ForegroundColor Cyan
Write-Host "[INFO] Lancement des tests via $ActivationScript..." -ForegroundColor Cyan

# & $ActivationScript -CommandToRun $CommandToRun

# --- NOUVELLE LOGIQUE D'EXÉCUTION DIRECTE ---
# Contournement de activate_project_env.ps1 et environment_manager.py pour le débogage.

# 1. Charger manuellement les variables depuis .env
$envFile = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "[ERREUR] Fichier .env introuvable à la racine. Impossible de continuer." -ForegroundColor Red
    exit 1
}

# Lire le fichier .env et charger les variables dans l'environnement du script
Get-Content $envFile | ForEach-Object {
    if ($_ -match "^\s*([\w.-]+)\s*=\s*(.*)\s*$") {
        $key = $matches[1]
        $value = $matches[2]
        # Supprimer les guillemets optionnels
        $value = $value -replace '^"|"$'
        $value = $value -replace "^'|'$"
        Set-Item -Path "env:$key" -Value $value
        Write-Host "[INFO] Variable depuis .env chargée: $key" -ForegroundColor Gray
    }
}

# 2. Vérifier que les variables essentielles sont là
if (-not $env:CONDA_ENV_NAME) {
    Write-Host "[ERREUR] CONDA_ENV_NAME n'est pas défini dans le fichier .env." -ForegroundColor Red
    exit 1
}

$CondaEnvName = $env:CONDA_ENV_NAME
Write-Host "[INFO] Environnement Conda cible : $CondaEnvName" -ForegroundColor Green

# 3. Définir les variables d'environnement cruciales
$env:PROJECT_ROOT = $ProjectRoot
$env:PYTHONPATH = $ProjectRoot
# Les autres variables comme les ports sont déjà chargées depuis .env

Write-Host "[INFO] PYTHONPATH défini sur: $($env:PYTHONPATH)" -ForegroundColor Cyan

# 4. Exécuter la commande directement avec 'conda run'
Write-Host "[INFO] Exécution directe via 'conda run'..." -ForegroundColor Green

try {
    # --no-capture-output permet de voir la sortie en temps réel
    # On passe explicitement la commande à exécuter à powershell
    conda run -n $CondaEnvName --no-capture-output powershell -c "$CommandToRun"
}
catch {
    Write-Host "[ERREUR] Échec de l'exécution de conda run." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
# --- FIN DE LA NOUVELLE LOGIQUE ---

$exitCode = $LASTEXITCODE
Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
exit $exitCode