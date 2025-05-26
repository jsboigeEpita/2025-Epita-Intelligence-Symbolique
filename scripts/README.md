# Scripts Utilitaires du Projet

Ce répertoire contient divers scripts Python et PowerShell pour faciliter le développement, la maintenance, l'exécution et la validation du projet d'analyse argumentative.

## Organisation des Scripts

Les scripts sont organisés en sous-dossiers thématiques :

-   **[`cleanup/`](./cleanup/README.md)** : Scripts pour nettoyer le projet, supprimer les fichiers obsolètes et gérer la configuration du dépôt.
-   **[`execution/`](./execution/README.md)** : Scripts principaux pour exécuter des fonctionnalités clés du système, comme la réparation ou la vérification des extraits.
-   **[`reports/`](./reports/README.md)** : Scripts liés à la génération ou à la mise à jour de rapports (par exemple, rapports de couverture).
-   **[`setup/`](./setup/README.md)** : Scripts pour configurer l'environnement de développement, gérer les dépendances (notamment JPype et les outils de compilation).
-   **[`testing/`](./testing/README.md)** : Scripts spécifiques pour des scénarios de test ou des simulations.
-   **[`utils/`](./utils/README.md)** : Petits scripts utilitaires pour des tâches de maintenance ponctuelles sur les fichiers du code source (encodage, indentation, syntaxe).
-   **[`validation/`](./validation/README.md)** : Scripts pour valider la structure du projet, les fichiers Markdown, ou d'autres aspects de la qualité.

## Scripts Principaux à la Racine de `scripts/`

En plus des sous-dossiers, quelques scripts importants résident directement à la racine de `scripts/` :

-   **`analyze_directory_usage.py`**: Analyse l'utilisation de certains répertoires dans le code.
-   **`check_encoding.py`**: Vérifie l'encodage des fichiers.
-   **`check_imports.py`**: S'assure que toutes les importations Python fonctionnent correctement.
-   **`compare_rhetorical_agents.py` / `compare_rhetorical_agents_simple.py`**: Scripts pour comparer les performances ou les résultats de différents agents rhétoriques.
-   **`decrypt_extracts.py`**: Utilitaire pour déchiffrer les extraits (à utiliser avec précaution).
-   **`download_test_jars.py`**: Télécharge les JARs minimaux nécessaires pour les tests.
-   **`fix_project_structure.py`**: Ancien script principal de restructuration (peut contenir des logiques utiles mais à utiliser avec prudence sur la structure actuelle).
-   **`generate_comprehensive_report.py`**: Génère un rapport d'analyse complet.
-   **`generate_coverage_report.py`**: Génère un rapport de couverture de tests.
-   **`generate_rhetorical_analysis_summaries.py`**: Crée des résumés à partir des analyses rhétoriques.
-   **`initialize_coverage_history.py`**: Initialise l'historique pour le suivi de la couverture des tests.
-   **`rhetorical_analysis.py` / `rhetorical_analysis_standalone.py`**: Scripts pour lancer des analyses rhétoriques.
-   **`script_commits.ps1`**: Script PowerShell pour aider à la gestion des commits.
-   **`test_imports.py` / `test_imports_after_reorg.py`**: Scripts pour tester les importations Python.
-   **`test_rhetorical_analysis.py`**: Script pour tester les fonctionnalités d'analyse rhétorique.
-   **`update_imports.py` / `update_paths.py`**: Anciens scripts de restructuration pour mettre à jour les importations et les chemins (à utiliser avec prudence).
-   **`verify_content_integrity.py` / `verify_files.py`**: Scripts pour vérifier l'intégrité des fichiers ou du contenu.
-   **`visualize_test_coverage.py`**: Génère des visualisations pour la couverture des tests.

## Utilisation

Pour chaque sous-dossier et pour de nombreux scripts individuels, un `README.md` spécifique détaille leur fonction et leur mode d'emploi.
De manière générale, les scripts Python s'exécutent avec `python scripts/chemin/vers/script.py [options]` et les scripts PowerShell avec `.\scripts\chemin\vers\script.ps1 [options]`.

<<<<<<< HEAD
# Mode normal (applique les modifications)
python scripts/fix_project_structure.py

# Options disponibles
python scripts/fix_project_structure.py --help
```

### Scripts individuels

- **`update_imports.py`** : Met à jour les importations dans les fichiers existants.

```bash
# Mode dry-run (analyse sans modification)
python scripts/update_imports.py --dry-run

