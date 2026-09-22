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

    # Vérification modèle (#2383) : un diagnostic rapporte ce qui est CONFIGURÉ.
    # Le repli « gpt-5.6-luna » qui vivait ici fabriquait un succès — variable
    # absente, le kernel était bâti sur un défaut codé en dur et le script
    # rendait « ✅ » pour une configuration qui n'était pas dans .env (entrée
    # versée à #2377 par la revue coord R1043). Un vide n'est pas une
    # configuration non plus (#2281 : vide ≠ absent, et vide ≠ configuré).
    model_id = os.getenv("OPENAI_CHAT_MODEL_ID")
    if not model_id:
        print("❌ OPENAI_CHAT_MODEL_ID non configurée")
        return False

    print(f"✅ OPENAI_CHAT_MODEL_ID configurée : {model_id}")

    # Test kernel
    try:
        kernel = Kernel()
        chat_service = OpenAIChatCompletion(
            service_id="test",
            api_key=api_key,
            ai_model_id=model_id,
        )
        kernel.add_service(chat_service)
        print(f"✅ Kernel Semantic Kernel créé avec succès (modèle : {model_id})")
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
