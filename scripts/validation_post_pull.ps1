# Script de validation post-pull pour la reconstruction hiérarchique
# Date: 2025-10-17
# Objectif: Valider que le système fonctionne correctement après le rebase

Write-Host "🔍 DÉBUT DE LA VALIDATION POST-PULL" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# 1. Vérification de l'état Git
Write-Host "`n1. Vérification de l'état Git..." -ForegroundColor Yellow
git status --porcelain
$gitStatus = $LASTEXITCODE
if ($gitStatus -eq 0) {
    Write-Host "✅ Git status OK" -ForegroundColor Green
} else {
    Write-Host "⚠️ Git status montre des modifications" -ForegroundColor Yellow
}

# 2. Validation des fichiers clés
Write-Host "`n2. Validation des fichiers clés..." -ForegroundColor Yellow
$filesToCheck = @(
    "../roo-extensions/mcps/internal/servers/roo-state-manager/src/utils/hierarchy-reconstruction-engine.ts",
    "../roo-extensions/mcps/internal/servers/roo-state-manager/src/utils/roo-storage-detector.ts",
    "../roo-extensions/mcps/internal/servers/roo-state-manager/src/utils/skeleton-comparator.ts"
)

foreach ($file in $filesToCheck) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        if ($content.Length -gt 1000) {
            Write-Host "✅ $file - Présent et valide" -ForegroundColor Green
        } else {
            Write-Host "❌ $file - Fichier trop court ou corrompu" -ForegroundColor Red
        }
    } else {
        Write-Host "❌ $file - Fichier manquant" -ForegroundColor Red
    }
}

# 3. Exécution des tests de reconstruction
Write-Host "`n3. Exécution des tests de reconstruction..." -ForegroundColor Yellow
Set-Location "../roo-extensions/mcps/internal/servers/roo-state-manager"

# Liste des fichiers de test hiérarchique
$testFiles = @(
    "tests/unit/hierarchy-reconstruction-engine.test.ts",
    "tests/unit/hierarchy-reconstruction-phase2.test.ts",
    "tests/integration/hierarchy-reconstruction-end-to-end.test.ts"
)

foreach ($testFile in $testFiles) {
    if (Test-Path $testFile) {
        Write-Host "`n🧪 Exécution de $testFile..." -ForegroundColor Cyan
        npm test $testFile
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ $testFile - Tests passés" -ForegroundColor Green
        } else {
            Write-Host "❌ $testFile - Tests échoués" -ForegroundColor Red
        }
    } else {
        Write-Host "⚠️ $testFile - Fichier de test non trouvé" -ForegroundColor Yellow
    }
}

# 4. Test de génération d'arbre
Write-Host "`n4. Test de génération d'arbre hiérarchique..." -ForegroundColor Yellow
Write-Host "Cette étape nécessite une conversation de test" -ForegroundColor Cyan

# 5. Vérification des dépendances
Write-Host "`n5. Vérification des dépendances..." -ForegroundColor Yellow
if (Test-Path "package.json") {
    $packageJson = Get-Content "package.json" -Raw | ConvertFrom-Json
    $keyDeps = @("@types/node", "typescript", "vitest")
    foreach ($dep in $keyDeps) {
        if ($packageJson.dependencies.$dep -or $packageJson.devDependencies.$dep) {
            Write-Host "✅ Dépendance $dep présente" -ForegroundColor Green
        } else {
            Write-Host "❌ Dépendance $dep manquante" -ForegroundColor Red
        }
    }
}

# 6. Compilation TypeScript
Write-Host "`n6. Test de compilation TypeScript..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Compilation TypeScript réussie" -ForegroundColor Green
} else {
    Write-Host "❌ Échec de compilation TypeScript" -ForegroundColor Red
}

# Retour au répertoire initial
Set-Location "../../../"

Write-Host "`n🏁 FIN DE LA VALIDATION" -ForegroundColor Cyan
Write-Host "=======================" -ForegroundColor Cyan