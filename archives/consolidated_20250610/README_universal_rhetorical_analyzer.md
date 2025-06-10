# 🚀 Universal Rhetorical Analyzer

**Script unifié final** fusionnant les capacités de `unified_production_analyzer.py` et `comprehensive_workflow_processor.py` dans une architecture modulaire intelligente.

## 🏗️ Architecture Modulaire

### Composants Réutilisables
```
argumentation_analysis/utils/
├── crypto_workflow.py       # Gestion corpus chiffrés
└── unified_pipeline.py      # Pipeline d'analyse unifié

scripts/consolidated/
├── universal_rhetorical_analyzer.py  # Orchestrateur principal
├── universal_config_example.json     # Configuration
└── test_universal_rhetorical_analyzer.py  # Tests

tests/unit/utils/
├── test_crypto_workflow.py          # Tests crypto
└── test_unified_pipeline.py         # Tests pipeline
```

### Avantages de l'Architecture
- ✅ **Modulaire** : Composants réutilisables dans `argumentation_analysis`
- ✅ **Testable** : Tests unitaires complets pour chaque module
- ✅ **Maintenable** : Script orchestrateur léger (492 lignes vs 1300+)
- ✅ **Extensible** : Facilité d'ajout de nouveaux modes
- ✅ **Compatible** : Garde toutes les fonctionnalités des scripts sources

## 🎯 Fonctionnalités Unifiées

### Du `unified_production_analyzer.py`
- ✅ Interface CLI riche avec 20+ paramètres
- ✅ Configuration LLM centralisée
- ✅ Mécanisme de retry automatique TweetyProject
- ✅ Support FOL/PL/Modal avec fallback
- ✅ Validation d'authenticité 100%

### Du `comprehensive_workflow_processor.py`
- ✅ Support textes chiffrés avec déchiffrement Fernet automatique
- ✅ Mode batch pour corpus chiffrés
- ✅ Workflow complet : déchiffrement → analyse → validation → rapport
- ✅ Pipeline parallélisé
- ✅ Tests de performance intégrés
- ✅ Formats de sortie multiples (JSON/Markdown/HTML)

## 🔧 Installation et Configuration

### Prérequis
```bash
# Installation des dépendances
pip install cryptography openai asyncio

# Configuration de l'environnement
export OPENAI_API_KEY="your_key_here"
export TEXT_CONFIG_PASSPHRASE="your_encryption_key"
```

### Structure des Fichiers
```
project_root/
├── argumentation_analysis/utils/    # Modules réutilisables
├── scripts/consolidated/           # Scripts orchestrateurs
├── tests/unit/utils/              # Tests unitaires
└── config/                       # Configuration centrale
```

## 📖 Utilisation

### Syntaxe Générale
```bash
python universal_rhetorical_analyzer.py [INPUT] [OPTIONS]
```

### Paramètres CLI Unifiés

#### Sources d'Entrée
```bash
--source-type [text|file|encrypted|batch|corpus]
```

#### Modes de Workflow
```bash
--workflow-mode [analysis|full|validation|performance]
```

#### Configuration Corpus
```bash
--corpus [fichiers .enc]          # Fichiers de corpus
--passphrase [clé]                 # Clé de déchiffrement
--no-decryption                    # Désactiver déchiffrement
```

#### Configuration Analyse
```bash
--analysis-modes [fallacies rhetoric logic coherence semantic unified advanced]
--parallel-workers [nombre]        # Workers parallèles
--allow-mock                       # Autoriser composants simulés
--llm-model [modèle]               # Modèle LLM
```

#### Configuration Sortie
```bash
--output-file [fichier]            # Fichier de sortie
--output-format [json|yaml]        # Format de sortie
--verbose                          # Mode verbeux
```

## 💡 Exemples d'Utilisation

### 1. Analyse de Texte Direct
```bash
# Analyse basique
python universal_rhetorical_analyzer.py "Votre texte à analyser"

# Analyse avec modes spécifiques
python universal_rhetorical_analyzer.py \
  --analysis-modes fallacies rhetoric \
  "Si on autorise cela, bientôt tout sera permis."
```

### 2. Analyse de Fichier
```bash
# Fichier texte simple
python universal_rhetorical_analyzer.py \
  --source-type file \
  --output-file results.json \
  document.txt
```

### 3. Corpus Chiffrés (Fonctionnalité Clé)
```bash
# Corpus unique chiffré
python universal_rhetorical_analyzer.py \
  --source-type encrypted \
  --passphrase "ma_clé_secrète" \
  data.enc

# Corpus multiples
python universal_rhetorical_analyzer.py \
  --source-type corpus \
  --corpus file1.enc file2.enc file3.enc \
  --passphrase "clé_commune"
```

### 4. Mode Batch
```bash
# Répertoire de fichiers texte
python universal_rhetorical_analyzer.py \
  --source-type batch \
  --parallel-workers 8 \
  /path/to/text/files/
```

### 5. Workflow Complet
```bash
# Workflow avec validation système
python universal_rhetorical_analyzer.py \
  --workflow-mode full \
  --source-type encrypted \
  --passphrase "clé" \
  corpus_data.enc
```

### 6. Tests de Performance
```bash
# Performance automatique
python universal_rhetorical_analyzer.py \
  --workflow-mode performance \
  --parallel-workers 8 \
  "Texte de test performance"
```

### 7. Mode Développement
```bash
# Développement avec mocks
python universal_rhetorical_analyzer.py \
  --allow-mock \
  --verbose \
  --analysis-modes fallacies rhetoric \
  "Texte de développement"
```

## 🔄 Migration depuis les Anciens Scripts

