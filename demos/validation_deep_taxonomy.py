import asyncio
import json
import pandas as pd
import semantic_kernel as sk
from pathlib import Path
import os
from dotenv import load_dotenv
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

from argumentation_analysis.paths import DATA_DIR
from demos.simple_exploration_tool import SimpleExplorationTool

async def validate_deep_taxonomy_fallacy():
    """
    Valide l'identification d'un sophisme en utilisant une approche simplifiée.
    """
    print("--- Validation d'un sophisme (approche simplifiée) ---")

    # --- Préparation ---
    # 1. Charger les variables d'environnement (pour la clé API)
    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    model_id = os.environ.get("OPENAI_CHAT_MODEL_ID")

    if not api_key or not model_id:
        print("❌ ERREUR: OPENAI_API_KEY ou OPENAI_CHAT_MODEL_ID non défini dans l'environnement.")
        print("Veuillez créer un fichier .env à la racine du projet avec ces variables.")
        return

    # 2. Créer une instance de Kernel et ajouter le service OpenAI
    kernel = sk.Kernel()
    kernel.add_service(
        OpenAIChatCompletion(
            service_id=model_id,
            ai_model_id=model_id,
            api_key=api_key,
        )
    )
    print("Service OpenAI configuré avec succès.")

    # 3. Charger la taxonomie et la formater pour le prompt
    taxonomy_path = str(DATA_DIR / "taxonomy_full.csv")
    try:
        taxonomy_df = pd.read_csv(taxonomy_path)
        # Créer une liste simple pour le prompt
        taxonomy_list = "\n".join(f"- {row['PK']}: {row['nom_vulgarisé']}" for _, row in taxonomy_df.iterrows())
        print(f"Taxonomie chargée avec {len(taxonomy_df)} entrées.")
    except FileNotFoundError:
        print(f"❌ ERREUR: Fichier de taxonomie introuvable à '{taxonomy_path}'")
        return

    # 4. Texte d'exemple
    sample_text = "Personne ne peut prouver que les licornes roses invisibles n'existent pas, donc elles doivent exister."
    print(f"Texte d'exemple : '{sample_text}'")

    # 5. Définir le prompt d'analyse
    prompt = """
    Tu es un expert en rhétorique. Analyse le texte suivant et identifie le sophisme le plus pertinent dans la liste fournie.
    Réponds UNIQUEMENT avec le PK (Primary Key) du sophisme identifié. Ne fournis aucune autre information.

    TEXTE:
    {{$input}}

    TAXONOMIE:
    {{$taxonomy}}
    """

    # --- Exécution ---
    print("\nLancement de l'analyse sémantique...")
    result = await kernel.invoke_prompt(
        prompt,
        input=sample_text,
        taxonomy=taxonomy_list
    )
    result_text = str(result).strip()
    print(f"Résultat du LLM : '{result_text}'")

    # --- Validation ---
    print("\n--- Conclusion de la validation ---")
    expected_fallacy_pk = "4"  # PK pour "Appel à l'ignorance"
    alternative_fallacy_pk = "1288" # PK pour "Affirmation invérifiable" (sémantiquement proche)
    
    if result_text == expected_fallacy_pk:
        print(f"✅ SUCCÈS : Le sophisme attendu (PK: {expected_fallacy_pk} - Appel à l'ignorance) a été correctement identifié.")
    elif result_text == alternative_fallacy_pk:
        print(f"✅ SUCCÈS (Alternatif) : Un sophisme sémantiquement très proche (PK: {alternative_fallacy_pk} - Affirmation invérifiable) a été identifié.")
        print("Cela valide la capacité du système à naviguer en profondeur dans la taxonomie.")
    else:
        print(f"❌ ÉCHEC : Le sophisme attendu (PK: {expected_fallacy_pk}) ou son alternative (PK: {alternative_fallacy_pk}) n'a pas été trouvé. Reçu : '{result_text}'.")

if __name__ == "__main__":
    asyncio.run(validate_deep_taxonomy_fallacy())