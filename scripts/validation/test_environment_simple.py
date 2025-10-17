#!/usr/bin/env python3
# scripts/test_environment_simple.py

"""
Test simple de l'environnement avant la validation complète.
"""

import argumentation_analysis.core.environment  # Activation automatique de l'environnement

import os
import asyncio
from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion


async def test_environment():
    """Test rapide de l'environnement."""

    print("🧪 TEST ENVIRONNEMENT")
    print("=" * 50)

    # Chargement .env
    load_dotenv()

    # Vérification clé API
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY non trouvée")
        return False

    print(f"✅ OPENAI_API_KEY trouvée (longueur: {len(api_key)})")

    # Test kernel
    try:
        kernel = Kernel()
        chat_service = OpenAIChatCompletion(
            service_id="test",
            api_key=api_key,
            ai_model_id=os.getenv("OPENAI_CHAT_MODEL_ID", "gpt-5-mini"),
        )
        kernel.add_service(chat_service)
        print("✅ Kernel Semantic Kernel créé avec succès")
        return True

    except Exception as e:
        print(f"❌ Erreur creation kernel: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_environment())
    if success:
        print("\n🎉 Environnement prêt pour la validation complète !")
    else:
        print("\n❌ Problème environnement - correction nécessaire")