### Depuis `unified_production_analyzer.py`
```bash
# Ancien
python scripts/consolidated/unified_production_analyzer.py \
  --analysis-modes unified \
  --require-real-gpt \
  "texte"

# Nouveau (équivalent)
python scripts/consolidated/universal_rhetorical_analyzer.py \
  --workflow-mode analysis \
  "texte"
```

### Depuis `comprehensive_workflow_processor.py`
```bash
# Ancien
python scripts/consolidated/comprehensive_workflow_processor.py \
  --mode full \
  --corpus data.enc \
  --passphrase "clé"

# Nouveau (équivalent)
python scripts/consolidated/universal_rhetorical_analyzer.py \
  --workflow-mode full \
  --source-type corpus \
  --corpus data.enc \
  --passphrase "clé"
```

## 🧪 Tests et Validation

### Tests Unitaires
```bash
# Tests des modules
python -m pytest tests/unit/utils/test_crypto_workflow.py -v
python -m pytest tests/unit/utils/test_unified_pipeline.py -v

# Tests du script principal
python -m pytest scripts/consolidated/test_universal_rhetorical_analyzer.py -v

# Tous les tests
python -m pytest tests/unit/utils/ scripts/consolidated/test_*.py -v
```

### Tests d'Intégration
```bash
# Test crypto workflow
python -m pytest tests/unit/utils/test_crypto_workflow.py::TestCryptoWorkflowIntegration -v

# Test pipeline complet
python -m pytest tests/unit/utils/test_unified_pipeline.py::TestPipelineIntegration -v

# Tests de performance
python -m pytest scripts/consolidated/test_universal_rhetorical_analyzer.py::TestPerformance -v
```

### Validation Manuelle
```bash
# Test rapide en mode développement
python scripts/consolidated/universal_rhetorical_analyzer.py \
  --allow-mock \
  --verbose \
  --analysis-modes unified fallacies \
  "Test de validation rapide"

# Test avec fichier
echo "Texte de test" > /tmp/test.txt
python scripts/consolidated/universal_rhetorical_analyzer.py \
  --source-type file \
  --allow-mock \
  /tmp/test.txt
```

## 📊 Formats de Sortie

### JSON (Par défaut)
```json
{
  "session_id": "universal_20250610_014530",
  "config": {
    "source_type": "text",
    "workflow_mode": "analysis",
    "analysis_modes": ["unified"],
    "require_authentic": true
  },
  "execution_time": 2.45,
  "timestamp": "2025-06-10T01:45:30",
  "results": {
    "analysis_results": [...],
    "pipeline_summary": {...}
  },
  "status": "completed"
}
```

### YAML
```yaml
session_id: universal_20250610_014530
config:
  source_type: text
  workflow_mode: analysis
results:
  analysis_results: [...]
status: completed
```

## ⚙️ Configuration Avancée

### Fichier de Configuration
```bash
# Utilisation d'un fichier de config (optionnel)
cp scripts/consolidated/universal_config_example.json my_config.json
# Modifier my_config.json selon vos besoins

python universal_rhetorical_analyzer.py \
  --config-file my_config.json \
  "texte"
```

### Variables d'Environnement
```bash
export TEXT_CONFIG_PASSPHRASE="ma_clé_défaut"
export OPENAI_API_KEY="sk-..."
export PYTHONPATH="${PYTHONPATH}:/path/to/project"
```

## 🚨 Dépannage

### Erreurs Communes

#### Erreurs d'Import
```bash
# Solution : Vérifier PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python scripts/consolidated/universal_rhetorical_analyzer.py --help
```

#### Erreurs de Crypto
```bash
# Test de déchiffrement
python scripts/consolidated/universal_rhetorical_analyzer.py \
  --source-type encrypted \
  --no-decryption \  # Test sans déchiffrement
  data.enc
```

#### Performance Lente
```bash
# Mode développement rapide
python scripts/consolidated/universal_rhetorical_analyzer.py \
  --allow-mock \
  --parallel-workers 2 \
  "texte"
```

### Mode Debug
```bash
# Debug complet
python scripts/consolidated/universal_rhetorical_analyzer.py \
  --verbose \
  --allow-mock \
  --workflow-mode validation \
  "debug test"
```

## 📈 Performance et Optimisation

### Recommandations
- **Développement** : Utilisez `--allow-mock` pour des tests rapides
- **Production** : Mode authentique par défaut avec retry automatique
- **Batch** : Ajustez `--parallel-workers` selon votre CPU
- **Corpus volumineux** : Utilisez le mode parallèle avec 4-8 workers

### Métriques
- **Texte simple** : ~1-3s en mode authentique
- **Corpus chiffré** : ~5-10s selon la taille
- **Batch parallèle** : ~2-4x plus rapide que séquentiel
- **Mode mock** : ~0.1-0.5s (développement)

## 🔮 Évolutions Futures

### Roadmap
1. **Support GPU** : Accélération pour analyses volumineuses
2. **Cache intelligent** : Éviter les re-analyses identiques
3. **API REST** : Service web pour intégration
4. **Streaming** : Analyse en temps réel
5. **Multi-langue** : Support langues non-françaises

### Extensibilité
- **Nouveaux modes** : Ajout facile dans `unified_pipeline.py`
- **Formats de sortie** : Extension simple via `UniversalRhetoricalAnalyzer`
- **Sources d'entrée** : Nouveaux types via `SourceType`
- **Algorithmes crypto** : Extension via `crypto_workflow.py`

## 📄 Licence et Contributions

- **Licence** : Projet académique EPITA 2025
- **Contributions** : Suivre l'architecture modulaire établie
- **Tests** : Obligatoires pour toute nouvelle fonctionnalité
- **Documentation** : Mise à jour requise pour changements API

---

**🎉 Universal Rhetorical Analyzer v1.0.0** - *L'analyseur rhétorique ultime pour tous vos besoins !*