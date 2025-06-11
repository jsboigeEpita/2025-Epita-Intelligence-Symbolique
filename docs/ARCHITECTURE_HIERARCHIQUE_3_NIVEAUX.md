# 🏗️ Architecture Hiérarchique 3 Niveaux - Documentation Technique

Documentation technique de l'architecture hiérarchique du système d'Intelligence Symbolique EPITA.

## 🎯 **Vue d'Ensemble**

Le système d'intelligence symbolique implémente une **architecture hiérarchique à 3 niveaux** dans `argumentation_analysis/orchestration/hierarchical/`. Cette architecture suit le modèle **Strategic → Tactical → Operational** pour une orchestration sophistiquée des agents et services.

---

## 🏗️ **Structure Hiérarchique Validée**

### **📁 Organisation Physique**
```
argumentation_analysis/orchestration/hierarchical/
├── strategic/                      # 🎯 NIVEAU STRATÉGIQUE
│   ├── __init__.py
│   ├── strategic_manager.py        # Gestionnaire allocation ressources
│   ├── resource_allocator.py       # Allocation intelligente
│   └── global_planner.py           # Planification globale
├── tactical/                       # ⚙️ NIVEAU TACTIQUE  
│   ├── __init__.py
│   ├── tactical_resolver.py        # Résolution tactique
│   ├── workflow_coordinator.py     # Coordination workflows
│   └── agent_coordinator.py        # Coordination agents
└── operational/                    # 🔧 NIVEAU OPÉRATIONNEL
    ├── __init__.py
    ├── task_executor.py           # Exécution tâches
    ├── agent_adapters.py          # Adaptateurs agents
    └── adapters/                  # Adaptateurs spécialisés
        ├── extract_agent_adapter.py
        ├── logic_agent_adapter.py
        └── informal_agent_adapter.py
```

---

## 🎯 **Niveau Stratégique** - `strategic/`

### **Responsabilités**
- **Allocation des ressources** globales du système
- **Planification à long terme** des analyses
- **Priorisation des tâches** selon les objectifs
- **Gestion des politiques** d'orchestration

### **Composants Principaux**

#### **📋 Strategic Manager** - `strategic_manager.py`
```python
class StrategicManager:
    """
    Gestionnaire principal du niveau stratégique
    - Allocation des ressources systèmes
    - Planification des workflows globaux
    - Définition des priorités d'analyse
    """
    
    def allocate_resources(self, analysis_request):
        """Alloue les ressources pour une demande d'analyse"""
        
    def plan_global_workflow(self, objectives):
        """Planifie le workflow global selon les objectifs"""
        
    def set_analysis_priorities(self, context):
        """Définit les priorités d'analyse selon le contexte"""
```

#### **🎯 Resource Allocator** - `resource_allocator.py`
```python
class ResourceAllocator:
    """
    Allocation intelligente des ressources
    - Agents disponibles et leurs spécialités
    - Capacités de traitement LLM
    - Mémoire et stockage temporaire
    """
    
    def allocate_agents(self, task_requirements):
        """Alloue les agents selon les besoins de la tâche"""
        
    def manage_llm_resources(self, analysis_complexity):
        """Gère les ressources LLM selon la complexité"""
```

#### **📊 Global Planner** - `global_planner.py`
```python
class GlobalPlanner:
    """
    Planification globale des analyses
    - Stratégies d'analyse selon le type de texte
    - Coordination inter-niveaux
    - Optimisation des performances
    """
    
    def create_analysis_strategy(self, text_analysis_request):
        """Crée une stratégie d'analyse globale"""
        
    def optimize_workflow_path(self, available_resources):
        """Optimise le chemin de workflow"""
```

---

## ⚙️ **Niveau Tactique** - `tactical/`

### **Responsabilités**
- **Coordination des agents** spécialisés
- **Gestion des workflows** d'analyse
- **Synchronisation** entre niveaux
- **Résolution tactique** des conflits

### **Composants Principaux**

#### **🎯 Tactical Resolver** - `tactical_resolver.py`
```python
class TacticalResolver:
    """
    Résolution tactique des demandes d'analyse
    - Traduction stratégie → actions concrètes
    - Coordination des agents spécialisés
    - Gestion des dépendances entre tâches
    """
    
    def resolve_analysis_strategy(self, strategic_plan):
        """Résout une stratégie en actions tactiques"""
        
    def coordinate_specialized_agents(self, agent_requirements):
        """Coordonne les agents spécialisés"""
        
    def manage_task_dependencies(self, workflow_tasks):
        """Gère les dépendances entre tâches"""
```

#### **🔄 Workflow Coordinator** - `workflow_coordinator.py`
```python
class WorkflowCoordinator:
    """
    Coordination des workflows d'analyse
    - Séquençage des étapes d'analyse
    - Gestion des états intermédiaires
    - Synchronisation avec le niveau opérationnel
    """
    
    def sequence_analysis_steps(self, tactical_plan):
        """Séquence les étapes d'analyse"""
        
    def manage_intermediate_states(self, workflow_state):
        """Gère les états intermédiaires du workflow"""
```

