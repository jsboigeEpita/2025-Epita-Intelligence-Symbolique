<#
.SYNOPSIS
Lance la suite de tests du projet avec pytest.

.DESCRIPTION
Ce script est le point d'entrée unique pour exécuter les tests.
Il utilise `activate_project_env.ps1` pour s'assurer que les tests
sont exécutés dans le bon environnement Conda (`projet-is-roo-new`) et
avec le `PYTHONPATH` correctement configuré.

Toute la sortie est redirigée pour être capturée par les logs, et les
erreurs sont gérées de manière centralisée.

.PARAMETER TestArgs
Accepte une chaîne de caractères contenant tous les arguments à passer
directement à pytest. Cela permet de cibler des tests spécifiques ou
d'utiliser des options pytest.

.EXAMPLE
# Exécute tous les tests
.\run_tests.ps1

.EXAMPLE
# Exécute un fichier de test spécifique
.\run_tests.ps1 "tests/agents/core/logic/test_tweety_bridge.py"

.EXAMPLE
# Exécute un test spécifique avec l'option -s pour voir les prints
.\run_tests.ps1 "tests/agents/core/logic/test_tweety_bridge.py -s"
#>
# Ce script ne prend plus d'arguments via le bloc `param`.
# Utilisez les paires clé-valeur, ex: .\run_tests.ps1 -TestType e2e

# --- Vérification et installation des dépendances PowerShell ---
try {
    $moduleName = "PSToml"
    # Vérifier si le module est déjà disponible
    if (-not (Get-Module -ListAvailable -Name $moduleName)) {
        Write-Host "[SETUP] Le module '$moduleName' est manquant. Tentative d'installation depuis PSGallery..." -ForegroundColor Yellow
        
        # Installer le module, en gérant les erreurs potentielles
        Install-Module -Name $moduleName -Scope CurrentUser -Repository PSGallery -Force -Confirm:$false -ErrorAction Stop
        
        Write-Host "[SETUP] Module '$moduleName' installé avec succès." -ForegroundColor Green
    }
    # Importer le module pour s'assurer qu'il est chargé dans la session
    Import-Module -Name $moduleName
}
catch {
    Write-Host "[ERREUR FATALE] Impossible d'installer ou d'importer le module '$moduleName'. Vérifiez votre connexion internet et la configuration de PSGallery." -ForegroundColor Red
    Write-Host "[ERREUR DÉTAILLÉE] $_" -ForegroundColor DarkRed
    exit 1
}


# --- Script Body ---
# UTF-8 signature au début du script pour forcer l'encodage correct
[System.Text.Encoding]::UTF8.GetPreamble()

# Préférences et chemin racine
$ErrorActionPreference = 'Stop'
$script:ProjectRoot = $PSScriptRoot
$script:globalExitCode = 0

# Fichier de dépendances pour le suivi
$dependencyFile = Join-Path $PSScriptRoot "pyproject.toml"

# --- Fonctions ---

# Fonction pour obtenir l'environnement Conda et le chemin Python à partir de `pyproject.toml`
function Get-CondaEnvFromConfig {
    if (-not (Test-Path $dependencyFile)) {
        throw "Fichier de configuration '$dependencyFile' introuvable."
    }
    $config = Get-Content $dependencyFile | Out-String | ConvertFrom-Toml
    $envName = $config.tool.poetry.extras.conda_env_name[0]
    if (-not $envName) {
        throw "Impossible de trouver 'conda_env_name' dans '$dependencyFile'. Assurez-vous qu'il est défini sous [tool.poetry.extras]."
    }
    return $envName
}

# Fonction pour exécuter une commande en utilisant le script d'activation central
# Cela garantit que l'environnement est correctement configuré.
function Invoke-ManagedCommand {
    param(
        [string]$CommandToRun,
        [switch]$NoExitOnError
    )

    $activationScript = Join-Path $script:ProjectRoot "activate_project_env.ps1"
    if (-not (Test-Path $activationScript)) {
        throw "Script d'activation '$activationScript' introuvable!"
    }

    # Déléguer l'exécution au script d'activation, qui gère Conda, PYTHONPATH, etc.
    $argumentList = "-Command `"$CommandToRun`""
    Write-Host "[CMD] $activationScript $argumentList" -ForegroundColor DarkCyan

    # Exécution du processus
    $process = Start-Process "powershell.exe" -ArgumentList "-File `"$activationScript`" $argumentList" -PassThru -NoNewWindow -Wait
    
    $exitCode = $process.ExitCode
    
    # Note: La gestion des logs stdout/stderr est désormais gérée par activate_project_env.ps1.
    # On se contente de vérifier le code de sortie.
    if ($exitCode -ne 0 -and (-not $NoExitOnError)) {
        throw "La commande déléguée via '$activationScript' a échoué avec le code de sortie: $exitCode."
    }
    
    return $exitCode
}


# --- Logique Principale ---

