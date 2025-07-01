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

from semantic_kernel.functions import KernelArguments
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# Map d'alias pour les sophismes, pour gérer les variations dans la réponse du LLM
ALIAS_MAP = {}

def compare_sophisms(analysis_result_dict, expected_sophisms):
    """Compare le résultat de l'analyse avec les sophismes attendus de manière flexible."""
    try:
        detected_sophisms_raw = analysis_result_dict.get("sophismes", [])
        if not detected_sophisms_raw:
            return False, "Aucun sophisme n'a été détecté dans la réponse de l'IA."
            
        detected_ids = []
        for item in detected_sophisms_raw:
            # Le modèle peut retourner 'fallacy_type' ou 'fallacy_name'
            name_raw = str(item.get('nom', '')).lower().strip()
            normalized_name = ALIAS_MAP.get(name_raw, name_raw)
            detected_ids.append(normalized_name)
        
        detected_set = set(detected_ids)
        expected_set = set(s.lower().strip() for s in expected_sophisms)
        
        success = expected_set.issubset(detected_set)
        details = f"Attendu: {sorted(list(expected_set))}, Détecté: {sorted(list(detected_set))}"
        return success, details
    except (AttributeError, TypeError, KeyError) as e:
        return False, f"Erreur lors de la comparaison des résultats: {e}. Réponse reçue: {analysis_result_dict}"

async def main():
    """Point d'entrée principal pour le script de débogage isolé."""
    print(f"{Colors.BOLD}--- Début du test de débogage pour 'Concept Volé' ---{Colors.ENDC}")

    scenario = {
        "text": "Reason is not reliable, therefore we cannot use it to find truth.",
        "expected_sophisms": ["stolen-concept"]
    }

    # Configuration du Kernel, du service LLM et du plugin d'analyse
    from argumentation_analysis.core.llm_service import create_llm_service
    from argumentation_analysis.agents.core.informal.informal_definitions import setup_informal_kernel, FallacyAnalysisResult
    from semantic_kernel.connectors.ai.open_ai.prompt_execution_settings.open_ai_prompt_execution_settings import OpenAIChatPromptExecutionSettings

    kernel = sk.Kernel()
    llm_service = create_llm_service(service_id="default", force_authentic=True)
    kernel.add_service(llm_service)
    
    # Utiliser la configuration standard de l'agent pour charger tous les prompts et plugins
    setup_informal_kernel(kernel, llm_service)
    analyze_function = kernel.plugins["InformalAnalyzer"]["semantic_AnalyzeFallacies"]

    success = False
    details = ""

    try:
        print(f"{Colors.YELLOW}Invoking semantic function 'analyze_argument_semantic'...{Colors.ENDC}")
        
        response = await kernel.invoke(
            analyze_function,
            KernelArguments(input=scenario["text"])
        )
        
        # La réponse est un ChatMessageContent contenant une chaîne JSON.
        # Nous devons la parser manuellement.
        content_str = str(response.value[0].content)

        # Nettoyage de la réponse pour extraire le JSON
        json_match = re.search(r"```json\n({.*?})\n```", content_str, re.DOTALL)
        if json_match:
            content_str = json_match.group(1)
            
        analysis_result_obj = FallacyAnalysisResult.model_validate_json(content_str)

        if not isinstance(analysis_result_obj, FallacyAnalysisResult):
            raise TypeError(f"La réponse n'est pas un objet FallacyAnalysisResult, mais {type(analysis_result_obj)}")

        analysis_result = json.loads(analysis_result_obj.model_dump_json())
        print(f"{Colors.GREEN}Résultat brut de l'analyse:{Colors.ENDC}\n{json.dumps(analysis_result, indent=2)}")
        
        success, details = compare_sophisms(analysis_result, scenario["expected_sophisms"])

    except Exception as e:
        import traceback
        details = f"Exception durant l'exécution: {e}\n{traceback.format_exc()}"
    
    # Affichage du résultat final
    print("\n--- Résultat Final ---")
    print(f"{Colors.YELLOW}Scénario testé:{Colors.ENDC} Appel à l'hypocrisie")
    print(f"{Colors.YELLOW}Détails:{Colors.ENDC} {details}")
    if success:
        print(f"{Colors.GREEN}{Colors.BOLD}[SUCCESS] Le test a réussi !{Colors.ENDC}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}[FAILED] Le test a échoué.{Colors.ENDC}")
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())