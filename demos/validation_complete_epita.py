#!/usr/bin/env python3
import sys
import os
import codecs
from pathlib import Path

# --- DÉBUT DU COUPE-CIRCUIT D'ENVIRONNEMENT ---
# Ce bloc garantit que le script s'exécute dans le bon contexte, même s'il est appelé directement.
try:
    # Détecter la racine du projet de manière robuste
    current_file_path = Path(__file__).resolve()
    project_root = current_file_path.parent.parent

    # Vérifier si la détection est correcte en cherchant un marqueur de projet
    if not (project_root / "argumentation_analysis").exists() or not (project_root / "pyproject.toml").exists():
        # Si le script est déplacé, remonter jusqu'à trouver la racine
        project_root = next((p for p in current_file_path.parents if (p / "pyproject.toml").exists()), None)
        if project_root is None:
            raise FileNotFoundError("Impossible de localiser la racine du projet. Assurez-vous que 'pyproject.toml' est présent.")

    # Ajouter la racine au sys.path si elle n'y est pas déjà
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Maintenant, l'appel explicite du vérificateur d'environnement est effectué
    from argumentation_analysis.core.environment import ensure_env
    ensure_env()

except (NameError, FileNotFoundError, RuntimeError) as e:
    print(f"ERREUR CRITIQUE DE BOOTSTRAP : Impossible de configurer l'environnement du projet.", file=sys.stderr)
    print(f"Détails: {e}", file=sys.stderr)
    print(f"Veuillez exécuter ce script via le wrapper 'activate_project_env.ps1'.", file=sys.stderr)
    sys.exit(1)
# --- FIN DU COUPE-CIRCUIT D'ENVIRONNEMENT ---

import asyncio
import csv
import sys
import os
import json
import time
import subprocess
import argparse
import random
import re
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

import semantic_kernel as sk
from argumentation_analysis.agents.agent_factory import AgentFactory
from config.unified_config import AgentType
from argumentation_analysis.agents.utils.taxonomy_navigator import TaxonomyNavigator
from argumentation_analysis.core.llm_service import create_llm_service
from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.function_call_content import FunctionCallContent
from semantic_kernel.contents.function_result_content import FunctionResultContent


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if not (PROJECT_ROOT / "examples" / "scripts_demonstration").exists():
    PROJECT_ROOT = Path(__file__).resolve().parent.parent
    if not (PROJECT_ROOT / "examples").exists():
        PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_DEMO_DIR = PROJECT_ROOT / "examples" / "scripts_demonstration"
DEMOS_DIR = PROJECT_ROOT / "demos"
ARGUMENTATION_DIR = PROJECT_ROOT / "argumentation_analysis"

class ValidationMode(Enum):
    BASIC = "basic"
    STANDARD = "standard"
    ADVANCED = "advanced"
    EXHAUSTIVE = "exhaustive"

