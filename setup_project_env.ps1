# Script d'installation de l'environnement du projet

param (
    [string]$Python310Path = "", # Chemin optionnel vers python.exe pour la version 3.10
    [switch]$NonInteractive = $false # Pour supprimer automatiquement les venv et l'environnement conda existant
)

# --- Configuration ---
$condaEnvName = "projet-is"
$environmentYmlFile = "environment.yml"

# Configuration JDK
$jdkDirNameOnly = "portable_jdk"
$jdkDir = Join-Path "libs" $jdkDirNameOnly
$jdkUrl = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_windows_hotspot_17.0.11_9.zip"

# NOUVEAU: Configuration Octave
$octaveDirNameOnly = "portable_octave"
$octaveDir = Join-Path "libs" $octaveDirNameOnly
$octaveVersionMajorMinor = "10.1.0" # Utilisé pour le nom du zip/dossier, ex: octave-10.1.0-w64
$octaveArch = "w64"
$octaveZipName = "octave-$($octaveVersionMajorMinor)-$($octaveArch).zip"
$octaveDownloadUrl = "https://ftp.gnu.org/gnu/octave/windows/$octaveZipName"
# Nom du dossier principal attendu dans le zip Octave
$octaveExtractedDirName = "octave-$($octaveVersionMajorMinor)-$($octaveArch)" 
$octaveTempDownloadDir = Join-Path "libs" "_temp_octave_download"


$Global:FoundPython310Executable = "" # Conservé pour la gestion du JDK/Octave si Python est nécessaire pour des scripts annexes hors Conda

# --- Fonctions Utilitaires ---

function Test-CondaInstallation {
    try {
        $condaInfo = conda --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $condaInfo -match "conda") {
            Write-Host "Conda est installé. Version: $condaInfo"
            return $true
        } else {
            Write-Warning "Conda ne semble pas être installé ou n'est pas dans le PATH. (conda --version a échoué ou n'a pas retourné 'conda')"
            return $false
        }
    }
    catch {
        Write-Warning "Erreur lors de la vérification de Conda : $($_.Exception.Message)"
        return $false
    }
}

