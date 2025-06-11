# Agents Spécialistes et Outils d'Analyse

Ce document détaille les agents spécialistes et les outils d'analyse rhétorique et fallacieuse utilisés dans le système.

## Structure Générale d'un Agent d'Analyse

La plupart des agents d'analyse suivent une structure similaire, utilisant des services partagés comme le `LLMService` pour interagir avec les modèles de langage.

```python
import logging
from project_core.services.llm_service import LLMService
from project_core.services.cache_service import CacheService # Exemple, si utilisé

class BaseAnalysisAgent:
    def __init__(self, llm_service: LLMService, cache_service: CacheService = None, agent_name: str = "BaseAnalysisAgent"):
        self.llm_service = llm_service
        self.cache_service = cache_service # Optionnel, pour la mise en cache des résultats
        self.agent_name = agent_name
        self.logger = logging.getLogger(f"{self.agent_name}")
        self.logger.info(f"{self.agent_name} initialized.")

    def analyze(self, text: str, context: dict = None) -> dict:
        # Implémentation de base de l'analyse
        # Peut être surchargée par des agents spécifiques
        raise NotImplementedError("Chaque agent doit implémenter sa propre méthode d'analyse.")

    def _prepare_prompt(self, text: str, context: dict = None) -> str:
        # Préparation du prompt pour le LLM
        # Doit être adapté par chaque agent
        raise NotImplementedError("Chaque agent doit implémenter sa propre méthode de préparation de prompt.")

    def _process_llm_response(self, response: str) -> dict:
        # Traitement de la réponse du LLM
        # Doit être adapté par chaque agent
        raise NotImplementedError("Chaque agent doit implémenter sa propre méthode de traitement de réponse.")

# Exemple d'utilisation (conceptuel)
# from project_core.services.llm_service_factory import LLMServiceFactory
# llm_service = LLMServiceFactory.create_service("openai_gpt4") # ou autre configuration
# agent = BaseAnalysisAgent(llm_service=llm_service)
# try:
#     results = agent.analyze("Ceci est un texte à analyser.")
#     print(results)
# except NotImplementedError as e:
#     print(e)
```

## Outils d'Analyse des Sophismes et de la Rhétorique

Ces outils sont typiquement utilisés par des agents plus spécialisés ou des services d'analyse.

### 1. `ContextualFallacyAnalyzer`

**Source :** [`../../argumentation_analysis/agents/tools/analysis/contextual_fallacy_analyzer.py`](../../argumentation_analysis/agents/tools/analysis/contextual_fallacy_analyzer.py)

Analyse un argument dans son contexte pour identifier les sophismes potentiels en se basant sur une taxonomie.

**Constructeur :**
```python
def __init__(self, llm_service: LLMService, taxonomy_path: str = "config/fallacies_taxonomy.json", cache_service: CacheService = None):
    """
    Initialise le ContextualFallacyAnalyzer.

    Args:
        llm_service: Le service LLM à utiliser pour l'analyse.
        taxonomy_path: Chemin vers le fichier JSON de la taxonomie des sophismes.
        cache_service: Service de cache optionnel.
    """
    # ...
```

**Méthodes Principales :**
*   `analyze_fallacies(self, argument_context: str, argument_statement: str, num_fallacies_to_identify: int = 3) -> List[Dict[str, Any]]`: Identifie les sophismes dans un énoncé d'argument donné son contexte.

**Exemple d'Utilisation :**
```python
from argumentation_analysis.agents.tools.analysis.contextual_fallacy_analyzer import ContextualFallacyAnalyzer
from project_core.services.llm_service_factory import LLMServiceFactory

# Initialisation (nécessite un LLMService configuré et une taxonomie)
llm_service = LLMServiceFactory.create_service("default_llm") # Assurez-vous que 'default_llm' est configuré
analyzer = ContextualFallacyAnalyzer(llm_service=llm_service, taxonomy_path="config/fallacies_taxonomy.json")

argument_statement = "Tous les experts s'accordent à dire que ce produit est le meilleur, donc il doit l'être."
argument_context = "Discussion sur un forum marketing à propos d'un nouveau gadget."
fallacies = analyzer.analyze_fallacies(argument_context=argument_context, argument_statement=argument_statement)
for fallacy in fallacies:
    print(f"Sophisme: {fallacy['fallacy_name']}, Description: {fallacy['description']}, Sévérité: {fallacy.get('severity', 'N/A')}")
```

