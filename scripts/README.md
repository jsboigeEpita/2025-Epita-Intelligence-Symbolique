# Scripts Utilitaires

## Vue d'ensemble

Ce module contient divers scripts Python et PowerShell pour faciliter le développement, la maintenance, l'exécution et la validation du projet d'analyse argumentative. Ces scripts automatisent des tâches courantes, simplifient les processus complexes et assurent la cohérence des opérations à travers le projet.

## Structure

Les scripts sont organisés en sous-dossiers thématiques :

- **`cleanup/`** : Scripts pour nettoyer le projet, supprimer les fichiers obsolètes et gérer la configuration du dépôt.
- **`execution/`** : Scripts principaux pour exécuter des fonctionnalités clés du système, comme la réparation ou la vérification des extraits.
- **`reports/`** : Scripts liés à la génération ou à la mise à jour de rapports (par exemple, rapports de couverture).
- **`setup/`** : Scripts pour configurer l'environnement de développement, gérer les dépendances (notamment JPype et les outils de compilation).
- **`testing/`** : Scripts spécifiques pour des scénarios de test ou des simulations.
- **`utils/`** : Petits scripts utilitaires pour des tâches de maintenance ponctuelles sur les fichiers du code source (encodage, indentation, syntaxe).
- **`validation/`** : Scripts pour valider la structure du projet, les fichiers Markdown, ou d'autres aspects de la qualité.

En plus des sous-dossiers, plusieurs scripts importants résident directement à la racine de `scripts/` :

- **`analyze_directory_usage.py`** : Analyse l'utilisation de certains répertoires dans le code.
- **`check_encoding.py`** : Vérifie l'encodage des fichiers.
- **`check_imports.py`** : S'assure que toutes les importations Python fonctionnent correctement.
- **`compare_rhetorical_agents.py`** / **`compare_rhetorical_agents_simple.py`** : Scripts pour comparer les performances ou les résultats de différents agents rhétoriques.
- **`decrypt_extracts.py`** : Utilitaire pour déchiffrer les extraits (à utiliser avec précaution).
- **`download_test_jars.py`** : Télécharge les JARs minimaux nécessaires pour les tests.
- **`fix_project_structure.py`** : Script principal de restructuration (à utiliser avec prudence sur la structure actuelle).
- **`generate_comprehensive_report.py`** : Génère un rapport d'analyse complet.
- **`generate_coverage_report.py`** : Génère un rapport de couverture de tests.
- **`generate_rhetorical_analysis_summaries.py`** : Crée des résumés à partir des analyses rhétoriques.
- **`initialize_coverage_history.py`** : Initialise l'historique pour le suivi de la couverture des tests.
- **`rhetorical_analysis.py`** / **`rhetorical_analysis_standalone.py`** : Scripts pour lancer des analyses rhétoriques.
- **`test_imports.py`** / **`test_imports_after_reorg.py`** : Scripts pour tester les importations Python.
- **`test_rhetorical_analysis.py`** : Script pour tester les fonctionnalités d'analyse rhétorique.
- **`update_imports.py`** / **`update_paths.py`** : Scripts pour mettre à jour les importations et les chemins.
- **`verify_content_integrity.py`** / **`verify_files.py`** : Scripts pour vérifier l'intégrité des fichiers ou du contenu.
- **`visualize_test_coverage.py`** : Génère des visualisations pour la couverture des tests.

## Fonctionnalités

1. **Automatisation des tâches de développement** : Scripts pour automatiser les tâches répétitives du développement.
2. **Validation et vérification** : Outils pour valider la structure du projet et vérifier l'intégrité des fichiers.
3. **Génération de rapports** : Scripts pour générer des rapports de couverture, d'analyse et de synthèse.
4. **Configuration de l'environnement** : Outils pour configurer et valider l'environnement de développement.
5. **Analyse rhétorique** : Scripts pour exécuter et tester les fonctionnalités d'analyse rhétorique.
6. **Maintenance du projet** : Utilitaires pour nettoyer, restructurer et maintenir le projet.

## Installation/Configuration

La plupart des scripts peuvent être exécutés directement sans installation supplémentaire, à condition que les dépendances du projet principal soient installées. Pour certains scripts spécifiques, des dépendances supplémentaires peuvent être nécessaires.

```bash
# Installation des dépendances principales du projet
pip install -r requirements.txt

# Installation des dépendances spécifiques pour les tests
pip install -r config/requirements-test.txt
```

## Utilisation

Pour chaque sous-dossier et pour de nombreux scripts individuels, un `README.md` spécifique détaille leur fonction et leur mode d'emploi.

