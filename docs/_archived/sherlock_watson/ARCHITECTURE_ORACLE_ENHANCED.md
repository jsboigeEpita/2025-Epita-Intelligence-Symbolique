# Documentation Technique Oracle Enhanced

## Architecture du Système

### 1. Composants Principaux

#### 1.1 Agent Oracle de Base (`OracleBaseAgent`)
- **Responsabilité**: Classe de base pour tous les agents Oracle
- **Fonctionnalités**: 
  - Gestion des requêtes Oracle
  - Système de permissions
  - Logging des interactions
  - Cache des réponses

#### 1.2 Agent Moriarty Interrogateur (`MoriartyInterrogatorAgent`)  
- **Responsabilité**: Agent Oracle spécialisé pour Cluedo
- **Fonctionnalités**:
  - Validation des suggestions Cluedo
  - Révélation automatique de cartes
  - Simulation des réponses d'autres joueurs
  - Stratégies de révélation avancées

#### 1.3 Dataset Cluedo (`CluedoDataset`)
- **Responsabilité**: Gestion des données du jeu Cluedo
- **Fonctionnalités**:
  - Solution secrète protégée
  - Historique des révélations
  - Validation d'intégrité
  - Statistiques du jeu

### 2. Flux de Données

```
Agent → DatasetAccessManager → CluedoDataset → Oracle Response
  ↓            ↓                     ↓              ↓
Permissions → QueryCache → ValidationRules → LoggedResponse
```

### 3. Gestion des Erreurs

- `OracleError`: Erreur de base
- `OraclePermissionError`: Erreurs de permissions
- `CluedoIntegrityError`: Violations des règles Cluedo
- `OracleValidationError`: Erreurs de validation

### 4. Configuration

```python
DEFAULT_ORACLE_CONFIG = {
    "max_revelations_per_agent": 3,
    "revelation_strategy": "strategic", 
    "cache_size": 1000,
    "cache_ttl": 300,
    "enable_logging": True
}
```

## Guide d'Utilisation

### Initialisation Système Oracle

```python
from argumentation_analysis.agents.core.oracle import (
    CluedoDataset, 
    CluedoDatasetManager,
    MoriartyInterrogatorAgent
)

# 1. Créer le dataset
dataset = CluedoDataset()

# 2. Créer le gestionnaire d'accès
manager = CluedoDatasetManager(dataset)

# 3. Créer l'agent Oracle
oracle_agent = MoriartyInterrogatorAgent(
    dataset_manager=manager,
    name="Moriarty",
    llm_service_id="OpenAI"
)
```

### Exécution d'une Requête Oracle

```python
# Validation d'une suggestion
response = await oracle_agent.validate_suggestion_cluedo(
    suspect="Colonel Moutarde",
    arme="Chandelier", 
    lieu="Bibliothèque",
    suggesting_agent="Sherlock"
)

print(response.data)  # Résultat de la validation
```

## Tests et Validation

### Tests Unitaires
- `test_oracle_base_agent.py`: Tests agent de base
- `test_moriarty_interrogator_agent.py`: Tests agent Moriarty
- `test_cluedo_dataset.py`: Tests dataset Cluedo
- `test_dataset_access_manager.py`: Tests gestionnaire d'accès

### Tests d'Intégration
- `test_oracle_integration.py`: Tests d'intégration Oracle
- `test_cluedo_extended_workflow.py`: Tests workflow complet

### Couverture des Tests
- **Cible**: 100% de couverture
- **Statut actuel**: 105/105 tests Oracle passent
- **Métriques**: Tous les composants Oracle couverts