# Mode normal (applique les modifications)
python scripts/update_imports.py
```

- **`update_paths.py`** : Met à jour les références aux chemins dans les fichiers existants.

```bash
# Mode dry-run (analyse sans modification)
python scripts/update_paths.py --dry-run

# Mode normal (applique les modifications)
python scripts/update_paths.py
```

- **`download_test_jars.py`** : Télécharge les JARs minimaux nécessaires pour les tests.

```bash
# Télécharge les JARs s'ils n'existent pas déjà
python scripts/download_test_jars.py

# Force le téléchargement même si les JARs existent déjà
python scripts/download_test_jars.py --force
```

- **`test_imports.py`** : Vérifie que les importations fonctionnent correctement.

```bash
python scripts/test_imports.py
```

- **`analyze_directory_usage.py`** : Analyse l'utilisation des répertoires `config/` et `data/` dans le code.

```bash
python scripts/analyze_directory_usage.py
```

- **`check_imports.py`** : Vérifie que toutes les importations fonctionnent correctement.

```bash
python scripts/check_imports.py
```

- **`embed_all_sources.py`** : S'assure que toutes les sources dans un fichier de configuration d'extraits ont leur texte source complet (`full_text`) embarqué. Il lit un fichier de configuration d'extraits chiffré, récupère le texte complet pour chaque source où il est manquant (en utilisant les informations `source_url` ou `path` et les services de `fetch_service`), puis sauvegarde la configuration mise à jour dans un nouveau fichier chiffré.

```bash
# Exemple d'utilisation du script d'embarquement
python scripts/embed_all_sources.py \
  --input-config chemin/vers/votre/extract_sources.json.gz.enc \
  --output-config chemin/vers/votre/extract_sources_embedded.json.gz.enc \
  --passphrase "votre_phrase_secrete" \
  --force
```
  **Arguments pour `embed_all_sources.py`**:
  - `--input-config` (requis): Chemin vers le fichier de configuration chiffré d'entrée.
  - `--output-config` (requis): Chemin vers le fichier de configuration chiffré de sortie.
  - `--passphrase` (optionnel): Passphrase pour le déchiffrement/chiffrement. Utilise `TEXT_CONFIG_PASSPHRASE` de l'environnement si non fourni.
  - `--force` (optionnel): Écrase le fichier de sortie s'il existe déjà.

## Utilisation recommandée

1. **Analyse des problèmes** : Exécutez d'abord les scripts en mode dry-run pour analyser les problèmes sans modifier les fichiers.

```bash
python scripts/fix_project_structure.py --dry-run
```

2. **Application des modifications** : Une fois que vous êtes satisfait des modifications proposées, exécutez le script principal sans l'option `--dry-run`.

```bash
python scripts/fix_project_structure.py
```

3. **Vérification des modifications** : Exécutez les tests unitaires pour vérifier que les modifications n'ont pas introduit de régressions.

```bash
cd argumentiation_analysis/tests
python run_tests.py
```

## Structure des répertoires créés

- **`argumentiation_analysis/libs/`** : Contient les JARs Tweety principaux
  - **`native/`** : Contient les bibliothèques natives spécifiques à la plateforme

- **`argumentiation_analysis/tests/resources/libs/`** : Contient les JARs minimaux pour les tests
  - **`native/`** : Contient les bibliothèques natives spécifiques à la plateforme pour les tests

## Fichiers créés ou modifiés

- **`argumentiation_analysis/paths.py`** : Module de gestion centralisée des chemins
- **`argumentiation_analysis/__init__.py`** : Fichier d'initialisation du package mis à jour
- **`argumentiation_analysis/core/__init__.py`** : Fichier d'initialisation du module core mis à jour
- **`argumentiation_analysis/agents/__init__.py`** : Fichier d'initialisation du module agents avec redirections
- **`argumentiation_analysis/orchestration/__init__.py`** : Fichier d'initialisation du module orchestration mis à jour
- **`argumentiation_analysis/tests/jvm_test_case.py`** : Classe de base pour les tests qui dépendent de la JVM
- **`argumentiation_analysis/tests/test_jvm_example.py`** : Exemple de test utilisant la classe JVMTestCase
- **`argumentiation_analysis/tests/run_tests.ps1`** : Script de test mis à jour pour vérifier les JARs de test
=======
Il est recommandé de se référer au README spécifique du script ou du sous-dossier avant toute utilisation.
>>>>>>> origin/main
