# Guide de l'Agent de Logique Modale

## Vue d'ensemble

L'agent de logique modale (`ModalLogicAgent`) est un nouvel agent logique qui permet d'analyser du texte en utilisant la logique modale. Il suit l'architecture robuste éprouvée des agents FOL et PL existants.

## Fonctionnalités

### Opérateurs modaux supportés
- `[]` (nécessité) : "il est nécessaire que"
- `<>` (possibilité) : "il est possible que"
- Connecteurs logiques standard : `!`, `&&`, `||`, `=>`, `<=>`

### Méthodes principales
1. **`text_to_belief_set`** : Convertit un texte en ensemble de croyances modales
2. **`generate_queries`** : Génère des requêtes modales pertinentes
3. **`execute_query`** : Exécute une requête modale sur un ensemble de croyances
4. **`interpret_results`** : Interprète les résultats en langage naturel
5. **`validate_formula`** : Valide la syntaxe d'une formule modale

## Structure JSON pour la logique modale

L'agent génère et utilise une structure JSON spécifique :

```json
{
  "propositions": ["il_pleut", "jean_travaille", "routes_mouillees"],
  "modal_formulas": [
    "[]il_pleut",
    "<>jean_travaille", 
    "il_pleut => []routes_mouillees"
  ]
}
```

## Utilisation

### Via la LogicAgentFactory

```python
from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
import semantic_kernel as sk

# Créer le kernel et ajouter le service LLM
kernel = sk.Kernel()
kernel.add_service(llm_service)

# Créer l'agent de logique modale
modal_agent = LogicAgentFactory.create_agent("modal", kernel, llm_service.service_id)
```

### Utilisation directe

```python
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
import semantic_kernel as sk

# Créer le kernel et ajouter le service LLM
kernel = sk.Kernel()
kernel.add_service(llm_service)

# Créer l'agent directement
modal_agent = ModalLogicAgent(kernel=kernel, service_id=llm_service.service_id)
modal_agent.setup_agent_components(llm_service.service_id)
```

### Exemple complet

```python
import asyncio

async def analyze_modal_text():
    text = "Il pleut nécessairement. Il est possible que Jean travaille."
    
    # Convertir en ensemble de croyances
    belief_set, status = await modal_agent.text_to_belief_set(text)
    
    if belief_set:
        print(f"Ensemble de croyances créé : {belief_set.logic_type}")
        
        # Générer des requêtes
        queries = await modal_agent.generate_queries(text, belief_set)
        print(f"Requêtes générées : {queries}")
        
        # Exécuter les requêtes
        results = []
        for query in queries:
            result, raw_output = modal_agent.execute_query(belief_set, query)
            results.append((result, raw_output))
        
        # Interpréter les résultats
        interpretation = await modal_agent.interpret_results(text, belief_set, queries, results)
        print(f"Interprétation : {interpretation}")

# Exécuter l'analyse
asyncio.run(analyze_modal_text())
```

## Tests et démonstration

### Script de test dédié
Un script de test complet est disponible dans `scripts/demo/test_modal_logic_agent.py` :

```bash
cd d:/2025-Epita-Intelligence-Symbolique-4
python scripts/demo/test_modal_logic_agent.py
```

### Intégration dans le script de démo principal
L'agent est maintenant intégré dans `scripts/demo/run_rhetorical_analysis_demo.py` et peut être utilisé avec l'option `--logic-type modal`.

## Architecture et intégration

### Héritage de BaseLogicAgent
L'agent hérite de `BaseLogicAgent` et implémente toutes les méthodes abstraites requises.

### Intégration avec TweetyBridge
L'agent utilise le `modal_handler` du `TweetyBridge` pour :
- Parser les formules modales
- Valider la syntaxe
- Exécuter les requêtes (via TweetyProject)
- Vérifier la cohérence

### Types de logique modale supportés
- **S4** (par défaut) : logique modale avec réflexivité et transitivité
- **K** : logique modale de base
- Extensible pour d'autres systèmes modaux

## Limitations actuelles

1. **Reasoner TweetyProject** : L'implémentation actuelle du `modal_handler` utilise des placeholders pour certaines fonctionnalités de raisonnement avancées.

2. **Validation contextuelle** : La validation avec TweetyProject peut être limitée selon la disponibilité des composants Java.

3. **Types de logique** : Actuellement optimisé pour S4, mais extensible.

## Logs et transparence

L'agent inclut des logs détaillés pour tracer son comportement :
- Conversion texte → ensemble de croyances
- Génération et validation des requêtes
- Exécution et interprétation des résultats
- Gestion d'erreurs robuste

## Exemples de textes supportés

1. **Nécessité simple** : "Il pleut nécessairement."
2. **Possibilité** : "Il est possible que Jean travaille."
3. **Implication modale** : "S'il pleut, alors il est nécessaire que les routes soient mouillées."
4. **Combinaisons complexes** : "Il est possible que Marie soit présente. Si Marie est présente, alors il est nécessaire que la réunion ait lieu."

L'agent est maintenant prêt à être utilisé aux côtés des agents FOL et PL dans le système d'analyse argumentative.