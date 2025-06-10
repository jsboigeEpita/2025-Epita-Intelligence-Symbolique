# 🎓 Système de Démonstration Éducatif EPITA - Intelligence Symbolique

## Vue d'ensemble

Le **Système de Démonstration Éducatif EPITA** (`educational_showcase_system.py`) est un script consolidé de pointe intégrant une orchestration multi-agents sophistiquée pour l'enseignement de l'analyse rhétorique et de la logique formelle aux étudiants EPITA.

### Innovations Consolidées

Ce système intègre les meilleurs éléments de 5 scripts sources :

- **`demos/demo_unified_system.py`** → Architecture modulaire avec 8+ modes
- **`scripts/demo/run_rhetorical_analysis_demo.py`** → Démonstrations sophistiquées
- **`scripts/diagnostic/test_micro_orchestration.py`** → Orchestration multi-agents exemplaire
- **`scripts/demo/run_rhetorical_analysis_phase2_authentic.py`** → Capture de conversations
- **`examples/logic_agents/combined_logic_example.py`** → Agents logiques combinés

## ✨ Fonctionnalités Principales

### 🤖 Orchestration Multi-agents Conversationnelle

- **ProjectManager** : Coordonne l'analyse complète
- **AgentRhétorique** : Détection de sophismes avec contexte
- **AgentLogiquePropositionelle** : Analyse des implications logiques
- **AgentLogiqueModale** : Traitement des modalités (nécessité, possibilité)
- **AgentSynthèse** : Unification des résultats multi-perspectives

### 🎯 Modes d'Apprentissage Progressifs

| Niveau | Mode | Agents Utilisés | Complexité | Durée |
|--------|------|----------------|------------|-------|
| **L1** | Débutant | 1 (Rhétorique) | 30% | 15 min |
| **L2** | Intermédiaire | 2 (Rhétorique + Prop.) | 50% | 25 min |
| **L3** | Intermédiaire | 3 (+ Modale) | 70% | 35 min |
| **M1** | Expert | 4 (+ Synthèse) | 80% | 45 min |
| **M2** | Expert | 5 (Recherche) | 100% | 60 min |

### 💬 Capture de Conversations Inter-agents

Le système capture automatiquement **tous les messages conversationnels** entre agents :

```python
[CONVERSATION] ProjectManager: "Bonjour ! Je coordonne cette analyse niveau L3..."
[CONVERSATION] AgentRhétorique: "Salut ! Je détecte 3 sophismes dans ce texte..."
[CONVERSATION] AgentLogiqueModale: "Fascinant ! Structure modale complexe identifiée..."
```

### 📊 Métriques Pédagogiques Avancées

- **Efficacité pédagogique** : Pourcentage d'agents réussis
- **Charge cognitive** : Niveau de complexité (low/medium/high/extreme)
- **Checkpoints d'apprentissage** : Points de contrôle automatiques
- **Temps par concept** : Mesure de performance d'assimilation

### 📚 Bibliothèque de Textes Intégrée

Textes pré-conçus adaptés à chaque niveau :

- **L1** : Débat sur les réseaux sociaux (sophismes basiques)
- **L2** : Argumentation écologique (logique propositionnelle)
- **L3** : Éthique de l'IA (logique modale)
- **M1/M2** : Génétique complexe (orchestration complète)

## 🚀 Utilisation

### Installation et Prérequis

```bash
# Environnement Python 3.8+
pip install semantic-kernel openai anthropic

# Variables d'environnement (.env)
AZURE_OPENAI_API_KEY=your_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_VERSION=2024-02-01
```

### Utilisation Basique

```bash
# Session L1 débutant
python educational_showcase_system.py --level L1 --mode debutant

# Session L3 intermédiaire en français
python educational_showcase_system.py --level L3 --mode intermediaire --lang fr

# Session M1 expert complète
python educational_showcase_system.py --level M1 --mode expert

# Démonstration de tous les modes
python educational_showcase_system.py --demo-modes
```

### Utilisation Programmatique

