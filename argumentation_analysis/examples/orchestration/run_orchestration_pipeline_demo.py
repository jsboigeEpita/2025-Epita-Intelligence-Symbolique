#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Démonstration du Pipeline d'Orchestration Unifié
===============================================

Ce script démontre l'utilisation du nouveau pipeline d'orchestration unifié
qui intègre l'architecture hiérarchique et les orchestrateurs spécialisés.

Usage:
    python run_orchestration_pipeline_demo.py [--mode MODE] [--type TYPE] [--text TEXT]

Exemples:
    # Démonstration complète avec tous les modes
    python run_orchestration_pipeline_demo.py
    
    # Mode spécifique
    python run_orchestration_pipeline_demo.py --mode hierarchical_full --type comprehensive
    
    # Texte personnalisé
    python run_orchestration_pipeline_demo.py --text "Votre texte à analyser"
    
    # Comparaison des approches
    python run_orchestration_pipeline_demo.py --compare

Auteur: Intelligence Symbolique EPITA
Date: 10/06/2025
"""

import asyncio
import argparse
import logging
import time
import sys
from typing import Dict, Any

# Configuration du logging pour la démonstration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)

# Import du nouveau pipeline unifié
try:
    from argumentation_analysis.pipelines.unified_pipeline import analyze_text

    ORCHESTRATION_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Pipeline unifié non disponible: {e}")
    ORCHESTRATION_AVAILABLE = False

# Import du pipeline original pour comparaison
try:
    from argumentation_analysis.pipelines.unified_text_analysis import (
        run_unified_text_analysis_pipeline,
        UnifiedAnalysisConfig,
    )

    ORIGINAL_PIPELINE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Pipeline original non disponible: {e}")
    ORIGINAL_PIPELINE_AVAILABLE = False


# Textes d'exemple pour différents types d'analyse
EXAMPLE_TEXTS = {
    "rhetorical": """
    L'éducation est fondamentale pour le développement d'une société. Premièrement, elle forme les citoyens 
    en leur donnant les connaissances nécessaires pour participer activement à la vie démocratique. 
    Deuxièmement, elle favorise l'innovation et le progrès technologique. Cependant, certains prétendent 
    que l'éducation traditionnelle est obsolète. Cette affirmation est clairement fausse car elle ignore 
    les nombreux bénéfices prouvés de l'enseignement structuré.
    """,
    "logical": """
    Si tous les hommes sont mortels, et si Socrate est un homme, alors Socrate est mortel. 
    Cette déduction suit le principe du syllogisme aristotélicien. Or, nous savons que Socrate est effectivement 
    un homme, donc nous pouvons conclure avec certitude qu'il est mortel. Ce raisonnement illustre parfaitement 
    la logique déductive où la conclusion découle nécessairement des prémisses.
    """,
    "investigative": """
    Le témoin A affirme avoir vu le suspect près de la scène de crime à 21h30. Le témoin B contredit cette version 
    en déclarant que le suspect était ailleurs à cette heure. L'alibi du suspect semble solide, mais plusieurs 
    incohérences apparaissent dans son témoignage. De plus, les preuves matérielles suggèrent une présence sur 
    les lieux. Qui dit la vérité ? Quels éléments permettraient de trancher cette contradiction ?
    """,
    "fallacy_focused": """
    "Tous ceux qui s'opposent à cette mesure sont des extrémistes dangereux. D'ailleurs, même mon voisin, 
    qui est pourtant quelqu'un de bien, la soutient. Si nous n'agissons pas maintenant, c'est la catastrophe 
    assurée ! De toute façon, puisque 90% des experts sont d'accord, il n'y a plus rien à débattre. 
    Soit vous êtes avec nous, soit vous êtes contre la nation."
    """,
    "debate": """
    Participant A : "Le télétravail améliore la productivité car les employés sont moins distraits."
    Participant B : "C'est faux ! Le télétravail isole les gens et nuit à la collaboration."
    Participant A : "Vous généralisez abusivement. Les études montrent une amélioration de 20% de la productivité."
    Participant B : "Ces études sont biaisées par l'industrie tech. En réalité, la créativité diminue sans contact humain."
    """,
    "comprehensive": """
    La question du changement climatique soulève des enjeux complexes qui nécessitent une approche multidisciplinaire. 
    D'un côté, les données scientifiques convergent vers un consensus sur l'origine anthropique du réchauffement. 
    Les modèles climatiques, basés sur des décennies d'observations, prévoient des conséquences dramatiques si aucune 
    action n'est entreprise. D'un autre côté, les solutions proposées font débat. Certains privilégient les technologies 
    vertes, d'autres la décroissance. Cependant, l'argument selon lequel "nous n'avons pas le choix" constitue une 
    fausse dichotomie qui ignore les nuances des politiques possibles. Il est donc crucial d'analyser rationnellement 
    les options disponibles sans tomber dans l'alarmisme ni le déni.
    """,
}


def print_header(title: str, char: str = "=", width: int = 80):
    """Affiche un en-tête formaté."""
    print(f"\n{char * width}")
    print(f"{title:^{width}}")
    print(f"{char * width}")


def print_results_summary(results: Dict[str, Any], title: str = "Résultats d'Analyse"):
    """Affiche un résumé formaté des résultats."""
    print_header(title, "─", 60)

    # Métadonnées de base
    metadata = results.get("metadata", {})
    print(f"📊 ID d'analyse: {metadata.get('analysis_id', 'N/A')}")
    print(f"🕐 Temps d'exécution: {results.get('execution_time', 0):.2f}s")
    print(f"📝 Mode d'orchestration: {metadata.get('orchestration_mode', 'N/A')}")
    print(f"🎯 Type d'analyse: {metadata.get('analysis_type', 'N/A')}")
    print(f"✅ Statut: {results.get('status', 'unknown')}")

    # Résultats hiérarchiques
    if "strategic_analysis" in results and results["strategic_analysis"]:
        strategic = results["strategic_analysis"]
        print(f"\n🎯 Analyse Stratégique:")
        print(f"   • Objectifs définis: {len(strategic.get('objectives', []))}")

    if "tactical_coordination" in results and results["tactical_coordination"]:
        tactical = results["tactical_coordination"]
        print(f"⚔️ Coordination Tactique:")
        print(f"   • Tâches créées: {tactical.get('tasks_created', 0)}")

    if "operational_results" in results and results["operational_results"]:
        operational = results["operational_results"]
        print(f"⚙️ Exécution Opérationnelle:")
        print(f"   • Tâches exécutées: {operational.get('tasks_executed', 0)}")

    # Orchestration spécialisée
    if "specialized_orchestration" in results and results["specialized_orchestration"]:
        specialized = results["specialized_orchestration"]
        orchestrator = specialized.get("orchestrator_used", "N/A")
        print(f"🚀 Orchestration Spécialisée:")
        print(f"   • Orchestrateur: {orchestrator}")
        print(f"   • Statut: {specialized.get('results', {}).get('status', 'N/A')}")

    # Coordination hiérarchique
    if "hierarchical_coordination" in results and results["hierarchical_coordination"]:
        coord = results["hierarchical_coordination"]
        print(f"🏗️ Coordination Hiérarchique:")
        print(f"   • Score global: {coord.get('overall_score', 0):.2%}")
        print(f"   • Alignement stratégique: {coord.get('strategic_alignment', 0):.2%}")
        print(f"   • Efficacité tactique: {coord.get('tactical_efficiency', 0):.2%}")
        print(f"   • Succès opérationnel: {coord.get('operational_success', 0):.2%}")

    # Analyses de base (compatibilité)
    if "informal_analysis" in results and results["informal_analysis"]:
        informal = results["informal_analysis"]
        fallacies = informal.get("fallacies", [])
        print(f"🔍 Analyse Informelle:")
        print(f"   • Sophismes détectés: {len(fallacies)}")
        if fallacies:
            avg_confidence = sum(f.get("confidence", 0) for f in fallacies) / len(
                fallacies
            )
            print(f"   • Confiance moyenne: {avg_confidence:.2%}")

    if "formal_analysis" in results and results["formal_analysis"]:
        formal = results["formal_analysis"]
        print(f"🧮 Analyse Formelle:")
        print(f"   • Statut: {formal.get('status', 'N/A')}")
        if formal.get("consistency_check") is not None:
            consistency = (
                "✅ Cohérent" if formal["consistency_check"] else "❌ Incohérent"
            )
            print(f"   • Cohérence: {consistency}")

    # Recommandations
    recommendations = results.get("recommendations", [])
    if recommendations:
        print(f"\n💡 Recommandations ({len(recommendations)}):")
        for i, rec in enumerate(
            recommendations[:3], 1
        ):  # Afficher max 3 recommandations
            print(f"   {i}. {rec}")

    # Erreurs éventuelles
    if "error" in results:
        print(f"\n❌ Erreur: {results['error']}")

    print("─" * 60)


async def demo_basic_usage():
    """Démonstration de l'utilisation de base."""
    print_header("Démonstration - Utilisation de Base")

    text = EXAMPLE_TEXTS["comprehensive"]
    print(f"📝 Texte d'exemple: {text[:100]}...")

    print("\n🔄 Analyse avec configuration par défaut (sélection automatique)...")
    start_time = time.time()

    try:
        results = await analyze_text(text, mode="orchestration")
        execution_time = time.time() - start_time

        print(f"✅ Analyse terminée en {execution_time:.2f}s")
        print_results_summary(results, "Analyse avec Configuration Par Défaut")

    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")