#### **🤖 Agent Coordinator** - `agent_coordinator.py`
```python
class AgentCoordinator:
    """
    Coordination spécialisée des agents
    - Sherlock Holmes (enquête et déduction)
    - Dr Watson (logique formelle)
    - Professor Moriarty (oracle et validation)
    """
    
    def coordinate_sherlock_watson(self, investigation_request):
        """Coordonne Sherlock et Watson pour investigation"""
        
    def engage_moriarty_oracle(self, validation_request):
        """Engage Moriarty comme oracle pour validation"""
```

---

## 🔧 **Niveau Opérationnel** - `operational/`

### **Responsabilités**
- **Exécution concrète** des tâches
- **Interface avec les agents** spécialisés
- **Traitement des données** en temps réel
- **Adaptation aux spécificités** de chaque agent

### **Composants Principaux**

#### **⚡ Task Executor** - `task_executor.py`
```python
class TaskExecutor:
    """
    Exécution des tâches opérationnelles
    - Traitement des requêtes d'analyse
    - Execution des agents spécialisés
    - Collecte et agrégation des résultats
    """
    
    def execute_analysis_task(self, operational_task):
        """Exécute une tâche d'analyse opérationnelle"""
        
    def run_specialized_agent(self, agent_config, input_data):
        """Exécute un agent spécialisé"""
        
    def aggregate_results(self, agent_results):
        """Agrège les résultats des agents"""
```

#### **🔌 Agent Adapters** - `agent_adapters.py`
```python
class AgentAdapters:
    """
    Adaptateurs pour agents spécialisés
    - ExtractAgent (extraction d'arguments)
    - LogicAgent (analyse logique formelle)
    - InformalAgent (analyse rhétorique)
    """
    
    def adapt_extract_agent(self, extraction_request):
        """Adapte l'ExtractAgent aux besoins spécifiques"""
        
    def adapt_logic_agent(self, logic_analysis_request):
        """Adapte le LogicAgent pour analyse formelle"""
        
    def adapt_informal_agent(self, rhetorical_request):
        """Adapte l'InformalAgent pour analyse rhétorique"""
```

### **🔧 Adaptateurs Spécialisés** - `adapters/`

#### **📝 Extract Agent Adapter** - `extract_agent_adapter.py`
```python
class ExtractAgentAdapter:
    """
    Adaptateur spécialisé pour ExtractAgent
    - Extraction d'arguments du texte
    - Identification de structures argumentatives
    - Interface avec le niveau tactique
    """
    
    def extract_arguments(self, text_input):
        """Extrait les arguments du texte"""
        
    def identify_argumentative_structures(self, extracted_content):
        """Identifie les structures argumentatives"""
```

#### **🧠 Logic Agent Adapter** - `logic_agent_adapter.py`
```python
class LogicAgentAdapter:
    """
    Adaptateur spécialisé pour LogicAgent
    - Analyse logique formelle avec TweetyProject
    - Validation de cohérence logique
    - Interface avec JPype pour Java
    """
    
    def perform_formal_logic_analysis(self, logical_statements):
        """Effectue une analyse logique formelle"""
        
    def validate_logical_consistency(self, argument_structure):
        """Valide la cohérence logique"""
```

#### **💬 Informal Agent Adapter** - `informal_agent_adapter.py`
```python
class InformalAgentAdapter:
    """
    Adaptateur spécialisé pour InformalAgent
    - Analyse rhétorique et détection de sophismes
    - Évaluation de la qualité argumentative
    - Interface avec les analyseurs contextuels
    """
    
    def analyze_rhetorical_structure(self, argument_content):
        """Analyse la structure rhétorique"""
        
    def detect_fallacies(self, rhetorical_analysis):
        """Détecte les sophismes dans l'analyse"""
```

---

## 🔄 **Flux d'Orchestration Hiérarchique**

### **📊 Diagramme de Flux**
```
┌─────────────────────────────────────────────────────────────┐
│                    NIVEAU STRATÉGIQUE                      │
│  📋 Strategic Manager → 🎯 Resource Allocator → 📊 Planner │
└─────────────────────┬───────────────────────────────────────┘
                      │ Stratégie Globale
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    NIVEAU TACTIQUE                         │
│  🎯 Tactical Resolver → 🔄 Workflow Coordinator → 🤖 Agent │
└─────────────────────┬───────────────────────────────────────┘
                      │ Plan Tactique
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  NIVEAU OPÉRATIONNEL                       │
│  ⚡ Task Executor → 🔌 Agent Adapters → 🔧 Spécialisés    │
└─────────────────────────────────────────────────────────────┘
```

### **🔄 Exemple de Flux Complet**

#### **1. Requête d'Analyse**
```python
# Niveau Stratégique
strategic_manager = StrategicManager()
strategy = strategic_manager.create_global_strategy(
    text="Analyse argumentative complexe",
    objectives=["detect_fallacies", "validate_logic", "extract_structure"]
)

# Allocation des ressources
resource_allocator = ResourceAllocator()
resources = resource_allocator.allocate_for_strategy(strategy)
```

