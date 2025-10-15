"""
Métadonnées et informations du projet d'argumentation Dung
"""

from datetime import datetime

PROJECT_METADATA = {
    "name": "Agent d'Argumentation Abstraite de Dung",
    "version": "1.0.0",
    "description": "Implémentation complète d'un agent d'argumentation basé sur les frameworks de Dung",
    "author": "Wassim",
    "creation_date": "2025-06-10",
    "python_version": "3.8+",
    "dependencies": [
        "matplotlib>=3.5.0",
        "networkx>=2.6.0",
        "pyjnius>=1.4.0",
        "numpy>=1.20.0",
    ],
    "tweety_version": "1.27-1.28",
    "supported_semantics": [
        "grounded",
        "preferred",
        "stable",
        "complete",
        "admissible",
        "ideal",
        "semi_stable",
    ],
    "features": [
        "Framework construction and manipulation",
        "Extension computation for all major semantics",
        "Graph visualization with matplotlib",
        "Import/Export (JSON, TGF, DOT formats)",
        "Random framework generation",
        "CLI interface for all operations",
        "Comprehensive unit and advanced testing",
        "Performance benchmarking tools",
        "Enhanced agent with corrections",
        "Real-world case studies",
    ],
    "supported_formats": {
        "json": "JavaScript Object Notation - Primary format",
        "tgf": "Trivial Graph Format - For Gephi/yEd",
        "dot": "GraphViz DOT - Professional rendering",
        "analysis": "JSON analysis reports",
    },
}


def print_project_info():
    """Affiche les informations complètes du projet"""
    print(f"=== {PROJECT_METADATA['name']} ===")
    print(f"Version: {PROJECT_METADATA['version']}")
    print(f"Auteur: {PROJECT_METADATA['author']}")
    print(f"Date de création: {PROJECT_METADATA['creation_date']}")
    print(f"Description: {PROJECT_METADATA['description']}")
    print(f"Python requis: {PROJECT_METADATA['python_version']}")
    print(f"TweetyProject: {PROJECT_METADATA['tweety_version']}")

    print(f"\nSémantiques supportées ({len(PROJECT_METADATA['supported_semantics'])}):")
    for semantic in PROJECT_METADATA["supported_semantics"]:
        print(f"  ✓ {semantic}")

    print(f"\nFormats d'import/export:")
    for fmt, desc in PROJECT_METADATA["supported_formats"].items():
        print(f"  ✓ {fmt.upper()}: {desc}")

    print(f"\nFonctionnalités principales:")
    for feature in PROJECT_METADATA["features"]:
        print(f"  ✓ {feature}")

    print(f"\nDépendances:")
    for dep in PROJECT_METADATA["dependencies"]:
        print(f"  • {dep}")


def get_project_stats():
    """Retourne des statistiques sur le projet"""
    return {
        "total_semantics": len(PROJECT_METADATA["supported_semantics"]),
        "total_formats": len(PROJECT_METADATA["supported_formats"]),
        "total_features": len(PROJECT_METADATA["features"]),
        "total_dependencies": len(PROJECT_METADATA["dependencies"]),
    }


def generate_project_summary():
    """Génère un résumé du projet pour documentation"""
    stats = get_project_stats()

    summary = f"""
# Résumé du Projet

**{PROJECT_METADATA['name']}** v{PROJECT_METADATA['version']}

## Vue d'ensemble
{PROJECT_METADATA['description']}

## Caractéristiques techniques
- **Sémantiques**: {stats['total_semantics']} sémantiques d'argumentation
- **Formats**: {stats['total_formats']} formats d'import/export
- **Fonctionnalités**: {stats['total_features']} fonctionnalités principales
- **Dépendances**: {stats['total_dependencies']} bibliothèques externes

## Architecture
Le projet est organisé autour de plusieurs composants modulaires:
- Agent principal avec cache optimisé
- Agent amélioré avec corrections
- Générateur de frameworks variés
- Utilitaires d'import/export
- Interface CLI complète
- Suite de tests exhaustive

## Cas d'usage
- Recherche en argumentation formelle
- Enseignement des logiques non-monotones
- Validation d'algorithmes d'argumentation
- Benchmarking et tests de performance
- Visualisation de débats structurés
"""

    return summary


if __name__ == "__main__":
    print_project_info()

    print("\n" + "=" * 60)
    print("STATISTIQUES DU PROJET")
    print("=" * 60)

    stats = get_project_stats()
    for key, value in stats.items():
        print(f"{key.replace('_', ' ').title()}: {value}")

    print("\n" + "=" * 60)
    print("RÉSUMÉ GÉNÉRÉ")
    print("=" * 60)
    print(generate_project_summary())
