# Script d'installation de l'environnement du projet

param (
    [string]$Python310Path = "" # Chemin optionnel vers python.exe pour la version 3.10
)

# --- Configuration ---
$pythonVersion = "3.10"
$venvName = "venv_py310"

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


$Global:FoundPython310Executable = ""

# --- Fonctions Utilitaires ---
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

Write-Host "Vérification de la présence de Python $pythonVersion..."
if (-not (Test-PythonVersion -version $pythonVersion -explicitPath $Python310Path)) {
    Write-Error "Python $pythonVersion n'est pas accessible. Veuillez l'installer, l'ajouter au PATH, ou spécifier le chemin via -Python310Path, puis relancez ce script."
    exit 1
}

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

$venvPath = Join-Path $PSScriptRoot $venvName
Write-Host "Vérification de l'environnement virtuel Python '$venvName'..."
if (-not (Test-Path $venvPath)) {
    Write-Host "Création de l'environnement virtuel Python '$venvName' avec Python $pythonVersion en utilisant '$Global:FoundPython310Executable'..."
    try {
        if ($Global:FoundPython310Executable -eq "py -$pythonVersion") {
            py "-$pythonVersion" -m venv $venvPath
        } elseif ($Global:FoundPython310Executable -and (Test-Path $Global:FoundPython310Executable -PathType Leaf)) {
            & $Global:FoundPython310Executable -m venv $venvPath
        } elseif ($Global:FoundPython310Executable) {
            & $Global:FoundPython310Executable -m venv $venvPath
        } else {
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

Write-Host "Installation/Mise à jour des dépendances Python depuis requirements.txt..."
$pipPath = Join-Path -Path $venvPath -ChildPath "Scripts\pip.exe"
$requirementsFile = Join-Path $PSScriptRoot "requirements.txt"
if (-not (Test-Path $requirementsFile)) {
    Write-Error "Le fichier requirements.txt est introuvable à la racine du projet."
    exit 1
}
try {
    Write-Host "Utilisation de $pipPath pour installer les dépendances."
    & $pipPath install -r $requirementsFile --upgrade
    Write-Host "Dépendances Python installées/mises à jour."
}
catch {
    Write-Error "Erreur lors de l'installation des dépendances Python : $($_.Exception.Message)"
    Write-Warning "Tentative d'installation après activation du venv..."
    try {
        $activateVenvScriptForPip = Join-Path -Path $venvPath -ChildPath "Scripts\Activate.ps1"
        . $activateVenvScriptForPip
        pip install -r $requirementsFile --upgrade
        if (Get-Command deactivate -ErrorAction SilentlyContinue) { deactivate }
        Write-Host "Dépendances Python installées/mises à jour (via activation)."
    } catch {
         Write-Error "Échec de l'installation des dépendances même après tentative d'activation: $($_.Exception.Message)"
         exit 1
    }
}

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

# NOUVEAU: Activation de l'environnement virtuel
Write-Host ""
Write-Host "--- Activation de l'environnement virtuel ---"
$activateVenvScriptPath = Join-Path $PSScriptRoot (Join-Path $venvName "Scripts\Activate.ps1")
if (Test-Path $activateVenvScriptPath) {
    try {
        Write-Host "Tentative d'activation de l'environnement virtuel '$venvName' via: $activateVenvScriptPath"
        . $activateVenvScriptPath
        Write-Host "Environnement virtuel '$venvName' activé pour cette session PowerShell."
        Write-Host "Le prompt devrait maintenant indiquer ($venvName). Vérifiez le prompt après l'exécution du script."
    } catch {
        Write-Warning "Échec de l'activation de l'environnement virtuel '$venvName': $($_.Exception.Message)"
        Write-Warning "Vous devrez peut-être l'activer manuellement : . $activateVenvScriptPath"
    }
} else {
    Write-Warning "Script d'activation '$activateVenvScriptPath' non trouvé. L'environnement n'a pas pu être activé automatiquement."
}
Write-Host "--- Fin Activation ---"

# MODIFIÉ: Instructions Finales
Write-Host ""
Write-Host "---------------------------------------------------------------------"
Write-Host "Installation et configuration de l'environnement terminées!"
Write-Host "Le script a tenté d'activer l'environnement virtuel '$venvName'."
Write-Host "Si votre prompt n'indique pas '($venvName)', vous pouvez l'activer"
Write-Host "manuellement dans votre session PowerShell actuelle en exécutant :"
Write-Host ""
Write-Host "    . (Join-Path \$PSScriptRoot '$venvName\Scripts\Activate.ps1')"
Write-Host ""
Write-Host "Alternativement, le script '.\activate_project_env.ps1' (s'il existe et est configuré)"
Write-Host "peut aussi être utilisé pour activer l'environnement dans une nouvelle session ou la session courante."
Write-Host "---------------------------------------------------------------------"