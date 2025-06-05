import pytest
import asyncio
from unittest.mock import patch, AsyncMock

# Importer les vraies classes nécessaires
# Assurez-vous que ces chemins d'importation sont corrects par rapport à la structure actuelle de votre projet.
from argumentation_analysis.orchestration.cluedo_orchestrator import (
    Kernel, EnqueteCluedoState, SherlockEnqueteAgent, WatsonLogicAssistant, GroupChatOrchestration,
    CluedoGroupChatManager # Ajout de l'import
)
from argumentation_analysis.orchestration.plugins.enquete_state_manager_plugin import EnqueteStateManagerPlugin
from semantic_kernel.agents.runtime import InProcessRuntime # Ajout de l'import
# Si d'autres éléments comme des stratégies spécifiques ou des types de messages sont nécessaires,
# importez-les également. Par exemple :
# from argumentation_analysis.core.strategies import BalancedParticipationStrategy
# from argumentation_analysis.core.datatypes import Message # Ou le type de message utilisé

# Chemin vers le module Kernel, si nécessaire pour certains types de patchs.
# Cependant, il est souvent préférable de patcher la méthode spécifique où l'appel LLM se produit.
KERNEL_MODULE_PATH = "argumentation_analysis.orchestration.cluedo_orchestrator.Kernel"
AGENT_BASE_MODULE_PATH = "argumentation_analysis.agents.core.abc.agent_bases.BaseAgent" # Exemple si l'appel est dans une classe de base

