#!/usr/bin/env python3
"""
Script de Démarrage du Système de Documentation IA Symbolique
==============================================================

Ce script lance automatiquement toute la chaîne de traitement :
1. Analyse de l'architecture du projet
2. Génération de la carte des connaissances
3. Création de la documentation HTML
4. Lancement de l'interface interactive

Usage : python start_system.py [options]
"""

import os
import sys
import time
import subprocess
import webbrowser
from pathlib import Path
from typing import Optional


class DocumentationSystemStarter:
    """Gestionnaire de démarrage du système de documentation"""

    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).absolute()
        self.system_dir = self.project_root / "documentation_system"
        self.output_files = {
            "analysis": "project_analysis.json",
            "knowledge": "knowledge_summary.json",
            "docs": "generated_docs",
            "map": "knowledge_map.html",
        }

    def check_requirements(self) -> bool:
        """Vérifie que tous les fichiers nécessaires sont présents"""
        print(" Vérification des prérequis...")

        required_files = [
            "doc_analyzer.py",
            "doc_generator.py",
            "knowledge_mapper.py",
            "interactive_guide.py",
        ]

        missing_files = []
        for file in required_files:
            if not (self.system_dir / file).exists():
                missing_files.append(file)

        if missing_files:
            print(f"❌ Fichiers manquants dans {self.system_dir}:")
            for file in missing_files:
                print(f"   - {file}")
            return False

        print("Tous les fichiers système sont présents")
        return True

    def _skip_interface_step(self):
        print("    knowledge_map.html")
        print("    generated_docs/index.html")
        print("    project_analysis.json")
        return True

    def check_dependencies(self) -> bool:
        """Vérifie les dépendances Python"""
        print(" Vérification des dépendances Python...")

        required_modules = [
            ("ast", "Module Python standard"),
            ("json", "Module Python standard"),
            ("pathlib", "Module Python standard"),
            ("networkx", "pip install networkx"),
        ]

        optional_modules = [
            ("flask", "pip install flask (pour interface web)"),
            ("jinja2", "pip install jinja2 (pour templates)"),
        ]

        missing_required = []
        missing_optional = []

        for module, install_cmd in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_required.append((module, install_cmd))

        for module, install_cmd in optional_modules:
            try:
                __import__(module)
            except ImportError:
                missing_optional.append((module, install_cmd))

        if missing_required:
            print(" Dépendances requises manquantes:")
            for module, cmd in missing_required:
                print(f"   - {module}: {cmd}")
            return False

        if missing_optional:
            print(" Dépendances optionnelles manquantes:")
            for module, cmd in missing_optional:
                print(f"   - {module}: {cmd}")
            print("   → Interface statique HTML sera utilisée")

        print(" Dépendances essentielles disponibles")
        return True

    def run_analysis(self) -> bool:
        """Lance l'analyse du projet"""
        print(" Étape 1/3 : Analyse de l'architecture du projet...")

        try:
            os.chdir(self.project_root)

            # Importer et lancer l'analyseur
            sys.path.insert(0, str(self.system_dir))
            from doc_analyzer import ProjectArchitectureAnalyzer

            analyzer = ProjectArchitectureAnalyzer(".")
            analysis = analyzer.analyze_full_project()
            analyzer.save_analysis(self.output_files["analysis"])

            print(
                f" Analyse terminée : {analysis['metadata']['total_modules_analyzed']} modules"
            )
            return True

        except Exception as e:
            print(f"❌ Erreur lors de l'analyse : {e}")
            return False

    def run_knowledge_mapping(self) -> bool:
        """Lance la génération de la carte des connaissances"""
        print(" Étape 2/3 : Génération de la carte des connaissances...")

        try:
            from knowledge_mapper import KnowledgeMapper

            mapper = KnowledgeMapper(self.output_files["analysis"])
            learning_paths = mapper.generate_learning_paths()
            mapper.export_interactive_map(self.output_files["map"])
            mapper.export_knowledge_summary(self.output_files["knowledge"])

            print(f" Carte générée : {len(learning_paths)} parcours d'apprentissage")
            return True

        except Exception as e:
            print(f" Erreur lors du mapping : {e}")
            return False

    def run_documentation_generation(self) -> bool:
        """Lance la génération de la documentation"""
        print(" Étape 3/3 : Génération de la documentation HTML...")

        try:
            from doc_generator import DocumentationGenerator

            generator = DocumentationGenerator(self.output_files["analysis"])
            output_dir = generator.generate_complete_documentation()

            print(f" Documentation générée dans : {output_dir}")
            return True

        except Exception as e:
            print(f"❌ Erreur lors de la génération : {e}")
            return False

    def run_interactive_interface(self, mode: str = "auto") -> bool:
        """Lance l'interface interactive"""
        print("🌐 Étape 4/4 : Lancement de l'interface interactive...")

        try:
            from interactive_guide import InteractiveDocumentationGuide, FLASK_AVAILABLE

            guide = InteractiveDocumentationGuide(
                self.output_files["analysis"], self.output_files["knowledge"]
            )

            if mode == "static" or not FLASK_AVAILABLE:
                print(" Mode interface statique")
                static_file = guide.generate_static_interface()

                # Ouvrir dans le navigateur
                try:
                    webbrowser.open(f"file://{static_file.absolute()}")
                    print(f" Interface ouverte : {static_file}")
                except Exception as e:
                    print(f" Ouverture manuelle requise : {static_file}")

                return True

            elif mode == "server" or mode == "auto":
                print(" Mode serveur Flask interacti")
                print(" L'interface s'ouvrira sur http://localhost:5000")
                print(" Appuyez sur Ctrl+C pour arrêter\n")

                guide.run_interactive_server(debug=False)
                return True

        except KeyboardInterrupt:
            print("\n Interface arrêtée par l'utilisateur")
            return True
        except Exception as e:
            print(f" Erreur lors de l'interface : {e}")
            return False

    def cleanup_old_files(self):
        """Nettoie les anciens fichiers générés"""
        print("🧹 Nettoyage des anciens fichiers...")

        for file_key, file_path in self.output_files.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                if full_path.is_file():
                    full_path.unlink()
                    print(f"    Supprimé : {file_path}")
                elif full_path.is_dir():
                    import shutil

                    shutil.rmtree(full_path)
                    print(f"    Supprimé : {file_path}/")

    def run_complete_workflow(self, mode: str = "auto", clean: bool = False) -> bool:
        """Lance le workflow complet"""
        print(" SYSTÈME DE DOCUMENTATION IA SYMBOLIQUE")
        print("=" * 50)
        print(f" Projet : {self.project_root}")
        print(f" Mode : {mode}")

        if clean:
            self.cleanup_old_files()

        # Vérifications préliminaires
        if not self.check_requirements():
            return False

        if not self.check_dependencies():
            return False

        print("\n Démarrage du processus de génération...")

        # Workflow principal
        steps = [
            ("Analyse", self.run_analysis),
            ("Mapping", self.run_knowledge_mapping),
            ("Documentation", self.run_documentation_generation),
            ("Interface", lambda: self._skip_interface_step()),
        ]

        start_time = time.time()

        for step_name, step_func in steps:
            step_start = time.time()

            if not step_func():
                print(f"\n Échec à l'étape : {step_name}")
                return False

            step_duration = time.time() - step_start
            print(f"    Durée : {step_duration:.1f}s\n")

        total_duration = time.time() - start_time

        print(" GÉNÉRATION TERMINÉE AVEC SUCCÈS !")
        print(f" Durée totale : {total_duration:.1f}s")
        print("\n Fichiers générés :")

        for file_key, file_path in self.output_files.items():
            full_path = self.project_root / file_path
            if full_path.exists():
                if full_path.is_file():
                    size = full_path.stat().st_size
                    print(f"    {file_path} ({size:,} octets)")
                else:
                    print(f"    {file_path}/ (dossier)")
            else:
                print(f"   ⚠️ {file_path} (non généré)")

        return True


