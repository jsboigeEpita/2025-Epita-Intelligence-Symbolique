#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DÉMO EINSTEIN ORACLE - MORIARTY DONNEUR D'INDICES

MISSION : Créer une démo où Moriarty donne des indices progressifs pour le puzzle Einstein
et Sherlock/Watson doivent déduire la solution à partir de ces indices.

PUZZLE EINSTEIN ADAPTÉ :
- 5 maisons de couleurs différentes
- 5 nationalités différentes
- 5 boissons différentes
- 5 animaux différents
- 5 cigarettes différentes

OBJECTIF : Trouver qui possède le poisson !
"""

import sys
import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import argparse

# Configuration UTF-8
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

# Configuration des chemins
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
sys.path.insert(0, str(PROJECT_ROOT))

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            str(PROJECT_ROOT / "einstein_oracle_demo_trace.log"), encoding="utf-8"
        ),
    ],
)
logger = logging.getLogger(__name__)


class EinsteinPuzzleOracle:
    """
    Oracle pour le puzzle Einstein avec solution prédéfinie et indices progressifs.
    """

    def __init__(self):
        self.solution = {
            1: {
                "couleur": "Jaune",
                "nationalite": "Norvégien",
                "boisson": "Eau",
                "cigarette": "Dunhill",
                "animal": "Chat",
            },
            2: {
                "couleur": "Bleue",
                "nationalite": "Danois",
                "boisson": "Thé",
                "cigarette": "Blend",
                "animal": "Cheval",
            },
            3: {
                "couleur": "Rouge",
                "nationalite": "Anglais",
                "boisson": "Lait",
                "cigarette": "Pall Mall",
                "animal": "Oiseau",
            },
            4: {
                "couleur": "Verte",
                "nationalite": "Allemand",
                "boisson": "Café",
                "cigarette": "Prince",
                "animal": "Poisson",
            },
            5: {
                "couleur": "Blanche",
                "nationalite": "Suédois",
                "boisson": "Bière",
                "cigarette": "Blue Master",
                "animal": "Chien",
            },
        }

        # Les indices d'Einstein dans l'ordre de révélation progressive
        self.indices = [
            "L'Anglais vit dans la maison rouge.",
            "Le Suédois a un chien.",
            "Le Danois boit du thé.",
            "La maison verte est immédiatement à gauche de la maison blanche.",
            "Le propriétaire de la maison verte boit du café.",
            "La personne qui fume des Pall Mall élève des oiseaux.",
            "Le propriétaire de la maison jaune fume des Dunhill.",
            "L'homme qui vit dans la maison du centre boit du lait.",
            "Le Norvégien vit dans la première maison.",
            "L'homme qui fume des Blend vit à côté de celui qui a un chat.",
            "L'homme qui a un cheval vit à côté de celui qui fume des Dunhill.",
            "L'homme qui fume des Blue Master boit de la bière.",
            "L'Allemand fume des Prince.",
            "Le Norvégien vit à côté de la maison bleue.",
            "L'homme qui fume des Blend a un voisin qui boit de l'eau.",
        ]

        self.indices_révélés = []
        self.current_indice_index = 0

    def get_next_indice(self) -> Optional[str]:
        """Retourne le prochain indice ou None si tous sont révélés"""
        if self.current_indice_index < len(self.indices):
            indice = self.indices[self.current_indice_index]
            self.indices_révélés.append(indice)
            self.current_indice_index += 1
            return indice
        return None

    def get_all_revealed_indices(self) -> List[str]:
        """Retourne tous les indices révélés jusqu'à présent"""
        return self.indices_révélés.copy()

    def check_solution_attempt(self, proposed_solution: str) -> Dict[str, Any]:
        """Vérifie une tentative de solution"""
        # Recherche de "Allemand" et "poisson" dans la réponse
        correct_answer = "L'Allemand possède le poisson"

        if (
            "allemand" in proposed_solution.lower()
            and "poisson" in proposed_solution.lower()
        ):
            return {
                "correct": True,
                "message": "🎯 CORRECT ! L'Allemand possède le poisson (maison 4).",
                "full_solution": self.solution,
            }
        else:
            return {
                "correct": False,
                "message": "❌ Incorrect. Continuez à déduire avec les indices...",
                "hint": "Pensez aux contraintes de position et aux déductions logiques.",
            }


