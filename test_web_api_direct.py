#!/usr/bin/env python3
"""
Test direct de l'API web pour diagnostiquer pourquoi la détection de sophismes
ne fonctionne pas via l'interface web malgré nos corrections.
"""

import sys
import os
import requests
import json

# Ajouter le répertoire parent au path pour importer les modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

def test_web_api_fallacy_detection():
    """
    Test direct de l'endpoint /api/analyze pour la détection de sophismes
    """
    print("TEST DIRECT DE L'API WEB POUR DÉTECTION SOPHISMES")
    print("=" * 60)
    
    # URL de l'API locale
    api_url = "http://localhost:5000/api/analyze"
    
    # Texte d'exemple exact utilisé dans l'interface web
    text = "Dieu existe parce que la Bible le dit, et la Bible est vraie parce qu'elle est la parole de Dieu."
    
    # Paramètres exacts de l'interface web
    payload = {
        "text": text,
        "analyze_fallacies": True,
        "analyze_structure": True,
        "evaluate_coherence": True
    }
    
    print(f"URL: {api_url}")
    print(f"Texte: '{text}'")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print()
    
    try:
        # Envoi de la requête POST
        print("Envoi de la requete a l'API...")
        response = requests.post(api_url, json=payload, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("Reponse recue avec succes")
            print()
            
            # Affichage de la réponse complète pour diagnostic
            print("RÉPONSE COMPLÈTE:")
            print("-" * 40)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            print()
            
            # Analyse spécifique des sophismes
            if 'fallacies' in result:
                fallacies = result['fallacies']
                print("ANALYSE DES SOPHISMES:")
                print(f"  Sophismes detectes: {len(fallacies)}")
                
                if fallacies:
                    for i, fallacy in enumerate(fallacies, 1):
                        print(f"  {i}. {fallacy.get('type', 'Type inconnu')}")
                        print(f"     Description: {fallacy.get('description', 'N/A')}")
                        print(f"     Confiance: {fallacy.get('confidence', 'N/A')}")
                else:
                    print("  AUCUN SOPHISME DETECTE")
            
            # Analyse du score de qualité
            if 'quality_score' in result:
                quality = result['quality_score']
                print(f"SCORE DE QUALITE: {quality}")
                
                if quality > 90:
                    print("  SCORE TROP ELEVE - Sophisme non pris en compte")
                else:
                    print("  Score acceptable")
            
            return result
                    
        else:
            print(f"Erreur HTTP: {response.status_code}")
            print(f"Reponse: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Erreur de connexion: {e}")
        return None

def test_direct_service_import():
    """
    Test direct du service sans passer par l'API HTTP
    """
    print("\nTEST DIRECT DU SERVICE PYTHON")
    print("=" * 40)
    
    try:
        from argumentation_analysis.services.web_api.services.fallacy_service import FallacyService
        
        print("Import du FallacyService reussi")
        
        # Initialisation du service
        service = FallacyService()
        print("Initialisation du service reussie")
        
        # Test avec le même texte
        text = "Dieu existe parce que la Bible le dit, et la Bible est vraie parce qu'elle est la parole de Dieu."
        
        print(f"Test avec: '{text}'")
        
        # Appel direct de la détection
        fallacies = service.detect_fallacies(text)
        
        print(f"Resultat: {len(fallacies)} sophisme(s) detecte(s)")
        
        if fallacies:
            for i, fallacy in enumerate(fallacies, 1):
                print(f"  {i}. {fallacy}")
        else:
            print("  AUCUN SOPHISME DETECTE PAR LE SERVICE DIRECT")
        
        return fallacies
        
    except Exception as e:
        print(f"Erreur lors du test direct: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("DIAGNOSTIC COMPLET: API WEB vs SERVICE DIRECT")
    print("=" * 60)
    
    # Test de l'API web
    web_result = test_web_api_fallacy_detection()
    
    # Test direct du service
    direct_result = test_direct_service_import()
    
    print("\n" + "=" * 60)
    print("RÉSUMÉ DU DIAGNOSTIC:")
    
    if web_result and direct_result:
        web_fallacies = len(web_result.get('fallacies', []))
        direct_fallacies = len(direct_result) if direct_result else 0
        
        print(f"  API Web: {web_fallacies} sophisme(s)")
        print(f"  Service Direct: {direct_fallacies} sophisme(s)")
        
        if web_fallacies == direct_fallacies:
            print("  Coherence entre API web et service direct")
        else:
            print("  INCOHERENCE DETECTEE")
    
    print("=" * 60)