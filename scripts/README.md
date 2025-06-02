# Scripts Utilitaires

## Vue d'ensemble

Ce module contient divers scripts Python et PowerShell pour faciliter le développement, la maintenance, l'exécution et la validation du projet d'analyse argumentative. Ces scripts automatisent des tâches courantes, simplifient les processus complexes et assurent la cohérence des opérations à travers le projet.

## Structure

Les scripts sont organisés en sous-dossiers thématiques :

- **`cleanup/`** : Scripts pour nettoyer le projet, supprimer les fichiers obsolètes et gérer la configuration du dépôt.
- **`execution/`** : Scripts principaux pour exécuter des fonctionnalités clés et des workflows complets du système. (Voir [`execution/README.md`](scripts/execution/README.md:1))
- **`extract_utils/`**: Scripts pour la gestion des extraits de sources (déchiffrement, inspection, chiffrement, embarquement, etc.). (Voir [`extract_utils/README.md`](scripts/extract_utils/README.md:1))
- **`maintenance/`**: Scripts pour la maintenance, la validation, les tests d'imports et la correction de la structure du projet. (Voir [`maintenance/README.md`](scripts/maintenance/README.md:1))
- **`reporting/`**: Scripts liés à la génération de rapports (couverture, analyse rhétorique, comparaison d'agents, etc.) et visualisations. (Voir [`reporting/README.md`](scripts/reporting/README.md:1))
- **`setup/`** : Scripts pour configurer l'environnement de développement, gérer les dépendances (notamment JPype et les outils de compilation). Contient également `download_test_jars.py` et `check_jpype_import.py`.
- **`testing/`** : Scripts spécifiques pour des scénarios de test, des simulations, ou des validations ponctuelles de composants. (Voir [`testing/README.md`](scripts/testing/README.md:1))
- **`utils/`** : Petits scripts utilitaires pour des tâches de maintenance ponctuelles sur les fichiers du code source (encodage, indentation, syntaxe).
- **`validation/`** : Scripts pour valider la structure du projet, les fichiers Markdown, ou d'autres aspects de la qualité.

Note : Les scripts de démonstration ont été déplacés vers le répertoire `examples/scripts_demonstration/`.

En plus des sous-dossiers, les scripts suivants résident directement à la racine de `scripts/` :

- **`analyze_directory_usage.py`** : Analyse l'utilisation de certains répertoires dans le code (utilise `project_core.dev_utils.code_validation`).
- **`check_encoding.py`** : Vérifie l'encodage UTF-8 des fichiers Python du projet (utilise `project_core.dev_utils.encoding_utils`).
- **`script_commits.ps1`**: Script PowerShell pour gérer les commits. **Note : L'usage de ce script doit être documenté plus en détail, ou une alternative en Python pourrait être envisagée pour simplifier les workflows de développement multi-plateforme.**

## Fonctionnalités

1.  **Automatisation des tâches de développement** : Scripts pour automatiser les tâches répétitives du développement.
2.  **Validation et vérification** : Outils pour valider la structure du projet et vérifier l'intégrité des fichiers.
3.  **Génération de rapports** : Scripts pour générer des rapports de couverture, d'analyse et de synthèse.
4.  **Configuration de l'environnement** : Outils pour configurer et valider l'environnement de développement.
5.  **Analyse rhétorique** : Scripts pour exécuter et tester les fonctionnalités d'analyse rhétorique.
6.  **Maintenance du projet** : Utilitaires pour nettoyer, restructurer et maintenir le projet.
7.  **Gestion des extraits de données** : Scripts pour chiffrer, déchiffrer, et traiter les extraits de sources.

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
python chemin/vers/script.py [options]
```
(Note: ajustez le `python` avec `python scripts/` si vous êtes à la racine du projet, ou configurez votre PYTHONPATH)

Et les scripts PowerShell avec :
```powershell
.\scripts\chemin\vers\script.ps1 [options]
```

### Exemples d'utilisation

#### Scripts de restructuration (dans `scripts/maintenance/`)

```bash
python scripts/maintenance/fix_project_structure.py --dry-run
```

#### Mise à jour des importations (dans `scripts/maintenance/`)

```bash
python scripts/maintenance/update_imports.py --dry-run
```

#### Téléchargement des JARs de test (dans `scripts/setup/`)

```bash
python scripts/setup/download_test_jars.py
```

#### Analyse de l'utilisation des répertoires

```bash
python scripts/analyze_directory_usage.py --dir argumentation_analysis --output results/usage_report.json
```

#### Déchiffrement des extraits (dans `scripts/extract_utils/`)
```bash
python scripts/extract_utils/decrypt_extracts.py --output temp_extracts/decrypted.json
```

#### Embarquement des sources dans les extraits (dans `scripts/extract_utils/`)
```bash
python scripts/extract_utils/embed_all_sources.py \
  --input-config chemin/vers/votre/extract_sources.json.gz.enc \
  --output-config chemin/vers/votre/extract_sources_embedded.json.gz.enc \
  --passphrase "votre_phrase_secrete"
```

## API/Interface

La plupart des scripts fournissent une interface en ligne de commande avec des options et des arguments. Consulter l'aide de chaque script (`--help`) pour plus de détails.

## Dépendances

### Dépendances externes
- Python 3.9+ : Nécessaire pour exécuter les scripts Python
- PowerShell 5.1+ : Nécessaire pour exécuter les scripts PowerShell
- Git : Utilisé par certains scripts pour la gestion du dépôt

### Dépendances internes
- Module `argumentation_analysis` : La plupart des scripts interagissent avec ce module
- Module `project_core` : Contient des utilitaires partagés.
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

1.  Assurez-vous que votre script suit les conventions de nommage et de structure du projet
2.  Documentez clairement l'objectif et l'utilisation de votre script
3.  Incluez des options `--help`, `--dry-run` et `--verbose` lorsque c'est pertinent
4.  Ajoutez des tests pour votre script dans le dossier `tests/scripts/`
5.  Mettez à jour ce README ou créez un README spécifique dans le sous-dossier approprié

## Ressources associées

- [Documentation des tests](../tests/README.md) : Informations sur les tests du projet
- [Guide de contribution](../docs/CONTRIBUTING.md) : Guide général pour contribuer au projet
- [Structure du projet](../docs/structure_projet.md) : Description détaillée de la structure du projet
- [Conventions d'importation](../docs/conventions_importation.md) : Conventions pour les importations Python

---

*Dernière mise à jour : 02/06/2025*
