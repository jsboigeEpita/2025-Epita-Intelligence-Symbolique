# Script d'installation de l'environnement du projet

param (
    [string]$Python310Path = "" # Chemin optionnel vers python.exe pour la version 3.10
)

# --- Configuration ---
$pythonVersion = "3.10"
$venvName = "venv_py310"
$jdkDir = "portable_jdk"
$jdkUrl = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_windows_hotspot_17.0.11_9.zip" # URL pour OpenJDK 17 LTS (ZIP Windows x64)
# Le nom du répertoire extrait du JDK peut varier, il sera déterminé dynamiquement.

$Global:FoundPython310Executable = "" # Variable globale pour stocker l'exécutable trouvé

# --- Fonctions Utilitaires ---
function Test-PythonVersion {
    param (
        [string]$version,
        [string]$explicitPath = ""
    )
    # 1. Essayer avec le chemin explicite s'il est fourni
    if (-not [string]::IsNullOrEmpty($explicitPath)) {
        if (Test-Path $explicitPath) {
            try {
                $output = & $explicitPath --version 2>&1
                if ($LASTEXITCODE -eq 0 -and $output -match $version) {
                    Write-Host "Python $version trouvé via chemin explicite: $explicitPath ($output)"
                    $Global:FoundPython310Executable = $explicitPath
                    return $true
                } else {
                    Write-Warning "Le chemin explicite $explicitPath ne pointe pas vers Python $version ou a échoué. ($output)"
                }
            } catch {
                Write-Warning "Erreur lors de la vérification de Python via chemin explicite $explicitPath. ($($_.Exception.Message))"
            }
        } else {
            Write-Warning "Chemin explicite $explicitPath non trouvé."
        }
    }

    # 2. Essayer avec py -version
    try {
        # Test plus robuste pour py.exe: exécuter une commande simple pour obtenir le chemin de l'exécutable
        $testCmdOutput = py "-$version" -c "import sys; print(sys.executable)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $actualVersionOutput = py "-$version" --version 2>&1 # Pour l'affichage
            Write-Host "Python $version trouvé via 'py -$version'. Exécutable: $testCmdOutput (Version: $actualVersionOutput)"
            $Global:FoundPython310Executable = "py -$version" # Marqueur spécial pour indiquer d'utiliser 'py -version'
            return $true
        } else {
            Write-Warning "Python $version non trouvé ou non exécutable via 'py -$version' (code de sortie pour test: $LASTEXITCODE)."
        }
    }
    catch {
        Write-Warning "Erreur lors de la vérification de Python $version avec 'py -$version'. ($($_.Exception.Message))"
    }

    # 3. Essayer avec python<version>
    $pythonExeName = "python$version"
    try {
        $output_alt = & $pythonExeName --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Python $version trouvé (via $pythonExeName): $output_alt"
            $Global:FoundPython310Executable = $pythonExeName
            return $true
        } else {
            Write-Warning "Python $version non trouvé (via $pythonExeName)."
        }
    }
    catch {
        Write-Warning "Erreur lors de la vérification de Python $version avec '$pythonExeName'. ($($_.Exception.Message))"
    }
    
    # 4. Tentative de détection pour l'utilisateur MYIA si $Python310Path (paramètre du script) n'a pas été fourni
    # et que les autres méthodes ont échoué.
    if ((-not $Global:FoundPython310Executable) -and `
        ([string]::IsNullOrEmpty($Python310Path)) -and `
        (-not [string]::IsNullOrEmpty($env:USERNAME)) -and `
        ($env:USERNAME -eq "MYIA")) {
        
        $defaultUserPath = "C:\Users\MYIA\AppData\Local\Programs\Python\Python$($version.Replace('.', ''))\python.exe"
        if (Test-Path $defaultUserPath) {
            Write-Host "Tentative de vérification avec le chemin par défaut pour l'utilisateur MYIA: $defaultUserPath"
            try {
                $output = & $defaultUserPath --version 2>&1
                if ($LASTEXITCODE -eq 0 -and $output -match $version) {
                    Write-Host "Python $version trouvé via chemin par défaut utilisateur MYIA: $defaultUserPath ($output)"
                    $Global:FoundPython310Executable = $defaultUserPath
                    return $true
                } else {
                     Write-Warning "Le chemin par défaut $defaultUserPath pour MYIA ne pointe pas vers Python $version ou a échoué. ($output)"
                }
            } catch {
                Write-Warning "Erreur lors de la vérification de Python via chemin par défaut MYIA $defaultUserPath. ($($_.Exception.Message))"
            }
        }
    }

    Write-Warning "Python $version non trouvé par les méthodes automatiques. Veuillez l'installer et l'ajouter au PATH, ou fournir le chemin via le paramètre -Python310Path."
    return $false
}

function Get-JdkSubDir {
    param (
        [string]$baseDir
    )
    $jdkSubDirs = Get-ChildItem -Path $baseDir -Directory | Where-Object {$_.Name -like "jdk-17*"}
    if ($jdkSubDirs.Count -eq 1) {
        return $jdkSubDirs[0].FullName
    } elseif ($jdkSubDirs.Count -gt 1) {
        Write-Warning "Plusieurs répertoires JDK trouvés dans $baseDir. Utilisation du premier: $($jdkSubDirs[0].FullName)"
        return $jdkSubDirs[0].FullName
    }
    else {
        return $null
    }
}

# --- Vérification Préalable de Python ---
Write-Host "Vérification de la présence de Python $pythonVersion..."
if (-not (Test-PythonVersion -version $pythonVersion -explicitPath $Python310Path)) {
    Write-Error "Python $pythonVersion n'est pas accessible. Veuillez l'installer, l'ajouter au PATH, ou spécifier le chemin via -Python310Path, puis relancez ce script."
    exit 1
}

# --- Téléchargement et Extraction du JDK Portable ---
Write-Host "Vérification du JDK portable..."
$extractedJdkPath = Get-JdkSubDir -baseDir (Join-Path $PSScriptRoot $jdkDir)

if (-not $extractedJdkPath) {
    Write-Host "JDK non trouvé dans $jdkDir. Téléchargement et extraction..."
    $tempDir = Join-Path $PSScriptRoot "_temp_jdk_download"
    $zipFilePath = Join-Path $tempDir "jdk.zip"

    if (-not (Test-Path $tempDir)) {
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
    }
    if (-not (Test-Path (Join-Path $PSScriptRoot $jdkDir))) {
        New-Item -ItemType Directory -Path (Join-Path $PSScriptRoot $jdkDir) -Force | Out-Null
    }

    try {
        Write-Host "Téléchargement du JDK depuis $jdkUrl vers $zipFilePath..."
        Invoke-WebRequest -Uri $jdkUrl -OutFile $zipFilePath
        Write-Host "JDK téléchargé."

        Write-Host "Extraction de $zipFilePath vers $($PSScriptRoot)\$jdkDir..."
        Expand-Archive -Path $zipFilePath -DestinationPath (Join-Path $PSScriptRoot $jdkDir) -Force
        Write-Host "JDK extrait."

        $extractedJdkPath = Get-JdkSubDir -baseDir (Join-Path $PSScriptRoot $jdkDir)
        if (-not $extractedJdkPath) {
            Write-Error "Impossible de déterminer le nom du répertoire JDK extrait dans $jdkDir."
            exit 1
        }
        Write-Host "JDK disponible dans : $extractedJdkPath"

    }
    catch {
        Write-Error "Une erreur s'est produite lors du téléchargement ou de l'extraction du JDK : $($_.Exception.Message)"
        exit 1
    }
    finally {
        if (Test-Path $zipFilePath) {
            Write-Host "Nettoyage du fichier ZIP téléchargé..."
            Remove-Item -Path $zipFilePath -Force
        }
        if (Test-Path $tempDir) {
            Remove-Item -Path $tempDir -Recurse -Force
        }
    }
} else {
    Write-Host "JDK portable déjà présent dans : $extractedJdkPath"
}
$finalJdkDirName = (Get-Item $extractedJdkPath).Name


Write-Host "Nettoyage des anciens répertoires d'environnements virtuels..."
if (Test-Path -Path ".\venv" -PathType Container) {
    Write-Host "Suppression de l'ancien répertoire .\venv..."
    Remove-Item -Recurse -Force ".\venv"
}
if (Test-Path -Path ".\.venv" -PathType Container) {
    Write-Host "Suppression de l'ancien répertoire .\.venv..."
    Remove-Item -Recurse -Force ".\.venv"
}
Write-Host "Nettoyage terminé."
# --- Création de l'Environnement Virtuel Python ---
$venvPath = Join-Path $PSScriptRoot $venvName
Write-Host "Vérification de l'environnement virtuel Python '$venvName'..."
if (-not (Test-Path $venvPath)) {
    Write-Host "Création de l'environnement virtuel Python '$venvName' avec Python $pythonVersion en utilisant '$Global:FoundPython310Executable'..."
    try {
        if ($Global:FoundPython310Executable -eq "py -$pythonVersion") {
            # Utiliser le Python Launcher si c'est ce qui a été trouvé
            py "-$pythonVersion" -m venv $venvPath
        } elseif ($Global:FoundPython310Executable -and (Test-Path $Global:FoundPython310Executable -PathType Leaf)) {
            # Utiliser le chemin direct vers l'exécutable s'il a été trouvé et est un fichier
            & $Global:FoundPython310Executable -m venv $venvPath
        } elseif ($Global:FoundPython310Executable) {
            # Cas où FoundPython310Executable pourrait être "python3.10" (nom de commande)
            & $Global:FoundPython310Executable -m venv $venvPath
        } else {
            # Ce cas ne devrait normalement pas être atteint à cause de la vérification préalable
            Write-Error "Aucun exécutable Python $pythonVersion valide n'a pu être déterminé pour créer l'environnement virtuel."
            exit 1
        }
        Write-Host "Environnement virtuel '$venvName' créé."
    }
    catch {
        Write-Error "Erreur lors de la création de l'environnement virtuel : $($_.Exception.Message)"
        exit 1
    }
} else {
    Write-Host "L'environnement virtuel '$venvName' existe déjà."
}

# --- Installation des Dépendances Python ---
Write-Host "Installation/Mise à jour des dépendances Python depuis requirements.txt..."
$pipPath = Join-Path -Path $venvPath -ChildPath "Scripts\pip.exe"
$pythonPathVenv = Join-Path -Path $venvPath -ChildPath "Scripts\python.exe"
$requirementsFile = Join-Path $PSScriptRoot "requirements.txt"

if (-not (Test-Path $requirementsFile)) {
    Write-Error "Le fichier requirements.txt est introuvable à la racine du projet."
    exit 1
}

try {
    # Utilisation directe de l'exécutable pip du venv
    Write-Host "Utilisation de $pipPath pour installer les dépendances."
    & $pipPath install -r $requirementsFile --upgrade
    Write-Host "Dépendances Python installées/mises à jour."
}
catch {
    Write-Error "Erreur lors de l'installation des dépendances Python : $($_.Exception.Message)"
    # Essayer d'activer et d'installer si l'appel direct échoue (moins probable mais pour robustesse)
    Write-Warning "Tentative d'installation après activation du venv..."
    try {
        $activateScript = Join-Path -Path $venvPath -ChildPath "Scripts\Activate.ps1"
        . $activateScript
        pip install -r $requirementsFile --upgrade
        deactivate # Si la fonction deactivate est disponible après l'activation
        Write-Host "Dépendances Python installées/mises à jour (via activation)."
    } catch {
         Write-Error "Échec de l'installation des dépendances même après tentative d'activation: $($_.Exception.Message)"
         exit 1
    }
}

# --- Création/Mise à jour du Fichier .env ---
$envTemplateFile = Join-Path $PSScriptRoot ".env.template"
$envFile = Join-Path $PSScriptRoot ".env"

Write-Host "Vérification du fichier .env..."
if (-not (Test-Path $envFile)) {
    if (Test-Path $envTemplateFile) {
        Write-Host "Copie de .env.template vers .env..."
        Copy-Item -Path $envTemplateFile -Destination $envFile -Force
    } else {
        Write-Warning "Le fichier .env.template est introuvable. Création d'un fichier .env vide."
        New-Item -Path $envFile -ItemType File -Force | Out-Null
    }
}

# Mise à jour de JAVA_HOME dans .env
Write-Host "Mise à jour de JAVA_HOME dans le fichier .env..."
$javaHomeLine = "JAVA_HOME=./$jdkDir/$finalJdkDirName" # Utilise des slashes pour la portabilité
$envContent = Get-Content $envFile -Raw
$javaHomeRegex = "(?m)^#?\s*JAVA_HOME=.*"

if ($envContent -match $javaHomeRegex) {
    Write-Host "JAVA_HOME trouvé, mise à jour de la ligne."
    $envContent = $envContent -replace $javaHomeRegex, $javaHomeLine
} else {
    Write-Host "JAVA_HOME non trouvé, ajout de la ligne."
    $envContent = $envContent + "`n" + $javaHomeLine
}
Set-Content -Path $envFile -Value $envContent -Force
Write-Host "Fichier .env mis à jour avec : $javaHomeLine"

# --- Instructions Finales ---
Write-Host ""
Write-Host "---------------------------------------------------------------------"
Write-Host "Installation de l'environnement terminée avec succès!"
Write-Host "Pour activer l'environnement, veuillez exécuter la commande suivante"
Write-Host "dans ce terminal ou dans un nouveau terminal PowerShell :"
Write-Host ""
Write-Host "    .\activate_project_env.ps1"
Write-Host "---------------------------------------------------------------------"