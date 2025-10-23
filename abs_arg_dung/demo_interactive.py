#!/usr/bin/env python3
"""
Démonstration interactive du projet d'argumentation Dung
Script de présentation pour showcaser toutes les fonctionnalités
"""

import time
import os
from agent import DungAgent
from enhanced_agent import EnhancedDungAgent
from framework_generator import FrameworkGenerator
from io_utils import FrameworkIO
from project_info import print_project_info


def pause(message="Appuyez sur Entrée pour continuer..."):
    """Pause interactive"""
    input(f"\n{message}")


def demo_header(title):
    """Affiche un en-tête de démonstration"""
    print(f"\n{'='*70}")
    print(f"🎯 {title}")
    print(f"{'='*70}")


def demo_basic_usage():
    """Démonstration de l'utilisation de base"""
    demo_header("DÉMONSTRATION 1: UTILISATION DE BASE")

    print("Création d'un framework simple pour modéliser un débat:")
    print("💭 Sujet: Faut-il être végétarien ?")

    agent = DungAgent()

    # Arguments du débat
    arguments = {
        "sante": "Être végétarien est bon pour la santé",
        "environnement": "L'élevage nuit à l'environnement",
        "plaisir": "La viande procure du plaisir gustati",
        "tradition": "Manger de la viande est traditionnel",
        "nutrition": "La viande apporte des nutriments essentiels",
    }

    print("\n📝 Arguments du débat:")
    for key, desc in arguments.items():
        agent.add_argument(key)
        print(f"  • {key}: {desc}")

    pause()

    print("\n⚔️ Relations d'attaque:")
    attacks = [
        ("sante", "nutrition"),
        ("environnement", "tradition"),
        ("plaisir", "sante"),
        ("nutrition", "sante"),
    ]

    for source, target in attacks:
        agent.add_attack(source, target)
        print(f"  • {source} attaque {target}")

    pause()

    print("\n🔍 Analyse du débat:")
    agent.analyze_semantics_relationships()

    pause()

    print("\n📊 Statut de chaque argument:")
    agent.print_all_arguments_status()

    pause()

    # Visualisation
    print("\n📈 Génération du graphique...")
    agent.visualize_graph(title_suffix=" - Débat Végétarisme")
    print("Graphique sauvegardé!")

    return agent


def demo_enhanced_agent():
    """Démonstration de l'agent amélioré"""
    demo_header("DÉMONSTRATION 2: AGENT AMÉLIORÉ vs STANDARD")

    print("Comparaison sur un cas problématique: argument auto-attaquant")
    print("💭 Cas: Un argument contradictoire qui s'auto-réfute")

    # Agent standard
    print("\n🔧 Agent standard:")
    standard_agent = DungAgent()
    standard_agent.add_argument("contradiction")
    standard_agent.add_argument("conclusion")
    standard_agent.add_attack("contradiction", "contradiction")  # Self-attack
    standard_agent.add_attack("contradiction", "conclusion")

    std_grounded = standard_agent.get_grounded_extension()
    print(f"Extension fondée: {std_grounded}")

    # Agent amélioré
    print("\n✨ Agent amélioré:")
    enhanced_agent = EnhancedDungAgent()
    enhanced_agent.add_argument("contradiction")
    enhanced_agent.add_argument("conclusion")
    enhanced_agent.add_attack("contradiction", "contradiction")
    enhanced_agent.add_attack("contradiction", "conclusion")

    enh_grounded = enhanced_agent.get_grounded_extension()
    print(f"Extension fondée: {enh_grounded}")

    print("\n🎯 Résultat:")
    if std_grounded != enh_grounded:
        print("✅ L'agent amélioré corrige le comportement!")
        print(f"  Standard: {std_grounded} (conservateur)")
        print(f"  Amélioré: {enh_grounded} (logique corrigée)")
    else:
        print("ℹ️  Les deux agents donnent le même résultat")

    pause()


def demo_classic_examples():
    """Démonstration des exemples classiques"""
    demo_header("DÉMONSTRATION 3: EXEMPLES CLASSIQUES")

    examples = FrameworkGenerator.generate_classic_examples()

    for name, agent in examples.items():
        print(f"\n🔥 Exemple: {name.upper()}")

        if name == "triangle":
            print(
                "Triangle conflictuel - Cycle d'arguments qui s'attaquent mutuellement"
            )
        elif name == "self_defending":
            print("Arguments auto-défendeurs - Conflit symétrique")
        elif name == "nixon_diamond":
            print("Diamant de Nixon - Dilemme classique avec conflits croisés")

        print("\nAnalyse:")
        semantics = agent.get_semantics_relationships()
        grounded = semantics["extensions"]["grounded"]
        preferred = semantics["extensions"]["preferred"]

        print(f"  Extension fondée: {grounded}")
        print(f"  Extensions préférées: {preferred}")

        if name == "nixon_diamond":
            print("  💡 Ce cas illustre l'importance des sémantiques multiples")

        pause("Continuer vers l'exemple suivant...")


