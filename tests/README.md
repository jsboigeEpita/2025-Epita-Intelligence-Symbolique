# Documentation des Tests de l'Application Web

Ce document décrit comment exécuter les différentes suites de tests pour l'application web.

## Prérequis

- Assurez-vous que l'environnement virtuel Python est activé.
- Installez les dépendances de test : `pip install -r requirements.txt` (si applicable) et `pip install pytest playwright`
- Installez les navigateurs pour Playwright : `playwright install`

## Suites de Tests

Il existe deux suites de tests principales :

1.  **Tests d'API (Pytest)**: Ces tests valident le comportement de l'API backend.
2.  **Tests End-to-End (Playwright)**: Ces tests simulent des interactions utilisateur complètes dans un navigateur.

## Exécution des Tests

Le moyen le plus simple d'exécuter tous les tests est d'utiliser le script d'orchestration.

### Méthode 1 : Exécution via l'Orchestrateur (Recommandé)

L'orchestrateur `unified_web_orchestrator.py` gère automatiquement le démarrage des serveurs, l'exécution des tests et l'arrêt.

```bash
# Activer l'environnement virtuel si nécessaire
# .venv/Scripts/activate

# Lancer la suite de tests complète (API + E2E)
python scripts/apps/webapp/unified_web_orchestrator.py
```

Le script va :
1. Démarrer le serveur backend Flask.
2. Démarrer le serveur frontend Node.js.
3. Exécuter les tests `pytest` situés dans `tests/functional/webapp`.
4. Exécuter les tests `Playwright` situés dans `tests/e2e/webapp`.
5. Arrêter les serveurs.

### Méthode 2 : Exécution Manuelle

#### 1. Tests d'API (Pytest)

Ces tests ne nécessitent que le démarrage du backend.

```bash
# 1. Démarrer le backend (dans un terminal)
python -m uvicorn argumentation_analysis.services.web_api.app:app --host 0.0.0.0 --port 5010

# 2. Lancer les tests pytest (dans un autre terminal)
pytest tests/functional/webapp/
```

#### 2. Tests End-to-End (Playwright)

Ces tests nécessitent que les **deux** serveurs (backend et frontend) soient en cours d'exécution.

```bash
# 1. S'assurer que le backend ET le frontend sont démarrés

# 2. Lancer les tests Playwright
playwright test tests/e2e/webapp/