#### **2. Résolution Tactique**
```python
# Niveau Tactique
tactical_resolver = TacticalResolver()
tactical_plan = tactical_resolver.resolve_strategy(strategy, resources)

# Coordination des agents
agent_coordinator = AgentCoordinator()
agent_assignments = agent_coordinator.assign_agents_to_tasks(tactical_plan)
```

#### **3. Exécution Opérationnelle**
```python
# Niveau Opérationnel
task_executor = TaskExecutor()
results = []

for assignment in agent_assignments:
    adapter = task_executor.get_adapter(assignment.agent_type)
    result = adapter.execute_task(assignment.task, assignment.parameters)
    results.append(result)

# Agrégation des résultats
final_result = task_executor.aggregate_results(results)
```

---

## 🎯 **Patterns d'Orchestration Identifiés**

### **🔄 Pattern Command-Control**
L'architecture implémente un pattern command-control strict :
- **Strategic** : Commande et définit la stratégie
- **Tactical** : Contrôle et coordonne l'exécution
- **Operational** : Exécute et rapporte les résultats

### **📡 Pattern Observer**
Communication inter-niveaux via pattern observer :
```python
class HierarchicalObserver:
    def notify_level_change(self, level, status, data):
        """Notifie les changements entre niveaux"""
        
    def propagate_results(self, from_level, to_level, results):
        """Propage les résultats entre niveaux"""
```

### **🏭 Pattern Factory**
Création d'agents et adaptateurs via factory :
```python
class AgentAdapterFactory:
    def create_adapter(self, agent_type, configuration):
        """Crée l'adaptateur approprié selon le type d'agent"""
        
    def configure_for_level(self, adapter, hierarchical_level):
        """Configure l'adaptateur pour le niveau hiérarchique"""
```

---

## 🧪 **Tests et Validation**

### **📋 Tests Hiérarchiques Validés**
```bash
# Tests niveau stratégique
python -m pytest tests/unit/orchestration/hierarchical/strategic/ -v

# Tests niveau tactique
python -m pytest tests/unit/orchestration/hierarchical/tactical/ -v

# Tests niveau opérationnel
python -m pytest tests/unit/orchestration/hierarchical/operational/ -v

# Tests intégration hiérarchique
python -m pytest tests/unit/orchestration/test_hierarchical_managers.py -v
```

### **🔧 Tests d'Adaptateurs**
```bash
# Tests adaptateurs spécialisés
python -m pytest tests/unit/orchestration/hierarchical/operational/adapters/ -v

# Test extract agent adapter
python -m pytest tests/unit/orchestration/hierarchical/operational/adapters/test_extract_agent_adapter.py -v
```

---

## 🏆 **Avantages de l'Architecture**

### **✅ Séparation des Responsabilités**
- **Strategic** : Vision globale et allocation ressources
- **Tactical** : Coordination et synchronisation
- **Operational** : Exécution et adaptation

### **✅ Scalabilité**
- Ajout facile de nouveaux agents au niveau opérationnel
- Extension des stratégies au niveau stratégique
- Coordination flexible au niveau tactique

### **✅ Maintenance**
- Code modulaire et responsabilités claires
- Tests par niveau avec isolation
- Documentation technique détaillée

### **✅ Performance**
- Allocation optimisée des ressources
- Parallélisation possible au niveau opérationnel
- Cache et réutilisation au niveau tactique

---

## 📚 **Documentation Technique Complète**

### **🔍 Références**
- **[Tests Hiérarchiques](../tests/unit/orchestration/hierarchical/)** - Tests validation architecture
- **[Adaptateurs Opérationnels](../tests/unit/orchestration/hierarchical/operational/adapters/)** - Tests adaptateurs
- **[Patterns d'Orchestration](./guides/GUIDE_PATTERNS_ORCHESTRATION_MODES.md)** - Patterns et bonnes pratiques

### **📖 Guides d'Utilisation**
- **[Guide Développeur](./GUIDE_DEVELOPPEUR_ARCHITECTURE.md)** - Développement avec architecture
- **[Guide Utilisateur](./GUIDE_UTILISATEUR_ARCHITECTURE.md)** - Utilisation pratique
- **[Exemples Concrets](../examples/)** - Implémentations réelles

---

## 🏆 **Conclusion**

L'architecture hiérarchique 3 niveaux constitue le **cœur du système d'intelligence symbolique**. Elle offre une orchestration sophistiquée, une séparation claire des responsabilités, et une scalabilité optimale pour les analyses argumentatives complexes.

### **✅ Points Clés**
- 🏗️ **Architecture structurée** avec tests complets
- 🎯 **3 niveaux distincts** avec responsabilités claires
- 🔧 **Adaptateurs spécialisés** pour chaque agent
- 🧪 **Tests hiérarchiques** documentés et fonctionnels
- 📚 **Documentation technique** complète et accessible

**📢 Architecture hiérarchique moderne pour le développement d'agents intelligents.**
