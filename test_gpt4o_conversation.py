#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test pour afficher la vraie conversation avec GPT-4o-mini."""

import asyncio
import os
import logging
from dotenv import load_dotenv
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Configuration du logging détaillé
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)

# Activer le logging détaillé pour Semantic Kernel et OpenAI
logging.getLogger("semantic_kernel").setLevel(logging.DEBUG)
logging.getLogger("openai").setLevel(logging.DEBUG)
logging.getLogger("httpx").setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

async def test_gpt4o_conversation():
    """Test direct avec GPT-4o-mini pour voir la conversation."""
    
    # Charger les variables d'environnement
    load_dotenv()
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("❌ OPENAI_API_KEY non trouvée")
        return False
    
    logger.info("🔑 Clé API OpenAI chargée")
    
    try:
        # Créer le kernel
        kernel = sk.Kernel()
        
        # Ajouter le service OpenAI
        chat_service = OpenAIChatCompletion(
            service_id="openai_chat",
            ai_model_id="gpt-4o-mini",
            api_key=api_key
        )
        kernel.add_service(chat_service)
        
        logger.info("🤖 Service GPT-4o-mini configuré")
        
        # Créer une fonction de test simple qui montre la conversation
        prompt_conversation_test = """
[INSTRUCTION POUR GPT-4o-mini]
Tu es un expert en analyse d'argumentation. Analyze ce texte politique et explique-moi EN DÉTAIL ton processus de réflexion.

Je veux voir:
1. Ta compréhension initiale du texte
2. Les arguments que tu identifies 
3. Ton analyse des techniques rhétoriques
4. Les sophismes potentiels que tu détectes
5. Ta conclusion finale

Sois TRÈS bavard et détaillé dans tes explications. Montre-moi comment tu raisonnes étape par étape.

TEXTE À ANALYSER:
{{$input}}

RÉPONDS EN FRANÇAIS avec beaucoup de détails sur ton processus d'analyse:
"""

        # Pas besoin de créer une fonction, on va directement faire invoke_prompt
        
        # Texte de test politique court
        texte_test = """
Les citoyens français méritent mieux que ces politiques actuelles. 
Tous les experts s'accordent à dire que notre approche est la seule viable.
Si nous ne changeons pas maintenant, c'est la catastrophe assurée pour nos enfants.
L'opposition ne propose que des solutions irréalistes qui ont déjà échoué partout ailleurs.
"""
        
        logger.info("🔍 Lancement de l'analyse avec GPT-4o-mini...")
        logger.info(f"📝 Texte analysé: {texte_test[:100]}...")
        
        # Exécuter l'analyse directement avec invoke_prompt
        arguments = KernelArguments(input=texte_test)
        result = await kernel.invoke_prompt(
            prompt=prompt_conversation_test,
            arguments=arguments
        )
        
        # Afficher le résultat complet
        response_text = str(result)
        
        logger.info("=" * 80)
        logger.info("🎯 CONVERSATION COMPLÈTE AVEC GPT-4o-mini:")
        logger.info("=" * 80)
        print(f"\n{response_text}\n")
        logger.info("=" * 80)
        logger.info("✅ Conversation GPT-4o-mini terminée avec succès!")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(test_gpt4o_conversation())
    if success:
        print("\n🎉 Test de conversation GPT-4o-mini réussi!")
    else:
        print("\n💥 Échec du test de conversation")