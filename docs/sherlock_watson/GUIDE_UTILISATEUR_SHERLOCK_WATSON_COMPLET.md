# 🎓 GUIDE UTILISATEUR COMPLET - SYSTÈME SHERLOCK/WATSON/MORIARTY
## Manuel d'Utilisation Détaillé et Cas d'Usage Avancés

**Guide Utilisateur Version 2.1.0**  
**Date** : 10/06/2025  
**Niveau** : Débutant à Avancé  

---

## 📋 **SOMMAIRE**

1. [🚀 Démarrage Rapide](#-démarrage-rapide)
2. [🎯 Configuration Détaillée](#-configuration-détaillée)
3. [🎭 Utilisation des Démonstrations](#-utilisation-des-démonstrations)
4. [🔧 Personnalisation Avancée](#-personnalisation-avancée)
5. [🛠️ Résolution de Problèmes](#️-résolution-de-problèmes)
6. [📊 Métriques et Analyse](#-métriques-et-analyse)
7. [🎓 Cas d'Usage Pédagogiques](#-cas-dusage-pédagogiques)

---

## 🚀 **DÉMARRAGE RAPIDE**

### ⚡ **Installation Express (5 minutes)**

```bash
# 1. Clonage du projet
git clone https://github.com/votre-repo/2025-Epita-Intelligence-Symbolique.git
cd 2025-Epita-Intelligence-Symbolique

# 2. Environnement Python avec Conda (RECOMMANDÉ)
conda create --name projet-is python=3.9.18
conda activate projet-is

# 3. Installation des dépendances
pip install -r requirements.txt

# 4. Vérification Java (requis pour TweetyProject)
java -version
# Sortie attendue: openjdk version "1.8.0_XXX" ou supérieur
```

### 🔑 **Configuration API Minimale**

```bash
# Création fichier .env avec vos clés API
cat > .env << EOF
# Configuration OpenRouter (RECOMMANDÉ - moins cher)
OPENROUTER_API_KEY=sk-or-v1-votre-clé-openrouter-ici
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=gpt-4o-mini

# Alternative OpenAI (plus cher mais directe)
OPENAI_API_KEY=sk-votre-clé-openai-ici
EOF
```

### ✅ **Test de Validation Immédiat**

```bash
# Test rapide du système (2 minutes)
python examples/Sherlock_Watson/sherlock_watson_authentic_demo.py

# Sortie attendue:
# 🚀 LANCEMENT CONVERSATION SHERLOCK-WATSON AUTHENTIQUE
# ✅ JVM TweetyProject initialisée (35+ JARs chargés)
# ✅ Service LLM configuré (gpt-4o-mini)
# 🎭 Sherlock: "Excellente observation, Watson..."
# 🧠 Watson: "En effet Holmes, l'analyse logique révèle..."
```

---

## 🎯 **CONFIGURATION DÉTAILLÉE**

### 🐍 **Environnement Python Optimal**

#### **Option A: Conda (RECOMMANDÉ - Plus Stable)**
```bash
# Installation Conda si nécessaire
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh

# Création environnement optimisé
conda create --name projet-is python=3.9.18 pip
conda activate projet-is

# Installation packages critiques via conda
conda install numpy=1.24.3 pandas=2.0.3 -c conda-forge

# Installation semantic-kernel via pip
pip install semantic-kernel>=1.29.0
pip install -r requirements.txt
```

#### **Option B: venv (Alternative)**
```bash
# Création environnement virtuel
python3.9 -m venv venv-projet-is
source venv-projet-is/bin/activate  # Linux/Mac
# ou
venv-projet-is\Scripts\activate     # Windows

# Installation complète
pip install --upgrade pip
pip install -r requirements.txt
```

### ☕ **Configuration Java pour TweetyProject**

#### **Vérification Installation Java**
```bash
# Test Java présent
java -version
javac -version

# Si Java absent (Ubuntu/Debian)
sudo apt update
sudo apt install openjdk-8-jdk

# Si Java absent (CentOS/RHEL)
sudo yum install java-1.8.0-openjdk-devel

# Si Java absent (Windows)
# Télécharger depuis: https://adoptopenjdk.net/
```

#### **Configuration Variables Environnement**
```bash
# Linux/Mac - Ajout à ~/.bashrc ou ~/.zshrc
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH
export CLASSPATH=$JAVA_HOME/lib:$CLASSPATH

# Windows - Variables système
set JAVA_HOME=C:\Program Files\Java\jdk1.8.0_XXX
set PATH=%JAVA_HOME%\bin;%PATH%

# Vérification configuration
echo $JAVA_HOME  # Doit afficher chemin Java
which java       # Doit trouver exécutable
```

### 🔐 **Configuration APIs et Services**

#### **OpenRouter (RECOMMANDÉ - Économique)**
```bash
# 1. Création compte sur https://openrouter.ai
# 2. Génération clé API dans Settings > API Keys
# 3. Ajout crédits: $5 suffit pour exploration complète

# Configuration .env
cat >> .env << EOF
OPENROUTER_API_KEY=sk-or-v1-votre-vraie-clé-ici
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=gpt-4o-mini

# Modèles alternatifs disponibles
# OPENROUTER_MODEL=claude-3-haiku-20240307
# OPENROUTER_MODEL=gpt-3.5-turbo
EOF
```

#### **OpenAI (Alternative Directe)**
```bash
# 1. Création compte sur https://platform.openai.com
# 2. Génération clé API dans API keys
# 3. Ajout crédits: $10 recommandé

# Configuration .env  
cat >> .env << EOF
OPENAI_API_KEY=sk-votre-vraie-clé-openai-ici
OPENAI_ORG_ID=org-votre-organisation-id    # Optionnel
EOF
```

#### **Test Configuration API**
```python
# Script de test API (test_api_config.py)
import os
from dotenv import load_dotenv
import openai

load_dotenv()

# Test OpenRouter
if os.getenv("OPENROUTER_API_KEY"):
    openai.api_key = os.getenv("OPENROUTER_API_KEY")
    openai.api_base = os.getenv("OPENROUTER_BASE_URL")
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Test connection"}],
            max_tokens=10
        )
        print("✅ OpenRouter: Connexion réussie")
    except Exception as e:
        print(f"❌ OpenRouter: Erreur - {e}")

# Test OpenAI
elif os.getenv("OPENAI_API_KEY"):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Test connection"}],
            max_tokens=10
        )
        print("✅ OpenAI: Connexion réussie")
    except Exception as e:
        print(f"❌ OpenAI: Erreur - {e}")
else:
    print("❌ Aucune clé API configurée")
```

---

## 🎭 **UTILISATION DES DÉMONSTRATIONS**

### 🕵️ **Démo 1: Conversation Sherlock-Watson Authentique**

#### **Objectif et Contexte**
Cette démonstration met en scène une conversation naturelle entre Sherlock Holmes et Dr Watson utilisant l'orchestrateur `CluedoExtendedOrchestrator` sans aucune simulation.

#### **Exécution Standard**
```bash
# Lancement simple
python examples/Sherlock_Watson/sherlock_watson_authentic_demo.py

# Avec logs détaillés
python examples/Sherlock_Watson/sherlock_watson_authentic_demo.py --verbose

# Avec sauvegarde personnalisée
python examples/Sherlock_Watson/sherlock_watson_authentic_demo.py --output ./mon_trace.json
```

#### **Paramètres Configurables**
```python
# Configuration dans le script (ligne ~50)
ORCHESTRATION_CONFIG = {
    "max_iterations": 10,        # Nombre max tours conversation
    "temperature": 0.7,          # Créativité LLM (0.1-1.0)
    "response_length": 150,      # Longueur max réponses
    "personality_strength": 0.8, # Force personnalités (0.1-1.0)
}
```

#### **Interprétation des Résultats**
```json
{
  "session_id": "sherlock_watson_20250610_040000",
  "total_messages": 7,
  "participants": ["Sherlock", "Watson"],
  "metrics": {
    "naturalness_score": 8.5,
    "personality_distinctiveness": 7.8,
    "conversation_flow": 8.2
  },
  "conversation": [
    {
      "agent": "Sherlock",
      "content": "Watson, observez ces indices curieux...",
      "timestamp": "2025-06-10T04:00:15.123Z",
      "analysis": {
        "personality_markers": ["observez", "curieux"],
        "leadership_indicators": true,
        "deductive_reasoning": true
      }
    }
  ]
}
```

### 🎲 **Démo 2: Oracle Cluedo Complet**

#### **Validation Exhaustive du Système**
Cette démonstration exécute les 157 tests de validation du système Oracle sans aucune simulation.

#### **Exécution et Options**
```bash
# Test complet standard
python examples/Sherlock_Watson/cluedo_oracle_complete.py

# Test avec rapport détaillé
python examples/Sherlock_Watson/cluedo_oracle_complete.py --detailed-report

# Test avec vérification intégrité renforcée
python examples/Sherlock_Watson/cluedo_oracle_complete.py --strict-integrity

# Test performance (chronométrage)
python examples/Sherlock_Watson/cluedo_oracle_complete.py --benchmark
```

#### **Métriques de Validation**
```bash
# Résultats attendus
✅ Tests Oracle: 157/157 réussis (100%)
✅ Modules validés: 8/8
├── Oracle Dataset: ✅ Opérationnel
├── Permission Manager: ✅ Sécurisé  
├── Integrity Monitor: ✅ Actif
├── Card Revelation System: ✅ Contrôlé
├── Solution Validation: ✅ Fonctionnel
├── Agent Access Control: ✅ Renforcé
├── Anti-Cheat System: ✅ Activé
└── Performance Cache: ✅ Optimisé

✅ Temps total: 12.4 secondes
✅ Mémoire utilisée: 245 MB
✅ Violations détectées: 0
```

### 🤖 **Démo 3: Agents Logiques Production**

#### **Validation TweetyProject et Logique Formelle**
Démonstration des capacités logiques avancées avec `CustomDataProcessor` authentique.

#### **Prérequis Spécifiques**
```bash
# Vérification TweetyProject ready
ls libs/tweety/*.jar | wc -l  # Doit afficher 35+

# Test rapide JVM
python -c "
import jpype
print('JPype version:', jpype.__version__)
try:
    jpype.startJVM()
    print('✅ JVM démarrage OK')
    jpype.shutdownJVM()
except Exception as e:
    print('❌ Erreur JVM:', e)
"
```

#### **Exécution Avancée**
```bash
# Standard avec logique propositionnelle
python examples/Sherlock_Watson/agents_logiques_production.py

# Avec logique FOL (First-Order Logic)
python examples/Sherlock_Watson/agents_logiques_production.py --logic-type fol

# Avec validation contraintes complexes
python examples/Sherlock_Watson/agents_logiques_production.py --complex-constraints

# Mode debug avec traces TweetyProject
python examples/Sherlock_Watson/agents_logiques_production.py --debug-tweety
```

#### **Validation des Sorties**
```bash
# Sortie attendue détaillée
🚀 LANCEMENT AGENTS LOGIQUES PRODUCTION
✅ JVM TweetyProject prête (35+ JARs chargés)
📊 Mémoire JVM allouée: 512 MB
🧠 Watson: Activation TweetyProject Bridge
🔍 Chargement classes critiques:
  ├── PlParser: ✅ org.tweetyproject.logics.pl.parser.PlParser
  ├── PlBeliefSet: ✅ org.tweetyproject.logics.pl.syntax.PlBeliefSet
  ├── Sat4jSolver: ✅ org.tweetyproject.logics.pl.sat.Sat4jSolver
  └── FolParser: ✅ org.tweetyproject.logics.fol.parser.FolParser

🧮 Test logique propositionnelle:
  Formule: "(a && b) || c"
  Résultat: ✅ Consistante
  Temps: 0.15s

🎯 CustomDataProcessor actif:
  Source: Données réelles (non simulées)
  Processeur: Authentique sans mocks
  Validation: 100% opérationnel
```

### 🎼 **Démo 4: Orchestration Finale Réelle**

#### **Démonstration Complète du Système**
Script d'orchestration le plus avancé intégrant tous les composants avec Semantic Kernel.

#### **Configuration Avancée**
```python
# Configuration orchestration (editable dans le script)
ADVANCED_CONFIG = {
    "orchestration_strategy": "balanced_participation",
    "termination_strategy": "intelligent_conclusion",
    "max_agents_active": 3,
    "conversation_depth": "deep",         # shallow, medium, deep
    "logic_validation_level": "strict",   # loose, moderate, strict
    "personality_emphasis": "high",       # low, medium, high
    "performance_monitoring": True,
}
```

#### **Modes d'Exécution**
```bash
# Mode standard (recommandé)
python examples/Sherlock_Watson/orchestration_finale_reelle.py

# Mode investigation complexe
python examples/Sherlock_Watson/orchestration_finale_reelle.py --mode complex

# Mode pédagogique avec explications
python examples/Sherlock_Watson/orchestration_finale_reelle.py --pedagogical

# Mode benchmark performance
python examples/Sherlock_Watson/orchestration_finale_reelle.py --benchmark

# Mode custom avec configuration
python examples/Sherlock_Watson/orchestration_finale_reelle.py --config custom_config.json
```

#### **Analyse des Résultats Complets**
```json
{
  "orchestration_session": {
    "session_id": "orch_finale_20250610_040000",
    "duration_seconds": 45.8,
    "total_cycles": 6,
    "agents_participated": 3,
    "resolution_achieved": true
  },
  "agent_performance": {
    "Sherlock": {
      "turns": 3,
      "avg_response_time": 2.1,
      "leadership_score": 8.7,
      "deduction_quality": 8.5
    },
    "Watson": {
      "turns": 2,
      "avg_response_time": 3.2,
      "logic_validation_score": 9.1,
      "tweety_queries": 4
    },
    "Moriarty": {
      "turns": 1,
      "avg_response_time": 1.8,
      "revelation_strategy": "progressive",
      "oracle_accuracy": 100
    }
  },
  "system_metrics": {
    "semantic_kernel_health": "excellent",
    "memory_usage_mb": 387,
    "api_calls_total": 12,
    "api_cost_estimated": "$0.08"
  }
}
```

---

## 🔧 **PERSONNALISATION AVANCÉE**

### 🎨 **Modification des Personnalités d'Agents**

#### **Sherlock Holmes - Personnalisation**
```python
# Fichier: custom_personalities.py
SHERLOCK_CUSTOM_INSTRUCTIONS = """
Vous êtes Sherlock Holmes avec les modifications suivantes:

STYLE MODIFIÉ:
- Plus collaboratif et moins autoritaire
- Explication détaillée de vos déductions
- Encouragement actif des autres agents

SPÉCIALISATIONS AJOUTÉES:
- Expertise en criminologie moderne
- Connaissance technologies actuelles
- Approche psychologique des suspects

CONTRAINTES SPÉCIALES:
- Toujours demander confirmation à Watson avant conclusion
- Partager systématiquement votre raisonnement
- Éviter les accusations directes sans preuves
"""

# Application dans le code
sherlock_agent = SherlockEnqueteAgent(
    kernel=kernel,
    agent_name="Sherlock_Custom",
    service_id="openai_chat",
    instructions=SHERLOCK_CUSTOM_INSTRUCTIONS
)
```

#### **Watson - Spécialisation Logique**
```python
WATSON_ENHANCED_INSTRUCTIONS = """
Vous êtes Dr Watson avec spécialisations techniques:

EXPERTISE RENFORCÉE:
- Maîtrise logique formelle (TweetyProject expert)
- Analyse statistique et probabiliste
- Validation scientifique rigoureuse

COMPORTEMENT MODIFIÉ:
- Propositions proactives d'analyses
- Questions techniques pertinentes
- Synthèses logiques structurées

OUTILS PRIVILÉGIÉS:
- Validation systématique via TweetyProject
- Calculs de probabilités
- Vérification cohérence logique
"""
```

### 🔮 **Extension du Système Oracle**

#### **Nouveau Dataset Personnalisé**
```python
# Création dataset custom
class CustomOracleDataset:
    """Oracle personnalisé pour énigmes spécialisées"""
    
    def __init__(self, domain: str):
        self.domain = domain
        self.custom_data = self._load_domain_data(domain)
        
    def _load_domain_data(self, domain: str) -> Dict:
        """Chargement données spécialisées par domaine"""
        datasets = {
            "histoire": self._load_historical_mysteries(),
            "science": self._load_scientific_puzzles(),
            "litterature": self._load_literary_enigmas(),
            "mathematiques": self._load_math_problems()
        }
        return datasets.get(domain, {})
    
    def _load_historical_mysteries(self) -> Dict:
        """Mystères historiques authentiques"""
        return {
            "jack_the_ripper": {
                "suspects": ["Montague Druitt", "Aaron Kosminski", "Thomas Cutbush"],
                "indices": ["Lettre Dear Boss", "Graffiti Goulston Street", "Témoignages"],
                "lieux": ["Whitechapel", "Spitalfields", "Mile End"]
            },
            "anastasia_romanov": {
                "prétendantes": ["Anna Anderson", "Eugenia Smith", "Nadezhda Vasilyeva"],
                "preuves": ["ADN", "Cicatrices", "Langues parlées"],
                "contexte": ["Révolution russe", "Massacre Ekaterinbourg", "Exil"]
            }
        }
```

#### **Stratégies de Révélation Personnalisées**
```python
class ProgressiveHintStrategy:
    """Stratégie de révélation d'indices progressive personnalisable"""
    
    def __init__(self, difficulty_level: str = "medium"):
        self.difficulty = difficulty_level
        self.hint_schedule = self._calculate_hint_schedule()
        
    def _calculate_hint_schedule(self) -> List[Dict]:
        """Calcul planning révélations selon difficulté"""
        schedules = {
            "easy": [
                {"turn": 2, "type": "direct_clue", "strength": 0.8},
                {"turn": 4, "type": "elimination", "strength": 0.9},
                {"turn": 6, "type": "confirmation", "strength": 1.0}
            ],
            "medium": [
                {"turn": 3, "type": "indirect_clue", "strength": 0.6},
                {"turn": 6, "type": "partial_elimination", "strength": 0.7},
                {"turn": 9, "type": "directed_hint", "strength": 0.8}
            ],
            "hard": [
                {"turn": 5, "type": "subtle_hint", "strength": 0.4},
                {"turn": 10, "type": "contradiction", "strength": 0.6},
                {"turn": 15, "type": "final_nudge", "strength": 0.7}
            ]
        }
        return schedules.get(self.difficulty, schedules["medium"])
```

### ⚙️ **Configuration des Stratégies d'Orchestration**

#### **Stratégie de Sélection Personnalisée**
```python
class ExpertiseBasedSelectionStrategy(SelectionStrategy):
    """Sélection agent basée sur expertise contextuelle"""
    
    def __init__(self):
        self.expertise_map = {
            "logical_reasoning": ["Watson"],
            "deductive_investigation": ["Sherlock"], 
            "information_revelation": ["Moriarty"],
            "collaborative_analysis": ["Sherlock", "Watson"],
            "contradiction_resolution": ["Watson", "Moriarty"]
        }
        
    async def next(self, agents: List[Agent], history: List[ChatMessage]) -> Agent:
        # Analyse contexte récent
        recent_context = self._analyze_recent_context(history[-3:])
        
        # Identification expertise requise
        required_expertise = self._identify_required_expertise(recent_context)
        
        # Sélection agent optimal
        suitable_agents = self.expertise_map.get(required_expertise, agents)
        
        return self._select_least_recently_used(suitable_agents, history)
```

---

## 🛠️ **RÉSOLUTION DE PROBLÈMES**

### ❌ **Erreurs Fréquentes et Solutions Détaillées**

#### **Erreur 1: JPype/TweetyProject Initialization**
```bash
# SYMPTÔME
JPypeException: Unable to start JVM: No such file or directory

# DIAGNOSTIC
python -c "
import jpype
print('JPype Path:', jpype.getDefaultJVMPath())
import os
print('JAVA_HOME:', os.getenv('JAVA_HOME'))
"

# SOLUTIONS
# Solution 1: Java non installé
sudo apt install openjdk-8-jdk  # Ubuntu/Debian
brew install openjdk@8          # macOS

# Solution 2: JAVA_HOME incorrect
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH

# Solution 3: Version Java incompatible
java -version  # Doit être 1.8+ (Java 8+)
```

#### **Erreur 2: Semantic Kernel Module**
```bash
# SYMPTÔME
ImportError: No module named 'semantic_kernel'

# DIAGNOSTIC
pip list | grep semantic

# SOLUTIONS
# Solution 1: Installation manquante
pip install semantic-kernel>=1.29.0

# Solution 2: Environnement incorrect
conda activate projet-is  # Vérifier activation
which python              # Vérifier environnement

# Solution 3: Version incompatible
pip install --upgrade semantic-kernel
pip list | grep semantic  # Vérifier version >=1.29.0
```

#### **Erreur 3: API Authentication**
```bash
# SYMPTÔME
openai.AuthenticationError: Invalid API key

# DIAGNOSTIC
cat .env | grep API_KEY
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('OpenRouter Key:', os.getenv('OPENROUTER_API_KEY')[:10] + '...')
print('OpenAI Key:', os.getenv('OPENAI_API_KEY')[:10] + '...')
"

# SOLUTIONS
# Solution 1: Clé API absente/incorrecte
# - Vérifier .env existe et contient clé
# - Régénérer clé sur openrouter.ai ou platform.openai.com

# Solution 2: Permissions insuffisantes
# - Vérifier crédits disponibles sur le compte
# - Vérifier limites d'usage non dépassées

# Solution 3: Configuration proxy/firewall
# - Tester connexion: curl https://openrouter.ai/api/v1/models
# - Configurer proxy si nécessaire
```

### 🔍 **Debugging Avancé**

#### **Mode Debug Complet**
```python
# Script de debug (debug_system.py)
import logging
import sys
import traceback
from pathlib import Path

# Configuration logging détaillé
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('debug_system.log')
    ]
)

def debug_system_components():
    """Diagnostic complet des composants système"""
    
    print("🔍 DIAGNOSTIC SYSTÈME COMPLET")
    print("=" * 50)
    
    # 1. Environnement Python
    print(f"Python: {sys.version}")
    print(f"Plateforme: {sys.platform}")
    
    # 2. Modules critiques
    critical_modules = [
        'semantic_kernel', 'jpype', 'openai', 
        'numpy', 'pandas', 'dotenv'
    ]
    
    for module in critical_modules:
        try:
            mod = __import__(module)
            version = getattr(mod, '__version__', 'Unknown')
            print(f"✅ {module}: {version}")
        except ImportError as e:
            print(f"❌ {module}: Non installé - {e}")
    
    # 3. Configuration environnement
    from dotenv import load_dotenv
    load_dotenv()
    
    env_vars = [
        'JAVA_HOME', 'OPENROUTER_API_KEY', 'OPENAI_API_KEY'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            masked = value[:10] + "..." if len(value) > 10 else value
            print(f"✅ {var}: {masked}")
        else:
            print(f"❌ {var}: Non défini")
    
    # 4. TweetyProject JARs
    tweety_dir = Path("libs/tweety")
    if tweety_dir.exists():
        jars = list(tweety_dir.glob("*.jar"))
        print(f"✅ TweetyProject JARs: {len(jars)} trouvés")
    else:
        print("❌ TweetyProject JARs: Dossier libs/tweety non trouvé")
    
    # 5. Test JVM
    try:
        import jpype
        jpype.startJVM()
        print("✅ JVM: Démarrage réussi")
        jpype.shutdownJVM()
    except Exception as e:
        print(f"❌ JVM: Erreur - {e}")

if __name__ == "__main__":
    debug_system_components()
```

#### **Profiling Performance**
```python
# Script profiling (profile_performance.py)
import time
import psutil
import cProfile
import pstats
from memory_profiler import profile

@profile
def profile_orchestration():
    """Profiling mémoire orchestration"""
    # Import avec timing
    start_time = time.time()
    
    from examples.Sherlock_Watson.orchestration_finale_reelle import main
    import_time = time.time() - start_time
    print(f"Import time: {import_time:.2f}s")
    
    # Exécution avec profiling
    start_memory = psutil.virtual_memory().used / 1024 / 1024  # MB
    
    result = main()
    
    end_memory = psutil.virtual_memory().used / 1024 / 1024  # MB
    memory_used = end_memory - start_memory
    
    print(f"Memory used: {memory_used:.1f} MB")
    return result

def profile_cpu():
    """Profiling CPU détaillé"""
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Exécution code à profiler
    profile_orchestration()
    
    profiler.disable()
    
    # Analyse résultats
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 fonctions
```

---

## 📊 **MÉTRIQUES ET ANALYSE**

### 📈 **Métriques de Performance Système**

#### **Monitoring Temps Réel**
```python
# Script monitoring (monitor_system.py)
import time
import psutil
import threading
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class SystemMetrics:
    timestamp: float
    cpu_percent: float
    memory_mb: float
    api_calls: int
    response_time: float

class SystemMonitor:
    """Monitoring système en temps réel"""
    
    def __init__(self):
        self.metrics_history: List[SystemMetrics] = []
        self.monitoring = False
        
    def start_monitoring(self):
        """Démarrage monitoring en arrière-plan"""
        self.monitoring = True
        monitor_thread = threading.Thread(target=self._monitor_loop)
        monitor_thread.daemon = True
        monitor_thread.start()
        
    def _monitor_loop(self):
        """Boucle monitoring continue"""
        while self.monitoring:
            metrics = SystemMetrics(
                timestamp=time.time(),
                cpu_percent=psutil.cpu_percent(),
                memory_mb=psutil.virtual_memory().used / 1024 / 1024,
                api_calls=self._count_api_calls(),
                response_time=self._measure_response_time()
            )
            self.metrics_history.append(metrics)
            time.sleep(1.0)  # Échantillonnage chaque seconde
            
    def generate_report(self) -> Dict:
        """Génération rapport de performance"""
        if not self.metrics_history:
            return {"error": "Aucune métrique collectée"}
            
        cpu_avg = sum(m.cpu_percent for m in self.metrics_history) / len(self.metrics_history)
        memory_avg = sum(m.memory_mb for m in self.metrics_history) / len(self.metrics_history)
        memory_peak = max(m.memory_mb for m in self.metrics_history)
        
        return {
            "duration_seconds": len(self.metrics_history),
            "performance": {
                "cpu_average": round(cpu_avg, 1),
                "memory_average_mb": round(memory_avg, 1),
                "memory_peak_mb": round(memory_peak, 1)
            },
            "api_usage": {
                "total_calls": self._count_total_api_calls(),
                "average_response_time": self._calculate_avg_response_time()
            }
        }
```

#### **Métriques Qualité Conversation**
```python
class ConversationQualityAnalyzer:
    """Analyseur qualité conversation multi-agents"""
    
    def analyze_conversation(self, messages: List[Dict]) -> Dict:
        """Analyse qualité complète conversation"""
        
        return {
            "personality_distinctiveness": self._measure_personality_distinction(messages),
            "conversation_naturalness": self._measure_naturalness(messages),
            "flow_continuity": self._measure_flow_continuity(messages),
            "logical_coherence": self._measure_logical_coherence(messages),
            "engagement_level": self._measure_engagement(messages)
        }
    
    def _measure_personality_distinction(self, messages: List[Dict]) -> float:
        """Mesure distinction personnalités agents"""
        agent_characteristics = {}
        
        for msg in messages:
            agent = msg['agent']
            content = msg['content'].lower()
            
            # Analyse markers personnalité
            sherlock_markers = ['observe', 'déduction', 'évident', 'elementary']
            watson_markers = ['analyse', 'logique', 'médical', 'validation']
            moriarty_markers = ['révèle', 'oracle', 'mystérieux', 'secret']
            
            if agent not in agent_characteristics:
                agent_characteristics[agent] = []
                
            if agent.lower() == 'sherlock':
                score = sum(1 for marker in sherlock_markers if marker in content)
            elif agent.lower() == 'watson':
                score = sum(1 for marker in watson_markers if marker in content)
            elif agent.lower() == 'moriarty':
                score = sum(1 for marker in moriarty_markers if marker in content)
            else:
                score = 0
                
            agent_characteristics[agent].append(score)
        
        # Calcul score distinction
        total_distinction = 0
        for agent, scores in agent_characteristics.items():
            avg_score = sum(scores) / len(scores) if scores else 0
            total_distinction += min(avg_score, 1.0)  # Cap à 1.0 par agent
            
        return min(total_distinction / len(agent_characteristics), 10.0) if agent_characteristics else 0.0
```

---

## 🎓 **CAS D'USAGE PÉDAGOGIQUES**

### 🎯 **Pour Étudiants en Intelligence Artificielle**

#### **TP 1: Découverte Systèmes Multi-Agents**
```bash
# Objectif: Comprendre coordination agents
# Durée: 2 heures
# Niveau: Débutant

# 1. Exécution conversation simple
python examples/Sherlock_Watson/sherlock_watson_authentic_demo.py

# 2. Analyse logs générés
cat logs/sherlock_watson_conversation_*.json | jq .

# 3. Questions d'analyse:
# - Comment les agents se coordonnent-ils?
# - Quels patterns de communication observe-t-on?
# - Comment les personnalités se distinguent-elles?

# 4. Exercice: Modifier température LLM et observer impact
# Editer le script, changer temperature de 0.7 à 0.3 puis 0.9
```

#### **TP 2: Logique Formelle avec TweetyProject**
```bash
# Objectif: Maîtriser raisonnement logique symbolique
# Durée: 3 heures  
# Niveau: Intermédiaire

# 1. Test logique propositionnelle simple
python examples/Sherlock_Watson/agents_logiques_production.py --logic-type pl

# 2. Formulation contraintes Einstein
python examples/Sherlock_Watson/agents_logiques_production.py --scenario examples/Sherlock_Watson/einstein_scenario.json

# 3. Exercices progressifs:
# - Formuler "Si A alors B" en logique formelle
# - Tester cohérence: A, A→B, ¬B
# - Déduire conclusions via TweetyProject

# 4. Projet: Créer nouvelle énigme logique
# Utiliser template Watson pour validation formelle
```

#### **TP 3: Orchestration Avancée**
```bash
# Objectif: Comprendre patterns orchestration
# Durée: 4 heures
# Niveau: Avancé

# 1. Orchestration standard
python examples/Sherlock_Watson/orchestration_finale_reelle.py

# 2. Modification stratégies sélection
# Editer et tester différentes SelectionStrategy

# 3. Métriques personnalisées
# Implémenter nouveau MetricsCollector

# 4. Challenge: Système 4 agents
# Ajouter nouvel agent spécialisé
```

### 🔬 **Pour Recherche Académique**

#### **Recherche 1: Performance Multi-Agents**
```python
# Protocole expérimental standardisé
def experimental_protocol():
    """Protocole recherche performance multi-agents"""
    
    # Variables indépendantes
    configurations = [
        {"agents": 2, "strategy": "round_robin"},
        {"agents": 3, "strategy": "balanced"},
        {"agents": 3, "strategy": "expertise_based"},
        {"agents": 4, "strategy": "hierarchical"}
    ]
    
    # Variables dépendantes mesurées
    metrics = [
        "resolution_time",
        "message_count", 
        "solution_accuracy",
        "conversation_quality"
    ]
    
    # Protocole expérimental
    for config in configurations:
        for trial in range(10):  # 10 répétitions par configuration
            result = run_orchestration_trial(config)
            record_experimental_data(config, result, trial)
    
    # Analyse statistique
    perform_anova_analysis()
    generate_research_report()
```

#### **Recherche 2: Évaluation Qualité Dialogue**
```python
# Framework évaluation dialogue IA
class DialogueEvaluationFramework:
    """Framework recherche qualité dialogue multi-agents"""
    
    def __init__(self):
        self.evaluation_dimensions = [
            "coherence_score",      # Cohérence logique
            "informativeness",      # Richesse informative
            "naturalness",          # Naturel conversation
            "personality_consistency", # Consistance personnalité
            "goal_achievement"      # Atteinte objectifs
        ]
    
    def evaluate_session(self, conversation: List[Dict]) -> Dict:
        """Évaluation complète session dialogue"""
        
        scores = {}
        for dimension in self.evaluation_dimensions:
            scores[dimension] = getattr(self, f"_evaluate_{dimension}")(conversation)
        
        # Score composite
        scores["overall_quality"] = sum(scores.values()) / len(scores)
        
        return scores
    
    def _evaluate_coherence_score(self, conversation: List[Dict]) -> float:
        """Évaluation cohérence via analyse sémantique"""
        # Implémentation analyse cohérence avec NLP
        pass
    
    def _evaluate_personality_consistency(self, conversation: List[Dict]) -> float:
        """Évaluation consistance personnalités"""
        # Analyse marqueurs linguistiques caractéristiques
        pass
```

---

## 🏆 **CONCLUSION**

Ce guide utilisateur complet vous donne tous les outils nécessaires pour maîtriser le système Sherlock/Watson/Moriarty, depuis l'installation de base jusqu'aux utilisations avancées en recherche. 

**🎯 Points Clés** :
- **Configuration robuste** avec gestion d'erreurs détaillée
- **Démonstrations progressives** du simple au complexe  
- **Personnalisation complète** pour adaptations spécifiques
- **Métriques avancées** pour évaluation rigoureuse
- **Cas d'usage pédagogiques** structurés et progressifs

**🚀 Prochaines Étapes Recommandées** :
1. Commencer par le démarrage rapide (5 minutes)
2. Tester les 4 démonstrations principales  
3. Explorer la personnalisation selon vos besoins
4. Implémenter vos propres cas d'usage

---

*Guide mis à jour - Version 2.1.0 - 10/06/2025*  
*Documentation exhaustive pour utilisation optimale du système*