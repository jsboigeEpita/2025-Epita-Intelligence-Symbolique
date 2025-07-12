# Définir le chemin racine du projet
$currentDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Join-Path -Path $currentDir -ChildPath "2.3.3-generation-contre-argument"

# Ajouter le chemin au PYTHONPATH pour la session courante
$env:PYTHONPATH = $projectRoot

# Exécuter le script de validation
python (Join-Path -Path $currentDir -ChildPath "demos/validation_deep_taxonomy.py")