async def demo_hierarchical_orchestration():
    """Démonstration de l'orchestration hiérarchique complète."""
    print_header("Démonstration - Orchestration Hiérarchique Complète")

    text = EXAMPLE_TEXTS["comprehensive"]

    print("🏗️ Lancement de l'orchestration hiérarchique complète...")

    try:
        results = await analyze_text(
            text, mode="orchestration", orchestration_mode="hierarchical_full"
        )
        print_results_summary(results, "Orchestration Hiérarchique Complète")

        # Affichage détaillé de la trace d'orchestration
        trace = results.get("orchestration_trace", [])
        if trace:
            print(f"\n📋 Trace d'orchestration ({len(trace)} événements):")
            for event in trace[-5:]:  # Afficher les 5 derniers événements
                timestamp = event.get("timestamp", "")[
                    :19
                ]  # Format YYYY-MM-DD HH:MM:SS
                event_type = event.get("event_type", "")
                print(f"   {timestamp} - {event_type}")

    except Exception as e:
        print(f"❌ Erreur lors de l'orchestration hiérarchique: {e}")


async def demo_specialized_orchestrators():
    """Démonstration des orchestrateurs spécialisés."""
    print_header("Démonstration - Orchestrateurs Spécialisés")

    specialized_demos = [
        {
            "name": "Investigation Cluedo",
            "mode": "cluedo",
            "text": EXAMPLE_TEXTS["investigative"],
        },
        {
            "name": "Analyse Rhétorique",
            "mode": "conversation",
            "text": EXAMPLE_TEXTS["rhetorical"],
        },
        {
            "name": "Détection de Sophismes",
            "mode": "real_llm",
            "text": EXAMPLE_TEXTS["fallacy_focused"],
        },
    ]

    for demo in specialized_demos:
        print(f"\n🚀 {demo['name']}...")

        try:
            results = await analyze_text(
                demo["text"], mode="orchestration", orchestration_mode=demo["mode"]
            )
            print_results_summary(results, f"Orchestrateur Spécialisé - {demo['name']}")

        except Exception as e:
            print(f"❌ Erreur {demo['name']}: {e}")


