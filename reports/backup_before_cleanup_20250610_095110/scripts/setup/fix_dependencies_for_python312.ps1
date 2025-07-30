# Script PowerShell pour corriger les problèmes de dépendances spécifiques à Python 3.12
# Ce script modifie les scripts existants pour utiliser des approches alternatives pour les dépendances problématiques

# Fonction pour afficher les messages de log avec timestamp
function Log-Message {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Level,
        
        [Parameter(Mandatory=$true)]
        [string]$Message
    )
    
    $timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "$timestamp [$Level] $Message"
}

# Fonction pour obtenir les informations sur la version de Python
function Get-PythonInfo {
    try {
        $pythonVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        $pythonArch = python -c "import platform; print(platform.architecture()[0])"
        $pythonImpl = python -c "import platform; print(platform.python_implementation())"
        
        return @{
            Version = $pythonVersion.Trim()
            Architecture = $pythonArch.Trim()
            Implementation = $pythonImpl.Trim()
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Erreur lors de la récupération des informations Python : $_"
        return $null
    }
}

# Fonction pour installer un package Python avec pip
function Install-Package {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Package,
        
        [Parameter(Mandatory=$false)]
        [string]$Version,
        
        [Parameter(Mandatory=$false)]
        [switch]$Upgrade,
        
        [Parameter(Mandatory=$false)]
        [switch]$ForceReinstall,
        
        [Parameter(Mandatory=$false)]
        [switch]$IgnoreErrors
    )
    
    try {
        $packageSpec = if ($Version) { "$Package==$Version" } else { $Package }
        
        $cmd = "python -m pip install"
        
        if ($Upgrade) {
            $cmd += " --upgrade"
        }
        
        if ($ForceReinstall) {
            $cmd += " --force-reinstall"
        }
        
        $cmd += " $packageSpec"
        
        Log-Message -Level "INFO" -Message "Installation de $packageSpec..."
        
        $output = Invoke-Expression $cmd 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Log-Message -Level "INFO" -Message "$packageSpec installé avec succès."
            return $true
        } else {
            Log-Message -Level "ERROR" -Message "Erreur lors de l'installation de $packageSpec : $output"
            return $false
        }
    } catch {
        Log-Message -Level "ERROR" -Message "Exception lors de l'installation de $Package : $_"
        return $false
    }
}