De manière générale, les scripts Python s'exécutent avec :
```bash
python scripts/chemin/vers/script.py [options]
```

Et les scripts PowerShell avec :
```powershell
.\scripts\chemin\vers\script.ps1 [options]
```

### Exemples d'utilisation

#### Scripts de restructuration

```bash
# Mode dry-run (analyse sans modification)
python scripts/fix_project_structure.py --dry-run

# Mode normal (applique les modifications)
python scripts/fix_project_structure.py

# Options disponibles
python scripts/fix_project_structure.py --help
```

#### Mise à jour des importations

```bash
# Mode dry-run (analyse sans modification)
python scripts/update_imports.py --dry-run

# Mode normal (applique les modifications)
python scripts/update_imports.py
```

#### Téléchargement des JARs de test

```bash
# Télécharge les JARs s'ils n'existent pas déjà
python scripts/download_test_jars.py

# Force le téléchargement même si les JARs existent déjà
python scripts/download_test_jars.py --force
```

#### Analyse de l'utilisation des répertoires

```bash
python scripts/analyze_directory_usage.py
```

#### Embarquement des sources dans les extraits

```bash
# Exemple d'utilisation du script d'embarquement
python scripts/embed_all_sources.py \
  --input-config chemin/vers/votre/extract_sources.json.gz.enc \
  --output-config chemin/vers/votre/extract_sources_embedded.json.gz.enc \
  --passphrase "votre_phrase_secrete" \
  --force
```

## API/Interface

La plupart des scripts fournissent une interface en ligne de commande avec des options et des arguments. Voici quelques interfaces communes :

### Script `fix_project_structure.py`

```
usage: fix_project_structure.py [-h] [--dry-run] [--verbose]

Options:
  -h, --help     affiche ce message d'aide et quitte
  --dry-run      exécute en mode simulation sans appliquer les modifications
  --verbose      affiche des informations détaillées pendant l'exécution
```

### Script `update_imports.py`

```
usage: update_imports.py [-h] [--dry-run] [--verbose] [--path PATH]

Options:
  -h, --help     affiche ce message d'aide et quitte
  --dry-run      exécute en mode simulation sans appliquer les modifications
  --verbose      affiche des informations détaillées pendant l'exécution
  --path PATH    chemin spécifique à traiter (par défaut: tout le projet)
```

### Script `embed_all_sources.py`

```
usage: embed_all_sources.py [-h] --input-config INPUT_CONFIG --output-config OUTPUT_CONFIG [--passphrase PASSPHRASE] [--force]

Options:
  -h, --help                 affiche ce message d'aide et quitte
  --input-config INPUT_CONFIG    chemin vers le fichier de configuration chiffré d'entrée
  --output-config OUTPUT_CONFIG  chemin vers le fichier de configuration chiffré de sortie
  --passphrase PASSPHRASE    passphrase pour le déchiffrement/chiffrement
  --force                    écrase le fichier de sortie s'il existe déjà
```

## Dépendances

### Dépendances externes
- Python 3.9+ : Nécessaire pour exécuter les scripts Python
- PowerShell 5.1+ : Nécessaire pour exécuter les scripts PowerShell
- Git : Utilisé par certains scripts pour la gestion du dépôt

### Dépendances internes
- Module `argumentation_analysis` : La plupart des scripts interagissent avec ce module
- Bibliothèques dans `libs/` : Certains scripts utilisent les bibliothèques externes du projet

## Tests

Les scripts eux-mêmes peuvent être testés avec les commandes suivantes :

```bash
# Tester un script spécifique
pytest tests/scripts/test_script_name.py

# Tester tous les scripts
pytest tests/scripts/
```

Certains scripts ont également des modes de test intégrés :

```bash
# Exécuter le mode test d'un script
python scripts/script_name.py --test
```

## Contribution

Pour contribuer aux scripts utilitaires :

1. Assurez-vous que votre script suit les conventions de nommage et de structure du projet
2. Documentez clairement l'objectif et l'utilisation de votre script
3. Incluez des options `--help`, `--dry-run` et `--verbose` lorsque c'est pertinent
4. Ajoutez des tests pour votre script dans le dossier `tests/scripts/`
5. Mettez à jour ce README ou créez un README spécifique dans le sous-dossier approprié

## Ressources associées

- [Documentation des tests](../tests/README.md) : Informations sur les tests du projet
- [Guide de contribution](../docs/CONTRIBUTING.md) : Guide général pour contribuer au projet
- [Structure du projet](../docs/structure_projet.md) : Description détaillée de la structure du projet
- [Conventions d'importation](../docs/conventions_importation.md) : Conventions pour les importations Python

---

*Dernière mise à jour : 27/05/2025*