async def demo_api_compatibility():
    """Démonstration de la compatibilité avec l'API existante."""
    print_header("Démonstration - Compatibilité API Existante")

    text = EXAMPLE_TEXTS["rhetorical"]

    print("🔄 Test avec l'API de compatibilité...")

    try:
        # Nouvelle API
        results = await analyze_text(
            text,
            mode="orchestration",
            orchestration_mode="auto_select",
            use_mocks=False,
        )
        print_results_summary(results, "Analyse via API unifiée")

        # Comparaison avec l'API originale si disponible
        if ORIGINAL_PIPELINE_AVAILABLE:
            print("\n🔄 Comparaison avec le pipeline original...")
            original_config = UnifiedAnalysisConfig(
                analysis_modes=["informal", "formal"], orchestration_mode="pipeline"
            )

            original_results = await run_unified_text_analysis_pipeline(
                text, original_config
            )
            print_results_summary(original_results, "Pipeline Original")

            # Comparaison simple
            new_time = results.get("execution_time", 0)
            old_time = original_results.get("execution_time", 0)
            print(f"\n⚡ Comparaison des performances:")
            print(f"   • Nouveau pipeline: {new_time:.2f}s")
            print(f"   • Pipeline original: {old_time:.2f}s")

    except Exception as e:
        print(f"❌ Erreur test compatibilité: {e}")


