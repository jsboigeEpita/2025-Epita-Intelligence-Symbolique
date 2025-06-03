# Scripts de Démonstration Approfondis

Ce document fournit une description détaillée des scripts de démonstration disponibles dans le répertoire `examples/scripts_demonstration/`. Ces scripts sont conçus pour illustrer des fonctionnalités clés et des cas d'usage spécifiques du projet d'Intelligence Symbolique EPITA.

Pour une vue d'ensemble de tous les exemples disponibles dans le projet (y compris les notebooks et autres types d'exemples), veuillez consulter le [README principal des exemples](../README.md). Le [README de ce répertoire](README.md:0) offre également un aperçu plus concis des scripts listés ici.

## Prérequis Généraux pour l'Exécution des Scripts

Avant d'exécuter l'un des scripts de ce répertoire, assurez-vous que :

1.  **Python 3.x** est installé sur votre système.
2.  L'**environnement virtuel** du projet est activé. Vous pouvez généralement l'activer en utilisant :
    *   Pour PowerShell (depuis la racine du projet) : `.\activate_project_env.ps1` (ou après avoir exécuté [`setup_project_env.ps1`](../../setup_project_env.ps1:0) pour la configuration initiale).
    *   Pour Bash/Shell (depuis la racine du projet) : `. ./activate_project_env.sh` (si un tel script est fourni).
3.  Les **dépendances du projet** sont installées. Consultez le `GUIDE_INSTALLATION_ETUDIANTS.md` (généralement dans `docs/guides/`) ou les fichiers `setup.py` / `requirements.txt` du projet. Certains scripts peuvent avoir des dépendances spécifiques mentionnées ci-dessous.
4.  Certains scripts, notamment ceux interagissant avec des services externes (comme les LLMs), peuvent nécessiter la configuration de clés API via un fichier `.env`. Référez-vous à la documentation spécifique de ces scripts.

## Scripts de Démonstration

### 1. `demonstration_epita.py`

*   **Lien vers le script :** [`demonstration_epita.py`](demonstration_epita.py:0)
*   **Objectif :** Fournir une démonstration complète des fonctionnalités clés implémentées dans ce dépôt pour le projet d'Intelligence Symbolique EPITA. Il permet de visualiser rapidement le déroulement de plusieurs processus importants du projet, en tentant d'utiliser les services réels lorsque c'est possible et configuré.
*   **Instructions d'Exécution :**
    Ouvrez un terminal à la racine du projet et lancez la commande suivante :
    ```bash
    python examples/scripts_demonstration/demonstration_epita.py
    ```
