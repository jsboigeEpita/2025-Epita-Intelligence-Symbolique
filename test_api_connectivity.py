import os
import openai
from dotenv import load_dotenv

# Charger les variables d'environnement du fichier .env
load_dotenv()

# Récupérer la clé API OpenRouter et l'URL de base
openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# Récupérer la clé API OpenAI (pour GPT-4o-mini via OpenRouter ou directement)
openai_api_key_direct = os.getenv("OPENAI_API_KEY")

print("--- Vérification de la connectivité API ---")

# Test OpenRouter
if openrouter_api_key:
    print("\n[OpenRouter]")
    print(f"  Clé API OpenRouter: {'Présente' if openrouter_api_key else 'Manquante'}")
    try:
        client_openrouter = openai.OpenAI(
            base_url=openrouter_base_url,
            api_key=openrouter_api_key,
        )
        # Tenter un appel simple, par exemple lister les modèles si l'API le permet,
        # ou un petit chat completion avec un modèle gratuit/peu coûteux.
        # Pour OpenRouter, un appel à /models est un bon test.
        models_response = client_openrouter.models.list()
        print(f"  Connexion à OpenRouter ({openrouter_base_url}) réussie.")
        # Vérifier si GPT-4o-mini est disponible via OpenRouter
        gpt4o_mini_available_or = any(model.id == "openai/gpt-4o-mini" for model in models_response.data)
        print(f"  GPT-4o-mini disponible via OpenRouter: {'Oui' if gpt4o_mini_available_or else 'Non'}")

    except openai.APIConnectionError as e:
        print(f"  Erreur de connexion à OpenRouter: {e}")
    except openai.AuthenticationError as e:
        print(f"  Erreur d'authentification OpenRouter (clé API invalide ?): {e}")
    except Exception as e:
        print(f"  Erreur inattendue avec OpenRouter: {e}")
else:
    print("\n[OpenRouter]")
    print("  Clé API OpenRouter (OPENROUTER_API_KEY) non trouvée dans .env")

# Test OpenAI Direct (si la clé est différente ou pour une vérification séparée)
# On suppose que si OPENAI_API_KEY est définie, elle pourrait être pour un accès direct
# ou utilisée par d'autres services qui s'attendent à ce nom de variable.
if openai_api_key_direct and openai_api_key_direct != openrouter_api_key:
    print("\n[OpenAI Direct]")
    print(f"  Clé API OpenAI (OPENAI_API_KEY): {'Présente'}")
    try:
        client_openai_direct = openai.OpenAI(api_key=openai_api_key_direct)
        # Test avec GPT-4o-mini
        client_openai_direct.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Bonjour!"}],
            max_tokens=5
        )
        print(f"  Connexion directe à OpenAI (GPT-4o-mini) réussie.")
    except openai.APIConnectionError as e:
        print(f"  Erreur de connexion directe à OpenAI: {e}")
    except openai.AuthenticationError as e:
        print(f"  Erreur d'authentification directe OpenAI (clé API invalide ?): {e}")
    except openai.NotFoundError as e:
        print(f"  Erreur: Modèle GPT-4o-mini non trouvé ou non accessible avec cette clé OpenAI directe: {e}")
    except Exception as e:
        print(f"  Erreur inattendue avec OpenAI Direct: {e}")
elif openai_api_key_direct == openrouter_api_key:
    print("\n[OpenAI Direct]")
    print("  Clé OPENAI_API_KEY est la même que OPENROUTER_API_KEY, test direct non effectué séparément.")
else:
    print("\n[OpenAI Direct]")
    print("  Clé API OpenAI (OPENAI_API_KEY) non trouvée pour un test direct.")

print("\n--- Fin de la vérification ---")