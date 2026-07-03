#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour lancer l'orchestration des agents d'analyse argumentative.

Ce script permet de lancer l'analyse argumentative depuis la racine du projet.
Il offre plusieurs modes d'orchestration :

  - **Pipeline (défaut)** : utilise UnifiedPipeline avec 17 workflows pré-construits
    (CapabilityRegistry + WorkflowDSL + state tracking).
  - **Conversational** : agents dialoguent via AgentGroupChat.
  - **Hierarchical** : StrategicManager → Lego WorkflowExecutor.
  - **Sherlock Modern** : investigation multi-agent.

Exemples :
    # Workflow standard (défaut) sur un fichier
    python argumentation_analysis/run_orchestration.py --file texte.txt

    # Workflow light sur du texte inline
    python argumentation_analysis/run_orchestration.py --text "Mon argument" --workflow light

    # Lister les workflows disponibles
    python argumentation_analysis/run_orchestration.py --list-workflows

    # Mode conversationnel
    python argumentation_analysis/run_orchestration.py --text "Mon argument" --mode conversational
"""

import sys
from pathlib import Path

# Bootstrap sys.path BEFORE any ``argumentation_analysis.*`` import (#883, #1336).
# When executed as ``python argumentation_analysis/run_orchestration.py``,
# sys.path[0] is the script directory (argumentation_analysis/), so the
# ``argumentation_analysis`` package itself is unresolvable until the project
# root is added. This MUST precede the dll_guard import below, otherwise the
# bare-subprocess invocation (no PYTHONPATH, no editable install — the CI
# condition) fails at the first line with ModuleNotFoundError. This is the
# root cause the test_run_orchestration subprocess tests assert against.
current_dir = Path(__file__).parent
project_root = current_dir.parent
if str(current_dir) not in sys.path:
    sys.path.append(str(current_dir))
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

import argumentation_analysis.core.dll_guard  # noqa: F401 — must load before jpype (#1019)

import json
import asyncio
import argparse
import logging
from typing import Any, Dict, Optional

# Ensure .env is loaded BEFORE any other import that might need API keys
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


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
    rich_output: bool = False,
    fallacy_tier: str = "llm",
    shield_preset: str = "off",
    vote_method: str = "copeland",
    consensus_threshold: float = 0.7,
    fol_solver: str = "eprover",
    counter_strategy: str = "auto",
    formal_extension: str = "all",
) -> Dict[str, Any]:
    """Exécute l'analyse via UnifiedPipeline (mode moderne).

    :param text_content: Le contenu textuel à analyser.
    :param workflow_name: Nom du workflow à utiliser.
    :param output_file: Chemin optionnel pour sauvegarder les résultats en JSON.
    :param fallacy_tier: Fallacy detection depth (taxonomy/hybrid/llm/full).
    :param shield_preset: AI Shield preset (off/basic/advanced/output_only/strict).
    :param vote_method: Social choice voting method for governance phase.
    :param consensus_threshold: Consensus threshold (0.0-1.0) for deliberation.
    :param fol_solver: FOL solver backend (tweety/prover9/eprover).
    :param counter_strategy: Counter-argument rhetorical strategy (auto/socratic/reductio/analogy/authority/statistical).
    :param formal_extension: Formal extension filter (all/core/none/csv list of 17 handlers).
    :return: Résultats de l'analyse.
    """
    from argumentation_analysis.orchestration.unified_pipeline import (
        run_unified_analysis,
    )

    logging.info(
        f"Lancement de l'analyse moderne (workflow={workflow_name}) "
        f"sur un texte de {len(text_content)} caractères..."
    )

    # Build context with parametric selectors
    context: Dict[str, Any] = {"fallacy_tier": fallacy_tier}
    if shield_preset != "off":
        context["shield_config"] = {
            "preset": shield_preset,
            "fail_open": shield_preset != "strict",
        }
    if vote_method != "copeland":
        context["vote_method"] = vote_method
    if consensus_threshold != 0.7:
        context["consensus_threshold"] = consensus_threshold
    if fol_solver != "eprover":
        context["fol_solver"] = fol_solver
    if counter_strategy != "auto":
        context["counter_strategy"] = counter_strategy
    if formal_extension != "all":
        context["formal_extension_filter"] = formal_extension

    results = await run_unified_analysis(
        text=text_content,
        workflow_name=workflow_name,
        context=context,
    )

    # Afficher le résumé
    summary = results.get("summary", {})
    print(f"\n{'='*60}")
    print(f" Résultats — Workflow: {results.get('workflow_name', workflow_name)}")
    print(f"{'='*60}")
    print(
        f"  Phases complétées : {summary.get('completed', 0)}/{summary.get('total', 0)}"
    )
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
            1 for v in state_snapshot.values() if v and v not in ([], {}, "", None, 0)
        )
        print(
            f"\n  État unifié : {non_empty} champs non-vides sur {len(state_snapshot)}"
        )

    print(f"{'='*60}\n")

    # Rich output formatting
    if rich_output:
        try:
            from argumentation_analysis.cli.output_formatter import (
                render_spectacular_result,
            )

            render_spectacular_result(results)
        except ImportError:
            logging.warning("Module output_formatter non disponible")

    # Sauvegarder en JSON si demandé
    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        logging.info(f"Résultats sauvegardés dans {output_path}")

    return results


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
  %(prog)s --file texte.txt --workflow formal_extended  # Full formal chain
  %(prog)s --list-workflows                    # Lister les workflows
  %(prog)s --file texte.txt --output results.json  # Sauvegarder résultats
  %(prog)s --text "Mon argument" --mode conversational  # Mode conversationnel (agents dialoguent)
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
    parser.add_argument(
        "--rich-output",
        action="store_true",
        help="Afficher les résultats avec le formatage Rich (sections colorées, cross-refs)",
    )

    # Mode d'orchestration
    parser.add_argument(
        "--mode",
        "-m",
        type=str,
        choices=[
            "pipeline",
            "conversational",
            "hierarchical",
            "cluedo",
            "sherlock_modern",
        ],
        default="pipeline",
        help="Mode d'orchestration: pipeline (séquentiel, défaut), "
        "conversational (agents dialoguent via AgentGroupChat), "
        "hierarchical (strategic planning → Lego execution), "
        "cluedo (investigation Sherlock-Watson-Oracle, #914), "
        "sherlock_modern (investigation multi-agent, #357)",
    )
    parser.add_argument(
        "--hierarchical-mode",
        type=str,
        choices=["bridge", "delegation"],
        default="bridge",
        help="Sub-mode for --mode hierarchical (RA-10 #1069): "
        "bridge (M2, default — strategic objectives → Lego/DAG execution), "
        "delegation (M3 — true strategic→tactical→operational 3-tier delegation, "
        "fails loud on a degraded chain instead of hardcoded fallback).",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Afficher les logs détaillés"
    )
    parser.add_argument(
        "--extraction-turns",
        type=int,
        default=7,
        help="Max turns for Extraction & Detection phase (default: 7)",
    )
    parser.add_argument(
        "--formal-turns",
        type=int,
        default=5,
        help="Max turns for Formal Analysis & Quality phase (default: 5)",
    )
    parser.add_argument(
        "--synthesis-turns",
        type=int,
        default=10,
        help="Max turns for Synthesis & Debate phase (default: 10)",
    )
    parser.add_argument(
        "--reanalysis-turns",
        type=int,
        default=5,
        help="Max turns for Re-Analysis phase if triggered (default: 5)",
    )

    # Parametric integration selectors (north-star R311)
    parser.add_argument(
        "--fallacy-tier",
        type=str,
        choices=["taxonomy", "hybrid", "llm", "full"],
        default="llm",
        help="Fallacy detection depth: taxonomy (lexical, no LLM), "
        "hybrid (neural+symbolic, optional LLM), "
        "llm (full LLM iterative, default), "
        "full (all strategies merged)",
    )
    parser.add_argument(
        "--shield-preset",
        type=str,
        choices=["off", "basic", "advanced", "output_only", "strict"],
        default="off",
        help="AI Shield preset: off (default, no shield), "
        "basic (heuristic only, no LLM cost), "
        "advanced (heuristic+LLM+output filter), "
        "output_only (post-LLM filtering only), "
        "strict (all layers, lowest thresholds, fail-closed)",
    )
    parser.add_argument(
        "--vote-method",
        type=str,
        choices=["approval", "stv", "copeland", "kemeny_young", "schulze"],
        default="copeland",
        help="Social choice voting method for governance phase: "
        "copeland (default, pairwise wins), "
        "approval (threshold-based), "
        "stv (single transferable vote), "
        "kemeny_young (optimal ranking), "
        "schulze (path-based, Condorcet-consistent)",
    )
    parser.add_argument(
        "--consensus-threshold",
        type=float,
        default=0.7,
        help="Consensus threshold (0.0-1.0) for governance deliberation (default: 0.7). "
        "Higher values require stronger agreement.",
    )
    parser.add_argument(
        "--fol-solver",
        type=str,
        choices=["tweety", "prover9", "eprover"],
        default="eprover",
        help="FOL solver backend: eprover (default, robust external solver), "
        "prover9 (external Prover9 binary, skip if absent), "
        "tweety (Java/TweetyProject, fallback of last resort)",
    )
    parser.add_argument(
        "--counter-strategy",
        type=str,
        choices=["auto", "socratic", "reductio", "analogy", "authority", "statistical"],
        default="auto",
        help="Counter-argument rhetorical strategy: auto (default, heuristic selection), "
        "socratic (questioning), reductio (reductio ad absurdum), "
        "analogy (analogical counter), authority (authority appeal), "
        "statistical (statistical evidence)",
    )
    parser.add_argument(
        "--formal-extension",
        type=str,
        default="all",
        help="Formal extension filter: all (default, run all 17 Tweety handlers), "
        "core (base 4 only: pl/fol/modal/dung), none (skip all formal), "
        "or comma-separated list (e.g. ranking,bipolar,aspic)",
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

    # Déterminer le mode d'orchestration
    mode = args.mode

    # Exécution de l'analyse
    if mode == "sherlock_modern":
        from argumentation_analysis.orchestration.sherlock_modern_orchestrator import (
            SherlockModernOrchestrator,
        )

        logging.info("Mode SHERLOCK MODERN : investigation multi-agent")
        orchestrator = SherlockModernOrchestrator()
        result = await orchestrator.investigate(text_content)

        print(f"\n{'='*60}")
        print(f" Sherlock Modern Investigation")
        print(f"{'='*60}")
        print(f"  Agents used     : {result.agent_count}")
        print(f"  Investigation steps : {len(result.trace)}")
        print(f"  Hypotheses tested   : {len(result.hypotheses)}")
        print(f"\n  Reasoning chain:")
        for i, step in enumerate(result.reasoning_chain, 1):
            print(f"    {i}. {step}")
        if result.hypotheses:
            print(f"\n  Hypotheses:")
            for h in result.hypotheses:
                status = "COHERENT" if h.get("coherent") else "INCOHERENT"
                print(f"    - {h['id']}: {status}")
        print(f"\n  Solution:\n    {result.solution[:500]}")
        print(f"{'='*60}\n")

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "trace": result.trace,
                        "solution": result.solution,
                        "agents": result.agents_used,
                        "hypotheses": result.hypotheses,
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                    default=str,
                )
            logging.info(f"Results saved to {output_path}")
    elif mode == "conversational":
        from argumentation_analysis.orchestration.conversational_orchestrator import (
            run_conversational_analysis,
        )

        logging.info("Mode CONVERSATIONNEL : agents dialoguent via AgentGroupChat")
        results = await run_conversational_analysis(
            text=text_content,
            max_turns_per_phase=5,
            extraction_max_turns=args.extraction_turns,
            formal_max_turns=args.formal_turns,
            synthesis_max_turns=args.synthesis_turns,
            reanalysis_max_turns=args.reanalysis_turns,
        )

        # Afficher le résumé
        print(f"\n{'='*60}")
        print(f" Mode conversationnel — {results['total_messages']} messages")
        print(f"{'='*60}")
        print(f"  Phases : {', '.join(results['phases'])}")
        print(f"  Messages total : {results['total_messages']}")
        print(f"  Champs état non-vides : {results['state_non_empty_fields']}")
        print(f"  Durée : {results['duration_seconds']:.1f}s")

        # Aperçu des messages
        for msg in results.get("conversation_log", [])[:10]:
            phase = msg.get("phase", "")
            agent = msg.get("agent", "?")
            content = msg.get("content", "")[:120]
            print(f"  [{phase}] {agent}: {content}...")
        if len(results.get("conversation_log", [])) > 10:
            print(f"  ... et {len(results['conversation_log']) - 10} messages de plus")

        print(f"{'='*60}\n")

        # Rich output formatting for conversational mode
        if args.rich_output:
            try:
                from argumentation_analysis.cli.output_formatter import (
                    render_spectacular_result,
                )

                # Normalize conversational result to expected format
                render_result = {
                    "workflow_name": results.get("workflow_name", "conversational"),
                    "state_snapshot": results.get("state_snapshot", {}),
                    "summary": results.get(
                        "summary",
                        {
                            "completed": len(results.get("phases", [])),
                            "total": len(results.get("phases", [])),
                        },
                    ),
                    "capabilities_used": results.get("capabilities_used", []),
                }
                render_spectacular_result(render_result)
            except ImportError:
                logging.warning("Module output_formatter non disponible")

        # Sauvegarder si demandé
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            logging.info(f"Résultats sauvegardés dans {output_path}")
    elif mode == "hierarchical":
        from argumentation_analysis.orchestration.hierarchical.orchestrator import (
            run_hierarchical_analysis,
        )

        hier_mode = getattr(args, "hierarchical_mode", "bridge")
        if hier_mode == "delegation":
            logging.info(
                "Mode HIÉRARCHIQUE (M3 delegation) : "
                "Strategic → Tactical → Operational (3-tier explicit chain)"
            )
        else:
            logging.info(
                "Mode HIÉRARCHIQUE (M2 bridge) : StrategicManager → Lego WorkflowExecutor"
            )
        results = await run_hierarchical_analysis(text=text_content, mode=hier_mode)

        # Afficher le résumé
        conclusion = results.get("conclusion", "")
        objectives = results.get("objectives", [])

        print(f"\n{'='*60}")
        if results.get("mode") == "delegation":
            op_results = results.get("operational_results", [])
            completed = sum(1 for r in op_results if r.get("status") == "completed")
            print(f" Mode hiérarchique (M3 delegation) — {len(op_results)} tâches")
            print(f"{'='*60}")
            print(f"  Objectifs stratégiques : {len(objectives)}")
            for obj in objectives:
                print(
                    f"    - [{obj.get('priority', '?').upper()}] {obj.get('description', '?')}"
                )
            print(f"  Tâches créées      : {results.get('tasks_created', 0)}")
            print(f"  Tâches complétées  : {completed}/{len(op_results)}")
        else:
            summary = results.get("summary", {})
            print(f" Mode hiérarchique (M2 bridge) — {summary.get('total', 0)} phases")
            print(f"{'='*60}")
            print(f"  Objectifs stratégiques : {len(objectives)}")
            for obj in objectives:
                print(
                    f"    - [{obj.get('priority', '?').upper()}] {obj.get('description', '?')}"
                )
            print(
                f"  Phases complétées : {summary.get('completed', 0)}/{summary.get('total', 0)}"
            )
            print(f"  Phases échouées   : {summary.get('failed', 0)}")
            print(f"  Phases sautées    : {summary.get('skipped', 0)}")
            print(f"  Durée : {results.get('duration_seconds', 0):.1f}s")
        if conclusion:
            print(f"\n  Conclusion : {conclusion}")
        print(f"{'='*60}\n")

        # Sauvegarder si demandé
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            logging.info(f"Résultats sauvegardés dans {output_path}")
    elif mode == "cluedo":
        from semantic_kernel import Kernel

        from argumentation_analysis.orchestration.cluedo_extended_orchestrator import (
            run_cluedo_oracle_game,
        )

        logging.info("Mode CLUEDO : investigation Sherlock-Watson-Oracle")

        # Build SK kernel with LLM service
        kernel = Kernel()
        if llm_service and hasattr(llm_service, "service_id"):
            from argumentation_analysis.core.llm_service import create_llm_service

            svc = create_llm_service(service_id="cluedo_mode")
            if svc and hasattr(svc, "add_to_kernel"):
                svc.add_to_kernel(kernel)
            else:
                kernel.add_service(svc)

        # Use text as initial question context if provided
        initial_question = (
            f"Analyse le texte suivant pour y trouver des indices : {text_content[:500]}"
            if text_content
            else "L'enquête commence. Sherlock, menez l'investigation !"
        )

        results = await run_cluedo_oracle_game(
            kernel=kernel,
            initial_question=initial_question,
        )

        # Display cluedo results
        investigation = results.get("investigation", {})
        solution = results.get("solution", {})
        trace = results.get("trace", [])

        print(f"\n{'='*60}")
        print(f" Cluedo Investigation Results")
        print(f"{'='*60}")
        print(f"  Trace steps     : {len(trace) if isinstance(trace, list) else 'N/A'}")
        if investigation:
            print(
                f"  Investigation   : {json.dumps(investigation, ensure_ascii=False, default=str)[:300]}"
            )
        if solution:
            print(
                f"  Solution        : {json.dumps(solution, ensure_ascii=False, default=str)[:300]}"
            )
        print(f"{'='*60}\n")

        # Save if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            logging.info(f"Results saved to {output_path}")
    else:
        await run_modern_analysis(
            text_content,
            workflow_name=args.workflow,
            output_file=args.output,
            rich_output=args.rich_output,
            fallacy_tier=args.fallacy_tier,
            shield_preset=args.shield_preset,
            vote_method=args.vote_method,
            consensus_threshold=args.consensus_threshold,
            fol_solver=args.fol_solver,
            counter_strategy=args.counter_strategy,
            formal_extension=args.formal_extension,
        )


if __name__ == "__main__":
    asyncio.run(main())
