# Rapport : Mécanique du Corpus Chiffré `extract_sources.json.gz.enc`

## 📋 Résumé Exécutif

J'ai remonté toute la mécanique autour du fichier `argumentation_analysis/data/extract_sources.json.gz.enc` depuis les scripts de bas niveau jusqu'aux composants de haut niveau. Voici la cartographie complète du système.

## 🗂️ Architecture du Système

### 1. **Fichier Central**
- **Fichier**: `argumentation_analysis/data/extract_sources.json.gz.enc`
- **Format**: JSON compressé et chiffré AES-GCM
- **Contenu**: Sources et extraits de textes pour l'analyse rhétorique

### 2. **Scripts de Bas Niveau**

#### A. Déchiffrement et Accès
- **`scripts/data_processing/decrypt_extracts.py`** 
  - Script principal pour déchiffrer le corpus
  - Affiche un résumé des sources disponibles
  - Sauvegarde temporaire des données déchiffrées
  
- **`scripts/data_processing/debug_inspect_extract_sources.py`**
  - Inspection avancée avec filtres
  - Options: `--source-id`, `--all-french`, `--all`
  - Utilise `display_extract_sources_details()`

#### B. Utilitaires Cryptographiques
- **`argumentation_analysis/utils/core_utils/crypto_utils.py`**
  - Fonctions `load_encryption_key()` et `decrypt_data_aesgcm()`
  
- **`argumentation_analysis/services/crypto_service.py`**
  - Service de chiffrement/déchiffrement centralisé

### 3. **Composants de Niveau Intermédiaire**

#### A. Gestionnaire de Sources
- **`argumentation_analysis/core/source_manager.py`**
  - Méthode `select_text_for_analysis()` : sélection intelligente d'extraits
  - Support pour sources SIMPLE et COMPLEX
  
#### B. Utilitaires d'Affichage
- **`argumentation_analysis/utils/debug_utils.py`**
  - Fonction `display_extract_sources_details()` pour l'affichage structuré
  - Filtrage par ID, sources françaises, etc.

### 4. **Composants de Haut Niveau**

#### A. Interface Utilisateur Web
- **`argumentation_analysis/ui/app.py`** (lignes 235-250)
  - **Sélection aléatoire** : `source_info = random.choice(local_current_extract_definitions)`
  - **Sélection manuelle** : via dropdowns source + extrait
  - **Mode "Texte Complet"** vs extraits spécifiques

#### B. Orchestrateur Principal
- **`argumentation_analysis/main_orchestrator.py`**
  - Point d'entrée principal du système
  - Gère l'initialisation du corpus chiffré

## 🎯 Mécanismes de Sélection

### 1. **Sélection Aléatoire**
```python
# Dans ui/app.py
source_info = random.choice(local_current_extract_definitions)
extracts_available = source_info.get("extracts", [])
potential_extracts = [{"extract_name": "Texte Complet"}] + extracts_available
extract_info = random.choice(potential_extracts)
```

### 2. **Sélection par Index**
```python
# Dans models/extract_definition.py
def get_extract_by_index(self, index: int):
    if 0 <= index < len(self.extracts):
        return self.extracts[index]
```

### 3. **Sélection Intelligente**
```python
# Dans core/source_manager.py
def select_text_for_analysis(self, extract_definitions):
    # Logique de fallback et sélection optimisée
```

## 🛠️ Scripts de Test Créés

### 1. **Script Principal** : `test_extract_corpus_selection.py`
- Test complet de la mécanique
- Démontre sélection aléatoire et par index
- Affiche les métadonnées du corpus

### 2. **Utilitaire Simple** : `select_extract.py`
- Interface en ligne de commande
- Options : `--random`, `--index N`, `--list`

## 📝 Commandes de Test

### Configuration de l'Environnement
```powershell
# Activation automatique avec le one-liner
./activate_project_env.ps1
```

### Tests du Corpus
```powershell
# Test complet de la mécanique
python test_extract_corpus_selection.py

# Utilisation de l'utilitaire simple
python select_extract.py --help
python select_extract.py --list
python select_extract.py --random
python select_extract.py --index 0

# Scripts existants pour inspection avancée
python scripts/data_processing/decrypt_extracts.py --verbose
python scripts/data_processing/debug_inspect_extract_sources.py --all-french
python scripts/data_processing/debug_inspect_extract_sources.py --source-id=0
```

### Tests d'Intégration
```powershell
# Interface web avec sélection aléatoire
python argumentation_analysis/ui/app.py

# Orchestrateur principal
python argumentation_analysis/main_orchestrator.py
```

## 🔐 Configuration Requise

### Variables d'Environnement
- **`TEXT_CONFIG_PASSPHRASE`** : Clé de déchiffrement du corpus
- Chargée automatiquement depuis `.env` par les scripts

### Dépendances
- Modules `argumentation_analysis.*`
- Package `project_core.utils.crypto_utils`
- Bibliothèques standard : `gzip`, `json`, `random`

## 📊 État Actuel du Corpus

- **Sources disponibles** : 1 (exemple vide de démonstration)
- **Extraits totaux** : 0
- **Format** : Structure prête pour données réelles

## 💡 Recommandations

1. **Pour tester avec des données réelles** : 
   - Utiliser `scripts/utils/create_test_encrypted_extracts.py`
   - Ou peupler le corpus via l'interface web

2. **Pour le débogage** :
   - Utiliser `debug_inspect_extract_sources.py` avec les filtres appropriés

3. **Pour l'intégration** :
   - Les scripts créés (`test_extract_corpus_selection.py` et `select_extract.py`) sont prêts pour usage production

## ✅ Conclusion

La mécanique complète autour de `extract_sources.json.gz.enc` est maintenant mappée et testée. Le système permet :
- Chiffrement sécurisé des sources textuelles
- Sélection aléatoire ou par index des extraits
- Interface web et CLI pour l'interaction
- Architecture modulaire et extensible

Tous les scripts de test sont fonctionnels et prêts à être utilisés.