function Test-PythonVersion {
    param (
        [string]$version,
        [string]$explicitPath = ""
    )
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
    try {
        $testCmdOutput = py "-$version" -c "import sys; print(sys.executable)" 2>&1
        if ($LASTEXITCODE -eq 0) {
            $actualVersionOutput = py "-$version" --version 2>&1
            Write-Host "Python $version trouvé via 'py -$version'. Exécutable: $testCmdOutput (Version: $actualVersionOutput)"
            $Global:FoundPython310Executable = "py -$version"
            return $true
        } else {
            Write-Warning "Python $version non trouvé ou non exécutable via 'py -$version' (code de sortie pour test: $LASTEXITCODE)."
        }
    }
    catch {
        Write-Warning "Erreur lors de la vérification de Python $version avec 'py -$version'. ($($_.Exception.Message))"
    }
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
    if (-not (Test-Path $baseDir)) {
        Write-Warning "Le répertoire de base pour Get-JdkSubDir '$baseDir' n'existe pas."
        return $null
    }
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

Write-Host ""
Write-Host "--- Nettoyage et déplacement des anciennes installations portables ---"
$libsDir = Join-Path $PSScriptRoot "libs"
if (-not (Test-Path $libsDir)) {
    Write-Host "Création du répertoire de bibliothèques: $libsDir..."
    New-Item -ItemType Directory -Path $libsDir -Force | Out-Null
}

function Move-Or-Clear-Old-Dir {
    param (
        [string]$oldDirNameAtRoot,
        [string]$newDirInLibsFullPath
    )
    $oldPathAtRoot = Join-Path $PSScriptRoot $oldDirNameAtRoot
    if (Test-Path $oldPathAtRoot) {
        if (Test-Path $newDirInLibsFullPath) {
            Write-Host "Le nouveau répertoire '$newDirInLibsFullPath' existe déjà. Suppression de l'ancien '$oldPathAtRoot'."
            Remove-Item -Path $oldPathAtRoot -Recurse -Force
        } else {
            Write-Host "Déplacement de '$oldPathAtRoot' vers '$newDirInLibsFullPath'..."
            Move-Item -Path $oldPathAtRoot -Destination $newDirInLibsFullPath -Force
        }
    } else {
        # Write-Host "L'ancien répertoire '$oldPathAtRoot' non trouvé, aucun déplacement/nettoyage nécessaire pour celui-ci."
    }
}

Move-Or-Clear-Old-Dir -oldDirNameAtRoot "portable_jdk" -newDirInLibsFullPath (Join-Path $PSScriptRoot $jdkDir)
Move-Or-Clear-Old-Dir -oldDirNameAtRoot "portable_octave" -newDirInLibsFullPath (Join-Path $PSScriptRoot $octaveDir)
Move-Or-Clear-Old-Dir -oldDirNameAtRoot "_temp_jdk_download" -newDirInLibsFullPath (Join-Path (Join-Path $PSScriptRoot "libs") "_temp_jdk_download")
Move-Or-Clear-Old-Dir -oldDirNameAtRoot "_temp" -newDirInLibsFullPath (Join-Path $PSScriptRoot $octaveTempDownloadDir)

Write-Host "Nettoyage et déplacement des anciennes installations terminés."
Write-Host "--- Fin Nettoyage ---"
Write-Host ""

Write-Host "Vérification de la présence de Conda..."
if (-not (Test-CondaInstallation)) {
    Write-Error "Conda n'est pas installé ou n'est pas accessible dans le PATH. Veuillez installer Conda (Miniconda ou Anaconda) et vous assurer qu'il est ajouté au PATH, puis relancez ce script."
    exit 1
}

# La vérification Python spécifique est moins critique si Conda gère Python,
# mais peut être conservée si des outils hors Conda en dépendent encore (ex: scripts de build spécifiques).
# Pour l'instant, on la commente car Conda va gérer Python.
# Write-Host "Vérification de la présence de Python $pythonVersion..."
# if (-not (Test-PythonVersion -version $pythonVersion -explicitPath $Python310Path)) {
#     Write-Error "Python $pythonVersion n'est pas accessible. Veuillez l'installer, l'ajouter au PATH, ou spécifier le chemin via -Python310Path, puis relancez ce script."
#     exit 1
# }

$fullJdkPath = Join-Path $PSScriptRoot $jdkDir
Write-Host "Vérification du JDK portable dans '$fullJdkPath'..."
$extractedJdkPath = Get-JdkSubDir -baseDir $fullJdkPath

if (-not $extractedJdkPath) {
    Write-Host "JDK non trouvé dans '$fullJdkPath'. Téléchargement et extraction..."
    $tempJdkDownloadDir = Join-Path $PSScriptRoot (Join-Path "libs" "_temp_jdk_download")
    $zipFilePath = Join-Path $tempJdkDownloadDir "jdk.zip"

    if (-not (Test-Path $tempJdkDownloadDir)) {
        New-Item -ItemType Directory -Path $tempJdkDownloadDir -Force | Out-Null
    }
    if (-not (Test-Path $fullJdkPath)) {
        New-Item -ItemType Directory -Path $fullJdkPath -Force | Out-Null
    }

    try {
        Write-Host "Téléchargement du JDK depuis $jdkUrl vers $zipFilePath..."
        Invoke-WebRequest -Uri $jdkUrl -OutFile $zipFilePath
        Write-Host "JDK téléchargé."
        Write-Host "Extraction de $zipFilePath vers '$fullJdkPath'..."
        Expand-Archive -Path $zipFilePath -DestinationPath $fullJdkPath -Force
        Write-Host "JDK extrait."
        $extractedJdkPath = Get-JdkSubDir -baseDir $fullJdkPath
        if (-not $extractedJdkPath) {
            Write-Error "Impossible de déterminer le nom du répertoire JDK extrait dans '$fullJdkPath'."
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
            Write-Host "Nettoyage du fichier ZIP téléchargé ($zipFilePath)..."
            Remove-Item -Path $zipFilePath -Force
        }
    }
} else {
    Write-Host "JDK portable déjà présent dans : $extractedJdkPath"
}
$finalJdkDirName = (Get-Item $extractedJdkPath).Name

# NOUVELLE SECTION: Téléchargement et Extraction d'Octave Portable
Write-Host ""
Write-Host "--- Configuration d'Octave Portable ---"
$fullOctaveDirPath = Join-Path $PSScriptRoot $octaveDir # ex: C:\projets\Epita\libs\portable_octave
$expectedOctaveCliPath = Join-Path $fullOctaveDirPath (Join-Path $octaveExtractedDirName "mingw64\bin\octave-cli.exe")

if (-not (Test-Path $expectedOctaveCliPath)) {
    Write-Host "Octave CLI non trouvé à '$expectedOctaveCliPath'. Tentative de téléchargement et extraction..."
    $fullOctaveTempDownloadDirPath = Join-Path $PSScriptRoot $octaveTempDownloadDir # ex: C:\projets\Epita\libs\_temp_octave_download
    $octaveZipFilePath = Join-Path $fullOctaveTempDownloadDirPath $octaveZipName

    if (-not (Test-Path $fullOctaveTempDownloadDirPath)) {
        New-Item -ItemType Directory -Path $fullOctaveTempDownloadDirPath -Force | Out-Null
    }
    if (-not (Test-Path $fullOctaveDirPath)) {
        New-Item -ItemType Directory -Path $fullOctaveDirPath -Force | Out-Null
    }

    try {
        if (-not (Test-Path $octaveZipFilePath)) {
            Write-Host "Téléchargement d'Octave depuis $octaveDownloadUrl vers $octaveZipFilePath..."
            Invoke-WebRequest -Uri $octaveDownloadUrl -OutFile $octaveZipFilePath
            Write-Host "Octave téléchargé."
        } else {
            Write-Host "Archive ZIP d'Octave déjà présente dans '$octaveZipFilePath'."
        }

        Write-Host "Extraction de '$octaveZipFilePath' vers '$fullOctaveDirPath'..."
        Expand-Archive -Path $octaveZipFilePath -DestinationPath $fullOctaveDirPath -Force
        Write-Host "Octave extrait."

        if (-not (Test-Path $expectedOctaveCliPath)) {
            Write-Warning "Octave CLI toujours introuvable à '$expectedOctaveCliPath' après extraction. Vérifiez le nom du répertoire extrait ('$octaveExtractedDirName') et la structure de l'archive. Certaines fonctionnalités pourraient ne pas être disponibles."
        } else {
            Write-Host "Octave portable disponible et CLI trouvé à : $expectedOctaveCliPath"
        }
    }
    catch {
        Write-Warning "Une erreur s'est produite lors du téléchargement ou de l'extraction d'Octave : $($_.Exception.Message)"
        Write-Warning "Octave ne sera peut-être pas disponible."
    }
    # Optionnel: supprimer le zip d'Octave après extraction
    # finally { if (Test-Path $octaveZipFilePath) { Remove-Item -Path $octaveZipFilePath -Force } }
} else {
    Write-Host "Octave portable déjà présent et CLI trouvé à : $expectedOctaveCliPath"
}
Write-Host "--- Fin Configuration Octave ---"
# FIN NOUVELLE SECTION OCTAVE

Write-Host "Nettoyage des anciens répertoires d'environnements virtuels (venv)..."
$oldVenvDirs = @("venv", ".venv", "venv_py310") # Ajoutez d'autres noms si nécessaire
foreach ($dirName in $oldVenvDirs) {
    $fullOldVenvPath = Join-Path $PSScriptRoot $dirName
    if (Test-Path -Path $fullOldVenvPath -PathType Container) {
        if ($NonInteractive) {
            Write-Host "Mode non interactif : Suppression automatique de l'ancien répertoire $fullOldVenvPath..."
            try {
                Remove-Item -Recurse -Force $fullOldVenvPath -ErrorAction Stop
                Write-Host "Répertoire $fullOldVenvPath supprimé."
            } catch {
                Write-Warning "Impossible de supprimer complètement $fullOldVenvPath. Erreur: $($_.Exception.Message)"
                Write-Warning "Vous devrez peut-être le supprimer manuellement."
            }
        } else {
            $confirmation = Read-Host "L'ancien répertoire d'environnement virtuel '$dirName' a été trouvé. Voulez-vous le supprimer ? (O/N)"
            if ($confirmation -eq 'O' -or $confirmation -eq 'o') {
                Write-Host "Suppression de l'ancien répertoire $fullOldVenvPath..."
                try {
                    Remove-Item -Recurse -Force $fullOldVenvPath -ErrorAction Stop
                    Write-Host "Répertoire $fullOldVenvPath supprimé."
                } catch {
                    Write-Warning "Impossible de supprimer complètement $fullOldVenvPath. Erreur: $($_.Exception.Message)"
                    Write-Warning "Vous devrez peut-être le supprimer manuellement."
                }
            } else {
                Write-Host "Le répertoire '$fullOldVenvPath' n'a pas été supprimé."
            }
        }
    }
}
Write-Host "Nettoyage des anciens venv terminé."

Write-Host ""
Write-Host "--- Configuration de l'environnement Conda '$condaEnvName' ---"

# Vérifier si l'environnement Conda existe déjà et demander s'il faut le supprimer pour une installation propre
$condaEnvExistsForCleanup = conda env list | Select-String -Pattern "\s$condaEnvName\s" -Quiet
if ($condaEnvExistsForCleanup) {
    if ($NonInteractive) {
        Write-Host "Mode non interactif : Suppression automatique de l'environnement Conda '$condaEnvName'..."
        try {
            conda env remove --name $condaEnvName -y
            if ($LASTEXITCODE -ne 0) {
                Write-Warning "La suppression de l'environnement Conda '$condaEnvName' a rencontré un problème. Il se peut qu'il ne soit pas complètement supprimé."
            } else {
                Write-Host "Environnement Conda '$condaEnvName' supprimé."
            }
        } catch {
            Write-Warning "Une exception s'est produite lors de la suppression de l'environnement Conda '$condaEnvName': $($_.Exception.Message)"
        }
    } else {
        $cleanupConfirmation = Read-Host "L'environnement Conda '$condaEnvName' existe déjà. Voulez-vous le supprimer pour une installation propre ? (O/N)"
        if ($cleanupConfirmation -eq 'O' -or $cleanupConfirmation -eq 'o') {
            Write-Host "Suppression de l'environnement Conda '$condaEnvName'..."
            try {
                conda env remove --name $condaEnvName -y
                if ($LASTEXITCODE -ne 0) {
                    Write-Warning "La suppression de l'environnement Conda '$condaEnvName' a rencontré un problème. Il se peut qu'il ne soit pas complètement supprimé."
                } else {
                    Write-Host "Environnement Conda '$condaEnvName' supprimé."
                }
            } catch {
                Write-Warning "Une exception s'est produite lors de la suppression de l'environnement Conda '$condaEnvName': $($_.Exception.Message)"
            }
        } else {
            Write-Host "L'environnement Conda '$condaEnvName' ne sera pas supprimé. Le script tentera une mise à jour."
        }
    }
}

$envFilePath = Join-Path $PSScriptRoot $environmentYmlFile
if (-not (Test-Path $envFilePath)) {
    Write-Error "Le fichier d'environnement '$environmentYmlFile' est introuvable à la racine du projet: $envFilePath"
    exit 1
}

# Forcer la suppression de l'environnement Conda en mode non interactif pour assurer un état propre
if ($NonInteractive) {
    Write-Host "Mode non interactif : Tentative de suppression préalable de l'environnement Conda '$condaEnvName' pour assurer un état propre..."
    try {
        conda env remove --name $condaEnvName -y
        if ($LASTEXITCODE -ne 0) {
            Write-Warning "La suppression préalable de l'environnement Conda '$condaEnvName' a rencontré un problème (Code: $LASTEXITCODE). Cela peut être normal s'il n'existait pas."
        } else {
            Write-Host "Environnement Conda '$condaEnvName' supprimé (ou n'existait pas)."
        }
    } catch {
        Write-Warning "Une exception s'est produite lors de la tentative de suppression préalable de l'environnement Conda '$condaEnvName': $($_.Exception.Message)"
    }
}

# Vérifier si l'environnement Conda existe déjà
$condaEnvList = conda env list | Select-String -Pattern "\s$condaEnvName\s" -Quiet
if ($condaEnvList) {
    Write-Host "L'environnement Conda '$condaEnvName' existe déjà. Mise à jour..."
    try {
        conda env update --name $condaEnvName --file $envFilePath --prune
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Erreur lors de la mise à jour de l'environnement Conda '$condaEnvName'. Vérifiez les messages ci-dessus."
            exit 1
        }
        Write-Host "Environnement Conda '$condaEnvName' mis à jour avec succès."
    }
    catch {
        Write-Error "Une exception s'est produite lors de la mise à jour de l'environnement Conda '$condaEnvName': $($_.Exception.Message)"
        exit 1
    }
} else {
    Write-Host "L'environnement Conda '$condaEnvName' n'existe pas. Création..."
    try {
        conda env create -f $envFilePath
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Erreur lors de la création de l'environnement Conda '$condaEnvName'. Vérifiez les messages ci-dessus."
            # Tenter de supprimer un environnement potentiellement partiellement créé
            Write-Warning "Tentative de suppression de l'environnement '$condaEnvName' suite à l'échec de la création..."
            conda env remove --name $condaEnvName -y
            exit 1
        }
        Write-Host "Environnement Conda '$condaEnvName' créé avec succès."
    }
    catch {
        Write-Error "Une exception s'est produite lors de la création de l'environnement Conda '$condaEnvName': $($_.Exception.Message)"
        exit 1
    }
}
Write-Host "--- Fin Configuration Conda ---"
Write-Host ""

