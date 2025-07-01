#!/usr/bin/env python3
import sys
import os
import asyncio
import json
import re
from pathlib import Path

# --- BOOTSTRAP: Assurer que l'environnement est configuré ---
try:
    current_file_path = Path(__file__).resolve()
    project_root = next((p for p in current_file_path.parents if (p / "pyproject.toml").exists()), None)
    if project_root is None:
        raise FileNotFoundError("Impossible de localiser la racine du projet.")
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from argumentation_analysis.core.environment import ensure_env
    ensure_env()
except (NameError, FileNotFoundError, RuntimeError) as e:
    print(f"ERREUR CRITIQUE DE BOOTSTRAP: {e}", file=sys.stderr)
    sys.exit(1)
# --- FIN BOOTSTRAP ---

import semantic_kernel as sk

from semantic_kernel.contents import ChatHistory
from argumentation_analysis.agents.plugins.fallacy_workflow_plugin import FallacyWorkflowPlugin
from argumentation_analysis.agents.utils.taxonomy_utils import Taxonomy

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def compare_sophisms(analysis_result_str: str, expected_sophisms: list[str]):
    """Compare le résultat de l'analyse (chaîne JSON d'un appel d'outil) avec les sophismes attendus."""
    try:
        # La sortie attendue est maintenant un `tool_code` qui est une chaîne en format JSON.
        match = re.search(r"```json\s*(\{.*?\})\s*```", analysis_result_str, re.DOTALL)
        if not match:
            # Si le JSON n'est pas dans un bloc de code, on essaie de le parser directement.
            try:
                data = json.loads(analysis_result_str)
            except json.JSONDecodeError:
                return False, f"La réponse n'est pas un JSON valide et n'est pas dans un bloc de code. Reçu: {analysis_result_str}"
        else:
            data = json.loads(match.group(1))

        # Le LLM peut imbriquer la liste sous une clé, on la cherche.
        if 'fallacies' in data:
            detected_sophisms_raw = data.get("fallacies", [])
        else: # Si pas de clé `fallacies`, on suppose que la liste est à la racine
            detected_sophisms_raw = data if isinstance(data, list) else []

        if not detected_sophisms_raw:
             return False, "Aucun sophisme n'a été détecté dans le JSON de la réponse."

        detected_ids = {str(item.get('fallacy_type', '')).lower().strip() for item in detected_sophisms_raw}
        expected_set = {s.lower().strip() for s in expected_sophisms}

        success = expected_set.issubset(detected_ids)
        details = f"Attendu: {sorted(list(expected_set))}, Détecté: {sorted(list(detected_ids))}"
        return success, details
    except (json.JSONDecodeError, AttributeError, TypeError, KeyError) as e:
        return False, f"Erreur de parsing ou de comparaison: {e}. Réponse reçue: {analysis_result_str}"


async def main():
    """Point d'entrée principal pour le script de débogage isolé."""
    print(f"{Colors.BOLD}--- Début du test de débogage pour 'Concept Volé' avec le nouveau workflow ---{Colors.ENDC}")

    scenario = {
        "text": "Reason is not reliable, therefore we cannot use it to find truth.",
        "expected_sophisms": ["stolen-concept"]
    }

    from argumentation_analysis.core.llm_service import create_llm_service
    
    kernel = sk.Kernel()
    llm_service = create_llm_service(service_id="default", force_authentic=True)
    kernel.add_service(llm_service)
    
    workflow_plugin = FallacyWorkflowPlugin(kernel)
    
    success = False
    details = ""

    try:
        print(f"{Colors.YELLOW}Invoking 'run_workflow'...{Colors.ENDC}")
        
        final_result_str = await workflow_plugin.run_workflow(
            argument_text=scenario["text"]
        )
        
        print(f"{Colors.GREEN}Résultat brut du workflow:{Colors.ENDC}\n{final_result_str}")
        
        # Le résultat est maintenant une chaîne JSON, la fonction de comparaison est adaptée
        success, details = compare_sophisms(final_result_str, scenario["expected_sophisms"])

    except Exception as e:
        import traceback
        details = f"Exception durant l'exécution: {e}\n{traceback.format_exc()}"
    
    # Affichage du résultat final
    print("\n--- Résultat Final ---")
    print(f"{Colors.YELLOW}Scénario testé:{Colors.ENDC} Concept Volé (Stolen Concept)")
    print(f"{Colors.YELLOW}Détails:{Colors.ENDC} {details}")
    if success:
        print(f"{Colors.GREEN}{Colors.BOLD}[SUCCESS] Le test a réussi !{Colors.ENDC}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}[FAILED] Le test a échoué.{Colors.ENDC}")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())