# Guide de Dépannage

Ce document fournit des solutions aux problèmes courants rencontrés lors de l'utilisation du système d'analyse argumentative. Il est organisé par catégories de problèmes pour faciliter la recherche de solutions.

## Table des Matières

- [Problèmes d'Installation](#problèmes-dinstallation)
  - [Erreurs de dépendances](#erreurs-de-dépendances)
  - [Problèmes avec JPype](#problèmes-avec-jpype)
  - [Erreurs de compilation](#erreurs-de-compilation)
- [Problèmes d'Exécution](#problèmes-dexécution)
  - [Erreurs de mémoire](#erreurs-de-mémoire)
  - [Performances lentes](#performances-lentes)
  - [Erreurs d'importation](#erreurs-dimportation)
- [Problèmes d'API](#problèmes-dapi)
  - [Erreurs de connexion](#erreurs-de-connexion)
  - [Problèmes d'authentification](#problèmes-dauthentification)
  - [Limites de requêtes](#limites-de-requêtes)
- [Problèmes d'Analyse](#problèmes-danalyse)
  - [Résultats incorrects](#résultats-incorrects)
  - [Analyses incomplètes](#analyses-incomplètes)
  - [Erreurs de format](#erreurs-de-format)
- [Problèmes de Visualisation](#problèmes-de-visualisation)
  - [Graphiques non générés](#graphiques-non-générés)
  - [Problèmes d'affichage](#problèmes-daffichage)

## Ressources de Diagnostic Générales

Avant de plonger dans des problèmes spécifiques, plusieurs scripts et ensembles de tests peuvent vous aider à diagnostiquer et résoudre les problèmes courants :

*   **Configuration de l'environnement :** Assurez-vous que votre environnement est correctement configuré en exécutant le script [`setup_project_env.ps1`](../../setup_project_env.ps1) (pour Windows) ou `setup_project_env.sh` (pour Linux/macOS).
*   **Tests Généraux :** Le répertoire [`scripts/testing/`](../../scripts/testing/) contient divers scripts pour tester différentes fonctionnalités du projet.
*   **Tests Unitaires :** Pour isoler des problèmes au niveau des modules, exécutez les tests situés dans [`tests/unit/`](../../tests/unit/).
*   **Tests d'Intégration :** Si vous suspectez des problèmes d'interaction entre différents composants, les tests dans [`tests/integration/`](../../tests/integration/) peuvent être utiles.
*   **Test de l'API :** Pour les problèmes spécifiques à l'API web, le script [`libs/web_api/test_api.py`](../../libs/web_api/test_api.py) permet de vérifier son bon fonctionnement.

Consultez également la [FAQ générale de développement](projets/sujets/aide/FAQ_DEVELOPPEMENT.md) pour des réponses aux questions fréquentes.

## Problèmes d'Installation

### Erreurs de dépendances

#### Symptôme : Conflits de versions lors de l'installation des dépendances

**Problème** : Lors de l'exécution de `pip install -r requirements.txt`, vous obtenez des erreurs de conflit de versions.

**Solution** :
1. Créez un environnement virtuel propre :
   ```bash
   python -m venv fresh_env
   source fresh_env/bin/activate  # Sur Unix/macOS
   fresh_env\Scripts\activate     # Sur Windows
   ```

2. Installez les dépendances par groupes :
   ```bash
   pip install --upgrade pip
   pip install -r requirements-core.txt
   pip install -r requirements-analysis.txt
   pip install -r requirements-visualization.txt
   ```

3. Si les conflits persistent, installez les packages problématiques individuellement :
   ```bash
   pip install package-name==specific-version
   ```

#### Symptôme : Erreur "Could not build wheels for..."

**Problème** : Certaines dépendances nécessitent des compilateurs spécifiques.

**Solution** :
1. Installez les outils de développement nécessaires :
   - **Windows** : Visual C++ Build Tools
   - **Linux** : `sudo apt-get install build-essential python3-dev`
   - **macOS** : `xcode-select --install`

2. Utilisez des wheels précompilées si disponibles :
   ```bash
   pip install --only-binary=:all: -r requirements.txt
   ```

3. Consultez le script `scripts/setup/install_prebuilt_dependencies.ps1` pour Windows.

### Problèmes avec JPype

#### Symptôme : Erreur lors de l'installation de JPype

**Problème** : JPype est une dépendance complexe qui peut échouer à l'installation.

**Solution** :
1. Suivez les instructions spécifiques dans `scripts/setup/README_INSTALLATION_OUTILS_COMPILATION.md`

2. Pour Windows, utilisez le script d'installation avec Visual Studio :
   ```powershell
   .\scripts\setup\install_jpype_with_vcvars.ps1
   ```

3. Pour les environnements sans possibilité d'installation de JPype, utilisez le mock :
   ```bash
   python scripts/setup/setup_jpype_mock.ps1
   ```

4. Vérifiez l'installation avec :
   ```bash
   python -c "import jpype; print(jpype.__version__)"
   ```

### Erreurs de compilation

#### Symptôme : Erreur de compilation lors de l'installation

**Problème** : Certains packages nécessitent une compilation qui peut échouer.

**Solution** :
1. Assurez-vous d'avoir les compilateurs et outils de développement à jour

2. Pour Windows, exécutez dans un terminal avec droits administrateur :
   ```powershell
   .\scripts\setup\run_with_vcvars.ps1
   ```

3. Pour les problèmes spécifiques à Python 3.12 :
   ```bash
   pip install --no-binary=:all: package-name
   ```

4. Consultez `scripts/setup/README_PYTHON312_COMPATIBILITY.md` pour les solutions spécifiques à Python 3.12

## Problèmes d'Exécution

### Erreurs de mémoire

#### Symptôme : "MemoryError" ou "Killed" lors de l'exécution

**Problème** : Le système manque de mémoire pour traiter de grands textes ou plusieurs analyses en parallèle.

**Solution** :
1. Réduisez la taille des textes analysés :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --max-length 10000
   ```

2. Utilisez le mode économie de mémoire :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --low-memory
   ```

3. Désactivez les analyses parallèles :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --no-parallel
   ```

4. Augmentez la mémoire swap (Linux/macOS) ou la mémoire virtuelle (Windows)

#### Symptôme : Ralentissements progressifs et utilisation croissante de la mémoire

**Problème** : Fuites de mémoire potentielles dans le traitement des analyses.

**Solution** :
1. Activez la collecte de déchets explicite :
   ```python
   import gc
   gc.collect()
   ```

2. Divisez les analyses en lots plus petits :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --batch-size 5
   ```

3. Redémarrez le service après un certain nombre d'analyses :
   ```bash
   python scripts/execution/run_with_restart.py --max-analyses 20
   ```

### Performances lentes

#### Symptôme : Analyses prenant beaucoup plus de temps que prévu

**Problème** : Inefficacités dans le traitement ou problèmes de configuration.

**Solution** :
1. Activez le cache LLM pour éviter les requêtes redondantes :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --enable-cache
   ```

2. Utilisez des modèles plus légers pour les analyses préliminaires :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --fast-mode
   ```

3. Profiler l'exécution pour identifier les goulots d'étranglement :
   ```bash
   python -m cProfile -o profile.out scripts/execution/run_analysis.py --file votre_fichier.txt
   python scripts/utils/analyze_profile.py profile.out
   ```

4. Vérifiez les logs pour identifier les opérations lentes :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --log-level DEBUG --log-file analysis.log
   ```

### Erreurs d'importation

#### Symptôme : "ModuleNotFoundError" lors de l'exécution

**Problème** : Python ne trouve pas les modules nécessaires.

**Solution** :
1. Vérifiez que le package est installé en mode développement :
   ```bash
   pip install -e .
   ```

2. Vérifiez le PYTHONPATH :
   ```bash
   python -c "import sys; print(sys.path)"
   ```

3. Ajoutez temporairement le chemin du projet :
   ```python
   import sys
   sys.path.append('/chemin/vers/projet')
   ```

4. Exécutez le script de vérification des imports :
   ```bash
   python scripts/test_imports.py
   ```
5. Exécutez les tests unitaires pour vérifier l'intégrité des modules concernés : consultez le répertoire [`tests/unit/`](../../tests/unit/).

#### Symptôme : "ImportError: cannot import name X" 

**Problème** : Structure d'importation circulaire ou module incomplet.

**Solution** :
1. Vérifiez les imports circulaires avec :
   ```bash
   python scripts/utils/check_circular_imports.py
   ```

2. Utilisez les imports relatifs dans les sous-modules :
   ```python
   from ..module import fonction
   ```

3. Restructurez les imports problématiques selon les recommandations dans `docs/conventions_importation.md`

## Problèmes d'API

Pour tout problème lié à l'API, il est fortement recommandé d'exécuter le script de test dédié [`libs/web_api/test_api.py`](../../libs/web_api/test_api.py) qui peut aider à identifier la source du problème (connexion, routes, réponses attendues, etc.).

### Erreurs de connexion

#### Symptôme : Impossible de se connecter à l'API web

**Problème** : L'API web n'est pas accessible.

**Solution** :
1. Vérifiez que le serveur est en cours d'exécution :
   ```bash
   cd services/web_api
   python app.py
   ```

2. Vérifiez le port et l'adresse de liaison :
   ```bash
   netstat -an | findstr 5000  # Windows
   netstat -an | grep 5000     # Linux/macOS
   ```

3. Assurez-vous qu'aucun pare-feu ne bloque la connexion

4. Testez avec curl :
   ```bash
   curl http://localhost:5000/health
   ```

#### Symptôme : Erreurs de timeout lors des requêtes API

**Problème** : Les requêtes prennent trop de temps et expirent.

**Solution** :
1. Augmentez le timeout dans la configuration client :
   ```python
   import requests
   response = requests.post(url, json=data, timeout=300)  # 5 minutes
   ```

2. Optimisez les performances du serveur :
   ```bash
   cd services/web_api
   python app.py --workers 4 --timeout 300
   ```

3. Utilisez des requêtes asynchrones pour les opérations longues :
   ```bash
   curl -X POST http://localhost:5000/analyze/async -d "text=Votre texte ici"
   ```

### Problèmes d'authentification

#### Symptôme : Erreurs 401 Unauthorized

**Problème** : Problèmes d'authentification avec l'API.

**Solution** :
1. Vérifiez que vous utilisez la bonne clé API :
   ```bash
   curl -H "Authorization: Bearer votre-clé-api" http://localhost:5000/protected-endpoint
   ```

2. Régénérez votre clé API :
   ```bash
   python scripts/utils/generate_api_key.py --user votre-nom
   ```

3. Vérifiez la configuration d'authentification dans `config/api_config.json`

### Limites de requêtes

#### Symptôme : Erreurs 429 Too Many Requests

**Problème** : Vous avez dépassé les limites de taux de l'API.

**Solution** :
1. Implémentez un backoff exponentiel :
   ```python
   import time
   import random
   
   def make_request_with_backoff(url, data, max_retries=5):
       for i in range(max_retries):
           try:
               response = requests.post(url, json=data)
               if response.status_code != 429:
                   return response
               wait_time = (2 ** i) + random.random()
               print(f"Rate limited. Waiting {wait_time:.2f} seconds...")
               time.sleep(wait_time)
           except Exception as e:
               print(f"Error: {e}")
       return None
   ```

2. Réduisez la fréquence des requêtes :
   ```bash
   python scripts/execution/run_analysis.py --rate-limit 10  # max 10 requêtes par minute
   ```

3. Utilisez le mode batch pour combiner plusieurs analyses :
   ```bash
   python scripts/execution/run_batch_analysis.py --input-dir textes/ --output-dir resultats/
   ```

## Problèmes d'Analyse

### Résultats incorrects

#### Symptôme : Détection incorrecte de sophismes ou d'arguments

**Problème** : Le système produit des analyses erronées.

**Solution** :
1. Ajustez les seuils de confiance :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --confidence-threshold 0.8
   ```

2. Utilisez un modèle de langage plus performant :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --model gpt-4
   ```

3. Fournissez plus de contexte dans l'analyse :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --with-context
   ```

4. Signalez le problème avec un exemple minimal :
   ```bash
   python scripts/utils/report_analysis_issue.py --file votre_fichier.txt --expected "Description des résultats attendus"
   ```

5. Exécutez les tests d'intégration pour vérifier les interactions entre les différents composants du système d'analyse : consultez le répertoire [`tests/integration/`](../../tests/integration/).

### Analyses incomplètes

#### Symptôme : Analyses partielles ou tronquées

**Problème** : Le système ne termine pas l'analyse complète du texte.

**Solution** :
1. Vérifiez les limites de tokens du modèle :
   ```bash
   python scripts/utils/check_token_limits.py --file votre_fichier.txt
   ```

2. Divisez le texte en sections plus petites :
   ```bash
   python scripts/utils/split_text.py --file votre_fichier.txt --max-tokens 2000
   ```

3. Utilisez l'analyse par segments :
   ```bash
   python scripts/execution/run_segmented_analysis.py --file votre_fichier.txt --segment-size 1000
   ```

4. Augmentez les limites de tokens dans la configuration :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --max-tokens 8000
   ```

### Erreurs de format

#### Symptôme : Erreurs JSON ou format de sortie incorrect

**Problème** : Les résultats ne sont pas correctement formatés.

**Solution** :
1. Validez le format de sortie :
   ```bash
   python scripts/utils/validate_output.py --file results/votre_resultat.json
   ```

2. Forcez un format de sortie spécifique :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --output-format json
   ```

3. Réparez les fichiers JSON corrompus :
   ```bash
   python scripts/utils/repair_json.py --file results/resultat_corrompu.json
   ```

4. Utilisez le mode strict pour la génération :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --strict-output
   ```

## Problèmes de Visualisation

### Graphiques non générés

#### Symptôme : Les visualisations ne sont pas créées

**Problème** : Les graphiques ou visualisations ne sont pas générés correctement.

**Solution** :
1. Vérifiez les dépendances de visualisation :
   ```bash
   pip install -r requirements-visualization.txt
   ```

2. Testez la génération de graphiques basiques :
   ```bash
   python scripts/utils/test_visualization.py
   ```

3. Vérifiez les permissions d'écriture dans le dossier de sortie

4. Utilisez un format alternatif :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --viz-format svg
   ```

### Problèmes d'affichage

#### Symptôme : Visualisations illisibles ou mal formatées

**Problème** : Les graphiques sont générés mais difficiles à lire ou mal formatés.

**Solution** :
1. Ajustez les paramètres de visualisation :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --viz-size 1600x1200 --viz-dpi 300
   ```

2. Utilisez un thème différent :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --viz-theme light
   ```

3. Simplifiez les graphiques complexes :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --viz-simplify
   ```

4. Exportez les données brutes pour une visualisation personnalisée :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --export-data results/data.csv
   ```

---

## Résolution des problèmes courants

### Erreur : "No module named 'argumentation_analysis'"

Cette erreur se produit généralement lorsque le package n'est pas correctement installé ou n'est pas dans le PYTHONPATH.

**Solution étape par étape** :

1. Vérifiez que vous êtes dans le bon environnement virtuel
2. Installez le package en mode développement :
   ```bash
   pip install -e .
   ```
3. Vérifiez l'installation :
   ```bash
   python -c "import argumentation_analysis; print(argumentation_analysis.__version__)"
   ```
4. Si le problème persiste, ajoutez manuellement le chemin :
   ```python
   import sys
   import os
   sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
   import argumentation_analysis
   ```

### Erreur : "RuntimeError: Java Exception occurred" avec JPype

Cette erreur indique un problème avec l'intégration Java via JPype.

**Solution étape par étape** :

1. Vérifiez que Java est correctement installé :
   ```bash
   java -version
   ```
2. Assurez-vous que JAVA_HOME est correctement configuré :
   ```bash
   echo %JAVA_HOME%  # Windows
   echo $JAVA_HOME   # Linux/macOS
   ```
3. Réinstallez JPype avec les options appropriées :
   ```bash
   pip uninstall -y JPype1
   pip install JPype1==1.4.1
   ```
4. Si le problème persiste, utilisez le mock JPype :
   ```bash
   python scripts/setup/setup_jpype_mock.ps1
   ```
5. Vérifiez l'installation :
   ```bash
   python tests/mocks/test_jpype_mock_simple.py
   ```

### Erreur : "API rate limit exceeded" avec les modèles externes

Cette erreur se produit lorsque vous dépassez les limites de taux des API de modèles de langage externes.

**Solution étape par étape** :

1. Implémentez un délai entre les requêtes :
   ```python
   import time
   time.sleep(1)  # Attendre 1 seconde entre les requêtes
   ```
2. Utilisez un pool de clés API :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --api-key-file keys.txt
   ```
3. Activez la mise en cache des requêtes :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --enable-cache
   ```
4. Passez à un niveau de service supérieur ou contactez le fournisseur d'API pour augmenter vos limites

### Erreur : "Process killed" lors de l'analyse de grands textes

Cette erreur se produit lorsque le système manque de mémoire pour traiter de grands textes.

**Solution étape par étape** :

1. Divisez le texte en segments plus petits :
   ```bash
   python scripts/utils/split_text.py --file grand_texte.txt --output-dir segments/ --max-chars 10000
   ```
2. Analysez chaque segment séparément :
   ```bash
   python scripts/execution/run_batch_analysis.py --input-dir segments/ --output-dir resultats/
   ```
3. Combinez les résultats :
   ```bash
   python scripts/utils/combine_results.py --input-dir resultats/ --output-file analyse_complete.json
   ```
4. Utilisez le mode économie de mémoire :
   ```bash
   python scripts/execution/run_analysis.py --file votre_fichier.txt --low-memory
   ```

---

Si vous rencontrez un problème qui n'est pas couvert dans ce guide, veuillez consulter les ressources suivantes :
*   La [FAQ générale de développement](projets/sujets/aide/FAQ_DEVELOPPEMENT.md).
*   Pour les problèmes spécifiques à l'interface web, consultez le [guide de dépannage de l'interface web](projets/sujets/aide/interface-web/TROUBLESHOOTING.md).

Si le problème persiste, ouvrez une issue sur le dépôt GitHub du projet avec une description détaillée du problème, les étapes pour le reproduire, et les logs pertinents.

*Dernière mise à jour : 27/05/2025*