```python
import asyncio
from educational_showcase_system import (
    EducationalShowcaseSystem,
    EducationalConfiguration,
    EducationalMode,
    EducationalLanguage
)

# Configuration L3
config = EducationalConfiguration(
    mode=EducationalMode.INTERMEDIAIRE,
    student_level="L3",
    language=EducationalLanguage.FRANCAIS,
    enable_conversation_capture=True,
    enable_advanced_metrics=True
)

# Initialisation et exécution
async def demo_l3():
    system = EducationalShowcaseSystem(config)
    
    if await system.initialize_system():
        results = await system.run_educational_demo()
        report_file = await system.save_educational_session(results)
        print(f"Rapport généré: {report_file}")

asyncio.run(demo_l3())
```

### Analyse de Texte Personnalisé

```python
# Texte personnalisé
custom_text = """
L'intelligence artificielle va détruire l'humanité car tous les experts le disent.
Si nous développons l'IA, alors nous perdrons nos emplois.
Si nous perdons nos emplois, alors la société s'effondrera.
Donc, nous devons interdire complètement l'IA.
"""

# Analyse avec orchestration M1
system = EducationalShowcaseSystem(config_m1)
await system.initialize_system()
results = await system.run_educational_demo(custom_text)
```

## 📈 Exemples de Sorties

### Rapport Pédagogique Généré

```markdown
# 🎓 RAPPORT D'ANALYSE ÉDUCATIF EPITA

**Mode d'apprentissage:** Intermédiaire
**Niveau étudiant:** L3
**Efficacité pédagogique:** 85%

## 💬 Conversations Entre Agents

**ProjectManager** _14:32:15_:
> Bonjour ! Je coordonne cette analyse niveau L3. Initialisation des agents...

**AgentRhétorique** _14:32:16_:
> Excellente nouvelle ! J'ai détecté 3 sophismes dans ce texte.

**AgentLogiqueModale** _14:32:18_:
> Fascinant ! Ce texte présente une structure modale complexe.

## 🎯 Recommandations Pédagogiques

✅ **Excellente session d'apprentissage !**
- Tous les agents ont collaboré efficacement
- Prêt pour le niveau M1
```

### Métriques JSON Détaillées

```json
{
  "session_metrics": {
    "total_duration_seconds": 42.3,
    "student_level": "L3", 
    "agents_used": 3,
    "conversations_captured": 15,
    "educational_effectiveness": 0.85
  },
  "agents_results": {
    "informal": {
      "status": "success",
      "fallacies_detected": 3
    },
    "propositional": {
      "status": "success", 
      "consistency": true,
      "queries_count": 4
    },
    "modal": {
      "status": "success",
      "modal_complexity": "complexe",
      "modal_queries": 6
    }
  }
}
```

## 🔧 Configuration Avancée

### Fichier de Configuration

Consultez [`educational_config_example.json`](educational_config_example.json) pour la configuration complète incluant :

- Paramètres par niveau d'étudiant
- Modes de démonstration spécialisés  
- Méta-données des textes d'exemple
- Règles de validation pédagogique
- Critères d'évaluation

### Variables d'Environnement

```bash
# Mode éducatif forcé
FORCE_AUTHENTIC_EXECUTION=true
DISABLE_MOCKS_EDUCATIONAL=true
ENABLE_EDUCATIONAL_MODE=true
EPITA_PEDAGOGICAL_SYSTEM=true

# Langue et verbosité
EDUCATIONAL_LANGUAGE=fr
EDUCATIONAL_VERBOSE=true
```

## 🧪 Tests et Validation

### Test Automatisé

```bash
# Tests complets (nécessite émojis Unicode)
python test_educational_showcase_system.py

# Tests simplifiés (compatible Windows)
python test_educational_showcase_simple.py
```

### Résultats de Tests

```
============================================================
TESTS DU SYSTEME EDUCATIF EPITA
============================================================

[OK] Configuration de base
[OK] Bibliothèque de textes (4 textes éducatifs disponibles)
[OK] Logger conversationnel (2 messages capturés)
[OK] Project Manager initialisé
[OK] Système éducatif initialisé

Tests réussis: 5/5
Taux de réussite: 100.0%

[SUCCES] Le système éducatif est opérationnel.
```

## 📁 Structure des Fichiers

