# Scripts d'exécution

Ce répertoire contient les scripts d'exécution des fonctionnalités principales et des workflows complets du projet d'analyse argumentative.

## Scripts disponibles

### 1. `rhetorical_analysis.py`

Script principal pour lancer des analyses rhétoriques sur des textes.
Il permet de configurer différents agents d'analyse et de traiter des corpus de textes.

**Fonctionnalités (générales) :**
- Chargement de corpus de textes.
- Configuration et exécution d'agents d'analyse rhétorique (basique et avancée).
- Génération de résultats d'analyse détaillés.

**Utilisation (exemple) :**
```bash
python scripts/execution/rhetorical_analysis.py --corpus <chemin_corpus> --output <fichier_resultats.json>
```
Consultez `python scripts/execution/rhetorical_analysis.py --help` pour toutes les options.

### 2. `run_full_python_analysis_workflow.py`

Exécute un workflow complet d'analyse Python, potentiellement enchaînant plusieurs étapes de traitement et d'analyse du projet.

**Fonctionnalités (générales) :**
- Orchestration de plusieurs étapes d'analyse.
- Peut inclure le chargement de données, le prétraitement, l'analyse rhétorique, et la génération de rapports intermédiaires ou finaux.

**Utilisation (exemple) :**
```bash
python scripts/execution/run_full_python_analysis_workflow.py --config <fichier_config_workflow>
```
Consultez `python scripts/execution/run_full_python_analysis_workflow.py --help` pour les options spécifiques.

### 3. `run_extract_repair.py`

Script d'exécution pour la réparation des bornes défectueuses dans les extraits. Ce script est un point d'entrée simplifié pour exécuter le script de réparation des bornes défectueuses dans les extraits. Il utilise les services refactorisés et les modèles centralisés.

**Fonctionnalités :**
- Configuration des services nécessaires (LLM, cache, chiffrement, extraction, récupération, définition)
- Chargement des définitions d'extraits
- Réparation des bornes défectueuses
- Génération d'un rapport
- Sauvegarde des modifications si demandé

**Options disponibles :**
- `--output`, `-o` : Fichier de sortie pour le rapport HTML (défaut: "repair_report.html")
- `--save`, `-s` : Sauvegarder les modifications
- `--hitler-only` : Traiter uniquement le corpus de discours d'Hitler
- `--verbose`, `-v` : Activer le mode verbeux
- `--input`, `-i` : Fichier d'entrée personnalisé
- `--output-json` : Fichier de sortie JSON pour vérification (défaut: "extract_sources_updated.json")

**Utilisation :**
```bash
# Exécution de base (génère un rapport sans sauvegarder les modifications)
python scripts/execution/run_extract_repair.py

# Exécution avec sauvegarde des modifications
python scripts/execution/run_extract_repair.py --save
```

### 4. `run_verify_extracts.py`

Script d'exécution pour la vérification des extraits. Ce script est un point d'entrée simplifié pour exécuter le script de vérification des extraits. Il utilise les services refactorisés et les modèles centralisés.

**Fonctionnalités :**
- Configuration des services nécessaires (cache, chiffrement, extraction, récupération, définition)
- Chargement des définitions d'extraits
- Vérification des extraits
- Génération d'un rapport

**Options disponibles :**
- `--output`, `-o` : Fichier de sortie pour le rapport HTML (défaut: "verify_report.html")
- `--verbose`, `-v` : Activer le mode verbeux
- `--input`, `-i` : Fichier d'entrée personnalisé
- `--hitler-only` : Traiter uniquement le corpus de discours d'Hitler

**Utilisation :**
```bash
# Exécution de base
python scripts/execution/run_verify_extracts.py
```

## Bonnes pratiques

1.  **Exécuter les scripts depuis la racine du projet** pour garantir que les chemins relatifs fonctionnent correctement.
2.  **Vérifier les extraits avant de les réparer** en exécutant d'abord `run_verify_extracts.py` pour identifier les problèmes.
3.  **Utiliser l'option `--verbose`** pour obtenir des informations détaillées sur l'exécution du script.
4.  **Utiliser l'option `--dry-run`** (si disponible) pour simuler l'exécution sans effectuer de modifications.
5.  **Examiner les rapports générés** pour comprendre les modifications apportées.