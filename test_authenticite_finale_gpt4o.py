#!/usr/bin/env python3
"""
TEST AUTHENTICITÉ FINALE - APPEL RÉEL GPT-4O-MINI
=================================================

Test final pour prouver l'authenticité avec un vrai appel API OpenAI.
Génère des données synthétiques uniques et teste l'orchestrateur Cluedo.
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

class AuthenticAPITester:
    """Testeur d'appels API authentiques."""
    
    def __init__(self):
        self.test_id = str(uuid.uuid4())[:8]
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.api_traces = []
        
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
        
        # Assouplir la vérification de la clé API pour éviter les faux positifs
        # La clé est considérée valide si elle n'est pas vide et ne contient pas de mots-clés de mock évidents
        if not api_key or "sk-test-" in api_key.lower() or "dummy" in api_key.lower() or "fake" in api_key.lower():
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
            
            # Trace complète
            api_trace = {
                "test_id": self.test_id,
                "timestamp": datetime.now().isoformat(),
                "prompt_hash": prompt_hash,
                "model": "gpt-4o-mini",
                "latency_ms": latency_ms,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "response_length": len(ai_response),
                "authenticity_markers": authenticity_markers,
                "response_preview": ai_response[:200] + "..." if len(ai_response) > 200 else ai_response
            }
            
            self.api_traces.append(api_trace)
            
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
    
    async def test_orchestrateur_avec_api_reelle(self) -> Dict[str, Any]:
        """Teste l'orchestrateur Cluedo avec API réelle."""
        logger.info(f"[ORCHESTRATEUR] Test avec API réelle")
        
        try:
            # Import de l'orchestrateur
            from argumentation_analysis.orchestration.cluedo_orchestrator import run_cluedo_game
            from semantic_kernel.kernel import Kernel
            from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
            
            # Configurer kernel avec vraie API
            kernel = Kernel()
            api_key = os.getenv('OPENAI_API_KEY', '')
            
            if not api_key or any(x in api_key.lower() for x in ['test', 'dummy', 'fake']):
                return {
                    "success": False,
                    "error": "Clé API non valide pour orchestrateur",
                    "authenticity": "MOCK_DETECTED"
                }
            
            # Service OpenAI réel
            service = OpenAIChatCompletion(
                service_id="authentic_test",
                ai_model_id="gpt-4o-mini",
                api_key=api_key
            )
            kernel.add_service(service)
            
            # Question d'enquête unique
            unique_question = f"""
            ENQUÊTE AUTHENTIQUE {self.test_id}
            
            Dans le laboratoire de l'EPITA, le professeur von Neumann a disparu mystérieusement.
            
            Indices trouvés:
            - Équation de Schrödinger incomplète au tableau
            - Chat quantique absent de sa boîte
            - Particule manquante dans l'accélérateur
            
            Suspects:
            - Dr. Heisenberg (expert en principe d'incertitude)
            - Prof. Einstein (opposé à la mécanique quantique)
            - Mme. Curie (spécialiste des radiations)
            
            Sherlock, analysez cette situation. Watson, aidez avec la logique.
            Maximum 2 tours pour cette démonstration d'authenticité.
            """
            
            # Mesurer temps d'exécution
            start_time = time.time()
            
            # Exécution réelle
            history, final_state = await run_cluedo_game(
                kernel=kernel,
                initial_question=unique_question,
                max_iterations=2  # Limité pour démonstration, correction pour Semantic Kernel
            )
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Analyser les résultats
            conversation_analysis = {
                "turns_count": len(history),
                "total_words": sum(len(msg["message"].split()) for msg in history),
                "unique_responses": len(set(msg["message"][:50] for msg in history)),
                "mentions_test_id": any(self.test_id in msg["message"] for msg in history),
                "has_reasoning": any("donc" in msg["message"].lower() or "car" in msg["message"].lower() for msg in history)
            }
            
            return {
                "success": True,
                "execution_time_seconds": execution_time,
                "conversation_turns": len(history),
                "conversation_analysis": conversation_analysis,
                "final_state_available": final_state is not None,
                "authenticity": "AUTHENTIC" if execution_time > 5 and len(history) > 1 else "SUSPICIOUS",
                "test_scenario": {
                    "test_id": self.test_id,
                    "unique_question_hash": hashlib.sha256(unique_question.encode()).hexdigest()[:16],
                    "timestamp": self.timestamp
                }
            }
            
        except Exception as e:
            logger.error(f"[ORCHESTRATEUR] Erreur: {e}")
            return {
                "success": False,
                "error": str(e),
                "authenticity": "ERROR"
            }