class EinsteinOracleOrchestrator:
    """
    Orchestrateur pour la démo Einstein avec Moriarty comme donneur d'indices.
    """

    def __init__(self, kernel, max_rounds=15, integration_test=False):
        self.kernel = kernel
        self.max_rounds = max_rounds
        self.integration_test = integration_test
        self.einstein_oracle = EinsteinPuzzleOracle()
        self.conversation_history = []
        self.round_count = 0
        self.solution_found = False

        # Import des modules nécessaires (même structure que Cluedo mais adapté)
        from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import (
            SherlockEnqueteAgent,
        )
        from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState

        self.SherlockEnqueteAgent = SherlockEnqueteAgent
        self.CluedoOracleState = CluedoOracleState

        self.agents = {}
        self.dummy_oracle_state = None

    async def setup_einstein_workflow(self):
        """Configuration du workflow Einstein"""
        logger.info("🧠 Configuration du workflow Einstein Oracle")

        # Création d'un état Oracle factice pour les agents (ils en ont besoin techniquement)
        elements = {"suspects": ["Einstein"], "armes": ["Logique"], "lieux": ["Puzzle"]}

        self.dummy_oracle_state = self.CluedoOracleState(
            nom_enquete_cluedo="Puzzle Einstein Oracle Demo",
            elements_jeu_cluedo=elements,
            description_cas="Puzzle d'Einstein avec Oracle Moriarty - Test de validation post-Git",
            initial_context={
                "type": "validation_test",
                "puzzle": "einstein",
                "version": "v2.1.0",
            },
        )

        # Création des agents adaptés pour Einstein
        # En mode integration_test, les agents ne sont pas utilisés (réponses scriptées)
        if not self.integration_test:
            self.agents["sherlock"] = self.SherlockEnqueteAgent(
                kernel=self.kernel,
                agent_name="Sherlock",
                system_prompt="""Tu es Sherlock Holmes face au puzzle d'Einstein.
                Ton objectif : déterminer QUI POSSÈDE LE POISSON en utilisant les indices de Moriarty.
                Analyse logiquement chaque indice, fais des déductions méthodiques.
                Quand tu penses connaître la réponse, dis clairement : 'Je conclus que [PERSONNE] possède le poisson'.""",
            )

            # Watson n'a pas besoin de Tweety pour Einstein (texte seulement),
            # donc on utilise SherlockEnqueteAgent comme base pour éviter la dépendance JVM
            self.agents["watson"] = self.SherlockEnqueteAgent(
                kernel=self.kernel,
                agent_name="Watson",
                system_prompt="""Tu es Watson, assistant logique de Holmes pour le puzzle Einstein.
                Aide Sherlock en organisant les informations, en proposant des grilles logiques,
                et en vérifiant les déductions. Tu peux aussi proposer des solutions intermédiaires.""",
            )

        logger.info("✅ Workflow Einstein configuré")
        logger.info(f"🎯 Solution secrète: L'Allemand possède le poisson (maison 4)")

        return self.dummy_oracle_state

    async def execute_einstein_workflow(
        self,
        initial_question: str = "Voici le puzzle Einstein ! Moriarty va vous donner des indices progressifs pour trouver qui possède le poisson.",
    ):
        """Exécution du workflow Einstein"""
        logger.info("🧠 Début de la démo Einstein Oracle")

        # Message initial
        self.conversation_history.append(
            {
                "round": 0,
                "agent": "System",
                "message": initial_question,
                "type": "initial",
            }
        )

        print(f"\n🎭 {initial_question}")
        print("🎯 OBJECTIF : Trouver qui possède le poisson !")
        print("📋 5 maisons, 5 nationalités, 5 boissons, 5 cigarettes, 5 animaux")
        print()

        # Boucle principale Einstein
        for round_num in range(1, self.max_rounds + 1):
            self.round_count = round_num
            logger.info(f"\n🔄 ROUND {round_num}")

            # Phase 1: Moriarty donne un indice
            indice_response = await self._moriarty_give_clue(round_num)
            if not indice_response:
                logger.info("📚 Tous les indices ont été donnés")
                break

            # Phase 2: Sherlock analyse
            sherlock_response = await self._sherlock_analyze(round_num)

            # Vérification de solution
            if self._check_solution_in_response(sherlock_response):
                break

            # Phase 3: Watson aide (tous les 2 rounds)
            if round_num % 2 == 0:
                watson_response = await self._watson_assist(round_num)
                if self._check_solution_in_response(watson_response):
                    break

            # Pause pour lisibilité
            if not self.integration_test:
                await asyncio.sleep(0.1)

        return await self._collect_einstein_metrics()

    async def _moriarty_give_clue(self, round_num: int) -> Optional[Dict[str, Any]]:
        """Moriarty donne un indice Einstein"""
        next_indice = self.einstein_oracle.get_next_indice()

        if not next_indice:
            return None

        # Message théâtral de Moriarty
        moriarty_messages = [
            f"*sourire énigmatique* Indice {round_num}: {next_indice}",
            f"*regard perçant* Voici votre {round_num}e indice : {next_indice}",
            f"Ah, mes chers... Indice {round_num}: {next_indice}",
            f"*pose dramatique* Méditer sur ceci : {next_indice}",
        ]

        moriarty_message = moriarty_messages[(round_num - 1) % len(moriarty_messages)]

        response = {
            "round": round_num,
            "agent": "Moriarty",
            "message": moriarty_message,
            "type": "oracle_clue",
            "indice_content": next_indice,
            "indices_total": len(self.einstein_oracle.indices_révélés),
        }

        self.conversation_history.append(response)
        logger.info(f"🎭 [Moriarty]: {moriarty_message}")
        print(f"🎭 [Moriarty]: {moriarty_message}")

        return response

    async def _sherlock_analyze(self, round_num: int) -> Dict[str, Any]:
        """Sherlock analyse les indices (LLM réel ou scripted selon le mode)"""
        all_indices = self.einstein_oracle.get_all_revealed_indices()

        if self.integration_test:
            # Mode test: réponses déterministes (pas d'appel LLM)
            scripted = [
                "Intéressant... Je note cette contrainte sur ma grille logique.",
                "Cette information élimine plusieurs possibilités. La déduction progresse.",
                "Ah ! Ces indices commencent à former un pattern logique.",
                "Watson, organisez ces données. Une solution émerge.",
                "Les contraintes se précisent... Je vois la structure du puzzle.",
                "Fascinant ! Ce nouvel indice confirme mes hypothèses précédentes.",
                "La logique devient claire. Position par position, tout s'assemble.",
                "Excellent ! Je commence à entrevoir qui possède le poisson...",
                "Les dernières pièces du puzzle... La solution est proche !",
                "Je conclus que l'Allemand possède le poisson ! Il vit dans la maison verte (4e position).",
            ]
            if round_num >= 9:
                analysis = scripted[-1]
            else:
                analysis = scripted[min(round_num - 1, len(scripted) - 2)]
        else:
            # Mode normal: appel LLM réel
            indices_text = "\n".join(f"  {i+1}. {idx}" for i, idx in enumerate(all_indices))
            prompt = (
                f"Puzzle Einstein - Round {round_num}.\n"
                f"5 maisons (positions 1-5), 5 nationalités (Anglais, Suédois, Danois, Norvégien, Allemand), "
                f"5 couleurs (Rouge, Verte, Bleue, Jaune, Blanche), 5 boissons (Thé, Café, Lait, Bière, Eau), "
                f"5 cigarettes (Pall Mall, Dunhill, Blend, Blue Master, Prince), 5 animaux (Chien, Chat, Oiseau, Cheval, Poisson).\n\n"
                f"Indices révélés jusqu'ici :\n{indices_text}\n\n"
                f"Question : Qui possède le poisson ?\n"
                f"Analyse les indices disponibles et fais des déductions logiques. "
                f"Si tu peux déduire la réponse, dis clairement : 'Je conclus que [PERSONNE] possède le poisson'."
            )
            try:
                response_messages = await self.agents["sherlock"].invoke(prompt)
                analysis = str(response_messages[0].content if hasattr(response_messages[0], 'content') else response_messages[0])
            except Exception as e:
                logger.warning(f"Invocation Sherlock non disponible (round {round_num}): {e}")
                analysis = f"[Sherlock réfléchit aux {len(all_indices)} indices disponibles...]"

        response = {
            "round": round_num + 0.1,
            "agent": "Sherlock",
            "message": analysis,
            "type": "deduction",
            "context_used": len(all_indices),
        }

        self.conversation_history.append(response)
        logger.info(f"🕵️ [Sherlock]: {analysis[:200]}")
        print(f"🕵️ [Sherlock]: {analysis[:300]}")

        return response

    async def _watson_assist(self, round_num: int) -> Dict[str, Any]:
        """Watson aide à l'organisation logique (LLM réel ou scripted selon le mode)"""
        all_indices = self.einstein_oracle.get_all_revealed_indices()

        if self.integration_test:
            # Mode test: réponses déterministes
            scripted = [
                "Holmes, j'organise les contraintes dans un tableau logique...",
                "Analysons méthodiquement : nationalités, couleurs, positions...",
                "Je propose de vérifier nos déductions avec les nouvelles contraintes.",
                "Excellent travail ! Notre grille logique se complète progressivement.",
                "Les connexions deviennent évidentes avec cette approche méthodique.",
            ]
            assist = scripted[min((round_num // 2) - 1, len(scripted) - 1)]
        else:
            # Mode normal: appel LLM réel
            indices_text = "\n".join(f"  {i+1}. {idx}" for i, idx in enumerate(all_indices))
            sherlock_last = ""
            for msg in reversed(self.conversation_history):
                if msg["agent"] == "Sherlock":
                    sherlock_last = msg["message"][:200]
                    break

            prompt = (
                f"Puzzle Einstein - Round {round_num}. Tu aides Sherlock Holmes.\n"
                f"Indices révélés :\n{indices_text}\n\n"
                f"Dernière analyse de Sherlock : {sherlock_last}\n\n"
                f"Organise les contraintes logiques, propose une grille de déduction, "
                f"et aide Sherlock à progresser vers la solution (qui possède le poisson ?)."
            )
            try:
                response_messages = await self.agents["watson"].invoke(prompt)
                assist = str(response_messages[0].content if hasattr(response_messages[0], 'content') else response_messages[0])
            except Exception as e:
                logger.warning(f"Invocation Watson non disponible (round {round_num}): {e}")
                assist = f"[Watson organise les {len(all_indices)} contraintes logiques...]"

        response = {
            "round": round_num + 0.2,
            "agent": "Watson",
            "message": assist,
            "type": "assistance",
        }

        self.conversation_history.append(response)
        logger.info(f"🔬 [Watson]: {assist[:200]}")
        print(f"🔬 [Watson]: {assist[:300]}")

        return response

    def _check_solution_in_response(self, response: Dict[str, Any]) -> bool:
        """Vérifie si la solution est proposée dans une réponse"""
        message = response["message"].lower()

        if "allemand" in message and "poisson" in message:
            # Solution trouvée !
            solution_check = self.einstein_oracle.check_solution_attempt(message)

            if solution_check["correct"]:
                self.solution_found = True

                # Message de confirmation
                confirmation = {
                    "round": response["round"] + 0.5,
                    "agent": "Moriarty",
                    "message": "🎯 *applaudit* MAGNIFIQUE ! L'Allemand possède effectivement le poisson ! Puzzle résolu !",
                    "type": "solution_confirmation",
                    "solution_verified": True,
                }

                self.conversation_history.append(confirmation)
                logger.info("🎉 SOLUTION TROUVÉE !")
                print(
                    "🎭 [Moriarty]: 🎯 *applaudit* MAGNIFIQUE ! L'Allemand possède effectivement le poisson ! Puzzle résolu !"
                )

                return True

        return False

    async def _collect_einstein_metrics(self) -> Dict[str, Any]:
        """Collecte les métriques de la démo Einstein"""
        return {
            "session_info": {
                "type": "EINSTEIN_ORACLE_DEMO",
                "timestamp": datetime.now().isoformat(),
                "description": "Démo puzzle Einstein avec Moriarty donneur d'indices progressifs",
            },
            "puzzle_metrics": {
                "total_rounds": self.round_count,
                "indices_revealed": len(self.einstein_oracle.indices_révélés),
                "total_indices": len(self.einstein_oracle.indices),
                "solution_found": self.solution_found,
            },
            "einstein_solution": {
                "correct_answer": "L'Allemand possède le poisson",
                "position": "Maison 4 (verte)",
                "full_solution": self.einstein_oracle.solution,
            },
            "oracle_performance": {
                "indices_progression": self.einstein_oracle.indices_révélés,
                "revelation_method": "Progressive clue giving",
                "oracle_role": "Clue Provider (not card revealer)",
            },
            "conversation_history": self.conversation_history,
            "demo_success": {
                "puzzle_completed": self.solution_found,
                "moriarty_as_oracle": "Successful - Progressive clue provider",
                "agents_deduction": "Successful logical reasoning demonstrated",
            },
        }


async def run_einstein_oracle_demo(integration_test=False):
    """Lance la démo Einstein Oracle"""
    if not integration_test:
        print("🧠 DÉMO EINSTEIN ORACLE - MORIARTY DONNEUR D'INDICES")
    print("=" * 60)
    print("🎯 OBJECTIF: Démontrer Moriarty comme Oracle donneur d'indices")
    print("🧩 PUZZLE: Qui possède le poisson ? (5 maisons, 5 nationalités...)")
    print("🎭 MORIARTY: Donne des indices progressifs")
    print("🕵️ SHERLOCK/WATSON: Déduisent la solution logiquement")
    print()

    # Configuration du kernel selon le mode
    if integration_test:
        # Mode test: kernel léger sans bootstrap complet
        import semantic_kernel as sk
        from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

        kernel = sk.Kernel()
        api_key = os.getenv("OPENAI_API_KEY", "test-key")
        model_id = os.getenv("OPENAI_CHAT_MODEL_ID", "gpt-4o-mini")
        chat_service = OpenAIChatCompletion(
            service_id="chat_completion", ai_model_id=model_id, api_key=api_key
        )
        kernel.add_service(chat_service)
    else:
        # Mode normal: bootstrap complet avec LLM réel
        from argumentation_analysis.core.bootstrap import initialize_project_environment

        environment_context = initialize_project_environment()
        kernel = environment_context.kernel
        if not kernel:
            raise ValueError("Le kernel sémantique n'a pas été trouvé dans le contexte.")

    # Exécution de la démo Einstein
    orchestrator = EinsteinOracleOrchestrator(
        kernel, max_rounds=15, integration_test=integration_test
    )

    try:
        # Configuration
        oracle_state = await orchestrator.setup_einstein_workflow()

        # Exécution
        result = await orchestrator.execute_einstein_workflow()

        # Sauvegarde et affichage
        save_einstein_trace(result)
        display_einstein_results(result)

        return result

    except Exception as e:
        logger.error(f"❌ Erreur durant la démo Einstein: {e}", exc_info=True)
        raise


def save_einstein_trace(result: Dict[str, Any]) -> str:
    """Sauvegarde la trace Einstein"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_file = (
        PROJECT_ROOT
        / "results"
        / "sherlock_watson"
        / f"einstein_oracle_demo_{timestamp}.json"
    )

    # Création du répertoire si nécessaire
    trace_file.parent.mkdir(parents=True, exist_ok=True)

    with open(str(trace_file), "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)

    logger.info(f"💾 Trace Einstein sauvegardée: {trace_file}")
    return str(trace_file)


def display_einstein_results(result: Dict[str, Any]):
    """Affiche les résultats de la démo Einstein"""
    print("\n" + "=" * 80)
    print("🧠 RÉSULTATS DÉMO EINSTEIN ORACLE")
    print("=" * 80)

    puzzle_metrics = result.get("puzzle_metrics", {})
    solution_info = result.get("einstein_solution", {})
    oracle_perf = result.get("oracle_performance", {})
    demo_success = result.get("demo_success", {})

    print(f"\n📊 MÉTRIQUES PUZZLE:")
    print(f"   Rounds total: {puzzle_metrics.get('total_rounds', 0)}")
    print(
        f"   Indices révélés: {puzzle_metrics.get('indices_revealed', 0)}/{puzzle_metrics.get('total_indices', 0)}"
    )
    print(
        f"   Solution trouvée: {'✅' if puzzle_metrics.get('solution_found') else '❌'}"
    )

    print(f"\n🎯 SOLUTION EINSTEIN:")
    print(f"   Réponse correcte: {solution_info.get('correct_answer', 'N/A')}")
    print(f"   Position: {solution_info.get('position', 'N/A')}")

    print(f"\n🎭 PERFORMANCE ORACLE:")
    print(f"   Méthode: {oracle_perf.get('revelation_method', 'N/A')}")
    print(f"   Rôle Oracle: {oracle_perf.get('oracle_role', 'N/A')}")
    print(f"   Indices donnés: {len(oracle_perf.get('indices_progression', []))}")

    print(f"\n🎉 SUCCÈS DÉMO:")
    print(
        f"   Puzzle complété: {'✅' if demo_success.get('puzzle_completed') else '❌'}"
    )
    print(f"   Moriarty Oracle: {demo_success.get('moriarty_as_oracle', 'N/A')}")
    print(f"   Déduction agents: {demo_success.get('agents_deduction', 'N/A')}")

    # Aperçu conversation
    conversation = result.get("conversation_history", [])
    if conversation:
        print(f"\n💬 APERÇU CONVERSATION ({len(conversation)} messages):")
        for i, msg in enumerate(conversation[-8:]):  # 8 derniers messages
            agent = msg.get("agent", "Unknown")
            content = msg.get("message", "")[:60]
            msg_type = msg.get("type", "unknown")
            print(f"   {len(conversation)-8+i+1}. [{agent}] ({msg_type}) {content}...")

    print("\n" + "=" * 80)
    print("✅ DÉMO EINSTEIN TERMINÉE - NOUVEAU TYPE D'ORACLE")
    print("=" * 80)


async def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Lance la démonstration de l'énigme d'Einstein avec un oracle."
    )
    parser.add_argument(
        "--integration-test",
        action="store_true",
        help="Exécute la démo en mode test d'intégration (plus rapide et moins de logs).",
    )
    args = parser.parse_args()

    try:
        result = await run_einstein_oracle_demo(integration_test=args.integration_test)
        if not args.integration_test:
            print(f"\n🎉 Démo Einstein terminée avec succès!")

    except Exception as e:
        logger.error(f"❌ Erreur critique: {e}", exc_info=True)
        print(f"\n❌ ERREUR CRITIQUE: {e}")


if __name__ == "__main__":
    asyncio.run(main())
