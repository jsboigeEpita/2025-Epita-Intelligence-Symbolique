# Guide Développeur Oracle Enhanced v2.1.0

## 🚀 Environnement de Développement

### Prérequis
- Python 3.9+
- Conda/Miniconda
- Git
- IDE avec support Python (VSCode recommandé)

### Configuration Initiale
```bash
# 1. Cloner le projet
git clone <repository_url>
cd 2025-Epita-Intelligence-Symbolique

# 2. Configurer l'environnement
powershell -File .\scripts\env\activate_project_env.ps1

# 3. Vérifier installation
python -c "from argumentation_analysis.agents.core.oracle import get_oracle_version; print(get_oracle_version())"
# Output attendu: 2.1.0
```

## 🏗️ Architecture de Développement

### Structure Modulaire Oracle
```
argumentation_analysis/agents/core/oracle/
├── __init__.py                     # Exports consolidés + métadonnées
├── oracle_base_agent.py           # Classe de base pour agents Oracle
├── moriarty_interrogator_agent.py # Implémentation Moriarty Oracle
├── cluedo_dataset.py              # Gestion données Cluedo + intégrité
├── dataset_access_manager.py      # Gestionnaire permissions + cache
├── permissions.py                 # Système permissions granulaire
├── error_handling.py              # 🆕 Gestion erreurs centralisée
└── interfaces.py                  # 🆕 Interfaces ABC standardisées
```

### Patterns de Développement

#### 1. Création Nouvel Agent Oracle
```python
from argumentation_analysis.agents.core.oracle import (
    OracleBaseAgent, OracleAgentInterface, StandardOracleResponse,
    oracle_error_handler, OracleValidationError
)

class MonNouvelOracleAgent(OracleBaseAgent, OracleAgentInterface):
    """Nouvel agent Oracle avec interfaces standardisées"""
    
    def __init__(self, dataset_manager, **kwargs):
        super().__init__(dataset_manager=dataset_manager, **kwargs)
        
    @oracle_error_handler("process_custom_request")
    async def process_oracle_request(self, requesting_agent: str, 
                                   query_type: str, query_params: dict) -> dict:
        # Validation métier
        if not self._validate_custom_request(query_params):
            raise OracleValidationError("Paramètres invalides")
            
        # Traitement Oracle spécialisé
        result = await self._process_custom_logic(requesting_agent, query_params)
        
        # Réponse standardisée
        return StandardOracleResponse(
            success=True,
            data=result,
            message=f"Request processed for {requesting_agent}"
        ).to_dict()
        
    def _validate_custom_request(self, params: dict) -> bool:
        """Validation métier spécialisée"""
        return "required_field" in params
        
    async def _process_custom_logic(self, agent: str, params: dict) -> dict:
        """Logique Oracle spécialisée"""
        return {"processed": True, "agent": agent}
```

#### 2. Extension Dataset Manager
```python
from argumentation_analysis.agents.core.oracle import (
    DatasetAccessManager, DatasetManagerInterface, 
    QueryType, OracleDatasetError
)

class MonDatasetManager(DatasetAccessManager, DatasetManagerInterface):
    """Dataset manager spécialisé avec validation custom"""
    
    def execute_query(self, agent_name: str, query_type: str, 
                     query_params: dict) -> dict:
        # Validation permissions héritée
        if not self.check_permission(agent_name, query_type):
            raise OraclePermissionError(f"Access denied for {agent_name}")
            
        # Logique spécialisée
        if query_type == "custom_query":
            return self._handle_custom_query(agent_name, query_params)
            
        # Déléguer au parent pour queries standard
        return super().execute_query(agent_name, query_type, query_params)
        
    def _handle_custom_query(self, agent: str, params: dict) -> dict:
        """Gestionnaire query custom"""
        return {"custom_result": f"Processed for {agent}"}
```

## 🧪 Développement Piloté par les Tests

### Workflow TDD Oracle Enhanced

#### 1. Écriture Tests d'abord
```python
# test_mon_nouvel_agent.py
import pytest
from unittest.mock import Mock

from argumentation_analysis.agents.core.oracle import (
    StandardOracleResponse, OracleValidationError
)
from mon_module import MonNouvelOracleAgent

class TestMonNouvelOracleAgent:
    def setup_method(self):
        self.mock_dataset_manager = Mock()
        self.agent = MonNouvelOracleAgent(
            dataset_manager=self.mock_dataset_manager,
            name="TestOracle"
        )
        
    @pytest.mark.asyncio
    async def test_process_oracle_request_success(self):
        """Test traitement requête Oracle réussie"""
        result = await self.agent.process_oracle_request(
            "Sherlock", "custom_query", {"required_field": "value"}
        )
        
        assert result["success"] is True
        assert result["data"]["processed"] is True
        assert "Sherlock" in result["message"]
        
    @pytest.mark.asyncio
    async def test_process_oracle_request_validation_error(self):
        """Test gestion erreur validation"""
        with pytest.raises(OracleValidationError):
            await self.agent.process_oracle_request(
                "Watson", "custom_query", {}  # Manque required_field
            )
```