### 2. `FallacySeverityEvaluator`

**Source :** [`../../argumentation_analysis/agents/tools/analysis/fallacy_severity_evaluator.py`](../../argumentation_analysis/agents/tools/analysis/fallacy_severity_evaluator.py)

Évalue la sévérité d'un sophisme identifié dans un argument.

**Méthodes Principales :**
*   `evaluate_severity(self, argument: str, fallacy_type: str, fallacy_description: str) -> str`: Évalue la sévérité (par exemple, "faible", "moyenne", "élevée").

**Exemple d'Utilisation :**
```python
from argumentation_analysis.agents.tools.analysis.fallacy_severity_evaluator import FallacySeverityEvaluator
from project_core.services.llm_service_factory import LLMServiceFactory

llm_service = LLMServiceFactory.create_service("default_llm")
evaluator = FallacySeverityEvaluator(llm_service=llm_service)

argument_text = "Si nous autorisons le mariage homosexuel, alors bientôt les gens voudront épouser des animaux."
fallacy_type = "Pente Glissante"
fallacy_description = "Affirmer qu'une action initiale mènera inévitablement à une série de conséquences négatives sans preuve suffisante."
severity = evaluator.evaluate_severity(argument=argument_text, fallacy_type=fallacy_type, fallacy_description=fallacy_description)
print(f"Sévérité du sophisme '{fallacy_type}': {severity}")
```

### 3. `ComplexFallacyAnalyzer`

**Source :** [`../../argumentation_analysis/agents/tools/analysis/complex_fallacy_analyzer.py`](../../argumentation_analysis/agents/tools/analysis/complex_fallacy_analyzer.py)

Analyse des arguments complexes pour identifier des sophismes imbriqués ou des combinaisons de sophismes.

**Méthodes Principales :**
*   `analyze_complex_argument(self, argument_text: str, context: str = None) -> Dict[str, Any]`: Analyse un texte argumentatif complexe.

**Exemple d'Utilisation :**
```python
from argumentation_analysis.agents.tools.analysis.complex_fallacy_analyzer import ComplexFallacyAnalyzer
from project_core.services.llm_service_factory import LLMServiceFactory

llm_service = LLMServiceFactory.create_service("default_llm")
analyzer = ComplexFallacyAnalyzer(llm_service=llm_service)

complex_argument = "Le candidat X a tort sur l'économie parce qu'il a mal orthographié un mot dans son discours, et de toute façon, son programme fiscal est soutenu par des gens peu recommandables. Donc, son plan économique est mauvais."
analysis_result = analyzer.analyze_complex_argument(argument_text=complex_argument)
print("Analyse de l'argument complexe:")
# La structure de analysis_result dépendra de l'implémentation de l'agent
# Typiquement, elle pourrait inclure une liste de sophismes, leur explication, etc.
if 'identified_fallacies' in analysis_result:
    for fallacy_info in analysis_result['identified_fallacies']:
        print(f"- Sophisme: {fallacy_info.get('type', 'N/A')}, Explication: {fallacy_info.get('explanation', 'N/A')}")
else:
    print(analysis_result)

```

### 4. `RhetoricalResultAnalyzer`

**Source :** [`../../argumentation_analysis/agents/tools/analysis/rhetorical_result_analyzer.py`](../../argumentation_analysis/agents/tools/analysis/rhetorical_result_analyzer.py)

Analyse les résultats d'une analyse rhétorique pour en extraire des insights, des patterns ou des scores.

**Méthodes Principales :**
*   `analyze_rhetorical_data(self, rhetorical_data: Dict[str, Any]) -> Dict[str, Any]`: Analyse les données rhétoriques structurées.

