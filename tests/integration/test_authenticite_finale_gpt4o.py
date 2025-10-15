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
    level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s"
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
            "Question: Qui a causé l'incident et comment?",
        ]

        return (
            "\n".join(unique_elements)
            + f"\n\nAnalysez ce cas en tant que détective Sherlock Holmes. Soyez précis et logique. Veuillez inclure l'Investigation ID '{self.test_id}' dans votre réponse."
        )

    def test_openai_api_direct(self) -> Dict[str, Any]:
        """Teste directement l'API OpenAI pour prouver l'authenticité."""
        logger.info(f"[API] Test direct OpenAI avec GPT-4o-mini")

        api_key = os.getenv("OPENAI_API_KEY", "")

        if (
            not api_key
            or "sk-test-" in api_key.lower()
            or "dummy" in api_key.lower()
            or "fake" in api_key.lower()
        ):
            return {
                "success": False,
                "error": "Clé API non valide ou factice",
                "authenticity": "MOCK_DETECTED",
            }

        try:
            import openai

            client = openai.OpenAI(api_key=api_key)
            unique_prompt = self.generate_unique_prompt()
            prompt_hash = hashlib.sha256(unique_prompt.encode()).hexdigest()[:16]
            logger.info(f"[API] Envoi prompt unique: {prompt_hash}")
            start_time = time.time()

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "Vous êtes Sherlock Holmes, détective brillant et logique.",
                    },
                    {"role": "user", "content": unique_prompt},
                ],
                max_tokens=1500,
                temperature=0.7,
            )

            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            ai_response = response.choices[0].message.content

            authenticity_markers = {
                "mentions_test_id": self.test_id in ai_response,
                "mentions_timestamp": self.timestamp in ai_response,
                "has_reasoning": any(
                    word in ai_response.lower()
                    for word in [
                        "donc",
                        "car",
                        "parce que",
                        "puisque",
                        "ainsi",
                        "élémentaire",
                        "déduction",
                    ]
                ),
                "response_length": len(ai_response),
                "latency_realistic": latency_ms > 500,
                "token_usage": response.usage.total_tokens if response.usage else 0,
            }

            api_trace = {
                "test_id": self.test_id,
                "timestamp": datetime.now().isoformat(),
                "prompt_hash": prompt_hash,
                "model": "gpt-4o-mini",
                "latency_ms": latency_ms,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "response_length": len(ai_response),
                "authenticity_markers": authenticity_markers,
                "full_response": ai_response,
            }

            self.api_traces.append(api_trace)
            logger.info(
                f"[API] Réponse reçue: {latency_ms:.1f}ms, {response.usage.total_tokens if response.usage else 0} tokens"
            )

            return {
                "success": True,
                "model": "gpt-4o-mini",
                "latency_ms": latency_ms,
                "tokens_used": response.usage.total_tokens if response.usage else 0,
                "response_length": len(ai_response),
                "authenticity_score": sum(authenticity_markers.values()),
                "authenticity_markers": authenticity_markers,
                "trace": api_trace,
                "authenticity": "AUTHENTIC"
                if latency_ms > 500
                and response.usage.total_tokens > 0
                and authenticity_markers["mentions_test_id"]
                else "SUSPICIOUS",
            }

        except Exception as e:
            logger.error(f"[API] Erreur appel OpenAI: {e}")
            return {"success": False, "error": str(e), "authenticity": "ERROR"}

    def test_orchestrateur_avec_api_reelle(self) -> Dict[str, Any]:
        """Teste l'orchestrateur Cluedo avec API réelle."""
        logger.info(f"[ORCHESTRATEUR] Test avec API réelle")

        try:
            from argumentation_analysis.orchestration.cluedo_orchestrator import (
                run_cluedo_game,
            )
            from semantic_kernel.kernel import Kernel
            from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion
            from semantic_kernel.contents.text_content import TextContent
            from semantic_kernel.contents.chat_message_content import ChatMessageContent

            kernel = Kernel()
            api_key = os.getenv("OPENAI_API_KEY", "")

            if not api_key or any(
                x in api_key.lower() for x in ["test", "dummy", "fake"]
            ):
                return {
                    "success": False,
                    "error": "Clé API non valide pour orchestrateur",
                    "authenticity": "MOCK_DETECTED",
                }

            service = OpenAIChatCompletion(
                service_id="authentic_test", ai_model_id="gpt-4o-mini", api_key=api_key
            )
            kernel.add_service(service)

            unique_question = f"""
            ENQUÊTE AUTHENTIQUE {self.test_id} - PHASE ORCHESTRATEUR
            
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
            Veuillez inclure l'ID d'enquête '{self.test_id}' dans vos échanges.
            Maximum 3 tours pour cette démonstration d'authenticité.
            """

            start_time = time.time()
            history, final_state = asyncio.run(
                run_cluedo_game(
                    kernel=kernel, initial_question=unique_question, max_iterations=3
                )
            )
            end_time = time.time()
            execution_time = end_time - start_time

            processed_history_texts = []
            if history:  # S'assurer que history n'est pas None
                for msg in history:
                    text_content = None
                    if isinstance(msg, ChatMessageContent):
                        if msg.content is not None:
                            text_content = str(msg.content)
                        elif msg.items:
                            for item in msg.items:
                                if isinstance(item, TextContent):
                                    text_content = item.text
                                    break
                    if text_content:
                        processed_history_texts.append(text_content)

            conversation_analysis = {
                "turns_count": len(history) if history else 0,
                "total_words": sum(
                    len(text.split()) for text in processed_history_texts
                ),
                "unique_responses": len(
                    set(text[:50] for text in processed_history_texts)
                ),
                "mentions_test_id": any(
                    self.test_id in text for text in processed_history_texts
                ),
                "has_reasoning": any(
                    word in text.lower()
                    for word in [
                        "donc",
                        "car",
                        "parce que",
                        "puisque",
                        "ainsi",
                        "élémentaire",
                        "déduction",
                    ]
                    for text in processed_history_texts
                ),
            }

            return {
                "success": True,
                "execution_time_seconds": execution_time,
                "conversation_turns": len(history) if history else 0,
                "conversation_analysis": conversation_analysis,
                "final_state_available": final_state is not None,
                "authenticity": "AUTHENTIC"
                if execution_time > 5
                and (len(history) if history else 0) > 1
                and conversation_analysis["mentions_test_id"]
                else "SUSPICIOUS",
                "test_scenario": {
                    "test_id": self.test_id,
                    "unique_question_hash": hashlib.sha256(
                        unique_question.encode()
                    ).hexdigest()[:16],
                    "timestamp": self.timestamp,
                },
                "history_preview": [
                    text[:200] + "..." if len(text) > 200 else text
                    for text in processed_history_texts
                ],
            }

        except Exception as e:
            logger.error(f"[ORCHESTRATEUR] Erreur: {e}")
            import traceback

            logger.error(traceback.format_exc())
            return {"success": False, "error": str(e), "authenticity": "ERROR"}


