# Script PowerShell pour exécuter test_list_models.py avec CLASSPATH configuré
$ErrorActionPreference = "Stop"

Write-Host "--- Début de l'exécution de run_test_list_models.ps1 ---"

# Chemin vers la racine du projet (deux niveaux au-dessus du répertoire courant du script)
$ProjectRoot = (Get-Item -Path $PSScriptRoot).Parent.Parent.FullName
Write-Host "Racine du projet détectée : $ProjectRoot"

# Chemin vers le répertoire libs
$LibsDir = Join-Path -Path $ProjectRoot -ChildPath "libs"
Write-Host "Répertoire des bibliothèques (libs) : $LibsDir"

If (-not (Test-Path $LibsDir)) {
    Write-Error "Le répertoire des bibliothèques '$LibsDir' n'a pas été trouvé."
    exit 1
}

# Construire la chaîne CLASSPATH
$JarFiles = Get-ChildItem -Path $LibsDir -Filter *.jar | ForEach-Object { $_.FullName }
If ($JarFiles.Count -eq 0) {
    Write-Warning "Aucun fichier .jar trouvé dans '$LibsDir'. Le CLASSPATH sera vide."
    $Env:CLASSPATH = ""
} Else {
    $Env:CLASSPATH = $JarFiles -join [System.IO.Path]::PathSeparator
    Write-Host "CLASSPATH défini à : $($Env:CLASSPATH)"
}

# Chemin vers l'interpréteur Python de l'environnement virtuel
$PythonExe = Join-Path -Path $ProjectRoot -ChildPath ".venv\\Scripts\\python.exe"
If (-not (Test-Path $PythonExe)) {
    # Essayer l'alternative "venv" si ".venv" n'existe pas
    $PythonExe = Join-Path -Path $ProjectRoot -ChildPath "venv\\Scripts\\python.exe"
    If (-not (Test-Path $PythonExe)) {
        Write-Error "L'interpréteur Python de l'environnement virtuel n'a pas été trouvé à '$((Join-Path -Path $ProjectRoot -ChildPath ".venv\\Scripts\\python.exe"))' ou '$((Join-Path -Path $ProjectRoot -ChildPath "venv\\Scripts\\python.exe"))'."
        exit 1
    }
}
Write-Host "Utilisation de l'interpréteur Python : $PythonExe"

# Exécuter le script de test Python
$TestScript = Join-Path -Path $PSScriptRoot -ChildPath "test_list_models.py" # MODIFIÉ ICI
Write-Host "Exécution du script de test : $TestScript"

# Exécuter et capturer la sortie et les erreurs
Try {
    & $PythonExe $TestScript
    If ($LASTEXITCODE -ne 0) {
        Write-Error "Le script Python '$TestScript' a retourné le code d'erreur : $LASTEXITCODE"
    } Else {
        Write-Host "Le script Python '$TestScript' s'est terminé avec succès (code de sortie 0)."
    }
} Catch {
    Write-Error "Une erreur PowerShell est survenue lors de l'exécution du script Python : $_"
}

Write-Host "--- Fin de l'exécution de run_test_list_models.ps1 ---"