# Script pour créer des fichiers README.md dans les sous-répertoires de tests

$baseDir = "d:/2025-Epita-Intelligence-Symbolique-4/tests"

# Lister tous les sous-répertoires de manière récursive
$subdirectories = Get-ChildItem -Path $baseDir -Recurse -Directory

foreach ($dir in $subdirectories) {
    $readmePath = Join-Path -Path $dir.FullName -ChildPath "README.md"

    # Vérifier si le README.md existe
    if (-not (Test-Path -Path $readmePath)) {
        Write-Host "Création du fichier README.md dans $($dir.FullName)"

        # Générer le contenu du README.md
        $readmeContent = "# Répertoire de Tests : $($dir.Name)`n`n"
        $readmeContent += "Ce répertoire contient les tests pour $($dir.Name).`n`n"
        $readmeContent += "## Fichiers de test`n`n"

        # Lister les fichiers de test dans le répertoire
        $testFiles = Get-ChildItem -Path $dir.FullName -Filter "*.py" -File
        if ($testFiles) {
            foreach ($file in $testFiles) {
                $readmeContent += "- $($file.Name)`n"
            }
        } else {
            $readmeContent += "Aucun fichier de test trouvé dans ce répertoire."
        }

        # Créer le fichier README.md
        New-Item -Path $readmePath -ItemType File -Value $readmeContent -Force | Out-Null
    }
}

Write-Host "Vérification des fichiers README.md terminée."