# Parse les arguments en utilisant une table de hachage pour les options
$params = @{
    TestType = "all" # Par défaut, exécute tous les tests non-intégration
}
$remainingArgs = @()
$i = 0
while ($i -lt $args.Count) {
    # Nos clés sont sensibles à la casse et commencent par un tiret (ex: -TestType)
    if ($args[$i] -match '^-([a-zA-Z0-9_]+)$') {
        $paramName = $Matches[1]
        # Si l'argument suivant existe et n'est pas une autre clé, alors c'est une valeur
        if ((($i + 1) -lt $args.Count) -and ($args[$i+1] -notmatch '^-')) {
            $params[$paramName] = $args[$i+1]
            $i++ # On consomme la valeur, on passe à l'argument suivant
        } else {
            # C'est un switch/flag (ex: -SkipOctave)
            $params[$paramName] = $true
        }
    } else {
        # Tout ce qui n'est pas une clé est considéré comme un argument restant (pour Pytest)
        $remainingArgs += $args[$i]
    }
    $i++
}

# Assignation des variables complexes après parsing
$TestType = $params['TestType']
$Path = if ($params.ContainsKey('Path')) { $params['Path'] } else { $null }
$PytestArgs = if ($remainingArgs.Count -gt 0) { $remainingArgs -join ' ' } else { $null }
$SkipOctave = $params.ContainsKey('SkipOctave')


Write-Host "[INFO] Début de l'exécution des tests avec le type: '$TestType'" -ForegroundColor Green
if ($Path) { Write-Host "[INFO] Chemin spécifié: '$Path'" }
if ($PytestArgs) { Write-Host "[INFO] Arguments Pytest supplémentaires: '$PytestArgs'" }