# La section d'installation des dépendances via pip est maintenant gérée par Conda et environment.yml
# $pipPath = Join-Path -Path $venvPath -ChildPath "Scripts\pip.exe"
# $requirementsFile = Join-Path $PSScriptRoot "requirements.txt"
# if (-not (Test-Path $requirementsFile)) {
#     Write-Error "Le fichier requirements.txt est introuvable à la racine du projet."
#     exit 1
# }
# try {
#     Write-Host "Utilisation de $pipPath pour installer les dépendances."
#     & $pipPath install -r $requirementsFile --upgrade
#     Write-Host "Dépendances Python installées/mises à jour."
# }
# catch {
#     Write-Error "Erreur lors de l'installation des dépendances Python : $($_.Exception.Message)"
#     Write-Warning "Tentative d'installation après activation du venv..."
#     try {
#         $activateVenvScriptForPip = Join-Path -Path $venvPath -ChildPath "Scripts\Activate.ps1"
#         . $activateVenvScriptForPip
#         pip install -r $requirementsFile --upgrade
#         if (Get-Command deactivate -ErrorAction SilentlyContinue) { deactivate }
#         Write-Host "Dépendances Python installées/mises à jour (via activation)."
#     } catch {
#          Write-Error "Échec de l'installation des dépendances même après tentative d'activation: $($_.Exception.Message)"
#          exit 1
#     }
# }

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

