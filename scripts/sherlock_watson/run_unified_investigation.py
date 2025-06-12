# ===== AUTO-ACTIVATION ENVIRONNEMENT =====
import scripts.core.auto_env
# =========================================
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT UNIFIÉ D'INVESTIGATION SHERLOCK-WATSON
==============================================

Ce script centralise et remplace les multiples scripts de démonstration 
Sherlock/Watson en un seul outil paramétrable.

Il intègre les logiques de :
- Workflows multiples (Cluedo, Einstein, JTMS)
- Modes d'exécution (normal, robuste)
- Désactivation optionnelle de dépendances (Java/JPype, Tweety)

Exemples d'utilisation :
-----------------------
# Lancer le workflow Cluedo en mode normal
python scripts/sherlock_watson/run_unified_investigation.py --workflow cluedo

# Lancer le workflow Einstein en mode robuste, sans le pont Tweety
python scripts/sherlock_watson/run_unified_investigation.py --workflow einstein --mode robust --no-tweety

# Lancer le workflow JTMS sans dépendance Java
python scripts/sherlock_watson/run_unified_investigation.py --workflow jtms --no-java
"""

import argparse
import asyncio
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

# --- Configuration initiale du chemin et de l'environnement ---
# Assurer que la racine du projet est dans sys.path pour les imports absolus
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Auto-activation de l'environnement et chargement des variables .env
import scripts.core.auto_env

# --- Configuration du logging ---
def setup_logging(session_id: str, workflow: str, level=logging.DEBUG):
    """Configure le logging racine pour la session."""
    log_dir = _PROJECT_ROOT / "logs" / "unified_investigation"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{session_id}_{workflow}.log"

    # S'assure de ne configurer qu'une fois
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_file, encoding='utf-8')
            ]
        )
    logging.getLogger().setLevel(level)
    # Appliquer le niveau à tous les handlers existants
    for handler in logging.getLogger().handlers:
        handler.setLevel(level)

    return logging.getLogger("UnifiedInvestigation")

logger = logging.getLogger(__name__) # Logger temporaire jusqu'à la configuration

# --- Vérification des dépendances optionnelles ---
try:
    import jpype
    import jpype.imports
    JPYPE_AVAILABLE = True
except ImportError:
    JPYPE_AVAILABLE = False

try:
    from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
    TWEETY_AVAILABLE = True
except ImportError:
    TWEETY_AVAILABLE = False


class UnifiedInvestigationEngine:
    """
    Moteur pour l'orchestration unifiée des investigations Sherlock-Watson.
    """

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.kernel = None
        self.results_dir = _PROJECT_ROOT / "results" / "unified_investigation" / self.session_id
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # La configuration du logging est maintenant globale
        setup_logging(self.session_id, self.args.workflow, level=logging.DEBUG)
        global logger
        logger = logging.getLogger("UnifiedInvestigation")
        
        logger.info(f"🚀 Initialisation du moteur d'investigation unifié (Session: {self.session_id})")
        logger.info(f"   - Workflow: {self.args.workflow}")
        logger.info(f"   - Mode: {self.args.mode}")
        logger.info(f"   - Java (JPype): {'Activé' if not self.args.no_java else 'Désactivé'}")
        logger.info(f"   - Tweety: {'Activé' if not self.args.no_tweety else 'Désactivé'}")

    async def initialize_system(self):
        """Initialise le système, y compris Semantic Kernel et les ponts optionnels."""
        logger.info("🔧 Initialisation du système...")

        # --- Gestion des dépendances optionnelles ---
        if self.args.no_java:
            logger.info("🚩 Flag --no-java: Désactivation de la logique basée sur Java.")
            os.environ['DISABLE_JAVA_LOGIC'] = '1'
        elif not JPYPE_AVAILABLE:
            logger.warning("🟡 JPype n'est pas installé. La logique Java sera désactivée.")
            os.environ['DISABLE_JAVA_LOGIC'] = '1'

        if self.args.no_tweety:
            logger.info("🚩 Flag --no-tweety: Désactivation du pont Tweety.")
            os.environ['NO_TWEETY_BRIDGE'] = '1'
        elif not TWEETY_AVAILABLE:
            logger.warning("🟡 Le pont Tweety n'est pas disponible. Passage en mode fallback.")
            os.environ['NO_TWEETY_BRIDGE'] = '1'

        # --- Initialisation de Semantic Kernel ---
        try:
            from semantic_kernel import Kernel
            from semantic_kernel.connectors.ai.open_ai import OpenAIChatCompletion

            self.kernel = Kernel()
            api_key = os.getenv("OPENAI_API_KEY")
            model_id = os.getenv("OPENAI_CHAT_MODEL_ID", "gpt-4o-mini")

            if not api_key or "simulation" in api_key:
                logger.error("❌ Clé API OpenAI réelle est requise.")
                return False
            
            main_service = OpenAIChatCompletion(
                service_id="chat_completion",
                api_key=api_key,
                ai_model_id=model_id,
            )
            self.kernel.add_service(main_service)
            logger.info(f"✅ Semantic Kernel initialisé avec le modèle {model_id}.")
            return True

        except ImportError:
            logger.error("❌ Semantic Kernel n'est pas installé. Impossible de continuer.")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'initialisation de Semantic Kernel: {e}")
            return False

    async def run(self):
        """Lance le workflow d'investigation sélectionné."""
        if not await self.initialize_system():
            return

        workflow_map = {
            'cluedo': self.run_cluedo_workflow,
            'einstein': self.run_einstein_workflow,
            'jtms': self.run_jtms_workflow,
        }

        workflow_func = workflow_map.get(self.args.workflow)
        if not workflow_func:
            logger.error(f"❌ Workflow '{self.args.workflow}' non reconnu.")
            return

        logger.info(f"🎬 Lancement du workflow: {self.args.workflow.upper()}")
        
        try:
            result = await workflow_func()
            result_file_path = await self.save_results(result)
            logger.info(f"✅ Workflow {self.args.workflow.upper()} terminé avec succès.")
            # Affiche le contenu du JSON final dans les logs
            if result_file_path:
                try:
                    with open(result_file_path, 'r', encoding='utf-8') as f:
                        final_content = json.load(f)
                    logger.info(f"CONTENU FINAL:\n{json.dumps(final_content, indent=2, ensure_ascii=False)}")
                except Exception as json_error:
                    logger.error(f"Erreur lors de la lecture du JSON final: {json_error}")
        except Exception as e:
            logger.error(f"❌ Erreur critique durant le workflow {self.args.workflow}: {e}", exc_info=True)
            if self.args.mode == 'robust':
                logger.info("MODE ROBUSTE: Tentative de sauvegarde des données partielles.")
                await self.save_results({"status": "failed", "error": str(e)})

    async def run_cluedo_workflow(self) -> Dict[str, Any]:
        """Exécute le workflow d'investigation Cluedo."""
        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import run_cluedo_oracle_game
        
        initial_question = "Enquête Cluedo: un meurtre a été commis. Découvrez le coupable, l'arme et le lieu."
        
        logger.info("🎮 Démarrage de l'enquête Cluedo...")
        cluedo_result = await run_cluedo_oracle_game(self.kernel, initial_question)
        
        return {
            "workflow": "cluedo",
            "status": "completed",
            "result_summary": cluedo_result.get("solution_analysis", {}),
            "full_results": cluedo_result
        }

    async def run_einstein_workflow(self) -> Dict[str, Any]:
        """Exécute le workflow de résolution de l'énigme d'Einstein."""
        from argumentation_analysis.orchestration.logique_complexe_orchestrator import LogiqueComplexeOrchestrator
        from argumentation_analysis.agents.core.pm.sherlock_enquete_agent import SherlockEnqueteAgent
        from argumentation_analysis.agents.core.logic.watson_logic_assistant import WatsonLogicAssistant
        
        orchestrateur = LogiqueComplexeOrchestrator(self.kernel)
        sherlock_agent = SherlockEnqueteAgent(kernel=self.kernel)
        watson_agent = WatsonLogicAssistant(kernel=self.kernel, use_tweety_bridge=(not self.args.no_tweety))

        logger.info("🧩 Démarrage de la résolution de l'énigme d'Einstein...")
        resultats = await orchestrateur.resoudre_enigme_complexe(sherlock_agent, watson_agent)

        return {
            "workflow": "einstein",
            "status": "completed",
            "enigme_resolue": resultats.get('enigme_resolue', False),
            "tours": resultats.get('tours_utilises', 0),
            "full_results": resultats
        }

    async def run_jtms_workflow(self) -> Dict[str, Any]:
        """Exécute une investigation collaborative basée sur JTMS."""
        from argumentation_analysis.agents.jtms_communication_hub import create_sherlock_watson_communication, run_investigation_session

        logger.info("🧠 Démarrage de l'investigation collaborative JTMS...")

        sherlock, watson, hub = await create_sherlock_watson_communication(
            self.kernel, use_tweety=not self.args.no_tweety
        )

        investigation_context = {
            "type": "jtms_murder_case",
            "description": "Meurtre mystérieux à résoudre avec raisonnement traçable."
        }
        
        session_results = await run_investigation_session(sherlock, watson, hub, investigation_context)

        return {
            "workflow": "jtms",
            "status": "completed",
            "success": session_results.get("success", False),
            "final_solution": session_results.get("final_solution", {}),
            "full_results": session_results
        }

    async def save_results(self, result_data: Dict[str, Any]) -> Optional[Path]:
        """Sauvegarde les résultats et retourne le chemin du fichier."""
        result_file = self.results_dir / f"result_{self.args.workflow}_{self.session_id}.json"
        logger.info(f"💾 Sauvegarde des résultats dans {result_file}")
        
        try:
            # Ajout des métadonnées de la session
            full_data = {
                "session_metadata": {
                    "session_id": self.session_id,
                    "timestamp": datetime.now().isoformat(),
                    "workflow": self.args.workflow,
                    "mode": self.args.mode,
                    "no_java": self.args.no_java,
                    "no_tweety": self.args.no_tweety,
                },
                "execution_result": result_data
            }
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(full_data, f, indent=2, ensure_ascii=False, default=str)
            return result_file
        except Exception as e:
            logger.error(f"❌ Impossible de sauvegarder les résultats: {e}")
            return None

def parse_arguments():
    """Définit et parse les arguments de la ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Script unifié pour les investigations Sherlock-Watson.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    parser.add_argument(
        '--workflow',
        type=str,
        required=True,
        choices=['cluedo', 'einstein', 'jtms'],
        help="Le type de workflow d'investigation à lancer."
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        default='normal',
        choices=['normal', 'robust'],
        help=(
            "Mode d'exécution:\n"
            "  - normal: exécution standard.\n"
            "  - robust: avec gestion d'erreurs avancée et tentatives de re-exécution."
        )
    )

    parser.add_argument(
        '--no-java',
        action='store_true',
        help="Désactive l'utilisation de JPype et de la logique basée sur Java."
    )

    parser.add_argument(
        '--no-tweety',
        action='store_true',
        help="Désactive l'utilisation du pont Tweety pour la logique formelle."
    )

    return parser.parse_args()

async def main():
    """Point d'entrée principal du script."""
    args = parse_arguments()
    engine = UnifiedInvestigationEngine(args)
    await engine.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⏹️ Exécution interrompue par l'utilisateur.")
    except Exception as general_error:
        logger.critical(f"❌ Une erreur non gérée est survenue: {general_error}", exc_info=True)
        sys.exit(1)