*   **Prérequis Spécifiques :**
    Avant d'exécuter le script, assurez-vous que les conditions suivantes sont remplies (en plus des prérequis généraux) :
    1.  **Dépendances du projet** :
        *   Le script `demonstration_epita.py` vérifie et tente d'installer automatiquement les dépendances `flask-cors` et `seaborn` si elles sont manquantes, en utilisant `pip`.
        *   Les autres dépendances majeures doivent être installées. Vous pouvez généralement les installer en exécutant :
            *   `pip install -r requirements.txt` (si un fichier `requirements.txt` est fourni et à jour à la racine du projet)
            *   Ou `pip install -e .` (si le projet utilise un `setup.py` pour une installation en mode édition depuis la racine).
        *   Les dépendances clés pour ce script et les modules qu'il appelle incluent (mais ne sont pas limitées à) :
            *   `pytest` et `pytest-cov` (pour les tests et la couverture)
            *   `python-dotenv` (pour la gestion des variables d'environnement)
            *   `pandas`, `matplotlib`, `markdown` (utilisées par le script `generate_comprehensive_report.py` qui est appelé par cette démo).
            *   Les bibliothèques spécifiques à `argumentation_analysis` (comme `semantic-kernel` si utilisé par `LLMService` réel, etc.).
    2.  **Configuration pour l'utilisation des services réels** :
        *   Un fichier nommé `.env` doit exister dans le dossier `argumentation_analysis/` (c'est-à-dire, le chemin complet attendu est `argumentation_analysis/.env` par rapport à la racine du projet).
        *   **Pour le déchiffrement réel des données** : Ce fichier `.env` DOIT contenir la variable d'environnement `TEXT_CONFIG_PASSPHRASE`. La valeur de cette variable doit être la passphrase correcte permettant de déchiffrer le fichier de données sources `argumentation_analysis/data/extract_sources.json.gz.enc`. Si cette variable n'est pas présente ou correcte, le script utilisera des versions mockées de `CryptoService` et `DefinitionService`.
        *   **Pour l'analyse rhétorique réelle avec `LLMService`** : Pour que le script utilise le `LLMService` réel (basé sur OpenAI par exemple), la variable `OPENAI_API_KEY` DOIT être définie, soit dans le fichier `argumentation_analysis/.env`, soit directement dans les variables d'environnement de votre système. Si cette clé n'est pas trouvée ou si l'import du `LLMService` réel échoue, un `MockLLMService` sera utilisé à la place.
    3.  **Comportement des Services (Réels vs. Mocks)** :
        *   Le script tente en **priorité** d'utiliser les versions réelles des services : `InformalAgent`, `LLMService`, `CryptoService`, et `DefinitionService`.
        *   **Tests Unitaires** : L'étape d'exécution des tests unitaires utilise typiquement des mocks pour isoler le code testé, conformément aux bonnes pratiques de test.
        *   **`LLMService`** : Si `OPENAI_API_KEY` est configurée et que l'import de `argumentation_analysis.services.llm_service.LLMService` réussit, le service réel est utilisé. Sinon, `MockLLMService` prend le relais.
        *   **`CryptoService` et `DefinitionService`** : Si l'import de `argumentation_analysis.services.crypto_service.CryptoService` et `argumentation_analysis.services.definition_service.DefinitionService` réussit ET que `TEXT_CONFIG_PASSPHRASE` est fournie, les services réels sont utilisés pour le déchiffrement. En cas d'échec d'import ou d'absence de passphrase, des mocks sont utilisés.
        *   **`InformalAgent`** : Le script tente d'importer et d'utiliser `argumentation_analysis.agents.informal_agent.InformalAgent`. Si l'import échoue, l'analyse rhétorique ne pourra pas être effectuée.

*   **Étapes de la Démonstration :**
    Le script `demonstration_epita.py` exécute les étapes suivantes séquentiellement :
    1.  **Vérification et Installation des Dépendances** :
        *   Vérifie si `flask-cors` et `seaborn` sont installés.
        *   Si l'un d'eux est manquant, tente de l'installer via `pip`.
        *   Affiche des messages clairs sur le statut de ces dépendances.
    2.  **Exécution des Tests Unitaires** :
        *   Lance `pytest` pour exécuter l'ensemble des tests unitaires du projet.
        *   Affiche un résumé des résultats des tests dans la console.
        *   Génère un rapport de couverture de code HTML à l'aide de `pytest-cov`.
    3.  **Analyse sur Texte Clair** :
        *   Charge un exemple de fichier texte (situé dans `examples/exemple_sophisme.txt`). Si le fichier n'existe pas, il est créé avec un contenu par défaut.
        *   Tente d'utiliser `InformalAgent` réel avec `LLMService` réel (si `OPENAI_API_KEY` est configurée) ou `MockLLMService` (sinon, ou en cas d'échec d'import du service réel).
        *   Affiche les résultats de cette analyse (généralement une structure JSON) dans la console.
    4.  **Analyse sur Données Chiffrées** :
        *   Tente de charger la `TEXT_CONFIG_PASSPHRASE` depuis `argumentation_analysis/.env`.
        *   Tente d'utiliser `CryptoService` réel pour déchiffrer le fichier `argumentation_analysis/data/extract_sources.json.gz.enc` (si la passphrase est valide et le service importé). Sinon, un mock est utilisé.
        *   Tente d'utiliser `DefinitionService` réel pour charger les extraits de texte à partir des données (potentiellement) déchiffrées. Sinon, un mock est utilisé.
        *   Sélectionne le premier extrait et effectue une analyse rhétorique avec `InformalAgent` réel (utilisant `LLMService` réel ou mocké, comme pour l'analyse sur texte clair).
        *   Sauvegarde le résultat de cette analyse dans un fichier JSON.
    5.  **Génération de Rapports Complets** :
        *   Si l'étape précédente (analyse sur données chiffrées) a réussi et produit un fichier de résultats JSON.
        *   Appelle le script `scripts/generate_comprehensive_report.py` (situé à la racine du projet) en lui passant le fichier JSON de résultats généré précédemment.
        *   Ce script `generate_comprehensive_report.py` est responsable de la création de rapports plus détaillés.

*   **Sortie Attendue / Localisation des Résultats :**
    Après l'exécution complète du script, les principaux résultats et rapports peuvent être trouvés aux emplacements suivants (relatifs à la racine du projet) :
    *   **Sortie Console** : Des informations détaillées sur chaque étape sont affichées directement dans le terminal.
    *   **Rapport de Couverture des Tests** : `htmlcov_demonstration/index.html`.
    *   **Résultat de l'Analyse sur Texte Clair** : Affiché dans la console.
    *   **Résultat de l'Analyse sur Données Chiffrées** : `results/real_analysis_encrypted_extract_demo.json`.
    *   **Rapports Complets (issus de `generate_comprehensive_report.py`)** : Dans le dossier `results/comprehensive_report/`. Cela peut inclure des fichiers HTML, Markdown, et des images de visualisation.
    Veuillez consulter la sortie console pour des indications précises sur les chemins des fichiers de sortie.

### 2. `demo_tweety_interaction_simple.py`

*   **Lien vers le script :** [`demo_tweety_interaction_simple.py`](demo_tweety_interaction_simple.py:0)
*   **Objectif :** Illustre une interaction de base avec la bibliothèque TweetyProject pour la manipulation d'arguments et de logiques formelles. Ce script montre comment créer des bases de connaissances en logique propositionnelle, ajouter des formules (faits et règles), et effectuer des requêtes simples pour vérifier l'implication logique.
*   **Instructions d'Exécution :**
    Après avoir activé l'environnement virtuel (voir Prérequis Généraux), ouvrez un terminal à la racine du projet et lancez :
    ```bash
    python examples/scripts_demonstration/demo_tweety_interaction_simple.py
    ```
*   **Prérequis Spécifiques :**
    *   Les bibliothèques TweetyProject doivent être installées. Elles sont généralement incluses dans les dépendances du projet si les modules d'analyse logique formelle sont utilisés. Vous pouvez vérifier le `setup.py` ou `requirements.txt`.
    *   Un **Java Development Kit (JDK)** (version 8 ou supérieure recommandée) doit être installé sur votre système et la variable d'environnement `JAVA_HOME` doit être correctement configurée, car TweetyProject est une bibliothèque Java.
*   **Sortie Attendue / Comportement :**
    *   Le script affichera dans la console les étapes de :
        *   Création d'une base de connaissance en logique propositionnelle.
        *   Ajout de faits (par exemple, "a", "b").
        *   Ajout de règles (par exemple, "a & b => c").
        *   Vérification si certaines conclusions (par exemple, "c", "d") sont dérivables de la base de connaissance.
    *   Les résultats des requêtes (vrai ou faux pour chaque conclusion testée) seront affichés.
    *   Aucun fichier n'est généré par ce script. Il s'agit purement d'une démonstration en console.

## Guides Complémentaires

Pour des explications plus approfondies sur les concepts illustrés par ces démonstrations, ou sur d'autres aspects du projet, veuillez vous référer aux guides disponibles dans le répertoire [`../../docs/guides/`](../../docs/guides/).