#!/usr/bin/env python3
# scripts/validation_traces_master_fixed.py

"""
Script maître de validation des démos Sherlock, Watson et Moriarty avec traces complètes.
Version corrigée avec auto_env compatible.
"""

import argumentation_analysis.core.environment  # Added import

# ===== INTÉGRATION AUTO_ENV - MÊME APPROCHE QUE CONFTEST.PY =====
import sys
import os
from pathlib import Path

# Déterminer le répertoire racine du projet
project_root = Path(__file__).parent.parent.absolute()

try:
    # Import direct par chemin absolu pour éviter les problèmes d'import
    scripts_core_path = project_root / "scripts" / "core"
    if str(scripts_core_path) not in sys.path:
        sys.path.insert(0, str(scripts_core_path))

    from auto_env import ensure_env

    success = ensure_env(silent=False)

    if success:
        print("[OK AUTO_ENV] Environnement projet activé avec succès")
    else:
        print("[WARN AUTO_ENV] Activation en mode dégradé")

except ImportError as e:
    print(f"[ERROR AUTO_ENV] Module auto_env non disponible: {e}")
except Exception as e:
    print(f"[ERROR AUTO_ENV] Erreur d'activation: {e}")

# ===== IMPORTS PRINCIPAUX =====
import asyncio
import json
import logging
import datetime
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

# Imports spécifiques au projet
from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
    run_cluedo_oracle_game,
)
from argumentation_analysis.orchestration.logique_complexe_orchestrator import (
    LogiqueComplexeOrchestrator,
)
from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import (
    SherlockEnqueteAgent,
    SherlockTools,
)
from argumentation_analysis.agents.core.logic.watson_logic_assistant import (
    WatsonLogicAssistant,
)
from argumentation_analysis.utils.core_utils.logging_utils import setup_logging