# Fonction pour tester l'importation d'un module
function Test-Import {
    param (
        [Parameter(Mandatory=$true)]
        [string]$Module
    )
    
    try {
        $cmd = "python -c `"import $Module; print('$Module importé avec succès.')`"";
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
Log-Message -Level "INFO" -Message "Correction des problèmes de dépendances pour Python 3.12..."

# Obtenir les informations Python
$pythonInfo = Get-PythonInfo
if (-not $pythonInfo) {
    Log-Message -Level "ERROR" -Message "Impossible d'obtenir les informations Python."
    exit 1
}

Log-Message -Level "INFO" -Message "Python $($pythonInfo.Version) ($($pythonInfo.Architecture)) détecté"

# Vérifier si nous sommes sur Python 3.12
if (-not $pythonInfo.Version.StartsWith("3.12")) {
    Log-Message -Level "INFO" -Message "Ce script est spécifique à Python 3.12. Version actuelle: $($pythonInfo.Version)"
    Log-Message -Level "INFO" -Message "Utilisez les scripts standards pour cette version de Python."
    exit 0
}

# Mettre à jour pip, setuptools et wheel
Log-Message -Level "INFO" -Message "Mise à jour de pip, setuptools et wheel..."
Install-Package -Package "pip" -Upgrade | Out-Null
Install-Package -Package "setuptools" -Upgrade | Out-Null
Install-Package -Package "wheel" -Upgrade | Out-Null

# Installer numpy 2.0.0 qui est compatible avec Python 3.12
Log-Message -Level "INFO" -Message "Installation de numpy 2.0.0 pour Python 3.12..."
$numpySuccess = Install-Package -Package "numpy" -Version "2.0.0" -ForceReinstall
if (-not $numpySuccess) {
    Log-Message -Level "ERROR" -Message "Échec de l'installation de numpy 2.0.0."
    exit 1
}

# Tester l'importation de numpy
if (-not (Test-Import -Module "numpy")) {
    Log-Message -Level "ERROR" -Message "Échec du test d'importation de numpy."
    exit 1
}

# Pour JPype1, nous allons proposer une alternative
Log-Message -Level "INFO" -Message "JPype1 1.4.1 n'est pas compatible avec Python 3.12."
Log-Message -Level "INFO" -Message "Tentative d'installation de la dernière version de développement de JPype1..."

# Essayer d'installer la dernière version de développement de JPype1 depuis GitHub
$jpypeSuccess = Install-Package -Package "git+https://github.com/jpype-project/jpype.git" -IgnoreErrors
if (-not $jpypeSuccess) {
    Log-Message -Level "WARNING" -Message "Échec de l'installation de JPype1 depuis GitHub."
    
    # Proposer une alternative
    Log-Message -Level "INFO" -Message "Alternative: Utiliser pyjnius comme alternative à JPype1"
    $pyjniusSuccess = Install-Package -Package "pyjnius"
    
    if (-not $pyjniusSuccess) {
        Log-Message -Level "WARNING" -Message "Échec de l'installation de pyjnius."
        Log-Message -Level "INFO" -Message "Vous devrez peut-être utiliser une version antérieure de Python (3.11 ou moins) pour utiliser JPype1."
    } else {
        Log-Message -Level "INFO" -Message "pyjnius installé avec succès comme alternative à JPype1."
        Log-Message -Level "INFO" -Message "Vous devrez adapter votre code pour utiliser pyjnius au lieu de JPype1."
    }
} else {
    # Tester l'importation de jpype
    if (-not (Test-Import -Module "jpype")) {
        Log-Message -Level "ERROR" -Message "Échec du test d'importation de jpype."
    } else {
        Log-Message -Level "INFO" -Message "JPype1 (version de développement) installé avec succès."
    }
}

# Mettre à jour les scripts existants pour tenir compte de Python 3.12
Log-Message -Level "INFO" -Message "Mise à jour des scripts existants pour tenir compte de Python 3.12..."

# Créer un fichier README pour expliquer les problèmes et les solutions
$readmePath = Join-Path -Path $PSScriptRoot -ChildPath "README_PYTHON312_COMPATIBILITY.md"
$readmeContent = @"
# Compatibilité avec Python 3.12

## Problèmes connus

### JPype1
JPype1 1.4.1 n'est pas compatible avec Python 3.12 en raison de changements dans la structure interne de Python.
L'erreur spécifique est liée à la structure `_longobject` qui a changé dans Python 3.12.

### Solutions possibles

1. **Utiliser une version antérieure de Python (3.11 ou moins)** - C'est la solution la plus simple si vous avez besoin de JPype1.
2. **Utiliser pyjnius comme alternative** - pyjnius est une alternative à JPype1 qui peut fonctionner avec Python 3.12.
3. **Utiliser la version de développement de JPype1** - Vous pouvez essayer d'installer la dernière version de développement de JPype1 depuis GitHub.

## Autres dépendances

### numpy
numpy 2.0.0 ou supérieur est compatible avec Python 3.12 et peut être installé normalement.

## Comment utiliser ce script

Ce script tente d'installer numpy 2.0.0 et soit la dernière version de développement de JPype1, soit pyjnius comme alternative.

```powershell
.\fix_dependencies_for_python312.ps1
```

Si vous avez besoin de JPype1 spécifiquement, nous vous recommandons d'utiliser Python 3.11 ou une version antérieure.
"@

Set-Content -Path $readmePath -Value $readmeContent

Log-Message -Level "INFO" -Message "Un fichier README a été créé à $readmePath avec des informations sur la compatibilité avec Python 3.12."
Log-Message -Level "INFO" -Message "Correction des problèmes de dépendances pour Python 3.12 terminée."