Write-Host "Mise à jour de JAVA_HOME dans le fichier .env..."
$correctRelativeJdkPath = "$(($jdkDir).TrimStart('\').TrimStart('/'))/$finalJdkDirName" -replace '\\', '/'
$javaHomeLine = "JAVA_HOME=./$correctRelativeJdkPath"
$envContent = Get-Content $envFile -Raw
$javaHomeRegex = "(?m)^#?\s*JAVA_HOME=.*"
if ($envContent -match $javaHomeRegex) {
    Write-Host "JAVA_HOME trouvé, mise à jour de la ligne."
    $envContent = $envContent -replace $javaHomeRegex, $javaHomeLine
} else {
    Write-Host "JAVA_HOME non trouvé, ajout de la ligne."
    if ($envContent -and $envContent[-1] -ne "`n" -and $envContent[-1] -ne "`r") {
        $envContent = $envContent + "`n"
    }
    $envContent = $envContent + $javaHomeLine
}
Set-Content -Path $envFile -Value $envContent -Force
Write-Host "Fichier .env mis à jour avec : $javaHomeLine"

Write-Host "Mise à jour de USE_REAL_JPYPE dans le fichier .env..."
$useRealJpypeLine = "USE_REAL_JPYPE=true"
# $envContent a déjà été lu pour JAVA_HOME, mais relisons-le au cas où pour être sûr
$envContent = Get-Content $envFile -Raw
$useRealJpypeRegex = "(?m)^#?\s*USE_REAL_JPYPE=.*"

