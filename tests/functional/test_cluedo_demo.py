import pytest
import asyncio
from unittest.mock import patch, AsyncMock
from typing import List, Dict

from argumentation_analysis.orchestration.cluedo_orchestrator import run_cluedo_game
from semantic_kernel.kernel import Kernel
from semantic_kernel.contents.chat_message_content import ChatMessageContent

@pytest.mark.asyncio
async def test_cluedo_functional_demo_flow():
    """
    Teste le flux fonctionnel du Cluedo en simulant la conversation
    et en validant l'ajout de la conclusion.
    """
    # 1. Définir la conversation attendue, y compris la conclusion
    expected_conversation = [
        {'sender': 'Sherlock', 'message': "Je soupçonne le Colonel Moutarde avec le chandelier dans le salon."},
        {'sender': 'Watson', 'message': "L'hypothèse de Sherlock est plausible, mais nous devrions vérifier les alibis."},
        {'sender': 'Sherlock', 'message': "J'ai trouvé une empreinte près de la bibliothèque, cela pourrait appartenir à Mademoiselle Rose."},
        {'sender': 'Watson', 'message': "En effet, cela contredit l'hypothèse initiale sur le Colonel Moutarde."},
        {'sender': 'Sherlock', 'message': "Conclusion : Mademoiselle Rose est la principale suspecte en raison de l'empreinte trouvée."}
    ]

    # L'historique que la boucle `invoke` du chat de groupe est censée produire
    # La boucle s'arrête après la réponse de Watson, donc l'historique simulé contient 4 messages.
    simulated_chat_history = [ChatMessageContent(role="assistant", content=msg['message'], name=msg['sender']) for msg in expected_conversation[:4]]

    # Le mock pour l'appel final à Sherlock
    async def mock_sherlock_invoke(prompt: str, **kwargs) -> List[ChatMessageContent]:
        if "résumer vos conclusions" in prompt:
            response_content = expected_conversation[4]['message']
            return [ChatMessageContent(role="assistant", content=response_content, name="Sherlock")]
        return []

    # On patch l'itérateur du group_chat pour qu'il ne fasse rien mais remplisse l'historique
    async def mock_group_chat_invoke(self):
        for msg in simulated_chat_history:
            yield msg

    with patch("semantic_kernel.agents.group_chat.agent_group_chat.AgentGroupChat.invoke", new=mock_group_chat_invoke), \
         patch("argumentation_analysis.orchestration.cluedo_orchestrator.SherlockEnqueteAgent.invoke", new_callable=AsyncMock) as mock_sherlock_invoke_method:
        
        # Configurer le mock pour l'appel de conclusion
        mock_sherlock_invoke_method.side_effect = mock_sherlock_invoke

        kernel_instance = Kernel()
        initial_question = "Un meurtre a été commis. Sherlock, commencez l'enquête."
        
        # L'historique initial est vide, il sera rempli par le mock de invoke
        # max_messages est une sécurité, la terminaison est attendue via les mots-clés.
        final_history = await run_cluedo_game(kernel_instance, initial_question, history=[], max_messages=10)

        # Assertions
        assert len(final_history) == len(expected_conversation), \
            f"Attendu {len(expected_conversation)} messages, mais obtenu {len(final_history)}. Historique: {final_history}"

        # L'historique final est déjà formaté par run_cluedo_game
        for i, expected_entry in enumerate(expected_conversation):
            actual_entry = final_history[i]
            assert actual_entry['sender'] == expected_entry['sender'], f"Message {i+1} sender mismatch"
            assert actual_entry['message'] == expected_entry['message'], f"Message {i+1} content mismatch"

        print("\n--- Historique Final de la Conversation (Test Fonctionnel) ---")
        for entry in final_history:
            print(f"  {entry['sender']}: {entry['message']}")
        print("--- Fin de l'Historique ---")