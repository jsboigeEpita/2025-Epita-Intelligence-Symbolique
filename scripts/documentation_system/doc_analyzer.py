"""
Documentation System - Analyseur Intelligent d'Architecture
===========================================================

Analyse automatiquement l'architecture du projet d'IA symbolique et extrait
les informations nécessaires pour générer une documentation structurée.

Spécialement conçu pour comprendre :
- Les agents spécialisés (extract, informal, logic, pm)
- L'orchestration hiérarchique (strategic, tactical, operational)
- Les outils d'analyse rhétorique
- Les flux de données et dépendances
"""

import os
import ast
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict
import importlib.util


@dataclass
class ModuleInfo:
    """Information extraite d'un module Python"""

    path: str
    name: str
    type: str  # 'agent', 'tool', 'orchestration', 'core', 'service', etc.
    category: str  # 'extract', 'informal', 'logic', 'rhetorical', etc.
    docstring: Optional[str] = None
    classes: List[str] = None
    functions: List[str] = None
    dependencies: Set[str] = None
    complexity_score: int = 0
    is_entry_point: bool = False

    def __post_init__(self):
        if self.classes is None:
            self.classes = []
        if self.functions is None:
            self.functions = []
        if self.dependencies is None:
            self.dependencies = set()


class ProjectArchitectureAnalyzer:
    """Analyseur intelligent de l'architecture du projet IA symbolique"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.modules: Dict[str, ModuleInfo] = {}
        self.architecture_tree = {}
        self.agent_patterns = {
            "extract": ["extract_agent", "extract_definitions", "extract"],
            "informal": ["informal_agent", "informal_definitions", "informal"],
            "logic": ["logic_agent", "propositional", "modal", "first_order", "tweety"],
            "pm": ["pm_agent", "pm_definitions"],
            "rhetorical": ["fallacy", "rhetorical", "sophisme", "argument"],
        }
        self.orchestration_levels = ["strategic", "tactical", "operational"]

    def analyze_full_project(self) -> Dict:
        """Analyse complète du projet"""
        print(" Démarrage de l'analyse du projet IA symbolique...")

        # 1. Scanner l'architecture générale
        self._scan_directory_structure()

        # 2. Analyser les modules Python
        self._analyze_python_modules()

        # 3. Détecter les patterns spécialisés
        self._detect_agent_patterns()

        # 4. Analyser les dépendances
        self._analyze_dependencies()

        # 5. Identifier les points d'entrée
        self._identify_entry_points()

        # 6. Calculer les métriques
        self._calculate_metrics()

        print(f" Analyse terminée : {len(self.modules)} modules analysés")

        return self._generate_analysis_report()

    def _scan_directory_structure(self):
        """Scanne la structure des répertoires pour comprendre l'organisation"""
        print(" Analyse de la structure des répertoires...")

        important_dirs = {
            "argumentation_analysis": "core",
            "agents": "agents",
            "orchestration": "orchestration",
            "tools": "tools",
            "examples": "examples",
            "tests": "tests",
            "docs": "documentation",
        }

        for dir_path in self.project_root.rglob("*"):
            if dir_path.is_dir() and not dir_path.name.startswith("."):
                rel_path = str(dir_path.relative_to(self.project_root))

                # Construire l'arbre d'architecture
                parts = rel_path.split(os.sep)
                current = self.architecture_tree
                for part in parts:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

    def _analyze_python_modules(self):
        """Analyse tous les modules Python du projet"""
        print(" Analyse des modules Python...")

        for py_file in self.project_root.rglob("*.py"):
            if self._should_analyze_file(py_file):
                try:
                    module_info = self._analyze_single_module(py_file)
                    if module_info:
                        self.modules[str(py_file.relative_to(self.project_root))] = (
                            module_info
                        )
                except Exception as e:
                    print(f" Erreur lors de l'analyse de {py_file}: {e}")

    def _should_analyze_file(self, file_path: Path) -> bool:
        """Détermine si un fichier doit être analysé"""
        # Ignorer certains répertoires
        ignore_dirs = {"__pycache__", ".git", "build", "dist", "_archives"}

        for part in file_path.parts:
            if part in ignore_dirs:
                return False

        # Ignorer les fichiers de test pour l'instant (on les analysera séparément)
        if "test_" in file_path.name and not file_path.parent.name == "tests":
            return False

        return True

    def _analyze_single_module(self, file_path: Path) -> Optional[ModuleInfo]:
        """Analyse un seul module Python"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parser AST
            tree = ast.parse(content)

            # Extraire les informations
            module_info = ModuleInfo(
                path=str(file_path.relative_to(self.project_root)),
                name=file_path.stem,
                type=self._determine_module_type(file_path),
                category=self._determine_module_category(file_path),
                docstring=ast.get_docstring(tree),
                complexity_score=self._calculate_complexity(tree),
            )

            # Extraire classes et fonctions
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    module_info.classes.append(node.name)
                elif isinstance(node, ast.FunctionDef) and not node.name.startswith(
                    "_"
                ):
                    module_info.functions.append(node.name)

            return module_info

        except Exception as e:
            print(f"Erreur lors de l'analyse de {file_path}: {e}")
            return None

    def _determine_module_type(self, file_path: Path) -> str:
        """Détermine le type d'un module basé sur son chemin"""
        path_str = str(file_path).lower()

        if "agents" in path_str:
            return "agent"
        elif "orchestration" in path_str:
            return "orchestration"
        elif "tools" in path_str:
            return "tool"
        elif "service" in path_str:
            return "service"
        elif "test" in path_str:
            return "test"
        elif "example" in path_str:
            return "example"
        elif "core" in path_str:
            return "core"
        elif "ui" in path_str:
            return "interface"
        else:
            return "utility"

    def _determine_module_category(self, file_path: Path) -> str:
        """Détermine la catégorie spécialisée d'un module"""
        path_str = str(file_path).lower()
        name = file_path.stem.lower()

        # Agents spécialisés
        for category, patterns in self.agent_patterns.items():
            if any(pattern in path_str or pattern in name for pattern in patterns):
                return category

        # Niveaux d'orchestration
        for level in self.orchestration_levels:
            if level in path_str:
                return level

        # Autres catégories
        if any(word in path_str for word in ["communication", "channel", "message"]):
            return "communication"
        elif any(word in path_str for word in ["analysis", "analyzer"]):
            return "analysis"
        elif any(word in path_str for word in ["pipeline", "workflow"]):
            return "pipeline"

        return "general"

    def _detect_agent_patterns(self):
        """Détecte les patterns spécifiques aux agents d'IA symbolique"""
        print(" Détection des patterns d'agents spécialisés...")

        agent_groups = defaultdict(list)

        for path, module in self.modules.items():
            if module.type == "agent":
                agent_groups[module.category].append(module)

        # Analyser chaque groupe d'agents
        for category, agents in agent_groups.items():
            print(f"    Catégorie '{category}': {len(agents)} module(s)")

    def _analyze_dependencies(self):
        """Analyse les dépendances entre modules"""
        print(" Analyse des dépendances...")

        for path, module in self.modules.items():
            try:
                file_path = self.project_root / path
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extraire les imports
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self._add_dependency(module, alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            self._add_dependency(module, node.module)

            except Exception as e:
                print(f"Erreur dépendances pour {path}: {e}")

    def _add_dependency(self, module: ModuleInfo, dep_name: str):
        """Ajoute une dépendance si elle fait partie du projet"""
        # Garder seulement les dépendances internes au projet
        internal_prefixes = [
            "argumentation_analysis",
            "agents",
            "orchestration",
            "tools",
            "core",
        ]

        if any(dep_name.startswith(prefix) for prefix in internal_prefixes):
            module.dependencies.add(dep_name)

    def _identify_entry_points(self):
        """Identifie les points d'entrée principaux du projet"""
        print(" Identification des points d'entrée...")

        entry_point_indicators = [
            "main",
            "run_",
            "start_",
            "launch_",
            "orchestrator",
            "app.py",
            "main_",
        ]

        for path, module in self.modules.items():
            name_lower = module.name.lower()
            if any(indicator in name_lower for indicator in entry_point_indicators):
                module.is_entry_point = True
                print(f"    Point d'entrée détecté: {module.name}")

    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calcule un score de complexité simple pour un module"""
        complexity = 0

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                complexity += 5
            elif isinstance(node, ast.FunctionDef):
                complexity += 3
            elif isinstance(node, ast.If):
                complexity += 1
            elif isinstance(node, ast.For):
                complexity += 2
            elif isinstance(node, ast.While):
                complexity += 2

        return complexity

    def _calculate_metrics(self):
        """Calcule des métriques générales du projet"""
        print(" Calcul des métriques...")

        self.metrics = {
            "total_modules": len(self.modules),
            "agents_count": len(
                [m for m in self.modules.values() if m.type == "agent"]
            ),
            "tools_count": len([m for m in self.modules.values() if m.type == "tool"]),
            "orchestration_count": len(
                [m for m in self.modules.values() if m.type == "orchestration"]
            ),
            "entry_points_count": len(
                [m for m in self.modules.values() if m.is_entry_point]
            ),
            "avg_complexity": (
                sum(m.complexity_score for m in self.modules.values())
                / len(self.modules)
                if self.modules
                else 0
            ),
            "categories": list(set(m.category for m in self.modules.values())),
            "types": list(set(m.type for m in self.modules.values())),
        }

    def _generate_analysis_report(self) -> Dict:
        """Génère le rapport d'analyse complet"""
        return {
            "metadata": {
                "project_root": str(self.project_root),
                "analysis_date": str(Path().cwd()),
                "total_modules_analyzed": len(self.modules),
            },
            "architecture_tree": self.architecture_tree,
            "modules": {path: asdict(module) for path, module in self.modules.items()},
            "metrics": self.metrics,
            "agent_categories": self._group_by_category(),
            "dependency_graph": self._build_dependency_graph(),
            "entry_points": self._get_entry_points_info(),
        }

    def _group_by_category(self) -> Dict[str, List[str]]:
        """Groupe les modules par catégorie"""
        categories = defaultdict(list)
        for path, module in self.modules.items():
            categories[module.category].append(
                {
                    "path": path,
                    "name": module.name,
                    "type": module.type,
                    "complexity": module.complexity_score,
                }
            )
        return dict(categories)

    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """Construit le graphe de dépendances"""
        graph = {}
        for path, module in self.modules.items():
            graph[path] = list(module.dependencies)
        return graph

    def _get_entry_points_info(self) -> List[Dict]:
        """Récupère les informations sur les points d'entrée"""
        entry_points = []
        for path, module in self.modules.items():
            if module.is_entry_point:
                entry_points.append(
                    {
                        "path": path,
                        "name": module.name,
                        "category": module.category,
                        "type": module.type,
                        "docstring": module.docstring,
                    }
                )
        return entry_points

    def save_analysis(self, output_file: str = "project_analysis.json"):
        """Sauvegarde l'analyse dans un fichier JSON"""
        analysis = self._generate_analysis_report()

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False, default=str)

        print(f" Analyse sauvegardée dans {output_file}")
        return output_file


def main():
    """Fonction principale pour tester l'analyseur"""
    import sys

    # Utiliser le répertoire courant ou celui passé en argument
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."

    print(" Analyse du Projet IA Symbolique")
    print("=" * 50)

    analyzer = ProjectArchitectureAnalyzer(project_root)
    analysis = analyzer.analyze_full_project()

    # Afficher un résumé
    print("\n RÉSUMÉ DE L'ANALYSE")
    print("=" * 30)
    print(f" Modules analysés: {analysis['metadata']['total_modules_analyzed']}")
    print(f" Agents détectés: {analysis['metrics']['agents_count']}")
    print(f" Outils détectés: {analysis['metrics']['tools_count']}")
    print(f" Orchestration: {analysis['metrics']['orchestration_count']}")
    print(f" Points d'entrée: {analysis['metrics']['entry_points_count']}")
    print(f" Complexité moyenne: {analysis['metrics']['avg_complexity']:.1f}")

    print(f"\n Catégories détectées: {', '.join(analysis['metrics']['categories'])}")

    # Sauvegarder
    analyzer.save_analysis()

    print("\n Analyse terminée avec succès!")


if __name__ == "__main__":
    main()