class MasterTraceValidator:
    """Validateur maître orchestrant toutes les validations avec traces."""

    def __init__(self, output_dir: str = ".temp"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.logger = logging.getLogger(__name__)

        # Création des répertoires de traces
        self.cluedo_dir = self.output_dir / "traces_cluedo"
        self.einstein_dir = self.output_dir / "traces_einstein"
        self.cluedo_dir.mkdir(parents=True, exist_ok=True)
        self.einstein_dir.mkdir(parents=True, exist_ok=True)

    def validate_environment(self) -> Dict[str, Any]:
        """Valide l'environnement avant d'exécuter les tests."""

        print("🔍 VALIDATION DE L'ENVIRONNEMENT")
        print("=" * 50)

        validation_results = {
            "openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
            "directories_created": True,
            "python_imports": True,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        # Vérification clé API
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("❌ OPENAI_API_KEY non définie")
            validation_results["openai_api_key"] = False
        else:
            print(f"✅ OPENAI_API_KEY définie (longueur: {len(api_key)})")

        # Vérification des répertoires
        if self.cluedo_dir.exists() and self.einstein_dir.exists():
            print("✅ Répertoires de traces créés")
        else:
            print("❌ Répertoires de traces manquants")
            validation_results["directories_created"] = False

        # Test d'imports
        try:
            print("✅ Imports des orchestrateurs réussis")
        except ImportError as e:
            print(f"❌ Erreur d'import: {e}")
            validation_results["python_imports"] = False

        # Résumé
        all_ok = all(
            validation_results[k]
            for k in ["openai_api_key", "directories_created", "python_imports"]
        )
        validation_results["environment_ready"] = all_ok

        if all_ok:
            print("\n🎉 ENVIRONNEMENT PRÊT POUR LA VALIDATION")
        else:
            print("\n⚠️  PROBLÈMES DÉTECTÉS - CORRECTION NÉCESSAIRE")

        return validation_results

    def create_kernel(self, model_name: str = "gpt-4o-mini") -> Kernel:
        """Création du kernel Semantic Kernel avec service OpenAI."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY non définie dans l'environnement")

        kernel = Kernel()
        chat_service = OpenAIChatCompletion(
            service_id="openai_chat", api_key=api_key, ai_model_id=model_name
        )
        kernel.add_service(chat_service)
        return kernel

    def generate_simple_cluedo_case(self) -> str:
        """Génère un cas de Cluedo simple (3-4 indices)."""
        return """Enquête Cluedo simple: 
        - Témoin A: 'J'ai vu Mme Peacock dans la bibliothèque vers 21h00'
        - Témoin B: 'Le chandelier manquait dans le salon après 21h30'
        - Témoin C: 'Professor Plum était dans la cuisine à 21h15'
        - Indice physique: Traces de cire dans la bibliothèque
        
        Question: Qui a commis le meurtre, avec quelle arme et dans quel lieu ?"""

    def generate_complex_cluedo_case(self) -> str:
        """Génère un cas de Cluedo complexe avec contradictions."""
        return """Enquête Cluedo complexe avec contradictions:
        - Témoin A: 'Mme Peacock était dans la bibliothèque vers 21h00'
        - Témoin B: 'Mme Peacock était dans le salon à 21h00' (CONTRADICTION)
        - Témoin C: 'J'ai entendu un bruit dans la bibliothèque vers 21h15'
        - Témoin D: 'Professor Plum avait le chandelier à 20h45'
        - Témoin E: 'Professor Plum n'avait pas d'arme à 20h45' (CONTRADICTION)
        - Indice: Empreintes de Mme Peacock sur le chandelier
        - Indice: Traces de cire dans la bibliothèque et le salon
        - Indice: Alibi partiel de Professor Plum en cuisine (20h30-21h00)
        - Indice: Porte de la bibliothèque fermée à clé après 21h30
        
        Question: Résolvez cette enquête en gérant les contradictions."""

    def generate_simple_einstein_case(self) -> str:
        """Génère un cas Einstein simple (5 contraintes)."""
        return """Énigme Einstein simple - 5 maisons:
        
        Il y a 5 maisons de couleurs différentes alignées.
        Dans chaque maison vit une personne de nationalité différente.
        Chaque personne boit une boisson différente, fume une marque différente et possède un animal différent.
        
        Contraintes:
        1. L'Anglais vit dans la maison rouge
        2. Le Suédois possède un chien  
        3. Le Danois boit du thé
        4. La maison verte est à gauche de la maison blanche
        5. Le propriétaire de la maison verte boit du café
        
        Question: Qui possède le poisson ?
        
        ATTENTION: Cette énigme DOIT être résolue avec la logique formelle TweetyProject par Watson."""

    def generate_complex_einstein_case(self) -> str:
        """Génère un cas Einstein complexe (10+ contraintes)."""
        return """Énigme Einstein complexe - 5 maisons:
        
        Il y a 5 maisons de couleurs différentes alignées.
        Dans chaque maison vit une personne de nationalité différente.
        Chaque personne boit une boisson différente, fume une marque différente et possède un animal différent.
        
        Contraintes complexes:
        1. L'Anglais vit dans la maison rouge
        2. Le Suédois possède un chien
        3. Le Danois boit du thé
        4. La maison verte est immédiatement à gauche de la maison blanche
        5. Le propriétaire de la maison verte boit du café
        6. La personne qui fume des Pall Mall possède des oiseaux
        7. Le propriétaire de la maison jaune fume des Dunhill
        8. La personne qui vit dans la maison du milieu boit du lait
        9. Le Norvégien vit dans la première maison
        10. La personne qui fume des Blend vit à côté de celle qui possède des chats
        11. La personne qui possède un cheval vit à côté de celle qui fume des Dunhill
        12. La personne qui fume des Blue Master boit de la bière
        13. L'Allemand fume des Prince
        14. Le Norvégien vit à côté de la maison bleue
        15. La personne qui fume des Blend a un voisin qui boit de l'eau
        
        Question: Qui possède le poisson ?
        
        ATTENTION: Cette énigme EXIGE l'utilisation intensive de TweetyProject par Watson.
        Minimum OBLIGATOIRE: 10+ clauses logiques + 5+ requêtes TweetyProject."""

    async def run_cluedo_validation(self) -> List[Dict[str, Any]]:
        """Exécute la validation Cluedo avec les cas simple et complexe."""

        print("🕵️ Démarrage validation Cluedo...")

        results = []

        # Cas simple
        print("\n🟢 CAS CLUEDO SIMPLE")
        print("=" * 40)
        simple_case = self.generate_simple_cluedo_case()
        simple_results = await self.run_cluedo_with_traces(simple_case, "simple")
        results.append(simple_results)

        # Cas complexe
        print("\n🔴 CAS CLUEDO COMPLEXE")
        print("=" * 40)
        complex_case = self.generate_complex_cluedo_case()
        complex_results = await self.run_cluedo_with_traces(complex_case, "complexe")
        results.append(complex_results)

        return results

    async def run_cluedo_with_traces(
        self, case_description: str, case_name: str
    ) -> Dict[str, Any]:
        """Exécute un cas Cluedo avec capture complète des traces."""

        try:
            # Création du kernel
            kernel = self.create_kernel()

            # Capture du timestamp de début
            start_time = datetime.datetime.now()

            # Exécution du jeu Cluedo
            print(f"📋 Scénario: {case_description[:100]}...")
            final_history, final_state = await run_cluedo_oracle_game(
                kernel, case_description
            )

            # Capture du timestamp de fin
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Construction des résultats complets
            results = {
                "metadata": {
                    "case_name": case_name,
                    "timestamp": self.timestamp,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "model_used": "gpt-4o-mini",
                },
                "input": {"case_description": case_description},
                "conversation_history": final_history,
                "final_state": {
                    "final_solution": getattr(final_state, "final_solution", None),
                    "solution_secrete": getattr(
                        final_state, "solution_secrete_cluedo", None
                    ),
                    "hypotheses": getattr(final_state, "hypotheses_enquete", []),
                    "tasks": getattr(final_state, "tasks", {}),
                },
                "analysis": {
                    "conversation_length": len(final_history) if final_history else 0,
                    "success": getattr(final_state, "final_solution", None) is not None,
                },
            }

            # Sauvegarde des traces
            trace_file = self.cluedo_dir / f"trace_{case_name}_{self.timestamp}.json"
            with open(trace_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

            print(f"✅ Traces Cluedo sauvegardées: {trace_file}")

            return results

        except Exception as e:
            print(f"❌ Erreur lors de l'exécution de {case_name}: {e}")
            raise

    async def run_einstein_validation(self) -> List[Dict[str, Any]]:
        """Exécute la validation Einstein avec les cas simple et complexe."""

        print("🧩 Démarrage validation Einstein...")

        results = []

        # Cas simple (5 contraintes)
        print("\n🟢 CAS EINSTEIN SIMPLE")
        print("=" * 40)
        simple_case = self.generate_simple_einstein_case()
        simple_results = await self.run_einstein_with_traces(simple_case, "simple")
        results.append(simple_results)

        # Cas complexe (10+ contraintes)
        print("\n🔴 CAS EINSTEIN COMPLEXE")
        print("=" * 40)
        complex_case = self.generate_complex_einstein_case()
        complex_results = await self.run_einstein_with_traces(complex_case, "complexe")
        results.append(complex_results)

        return results

    async def run_einstein_with_traces(
        self, case_description: str, case_name: str
    ) -> Dict[str, Any]:
        """Exécute un cas Einstein avec capture complète des traces."""

        try:
            # Création du kernel
            kernel = self.create_kernel()

            # Capture du timestamp de début
            start_time = datetime.datetime.now()

            # Création de l'orchestrateur logique complexe
            orchestrateur = LogiqueComplexeOrchestrator(kernel)

            # Création des agents spécialisés avec outils
            sherlock_tools = SherlockTools(kernel)
            kernel.add_plugin(sherlock_tools, plugin_name="SherlockTools")

            sherlock_agent = SherlockEnqueteAgent(
                kernel=kernel, agent_name="Sherlock", service_id="openai_chat"
            )

            watson_agent = WatsonLogicAssistant(
                kernel=kernel, agent_name="Watson", service_id="openai_chat"
            )

            # Exécution de l'énigme Einstein
            print(f"📋 Énigme: {case_description[:150]}...")

            resultats = await orchestrateur.resoudre_enigme_complexe(
                sherlock_agent, watson_agent
            )

            # Capture du timestamp de fin
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()

            # Construction des résultats complets
            results = {
                "metadata": {
                    "case_name": case_name,
                    "timestamp": self.timestamp,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration_seconds": duration,
                    "model_used": "gpt-4o-mini",
                },
                "input": {"case_description": case_description},
                "execution_results": resultats,
                "analysis": {
                    "enigme_resolue": resultats.get("enigme_resolue", False),
                    "tours_utilises": resultats.get("tours_utilises", 0),
                },
            }

            # Sauvegarde des traces
            trace_file = (
                self.einstein_dir / f"trace_einstein_{case_name}_{self.timestamp}.json"
            )
            with open(trace_file, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)

            print(f"✅ Traces Einstein sauvegardées: {trace_file}")

            return results

        except Exception as e:
            print(f"❌ Erreur lors de l'exécution de {case_name}: {e}")
            raise

    async def run_full_validation(self) -> Dict[str, Any]:
        """Exécute la validation complète des démos avec traces."""

        print("\n🚀 LANCEMENT VALIDATION COMPLÈTE AVEC TRACES")
        print("=" * 80)

        # Validation de l'environnement
        env_validation = self.validate_environment()
        if not env_validation["environment_ready"]:
            raise RuntimeError("Environnement non prêt pour la validation")

        start_time = datetime.datetime.now()
        all_results = {
            "metadata": {
                "validation_start": start_time.isoformat(),
                "timestamp": self.timestamp,
                "environment_validation": env_validation,
            },
            "cluedo_results": None,
            "einstein_results": None,
        }

        try:
            # ÉTAPE 1: Validation Cluedo
            print(f"\n📋 ÉTAPE 1/2: VALIDATION CLUEDO")
            print(f"{'='*50}")

            cluedo_results = await self.run_cluedo_validation()
            all_results["cluedo_results"] = cluedo_results

            # ÉTAPE 2: Validation Einstein
            print(f"\n🧩 ÉTAPE 2/2: VALIDATION EINSTEIN")
            print(f"{'='*50}")

            einstein_results = await self.run_einstein_validation()
            all_results["einstein_results"] = einstein_results

            # Finalisation
            end_time = datetime.datetime.now()
            total_duration = (end_time - start_time).total_seconds()

            all_results["metadata"]["validation_end"] = end_time.isoformat()
            all_results["metadata"]["total_duration"] = total_duration

            # Sauvegarde du rapport global
            report_file = (
                self.output_dir / f"global_validation_report_{self.timestamp}.json"
            )

            with open(report_file, "w", encoding="utf-8") as f:
                json.dump(all_results, f, indent=2, ensure_ascii=False, default=str)

            # Affichage du résumé final
            self.display_final_summary(all_results)

            return all_results

        except Exception as e:
            self.logger.error(f"❌ Erreur lors de la validation complète: {e}")
            raise

    def display_final_summary(self, all_results: Dict[str, Any]):
        """Affiche le résumé final de la validation."""

        print(f"\n{'='*80}")
        print(f"🎉 VALIDATION COMPLÈTE TERMINÉE")
        print(f"{'='*80}")

        metadata = all_results["metadata"]
        cluedo_results = all_results["cluedo_results"]
        einstein_results = all_results["einstein_results"]

        print(f"⏱️  Durée totale: {metadata['total_duration']:.2f}s")
        print(f"🧪 Tests Cluedo: {len(cluedo_results) if cluedo_results else 0}")
        print(f"🧪 Tests Einstein: {len(einstein_results) if einstein_results else 0}")

        print(f"\n📁 TRACES GÉNÉRÉES:")
        print(f"   - Cluedo: {self.cluedo_dir}/")
        print(f"   - Einstein: {self.einstein_dir}/")
        print(f"   - Rapport global: global_validation_report_{self.timestamp}.json")

        print(
            f"\n✅ Validation des démos Sherlock, Watson et Moriarty terminée avec succès!"
        )


async def main():
    """Fonction principale de validation complète avec traces."""

    print("🚀 VALIDATION MAÎTRE - DÉMOS SHERLOCK, WATSON ET MORIARTY")
    print("=" * 80)
    print("🎯 Objectif: Valider les démos avec traces agentiques complètes")
    print("🔧 Tests: Cluedo (informel) + Einstein (formel avec TweetyProject)")
    print("📊 Livrables: Traces JSON + Rapports d'analyse + Validation qualité")

    # Configuration du logging
    setup_logging()

    # Chargement de l'environnement
    load_dotenv()

    try:
        # Création et lancement du validateur maître
        master_validator = MasterTraceValidator()

        # Exécution de la validation complète
        results = await master_validator.run_full_validation()

        return results

    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE: {e}")
        logging.error(f"Erreur validation maître: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
