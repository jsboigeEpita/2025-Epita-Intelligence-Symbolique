# Script PowerShell pour configurer automatiquement l'utilisation du mock JPype1
# lorsque Python 3.12 ou supérieur est détecté

# Fonction pour afficher les messages de log avec timestamp
function Log-Message {
    param (
        [string]$Level,
        [string]$Message
    )
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "$timestamp [$Level] $Message"
}

# Fonction pour tester l'importation d'un module
function Test-ModuleImport {
    param (
        [string]$Module
    )
    
    try {
        $cmd = "python -c `"import $Module; print('$Module importé avec succès.')`""
        $output = Invoke-Expression $cmd 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Log-Message -Level "INFO" -Message "$output"
            return $true
        } else {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'importation de $Module : $output"
            return $false
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Exception lors du test d'importation de $Module : $_"
        return $false
    }
}

# Point d'entrée principal du script
Log-Message -Level "INFO" -Message "Configuration du mock JPype1..."

# Obtenir la version de Python
$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Log-Message -Level "INFO" -Message "Version de Python détectée : $pythonVersion"

# Vérifier si la version de Python est 3.12 ou supérieure
$pythonMajor = [int]($pythonVersion.Split('.')[0])
$pythonMinor = [int]($pythonVersion.Split('.')[1])
$needsMock = ($pythonMajor -eq 3 -and $pythonMinor -ge 12) -or ($pythonMajor -gt 3)

if ($needsMock) {
    Log-Message -Level "INFO" -Message "Python $pythonVersion détecté. Configuration du mock JPype1..."
    
    # Vérifier si JPype1 est déjà installé
    $jpypeInstalled = Test-ModuleImport -Module "jpype"
    
    if ($jpypeInstalled) {
        Log-Message -Level "INFO" -Message "JPype1 est déjà installé, mais pourrait ne pas fonctionner correctement avec Python $pythonVersion."
        Log-Message -Level "INFO" -Message "Nous allons configurer le mock JPype1 pour assurer la compatibilité."
    } else {
        Log-Message -Level "INFO" -Message "JPype1 n'est pas installé ou ne fonctionne pas correctement avec Python $pythonVersion."
        Log-Message -Level "INFO" -Message "Configuration du mock JPype1..."
    }
    
    # Vérifier que le mock JPype1 existe
    $projectRoot = (Get-Item -Path ".\").FullName
    $mockPath = Join-Path -Path $projectRoot -ChildPath "tests\mocks\jpype_mock.py"
    
    if (Test-Path $mockPath) {
        Log-Message -Level "INFO" -Message "Mock JPype1 trouvé à $mockPath"
    } else {
        Log-Message -Level "ERROR" -Message "Mock JPype1 non trouvé à $mockPath"
        Log-Message -Level "ERROR" -Message "Assurez-vous que le fichier tests/mocks/jpype_mock.py existe."
        exit 1
    }
    
    # Tester le mock JPype1
    Log-Message -Level "INFO" -Message "Test du mock JPype1..."
    $testScript = Join-Path -Path $projectRoot -ChildPath "scripts\setup\test_jpype_mock.py"
    
    if (Test-Path $testScript) {
        $cmd = "python `"$testScript`""
        $output = Invoke-Expression $cmd 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Log-Message -Level "INFO" -Message "Mock JPype1 testé avec succès."
        } else {
            Log-Message -Level "ERROR" -Message "Erreur lors du test du mock JPype1 : $output"
            exit 1
        }
    } else {
        Log-Message -Level "ERROR" -Message "Script de test non trouvé à $testScript"
        exit 1
    }
    
    # Exécuter les tests avec le mock
    Log-Message -Level "INFO" -Message "Exécution des tests avec le mock JPype1..."
    $runTestsScript = Join-Path -Path $projectRoot -ChildPath "scripts\setup\run_tests_with_mock.py"
    
    if (Test-Path $runTestsScript) {
        Log-Message -Level "INFO" -Message "Vous pouvez exécuter les tests avec le mock en utilisant la commande suivante :"
        Log-Message -Level "INFO" -Message "python `"$runTestsScript`""
    } else {
        Log-Message -Level "WARNING" -Message "Script d'exécution des tests non trouvé à $runTestsScript"
    }
    
    Log-Message -Level "SUCCESS" -Message "Mock JPype1 configuré avec succès pour Python $pythonVersion."
    Log-Message -Level "INFO" -Message "Vous pouvez maintenant exécuter vos tests sans avoir besoin d'installer JPype1."
} else {
    Log-Message -Level "INFO" -Message "Python $pythonVersion détecté. Pas besoin de configurer le mock JPype1."
    Log-Message -Level "INFO" -Message "JPype1 devrait fonctionner normalement avec cette version de Python."
    
    # Vérifier si JPype1 est installé
    $jpypeInstalled = Test-ModuleImport -Module "jpype"
    
    if (-not $jpypeInstalled) {
        Log-Message -Level "WARNING" -Message "JPype1 n'est pas installé ou ne fonctionne pas correctement."
        Log-Message -Level "INFO" -Message "Vous pouvez l'installer avec la commande suivante :"
        Log-Message -Level "INFO" -Message "python -m pip install JPype1==1.4.1"
    }
}

exit 0