def main():
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
                "objective": "Prouver authenticité système via appels API réels",
            },
            "tests": {},
        }

        print("\n[TEST 1] Appel direct API OpenAI...")
        api_result = tester.test_openai_api_direct()
        results["tests"]["direct_api"] = api_result

        if api_result["success"]:
            print(
                f"[OK] API Response: {api_result['latency_ms']:.1f}ms, {api_result['tokens_used']} tokens"
            )
            print(f"[OK] Authenticite: {api_result['authenticity']}")
            if api_result["authenticity_markers"].get("mentions_test_id"):
                print(f"[OK] Test ID '{tester.test_id}' mentionné dans la réponse.")
            else:
                print(
                    f"[WARNING] Test ID '{tester.test_id}' NON mentionné dans la réponse directe."
                )
        else:
            print(f"[ERROR] Echec API: {api_result.get('error', 'Inconnu')}")

        print("\n[TEST 2] Orchestrateur Cluedo avec API reelle...")
        orchestrateur_result = tester.test_orchestrateur_avec_api_reelle()
        results["tests"]["orchestrateur"] = orchestrateur_result

        if orchestrateur_result["success"]:
            print(
                f"[OK] Orchestrateur: {orchestrateur_result['execution_time_seconds']:.1f}s, {orchestrateur_result['conversation_turns']} tours"
            )
            print(f"[OK] Authenticite: {orchestrateur_result['authenticity']}")
            if orchestrateur_result["conversation_analysis"].get("mentions_test_id"):
                print(
                    f"[OK] Test ID '{tester.test_id}' mentionné dans la conversation de l'orchestrateur."
                )
            else:
                print(
                    f"[WARNING] Test ID '{tester.test_id}' NON mentionné dans la conversation de l'orchestrateur."
                )
        else:
            print(
                f"[ERROR] Echec Orchestrateur: {orchestrateur_result.get('error', 'Inconnu')}"
            )

        authenticity_scores = []
        for test_name, test_result in results["tests"].items():
            if test_result.get("authenticity") == "AUTHENTIC":
                authenticity_scores.append(100)
            elif test_result.get("authenticity") == "SUSPICIOUS":
                authenticity_scores.append(50)
            else:
                authenticity_scores.append(0)

        final_score = (
            sum(authenticity_scores) / len(authenticity_scores)
            if authenticity_scores
            else 0
        )
        results["final_authenticity_score"] = final_score

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = (
            f"reports/authenticite_finale_gpt4o_{tester.test_id}_{timestamp}.json"
        )

        os.makedirs("reports", exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

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
            print("\n[WARNING] SYSTEME PARTIELLEMENT AUTHENTIQUE OU PREUVE FAIBLE")
            print(
                "Certains composants fonctionnent avec API reelle, mais la preuve d'unicité pourrait être renforcée."
            )
            print(
                "Vérifiez les logs et le rapport pour les détails des marqueurs d'authenticité."
            )
        else:
            print("\n[ERROR] AUTHENTICITE NON PROUVEE OU ECHEC DES TESTS")
            print(
                "Verifiez la configuration des cles API et les erreurs dans les logs."
            )

        return final_score >= 50

    except Exception as e:
        logger.error(f"Erreur test authenticité: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()
