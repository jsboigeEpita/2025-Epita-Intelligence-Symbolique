# Nettoyage final de la racine du projet
# Déplace tous les fichiers restants vers leurs répertoires appropriés

Write-Host "=== NETTOYAGE FINAL DE LA RACINE ===" -ForegroundColor Green

# Créer les répertoires nécessaires
$directories = @(
    'docs/reports',
    'docs/guides', 
    'docs/migration',
    'docs/plans',
    'scripts/legacy_root',
    'config/pytest',
    'archives/root_cleanup'
)

foreach($dir in $directories) {
    if(!(Test-Path $dir)) {
        New-Item -Path $dir -ItemType Directory -Force | Out-Null
        Write-Host "Créé: $dir" -ForegroundColor Yellow
    }
}

# Déplacer les rapports
Write-Host "Déplacement des rapports RAPPORT_*.md" -ForegroundColor Blue
Get-ChildItem -Path . -Name "RAPPORT_*.md" | ForEach-Object {
    git mv $_ docs/reports/
    Write-Host "  -> $_" -ForegroundColor Gray
}

# Déplacer les guides
Write-Host "Déplacement des guides" -ForegroundColor Blue
$guides = @("GUIDE_*.md", "GETTING_STARTED.md", "ENVIRONMENT_SETUP.md")
foreach($pattern in $guides) {
    Get-ChildItem -Path . -Name $pattern | ForEach-Object {
        git mv $_ docs/guides/
        Write-Host "  -> $_" -ForegroundColor Gray
    }
}

# Déplacer les fichiers de migration
Write-Host "Déplacement des fichiers de migration" -ForegroundColor Blue
$migration = @("MIGRATION_*.md", "CHANGELOG_*.md")
foreach($pattern in $migration) {
    Get-ChildItem -Path . -Name $pattern | ForEach-Object {
        git mv $_ docs/migration/
        Write-Host "  -> $_" -ForegroundColor Gray
    }
}

# Déplacer les plans
Write-Host "Déplacement des plans" -ForegroundColor Blue
Get-ChildItem -Path . -Name "PLAN_*.md" | ForEach-Object {
    git mv $_ docs/plans/
    Write-Host "  -> $_" -ForegroundColor Gray
}

# Déplacer les scripts PowerShell
Write-Host "Déplacement des scripts PowerShell" -ForegroundColor Blue
Get-ChildItem -Path . -Name "*.ps1" | ForEach-Object {
    git mv $_ scripts/legacy_root/
    Write-Host "  -> $_" -ForegroundColor Gray
}

# Déplacer les configurations pytest
Write-Host "Déplacement des configurations pytest" -ForegroundColor Blue
Get-ChildItem -Path . -Name "pytest*.ini" | ForEach-Object {
    git mv $_ config/pytest/
    Write-Host "  -> $_" -ForegroundColor Gray
}

# Déplacer les autres fichiers .md vers docs/
Write-Host "Déplacement des autres fichiers .md" -ForegroundColor Blue
$autres = @("*.md")
foreach($pattern in $autres) {
    Get-ChildItem -Path . -Name $pattern | Where-Object { $_ -ne "README.md" } | ForEach-Object {
        git mv $_ docs/
        Write-Host "  -> $_" -ForegroundColor Gray
    }
}

# Déplacer les fichiers temporaires et de données
Write-Host "Déplacement des fichiers temporaires" -ForegroundColor Blue
$temp = @("*.json", "*.html")
foreach($pattern in $temp) {
    Get-ChildItem -Path . -Name $pattern | Where-Object { 
        $_ -ne "playwright.config.js" -and $_ -ne "pyproject.toml" 
    } | ForEach-Object {
        git mv $_ archives/root_cleanup/
        Write-Host "  -> $_" -ForegroundColor Gray
    }
}

# Déplacer les fichiers .env supplémentaires
Write-Host "Déplacement des fichiers .env" -ForegroundColor Blue
Get-ChildItem -Path . -Name ".env.*" | ForEach-Object {
    git mv $_ config/
    Write-Host "  -> $_" -ForegroundColor Gray
}

Write-Host "=== NETTOYAGE TERMINÉ ===" -ForegroundColor Green
Write-Host "Fichiers restants à la racine :" -ForegroundColor Yellow
Get-ChildItem -Path . -File | Where-Object { $_.Name -notlike ".*" } | Sort-Object Name | ForEach-Object {
    Write-Host "  $($_.Name)" -ForegroundColor Gray
}