#!/usr/bin/env python3
"""Test rapide de connectivité API OpenAI"""

import os
from dotenv import load_dotenv

# Chargement .env
load_dotenv()

try:
    import openai
    client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Test de connectivité - répondez juste OK"}],
        max_tokens=5
    )
    
    print(f"[OK] API OpenAI fonctionnelle: {response.choices[0].message.content}")
    
except Exception as e:
    print(f"[ERREUR] API OpenAI: {e}")