def main():
    """Fonction principale avec gestion des arguments"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Système de Documentation Automatique IA Symbolique",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation :
  python start_system.py                    # Mode automatique
  python start_system.py --mode server     # Serveur Flask obligatoire
  python start_system.py --mode static     # Interface HTML statique
  python start_system.py --clean           # Nettoyer avant génération
  python start_system.py --project ../     # Projet dans dossier parent
        """,
    )

    parser.add_argument(
        "--mode",
        choices=["auto", "server", "static"],
        default="auto",
        help="Mode d'interface (auto=détection automatique, server=Flask, static=HTML)",
    )

    parser.add_argument(
        "--project",
        default=".",
        help="Chemin vers le projet à analyser (défaut: répertoire courant)",
    )

    parser.add_argument(
        "--clean",
        action="store_true",
        help="Nettoyer les anciens fichiers avant génération",
    )

    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Vérifier seulement les prérequis sans lancer la génération",
    )

    args = parser.parse_args()

    # Créer le gestionnaire
    starter = DocumentationSystemStarter(args.project)

    # Mode vérification seulement
    if args.check_only:
        print("🔍 VÉRIFICATION DES PRÉREQUIS UNIQUEMENT")
        print("=" * 40)

        req_ok = starter.check_requirements()
        dep_ok = starter.check_dependencies()

        if req_ok and dep_ok:
            print("\n✅ Système prêt à fonctionner !")
            sys.exit(0)
        else:
            print("\n❌ Problèmes détectés - corrigez avant utilisation")
            sys.exit(1)

    # Workflow complet
    success = starter.run_complete_workflow(mode=args.mode, clean=args.clean)

    if success:
        print("\nProjet : Documentation et transfert de connaissances")
        print("EPITA 2025 - IA Symbolique")
        sys.exit(0)
    else:
        print("\n❌ Génération échouée - consultez les erreurs ci-dessus")
        sys.exit(1)


if __name__ == "__main__":
    main()
