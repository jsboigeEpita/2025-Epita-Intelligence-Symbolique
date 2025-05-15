# Script pour créer les répertoires de données de test

$baseDir = "tests\test_data"

# Liste des répertoires à créer
$directories = @(
    "$baseDir\extract_definitions\valid",
    "$baseDir\extract_definitions\partial",
    "$baseDir\extract_definitions\invalid",
    "$baseDir\source_texts\with_markers",
    "$baseDir\source_texts\partial_markers",
    "$baseDir\source_texts\no_markers",
    "$baseDir\service_configs\llm",
    "$baseDir\service_configs\cache",
    "$baseDir\service_configs\crypto",
    "$baseDir\error_cases"
)

# Créer chaque répertoire
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -Path $dir -ItemType Directory -Force
        Write-Host "Répertoire créé: $dir"
    } else {
        Write-Host "Le répertoire existe déjà: $dir"
    }
}

Write-Host "Création des répertoires terminée."