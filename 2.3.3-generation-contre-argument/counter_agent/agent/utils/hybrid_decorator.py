# Fichier: argumentation_analysis/agents/utils/hybrid_decorator.py

import asyncio
from functools import wraps
from semantic_kernel import Kernel
import json


def hybrid_function(prompt_template: str, result_parser: callable = None):
    """
    Décorateur pour créer une fonction hybride.
    - Le LLM utilise le 'prompt_template' pour raisonner.
    - La fonction native décorée exécute une tâche avec le résultat du LLM.
    """

    def decorator(native_func):
        @wraps(native_func)
        async def wrapper(self, kernel: Kernel, **kwargs):
            # 1. Invoquer le LLM pour le raisonnement
            reasoning_result = await kernel.invoke_prompt(
                prompt_template, arguments=kwargs
            )

            # 2. Utiliser un analyseur pour extraire les arguments pour la fonction native
            parsed_args = (
                result_parser(reasoning_result)
                if result_parser
                else json.loads(reasoning_result.value)
            )

            # 3. Appeler la fonction native avec les arguments traités
            # Assurer que la fonction native est attendue si c'est une coroutine
            if asyncio.iscoroutinefunction(native_func):
                return await native_func(self, **parsed_args)
            else:
                return native_func(self, **parsed_args)

        # Attacher les métadonnées pour que semantic-kernel puisse les utiliser
        wrapper.is_kernel_function = True
        wrapper.prompt = prompt_template
        # Pour la compatibilité, ajoutons des métadonnées que le kernel pourrait rechercher
        wrapper.ai_function = True
        wrapper.name = native_func.__name__
        wrapper.description = "Fonction hybride combinant LLM et code natif."

        return wrapper

    return decorator