@pytest.mark.asyncio
async def test_cluedo_functional_demo_flow():
    """
    Teste un flux fonctionnel simple du Cluedo pour une démo.
    Utilise les vrais agents mais mocke les appels LLM pour des réponses contrôlées.
    """
    # 1. Définir le scénario de réponses LLM mockées
    mock_llm_responses = {
        "sherlock, quelle est votre première hypothèse": "Je soupçonne le Colonel Moutarde avec le chandelier dans le salon.",
        "watson, que pensez-vous de l'hypothèse de sherlock": "L'hypothèse de Sherlock me semble plausible, mais nous devrions vérifier ses alibis.",
        "sherlock, avez-vous d'autres pistes ou des preuves": "J'ai trouvé une empreinte près de la bibliothèque, cela pourrait appartenir à Mademoiselle Rose.",
        "watson, cette nouvelle information change-t-elle votre perspective": "En effet, si Mademoiselle Rose était près de la bibliothèque, cela contredit l'hypothèse initiale sur le Colonel Moutarde dans le salon."
    }

    async def mock_invoke_llm_side_effect(prompt_text: str, **kwargs):
        # Normalise le prompt_text pour une comparaison insensible à la casse et aux espaces superflus
        normalized_prompt = ' '.join(str(prompt_text).lower().split())
        print(f"Mock LLM received prompt: {normalized_prompt}") # Pour le débogage
        for key, resp in mock_llm_responses.items():
            normalized_key = ' '.join(key.lower().split())
            if normalized_key in normalized_prompt:
                print(f"Mock LLM matched key: {normalized_key} -> returning: {resp}") # Pour le débogage
                # La réponse doit être formatée comme ce que l'agent attend du LLM.
                # Si l'agent attend un objet Message ou une structure spécifique, adaptez ceci.
                # Pour l'instant, supposons qu'une chaîne de caractères simple suffit ou que l'agent la traite.
                return resp 
        print(f"Mock LLM: No match found for prompt, returning default.") # Pour le débogage
        return "Réponse par défaut du mock LLM car aucune clé n'a correspondu."

    # 2. Configuration de l'état de l'enquête (réel)
    # Utilisez les vrais objets et configurations autant que possible, sauf pour les appels LLM.
    enquete_state = EnqueteCluedoState(
        nom_enquete_cluedo="Démonstration Fonctionnelle Cluedo",
        elements_jeu_cluedo={
            "suspects": ["Colonel Moutarde", "Professeur Violet", "Mademoiselle Rose", "Docteur Olive", "Madame Pervenche", "Monsieur Prunelle"],
            "armes": ["Poignard", "Chandelier", "Revolver", "Corde", "Matraque", "Clé Anglaise"],
            "lieux": ["Salon", "Cuisine", "Bureau", "Bibliothèque", "Salle de Billard", "Jardin d'Hiver"]
        },
        description_cas="Un meurtre a été commis au Manoir Tudor lors d'une soirée orageuse. Le célèbre détective Sherlock Holmes et son fidèle assistant Watson sont appelés pour résoudre l'affaire.",
        initial_context="Un meurtre a été commis au Manoir Tudor lors d'une soirée orageuse. Le célèbre détective Sherlock Holmes et son fidèle assistant Watson sont appelés pour résoudre l'affaire.",
        # La solution peut être définie pour certains scénarios de test, ou laissée non définie
        # si le test ne vérifie pas la découverte de la solution exacte.
        auto_generate_solution=True # Permettre la génération auto pour satisfaire le constructeur.
    )
    # Optionnel: définir une solution si le flux de test en dépend.
    # enquete_state.solution_enquete = {"suspect": "Mademoiselle Rose", "arme": "Poignard", "lieu": "Bibliothèque"}


    # 3. Patch des appels LLM et initialisation du Kernel et des Agents
    # Le chemin exact à patcher est crucial. Il faut identifier où l'appel au LLM (ex: OpenAI, Azure)
    # est effectivement réalisé. Cela pourrait être dans une méthode du Kernel, une méthode d'une classe
    # de base pour les agents, ou directement dans les agents.
    #
    # Hypothèses communes pour le patch :
    # a) Si les agents utilisent une instance de Kernel pour appeler le LLM via une méthode comme `kernel.invoke_prompt(prompt)`:
    #    PATH_TO_PATCH = f"{KERNEL_MODULE_PATH}.invoke_prompt" # ou .invoke, .complete, etc.
    # b) Si les agents héritent d'une BaseAgent qui a une méthode `_invoke_llm(prompt)`:
    #    PATH_TO_PATCH = f"{AGENT_BASE_MODULE_PATH}._invoke_llm"
    # c) Si les agents utilisent directement un client LLM (ex: client OpenAI):
    #    PATH_TO_PATCH = "openai.ChatCompletion.create" # ou la méthode spécifique du client
    #
    # Pour cette tâche, nous allons essayer de patcher une méthode générique au niveau du Kernel ou de la base Agent.
    # **Action Requise pour le développeur : Vérifier et ajuster ce chemin de patch.**
    # Le rapport précédent mentionnait `Kernel.invoke_prompt`. Si cette méthode existe et fait l'appel LLM,
    # ce serait un bon candidat. Sinon, il faut trouver la méthode de plus bas niveau qui fait l'appel externe.
    #
    # Le chemin de patch cible la méthode `invoke_prompt_async` du Kernel.
    # C'est une méthode standard de Semantic Kernel pour exécuter un prompt et obtenir une réponse du LLM.
    # Le mock `mock_invoke_llm_side_effect` est conçu pour intercepter l'appel à cette méthode.
    PATH_TO_LLM_CALL_TO_PATCH = f"{KERNEL_MODULE_PATH}.invoke"
    # Note: KERNEL_MODULE_PATH pointe vers 'argumentation_analysis.orchestration.cluedo_orchestrator.Kernel',
    # qui est l'importation de 'semantic_kernel.kernel.Kernel' utilisée dans ce test.
    # Ce chemin est choisi car il correspond à la manière dont les agents sont susceptibles d'invoquer les LLMs
    # via le kernel pour des prompts directs, et la signature du mock correspond.

    with patch(PATH_TO_LLM_CALL_TO_PATCH, side_effect=mock_invoke_llm_side_effect, new_callable=AsyncMock) as mock_llm_actual_call:
        kernel_instance = Kernel() # Vraie instance du Kernel

        # Enregistrement du plugin de gestion d'état
        enquete_state_plugin_name = "EnqueteCluedoPlugin"
        enquete_manager_plugin = EnqueteStateManagerPlugin(enquete_state)
        kernel_instance.add_plugin(enquete_manager_plugin, enquete_state_plugin_name)

        # Initialisation des vrais agents
        sherlock = SherlockEnqueteAgent(
            kernel=kernel_instance,
            agent_name="Sherlock Holmes"
            # system_prompt="Vous êtes Sherlock Holmes. Menez l'enquête pour résoudre le mystère du Cluedo." # Optionnel
            # Autres paramètres de configuration si nécessaire
        )
        watson = WatsonLogicAssistant(
            kernel=kernel_instance,
            agent_name="Dr. Watson"
            # system_prompt="Vous êtes Dr. Watson. Assistez Sherlock Holmes en analysant la logique et les informations." # Optionnel
            # Autres paramètres de configuration
        )
        
        # Configuration du CluedoGroupChatManager
        cluedo_chat_manager = CluedoGroupChatManager(
            members=[sherlock, watson],
            # Vous pouvez ajuster max_turns_per_agent, max_total_messages, termination_keywords ici si nécessaire
            # Pour le test, les valeurs par défaut du manager peuvent suffire ou être surchargées.
            # Par exemple:
            # max_turns_per_agent=2,
            # max_total_messages=6 # Pour s'assurer que les 4 réponses mockées sont utilisées
        )

        # Configuration de GroupChatOrchestration avec les vrais agents
        # Adapter les paramètres selon l'API actuelle de GroupChatOrchestration
        group_chat = GroupChatOrchestration(
            members=[sherlock, watson], # Doit correspondre aux membres du manager
            manager=cluedo_chat_manager,
            runtime=InProcessRuntime() # Nécessaire pour exécuter le chat
        )

        # 4. Exécution du flux de conversation
        # Le message initial peut venir d'un "GameMaster" ou d'un utilisateur système.
        initial_user_message = [
            {"role": "user", "name": "GameMaster", "content": "L'enquête sur le meurtre au Manoir Tudor commence. Sherlock, quelle est votre première hypothèse ?"}
        ]
        
        # La méthode pour démarrer la conversation peut être .invoke(), .run(), .chat(), etc.
        # Adaptez ceci à l'API de GroupChatOrchestration.
        final_conversation_history = await group_chat.invoke(input=initial_user_message)

        # 5. Assertions
        assert final_conversation_history is not None, "L'historique de la conversation ne devrait pas être None."
        assert len(final_conversation_history) > 1, "L'historique devrait contenir plus que le message initial."

        # Vérifier que les agents ont participé
        sherlock_participated = any(msg.get("name") == sherlock.name for msg in final_conversation_history if isinstance(msg, dict))
        watson_participated = any(msg.get("name") == watson.name for msg in final_conversation_history if isinstance(msg, dict))
        
        assert sherlock_participated, f"{sherlock.name} n'a pas participé à la conversation."
        assert watson_participated, f"{watson.name} n'a pas participé à la conversation."

        # Vérifier que les appels LLM mockés ont été faits
        # Le nombre exact d'appels dépend de la logique de GroupChatOrchestration et du nombre de tours.
        assert mock_llm_actual_call.call_count > 0, "La fonction d'appel LLM mockée aurait dû être appelée."
        # Exemple d'assertion plus précise si on s'attend à un certain nombre d'appels :
        # assert mock_llm_actual_call.call_count >= 2, "Au moins un appel LLM par agent actif attendu."

        # Vérifier que les réponses mockées sont présentes dans l'historique
        # (Ceci dépend du format exact des messages dans l'historique)
        history_texts = [msg.get("content", "").lower() for msg in final_conversation_history if isinstance(msg, dict)]
        
        assert any(mock_llm_responses["sherlock, quelle est votre première hypothèse"].lower() in text for text in history_texts), \
            "La première réponse mockée de Sherlock n'a pas été trouvée dans l'historique."
        assert any(mock_llm_responses["watson, que pensez-vous de l'hypothèse de sherlock"].lower() in text for text in history_texts), \
            "La réponse mockée de Watson n'a pas été trouvée dans l'historique."

        # Afficher l'historique final pour inspection manuelle si nécessaire (utile pendant le développement)
        print("\n--- Historique Final de la Conversation (Test Fonctionnel) ---")
        for message in final_conversation_history:
            if isinstance(message, dict):
                sender_name = message.get("name", message.get("role", "Unknown"))
                content = message.get("content", "")
                print(f"  {sender_name}: {content}")
            else:
                print(f"  {message}") # Au cas où le format serait différent
        print("--- Fin de l'Historique ---")

# Pour exécuter ce test:
# Assurez-vous que pytest et pytest-asyncio sont installés.
# Exécutez `pytest tests/functional/test_cluedo_demo.py` depuis la racine du projet.
# Vous devrez peut-être ajuster les chemins d'importation et le PATH_TO_LLM_CALL_TO_PATCH.