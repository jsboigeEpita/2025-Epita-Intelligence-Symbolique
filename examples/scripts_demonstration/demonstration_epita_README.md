# Script de Démonstration `demonstration_epita.py`

## Objectif du script

Ce script a pour but de démontrer les fonctionnalités clés du projet d'Intelligence Symbolique EPITA. Il illustre l'intégration et l'utilisation de divers composants du système, notamment :

1.  L'initialisation de l'environnement du projet.
2.  L'exécution des tests unitaires via `pytest`.
3.  L'analyse rhétorique (détection de sophismes) sur un exemple de texte clair.
4.  L'analyse rhétorique sur des données préalablement chiffrées, impliquant le déchiffrement et le traitement.
5.  La génération d'un rapport complet (HTML, Markdown) à partir des résultats d'analyse.
6.  Une interaction basique avec TweetyProject pour des opérations logiques simples.

Le script est conçu pour être auto-suffisant en termes de petites dépendances (comme `flask-cors`, `seaborn`, `markdown`, `semantic-kernel`) qu'il tente d'installer si elles sont manquantes. Il utilise un système de logging détaillé pour suivre chaque étape de son exécution.

## Prérequis

Avant d'exécuter ce script, assurez-vous que les conditions suivantes sont remplies :

1.  **Python 3.x** : Une version récente de Python 3 (typiquement 3.9+) doit être installée et accessible.
2.  **Dépendances du projet** :
    *   Les dépendances principales du projet doivent être installées. Le moyen le plus simple est d'exécuter `pip install -r requirements.txt` et/ou `pip install -e .` depuis la racine du projet.
    *   Le script tentera d'installer `flask-cors`, `seaborn`, `markdown` et `semantic-kernel` s'ils ne sont pas détectés.
3.  **Configuration pour l'analyse de données chiffrées et LLM réel** :
    *   Un fichier `.env` doit exister dans le répertoire `argumentation_analysis/` (c'est-à-dire `argumentation_analysis/.env`).
    *   Ce fichier `.env` **DOIT** contenir la variable `TEXT_CONFIG_PASSPHRASE` avec la passphrase correcte pour déchiffrer le fichier de configuration des sources chiffrées (par exemple, `argumentation_analysis/data/extract_sources.json.gz.enc`).
    *   La variable `ENCRYPTION_KEY` doit être définie dans le fichier `argumentation_analysis/ui/config.py` si vous souhaitez utiliser le `RealCryptoService` (ce qui est le cas par défaut si la clé est présente).
    *   Pour utiliser le service LLM réel (OpenAI) pour l'analyse rhétorique (plutôt qu'un mock), la variable `OPENAI_API_KEY` **DOIT** être définie, soit dans le fichier `.env`, soit comme variable d'environnement système. Si elle n'est pas trouvée, un `MockLLMService` sera utilisé.
4.  **Position d'exécution** : Le script est conçu pour être exécuté depuis la **racine du projet**.

## Comment exécuter le script

Pour exécuter le script de démonstration, ouvrez un terminal PowerShell à la racine de votre projet et lancez la commande suivante :

```powershell
.\scripts\activate_project_env.ps1; python examples/scripts_demonstration/demonstration_epita.py
```

Cette commande effectue deux actions :
1.  `.\scripts\activate_project_env.ps1` : Active l'environnement virtuel du projet (s'il est configuré) et configure les variables d'environnement nécessaires (comme `PYTHONPATH`).
2.  `python examples/scripts_demonstration/demonstration_epita.py` : Exécute le script de démonstration.

Les logs détaillés de l'exécution s'afficheront dans la console.

## Sections de la démonstration

Le script exécute séquentiellement les étapes suivantes :

1.  **Initialisation et Vérification des Dépendances** :
    *   Le script configure le logging et reconfigure `sys.stdout` et `sys.stderr` pour utiliser l'encodage UTF-8.
    *   Il détermine la racine du projet et l'ajoute au `PYTHONPATH` si nécessaire.
    *   Le module `project_core.bootstrap` est importé et utilisé pour initialiser le `ProjectContext`. Cela inclut le chargement des variables d'environnement depuis `.env`, l'initialisation optionnelle de la JVM pour TweetyProject, et la mise en place des services principaux (LLM, Crypto, Definition, Agents).
    *   Une vérification des dépendances Python mineures (`flask-cors`, `seaborn`, `markdown`, `semantic-kernel`) est effectuée, avec une tentative d'installation si elles sont manquantes.

2.  **Exécution des Tests Unitaires** :
    *   La fonction `run_unit_tests()` lance `pytest` pour exécuter l'ensemble des tests unitaires du projet.
    *   Les résultats (succès, échecs, erreurs, résumé) sont capturés et affichés dans les logs.
    *   Cette étape démontre la robustesse et la couverture de test du code base.

3.  **Analyse Rhétorique sur Texte Clair** :
    *   La fonction `analyze_clear_text_example()` lit un fichier d'exemple (`examples/exemple_sophisme.txt`).
    *   Elle utilise l'`InformalAgent` (configuré avec un service LLM réel ou mock) pour analyser le contenu du texte et détecter les sophismes.
    *   Les résultats de l'analyse sont affichés au format JSON dans les logs.

4.  **Analyse Rhétorique sur Données Chiffrées** :
    *   La fonction `analyze_encrypted_data()` utilise le `DefinitionService` pour charger des définitions d'extraits (potentiellement à partir d'une source chiffrée si `RealDefinitionService` est utilisé et configuré).
    *   Un extrait est sélectionné (le premier de la liste chargée). Le texte de cet extrait (qui est supposé être déchiffré par le `DefinitionService` s'il provient d'une source chiffrée) est ensuite analysé par l'`InformalAgent`.
    *   Les résultats de cette analyse sont affichés dans les logs et sauvegardés dans un fichier JSON (par exemple, `results/analysis_encrypted_extract_demo_refactored.json`).

5.  **Génération d'un Rapport Complet** :
    *   Si l'analyse des données chiffrées a produit un fichier de résultats, la fonction `generate_report_from_analysis()` est appelée.
    *   Elle exécute le script `scripts/generate_comprehensive_report.py` en lui passant le fichier JSON des résultats d'analyse.
    *   Ce script génère des rapports en plusieurs formats (typiquement HTML et Markdown) qui sont sauvegardés dans le répertoire `results/reports/comprehensive/`. Les logs indiquent le chemin exact.

6.  **Interaction Basique avec TweetyProject** (Section TODO dans le script, mais avec un exemple fonctionnel) :
    *   Cette section illustre comment interagir avec TweetyProject via `jpype` si la JVM a été initialisée par le bootstrap.
    *   Un exemple simple montre comment charger une classe Java de Tweety (`PlParser`), parser une formule logique simple, et en extraire les atomes.

## Sorties Attendues

Lors de l'exécution du script, vous devriez observer :

*   **Logs détaillés dans la console** : Chaque étape, succès, avertissement ou erreur est journalisé.
*   **Fichier de résultats d'analyse chiffrée** : Un fichier JSON est créé, par exemple, sous `results/analysis_encrypted_extract_demo_refactored.json`, contenant les résultats de l'analyse de l'extrait chiffré.
*   **Rapports générés** : Si l'étape de génération de rapport réussit, des fichiers de rapport (par exemple, `comprehensive_report.html`, `comprehensive_report.md`) seront disponibles dans un sous-dossier de `results/reports/comprehensive/`.

Consultez les logs pour les chemins exacts des fichiers générés et pour toute information de débogage en cas de problème.