if ($envContent -match $useRealJpypeRegex) {
    Write-Host "USE_REAL_JPYPE trouvé, mise à jour de la ligne pour s'assurer qu'il est à 'true' et non commenté."
    $envContent = $envContent -replace $useRealJpypeRegex, $useRealJpypeLine
} else {
    Write-Host "USE_REAL_JPYPE non trouvé, ajout de la ligne."
    # S'assurer qu'il y a un retour à la ligne si le fichier n'est pas vide et ne termine pas par un newline
    if ($envContent -and $envContent.Length -gt 0 -and $envContent[-1] -ne "`n" -and $envContent[-1] -ne "`r") {
        $envContent = $envContent + [System.Environment]::NewLine
    }
    $envContent = $envContent + $useRealJpypeLine
}
Set-Content -Path $envFile -Value $envContent -Force -Encoding UTF8 # Spécifier l'encodage pour la cohérence
Write-Host "Fichier .env mis à jour concernant USE_REAL_JPYPE."

# La section d'activation de venv est remplacée par des instructions pour Conda.
# L'activation de Conda ne se fait pas de la même manière programmatiquement dans un script
# de manière persistante pour la session appelante sans hacks.
# Il est préférable d'instruire l'utilisateur.

# MODIFIÉ: Instructions Finales
Write-Host ""
Write-Host "---------------------------------------------------------------------"
Write-Host "Installation et configuration de l'environnement Conda '$condaEnvName' terminées!"
Write-Host "---------------------------------------------------------------------"
Write-Host ""
Write-Host "Appel du script d'activation (activate_project_env.ps1) pour exécuter 'pip install -e .' dans l'environnement..."
Write-Host ""

