# Documentation des Tests du Projet

Ce document décrit comment exécuter les différentes suites de tests pour l'ensemble du projet.

## Prérequis

- Assurez-vous que votre environnement Conda (`base`) est correctement configuré.
- Installez les dépendances de test :
  - Pour Python : `pip install -r requirements.txt` (si applicable), `pip install pytest`
  - Pour les tests E2E (JavaScript) : `pip install playwright` suivi de `playwright install`

## Point d'Entrée Unifié : `run_tests.ps1`

Le moyen le plus simple et recommandé pour lancer les tests est d'utiliser le script unifié `run_tests.ps1` à la racine du projet. Ce script gère l'activation de l'environnement et l'exécution de la suite de tests appropriée.

### Utilisation

Ouvrez un terminal PowerShell et utilisez la syntaxe suivante :

```powershell
.\run_tests.ps1 -Type <type_de_test>
```

Où `<type_de_test>` peut être :
- `unit` : Lance les tests unitaires (rapides, sans I/O).
- `functional` : Lance les tests fonctionnels.
- `integration` : Lance les tests d'intégration.
- `e2e` : Lance les tests End-to-End avec Playwright (JS/TS).
- `e2e-python` : Lance les tests End-to-End avec Pytest (Python).
- `validation` : Lance les tests de validation.
- `all` : (Défaut) Lance les tests `unit` et `functional`.

### Exemples Concrets

**1. Lancer la suite complète des tests unitaires (recommandé pour la validation rapide) :**

```powershell
.\run_tests.ps1 -Type unit
```

**2. Lancer un répertoire de tests unitaires spécifique :**

```powershell
.\run_tests.ps1 -Type unit -Path tests/unit/agents/
```

**3. Lancer les tests End-to-End avec Playwright :**
Assurez-vous d'avoir exécuté `playwright install` au préalable.

```powershell
.\run_tests.ps1 -Type e2e -Browser chromium
```

---

## Méthodes d'Exécution Alternatives (Manuelles)

### Tests Pytest (unit, functional, etc.)

Si vous ne souhaitez pas utiliser le script unifié, vous pouvez lancer `pytest` directement après avoir activé l'environnement Conda.

```bash
# Activer l'environnement Conda
conda activate base

# Lancer les tests unitaires
python -m pytest tests/unit/

# Lancer les tests fonctionnels
python -m pytest tests/functional/
```

### Tests End-to-End (Playwright)

Ces tests nécessitent que les **deux** serveurs (backend et frontend) soient démarrés manuellement au préalable.

```bash
# 1. Démarrer le backend (dans un terminal)
# ...

# 2. Démarrer le frontend (dans un autre terminal)
# ...

# 3. Lancer les tests Playwright (dans un troisième terminal)
playwright test tests/e2e/webapp/