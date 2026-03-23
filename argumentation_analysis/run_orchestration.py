#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour lancer l'orchestration des agents d'analyse argumentative.

Ce script permet de lancer l'analyse argumentative depuis la racine du projet.
Il offre deux modes :

  - **Moderne (défaut)** : utilise UnifiedPipeline avec 17 workflows pré-construits
    (CapabilityRegistry + WorkflowDSL + state tracking).
  - **Legacy** : utilise l'ancien AnalysisRunner (--legacy flag).

Exemples :
    # Workflow standard (défaut) sur un fichier
    python argumentation_analysis/run_orchestration.py --file texte.txt

    # Workflow light sur du texte inline
    python argumentation_analysis/run_orchestration.py --text "Mon argument" --workflow light

    # Lister les workflows disponibles
    python argumentation_analysis/run_orchestration.py --list-workflows

    # Mode legacy (ancien pipeline)
    python argumentation_analysis/run_orchestration.py --file texte.txt --legacy
"""

import sys
import json
import asyncio
import argparse
import logging
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure .env is loaded BEFORE any other import that might need API keys
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# Ajouter le répertoire parent au chemin de recherche des modules
current_dir = Path(__file__).parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))


def setup_logging(verbose: bool = False) -> None:
    """Configuration du logging pour l'orchestration."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # Réduire la verbosité de certaines bibliothèques
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("semantic_kernel.connectors.ai").setLevel(logging.WARNING)

    # Garder le niveau choisi pour l'orchestration et les agents
    logging.getLogger("Orchestration").setLevel(level)

    logging.info("Logging configuré pour l'orchestration.")


def list_workflows() -> None:
    """Affiche les workflows disponibles dans le catalogue."""
    try:
        from argumentation_analysis.orchestration.unified_pipeline import (
            get_workflow_catalog,
        )

        catalog = get_workflow_catalog()
        print(f"\n{'='*60}")
        print(f" {len(catalog)} workflows disponibles")
        print(f"{'='*60}\n")
        for name, wf in sorted(catalog.items()):
            phase_count = len(wf.phases) if hasattr(wf, "phases") else "?"
            print(f"  {name:<25} ({phase_count} phases)")
        print(f"\n{'='*60}")
        print("  Usage: --workflow <nom>  (défaut: standard)")
        print(f"{'='*60}\n")
    except Exception as e:
        print(f"Erreur lors du chargement du catalogue: {e}")
        sys.exit(1)


async def setup_environment() -> Any:
    """Initialise l'environnement nécessaire pour l'orchestration.

    Charge les variables d'environnement, initialise la JVM et crée le service LLM.

    :return: L'instance du service LLM si la création est réussie, sinon None.
    :rtype: Any
    """
    logging.info(
        "Initialisation de l'environnement (chargement des settings implicite)..."
    )

    # Initialisation de la JVM
    from argumentation_analysis.core.jvm_setup import initialize_jvm

    logging.info("Initialisation de la JVM...")
    jvm_ready_status = initialize_jvm()

    if not jvm_ready_status:
        logging.warning(
            "JVM n'a pas pu être initialisée. Les agents logiques formels utiliseront les fallbacks Python."
        )

    # Création du Service LLM
    from argumentation_analysis.core.llm_service import create_llm_service

    logging.info("Création du service LLM...")
    try:
        llm_service = create_llm_service(service_id="orchestration_llm")
        logging.info(
            f"[OK] Service LLM créé avec succès (ID: {llm_service.service_id})."
        )
        return llm_service
    except Exception as e:
        logging.warning(f"Service LLM non disponible: {e}")
        return None