# Exécute pip install -e . dans l'environnement Conda via activate_project_env.ps1
$pipInstallCommand = "pip install -e ."
$activateScriptPath = Join-Path $PSScriptRoot "activate_project_env.ps1"
try {
    Write-Host "Exécution de: powershell -File $activateScriptPath -CommandToRun '$pipInstallCommand'"
    # Utiliser powershell -File pour s'assurer que le script est exécuté dans un nouveau scope
    # et que -CommandToRun est bien passé.
    powershell -File $activateScriptPath -CommandToRun $pipInstallCommand
    if ($LASTEXITCODE -ne 0) {
        Write-Error "L'exécution de '$pipInstallCommand' via activate_project_env.ps1 a échoué avec le code $LASTEXITCODE."
    } else {
        Write-Host "'$pipInstallCommand' exécuté avec succès via activate_project_env.ps1."
    }
} catch {
    Write-Error "Une exception s'est produite lors de l'appel à activate_project_env.ps1 pour '$pipInstallCommand': $($_.Exception.Message)"
}

Write-Host ""
Write-Host "Fin du script setup_project_env.ps1."
Write-Host "L'environnement '$condaEnvName' devrait être configuré et le projet installé en mode édition."
Write-Host "Pour utiliser l'environnement, activez-le dans un nouveau terminal :"
Write-Host "    conda activate $condaEnvName"
Write-Host "Ou utilisez directement activate_project_env.ps1 avec le paramètre -CommandToRun pour vos commandes."
Write-Host "---------------------------------------------------------------------"