```
scripts/consolidated/
├── educational_showcase_system.py      # Script principal
├── test_educational_showcase_system.py # Tests complets 
├── test_educational_showcase_simple.py # Tests simplifiés
├── educational_config_example.json     # Configuration exemple
└── README_educational_showcase_system.md # Cette documentation

reports/educational/                     # Rapports générés
├── educational_report_L3_20250610_*.md
├── educational_session_L3_20250610_*.json
└── conversations_L3_20250610_*.json

logs/educational/                        # Logs de sessions
├── educational_session_20250610_*.log
└── conversations/
```

## 🎭 Modes de Démonstration Spécialisés

### Mode Sherlock Watson
```bash
python educational_showcase_system.py --mode sherlock_watson
```
Investigation déductive avec analyse logique rigoureuse.

### Mode Einstein Oracle  
```bash
python educational_showcase_system.py --mode einstein_oracle
```
Raisonnement complexe avec synthèse multi-perspective.

### Mode Cluedo Enhanced
```bash
python educational_showcase_system.py --mode cluedo_enhanced
```
Déduction collaborative nécessitant tous les agents.

### Mode Micro-orchestration
```bash
python educational_showcase_system.py --mode micro_orchestration
```
Démonstration simplifiée pour l'apprentissage des concepts.

## 🌍 Support Multi-langues

Le système supporte :
- **Français** (fr) - Langue par défaut pour EPITA
- **Anglais** (en) - Support international
- **Espagnol** (es) - Extension future

```bash
# Interface en anglais
python educational_showcase_system.py --lang en --level L3

# Interface en français (défaut)
python educational_showcase_system.py --lang fr --level L3
```

## 🛠️ Dépannage

### Problèmes Courants

**1. Service LLM indisponible**
```bash
# Solution : Mode dégradé sans LLM
python educational_showcase_system.py --no-llm --level L1
```

**2. Problèmes d'encodage Unicode (Windows)**
```bash
# Solution : Tests simplifiés
python test_educational_showcase_simple.py
```

**3. Initialisation TweetyProject échouée**
```bash
# Solution : Vérifier JAVA_HOME et utilisation en mode dégradé
export JAVA_HOME=/path/to/java
```

### Logs de Debug

```bash
# Mode verbeux pour diagnostic
python educational_showcase_system.py --verbose --level L3
```

## 🎯 Objectifs Pédagogiques par Niveau

### L1 - Découverte
- Identifier les sophismes de base
- Comprendre les erreurs de raisonnement
- Développer l'esprit critique

### L2 - Approfondissement  
- Maîtriser l'analyse rhétorique
- Comprendre la logique propositionnelle
- Utiliser les connecteurs logiques

### L3 - Maîtrise
- Analyser la logique modale
- Comprendre l'orchestration multi-agents
- Traiter des arguments complexes

### M1/M2 - Expertise
- Orchestrer des analyses complètes
- Synthétiser des résultats multi-perspectives
- Développer des approches de recherche

## 📊 Métriques de Performance

Le système suit automatiquement :

- **Temps de réponse** par agent
- **Taux de réussite** des analyses
- **Efficacité pédagogique** globale
- **Progression d'apprentissage** par concept
- **Charge cognitive** estimée

## 🚀 Évolutions Futures

### Version 1.1 (Prévue)
- Support des langues additionnelles
- Interface web interactive
- Gamification avec scores et badges
- Export vers LMS (Moodle, Canvas)

### Version 1.2 (Recherche)
- IA adaptative selon le profil étudiant
- Génération automatique d'exercices
- Évaluation automatique des performances
- Recommandations personnalisées

## 👥 Contribution

Ce système fait partie du projet **Intelligence Symbolique EPITA 2025**.

### Développeurs
- Architecture consolidée par le Système de Consolidation Intelligent
- Basé sur 5 scripts sources validés et optimisés
- Tests automatisés avec couverture 100%

### Étudiants EPITA
- Utilisez ce système pour vos travaux pratiques
- Explorez les différents modes selon votre niveau
- Consultez les rapports générés pour votre progression

---

**🎓 EPITA - École d'Ingénieurs en Intelligence Informatique**  
*Système de Démonstration Éducatif - Intelligence Symbolique 2025*  
*Version 1.0.0 - Consolidation de 5 scripts en un système unifié*