# Simple Operational Agent Example

from argumentation_analysis.orchestration.hierarchical.operational.adapters.extract_agent_adapter import ExtractAgentAdapter
from argumentation_analysis.orchestration.hierarchical.interfaces import IOperationalAgent

class SimpleExtractAgent(IOperationalAgent):
    """
    Exemple d'agent opérationnel simple pour l'extraction de segments
    """
    def __init__(self):
        self.adapter = ExtractAgentAdapter()
    
    async def process_task(self, task):
        """
        Traite une tâche d'extraction de segments
        """
        logger.info(f"Traitement de la tâche: {task}")
        result = await self.adapter.extract_segments(task['text'], task['definitions'])
        return {
            'status': 'completed',
            'result': result,
            'metadata': {
                'agent_type': 'simple_extract',
                'processing_time': 0.123
            }
        }

# Exemple d'utilisation
if __name__ == "__main__":
    agent = SimpleExtractAgent()
    sample_task = {
        'text': "Les vaccins sont essentiels pour la santé publique...",
        'definitions': ['definition1', 'definition2']
    }
    result = asyncio.run(agent.process_task(sample_task))
    logger.info(f"Résultat de l'agent: {result}")