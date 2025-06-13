# argumentation_analysis/orchestration/cluedo_components/logging_handler.py
import logging
from typing import Callable, Awaitable

# semantic_kernel imports
from semantic_kernel.filters.functions.function_invocation_context import FunctionInvocationContext

logger = logging.getLogger(__name__)

class ToolCallLoggingHandler:
    """
    Filtre pour journaliser les appels de fonctions (outils) du kernel,
    utilisant le nouveau système de filtres de Semantic Kernel.
    """
    async def __call__(self, context: FunctionInvocationContext, next: Callable[..., Awaitable[None]]) -> None:
        """Handler de filtre exécuté avant et après l'invocation de la fonction."""
        # Logique "avant" (invoking)
        metadata = context.function.metadata
        function_name = f"{metadata.plugin_name}.{metadata.name}"
        logger.debug(f"▶️  FILTER: INVOKING KERNEL FUNCTION: {function_name}")
        
        args_str = ", ".join(f"{k}='{str(v)[:100]}...'" for k, v in context.arguments.items())
        logger.debug(f"  ▶️  FILTER: ARGS: {args_str}")

        # Exécute la fonction suivante dans la chaîne (ou la fonction elle-même)
        await next(context)

        # Logique "après" (invoked)
        result_content = "N/A"
        
        if context.result and context.result.metadata.get('exception'):
            exception = context.result.metadata['exception']
            logger.error(f"  ◀️  FILTER: EXCEPTION in {function_name}: {exception}")
            result_content = f"EXCEPTION: {exception}"
        elif context.result:
            result_value = context.result.value
            if isinstance(result_value, list):
                result_content = f"List[{len(result_value)}] - " + ", ".join(map(str, result_value[:3]))
            else:
                result_content = str(result_value)
        
        logger.debug(f"  ◀️  FILTER: RESULT for {function_name}: {result_content[:500]}...") # Tronqué
        logger.debug(f"◀️  FILTER: FINISHED KERNEL FUNCTION: {function_name}")