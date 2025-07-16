# Conception du Harnais de Tests d'Intégration

Ce document décrit la stratégie et l'architecture pour le harnais de tests d'intégration du projet d'analyse de sophismes. L'objectif est de valider de bout en bout le bon fonctionnement de la famille d'agents.

## 1. Outils (Tooling)

Pour assurer la robustesse et la maintenabilité de nos tests, nous utiliserons les outils suivants :

*   **`pytest`**: Un framework de test puissant et flexible qui sera notre exécuteur de tests principal.
*   **`pytest-asyncio`**: Une extension pour `pytest` indispensable pour tester notre code asynchrone, notamment les appels aux agents basés sur Semantic Kernel.

Ces dépendances devront être ajoutées à un fichier `requirements.txt` ou un framework de gestion de dépendances équivalent (comme Poetry ou PDM) pour garantir un environnement de test reproductible.

## 2. Structure des Répertoires

Nous adopterons une structure de répertoires claire et standard pour isoler les tests du code de l'application :

```
.
├── argumentation_analysis/
├── docs/
│   └── INTEGRATION_TESTING_DESIGN.md
└── tests/
    ├── __init__.py
    └── integration/
        ├── __init__.py
        ├── test_agent_family.py
        └── test_cases.json
```

*   Un répertoire `tests/` à la racine contiendra l'ensemble de notre code de test.
*   Un sous-répertoire `integration/` sera dédié spécifiquement aux tests d'intégration.

## 3. Stratégie des Données de Test

Pour découpler les données de test de la logique de test, nous utiliserons un fichier JSON centralisé : [`tests/integration/test_cases.json`](tests/integration/test_cases.json:1).

Ce fichier contiendra une liste d'objets, où chaque objet représente un cas de test avec la structure suivante :

*   `id` (string): Un identifiant unique pour le cas de test (ex: "ad_hominem_case_01").
*   `text` (string): Le texte d'entrée à fournir à l'agent pour analyse.
*   `expected_fallacies` (list[string]): Une liste des noms de sophismes (correspondant aux noms de fichiers de la taxonomie, sans extension) que l'agent est censé détecter dans le texte.

## 4. Stratégie d'Implémentation des Tests

Le fichier de test principal sera [`tests/integration/test_agent_family.py`](tests/integration/test_agent_family.py:1).

### Fixtures Pytest

Nous utiliserons des fixtures `pytest` pour gérer la configuration et le nettoyage des ressources :

*   Une fixture `kernel` sera responsable de l'initialisation du Kernel sémantique.
*   Une fixture `agent_factory` (avec une portée `module`) dépendra de la fixture `kernel` et instanciera `AgentFactory` une seule fois pour l'ensemble des tests du module.

### Paramétrisation des Tests

La fonction de test principale sera paramétrée pour atteindre une couverture exhaustive :

1.  Les cas de test seront chargés à partir du fichier [`test_cases.json`](tests/integration/test_cases.json:1).
2.  Les types d'agents seront récupérés à partir de l'énumération `AgentType`.
3.  Nous utiliserons `pytest.mark.parametrize` pour créer dynamiquement un test pour **chaque combinaison** d'un cas de test et d'un type d'agent.

### Stratégie d'Assertion

L'analyse de l'agent produit un résultat génératif, il est donc contre-productif d'effectuer des assertions sur le texte exact du résumé (`summary`). Nos assertions se concentreront sur la structure et la présence des résultats attendus :

1.  **Validation de la Structure**: Le dictionnaire de résultat doit contenir les clés `summary` et `findings`.
2.  **Présence de Résultats**: La liste `findings` ne doit pas être vide.
3.  **Vérification des Sophismes**: Nous vérifierons que l'ensemble des sophismes définis dans `expected_fallacies` pour un cas de test donné est un **sous-ensemble** des noms de sophismes retournés dans la liste `findings`. Cela permet à l'agent de trouver des sophismes supplémentaires sans faire échouer le test.

## 5. Exemples de Code

### Extrait de `test_cases.json`

```json
[
  {
    "id": "ad_hominem_case_01",
    "text": "N'écoutez pas son argument sur l'économie, il ne sait même pas s'habiller correctement. Son avis ne peut pas être pertinent.",
    "expected_fallacies": [
      "ad-hominem"
    ]
  }
]
```

### Pseudo-code pour `test_agent_family.py`

```python
import pytest
from argumentation_analysis.agents import AgentType, AgentFactory

# Une fonction helper pour charger les cas de test depuis le JSON
def load_test_cases():
    # ... logique pour ouvrir et lire tests/integration/test_cases.json
    pass

@pytest.fixture(scope="module")
def agent_factory() -> AgentFactory:
    """Initialise l'usine d'agents une seule fois par module."""
    return AgentFactory()

@pytest.mark.asyncio
@pytest.mark.parametrize("agent_type", list(AgentType))
@pytest.mark.parametrize("test_case", load_test_cases())
async def test_fallacy_detection_across_agents(agent_factory, agent_type, test_case):
    """
    Teste la détection de sophismes pour chaque agent avec chaque cas de test.
    """
    # 1. Création de l'agent via la factory
    agent = agent_factory.create_agent(agent_type)
    
    # 2. Exécution de l'analyse
    input_text = test_case["text"]
    result = await agent.analyze(input_text)
    
    # 3. Assertions
    assert result is not None
    assert "summary" in result
    assert "findings" in result
    assert isinstance(result["findings"], list)
    
    # On s'assure qu'au moins les sophismes attendus sont détectés
    found_fallacy_names = {finding["name"] for finding in result["findings"]}
    expected_fallacy_names = set(test_case["expected_fallacies"])
    
    assert expected_fallacy_names.issubset(found_fallacy_names)
