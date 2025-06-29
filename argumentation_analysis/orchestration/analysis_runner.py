# Fichier: argumentation_analysis/orchestration/analysis_runner.py

import asyncio
import logging
import os

from semantic_kernel.agents import AgentGroupChat
from semantic_kernel.contents import ChatMessageContent, AuthorRole

from ..kernel.kernel_builder import KernelBuilder
from ..agents.agent_factory import AgentFactory

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    """
    Point d'entrée principal pour l'orchestration de l'analyse d'argumentation.
    """
    logger.info("Démarrage du processus d'analyse d'argumentation.")
    
    # 1. Configuration et construction du Kernel
    config_path = os.path.join("config", "config.yaml")
    env_path = os.path.join("config", ".env")
    
    try:
        settings = KernelBuilder.load_settings(config_path, env_path)
        kernel = KernelBuilder.create_kernel(settings)
        llm_service_id = settings.default_llm_service_id
        logger.info("Kernel et services IA configurés avec succès.")
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

    # 3. Création et configuration du Chat de Groupe d'Agents
    chat = AgentGroupChat(
        agents=[manager_agent, fallacy_agent],
        admin_agent=manager_agent  # Le chef de projet initie et termine la conversation
    )
    logger.info("AgentGroupChat créé avec le Project_Manager comme administrateur.")

    # 4. Exécution du scénario d'analyse
    input_text = (
        "Le sénateur prétend que sa loi va créer des emplois, "
        "mais il a été vu en train de manger une glace au chocolat. "
        "On ne peut pas faire confiance à un homme politique qui aime le chocolat. "
        "Son projet est donc mauvais."
    )
    
    logger.info(f"Début de l'invocation du chat avec le texte d'entrée.")
    
    # Ajout du message initial au chat, provenant de "l'utilisateur"
    initial_message = ChatMessageContent(role=AuthorRole.USER, content=input_text)
    
    # Invocation du chat et récupération de l'historique complet
    full_history = await chat.invoke([initial_message])
    
    logger.info("Invocation du chat terminée. Affichage de l'historique complet de la conversation.")
    
    # 5. Affichage des résultats
    for message in full_history:
        print(f"[{message.role.value.upper()}] - {message.name or 'User'}:\n---\n{message.content}\n---")

if __name__ == "__main__":
    asyncio.run(main())
