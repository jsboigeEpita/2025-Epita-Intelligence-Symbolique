# src/argumentation_analysis/agents/core/informal/__init__.py
"""
Package `informal` pour l'analyse informelle des arguments.

Ce package contient les composants relatifs à l'analyse des arguments
en langage naturel, en se concentrant sur les aspects informels tels que
l'identification des types de sophismes, l'évaluation de la force persuasive,
et d'autres analyses rhétoriques qui ne reposent pas sur une logique formelle stricte.

Modules et classes clés :
    - `InformalAgent`: L'agent principal pour l'analyse informelle.
    - `informal_definitions`: Structures de données et taxonomies pour l'analyse informelle.
    - `prompts`: Templates de prompts pour guider le LLM dans les tâches d'analyse informelle.
"""

try:
    from .informal_agent import InformalAnalysisAgent
    from .informal_definitions import (
        InformalAnalysisPlugin,
        INFORMAL_AGENT_INSTRUCTIONS
    )
    from .prompts import (
        prompt_identify_args_v8,
        prompt_analyze_fallacies_v1,
        prompt_justify_fallacy_attribution_v1
    )

    __all__ = [
        "InformalAnalysisAgent",
        "InformalAnalysisPlugin",
        "INFORMAL_AGENT_INSTRUCTIONS",
        "prompt_identify_args_v8",
        "prompt_analyze_fallacies_v1",
        "prompt_justify_fallacy_attribution_v1",
    ]
except ImportError as e:
    import logging
    logging.warning(f"Certains composants de 'agents.core.informal' n'ont pas pu être importés/exposés: {e}")
    __all__ = []