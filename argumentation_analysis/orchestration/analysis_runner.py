# Fichier: argumentation_analysis/orchestration/analysis_runner.py

import asyncio
import logging
from semantic_kernel.agents import AgentGroupChat
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.agents.chat_completion.chat_completion_agent import ChatHistoryAgentThread
from semantic_kernel.agents.channels.chat_history_channel import ChatHistoryChannel

from argumentation_analysis.config.settings import AppSettings
from argumentation_analysis.kernel.kernel_builder import KernelBuilder
from argumentation_analysis.agents.agent_factory import AgentFactory

# Correction pour Pydantic : Reconstruire le modèle après avoir défini la dépendance de thread.
ChatHistoryChannel.model_rebuild()

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """
    Point d'entrée principal pour l'orchestration de l'analyse d'argumentation.
    """
    logger.info("Démarrage du processus d'analyse d'argumentation.")
    
    # 1. Configuration et construction du Kernel
    try:
        settings = AppSettings()
        kernel = KernelBuilder.create_kernel(settings)
        llm_service_id = settings.service_manager.default_llm_service_id
        logger.info(f"Kernel et services IA configurés avec succès en utilisant '{llm_service_id}'.")
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Erreur de configuration critique: {e}")
        return

    # 2. Création des agents via la Factory
    factory = AgentFactory(kernel, llm_service_id)
    
    try:
        fallacy_agent = factory.create_informal_fallacy_agent()
        manager_agent = factory.create_project_manager_agent()
        logger.info(f"Agents créés : {fallacy_agent.name}, {manager_agent.name}")
    except Exception as e:
        logger.error(f"Erreur lors de la création des agents : {e}")
        return

    # 3. Préparation du chat
    input_text = (
        "Le sénateur prétend que sa loi va créer des emplois, "
        "mais il a été vu en train de manger une glace au chocolat. "
        "On ne peut pas faire confiance à un homme politique qui aime le chocolat. "
        "Son projet est donc mauvais."
    )
    
    # Création de l'historique de chat avec le message initial de l'utilisateur
    chat_history = ChatHistory()
    chat_history.add_message(message=ChatMessageContent(role=AuthorRole.USER, content=input_text))

    # 4. Création et configuration du Chat de Groupe d'Agents
    chat = AgentGroupChat(
        agents=[manager_agent, fallacy_agent],
        chat_history=chat_history
    )
    logger.info("AgentGroupChat créé et pré-configuré avec l'historique initial.")

    # 5. Exécution du scénario d'analyse
    logger.info(f"Début de l'invocation du chat.")
    
    # Invocation du chat et récupération de l'historique complet.
    # On ajoute le message initial à l'historique affiché.
    history = [chat_history.messages[0]]
    async for message in chat.invoke():
        history.append(message)
    
    logger.info("Invocation du chat terminée. Affichage de l'historique complet de la conversation.")
    
    # 6. Affichage des résultats
    for message in history:
        print(f"[{message.role.value.upper()}] - {message.name or 'User'}:\n---\n{message.content}\n---")

if __name__ == "__main__":
    asyncio.run(main())
