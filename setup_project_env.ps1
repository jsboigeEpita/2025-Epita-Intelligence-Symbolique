# Script d'installation de l'environnement du projet

# --- Configuration ---
$pythonVersion = "3.10"
$venvName = "venv_py310"
$jdkDir = "portable_jdk"
$jdkUrl = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_windows_hotspot_17.0.11_9.zip" # URL pour OpenJDK 17 LTS (ZIP Windows x64)
# Le nom du répertoire extrait du JDK peut varier, il sera déterminé dynamiquement.

# --- Fonctions Utilitaires ---
function Test-PythonVersion {
    param (
        [string]$version
    )
    try {
        $output = py "-$version" --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Python $version trouvé : $output"
            return $true
        } else {
            Write-Warning "Python $version non trouvé ou n'est pas dans le PATH. Tentative avec python$version..."
            $output_alt = python$version --version 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "Python $version trouvé (via python$version): $output_alt"
                return $true
            } else {
                Write-Warning "Python $version non trouvé (via python$version). Veuillez l'installer et l'ajouter au PATH."
                return $false
            }
        }
    }
    catch {
        Write-Warning "Erreur lors de la vérification de Python $version. Veuillez l'installer et l'ajouter au PATH."
        return $false
    }
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
if (-not (Test-PythonVersion -version $pythonVersion)) {
    Write-Error "Python $pythonVersion n'est pas accessible. Veuillez l'installer et l'ajouter au PATH, puis relancez ce script."
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


# --- Création de l'Environnement Virtuel Python ---
$venvPath = Join-Path $PSScriptRoot $venvName
Write-Host "Vérification de l'environnement virtuel Python '$venvName'..."
if (-not (Test-Path $venvPath)) {
    Write-Host "Création de l'environnement virtuel Python '$venvName' avec Python $pythonVersion..."
    try {
        py "-$pythonVersion" -m venv $venvPath
        # Alternative si py -version ne fonctionne pas mais python<version> oui
        # & "python$pythonVersion" -m venv $venvPath
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