#### 2. Implémentation Minimale
```python
# Implémentation juste pour faire passer les tests
class MonNouvelOracleAgent(OracleBaseAgent):
    async def process_oracle_request(self, requesting_agent, query_type, query_params):
        if "required_field" not in query_params:
            raise OracleValidationError("required_field manquant")
        return {"success": True, "data": {"processed": True}, "message": f"Processed for {requesting_agent}"}
```

#### 3. Refactorisation et Amélioration
```python
# Refactorisation avec interfaces complètes
class MonNouvelOracleAgent(OracleBaseAgent, OracleAgentInterface):
    # Implémentation complète comme dans l'exemple précédent
```

### Exécution Tests en Développement

```bash
# Tests module spécifique
pytest tests/unit/argumentation_analysis/agents/core/oracle/test_mon_module.py -v

# Tests avec couverture
pytest tests/unit/argumentation_analysis/agents/core/oracle/ --cov=argumentation_analysis.agents.core.oracle --cov-report=term-missing

# Tests intégration
pytest tests/integration/test_oracle_integration.py -v

# Validation couverture complète
python scripts/maintenance/validate_oracle_coverage.py
```

## 🔍 Debugging et Monitoring

### Logging Avancé Oracle
```python
import logging
from argumentation_analysis.agents.core.oracle.error_handling import OracleErrorHandler

# Configuration logging Oracle
logging.basicConfig(level=logging.DEBUG)
oracle_logger = logging.getLogger("oracle.debug")

# Handler erreurs avec logging
error_handler = OracleErrorHandler(logger=oracle_logger)

# Dans votre agent
class DebuggableOracleAgent(OracleBaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.error_handler = error_handler
        
    async def process_oracle_request(self, agent, query_type, params):
        oracle_logger.info(f"Processing {query_type} for {agent}")
        oracle_logger.debug(f"Parameters: {params}")
        
        try:
            result = await self._internal_process(agent, query_type, params)
            oracle_logger.info(f"Success: {result}")
            return result
        except Exception as e:
            error_info = self.error_handler.handle_oracle_error(e, f"agent={agent}")
            oracle_logger.error(f"Oracle error: {error_info}")
            raise
```

### Métriques en Temps Réel
```python
# Collecte métriques Oracle
def get_oracle_metrics(agent: OracleBaseAgent) -> dict:
    """Collecte métriques Oracle en temps réel"""
    return {
        "oracle_stats": agent.get_oracle_statistics(),
        "error_stats": agent.error_handler.get_error_statistics() if hasattr(agent, 'error_handler') else {},
        "cache_stats": agent.dataset_manager.cache.get_stats() if hasattr(agent.dataset_manager, 'cache') else {}
    }

# Monitoring continu
import time
while True:
    metrics = get_oracle_metrics(mon_agent_oracle)
    print(f"Oracle Metrics: {metrics}")
    time.sleep(10)
```

## 📦 Build et Déploiement

### Préparation Release
```bash
# 1. Tests complets
python scripts/maintenance/validate_oracle_coverage.py

# 2. Validation intégrité
python -m pytest tests/ -x --tb=short

# 3. Build documentation
python scripts/maintenance/update_documentation.py

# 4. Package version
python setup.py sdist bdist_wheel

# 5. Commit et tag
git add .
git commit -m "Release Oracle Enhanced v2.1.0"
git tag v2.1.0
git push origin main --tags
```

### Intégration Continue
```yaml
# .github/workflows/oracle-ci.yml
name: Oracle Enhanced CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.9
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    - name: Run Oracle tests
      run: |
        python scripts/maintenance/validate_oracle_coverage.py
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

## 🎯 Bonnes Pratiques

### Code Style Oracle
- **PEP 8**: Respect strict (utiliser `black` formatter)
- **Type hints**: Obligatoires pour toutes les méthodes publiques
- **Docstrings**: Format Google/NumPy avec exemples
- **Imports**: Ordre: stdlib, tiers, projet (utilisez `isort`)

### Gestion Erreurs
- **Toujours** utiliser les classes d'erreurs Oracle spécialisées
- **Jamais** catch `Exception` générique dans le code Oracle
- **Toujours** logger contexte d'erreur avec `oracle_error_handler`

### Tests
- **Couverture 100%** obligatoire pour nouveau code Oracle
- **Tests unitaires** isolés avec mocks appropriés
- **Tests d'intégration** pour workflows complets
- **Tests de performance** pour optimisations critiques

---
*Guide Développeur Oracle Enhanced v2.1.0 - Mise à jour automatique*