async def demo_orchestration_comparison():
    """Démonstration de la comparaison d'approches d'orchestration."""
    print_header("Démonstration - Comparaison des Approches d'Orchestration")

    EXAMPLE_TEXTS["comprehensive"]
    approaches = ["pipeline", "hierarchical", "specialized", "hybrid"]

    print(f"📊 Comparaison des approches: {', '.join(approaches)}")
    print("🔄 Lancement des analyses comparatives...")

    try:
        print("La comparaison des approches est maintenant gérée par le mode 'hybrid'.")
        # Laisser vide car la fonction a été Dépréciée.
    except Exception as e:
        print(f"❌ Erreur comparaison: {e}")


async def demo_custom_analysis():
    """Démonstration d'une analyse personnalisée."""
    print_header("Démonstration - Analyse Personnalisée")

    text = EXAMPLE_TEXTS["debate"]

    print("🎯 Analyse de débat avec configuration hybride adaptative...")
    print(f"📝 Texte: {text[:150]}...")

    try:
        results = await analyze_text(
            text,
            mode="hybrid",
            orchestration_mode="adaptive_hybrid",
            analysis_type="debate_analysis",
        )
        print_results_summary(results, "Analyse Personnalisée - Débat")

        # Affichage des détails de configuration
        metadata = results.get("metadata", {})
        print(f"\n⚙️ Configuration utilisée:")
        print(f"   • Mode d'orchestration: {metadata.get('orchestration_mode')}")
        print(f"   • Type d'analyse: {metadata.get('analysis_type')}")

        # Trace d'orchestration si disponible
        trace = results.get("orchestration_trace", [])
        strategic_events = [e for e in trace if "strategic" in e.get("event_type", "")]
        specialized_events = [
            e for e in trace if "specialized" in e.get("event_type", "")
        ]

        if strategic_events or specialized_events:
            print(f"\n📋 Activité d'orchestration:")
            print(f"   • Événements stratégiques: {len(strategic_events)}")
            print(f"   • Événements spécialisés: {len(specialized_events)}")

    except Exception as e:
        print(f"❌ Erreur analyse personnalisée: {e}")


async def run_full_demo(args: argparse.Namespace):
    """Lance la démonstration complète."""
    print_header("DÉMONSTRATION COMPLÈTE DU PIPELINE D'ORCHESTRATION UNIFIÉ", "=", 80)

    if not ORCHESTRATION_AVAILABLE:
        print("❌ Le pipeline d'orchestration n'est pas disponible.")
        print("   Vérifiez que tous les modules requis sont installés.")
        return

    print("🚀 Démarrage de la démonstration complète...")
    print(
        "   Cette démonstration présente les différentes capacités du nouveau pipeline."
    )

    demos = [
        demo_basic_usage,
        demo_hierarchical_orchestration,
        demo_specialized_orchestrators,
        demo_api_compatibility,
        demo_orchestration_comparison,
        demo_custom_analysis,
    ]

    total_start = time.time()

    for i, demo in enumerate(demos, 1):
        print(
            f"\n📍 Démonstration {i}/{len(demos)}: {demo.__name__.replace('demo_', '').replace('_', ' ').title()}"
        )

        try:
            await demo()
        except KeyboardInterrupt:
            print("\n⏹️ Démonstration interrompue par l'utilisateur.")
            break
        except Exception as e:
            print(f"❌ Erreur lors de la démonstration {demo.__name__}: {e}")
            continue

        if i < len(demos) and not args.non_interactive:
            # Désactivation de l'attente pour l'automatisation.
            # print("\n⏱️ Appuyez sur Entrée pour continuer vers la démonstration suivante...")
            # input()
            pass

    total_time = time.time() - total_start
    print(f"\n🏁 Démonstration complète terminée en {total_time:.1f}s")
    print("   Merci d'avoir testé le pipeline d'orchestration unifié !")


