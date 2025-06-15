# Plan de Migration - AbstractLogicAgent → BaseLogicAgent

> **[✅ TERMINÉ]** Ce plan de migration a été exécuté avec succès le 14/06/2025. `AbstractLogicAgent` a été supprimé et ses fonctionnalités d'orchestration ont été intégrées dans `BaseLogicAgent`. Ce document est conservé pour référence historique.

## 🎯 Objectif

Migrer les fonctionnalités d'orchestration de tâches d'`AbstractLogicAgent` vers `BaseLogicAgent` pour unifier l'architecture des agents logiques, puis supprimer `AbstractLogicAgent` devenu obsolète.

## 📊 Analyse Comparative

### BaseLogicAgent (Architecture ACTIVE)
- ✅ **Héritage** : `BaseAgent + ABC`
- ✅ **Logique formelle** : `text_to_belief_set()`, `generate_queries()`, `execute_query()`
- ✅ **TweetyBridge** : Intégration avec solveurs logiques
- ✅ **Validation** : `validate_formula()`, `is_consistent()`
- ❌ **Orchestration** : Aucune gestion de tâches

### AbstractLogicAgent (Architecture OBSOLÈTE)
- ❌ **Héritage** : `ABC` uniquement (pas de `BaseAgent`)
- ✅ **Logique formelle** : Signatures similaires à `BaseLogicAgent`
- ❌ **TweetyBridge** : Non intégré
- ✅ **Orchestration** : `process_task()`, gestion complète des tâches

## 🔄 Méthodes à Migrer

### 1. **Interface d'Orchestration Principale**
```python
def process_task(self, task_id: str, task_description: str, state_manager: Any) -> Dict[str, Any]
```
- **Fonction** : Point d'entrée pour le traitement des tâches
- **Routage** : Analyse la description pour diriger vers les handlers appropriés

### 2. **Handlers de Tâches Spécialisés**
```python
def _handle_translation_task(self, task_id: str, task_description: str, state: Dict[str, Any], state_manager: Any) -> Dict[str, Any]
def _handle_query_task(self, task_id: str, task_description: str, state: Dict[str, Any], state_manager: Any) -> Dict[str, Any]
```
- **Translation** : Conversion texte → ensemble de croyances
- **Query** : Exécution de requêtes logiques + interprétation

### 3. **Utilitaires d'Extraction**
```python
def _extract_source_text(self, task_description: str, state: Dict[str, Any]) -> str
def _extract_belief_set_id(self, task_description: str) -> Optional[str]
```
- **Parsing** : Extraction d'informations depuis les descriptions de tâches

### 4. **Factory Method Abstraite**
```python
@abstractmethod
def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> BeliefSet
```
- **Instanciation** : Création de BeliefSet spécifiques au type de logique

## 🏗️ Plan de Migration Détaillé

### Phase 1 : Préparation de BaseLogicAgent

#### 1.1 Ajout d'Imports Nécessaires
```python
# Dans argumentation_analysis/agents/core/abc/agent_bases.py
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
```

#### 1.2 Extension de BaseLogicAgent
- **Ajouter** les méthodes d'orchestration comme méthodes concrètes
- **Maintenir** la compatibilité avec l'architecture existante
- **Préserver** l'interface TweetyBridge

### Phase 2 : Migration des Méthodes

#### 2.1 Migration du Process Task
```python
def process_task(self, task_id: str, task_description: str, state_manager: Any) -> Dict[str, Any]:
    """
    Traite une tâche assignée à l'agent logique.
    
    Migré depuis AbstractLogicAgent pour unifier l'architecture.
    """
    # Code complet de AbstractLogicAgent.process_task()
```

#### 2.2 Migration des Handlers
- Copie intégrale de `_handle_translation_task()`
- Copie intégrale de `_handle_query_task()`
- Adaptation pour utiliser `self.tweety_bridge` au lieu de méthodes abstraites

#### 2.3 Migration des Utilitaires
- Copie intégrale de `_extract_source_text()`
- Copie intégrale de `_extract_belief_set_id()`
- Ajout de `_create_belief_set_from_data()` comme méthode abstraite

### Phase 3 : Adaptation des Signatures

#### 3.1 Harmonisation des Méthodes Existantes
```python
# AVANT (AbstractLogicAgent)
def text_to_belief_set(self, text: str) -> Tuple[Optional[BeliefSet], str]

# APRÈS (BaseLogicAgent unifié)
def text_to_belief_set(self, text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[Optional[BeliefSet], str]
```

#### 3.2 Backward Compatibility
- Maintenir les signatures existantes dans BaseLogicAgent
- Adapter les appels dans les méthodes migrées

### Phase 4 : Mise à Jour des Agents Concrets

#### 4.1 Implémentation de _create_belief_set_from_data()
```python
# Dans ModalLogicAgent, PropositionalLogicAgent, etc.
def _create_belief_set_from_data(self, belief_set_data: Dict[str, Any]) -> BeliefSet:
    logic_type = belief_set_data.get("logic_type")
    content = belief_set_data.get("content", [])
    return ModalBeliefSet(content)  # Spécifique au type d'agent
```

### Phase 5 : Suppression d'AbstractLogicAgent

#### 5.1 Suppression des Fichiers
- `argumentation_analysis/agents/core/logic/abstract_logic_agent.py`

#### 5.2 Nettoyage des Exports
- Retirer de `argumentation_analysis/agents/core/logic/__init__.py`

#### 5.3 Mise à Jour de la Documentation
- Nettoyer `argumentation_analysis/agents/core/logic/README.md`

## 🧪 Plan de Validation

### Tests d'Intégration
1. **Vérifier** que tous les agents logiques héritent correctement de BaseLogicAgent étendu
2. **Tester** les nouvelles fonctionnalités d'orchestration sur ModalLogicAgent
3. **Valider** la backward compatibility des méthodes existantes

### Tests de Non-régression
1. **Exécuter** les tests existants sans modification
2. **Vérifier** que LogicFactory fonctionne toujours
3. **Tester** les scripts Sherlock & Watson

## 📋 Checklist d'Exécution

- [ ] **Phase 1** : Préparer BaseLogicAgent avec imports et structure
- [ ] **Phase 2** : Migrer les méthodes d'orchestration 
- [ ] **Phase 3** : Harmoniser les signatures de méthodes
- [ ] **Phase 4** : Implémenter _create_belief_set_from_data() dans les agents concrets
- [ ] **Phase 5** : Supprimer AbstractLogicAgent et nettoyer les références
- [ ] **Tests** : Valider la migration complète
- [ ] **Documentation** : Mettre à jour README.md

## 🎯 Résultat Final

Une architecture unifiée avec :
- ✅ **BaseLogicAgent** comme unique classe de base pour tous les agents logiques
- ✅ **Fonctionnalités complètes** : logique formelle + orchestration de tâches
- ✅ **TweetyBridge** intégré
- ✅ **Backward compatibility** préservée
- ✅ **Dette technique** éliminée

## 🚀 Prochaines Étapes

Une fois cette migration validée, procéder à la **Phase 3** de la mission : mise à jour de la documentation "Sherlock & Watson" pour refléter l'architecture consolidée.