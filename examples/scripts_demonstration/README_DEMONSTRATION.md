# README pour le Script de Démonstration EPITA

Ce document décrit le script `demonstration_epita.py`, son objectif, son utilisation, et les étapes qu'il exécute.

## Objectif du Script

Le script `scripts/demonstration_epita.py` a pour but de fournir une démonstration des fonctionnalités clés implémentées dans ce dépôt pour le projet d'Intelligence Symbolique EPITA. Il permet de visualiser rapidement le déroulement de plusieurs processus importants du projet, en tentant d'utiliser les services réels lorsque c'est possible et configuré.

## Instructions d'Exécution

Pour exécuter le script de démonstration, ouvrez un terminal à la racine du projet et lancez la commande suivante :

```bash
python scripts/demonstration_epita.py
```

## Prérequis

Avant d'exécuter le script, assurez-vous que les conditions suivantes sont remplies :

1.  **Python 3.x** est installé sur votre système.
2.  **Dépendances du projet** :
    *   Le script `demonstration_epita.py` vérifie et tente d'installer automatiquement les dépendances `flask-cors` et `seaborn` si elles sont manquantes, en utilisant `pip`.
    *   Les autres dépendances majeures doivent être installées manuellement. Vous pouvez généralement les installer en exécutant :
        *   `pip install -r requirements.txt` (si un fichier `requirements.txt` est fourni et à jour)
        *   Ou `pip install -e .` (si le projet utilise un `setup.py` pour une installation en mode édition).
    *   Les dépendances clés pour ce script et les modules qu'il appelle incluent (mais ne sont pas limitées à) :
        *   `pytest` et `pytest-cov` (pour les tests et la couverture)
        *   `python-dotenv` (pour la gestion des variables d'environnement)
        *   `pandas`, `matplotlib`, `markdown` (utilisées par le script `generate_comprehensive_report.py` qui est appelé par cette démo).
        *   Les bibliothèques spécifiques à `argumentation_analysis` (comme `semantic-kernel` si utilisé par `LLMService` réel, etc.).
3.  **Configuration pour l'utilisation des services réels** :
    *   Un fichier nommé `.env` doit exister dans le dossier `argumentation_analysis/` (c'est-à-dire, le chemin complet attendu est `argumentation_analysis/.env`).
    *   **Pour le déchiffrement réel des données** : Ce fichier `.env` DOIT contenir la variable d'environnement `TEXT_CONFIG_PASSPHRASE`. La valeur de cette variable doit être la passphrase correcte permettant de déchiffrer le fichier de données sources `argumentation_analysis/data/extract_sources.json.gz.enc`. Si cette variable n'est pas présente ou correcte, le script utilisera des versions mockées de `CryptoService` et `DefinitionService`.
    *   **Pour l'analyse rhétorique réelle avec `LLMService`** : Pour que le script utilise le `LLMService` réel (basé sur OpenAI par exemple), la variable `OPENAI_API_KEY` DOIT être définie, soit dans le fichier `argumentation_analysis/.env`, soit directement dans les variables d'environnement de votre système. Si cette clé n'est pas trouvée ou si l'import du `LLMService` réel échoue, un `MockLLMService` sera utilisé à la place.
4.  **Comportement des Services (Réels vs. Mocks)** :
    *   Le script tente en **priorité** d'utiliser les versions réelles des services : `InformalAgent`, `LLMService`, `CryptoService`, et `DefinitionService`.
    *   **Tests Unitaires** : L'étape d'exécution des tests unitaires utilise typiquement des mocks pour isoler le code testé, conformément aux bonnes pratiques de test.
    *   **`LLMService`** : Si `OPENAI_API_KEY` est configurée et que l'import de `argumentation_analysis.services.llm_service.LLMService` réussit, le service réel est utilisé. Sinon, `MockLLMService` prend le relais.
    *   **`CryptoService` et `DefinitionService`** : Si l'import de `argumentation_analysis.services.crypto_service.CryptoService` et `argumentation_analysis.services.definition_service.DefinitionService` réussit ET que `TEXT_CONFIG_PASSPHRASE` est fournie, les services réels sont utilisés pour le déchiffrement. En cas d'échec d'import ou d'absence de passphrase, des mocks sont utilisés.
    *   **`InformalAgent`** : Le script tente d'importer et d'utiliser `argumentation_analysis.agents.informal_agent.InformalAgent`. Si l'import échoue, l'analyse rhétorique ne pourra pas être effectuée.

## Étapes de la Démonstration

Le script `demonstration_epita.py` exécute les étapes suivantes séquentiellement :

1.  **Vérification et Installation des Dépendances** :
    *   Vérifie si `flask-cors` et `seaborn` sont installés.
    *   Si l'un d'eux est manquant, tente de l'installer via `pip`.
    *   Affiche des messages clairs sur le statut de ces dépendances.

2.  **Exécution des Tests Unitaires** :
    *   Lance `pytest` pour exécuter l'ensemble des tests unitaires du projet.
    *   Affiche un résumé des résultats des tests dans la console.
    *   Génère un rapport de couverture de code HTML à l'aide de `pytest-cov`.
    *   **Résultats attendus** :
        *   Sortie console indiquant le succès ou l'échec des tests.
        *   Rapport de couverture HTML généré dans le dossier `htmlcov_demonstration/` (accessible via `htmlcov_demonstration/index.html`).

3.  **Analyse sur Texte Clair** :
    *   Charge un exemple de fichier texte (situé dans `examples/exemple_sophisme.txt`). Si le fichier n'existe pas, il est créé avec un contenu par défaut.
    *   Tente d'utiliser `InformalAgent` réel avec `LLMService` réel (si `OPENAI_API_KEY` est configurée) ou `MockLLMService` (sinon, ou en cas d'échec d'import du service réel).
    *   Affiche les résultats de cette analyse (généralement une structure JSON) dans la console.
    *   **Résultats attendus** :
        *   Sortie console affichant le contenu du fichier d'exemple et les résultats JSON de l'analyse.

4.  **Analyse sur Données Chiffrées** :
    *   Tente de charger la `TEXT_CONFIG_PASSPHRASE` depuis `argumentation_analysis/.env`.
    *   Tente d'utiliser `CryptoService` réel pour déchiffrer le fichier `argumentation_analysis/data/extract_sources.json.gz.enc` (si la passphrase est valide et le service importé). Sinon, un mock est utilisé.
    *   Tente d'utiliser `DefinitionService` réel pour charger les extraits de texte à partir des données (potentiellement) déchiffrées. Sinon, un mock est utilisé.
    *   Sélectionne le premier extrait et effectue une analyse rhétorique avec `InformalAgent` réel (utilisant `LLMService` réel ou mocké, comme pour l'analyse sur texte clair).
    *   Sauvegarde le résultat de cette analyse dans un fichier JSON.
    *   **Résultats attendus** :
        *   Sortie console détaillant les étapes de chargement, déchiffrement (réel ou simulé), et l'analyse.
        *   Un fichier JSON contenant les résultats de l'analyse, sauvegardé à `results/real_analysis_encrypted_extract_demo.json`.

5.  **Génération de Rapports Complets** :
    *   Si l'étape précédente (analyse sur données chiffrées) a réussi et produit un fichier de résultats JSON.
    *   Appelle le script `scripts/generate_comprehensive_report.py` en lui passant le fichier JSON de résultats généré précédemment.
    *   Ce script `generate_comprehensive_report.py` est responsable de la création de rapports plus détaillés (potentiellement HTML, Markdown, graphiques).
    *   **Résultats attendus** :
        *   Sortie console indiquant le déroulement de la génération du rapport.
        *   Des fichiers de rapport (par exemple, `rapport_analyse_complet.html`, `rapport_analyse_complet.md`, et des visualisations graphiques) générés dans le dossier `results/comprehensive_report/` (ou un sous-dossier similaire, comme indiqué par la sortie du script).

## Localisation des Résultats

Après l'exécution complète du script, les principaux résultats et rapports peuvent être trouvés aux emplacements suivants :

*   **Sortie Console** : Des informations détaillées sur chaque étape sont affichées directement dans le terminal, y compris si les services réels ou les mocks ont été utilisés.
*   **Rapport de Couverture des Tests** : `htmlcov_demonstration/index.html` (ouvrez ce fichier dans un navigateur web).
*   **Résultat de l'Analyse sur Texte Clair** : Affiché dans la console.
*   **Résultat de l'Analyse sur Données Chiffrées** : `results/real_analysis_encrypted_extract_demo.json`.
*   **Rapports Complets (issus de `generate_comprehensive_report.py`)** : Dans le dossier `results/comprehensive_report/` (ou un sous-dossier similaire). Cela peut inclure des fichiers HTML, Markdown, et des images de visualisation.

Veuillez consulter la sortie console du script `demonstration_epita.py` et du script `generate_comprehensive_report.py` pour des indications précises sur les chemins des fichiers de sortie, car ils peuvent légèrement varier en fonction de la configuration ou des mises à jour des scripts.