def demo_random_generation():
    """Démonstration de la génération aléatoire"""
    demo_header("DÉMONSTRATION 4: GÉNÉRATION & ANALYSE AUTOMATIQUE")

    print("Génération de frameworks aléatoires pour analyse statistique")

    sizes = [5, 8, 12]
    probabilities = [0.2, 0.4, 0.6]

    results = []

    for size in sizes:
        for prob in probabilities:
            print(f"\n🎲 Framework: {size} arguments, probabilité d'attaque {prob}")

            agent = FrameworkGenerator.generate_random_framework(size, prob, seed=42)
            props = agent.get_framework_properties()
            semantics = agent.get_semantics_relationships()

            result = {
                "size": size,
                "prob": prob,
                "attacks": props["num_attacks"],
                "cycles": props["has_cycles"],
                "grounded_size": len(semantics["extensions"]["grounded"]),
                "preferred_count": len(semantics["extensions"]["preferred"]),
            }
            results.append(result)

            print(f"  📊 {result['attacks']} attaques, cycles: {result['cycles']}")
            print(f"  📊 Extension fondée: {result['grounded_size']} arguments")
            print(f"  📊 {result['preferred_count']} extensions préférées")

    pause()

    print("\n📈 Tendances observées:")
    for result in results:
        density = result["attacks"] / (result["size"] ** 2)
        print(
            f"  Taille {result['size']}, prob {result['prob']}: densité {density:.2f}"
        )


def demo_import_export():
    """Démonstration des capacités d'import/export"""
    demo_header("DÉMONSTRATION 5: IMPORT/EXPORT & INTEROPÉRABILITÉ")

    print("Création d'un framework et export vers différents formats")

    # Créer un framework d'exemple
    agent = DungAgent()
    for arg in ["A", "B", "C", "D"]:
        agent.add_argument(arg)

    agent.add_attack("A", "B")
    agent.add_attack("B", "C")
    agent.add_attack("C", "D")
    agent.add_attack("D", "A")  # Cycle

    print("Framework créé: A→B→C→D→A (cycle)")

    # Export vers différents formats
    formats = {
        "json": "demo_framework.json",
        "tg": "demo_framework.tg",
        "dot": "demo_framework.dot",
    }

    print("\n💾 Export vers différents formats:")
    for fmt, filename in formats.items():
        if fmt == "json":
            FrameworkIO.export_to_json(agent, filename)
        elif fmt == "tg":
            FrameworkIO.export_to_tgf(agent, filename)
        elif fmt == "dot":
            FrameworkIO.export_to_dot(agent, filename)

        if os.path.exists(filename):
            size = os.path.getsize(filename)
            print(f"  ✅ {fmt.upper()}: {filename} ({size} bytes)")

    # Test import
    print("\n📥 Test d'import depuis JSON:")
    imported_agent = FrameworkIO.import_from_json("demo_framework.json")
    imported_grounded = imported_agent.get_grounded_extension()
    print(f"Extension fondée importée: {imported_grounded}")

    # Export rapport d'analyse
    print("\n📋 Export rapport d'analyse:")
    FrameworkIO.export_analysis_report(agent, "demo_analysis.json")
    print("Rapport complet exporté!")

    pause()


def demo_performance():
    """Démonstration de performance"""
    demo_header("DÉMONSTRATION 6: PERFORMANCE & PASSAGE À L'ÉCHELLE")

    print("Test de performance sur différentes tailles de frameworks")

    sizes = [5, 10, 15]

    for size in sizes:
        print(f"\n⏱️ Test taille {size}:")
        agent = FrameworkGenerator.generate_random_framework(size, 0.3, seed=42)

        start_time = time.time()
        grounded = agent.get_grounded_extension()
        preferred = agent.get_preferred_extensions()
        stable = agent.get_stable_extensions()
        complete = agent.get_complete_extensions()
        end_time = time.time()

        computation_time = end_time - start_time

        print(f"  🕒 Temps de calcul: {computation_time:.4f}s")
        print(f"  📊 Extensions: grounded={len(grounded)}, preferred={len(preferred)}")
        print(f"     stable={len(stable)}, complete={len(complete)}")

        if computation_time > 1.0:
            print("  ⚠️  Calcul intensif détecté")
        else:
            print("  ✅ Performance excellente")

    pause()


def main_demo():
    """Démonstration principale"""
    print("🎯 DÉMONSTRATION INTERACTIVE")
    print("Agent d'Argumentation Abstraite de Dung")
    print("=" * 70)

    print_project_info()

    pause("Démarrer la démonstration...")

    # Exécuter toutes les démonstrations
    demos = [
        ("Utilisation de base", demo_basic_usage),
        ("Agent amélioré", demo_enhanced_agent),
        ("Exemples classiques", demo_classic_examples),
        ("Génération aléatoire", demo_random_generation),
        ("Import/Export", demo_import_export),
        ("Performance", demo_performance),
    ]

    for i, (title, demo_func) in enumerate(demos, 1):
        print(f"\n🎬 Démonstration {i}/{len(demos)}: {title}")
        try:
            demo_func()
        except KeyboardInterrupt:
            print("\n⏸️ Démonstration interrompue par l'utilisateur")
            break
        except Exception as e:
            print(f"\n❌ Erreur dans la démonstration: {e}")
            continue

    # Conclusion
    demo_header("CONCLUSION")
    print("🎉 Démonstration terminée!")
    print("\nVotre projet d'argumentation Dung comprend:")
    print("✅ Agent principal avec toutes les sémantiques")
    print("✅ Agent amélioré avec corrections")
    print("✅ Génération automatique de frameworks")
    print("✅ Import/export multi-formats")
    print("✅ Interface CLI complète")
    print("✅ Tests exhaustifs et benchmarks")
    print("✅ Visualisation graphique")
    print("✅ Documentation professionnelle")

    print("\n🚀 Le projet est maintenant prêt pour évaluation!")
    print("📁 Tous les fichiers sont dans: /home/wassim/repos/mon_agent_dung")


if __name__ == "__main__":
    try:
        main_demo()
    except KeyboardInterrupt:
        print("\n\n👋 Démonstration terminée par l'utilisateur")
    except Exception as e:
        print(f"\n\n💥 Erreur inattendue: {e}")
        import traceback

        traceback.print_exc()
