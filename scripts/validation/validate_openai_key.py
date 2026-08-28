import os
from openai import OpenAI
from dotenv import load_dotenv


def validate_key():
    # Charger les variables d'environnement depuis .env
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(
            "❌ ERREUR : La variable d'environnement OPENAI_API_KEY n'est pas définie."
        )
        return

    print(f"🔑 Clé API trouvée, commençant par : {api_key[:4]}...")

    try:
        client = OpenAI(api_key=api_key)
        models = client.models.list()
        print("✅ Connexion réussie à l'API OpenAI.")
        print(
            f"🤖 Modèle gpt-5.6-luna trouvé : {'gpt-5.6-luna' in [m.id for m in models.data]}"
        )
    except Exception as e:
        print(f"❌ ERREUR : Échec de la connexion à l'API OpenAI : {e}")


if __name__ == "__main__":
    validate_key()
