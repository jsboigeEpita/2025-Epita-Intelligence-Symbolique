# Scripts d'exécution

Ce répertoire contient les scripts d'exécution des fonctionnalités principales du projet d'analyse argumentative.

## Scripts disponibles

### 1. run_extract_repair.py

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

# Exécution en mode verbeux avec un fichier d'entrée personnalisé
python scripts/execution/run_extract_repair.py --verbose --input chemin/vers/fichier.json
```

### 2. run_verify_extracts.py

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

# Exécution en mode verbeux
python scripts/execution/run_verify_extracts.py --verbose

# Exécution avec un fichier d'entrée personnalisé
python scripts/execution/run_verify_extracts.py --input chemin/vers/fichier.json
```

## Bonnes pratiques

1. **Exécuter les scripts depuis la racine du projet** pour garantir que les chemins relatifs fonctionnent correctement.
2. **Vérifier les extraits avant de les réparer** en exécutant d'abord `run_verify_extracts.py` pour identifier les problèmes.
3. **Utiliser l'option `--verbose`** pour obtenir des informations détaillées sur l'exécution du script.
4. **Utiliser l'option `--dry-run`** (si disponible) pour simuler l'exécution sans effectuer de modifications.
5. **Examiner les rapports générés** pour comprendre les modifications apportées.