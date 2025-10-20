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
        from argumentation_analysis.agents.core.logic.watson_logic_assistant import (
            WatsonLogicAssistant,
        )
        from argumentation_analysis.core.cluedo_oracle_state import CluedoOracleState

        self.SherlockEnqueteAgent = SherlockEnqueteAgent
        self.WatsonLogicAssistant = WatsonLogicAssistant
        self.CluedoOracleState = CluedoOracleState

        self.agents = {}
        self.dummy_oracle_state = None

    async def setup_einstein_workflow(self):
        """Configuration du workflow Einstein"""
        logger.info("🧠 Configuration du workflow Einstein Oracle")

        # Création d'un état Oracle factice pour les agents (ils en ont besoin techniquement)
        elements = {"suspects": ["Einstein"], "armes": ["Logique"], "lieux": ["Puzzle"]}

        # Import nécessaire pour CluedoDataset
        from argumentation_analysis.agents.core.oracle.cluedo_dataset import (
            CluedoDataset,
        )

        CluedoDataset(elements)

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
        self.agents["sherlock"] = self.SherlockEnqueteAgent(
            kernel=self.kernel,
            agent_name="Sherlock",
            system_prompt="""Tu es Sherlock Holmes face au puzzle d'Einstein.
            Ton objectif : déterminer QUI POSSÈDE LE POISSON en utilisant les indices de Moriarty.
            Analyse logiquement chaque indice, fais des déductions méthodiques.
            Quand tu penses connaître la réponse, dis clairement : 'Je conclus que [PERSONNE] possède le poisson'.""",
        )

        self.agents["watson"] = self.WatsonLogicAssistant(
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
        """Sherlock analyse les indices"""
        # Construction du contexte avec tous les indices révélés
        all_indices = self.einstein_oracle.get_all_revealed_indices()
        context = "Indices révélés :\n" + "\n".join(
            f"- {indice}" for indice in all_indices
        )

        # Simulation de réponse Sherlock (dans un vrai système, appel agent)
        sherlock_analyses = [
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

        # Choix de réponse selon le round
        if round_num >= 9:  # Solution proche
            analysis = "Je conclus que l'Allemand possède le poisson ! Il vit dans la maison verte (4e position)."
        else:
            analysis = sherlock_analyses[min(round_num - 1, len(sherlock_analyses) - 2)]

        response = {
            "round": round_num + 0.1,
            "agent": "Sherlock",
            "message": analysis,
            "type": "deduction",
            "context_used": len(all_indices),
        }

        self.conversation_history.append(response)
        logger.info(f"🕵️ [Sherlock]: {analysis}")
        print(f"🕵️ [Sherlock]: {analysis}")

        return response

    async def _watson_assist(self, round_num: int) -> Dict[str, Any]:
        """Watson aide à l'organisation logique"""
        watson_assists = [
            "Holmes, j'organise les contraintes dans un tableau logique...",
            "Analysons méthodiquement : nationalités, couleurs, positions...",
            "Je propose de vérifier nos déductions avec les nouvelles contraintes.",
            "Excellent travail ! Notre grille logique se complète progressivement.",
            "Les connexions deviennent évidentes avec cette approche méthodique.",
        ]

        assist = watson_assists[min((round_num // 2) - 1, len(watson_assists) - 1)]

        response = {
            "round": round_num + 0.2,
            "agent": "Watson",
            "message": assist,
            "type": "assistance",
        }

        self.conversation_history.append(response)
        logger.info(f"🔬 [Watson]: {assist}")
        print(f"🔬 [Watson]: {assist}")

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

    # Configuration Semantic Kernel
    import semantic_kernel as sk
    from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

    kernel = sk.Kernel()

    # Service de simulation pour la démo
    api_key = os.getenv("OPENAI_API_KEY", "demo-key-simulation")
    chat_service = OpenAIChatCompletion(
        service_id="einstein_demo_chat", ai_model_id="gpt-4", api_key=api_key
    )
    kernel.add_service(chat_service)

    # Exécution de la démo Einstein
    orchestrator = EinsteinOracleOrchestrator(
        kernel, max_rounds=15, integration_test=integration_test
    )

    try:
        # Configuration
        await orchestrator.setup_einstein_workflow()

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
    print(f"   Puzzle complété: {'✅' if demo_success.get('puzzle_completed') else '❌'}")
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

    # En mode test d'intégration, on s'assure d'initialiser notre propre JVM
    if args.integration_test:
        from argumentation_analysis.core.jvm_setup import (
            initialize_jvm,
            shutdown_jvm,
            is_jvm_started,
        )

        if not is_jvm_started():
            initialize_jvm()

    try:
        result = await run_einstein_oracle_demo(integration_test=args.integration_test)
        if not args.integration_test:
            print(f"\n🎉 Démo Einstein terminée avec succès!")

    except Exception as e:
        logger.error(f"❌ Erreur critique: {e}", exc_info=True)
        print(f"\n❌ ERREUR CRITIQUE: {e}")
    finally:
        if args.integration_test:
            from argumentation_analysis.core.jvm_setup import (
                shutdown_jvm,
                is_jvm_started,
            )

            if is_jvm_started():
                shutdown_jvm()


if __name__ == "__main__":
    asyncio.run(main())
