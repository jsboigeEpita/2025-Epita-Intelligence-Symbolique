import argparse
import sys
from agent import DungAgent
from enhanced_agent import EnhancedDungAgent
from framework_generator import FrameworkGenerator
from io_utils import FrameworkIO
from config import get_project_info, RANDOM_GENERATION_CONFIG


def main():
    parser = argparse.ArgumentParser(
        description="Agent d'argumentation abstraite de Dung"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commandes disponibles")

    # Commande pour créer un framework interactif
    create_parser = subparsers.add_parser(
        "create", help="Créer un framework interactivement"
    )
    create_parser.add_argument(
        "--enhanced", action="store_true", help="Utiliser l'agent amélioré"
    )

    # Commande pour générer un framework aléatoire
    random_parser = subparsers.add_parser(
        "random", help="Générer un framework aléatoire"
    )
    random_parser.add_argument("--size", type=int, default=5, help="Nombre d'arguments")
    random_parser.add_argument(
        "--prob", type=float, default=0.3, help="Probabilité d'attaque"
    )
    random_parser.add_argument("--seed", type=int, help="Graine aléatoire")
    random_parser.add_argument("--save", help="Sauvegarder dans un fichier JSON")

    # Commande pour analyser un framework depuis un fichier
    analyze_parser = subparsers.add_parser(
        "analyze", help="Analyser un framework depuis un fichier"
    )
    analyze_parser.add_argument("file", help="Fichier JSON du framework")
    analyze_parser.add_argument(
        "--enhanced", action="store_true", help="Utiliser l'agent amélioré"
    )
    analyze_parser.add_argument("--export", help="Exporter l'analyse vers un fichier")

    # Commande pour les exemples classiques
    examples_parser = subparsers.add_parser("examples", help="Exemples classiques")
    examples_parser.add_argument(
        "--list", action="store_true", help="Lister les exemples disponibles"
    )
    examples_parser.add_argument("--run", help="Exécuter un exemple spécifique")

    # Commande de conversion de formats
    convert_parser = subparsers.add_parser("convert", help="Convertir entre formats")
    convert_parser.add_argument("input", help="Fichier d'entrée")
    convert_parser.add_argument("output", help="Fichier de sortie")
    convert_parser.add_argument(
        "--format",
        choices=["json", "tgf", "dot"],
        default="json",
        help="Format de sortie",
    )

    # Commande d'information
    info_parser = subparsers.add_parser("info", help="Informations sur le projet")

    args = parser.parse_args()

    if args.command == "create":
        create_interactive_framework(args.enhanced)
    elif args.command == "random":
        generate_random_framework(args)
    elif args.command == "analyze":
        analyze_framework_file(args)
    elif args.command == "examples":
        handle_examples(args)
    elif args.command == "convert":
        convert_framework(args)
    elif args.command == "info":
        show_project_info()
    else:
        parser.print_help()


def create_interactive_framework(use_enhanced=False):
    """Création interactive d'un framework"""
    agent_class = EnhancedDungAgent if use_enhanced else DungAgent
    agent = agent_class()

    print("=== CRÉATION INTERACTIVE D'UN FRAMEWORK ===")
    if use_enhanced:
        print("(Utilisation de l'agent amélioré)")

    # Ajouter des arguments
    print("\n--- Ajout des arguments ---")
    while True:
        arg = input("Nom de l'argument (ou 'stop' pour terminer): ").strip()
        if arg.lower() == "stop":
            break
        if arg:
            agent.add_argument(arg)
            print(f"✓ Argument '{arg}' ajouté")

    if len(agent._arguments) == 0:
        print("Aucun argument ajouté. Abandon.")
        return

    # Ajouter des attaques
    print(f"\n--- Ajout des attaques ---")
    print(f"Arguments disponibles: {list(agent._arguments.keys())}")
    while True:
        attack = input("Attaque (format: source target, ou 'stop'): ").strip()
        if attack.lower() == "stop":
            break
        parts = attack.split()
        if len(parts) == 2:
            source, target = parts
            if source in agent._arguments and target in agent._arguments:
                agent.add_attack(source, target)
                print(f"✓ Attaque {source} → {target} ajoutée")
            else:
                print("❌ Arguments invalides")
        else:
            print("❌ Format invalide (utilisez: source target)")

    analyze_framework(agent)

    # Optionnel: sauvegarder
    save = input("\nSauvegarder ce framework? (o/n): ").strip().lower()
    if save == "o":
        filename = input("Nom du fichier (sans extension): ").strip()
        if filename:
            FrameworkIO.export_to_json(agent, f"{filename}.json")


def generate_random_framework(args):
    """Génère un framework aléatoire"""
    print(f"=== GÉNÉRATION FRAMEWORK ALÉATOIRE ===")
    print(f"Taille: {args.size}, Probabilité: {args.prob}")
    if args.seed:
        print(f"Graine: {args.seed}")

    agent = FrameworkGenerator.generate_random_framework(
        args.size, args.prob, args.seed
    )

    analyze_framework(agent)

    if args.save:
        FrameworkIO.export_to_json(agent, args.save)


def analyze_framework_file(args):
    """Analyse un framework depuis un fichier"""
    try:
        if args.enhanced:
            # Charger dans agent standard puis transférer
            temp_agent = FrameworkIO.import_from_json(args.file)
            agent = EnhancedDungAgent()

            # Transférer les arguments et attaques
            for arg_name in temp_agent._arguments.keys():
                agent.add_argument(arg_name)
            for attack in temp_agent.af.getAttacks():
                source = attack.getAttacker().getName()
                target = attack.getAttacked().getName()
                agent.add_attack(source, target)
        else:
            agent = FrameworkIO.import_from_json(args.file)

        analyze_framework(agent)

        if args.export:
            FrameworkIO.export_analysis_report(agent, args.export)

    except FileNotFoundError:
        print(f"❌ Fichier non trouvé: {args.file}")
    except Exception as e:
        print(f"❌ Erreur lors de l'analyse: {e}")


def handle_examples(args):
    """Gère les exemples classiques"""
    examples = FrameworkGenerator.generate_classic_examples()

    if args.list:
        print("=== EXEMPLES DISPONIBLES ===")
        for name, agent in examples.items():
            props = agent.get_framework_properties()
            print(
                f"- {name}: {props['num_arguments']} arguments, {props['num_attacks']} attaques"
            )
        return

    if args.run:
        if args.run in examples:
            print(f"=== EXEMPLE: {args.run.upper()} ===")
            analyze_framework(examples[args.run])
        else:
            print(f"❌ Exemple '{args.run}' non trouvé")
            print(f"Exemples disponibles: {list(examples.keys())}")
        return

    # Exécuter tous les exemples
    for name, agent in examples.items():
        print(f"\n{'='*20} {name.upper()} {'='*20}")
        analyze_framework(agent)


def convert_framework(args):
    """Convertit un framework entre formats"""
    try:
        agent = FrameworkIO.import_from_json(args.input)

        if args.format == "json":
            FrameworkIO.export_to_json(agent, args.output)
        elif args.format == "tgf":
            FrameworkIO.export_to_tgf(agent, args.output)
        elif args.format == "dot":
            FrameworkIO.export_to_dot(agent, args.output)

        print(f"✓ Conversion terminée: {args.input} → {args.output}")

    except Exception as e:
        print(f"❌ Erreur de conversion: {e}")


def analyze_framework(agent):
    """Analyse complète d'un framework"""
    print("\n" + "=" * 60)
    print("ANALYSE DU FRAMEWORK")
    print("=" * 60)

    agent.analyze_framework_properties()
    print()
    agent.analyze_semantics_relationships()
    print()
    agent.print_all_arguments_status()


def show_project_info():
    """Affiche les informations du projet"""
    info = get_project_info()
    print("=== INFORMATIONS DU PROJET ===")
    print(f"Nom: {info['name']}")
    print(f"Version: {info['version']}")
    print(f"Sémantiques supportées: {', '.join(info['supported_semantics'])}")
    print(f"Formats supportés: {', '.join(info['supported_formats'])}")
    print(f"Racine du projet: {info['project_root']}")


if __name__ == "__main__":
    main()