async def run_modern_analysis(
    text_content: str,
    workflow_name: str = "standard",
    output_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Exécute l'analyse via UnifiedPipeline (mode moderne).

    :param text_content: Le contenu textuel à analyser.
    :param workflow_name: Nom du workflow à utiliser.
    :param output_file: Chemin optionnel pour sauvegarder les résultats en JSON.
    :return: Résultats de l'analyse.
    """
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    logging.info(
        f"Lancement de l'analyse moderne (workflow={workflow_name}) "
        f"sur un texte de {len(text_content)} caractères..."
    )

    results = await run_unified_analysis(
        text=text_content,
        workflow_name=workflow_name,
    )

    # Afficher le résumé
    summary = results.get("summary", {})
    print(f"\n{'='*60}")
    print(f" Résultats — Workflow: {results.get('workflow_name', workflow_name)}")
    print(f"{'='*60}")
    print(f"  Phases complétées : {summary.get('completed', 0)}/{summary.get('total', 0)}")
    print(f"  Phases échouées   : {summary.get('failed', 0)}")
    print(f"  Phases sautées    : {summary.get('skipped', 0)}")

    # Afficher les capabilities utilisées
    caps_used = results.get("capabilities_used", [])
    if caps_used:
        print(f"\n  Capabilities utilisées ({len(caps_used)}):")
        for cap in caps_used:
            print(f"    - {cap}")

    caps_missing = results.get("capabilities_missing", [])
    if caps_missing:
        print(f"\n  Capabilities manquantes ({len(caps_missing)}):")
        for cap in caps_missing:
            print(f"    - {cap}")

    # Afficher l'état unifié si disponible
    state_snapshot = results.get("state_snapshot")
    if state_snapshot:
        non_empty = sum(
            1
            for v in state_snapshot.values()
            if v and v not in ([], {}, "", None, 0)
        )
        print(f"\n  État unifié : {non_empty} champs non-vides sur {len(state_snapshot)}")

    print(f"{'='*60}\n")

    # Sauvegarder en JSON si demandé
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        logging.info(f"Résultats sauvegardés dans {output_path}")

    return results


async def run_legacy_analysis(
    text_content: str,
    llm_service: Any,
) -> None:
    """Exécute l'analyse via l'ancien AnalysisRunner (mode legacy).

    :param text_content: Le contenu textuel à analyser.
    :param llm_service: L'instance du service LLM initialisée.
    """
    if not text_content or not llm_service:
        logging.error(
            "Orchestration impossible: texte vide ou service LLM non disponible."
        )
        return

    logging.info(
        f"Lancement de l'orchestration legacy sur un texte de {len(text_content)} caractères..."
    )

    try:
        from argumentation_analysis.orchestration.analysis_runner import run_analysis

        await run_analysis(text_content=text_content, llm_service=llm_service)

        logging.info("Orchestration legacy terminée avec succès.")
    except Exception as e:
        logging.error(f"Erreur lors de l'orchestration legacy: {e}", exc_info=True)


async def main():
    """Fonction principale du script."""
    parser = argparse.ArgumentParser(
        description="Orchestration des agents d'analyse argumentative",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  %(prog)s --file texte.txt                    # Workflow standard (défaut)
  %(prog)s --text "Mon argument" --workflow light  # Workflow light
  %(prog)s --file texte.txt --workflow collaborative  # Débat multi-agents
  %(prog)s --list-workflows                    # Lister les workflows
  %(prog)s --file texte.txt --output results.json  # Sauvegarder résultats
  %(prog)s --file texte.txt --legacy           # Mode legacy (AnalysisRunner)
        """,
    )

    # Groupe mutuellement exclusif pour les sources de texte
    text_source = parser.add_mutually_exclusive_group()
    text_source.add_argument(
        "--file", "-f", type=str, help="Chemin vers un fichier texte à analyser"
    )
    text_source.add_argument(
        "--text", "-t", type=str, help="Texte à analyser (directement en argument)"
    )
    text_source.add_argument(
        "--ui",
        "-u",
        action="store_true",
        help="Utiliser l'interface utilisateur pour sélectionner le texte",
    )

    # Options de workflow (mode moderne)
    parser.add_argument(
        "--workflow",
        "-w",
        type=str,
        default="standard",
        help="Workflow à utiliser (défaut: standard). Voir --list-workflows",
    )
    parser.add_argument(
        "--list-workflows",
        action="store_true",
        help="Lister les workflows disponibles et quitter",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Chemin pour sauvegarder les résultats en JSON",
    )

    # Options générales
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Utiliser l'ancien pipeline (AnalysisRunner) au lieu de UnifiedPipeline",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Afficher les logs détaillés"
    )

    args = parser.parse_args()

    # Configuration du logging
    setup_logging(args.verbose)

    # Action spéciale : lister les workflows
    if args.list_workflows:
        list_workflows()
        return

    # Vérifier qu'une source de texte est fournie
    if not args.file and not args.text and not args.ui:
        parser.error(
            "Vous devez spécifier une source de texte (--file, --text, ou --ui). "
            "Utilisez --list-workflows pour voir les workflows disponibles."
        )

    # Initialisation de l'environnement
    llm_service = await setup_environment()
    if not llm_service and args.legacy:
        logging.error("Service LLM requis pour le mode legacy.")
        return

    # Récupération du texte selon la source choisie
    text_content = None

    if args.file:
        try:
            file_path = Path(args.file)
            if not file_path.exists():
                logging.error(f"Le fichier {file_path} n'existe pas.")
                return

            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
            logging.info(
                f"Texte chargé depuis {file_path} ({len(text_content)} caractères)"
            )
        except Exception as e:
            logging.error(f"Erreur lors de la lecture du fichier: {e}")
            return

    elif args.text:
        text_content = args.text
        logging.info(
            f"Utilisation du texte fourni en argument ({len(text_content)} caractères)"
        )

    elif args.ui:
        from argumentation_analysis.ui.app import configure_analysis_task

        try:
            logging.info("Lancement de l'interface utilisateur...")
            text_content = configure_analysis_task()
            if not text_content:
                logging.warning("Aucun texte n'a été sélectionné via l'interface.")
                return
            logging.info(
                f"Texte sélectionné via l'interface ({len(text_content)} caractères)"
            )
        except Exception as e:
            logging.error(
                f"Erreur lors de l'utilisation de l'interface: {e}", exc_info=True
            )
            return

    if not text_content:
        logging.error("Aucun texte à analyser.")
        return

    # Exécution de l'analyse
    if args.legacy:
        await run_legacy_analysis(text_content, llm_service)
    else:
        await run_modern_analysis(
            text_content,
            workflow_name=args.workflow,
            output_file=args.output,
        )


if __name__ == "__main__":
    asyncio.run(main())
