# API de `analysis_runner.py` (Orchestration Simple)

## Introduction

Le module `analysis_runner.py` (situé dans `argumentation_analysis/orchestration/`) fournit la fonction principale pour l'approche d'orchestration simple. Cette approche utilise un `AgentGroupChat` de Semantic Kernel pour coordonner les interactions entre les agents.

[Retour au README de l'Orchestration](./README.md)

## Fonction Principale

### `run_analysis_conversation(texte_a_analyser: str, llm_service, agents_to_include: Optional[List[str]] = None, verbose: bool = False, output_file: Optional[str] = None) -> Dict`

Cette fonction asynchrone est le point d'entrée pour lancer une analyse argumentative en utilisant l'orchestration simple.

**Paramètres :**
-   `texte_a_analyser` (str) : Le texte brut qui doit être analysé.
-   `llm_service` : L'instance du service LLM (par exemple, `OpenAIChatCompletion` ou `AzureChatCompletion`) à utiliser par les agents.
-   `agents_to_include` (Optional[List[str]], default=None) : Une liste optionnelle des noms des agents à inclure dans la conversation. Si `None`, tous les agents configurés sont inclus. Les noms d'agents typiques sont "pm", "informal", "pl", "extract".
-   `verbose` (bool, default=False) : Si `True`, affiche des logs détaillés pendant l'exécution de la conversation.
-   `output_file` (Optional[str], default=None) : Si un chemin de fichier est fourni, l'état final de l'analyse (`RhetoricalAnalysisState` sérialisé en JSON) sera sauvegardé dans ce fichier.

**Retourne :**
-   `Dict` : Un dictionnaire représentant l'état final de l'analyse (`RhetoricalAnalysisState` sérialisé).

**Fonctionnement :**
1.  **Isolation** : Crée à chaque appel des instances locales et neuves de :
    *   `RhetoricalAnalysisState` : Pour stocker l'état de l'analyse en cours.
    *   `StateManagerPlugin` : Encapsule l'état et expose des fonctions natives aux agents pour interagir avec l'état.
    *   `Kernel` (Semantic Kernel) : Le noyau sur lequel les agents et leurs plugins sont enregistrés.
    *   Tous les agents définis (par exemple, `ProjectManagerAgent`, `InformalAnalysisAgent`, `PropositionalLogicAgent`, `ExtractAgent`) en tant que `ChatCompletionAgent`.
    *   Les stratégies d'orchestration (`SimpleTerminationStrategy`, `DelegatingSelectionStrategy`).
2.  **Configuration** :
    *   Initialise le `Kernel` local avec le `llm_service` fourni et le `StateManagerPlugin` local.
    *   Appelle les fonctions `setup_*_kernel` de chaque agent inclus pour enregistrer leurs plugins et fonctions sémantiques/natives spécifiques sur ce `Kernel` local.
3.  **Exécution** :
    *   Crée une instance `AgentGroupChat` en lui passant la liste des agents configurés et les stratégies d'orchestration.
    *   Lance la conversation en appelant la méthode `invoke()` sur l'instance `AgentGroupChat`. Le texte initial à analyser est souvent passé comme premier message ou via une tâche initiale définie dans l'état.
    *   Gère la boucle d'échanges de messages entre les agents, où chaque agent peut appeler des fonctions (outils) ou désigner le prochain agent.
4.  **Suivi & Résultat** :
    *   Si `verbose` est `True`, logue et affiche les tours de conversation, y compris les appels d'outils et les réponses des agents.
    *   À la fin de la conversation (déterminée par la `TerminationStrategy`), l'état final de l'analyse (`RhetoricalAnalysisState`) est retourné.
    *   Si `output_file` est fourni, l'état final est sauvegardé dans ce fichier.

## Stratégies d'Orchestration Utilisées

-   **`SimpleTerminationStrategy`** (définie dans `argumentation_analysis/core/strategies.py`) :
    *   Arrête la conversation si la clé `final_conclusion` est présente et non vide dans l'état partagé.
    *   Arrête également la conversation si un nombre maximum de tours (configurable, par exemple `max_steps=25`) est atteint pour éviter les boucles infinies.
-   **`DelegatingSelectionStrategy`** (définie dans `argumentation_analysis/core/strategies.py`) :
    *   Choisit le prochain agent à intervenir.
    *   Priorise la désignation explicite : si un agent a désigné un `_next_agent_designated` dans l'état partagé, cet agent est sélectionné.
    *   Sinon, par défaut, retourne au `ProjectManagerAgent` après l'intervention d'un autre agent spécialiste, pour permettre au PM de réévaluer la situation et de déléguer la prochaine tâche.

## Exemple d'Appel

```python
import asyncio
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.orchestration.analysis_runner import run_analysis_conversation

async def main():
    llm_service = create_llm_service() # Assurez-vous que .env est configuré
    texte_a_analyser = "Les arguments pour cette loi sont faibles, mais ceux contre sont encore plus faibles."
    
    final_state = await run_analysis_conversation(
        texte_a_analyser=texte_a_analyser,
        llm_service=llm_service,
        verbose=True,
        output_file="analysis_results.json"
    )
    
    print("Analyse terminée. Résultats sauvegardés dans analysis_results.json")
    # print(final_state)

if __name__ == "__main__":
    asyncio.run(main())
```

Cette page sera complétée avec plus de détails sur la configuration des agents et les interactions spécifiques.