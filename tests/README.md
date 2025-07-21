# Documentation des Tests du Projet

Ce document décrit la méthode **unique et recommandée** pour exécuter les différentes suites de tests du projet.

---

## Point d'Entrée Unifié : `run_tests.ps1`

Toute l'exécution des tests doit passer par le script unifié `run_tests.ps1` situé à la racine du projet. Ce script est le seul point d'entrée supporté.

**Pourquoi est-ce obligatoire ?**
Ce script ne se contente pas de lancer les tests. Il est responsable de :
1.  **Activer l'environnement Conda** correctement.
2.  **Charger les variables d'environnement** spécifiques aux tests (depuis `.env.test`).
3.  **Désactiver les services non nécessaires** (comme OpenTelemetry) pour isoler les tests.
4.  **Déléguer l'exécution** à l'orchestrateur de test interne (`project_core/test_runner.py`) avec les bons paramètres.

Tenter de lancer `pytest` ou `playwright` manuellement contourne ces étapes cruciales et mènera à des échecs ou des résultats non fiables.

### Utilisation

Ouvrez un terminal PowerShell et utilisez la syntaxe suivante :

```powershell
.\run_tests.ps1 -Type <type_de_test> [options]
```

#### Types de Tests (`-Type`)
- `unit` : Lance les tests unitaires (rapides, sans I/O).
- `functional` : Lance les tests fonctionnels.
- `integration` : Lance les tests d'intégration.
- `e2e` : Lance les tests End-to-End avec Playwright (JS/TS).
- `e2e-python` : Lance les tests End-to-End avec Pytest (Python).
- `validation` : Lance les tests de validation.
- `all` : (Défaut) Lance les tests `unit` et `functional`.

#### Options Communes
- `-Path <chemin>` : Cible un fichier ou un répertoire de test spécifique.
- `-Browser <nom>` : Pour les tests `e2e`, spécifie le navigateur (`chromium`, `firefox`, `webkit`).
- `-PytestArgs "<args>"` : Passe des arguments supplémentaires directement à Pytest (ex: `-PytestArgs "-k mon_test -s"`).

### Exemples Concrets

**1. Lancer tous les tests unitaires (recommandé pour une validation rapide) :**
```powershell
.\run_tests.ps1 -Type unit
```

**2. Lancer un répertoire de tests fonctionnels spécifique :**
```powershell
.\run_tests.ps1 -Type functional -Path tests/functional/database/
```

**3. Lancer un seul fichier de test en affichant les `print()` :**
```powershell
.\run_tests.ps1 -Type unit -Path tests/unit/agents/test_parser.py -PytestArgs "-s"
```

**4. Lancer les tests End-to-End avec Playwright sur Firefox :**
```powershell
.\run_tests.ps1 -Type e2e -Browser firefox
```

---

## Note Importante : L'Erreur "Windows fatal exception"

Lors de l'exécution de tests qui dépendent de Java (comme les tests d'intégration), vous pourriez voir le message suivant dans les logs :

> **Windows fatal exception: access violation**

**CECI N'EST PAS UNE ERREUR BLOQUANTE.**

Ce message est un **artefact cosmétique** connu de la bibliothèque `JPype` sous Windows. Il n'a **aucun impact** sur l'exécution ou le résultat des tests. La JVM est démarrée et fonctionne correctement.

**Vous devez ignorer ce message.** N'essayez pas de le "corriger", les véritables causes d'instabilité ont déjà été résolues en désactivant certaines options JVM dans le code.

---

## Couverture des Solveurs (`tweety` et `prover9`)

Les tests d'intégration cruciaux qui dépendent d'un solveur logique (comme ceux pour le `FOLHandler`) sont maintenant **automatiquement paramétrés**.

Cela signifie que lorsque vous exécutez la suite de tests (par exemple, `.\run_tests.ps1 -Type integration`), les tests concernés s'exécuteront **deux fois** : une fois en forçant l'utilisation de `tweety`, et une fois en forçant l'utilisation de `prover9`.

Vous n'avez **plus besoin** de définir manuellement la variable d'environnement `ARG_ANALYSIS_SOLVER` pour assurer la couverture des deux solveurs. Le framework de test s'en charge.