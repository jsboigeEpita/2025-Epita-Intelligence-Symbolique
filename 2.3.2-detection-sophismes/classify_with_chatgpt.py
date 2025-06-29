import argparse
import openai
import json
import os

# Load metadata to get fallacy types
with open('./data/french_metadata.json', 'r') as f:
    metadata = json.load(f)
FALLACY_TYPES = metadata['fallacy_types']

def classify_fallacies_with_chatgpt(text: str, api_key: str) -> dict:
    """
    Classifies fallacies in a given French text using the OpenAI ChatGPT API.
    """
    openai.api_key = api_key

    fallacy_list_str = ", ".join([f"'{f}'" for f in FALLACY_TYPES])

    prompt = f"""Vous êtes un expert en logique et en argumentation. Analysez le texte français suivant et identifiez tous les sophismes (fallacies) présents parmi la liste suivante : {fallacy_list_str}. Pour chaque sophisme détecté, indiquez son nom (en français et entre parenthèses en anglais si applicable, par exemple 'Attaque personnelle (Ad Hominem)'), et fournissez une brève justification expliquant pourquoi il s'agit de ce sophisme dans le contexte du texte. Si aucun sophisme n'est détecté, indiquez-le.

Retournez le résultat au format JSON, comme suit :
{{
  "fallacies_detected": true/false,
  "fallacies": [
    {{
      "type": "Nom du sophisme (Nom Anglais)",
      "justification": "Justification concise ici."
    }}
  ]
}}

Texte à analyser : {json.dumps(text)}
"""

    try:
        response = openai.chat.completions.create(
            model="gpt-4",  # You can change this to "gpt-4" or other available models
            messages=[
                {"role": "system", "content": "You are a helpful assistant that classifies fallacies in French text."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0, # Keep temperature low for consistent classification
        )

        chat_response_content = response.choices[0].message.content
        
        # Attempt to parse the JSON response
        try:
            parsed_response = json.loads(chat_response_content)
            return parsed_response
        except json.JSONDecodeError:
            print(f"Erreur: La réponse de l'API n'est pas un JSON valide.\nRéponse brute: {chat_response_content}")
            return {"fallacies_detected": False, "fallacies": [], "error": "Invalid JSON response"}

    except openai.APIError as e:
        print(f"Erreur de l'API OpenAI: {e}")
        return {"fallacies_detected": False, "fallacies": [], "error": str(e)}
    except Exception as e:
        print(f"Une erreur inattendue s'est produite: {e}")
        return {"fallacies_detected": False, "fallacies": [], "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="Classify fallacies in French text using ChatGPT API.")
    parser.add_argument("text", type=str, help="The French text to analyze.")
    parser.add_argument("--api_key", type=str, help="Your OpenAI API Key. If not provided, it will try to read from OPENAI_API_KEY environment variable.", default=os.environ.get("OPENAI_API_KEY"))
    
    args = parser.parse_args()

    if not args.api_key:
        args.api_key = input("Veuillez entrer votre clé API OpenAI: ")

    if not args.api_key:
        print("Erreur: Clé API OpenAI non fournie. Impossible de procéder.")
        return

    print(f"\nAnalyse du texte avec ChatGPT: '{args.text}'\n")
    results = classify_fallacies_with_chatgpt(args.text, args.api_key)
    
    print("\n" + "="*50)
    print("Résultats de la classification ChatGPT:")
    print("="*50)
    if results.get("fallacies_detected"):
        for fallacy in results["fallacies"]:
            print(f"- Type: {fallacy.get('type', 'N/A')}")
            print(f"  Justification: {fallacy.get('justification', 'N/A')}\n")
    else:
        print("Aucun sophisme détecté ou une erreur est survenue.")
        if "error" in results:
            print(f"Détails de l'erreur: {results['error']}")
    print("="*50)

if __name__ == '__main__':
    main()