**Exemple d'Utilisation :**
```python
from argumentation_analysis.agents.tools.analysis.rhetorical_result_analyzer import RhetoricalResultAnalyzer
from project_core.services.llm_service_factory import LLMServiceFactory

llm_service = LLMServiceFactory.create_service("default_llm")
analyzer = RhetoricalResultAnalyzer(llm_service=llm_service)

# rhetorical_data est typiquement le résultat d'un autre agent ou processus
# qui a identifié des figures de style, des appels émotionnels, etc.
rhetorical_data_example = {
    "text": "Amis, Romains, compatriotes, prêtez-moi l'oreille!",
    "figures_of_speech": [
        {"type": "Apostrophe", "details": "S'adresse directement à l'auditoire."},
        {"type": "Asyndète", "details": "Absence de conjonctions entre 'Amis, Romains, compatriotes'."}
    ],
    "emotional_appeals": ["Pathos"],
    "identified_fallacies": [] # Supposons qu'une analyse de sophisme a déjà eu lieu
}
insights = analyzer.analyze_rhetorical_data(rhetorical_data=rhetorical_data_example)
print("Insights de l'analyse rhétorique:")
# La structure de 'insights' dépendra de l'implémentation
print(insights.get("summary", "Aucun résumé disponible."))
if insights.get("key_findings"):
    for finding in insights["key_findings"]:
        print(f"- {finding}")
```

### 5. `RhetoricalResultVisualizer`

**Source :** [`../../argumentation_analysis/agents/tools/analysis/rhetorical_result_visualizer.py`](../../argumentation_analysis/agents/tools/analysis/rhetorical_result_visualizer.py)

Génère des visualisations (graphiques, tableaux) à partir des résultats d'une analyse rhétorique.

**Méthodes Principales :**
*   `generate_visualization(self, analysis_results: Dict[str, Any], visualization_type: str = "summary_table") -> Any`: Génère une visualisation spécifique.
*   `generate_all_visualizations(self, analysis_results: Dict[str, Any], output_dir: str = "reports/visualizations") -> Dict[str, str]`: Génère toutes les visualisations configurées et les sauvegarde.

**Exemple d'Utilisation :**
```python
from argumentation_analysis.agents.tools.analysis.rhetorical_result_visualizer import RhetoricalResultVisualizer

# Supposons que 'insights' provient de l'exemple RhetoricalResultAnalyzer
insights_example = {
    "summary": "L'orateur utilise fortement l'apostrophe et l'asyndète pour capter l'attention.",
    "key_findings": [
        "Utilisation efficace de l'apostrophe.",
        "L'asyndète crée un rythme rapide."
    ],
    "rhetorical_device_counts": {"Apostrophe": 1, "Asyndète": 1},
    "sentiment_score": 0.7 # Exemple de donnée additionnelle
}

visualizer = RhetoricalResultVisualizer() # Ne nécessite pas de LLM pour la génération de base

# Générer une visualisation spécifique (par exemple, un tableau)
# La nature de la sortie dépend de l'implémentation (ex: objet matplotlib, HTML, etc.)
# Pour cet exemple, supposons qu'elle retourne une description ou un chemin de fichier
summary_table_viz = visualizer.generate_visualization(analysis_results=insights_example, visualization_type="summary_table")
print(f"Visualisation (table résumé): {summary_table_viz}")

# Générer toutes les visualisations et les sauvegarder
# Assurez-vous que le répertoire de sortie existe ou peut être créé.
import os
output_directory = "output/rhetorical_visualizations"
os.makedirs(output_directory, exist_ok=True)

saved_visualizations = visualizer.generate_all_visualizations(analysis_results=insights_example, output_dir=output_directory)
print("Visualisations sauvegardées:")
for viz_name, viz_path in saved_visualizations.items():
    print(f"- {viz_name}: {viz_path}")

```

## Tests Associés

Les tests pour ces outils, en particulier leurs versions "enhanced", peuvent être trouvés sous :
- [`tests/agents/tools/analysis/enhanced/test_enhanced_contextual_fallacy_analyzer.py`](../../tests/agents/tools/analysis/enhanced/test_enhanced_contextual_fallacy_analyzer.py)
- [`tests/agents/tools/analysis/enhanced/test_enhanced_fallacy_severity_evaluator.py`](../../tests/agents/tools/analysis/enhanced/test_enhanced_fallacy_severity_evaluator.py)
- [`tests/agents/tools/analysis/enhanced/test_enhanced_complex_fallacy_analyzer.py`](../../tests/agents/tools/analysis/enhanced/test_enhanced_complex_fallacy_analyzer.py)

Il est recommandé de vérifier la couverture des tests pour les versions de base de `RhetoricalResultAnalyzer` et `RhetoricalResultVisualizer` et de les compléter si nécessaire.