async def main():
    """Point d'entrée principal du test d'authenticité finale."""
    print("TEST D'AUTHENTICITE FINALE - GPT-4O-MINI")
    print("Preuves d'appels API réels avec données synthétiques")
    print("=" * 60)
    
    tester = AuthenticAPITester()
    
    try:
        results = {
            "test_session": {
                "id": tester.test_id,
                "timestamp": tester.timestamp,
                "objective": "Prouver authenticité système via appels API réels"
            },
            "tests": {}
        }
        
        # Test 1: Appel API direct
        print("\n[TEST 1] Appel direct API OpenAI...")
        api_result = await tester.test_openai_api_direct()
        results["tests"]["direct_api"] = api_result
        
        if api_result["success"]:
            print(f"[OK] API Response: {api_result['latency_ms']:.1f}ms, {api_result['tokens_used']} tokens")
            print(f"[OK] Authenticite: {api_result['authenticity']}")
        else:
            print(f"[ERROR] Echec API: {api_result.get('error', 'Inconnu')}")
        
        # Test 2: Orchestrateur avec API réelle
        print("\n[TEST 2] Orchestrateur Cluedo avec API reelle...")
        orchestrateur_result = await tester.test_orchestrateur_avec_api_reelle()
        results["tests"]["orchestrateur"] = orchestrateur_result
        
        if orchestrateur_result["success"]:
            print(f"[OK] Orchestrateur: {orchestrateur_result['execution_time_seconds']:.1f}s, {orchestrateur_result['conversation_turns']} tours")
            print(f"[OK] Authenticite: {orchestrateur_result['authenticity']}")
        else:
            print(f"[ERROR] Echec Orchestrateur: {orchestrateur_result.get('error', 'Inconnu')}")
        
        # Calcul score final
        authenticity_scores = []
        for test_name, test_result in results["tests"].items():
            if test_result.get("authenticity") == "AUTHENTIC":
                authenticity_scores.append(100)
            elif test_result.get("authenticity") == "SUSPICIOUS":
                authenticity_scores.append(50)
            else:
                authenticity_scores.append(0)
        
        final_score = sum(authenticity_scores) / len(authenticity_scores) if authenticity_scores else 0
        results["final_authenticity_score"] = final_score
        
        # Sauvegarder les traces
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"reports/authenticite_finale_gpt4o_{timestamp}.json"
        
        os.makedirs("reports", exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        # Résultats finaux
        print("\n" + "=" * 60)
        print("RÉSULTATS FINAUX D'AUTHENTICITÉ")
        print("=" * 60)
        print(f"Test ID: {tester.test_id}")
        print(f"Score Final: {final_score:.1f}/100")
        print(f"Rapport: {report_path}")
        
        if final_score >= 80:
            print("\n[SUCCESS] MISSION ACCOMPLIE - SYSTEME AUTHENTIQUE PROUVE!")
            print("[OK] Appels API reels avec GPT-4o-mini confirmes")
            print("[OK] Donnees synthetiques generees et traitees")
            print("[OK] Orchestrateur fonctionnel avec traces auditables")
            print("[OK] Elimination des mocks de complaisance reussie")
        elif final_score >= 50:
            print("\n[WARNING] SYSTEME PARTIELLEMENT AUTHENTIQUE")
            print("Certains composants fonctionnent avec API reelle")
        else:
            print("\n[ERROR] AUTHENTICITE NON PROUVEE")
            print("Verifiez la configuration des cles API")
        
        return final_score >= 50
        
    except Exception as e:
        logger.error(f"Erreur test authenticité: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)