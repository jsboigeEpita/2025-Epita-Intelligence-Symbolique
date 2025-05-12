# Tutoriel 4: Ajout d'un nouvel agent spécialiste

## Objectif
Apprendre à concevoir, implémenter et intégrer un nouvel agent dans l'architecture hiérarchique

## Conception de l'agent
```python
# Définition de l'interface d'un agent standard
class BaseAgent:
    def __init__(self, config):
        self.config = config
    
    async def analyze(self, text, context):
        """Méthode principale d'analyse"""
        raise NotImplementedError
    
    def get_results(self):
        """Récupération des résultats formatés"""
        raise NotImplementedError
```

## Implémentation d'un agent de détection de biais
```python
# agents/bias_detector_agent.py
from argumentiation_analysis.orchestration.hierarchical.operational.adapters.base_agent import BaseAgent

class BiasDetectorAgent(BaseAgent):
    def __init__(self, config):
        super().__init__(config)
        self.bias_taxonomy = self._load_bias_taxonomy()
    
    async def analyze(self, text, context):
        # Implémentation spécifique de détection de biais
        results = {
            "biases": [],
            "confidence": 0.0
        }
        
        # Analyse du texte pour détecter les biais
        for bias_type in self.bias_taxonomy:
            if self._detect_bias(text, bias_type):
                results["biases"].append({
                    "type": bias_type,
                    "description": self.bias_taxonomy[bias_type]["description"]
                })
        
        # Calcul de la confiance
        results["confidence"] = len(results["biases"]) / len(self.bias_taxonomy)
        return results
    
    def get_results(self):
        return self._format_results()
```

## Intégration dans le système
```python
# Mise à jour du registre d'agents
from argumentiation_analysis.orchestration.hierarchical.strategic.planner import register_agent

register_agent("bias_detector", BiasDetectorAgent)

# Configuration d'exemple
config = {
    "agents": {
        "extract": "ExtractAgent",
        "informal": "InformalAgent",
        "pl": "PLAgent",
        "bias_detector": "BiasDetectorAgent"
    }
}
```

## Tests et validation
```python
# tests/test_bias_detector_agent.py
import pytest
from agents.bias_detector_agent import BiasDetectorAgent

def test_bias_detection():
    config = {"sensitivity": 0.7}
    agent = BiasDetectorAgent(config)
    
    text = "Les solutions technologiques sont toujours les meilleures, car les humains sont imprévisibles."
    
    results = agent.analyze(text, {})
    assert len(results["biases"]) >= 1
    assert any(bias["type"] == "overgeneralization" for bias in results["biases"])
    assert 0 <= results["confidence"] <= 1
```

## Exercice pratique
1. Créer un nouvel agent pour détecter les arguments d'autorité
2. Implémenter la méthode d'analyse spécifique
3. Intégrer l'agent dans le système d'orchestration
4. Écrire des tests unitaires pour valider son fonctionnement

## Références
- Architecture des agents: `docs/architecture_hierarchique_trois_niveaux.md`
- Exemple d'agent: `orchestration/hierarchical/operational/adapters/extract_agent_adapter.py`
- Tests d'intégration: `tests/test_operational_agents_integration.py`