# 🚀 Guide de Démarrage Rapide - Système Sherlock-Watson-Moriarty

## ⚡ Démarrage en 3 étapes

### 1. Préparation de l'environnement
```bash
# Assurer que vous êtes dans le répertoire du projet
cd d:/2025-Epita-Intelligence-Symbolique

# Vérifier que l'environnement conda est disponible
conda info --envs | grep epita_symbolic_ai_sherlock
```

### 2. Lancement du système
```bash
# Option A: Lancement via script d'activation (RECOMMANDÉ)
powershell -File .\scripts\env\activate_project_env.ps1 -CommandToRun "python scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py"

# Option B: Lancement direct (si environnement déjà activé)
python scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py
```

### 3. Consultation des résultats
```bash
# Voir les traces générées
ls results/sherlock_watson/trace_robuste_*.json

# Voir le dernier fichier de trace
ls -la results/sherlock_watson/ | tail -1
```

---

## 📋 Vérifications Préalables

### Configuration Requise
- ✅ **Python 3.8+** avec environment conda `epita_symbolic_ai_sherlock`
- ✅ **Java JDK 17** (fourni dans `libs/portable_jdk/`)
- ✅ **Variables d'environnement** dans `.env`
- ✅ **Bibliothèques Tweety** (35+ JARs dans `libs/tweety/`)

### Test de Connectivité
```bash
# Test API OpenAI
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key:', os.getenv('OPENAI_API_KEY')[:10] + '...')"

# Test JVM Java
java -version

# Test environnement Python
python -c "import semantic_kernel; print('Semantic Kernel OK')"
```

---

## 🎯 Scénarios d'Utilisation

### Scénario 1: Session Standard
```bash
# Exécution normale avec 3 cycles maximum
python scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py
```
**Durée attendue**: 2-3 minutes  
**Sortie**: Session interactive avec 3+ tours de dialogue

### Scénario 2: Test de Validation
```bash
# Exécution des tests automatisés
python -m pytest tests/validation_sherlock_watson/test_phase_d_trace_ideale.py -v
```
**Durée attendue**: 30-60 secondes  
**Sortie**: Rapport de tests avec assertions

### Scénario 3: Session de Debug
```bash
# Version avec logs étendus
python scripts/sherlock_watson/run_real_sherlock_watson_moriarty.py
```
**Durée attendue**: 3-5 minutes  
**Sortie**: Logs détaillés pour diagnostic

---

## 📁 Structure des Fichiers

### Scripts Principaux
- `scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py` - **VERSION RECOMMANDÉE**
- `scripts/sherlock_watson/run_real_sherlock_watson_moriarty.py` - Version de développement

### Tests Disponibles
- `tests/validation_sherlock_watson/test_phase_a_*.py` - Tests personnalités
- `tests/validation_sherlock_watson/test_phase_b_*.py` - Tests dialogue naturel
- `tests/validation_sherlock_watson/test_phase_c_*.py` - Tests transitions fluides
- `tests/validation_sherlock_watson/test_phase_d_*.py` - Tests trace idéale

### Sorties Générées
- `results/sherlock_watson/trace_robuste_*.json` - Traces sessions principales
- `results/sherlock_watson/analyse_trace_*.json` - Analyses détaillées
- `results/sherlock_watson/rapport_validation_*.json` - Rapports de validation

---

## 🔧 Résolution de Problèmes

### Problème: "Erreur d'activation conda"
```bash
# Solution: Vérifier le chemin conda
where conda
conda info

# Alternative: Utiliser le chemin complet
C:\Tools\miniconda3\Scripts\conda.exe activate epita_symbolic_ai_sherlock
```

### Problème: "JVM ne démarre pas"
```bash
# Vérifier JAVA_HOME
echo $env:JAVA_HOME

# Solution: Redéfinir la variable
$env:JAVA_HOME = "D:\2025-Epita-Intelligence-Symbolique\libs\portable_jdk\jdk-17.0.11+9"
```

### Problème: "API OpenAI non disponible"
```bash
# Vérifier le fichier .env
cat .env | grep OPENAI_API_KEY

# Test de connectivité
curl -H "Authorization: Bearer $OPENAI_API_KEY" https://api.openai.com/v1/models
```

### Problème: "Imports manquants"
```bash
# Réinstaller les dépendances
pip install -e .

# Vérifier PYTHONPATH
echo $env:PYTHONPATH
```

---

## 📊 Attendus et Métriques

### Session Normale
- **Agents actifs**: 3 (Sherlock, Watson, Moriarty)
- **Tours minimum**: 3 cycles
- **Messages capturés**: 5-10 messages
- **Durée totale**: 2-5 minutes

### Indicateurs de Succès
```
✅ "JVM démarrée avec succès"
✅ "Service LLM créé avec succès"
✅ "Workflow configuré avec 3 agents"
✅ "Session complète réussie"
✅ "Trace sauvegardée : ..."
```

### Indicateurs d'Échec
```
❌ "Erreur de démarrage JVM"
❌ "API Key non valide"
❌ "Timeout de connexion"
❌ "Import Error"
```

---

## 🎭 Personnalisation

### Modifier le Nombre de Cycles
Éditez `scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py`:
```python
# Ligne ~45
termination_strategy = OracleTerminationStrategy(max_cycles=5)  # Était 3
```

### Changer le Modèle LLM
Modifiez `.env`:
```bash
OPENAI_CHAT_MODEL_ID=gpt-4  # Était gpt-4o-mini
```

### Ajuster la Stratégie Oracle
Éditez la configuration:
```python
# Options: "conservative", "balanced", "aggressive"
strategy = "aggressive"
```

---

## 📞 Support et Documentation

### Documentation Complète
- `docs/sherlock_watson/MISSION_SHERLOCK_WATSON_COMPLETE.md` - Rapport final
- `docs/sherlock_watson/documentation_phase_*.md` - Documentation par phases

### Fichiers de Référence
- `docs/DOC_CONCEPTION_SHERLOCK_WATSON.md` - Conception originale
- `docs/analyse_orchestrations_sherlock_watson.md` - Analyse technique

### Logs et Debug
- Logs en temps réel dans la console
- Traces JSON dans `results/sherlock_watson/`
- Configuration debug dans les scripts

---

**Dernière mise à jour**: 07 juin 2025  
**Version du guide**: 1.0  
**Compatibilité**: Système Sherlock-Watson-Moriarty v1.0