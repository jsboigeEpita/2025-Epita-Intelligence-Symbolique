# Démonstration de l'Analyse Rhétorique

Ce document explique comment exécuter le script de démonstration pour le flux d'analyse rhétorique.

## But de la Démo

Le script `run_rhetorical_analysis_demo.py` a pour objectif de :
1.  Illustrer le processus de déchiffrement et de sélection d'un texte source.
2.  Montrer comment lancer l'analyse rhétorique collaborative sur ce texte.
3.  Démontrer la configuration du logging pour capturer la conversation détaillée entre les agents IA.
4.  Indiquer où trouver les résultats de l'analyse et les logs.

## Préparation de l'Environnement

Avant de lancer la démo, assurez-vous des points suivants :

1.  **Variables d'Environnement** :
    *   Le script tentera de lire la phrase secrète depuis la variable d'environnement `TEXT_CONFIG_PASSPHRASE`.
    *   Si `TEXT_CONFIG_PASSPHRASE` n'est pas définie, le script vous la demandera interactivement lors de son exécution.
    *   Assurez-vous que votre fichier `.env` (situé à la racine du projet) contient les configurations nécessaires pour le service LLM (par exemple, `OPENAI_API_KEY`, `OPENAI_CHAT_MODEL_ID`). Le script tente de charger ce fichier.

2.  **Fichier Source Chiffré** :
    *   Le fichier de données chiffré `argumentation_analysis/data/extract_sources.json.gz.enc` doit être présent.

3.  **Dépendances** :
    *   Toutes les dépendances Python du projet doivent être installées (généralement via `pip install -r requirements.txt` ou `poetry install`).
    *   Un environnement Java Development Kit (JDK >= 11) doit être installé et la variable d'environnement `JAVA_HOME` correctement configurée si vous souhaitez utiliser l'agent de logique propositionnelle (qui dépend de la JVM via JPype et Tweety). Le script tentera d'initialiser la JVM.
    *   Les bibliothèques JAR nécessaires (par exemple, pour Tweety) doivent être présentes dans le répertoire `libs/`.

4.  **Environnement d'Exécution** :
    *   Il est recommandé de lancer le script depuis un environnement virtuel où les dépendances du projet sont installées.
    *   Vous pouvez utiliser le script `scripts/env/activate_project_env.ps1` (sous PowerShell) pour configurer certaines variables d'environnement utiles (comme `PYTHONPATH` et `LD_LIBRARY_PATH` pour Linux/macOS).

## Lancement du Script

Pour lancer la démonstration, exécutez la commande suivante depuis la racine de votre projet :

```bash
python scripts/demo/run_rhetorical_analysis_demo.py
```

Ou si vous êtes déjà dans le répertoire `scripts/demo/` :

```bash
python run_rhetorical_analysis_demo.py
```

### Lancement via le script d'activation de l'environnement (Recommandé)

Pour vous assurer que toutes les variables d'environnement (comme `PYTHONPATH`, `JAVA_HOME` si configuré par le setup Python, et les variables du fichier `.env`) sont correctement chargées, vous pouvez utiliser le script d'activation `activate_project_env.ps1` pour lancer la démo en une seule commande depuis la racine du projet :

```powershell
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python .\scripts\demo\run_rhetorical_analysis_demo.py"
```
Cette méthode est particulièrement utile si vous n'avez pas activé manuellement un environnement virtuel ou si vous voulez garantir la cohérence de l'environnement d'exécution.

Le script effectuera les étapes suivantes :
*   Demande de la phrase secrète (si non fournie via `TEXT_CONFIG_PASSPHRASE`).
*   Déchiffrement du fichier `extract_sources.json.gz.enc`.
*   Sélection d'un texte prédéfini pour l'analyse.
*   Initialisation de la JVM et du service LLM.
*   Lancement de la conversation d'analyse rhétorique.
*   Affichage d'informations sur les logs et les résultats.

## Texte Source Utilisé

Pour cette démonstration, le script sélectionne de manière prédéfinie :
*   La **première `SourceDefinition`** trouvée dans le fichier `extract_sources.json.gz.enc`.
*   Le **premier `Extract`** de cette source.

Le nom de la source et de l'extrait sélectionnés seront affichés dans les logs de la console au début de l'exécution.

## Fichier Log de la Conversation

La conversation détaillée entre les agents IA, y compris les messages échangés et les appels aux outils (fonctions), est enregistrée dans le fichier suivant :

*   `logs/rhetorical_analysis_demo_conversation.log`

Ce fichier est configuré pour enregistrer les messages à partir du niveau `DEBUG`, fournissant ainsi une trace complète du déroulement de l'analyse.

## Rapports Finaux de l'Analyse

Le script `run_rhetorical_analysis_demo.py` invoque la fonction `run_analysis_conversation` du module `argumentation_analysis.orchestration.analysis_runner`. La manière dont les rapports finaux sont sauvegardés dépend de la logique interne de `analysis_runner` et des fonctions qu'il appelle (comme `generate_report`).

Typiquement, les rapports d'analyse (souvent au format JSON) sont sauvegardés :
*   Dans le répertoire d'où le script est exécuté (la racine du projet si vous lancez `python scripts/demo/...`).
*   Ou potentiellement dans un sous-répertoire dédié comme `reports/` ou `logs/outputs/` si `analysis_runner` est configuré pour cela.
*   Le nom du fichier de rapport inclut généralement un horodatage pour l'unicité (par exemple, `rapport_analyse_YYYYMMDD_HHMMSS.json`).

Consultez les derniers messages affichés par le script dans la console ; il donne des indications sur l'emplacement attendu des rapports. Le script de démo lui-même ne spécifie pas d'emplacement de sortie pour les rapports finaux, il s'appuie sur le comportement par défaut du `analysis_runner`.