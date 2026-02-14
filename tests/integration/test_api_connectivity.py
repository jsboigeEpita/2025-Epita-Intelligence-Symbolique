import os
import openai
import pytest
from dotenv import load_dotenv


@pytest.mark.requires_api
def test_api_connectivity():
    """
    Vérifie la connectivité aux APIs OpenRouter et OpenAI.
    Ce test utilise les clés API stockées dans les variables d'environnement.

    Note: Ce test adapte son comportement selon les clés API disponibles:
    - Teste OpenRouter si OPENROUTER_API_KEY est configurée
    - Teste OpenAI si OPENAI_API_KEY est configurée
    - Skip si aucune clé n'est disponible
    """
    # Charger les variables d'environnement du fichier .env
    load_dotenv()

    # Récupérer la clé API OpenRouter et l'URL de base
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    openrouter_base_url = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )

    # Récupérer la clé API OpenAI
    openai_api_key_direct = os.getenv("OPENAI_API_KEY")

    print("--- Vérification de la connectivité API ---")

    # Test OpenRouter
    if openrouter_api_key:
        print("\n[OpenRouter]")
        assert (
            openrouter_api_key
        ), "La clé API OpenRouter (OPENROUTER_API_KEY) est manquante."
        try:
            client_openrouter = openai.OpenAI(
                base_url=openrouter_base_url,
                api_key=openrouter_api_key,
            )
            models_response = client_openrouter.models.list()
            print(f"  Connexion à OpenRouter ({openrouter_base_url}) réussie.")
            gpt4o_mini_available_or = any(
                model.id == "openai/gpt-5-mini" for model in models_response.data
            )
            print(
                f"  GPT-4o-mini disponible via OpenRouter: {'Oui' if gpt4o_mini_available_or else 'Non'}"
            )
            assert gpt4o_mini_available_or
        except Exception as e:
            pytest.fail(f"Erreur lors du test de OpenRouter: {e}")
    else:
        pytest.skip("Clé API OpenRouter (OPENROUTER_API_KEY) non trouvée. Test sauté.")

    # Test OpenAI Direct
    if openai_api_key_direct and openai_api_key_direct != openrouter_api_key:
        print("\n[OpenAI Direct]")
        assert (
            openai_api_key_direct
        ), "La clé API OpenAI (OPENAI_API_KEY) est manquante."
        try:
            client_openai_direct = openai.OpenAI(api_key=openai_api_key_direct)
            client_openai_direct.chat.completions.create(
                model="gpt-5-mini",
                messages=[{"role": "user", "content": "Bonjour!"}],
                max_tokens=5,
            )
            print("  Connexion directe à OpenAI (GPT-4o-mini) réussie.")
        except Exception as e:
            pytest.fail(f"Erreur lors du test de OpenAI Direct: {e}")
    else:
        print("\n[OpenAI Direct]")
        print("  Clé API OpenAI non configurée ou identique à OpenRouter. Test sauté.")
