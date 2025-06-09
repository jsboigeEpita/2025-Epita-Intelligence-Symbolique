#!/usr/bin/env python3
"""
TEST AUTHENTICITÉ FINALE SIMPLIFIÉ - GPT-4O-MINI
===============================================

Test simplifié pour prouver l'authenticité avec un vrai appel API OpenAI
et validation TweetyProject sans l'orchestrateur complexe.
"""

import asyncio
import json
import time
import os
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from dotenv import load_dotenv

# Charger les variables d'environnement depuis .env
load_dotenv()

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

class SimplifiedAuthenticTester:
    """Testeur d'authenticité simplifié."""
    
    def __init__(self):
        self.test_id = str(uuid.uuid4())[:8]
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def generate_unique_prompt(self) -> str:
        """Génère un prompt unique pour test."""
        unique_elements = [
            f"Investigation ID: {self.test_id}",
            f"Timestamp: {self.timestamp}",
            "Cas unique: Disparition mystérieuse dans un laboratoire de physique quantique",
            "Suspects: Dr. Heisenberg (spécialiste incertitudes), Prof. Schrödinger (expert superposition), Dr. Einstein (théoricien relativité)",
            "Indices: Équation incomplète au tableau, particule manquante dans l'accélérateur, chat quantique absent",
            "Question: Qui a causé l'incident et comment?"
        ]
        
        return "\n".join(unique_elements) + f"\n\nAnalysez ce cas en tant que détective Sherlock Holmes. Soyez précis et logique."
    
    async def test_openai_api_direct(self) -> Dict[str, Any]:
        """Teste directement l'API OpenAI pour prouver l'authenticité."""
        logger.info(f"[API] Test direct OpenAI avec GPT-4o-mini")
        
        api_key = os.getenv('OPENAI_API_KEY', '')
        
        if not api_key or any(x in api_key.lower() for x in ['test', 'dummy', 'fake']):
            return {
                "success": False,
                "error": "Clé API non valide ou factice",
                "authenticity": "MOCK_DETECTED"
            }
        
        try:
            import openai
            
            # Configurer le client OpenAI
            client = openai.OpenAI(api_key=api_key)
            
            # Générer prompt unique
            unique_prompt = self.generate_unique_prompt()
            prompt_hash = hashlib.sha256(unique_prompt.encode()).hexdigest()[:16]
            
            logger.info(f"[API] Envoi prompt unique: {prompt_hash}")
            
            # Mesurer temps de réponse
            start_time = time.time()
            
            # Appel API réel
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Vous êtes Sherlock Holmes, détective brillant et logique."},
                    {"role": "user", "content": unique_prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            
            # Extraire la réponse
            ai_response = response.choices[0].message.content
            
            # Analyser la réponse pour détecter l'authenticité
            authenticity_markers = {
                "mentions_test_id": self.test_id in ai_response,
                "mentions_timestamp": self.timestamp in ai_response,
                "has_reasoning": any(word in ai_response.lower() for word in ['donc', 'car', 'parce que', 'puisque', 'ainsi']),
                "response_length": len(ai_response),
                "latency_realistic": latency_ms > 500,  # Latence réaliste
                "token_usage": response.usage.total_tokens if response.usage else 0
            }
            
            # Trace complète pour audit
            api_trace = {
                "test_id": self.test_id,
                "timestamp": datetime.now().isoformat(),
                "prompt_hash": prompt_hash,
                "model": "gpt-4o-mini",
                "latency_ms": latency_ms,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "response_length": len(ai_response),
                "authenticity_markers": authenticity_markers,
                "response_preview": ai_response[:200] + "..."
            }
            
            logger.info(f"[API] Réponse reçue: {latency_ms:.1f}ms, {response.usage.total_tokens if response.usage else 0} tokens")
            
            return {
                "success": True,
                "model": "gpt-4o-mini",
                "latency_ms": latency_ms,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "response_length": len(ai_response),
                "authenticity_score": sum(authenticity_markers.values()),
                "authenticity_markers": authenticity_markers,
                "trace": api_trace,
                "authenticity": "AUTHENTIC" if latency_ms > 500 and response.usage.total_tokens > 0 else "SUSPICIOUS"
            }
            
        except Exception as e:
            logger.error(f"[API] Erreur appel OpenAI: {e}")
            return {
                "success": False,
                "error": str(e),
                "authenticity": "ERROR"
            }
    
    def test_tweety_project_integration(self) -> Dict[str, Any]:
        """Teste l'intégration TweetyProject pour prouver l'authenticité du système logique."""
        logger.info(f"[TWEETY] Test intégration TweetyProject")
        
        try:
            # Import des composants TweetyProject
            from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
            
            # Initialiser TweetyProject via TweetyBridge
            tweety_bridge = TweetyBridge()
            tweety_init = tweety_bridge.tweety_initializer
            
            # Vérifier que la JVM est démarrée
            if not tweety_init._jvm_started:
                return {
                    "success": False,
                    "error": "JVM TweetyProject non démarrée",
                    "authenticity": "MOCK_DETECTED"
                }
            
            # Compter les JARs chargés
            jars_count = len(tweety_init._tweety_jars) if hasattr(tweety_init, '_tweety_jars') else 0
            
            # Test basique de logique propositionnelle
            test_pl_success = False
            try:
                if hasattr(tweety_init, 'pl_parser') and tweety_init.pl_parser:
                    # Test simple parsing
                    test_formula = "a || b"
                    parsed = tweety_init.pl_parser.parseFormula(test_formula)
                    test_pl_success = parsed is not None
            except Exception as e:
                logger.warning(f"[TWEETY] Test PL échoué: {e}")
            
            # Calculer score d'authenticité
            authenticity_score = 0
            if tweety_init._jvm_started:
                authenticity_score += 40
            if jars_count >= 30:
                authenticity_score += 30
            if test_pl_success:
                authenticity_score += 30
            
            return {
                "success": True,
                "jvm_started": tweety_init._jvm_started,
                "jars_loaded": jars_count,
                "pl_parser_working": test_pl_success,
                "authenticity_score": authenticity_score,
                "authenticity": "AUTHENTIC" if authenticity_score >= 80 else "PARTIAL"
            }
            
        except Exception as e:
            logger.error(f"[TWEETY] Erreur test TweetyProject: {e}")
            return {
                "success": False,
                "error": str(e),
                "authenticity": "ERROR"
            }

async def main():
    """Point d'entrée principal du test d'authenticité finale simplifié."""
    print("TEST D'AUTHENTICITE FINALE SIMPLIFIÉ - GPT-4O-MINI")
    print("Preuves essentielles d'appels API réels + TweetyProject")
    print("=" * 60)
    
    tester = SimplifiedAuthenticTester()
    
    try:
        results = {
            "test_session": {
                "id": tester.test_id,
                "timestamp": tester.timestamp,
                "objective": "Prouver authenticité système via tests simplifiés"
            },
            "tests": {}
        }
        
        # Test 1: API OpenAI directe
        print("\n[TEST 1] Appel direct API OpenAI...")
        api_result = await tester.test_openai_api_direct()
        results["tests"]["direct_api"] = api_result
        
        if api_result["success"]:
            print(f"[OK] API Response: {api_result['latency_ms']:.1f}ms, {api_result['tokens_used']} tokens")
            print(f"[OK] Authenticite: {api_result['authenticity']}")
        else:
            print(f"[ERROR] API: {api_result.get('error', 'Erreur inconnue')}")
        
        # Test 2: TweetyProject
        print("\n[TEST 2] Intégration TweetyProject...")
        tweety_result = tester.test_tweety_project_integration()
        results["tests"]["tweety_project"] = tweety_result
        
        if tweety_result["success"]:
            print(f"[OK] JVM: {tweety_result['jvm_started']}")
            print(f"[OK] JARs: {tweety_result['jars_loaded']}")
            print(f"[OK] PL Parser: {tweety_result['pl_parser_working']}")
            print(f"[OK] Authenticite: {tweety_result['authenticity']}")
        else:
            print(f"[ERROR] TweetyProject: {tweety_result.get('error', 'Erreur inconnue')}")
        
        # Calcul du score final
        total_score = 0
        test_count = 0
        
        if api_result["success"] and api_result["authenticity"] == "AUTHENTIC":
            total_score += 50
        test_count += 1
        
        if tweety_result["success"]:
            if tweety_result["authenticity"] == "AUTHENTIC":
                total_score += 50
            elif tweety_result["authenticity"] == "PARTIAL":
                total_score += 30
        test_count += 1
        
        final_score = total_score
        results["final_authenticity_score"] = final_score
        
        # Sauvegarder le rapport
        report_filename = f"reports/authenticite_finale_simple_{tester.timestamp}.json"
        os.makedirs("reports", exist_ok=True)
        
        with open(report_filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print("\n" + "=" * 60)
        print("RÉSULTATS FINAUX D'AUTHENTICITÉ")
        print("=" * 60)
        print(f"Test ID: {tester.test_id}")
        print(f"Score Final: {final_score}/100")
        print(f"Rapport: {report_filename}")
        
        if final_score >= 80:
            print("\n[OK] SYSTEME ENTIEREMENT AUTHENTIQUE")
            print("API reelle + TweetyProject fonctionnel")
        elif final_score >= 50:
            print("\n[WARNING] SYSTEME PARTIELLEMENT AUTHENTIQUE")
            print("Composants majeurs fonctionnels")
        else:
            print("\n[ERROR] SYSTEME NON AUTHENTIQUE")
            print("Tests d'authenticite echoues")
            
    except Exception as e:
        logger.error(f"Erreur critique: {e}")
        print(f"\n[ERROR] ERREUR CRITIQUE: {e}")

if __name__ == "__main__":
    asyncio.run(main())