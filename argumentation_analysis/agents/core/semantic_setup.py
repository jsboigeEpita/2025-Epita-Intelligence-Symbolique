# argumentation_analysis/agents/core/semantic_setup.py
"""
Enregistrement des fonctions sémantiques d'un agent, sans échec silencieux (#2632).

Un agent (ou une fonction ``setup_*_kernel``) enregistre des fonctions de
prompt dont il ne peut pas se passer, avec les settings du service LLM que son
appelant a nommé. Les deux viennent du code appelant : un échec est un défaut
de ce code, il lève en nommant ce qui était configuré, ce qui a échoué et
pourquoi. Plusieurs setups journalisaient l'échec puis continuaient : l'agent
existait sans ses fonctions, ou les exécutait avec les settings par défaut du
kernel au lieu de ceux de son service.
"""

from typing import Any, Optional

from semantic_kernel import Kernel


class SemanticSetupError(RuntimeError):
    """Une fonction sémantique ou ses settings n'ont pas pu être configurés."""


def prompt_settings(kernel: Kernel, service_id: str, owner: str) -> Any:
    """Les settings de prompt du service ``service_id`` enregistré dans ``kernel``.

    ``owner`` nomme ce qui est configuré (agent ou plugin), pour le message.
    """
    try:
        return kernel.get_prompt_execution_settings_from_service_id(service_id)
    except Exception as e:
        raise SemanticSetupError(
            f"{owner} : settings du service LLM '{service_id}' introuvables "
            f"({type(e).__name__}: {e})"
        ) from e


def register_prompt_function(
    kernel: Kernel,
    owner: str,
    plugin_name: str,
    function_name: str,
    prompt: str,
    description: str,
    settings: Optional[Any] = None,
) -> None:
    """Enregistre ``plugin_name.function_name`` dans ``kernel``, ou lève.

    Un prompt vide est refusé par Semantic Kernel lui-même : c'est un défaut
    de la constante, il lève comme le reste.
    """
    try:
        kernel.add_function(
            prompt=prompt,
            plugin_name=plugin_name,
            function_name=function_name,
            description=description,
            prompt_execution_settings=settings,
        )
    except Exception as e:
        raise SemanticSetupError(
            f"{owner} : fonction sémantique {plugin_name}.{function_name} non "
            f"enregistrée ({type(e).__name__}: {e})"
        ) from e