class ComplexityLevel(Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    RESEARCH = "research"

class AnalysisLevel(Enum):
   LEXICAL = "lexical"
   SEMANTIC = "semantic"
   HYBRID = "hybrid"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

class ValidationEpitaComplete:
    def __init__(self, mode: ValidationMode = ValidationMode.EXHAUSTIVE,
                 complexity: ComplexityLevel = ComplexityLevel.COMPLEX,
                 level: AnalysisLevel = AnalysisLevel.SEMANTIC,
                 agent_type: str = "full",
                 enable_synthetic: bool = False,
                 taxonomy_file_path: Optional[str] = None,
                 trace_log_path: Optional[str] = None,
                 dialogue_text: Optional[str] = None,
                 file_path: Optional[str] = None,
                 integration_test: bool = False):
        self.mode = mode
        self.complexity = complexity
        self.level = level
        self.agent_type = agent_type
        self.enable_synthetic = enable_synthetic
        self.taxonomy_file_path = taxonomy_file_path
        self.trace_log_path = trace_log_path
        self.dialogue_text = dialogue_text
        self.file_path = file_path
        self.integration_test = integration_test
        self.results = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "mode": mode.value,
                "complexity": complexity.value,
                "analysis_level": level.value,
                "agent_type": agent_type,
                "synthetic_enabled": enable_synthetic,
                "taxonomy_file": taxonomy_file_path,
                "trace_log_path": trace_log_path,
                "integration_test_mode": integration_test,
                "version": "3.0_factory_and_validation_fix"
            },
            "components": {},
            "score": 0, "max_score": 0, "certification": "PENDING",
            "performance_metrics": {}, "authenticity_scores": {}
        }
        self._setup_environment()
        if "argumentation_analysis.core.environment" in sys.modules:
            print(f"{Colors.GREEN}[OK] [SETUP] Module auto_env est bien chargé.{Colors.ENDC}")
        else:
            print(f"{Colors.WARNING}[WARN] [SETUP] Le module auto_env n'a pas été pré-chargé.{Colors.ENDC}")

    INTEGRATION_TEST_CASES = [
        {"test_name": "Question Piège", "dialogue": "As-tu arrêté de manipuler les chiffres ?", "expected_fallacy_id": "179", "expected_fallacy_name": "Question piège"},
        {"test_name": "Pente Savonneuse", "dialogue": "Si on autorise les trottinettes, demain ce sera les motos.", "expected_fallacy_id": "987", "expected_fallacy_name": "Pente savonneuse"},
        {"test_name": "Argument par le Scénario", "dialogue": "Il a acheté une pelle. Son voisin a disparu. C'est évident.", "expected_fallacy_id": "61", "expected_fallacy_name": "Argument par le scénario"},
        {"test_name": "Homme de Paille", "dialogue": "Les écolos veulent nous faire revenir à l'âge de pierre.", "expected_fallacy_id": "944", "expected_fallacy_name": "Homme de paille"},
    ]

    def _setup_environment(self):
        print(f"{Colors.CYAN}[SETUP] Configuration de l'environnement...{Colors.ENDC}")
        paths_to_add = [str(p) for p in [PROJECT_ROOT, PROJECT_ROOT / "argumentation_analysis", PROJECT_ROOT / "examples", PROJECT_ROOT / "scripts", PROJECT_ROOT / "tests", PROJECT_ROOT / "demos"]]
        for path in paths_to_add:
            if path not in sys.path:
                sys.path.insert(0, path)
        os.environ['PYTHONPATH'] = os.pathsep.join(paths_to_add + [os.environ.get('PYTHONPATH', '')])
        print(f"{Colors.GREEN}[OK] Environnement configuré avec {len(paths_to_add)} chemins{Colors.ENDC}")

    def log_test(self, component: str, test: str, status: str, details: str = "", execution_time: float = 0.0, authenticity_score: float = 0.0):
        if component not in self.results["components"]:
            self.results["components"][component] = {"tests": [], "score": 0, "status": "PENDING", "total_execution_time": 0.0, "average_authenticity": 0.0}
        test_result = {"name": test, "status": status, "details": details, "timestamp": datetime.now().isoformat(), "execution_time": execution_time, "authenticity_score": authenticity_score}
        self.results["components"][component]["tests"].append(test_result)
        self.results["components"][component]["total_execution_time"] += execution_time
        auth_scores = [t.get("authenticity_score", 0) for t in self.results["components"][component]["tests"]]
        self.results["components"][component]["average_authenticity"] = sum(auth_scores) / len(auth_scores) if auth_scores else 0
        color = {"SUCCESS": Colors.GREEN, "WARNING": Colors.WARNING, "FAILED": Colors.FAIL, "PARTIAL": Colors.CYAN}.get(status, Colors.ENDC)
        print(f"{color}[{status}]{Colors.ENDC} {component} - {test}")
        if details: print(f"     [INFO] {details}")

    def _load_taxonomy_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Charge les données de la taxonomie à partir d'un fichier CSV."""
        if not file_path or not Path(file_path).exists():
            logging.error(f"Fichier de taxonomie non trouvé ou chemin non spécifié : {file_path}")
            return []
        try:
            # Utiliser codecs.open pour une meilleure gestion des encodages si nécessaire
            with codecs.open(file_path, 'r', 'utf-8') as infile:
                reader = csv.DictReader(infile)
                return list(reader)
        except Exception as e:
            logging.error(f"Erreur lors du chargement ou du parsing du fichier de taxonomie '{file_path}': {e}", exc_info=True)
            return []

    async def validate_informal_analysis_scenarios(self) -> bool:
        print(f"\n{Colors.BOLD}VALIDATION DE L'ANALYSE INFORMELLE (AGENT: {self.agent_type.upper()}){Colors.ENDC}")
        trace_dir = PROJECT_ROOT / "_temp" / "validation_traces"
        trace_dir.mkdir(exist_ok=True, parents=True)

        if self.integration_test:
            logging.info("Lancement des tests d'intégration...")
            scenarios = {case["test_name"]: {"text": case["dialogue"], "expected_sophisms": [case["expected_fallacy_name"]], "expected_id": case["expected_fallacy_id"]} for case in self.INTEGRATION_TEST_CASES}
            if self.agent_type != 'explore_only':
                logging.warning("Le mode intégration nécessite 'explore_only'. Forçage du type.")
                self.agent_type = 'explore_only'
        else:
            scenarios = {"Ad Hominem": {"text": "C'est un idiot, donc il a tort.", "expected_sophisms": ["ad-hominem"]}}

        taxonomy_data = self._load_taxonomy_data(self.taxonomy_file_path)
        if not taxonomy_data:
            self.log_test("Configuration", "Chargement de la Taxonomie", "FAILED", f"Impossible de charger les données depuis {self.taxonomy_file_path}.")
            return False
        
        taxonomy_navigator = TaxonomyNavigator(taxonomy_data)
        overall_success = True

        for test_name, config in scenarios.items():
            kernel = sk.Kernel()
            kernel.add_service(create_llm_service(service_id="default", force_authentic=True))
            agent_factory = AgentFactory(kernel, "default")
            start_time = time.time()
            safe_test_name = re.sub(r'[\s\(\)]+', '_', test_name).lower()
            
            try:
                informal_agent = agent_factory.create_informal_fallacy_agent(
                    config_name=self.agent_type,
                    trace_log_path=str(trace_dir / f"{safe_test_name}.log"),
                    taxonomy_data=taxonomy_data,
                )
                
                chat_history = ChatHistory()
                chat_history.add_user_message(config["text"])
                final_answer, max_turns = "", 10

                for i in range(max_turns):
                    logging.info(f"--- Tour {i+1}/{max_turns} pour '{test_name}' ---")
                    
                    # Invocation de l'agent
                    response_stream = informal_agent.invoke(history=chat_history)
                    
                    # Traitement de la réponse
                    full_response_content = ""
                    tool_calls = []
                    async for message in response_stream:
                        if isinstance(message, FunctionCallContent):
                            tool_calls.append(message)
                        elif hasattr(message, 'content') and message.content:
                            full_response_content += str(message.content)

                    # Si l'agent répond avec du texte, on l'ajoute à l'historique
                    if full_response_content:
                        logging.info(f"Réponse textuelle de l'agent: {full_response_content[:200]}...")
                        chat_history.add_assistant_message(full_response_content)

                    # S'il n'y a pas d'appel d'outil, la conversation de l'agent est terminée pour ce tour
                    if not tool_calls:
                        final_answer = full_response_content
                        logging.info("L'agent a terminé, pas d'appel d'outil. Réponse finale extraite.")
                        break

                    # S'il y a des appels d'outils, on les exécute
                    logging.info(f"{len(tool_calls)} appel(s) d'outil(s) détecté(s).")
                    for tool_call in tool_calls:
                        # Le nom de la fonction dans le prompt est 'get_branch_as_str'
                        # mais l'agent peut encore appeler 'explore_branch' par habitude de l'entraînement
                        if tool_call.function_name in ["get_branch_as_str", "explore_branch"]:
                            logging.info(f"  - Exécution: {tool_call.function_name}({tool_call.arguments})")
                            try:
                                tool_args = json.loads(tool_call.arguments)
                                node_id = tool_args.get("node_id", "1")
                                tool_result = taxonomy_navigator.get_branch_as_str(node_id)
                            except (json.JSONDecodeError, TypeError) as e:
                                tool_result = f"Erreur de parsing des arguments : {e}"
                                logging.error(tool_result)
                        else:
                            tool_result = f"Outil inconnu '{tool_call.function_name}'."
                            logging.warning(tool_result)
                        
                        # Ajout du résultat de l'outil à l'historique pour le prochain tour
                        chat_history.add_tool_message(FunctionResultContent(tool_call_id=tool_call.id, content=tool_result))
                
                else: # Si la boucle for se termine (max_turns atteint)
                    final_answer = "TIMEOUT"
                    logging.warning(f"Test '{test_name}' a atteint le nombre maximum de tours.")

                expected_sophism = config["expected_sophisms"][0].lower()
                # La réponse finale est maintenant la dernière chose dite par l'assistant
                last_assistant_message = ""
                for msg in reversed(chat_history.messages):
                    if msg.role == "assistant":
                        last_assistant_message = msg.content
                        break
                
                success = expected_sophism in last_assistant_message.lower()
                details = f"Attendu: '{expected_sophism}', Obtenu: '{last_assistant_message.strip()}'"
                self.log_test("Analyse Informelle", test_name, "SUCCESS" if success else "FAILED", details, time.time() - start_time, 0.9 if success else 0.1)
                if not success: overall_success = False
            except Exception as e:
                logging.error(f"Exception inattendue pour le test '{test_name}'", exc_info=True)
                self.log_test("Analyse Informelle", test_name, "FAILED", f"Exception: {e}", time.time() - start_time, 0.0)
                overall_success = False
        return overall_success

    async def run_complete_validation(self) -> Dict[str, Any]:
        if self.integration_test or self.dialogue_text:
            await self.validate_informal_analysis_scenarios()
        else:
            logging.error("Mode de validation non spécifié ou non supporté pour exécution directe.")
        return self.results

    async def shutdown(self):
        logging.info("Arrêt des services.")