# Branche 1: Installation ou mise à jour des dépendances
if ($TestType -eq "install" -or $TestType -eq "update") {
    Write-Host "[INFO] Installation/Mise à jour des dépendances via Poetry..." -ForegroundColor Cyan
    $installCommand = "python -m poetry " + (if ($TestType -eq "update") { "update" } else { "install --sync" })
    Invoke-ManagedCommand -CommandToRun $installCommand
    exit $LASTEXITCODE
}
# Branche 2: Nettoyage
elseif ($TestType -eq "clean") {
    Write-Host "[INFO] Nettoyage du projet..." -ForegroundColor Cyan
    Get-ChildItem -Path $script:ProjectRoot -Include @("__pycache__", "*.pyc", "_temp") -Recurse -Force | Remove-Item -Recurse -Force
    Write-Host "[INFO] Nettoyage terminé." -ForegroundColor Green
    exit 0
}
# Branche 3: Tests d'intégration avec gestion du backend
elseif ($TestType -eq "e2e") {
    Write-Host "[INFO] Lancement du cycle de test E2E complet via l'orchestrateur..." -ForegroundColor Cyan
    $testPathToRun = if ($Path) { $Path } else { "tests/e2e" }
    $config_file = "tests/e2e/e2e_config.yml"
    # Encapsuler les arguments de pytest dans des apostrophes pour les passer comme une seule chaîne
    $pytestArgsString = "-s -vv `"$testPathToRun`" $PytestArgs".Trim()
    $pytestCommand = "python -m argumentation_analysis.webapp.orchestrator --config `"$config_file`" --frontend test --pytest-args '$pytestArgsString'"
    
    $script:globalExitCode = Invoke-ManagedCommand -CommandToRun $pytestCommand -NoExitOnError
    Write-Host "[INFO] Exécution des tests E2E terminée avec le code de sortie: $script:globalExitCode" -ForegroundColor Cyan
    exit $script:globalExitCode
}
elseif ($TestType -eq "integration") {
    Write-Host "[INFO] Lancement du cycle de test d'intégration avec gestion du backend..." -ForegroundColor Cyan
    $urlsFile = Join-Path $script:ProjectRoot "_temp/service_urls.json" # Fichier pour stocker les PIDs

    try {
        # --- ÉTAPE 1: Démarrer le backend et capturer l'URL ---
        Write-Host "[INFO] Étape 1: Démarrage du service backend en arrière-plan..." -ForegroundColor Yellow
        
        $tempDir = Split-Path $urlsFile -Parent
        if (-not (Test-Path $tempDir)) { New-Item -ItemType Directory -Path $tempDir | Out-Null }
        if (Test-Path $urlsFile) { Remove-Item $urlsFile }
        
        $startArguments = "python -m argumentation_analysis.webapp.orchestrator --backend-only --log-level INFO --exit-after-start"
        
        Write-Host "[CMD] Lancement en arrière-plan: $startArguments"
        # Remplacé par un appel direct non bloquant pour permettre à la boucle de synchronisation de fonctionner.
        $activationScript = Join-Path $script:ProjectRoot "activate_project_env.ps1"
        $startProcessArgs = "-File `"$activationScript`" -Command `"$startArguments`""
        Write-Host "[CMD] Lancement en arrière-plan via Start-Process (sans -Wait): powershell.exe $startProcessArgs" -ForegroundColor DarkCyan
        Start-Process "powershell.exe" -ArgumentList $startProcessArgs -NoNewWindow
        
        # L'attente du fichier d'URL devient le mécanisme de synchronisation principal
        $maxWaitSeconds = 40
        $waitIntervalSeconds = 2
        $waitedSeconds = 0
        while (-not (Test-Path $urlsFile) -and $waitedSeconds -lt $maxWaitSeconds) {
            Write-Host "[INFO] Attente du fichier d'URLs... ($($waitedSeconds)s / $($maxWaitSeconds)s)" -ForegroundColor Gray
            Start-Sleep -Seconds $waitIntervalSeconds
            $waitedSeconds += $waitIntervalSeconds
        }

        if (-not (Test-Path $urlsFile)) { throw "Timeout: Le fichier d'URLs '$urlsFile' n'a pas été créé." }
        
        $urlsData = Get-Content -Encoding UTF8 $urlsFile | ConvertFrom-Json
        $backendUrl = $urlsData.backend_url
        if (-not $backendUrl) { throw "Impossible de trouver l'URL du backend dans '$urlsFile'." }
        
        Write-Host "[INFO] URL Backend capturée: $backendUrl" -ForegroundColor Green
        
        # Définir les variables d'environnement pour Pytest
        $env:BACKEND_URL = $backendUrl
        $env:IS_INTEGRATION_TEST = "true"

        # --- ÉTAPE 2: Lancer Pytest pour les tests d'intégration ---
        Write-Host "[INFO] Étape 2: Lancement de Pytest pour les tests d'intégration..." -ForegroundColor Yellow
        $testPathToRun = if ($Path) { $Path } else { "tests/integration" }
        $pytestCommand = "python -m pytest -s -vv `"$testPathToRun`""
        
        If ($PytestArgs) {
             $pytestCommand += " $PytestArgs"
        }

        $script:globalExitCode = Invoke-ManagedCommand -CommandToRun $pytestCommand -NoExitOnError
    }
    catch {
        Write-Host "[ERREUR FATALE] $_" -ForegroundColor Red
        $script:globalExitCode = 1
    }
    finally {
        # --- ÉTAPE 3: Arrêter le backend ---
        Write-Host "[INFO] Étape 3: Arrêt des services..." -ForegroundColor Yellow
        $stopCommand = "python -m argumentation_analysis.webapp.orchestrator --stop"
        $stopExitCode = Invoke-ManagedCommand -CommandToRun $stopCommand -NoExitOnError
        if ($stopExitCode -ne 0) {
            Write-Host "[AVERTISSEMENT] L'orchestrateur a rencontré une erreur lors de l'arrêt (code: $stopExitCode)." -ForegroundColor Yellow
            if ($script:globalExitCode -eq 0) { $script:globalExitCode = 1 }
        }
        
        if (Test-Path $urlsFile) { Remove-Item $urlsFile }
    }
    
    Write-Host "[INFO] Exécution des tests d'intégration terminée avec le code de sortie: $script:globalExitCode" -ForegroundColor Cyan
    exit $script:globalExitCode
}
# Branche 4: Tests Unit/Functional (Python) directs
else {
    Write-Host "[INFO] Lancement des tests de type '$TestType' via le point d'entrée unifié..." -ForegroundColor Cyan

    $testPaths = @{
        "unit"       = "tests/unit"
        "functional" = "tests/functional"
        "all"        = @("tests/unit", "tests/functional") # 'integration' et 'e2e' sont gérés à part
        "validation" = "tests/validation"
    }

    $selectedPaths = if ($Path) {
        @($Path)
    } else {
        $testPaths[$TestType]
    }

    if (-not $selectedPaths) {
        Write-Host "[ERREUR] Type de test '$TestType' non valide. Options valides: $($testPaths.Keys -join ', ')." -ForegroundColor Red
        exit 1
    }
    
    # Construire la commande pytest
    $pytestCommandParts = @("python", "-m", "pytest", "-s", "-vv") + $selectedPaths
    
    if ($SkipOctave) {
        $pytestCommandParts += "--skip-octave"
    }

    if ($PytestArgs) {
        # Utiliser directement PytestArgs qui contient maintenant les arguments restants
        $pytestCommandParts += $PytestArgs.Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
    }
    $pytestFinalCommand = $pytestCommandParts -join " "

    # Exécution
    $runnerLogFile = Join-Path $script:ProjectRoot '_temp/test_runner.log'
    Write-Host "[INFO] Commande Pytest à exécuter: $pytestFinalCommand" -ForegroundColor Green
    Write-Host "[INFO] Les logs partiels seront visibles ici. Voir '$runnerLogFile' pour les détails complets." -ForegroundColor Yellow

    try {
        $exitCode = Invoke-ManagedCommand -CommandToRun $pytestFinalCommand
        if ($exitCode -ne 0) {
             Write-Host "[ERREUR] Pytest a échoué avec le code $exitCode" -ForegroundColor Red
             exit $exitCode
        }
        Write-Host "[INFO] Exécution terminée avec le code de sortie : $exitCode" -ForegroundColor Cyan
        exit $exitCode
    }
    catch {
        Write-Host "[ERREUR] Une erreur est survenue: $_" -ForegroundColor Red
        exit 1
    }
}