async def run_specific_demo(args: argparse.Namespace):
    """Lance une démonstration spécifique en utilisant les arguments parsés."""
    mode = args.mode
    analysis_type = args.type
    text = args.text
    output_dir = args.output_dir

    print_header(f"Démonstration Spécifique - {mode.upper()}")

    if not text:
        # Sélectionner un texte approprié selon le type d'analyse
        text_mapping = {
            "rhetorical": "rhetorical",
            "logical": "logical",
            "investigative": "investigative",
            "fallacy_focused": "fallacy_focused",
            "debate_analysis": "debate",
            "comprehensive": "comprehensive",
        }
        text_key = text_mapping.get(analysis_type, "comprehensive")
        text = EXAMPLE_TEXTS[text_key]

    try:
        # Utiliser la fonction factory pour créer la configuration à partir des arguments
        config = create_extended_config_from_params(
            orchestration_mode=mode,
            analysis_type=analysis_type,
            output_dir=output_dir,
            save_orchestration_trace=True,
        )

        print(f"🎯 Mode d'orchestration: {config.orchestration_mode.value}")
        print(f"📊 Type d'analyse: {config.analysis_type.value}")
        print(f"📝 Texte: {text[:100]}...")
        print(f"📁 Répertoire de sortie: {config.output_dir}")

        print("\n🔄 Lancement de l'analyse...")

        results = await run_unified_orchestration_pipeline(text, config)
        print_results_summary(results, f"Démonstration - {mode.title()}")

    except Exception as e:
        print(f"❌ Erreur lors de la démonstration spécifique: {e}")


def main():
    """Point d'entrée principal du script."""
    parser = argparse.ArgumentParser(
        description="Démonstration du Pipeline d'Orchestration Unifié",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  %(prog)s                                    # Démonstration complète
  %(prog)s --mode hierarchical_full           # Mode hiérarchique complet
  %(prog)s --type investigative               # Analyse investigative
  %(prog)s --mode cluedo --type investigative # Investigation Cluedo
  %(prog)s --compare                          # Comparaison des approches
  %(prog)s --text "Votre texte"               # Texte personnalisé
        """,
    )

    parser.add_argument(
        "--mode",
        choices=[
            "auto_select",
            "hierarchical_full",
            "strategic_only",
            "tactical_coordination",
            "operational_direct",
            "cluedo_investigation",
            "logic_complex",
            "adaptive_hybrid",
            "pipeline",
            "real",
            "conversation",
        ],
        default=None,
        help="Mode d'orchestration à utiliser",
    )

    parser.add_argument(
        "--type",
        choices=[
            "comprehensive",
            "rhetorical",
            "logical",
            "investigative",
            "fallacy_focused",
            "argument_structure",
            "debate_analysis",
            "custom",
        ],
        default="comprehensive",
        help="Type d'analyse à effectuer",
    )

    parser.add_argument(
        "--text", type=str, default=None, help="Texte personnalisé à analyser"
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Répertoire pour sauvegarder les résultats et les traces",
    )

    parser.add_argument(
        "--compare",
        action="store_true",
        help="Lancer une comparaison des différentes approches d'orchestration",
    )

    parser.add_argument(
        "--verbose", action="store_true", help="Affichage verbeux avec logs détaillés"
    )

    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Désactive les pauses interactives entre les démonstrations",
    )

    args = parser.parse_args()

    # Configuration du logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Vérification de la disponibilité
    if not ORCHESTRATION_AVAILABLE:
        print("❌ Erreur: Le pipeline d'orchestration unifié n'est pas disponible.")
        print(
            "   Vérifiez que tous les modules et dépendances sont correctement installés."
        )
        return 1

    # Exécution selon les arguments
    try:
        if args.compare:
            # Comparaison des approches
            text = args.text or EXAMPLE_TEXTS["comprehensive"]
            asyncio.run(compare_orchestration_approaches(text))

        elif args.mode:
            # Démonstration spécifique
            asyncio.run(run_specific_demo(args))

        else:
            # Démonstration complète
            asyncio.run(run_full_demo(args))

    except KeyboardInterrupt:
        print("\n⏹️ Démonstration interrompue par l'utilisateur.")
        return 0
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
