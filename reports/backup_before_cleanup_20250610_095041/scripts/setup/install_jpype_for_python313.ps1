# Script PowerShell pour installer JPype1 pour Python 3.13
# Version simplifiée pour éviter les problèmes de paramètres

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
Log-Message -Level "INFO" -Message "Installation de JPype1 pour Python 3.13..."

# Obtenir la version de Python
$pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Log-Message -Level "INFO" -Message "Version de Python détectée : $pythonVersion"

# Vérifier si JPype1 est déjà installé
$jpypeInstalled = Test-ModuleImport -Module "jpype"
if ($jpypeInstalled) {
    Log-Message -Level "INFO" -Message "JPype1 est déjà installé et fonctionne correctement."
    exit 0
}

# Désinstaller JPype1 s'il est déjà installé mais ne fonctionne pas
Log-Message -Level "INFO" -Message "Désinstallation de JPype1 existant..."
python -m pip uninstall -y JPype1 | Out-Null

# Mettre à jour pip, setuptools et wheel
Log-Message -Level "INFO" -Message "Mise à jour de pip, setuptools et wheel..."
python -m pip install --upgrade pip setuptools wheel | Out-Null

# Méthode 1: Installer JPype1 avec pip standard
Log-Message -Level "INFO" -Message "Méthode 1: Installation de JPype1 avec pip standard..."
$cmd = "python -m pip install --force-reinstall JPype1==1.4.1"
Log-Message -Level "INFO" -Message "Commande: $cmd"
$output = Invoke-Expression $cmd 2>&1

if ($LASTEXITCODE -eq 0 -and (Test-ModuleImport -Module "jpype")) {
    Log-Message -Level "INFO" -Message "JPype1 installé avec succès avec pip standard."
    exit 0
}

# Méthode 2: Installer JPype1 avec pip et --no-binary
Log-Message -Level "INFO" -Message "Méthode 2: Installation de JPype1 avec pip et --no-binary..."
$cmd = "python -m pip install --force-reinstall --no-binary=JPype1 JPype1==1.4.1"
Log-Message -Level "INFO" -Message "Commande: $cmd"
$output = Invoke-Expression $cmd 2>&1

if ($LASTEXITCODE -eq 0 -and (Test-ModuleImport -Module "jpype")) {
    Log-Message -Level "INFO" -Message "JPype1 installé avec succès avec pip et --no-binary."
    exit 0
}

# Méthode 3: Installer JPype1 depuis GitHub
Log-Message -Level "INFO" -Message "Méthode 3: Installation de JPype1 depuis GitHub..."
$cmd = "python -m pip install git+https://github.com/jpype-project/jpype.git@master"
Log-Message -Level "INFO" -Message "Commande: $cmd"
$output = Invoke-Expression $cmd 2>&1

if ($LASTEXITCODE -eq 0 -and (Test-ModuleImport -Module "jpype")) {
    Log-Message -Level "INFO" -Message "JPype1 installé avec succès depuis GitHub."
    exit 0
}

# Méthode 4: Essayer d'installer pyjnius comme alternative
Log-Message -Level "INFO" -Message "Méthode 4: Installation de pyjnius comme alternative à JPype1..."
$cmd = "python -m pip install pyjnius"
Log-Message -Level "INFO" -Message "Commande: $cmd"
$output = Invoke-Expression $cmd 2>&1

if ($LASTEXITCODE -eq 0 -and (Test-ModuleImport -Module "jnius")) {
    Log-Message -Level "INFO" -Message "pyjnius installé avec succès comme alternative à JPype1."
    Log-Message -Level "INFO" -Message "Vous devrez adapter votre code pour utiliser pyjnius au lieu de JPype1."
    exit 0
}

# Si toutes les méthodes ont échoué
Log-Message -Level "ERROR" -Message "Toutes les méthodes d'installation de JPype1 ont échoué."
Log-Message -Level "INFO" -Message "Suggestions:"
Log-Message -Level "INFO" -Message "1. Essayez d'installer une version antérieure de Python (3.11 ou moins)."
Log-Message -Level "INFO" -Message "2. Vérifiez que Visual Studio avec les outils de développement C++ est correctement installé."
Log-Message -Level "INFO" -Message "3. Pour Python 3.13, JPype1 n'est peut-être pas encore officiellement compatible."
Log-Message -Level "INFO" -Message "4. Consultez la documentation de JPype1 pour plus d'informations: https://jpype.readthedocs.io/"

exit 1