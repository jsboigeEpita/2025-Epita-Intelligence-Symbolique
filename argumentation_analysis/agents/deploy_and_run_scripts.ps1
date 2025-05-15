# Script PowerShell pour déployer et exécuter les scripts d'encryption dans le répertoire parent

# Définir les chemins
$currentDir = Get-Location
$parentDir = (Get-Item $currentDir).Parent.FullName

# Afficher les informations
Write-Host "\n=== Déploiement et exécution des scripts d'encryption ===\n"
Write-Host "Répertoire courant: $currentDir"
Write-Host "Répertoire parent: $parentDir"

# Liste des fichiers à copier
$filesToCopy = @(
    "create_complete_encrypted_config.py",
    "load_complete_encrypted_config.py",
    "cleanup_after_encryption.py",
    "create_and_archive_encrypted_config.py"
)

# Copier les fichiers vers le répertoire parent
Write-Host "\n--- Copie des fichiers vers le répertoire parent ---\n"
foreach ($file in $filesToCopy) {
    $sourcePath = Join-Path -Path $currentDir -ChildPath $file
    $destPath = Join-Path -Path $parentDir -ChildPath $file
    
    if (Test-Path $sourcePath) {
        Copy-Item -Path $sourcePath -Destination $destPath -Force
        Write-Host "✅ Fichier '$file' copié vers '$destPath'"
    } else {
        Write-Host "❌ Erreur: Le fichier '$file' n'existe pas dans '$currentDir'"
    }
}

# Vérifier si le fichier de cache du Kremlin existe
$kremlinCachePath = Join-Path -Path $parentDir -ChildPath "text_cache\4cf2d4853745719f6504a54610237738ad016de4f64176c3e8f5218f8fd2c01b.txt"
if (-not (Test-Path $kremlinCachePath)) {
    Write-Host "\n--- Création du fichier de cache du Kremlin ---\n"
    $createKremlinCachePath = Join-Path -Path $currentDir -ChildPath "create_kremlin_cache.py"
    
    # Exécuter le script depuis le répertoire parent
    Push-Location $parentDir
    try {
        python $createKremlinCachePath
    } catch {
        Write-Host "❌ Erreur lors de l'exécution du script 'create_kremlin_cache.py': $_"
    }
    Pop-Location
} else {
    Write-Host "\n✅ Le fichier de cache du Kremlin existe déjà: '$kremlinCachePath'"
}

# Demander à l'utilisateur s'il souhaite exécuter le script principal
$runScript = Read-Host "\nSouhaitez-vous exécuter le script principal d'encryption? (o/n)"
if ($runScript -eq "o" -or $runScript -eq "oui" -or $runScript -eq "y" -or $runScript -eq "yes") {
    Write-Host "\n--- Exécution du script principal ---\n"
    $mainScriptPath = Join-Path -Path $parentDir -ChildPath "create_and_archive_encrypted_config.py"
    
    # Exécuter le script depuis le répertoire parent
    Push-Location $parentDir
    try {
        python $mainScriptPath
    } catch {
        Write-Host "❌ Erreur lors de l'exécution du script principal: $_"
    }
    Pop-Location
} else {
    Write-Host "\nLe script principal n'a pas été exécuté."
}

# Demander à l'utilisateur s'il souhaite supprimer les scripts du répertoire agents
$cleanupScripts = Read-Host "\nSouhaitez-vous supprimer les scripts du répertoire 'agents'? (o/n)"
if ($cleanupScripts -eq "o" -or $cleanupScripts -eq "oui" -or $cleanupScripts -eq "y" -or $cleanupScripts -eq "yes") {
    Write-Host "\n--- Suppression des scripts du répertoire 'agents' ---\n"
    foreach ($file in $filesToCopy) {
        $filePath = Join-Path -Path $currentDir -ChildPath $file
        
        if (Test-Path $filePath) {
            Remove-Item -Path $filePath -Force
            Write-Host "✅ Fichier '$file' supprimé de '$currentDir'"
        }
    }
} else {
    Write-Host "\nLes scripts n'ont pas été supprimés du répertoire 'agents'."
}

Write-Host "\n=== Opération terminée ===\n"
Write-Host "Pour exécuter le script principal manuellement, utilisez la commande suivante depuis le répertoire parent:"
Write-Host "python create_and_archive_encrypted_config.py"