def main():
    parser = argparse.ArgumentParser(description="Validation Complète EPITA")
    parser.add_argument('--mode', type=str, default='exhaustive', choices=[e.value for e in ValidationMode])
    parser.add_argument('--complexity', type=str, default='complex', choices=[e.value for e in ComplexityLevel])
    parser.add_argument('--level', type=str, default='semantic', choices=[e.value for e in AnalysisLevel])
    parser.add_argument('--agent-type', type=str, default='workflow_only', choices=['simple', 'explore_only', 'workflow_only'])
    parser.add_argument('--taxonomy', type=str, default='argumentation_analysis/data/argumentum_fallacies_taxonomy.csv')
    parser.add_argument('--verbose', action='store_true')
    parser.add_argument('--integration-test', action='store_true')
    parser.add_argument('--dialogue-text', type=str, default=None)
    parser.add_argument('--activate-env', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', stream=sys.stdout)
    
    if args.activate_env:
        cmd = [ "powershell", "-File", str(PROJECT_ROOT / "activate_project_env.ps1"), "-CommandToRun", f"python {' '.join(sys.argv)}"]
        subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
        return

    print(f"{Colors.BOLD}{'='*80}\n   VALIDATION COMPLETE DEMO EPITA - V2.8\n{'='*80}{Colors.ENDC}")
    validator = None
    success = False
    try:
        validator = ValidationEpitaComplete(
            mode=ValidationMode(args.mode),
            complexity=ComplexityLevel(args.complexity),
            level=AnalysisLevel(args.level),
            agent_type=args.agent_type,
            taxonomy_file_path=args.taxonomy,
            dialogue_text=args.dialogue_text,
            integration_test=args.integration_test
        )
        print(f"{Colors.GREEN}[OK] Validateur initialisé.{Colors.ENDC}")
        results = asyncio.run(validator.run_complete_validation())
        
        # Simple check for now
        comp = results.get("components", {}).get("Analyse Informelle", {})
        tests = comp.get("tests", [])
        if all(t.get("status") == "SUCCESS" for t in tests if tests):
            success = True

    except Exception as e:
        logging.critical("ERREUR CRITIQUE PENDANT LA VALIDATION", exc_info=True)
        success = False
    finally:
        if validator:
            logging.info("Nettoyage...")
            asyncio.run(validator.shutdown())
    
    return success

if __name__ == "__main__":
    if main():
        logging.info("Validation terminée avec succès.")
        sys.exit(0)
    else:
        logging.error("Validation terminée avec des erreurs.")
        sys.exit(1)