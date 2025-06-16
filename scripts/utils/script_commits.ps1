# Script d'exécution des commits et push pour les modifications documentaires
# Date: 22/05/2025

Write-Host "Début de l'organisation et exécution des commits..." -ForegroundColor Cyan

# 1. AMÉLIORATIONS DOCUMENTAIRES

# 1.1 Guide de démarrage rapide
Write-Host "Commit 1: Guide de démarrage rapide" -ForegroundColor Green
git add GETTING_STARTED.md
git commit -m "Ajout du guide de démarrage rapide pour faciliter l'onboarding des nouveaux contributeurs"

# 1.2 Clarification des dossiers dupliqués
Write-Host "Commit 2: Clarification des dossiers dupliqués" -ForegroundColor Green
git add plan_clarification_dossiers_dupliques.md
git commit -m "Documentation: Plan de clarification pour les dossiers dupliqués dans le projet"

# 1.3 Alignement de la documentation (README et autres fichiers de documentation)
Write-Host "Commit 3: Alignement de la documentation générale" -ForegroundColor Green
git add README.md
git add argumentation_analysis/examples/README.md
git add argumentation_analysis/results/README.md
git add docs/reference/README.md
git add examples/README.md
git add results/README.md
git commit -m "Harmonisation des fichiers README à travers le projet pour une meilleure cohérence documentaire"

# 2. DOCUMENTATION TECHNIQUE

# 2.1 Documentation des API des agents
Write-Host "Commit 4: Documentation des API des agents" -ForegroundColor Green
git add docs/reference/agents/
git commit -m "Ajout de la documentation détaillée des API des agents spécialistes"

# 2.2 Documentation de l'architecture d'orchestration
Write-Host "Commit 5: Documentation de l'architecture d'orchestration" -ForegroundColor Green
git add docs/reference/orchestration/
git add docs/analyse_structure_depot.md
git commit -m "Documentation de l'architecture d'orchestration et analyse de la structure du dépôt"

# 2.3 Autres améliorations techniques
Write-Host "Commit 6: Mise à jour des fichiers de configuration" -ForegroundColor Green
git add .gitignore
git commit -m "Mise à jour du .gitignore pour exclure les fichiers temporaires et de configuration locale"

Write-Host "Commit 7: Mise à jour des résultats d'analyse" -ForegroundColor Green
git add results/test_analysis_result.json
git commit -m "Mise à jour des résultats d'analyse de test pour refléter les dernières modifications"

Write-Host "Commit 8: Ajout des fichiers de test" -ForegroundColor Green
git add scripts/execution/run_test.py
git add tests/test_*.py
git commit -m "Ajout des fichiers de test pour la validation et la vérification du système"

Write-Host "Commit 9: Ajout des exemples de textes pour l'analyse" -ForegroundColor Green
git add examples/article_scientifique.txt
git add examples/discours_avec_template.txt
git add examples/discours_politique.txt
git add examples/texte_sans_marqueurs.txt
git commit -m "Ajout d'exemples de textes variés pour les tests d'analyse rhétorique"

# 3. PUSH ET VÉRIFICATION

# 3.1 Push vers le dépôt distant
Write-Host "Push des modifications vers le dépôt distant..." -ForegroundColor Yellow
git push origin main

# 3.2 Vérification de l'état après push
Write-Host "Vérification de l'état du dépôt après push..." -ForegroundColor Yellow
git status

# 3.3 Affichage des derniers commits pour vérification
Write-Host "Affichage des derniers commits pour vérification..." -ForegroundColor Yellow
git log --oneline -n 10

Write-Host "Processus de commit et push terminé avec succès!" -ForegroundColor Cyan