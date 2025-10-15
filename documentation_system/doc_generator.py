"""
Documentation System - Générateur Automatique de Documentation
===============================================================

Génère automatiquement une documentation structurée et interactive
à partir de l'analyse de l'architecture du projet IA symbolique.

Produit :
- Documentation technique détaillée par module
- Guides d'utilisation par catégorie d'agents
- Tutoriels d'onboarding automatiques
- Diagrammes d'architecture
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from jinja2 import Template, Environment, FileSystemLoader
import markdown


class DocumentationGenerator:
    """Générateur automatique de documentation pour le projet IA symbolique"""

    def __init__(self, analysis_file: str = "project_analysis.json"):
        self.analysis_file = analysis_file
        self.analysis_data = None
        self.output_dir = Path("generated_docs")
        self.templates_dir = Path("doc_templates")

        # Créer les répertoires de sortie
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / "guides").mkdir(exist_ok=True)
        (self.output_dir / "reference").mkdir(exist_ok=True)
        (self.output_dir / "tutorials").mkdir(exist_ok=True)

        self._load_analysis()
        self._setup_templates()

    def _load_analysis(self):
        """Charge les données d'analyse"""
        try:
            with open(self.analysis_file, "r", encoding="utf-8") as f:
                self.analysis_data = json.load(f)
            print(f" Analyse chargée depuis {self.analysis_file}")
        except Exception as e:
            print(f" Erreur lors du chargement de l'analyse: {e}")
            raise

    def _setup_templates(self):
        """Configure le système de templates"""
        # Templates embarqués pour éviter les dépendances externes
        self.templates = {
            "index": self._get_index_template(),
            "module_reference": self._get_module_reference_template(),
            "agent_guide": self._get_agent_guide_template(),
            "tutorial": self._get_tutorial_template(),
            "architecture_overview": self._get_architecture_overview_template(),
        }

    def generate_complete_documentation(self):
        """Génère la documentation complète"""
        print(" Génération de la documentation complète...")

        # 1. Page d'index principale
        self._generate_index_page()

        # 2. Documentation technique par module
        self._generate_module_references()

        # 3. Guides par catégorie d'agents
        self._generate_agent_guides()

        # 4. Tutoriels d'onboarding
        self._generate_tutorials()

        # 5. Vue d'ensemble de l'architecture
        self._generate_architecture_overview()

        # 6. Fichier CSS pour le style
        self._generate_css()

        print(f" Documentation générée dans {self.output_dir}")
        return self.output_dir

    def _generate_index_page(self):
        """Génère la page d'index principale"""
        print(" Génération de la page d'index...")

        template = Template(self.templates["index"])

        # Préparer les données pour la page d'index
        context = {
            "project_name": "Système d'IA Symbolique - Analyse Argumentative",
            "generation_date": datetime.now().strftime("%d/%m/%Y à %H:%M"),
            "metrics": self.analysis_data["metrics"],
            "categories": self._get_category_summary(),
            "entry_points": self.analysis_data["entry_points"],
            "quick_start_modules": self._get_quick_start_modules(),
        }

        output = template.render(**context)

        with open(self.output_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(output)

    def _generate_module_references(self):
        """Génère la documentation de référence pour chaque module"""
        print(" Génération des références de modules...")

        template = Template(self.templates["module_reference"])

        for module_path, module_data in self.analysis_data["modules"].items():
            context = {
                "module": module_data,
                "module_path": module_path,
                "dependencies": self._get_module_dependencies(module_path),
                "dependents": self._get_module_dependents(module_path),
                "examples": self._find_module_examples(module_data),
            }

            output = template.render(**context)

            # Nom de fichier sécurisé
            safe_name = module_path.replace("/", "_").replace(".py", "") + ".html"

            with open(
                self.output_dir / "reference" / safe_name, "w", encoding="utf-8"
            ) as f:
                f.write(output)

    def _generate_agent_guides(self):
        """Génère des guides spécialisés par catégorie d'agents"""
        print(" Génération des guides d'agents...")

        template = Template(self.templates["agent_guide"])

        agent_categories = self.analysis_data["agent_categories"]

        for category, modules in agent_categories.items():
            if category in ["extract", "informal", "logic", "rhetorical"]:
                context = {
                    "category": category,
                    "category_title": self._get_category_title(category),
                    "category_description": self._get_category_description(category),
                    "modules": modules,
                    "usage_examples": self._get_category_examples(category),
                    "best_practices": self._get_category_best_practices(category),
                }

                output = template.render(**context)

                with open(
                    self.output_dir / "guides" / f"{category}_guide.html",
                    "w",
                    encoding="utf-8",
                ) as f:
                    f.write(output)

    def _generate_tutorials(self):
        """Génère des tutoriels d'onboarding automatiques"""
        print(" Génération des tutoriels...")

        template = Template(self.templates["tutorial"])

        tutorials = [
            {
                "name": "getting_started",
                "title": "Démarrage Rapide",
                "description": "Comment commencer avec le système d'IA symbolique",
                "steps": self._generate_getting_started_steps(),
            },
            {
                "name": "agent_development",
                "title": "Développement d'Agents",
                "description": "Guide pour créer de nouveaux agents spécialisés",
                "steps": self._generate_agent_development_steps(),
            },
            {
                "name": "orchestration_usage",
                "title": "Utilisation de l'Orchestration",
                "description": "Comment utiliser le système d'orchestration hiérarchique",
                "steps": self._generate_orchestration_steps(),
            },
        ]

        for tutorial_data in tutorials:
            context = tutorial_data
            output = template.render(**context)

            with open(
                self.output_dir / "tutorials" / f"{tutorial_data['name']}.html",
                "w",
                encoding="utf-8",
            ) as f:
                f.write(output)

    def _generate_architecture_overview(self):
        """Génère une vue d'ensemble de l'architecture"""
        print(" Génération de la vue d'architecture...")

        template = Template(self.templates["architecture_overview"])

        context = {
            "architecture_tree": self.analysis_data["architecture_tree"],
            "dependency_graph": self._build_visual_dependency_graph(),
            "component_overview": self._get_component_overview(),
            "data_flow": self._describe_data_flow(),
        }

        output = template.render(**context)

        with open(self.output_dir / "architecture.html", "w", encoding="utf-8") as f:
            f.write(output)

    def _generate_css(self):
        """Génère le fichier CSS pour le style"""
        css_content = """
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f8f9fa;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            text-align: center;
        }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 2rem 0;
        }
        
        .metric-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: bold;
            color: #667eea;
            display: block;
        }
        
        .category-section {
            background: white;
            margin: 1rem 0;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .module-list {
            list-style: none;
            padding: 0;
        }
        
        .module-list li {
            padding: 0.5rem;
            margin: 0.25rem 0;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            border-radius: 4px;
        }
        
        .code-block {
            background: #f4f4f4;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 1rem;
            overflow-x: auto;
            margin: 1rem 0;
        }
        
        .nav-menu {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        
        .nav-menu a {
            color: #667eea;
            text-decoration: none;
            margin: 0 1rem;
            font-weight: 500;
        }
        
        .nav-menu a:hover {
            text-decoration: underline;
        }
        
        .step {
            background: white;
            margin: 1rem 0;
            padding: 1.5rem;
            border-radius: 8px;
            border-left: 4px solid #28a745;
        }
        
        .dependencies {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            border-radius: 4px;
            padding: 1rem;
            margin: 1rem 0;
        }
        """

        with open(self.output_dir / "style.css", "w", encoding="utf-8") as f:
            f.write(css_content)

    # Méthodes utilitaires pour préparer les données

    def _get_category_summary(self) -> Dict[str, int]:
        """Résumé par catégorie"""
        categories = {}
        for category, modules in self.analysis_data["agent_categories"].items():
            categories[category] = len(modules)
        return categories

    def _get_quick_start_modules(self) -> List[Dict]:
        """Modules recommandés pour démarrer"""
        entry_points = self.analysis_data["entry_points"]
        return sorted(entry_points, key=lambda x: x["name"])[:5]

    def _get_module_dependencies(self, module_path: str) -> List[str]:
        """Dépendances d'un module"""
        return self.analysis_data["dependency_graph"].get(module_path, [])

    def _get_module_dependents(self, module_path: str) -> List[str]:
        """Modules qui dépendent de ce module"""
        dependents = []
        for path, deps in self.analysis_data["dependency_graph"].items():
            if module_path in deps:
                dependents.append(path)
        return dependents

    def _find_module_examples(self, module_data: Dict) -> List[str]:
        """Trouve des exemples d'utilisation pour un module"""
        examples = []

        # Logique simple pour proposer des exemples
        if module_data["category"] == "extract":
            examples.append("Extraction de segments argumentatifs depuis un texte")
        elif module_data["category"] == "informal":
            examples.append("Détection de sophismes dans un discours")
        elif module_data["category"] == "logic":
            examples.append("Raisonnement logique avec TweetyProject")

        return examples

    def _get_category_title(self, category: str) -> str:
        """Titre formaté pour une catégorie"""
        titles = {
            "extract": "Agents d'Extraction",
            "informal": "Agents d'Analyse Informelle",
            "logic": "Agents de Logique Formelle",
            "rhetorical": "Outils d'Analyse Rhétorique",
        }
        return titles.get(category, category.title())

    def _get_category_description(self, category: str) -> str:
        """Description d'une catégorie"""
        descriptions = {
            "extract": "Ces agents sont spécialisés dans l'extraction automatique de segments argumentatifs depuis des textes.",
            "informal": "Ces agents analysent les arguments de manière informelle, détectant les sophismes et biais cognitifs.",
            "logic": "Ces agents utilisent la logique formelle pour le raisonnement symbolique et la validation d'arguments.",
            "rhetorical": "Ces outils fournissent des analyses avancées de la structure rhétorique et de la qualité argumentative.",
        }
        return descriptions.get(category, f"Modules de la catégorie {category}")

    def _get_category_examples(self, category: str) -> List[str]:
        """Exemples d'utilisation par catégorie"""
        examples = {
            "extract": [
                "text_extractor.extract_arguments(discourse_text)",
                "segments = extract_agent.find_markers(political_speech)",
            ],
            "informal": [
                "fallacies = informal_agent.detect_fallacies(argument_text)",
                "bias_score = informal_agent.evaluate_bias(statement)",
            ],
            "logic": [
                "proof = logic_agent.prove_theorem(premises, conclusion)",
                "consistent = logic_agent.check_consistency(belief_set)",
            ],
        }
        return examples.get(category, [])

    def _get_category_best_practices(self, category: str) -> List[str]:
        """Bonnes pratiques par catégorie"""
        practices = {
            "extract": [
                "Valider les marqueurs d'extraction avant traitement",
                "Utiliser des templates adaptés au type de discours",
            ],
            "informal": [
                "Combiner plusieurs heuristiques pour la détection",
                "Valider les résultats avec des experts humains",
            ],
            "logic": [
                "Vérifier la cohérence des bases de connaissances",
                "Optimiser les requêtes pour de meilleures performances",
            ],
        }
        return practices.get(category, [])

    def _generate_getting_started_steps(self) -> List[Dict]:
        """Étapes pour démarrer"""
        return [
            {
                "title": "Installation des dépendances",
                "description": "Installer les bibliothèques requises",
                "code": "pip install -r requirements.txt",
            },
            {
                "title": "Initialisation du projet",
                "description": "Configurer l'environnement de base",
                "code": "python setup_env.py",
            },
            {
                "title": "Premier test",
                "description": "Exécuter un exemple simple",
                "code": "python examples/simple_analysis.py",
            },
        ]

    def _generate_agent_development_steps(self) -> List[Dict]:
        """Étapes pour développer un agent"""
        return [
            {
                "title": "Créer la structure de base",
                "description": "Utiliser le template d'agent",
                "code": "cp -r agents/templates/student_template agents/my_agent",
            },
            {
                "title": "Implémenter la logique",
                "description": "Modifier agent.py avec votre logique",
                "code": "# Voir le guide détaillé dans agent.py",
            },
            {
                "title": "Tester l'agent",
                "description": "Créer des tests unitaires",
                "code": "python -m pytest tests/test_my_agent.py",
            },
        ]

    def _generate_orchestration_steps(self) -> List[Dict]:
        """Étapes pour l'orchestration"""
        return [
            {
                "title": "Comprendre la hiérarchie",
                "description": "Trois niveaux : Strategic, Tactical, Operational",
                "code": "# Voir documentation architecture",
            },
            {
                "title": "Configurer une tâche",
                "description": "Définir le workflow d'analyse",
                "code": "task = AnalysisTask(...); orchestrator.execute(task)",
            },
        ]

    def _build_visual_dependency_graph(self) -> str:
        """Construit une représentation visuelle du graphe de dépendances"""
        # Version simplifiée pour l'exemple
        return "Graphique de dépendances (à implémenter avec D3.js ou similar)"

    def _get_component_overview(self) -> Dict:
        """Vue d'ensemble des composants"""
        return {
            "agents": len(
                [
                    m
                    for m in self.analysis_data["modules"].values()
                    if m["type"] == "agent"
                ]
            ),
            "orchestration": len(
                [
                    m
                    for m in self.analysis_data["modules"].values()
                    if m["type"] == "orchestration"
                ]
            ),
            "tools": len(
                [
                    m
                    for m in self.analysis_data["modules"].values()
                    if m["type"] == "tool"
                ]
            ),
        }

    def _describe_data_flow(self) -> List[str]:
        """Décrit le flux de données général"""
        return [
            "1. Entrée de texte → Agents d'extraction",
            "2. Segments extraits → Agents d'analyse informelle",
            "3. Arguments structurés → Agents de logique formelle",
            "4. Résultats consolidés → Outils de visualisation",
        ]

    # Templates embarqués

    def _get_index_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{{ project_name }} - Documentation</title>
            <link rel="stylesheet" href="style.css">
        </head>
        <body>
            <div class="header">
                <h1>{{ project_name }}</h1>
                <p>Documentation technique générée automatiquement</p>
                <p><small>Généré le {{ generation_date }}</small></p>
            </div>
            
            <nav class="nav-menu">
                <a href="index.html">🏠 Accueil</a>
                <a href="architecture.html">🏗️ Architecture</a>
                <a href="guides/">📚 Guides</a>
                <a href="tutorials/">📖 Tutoriels</a>
                <a href="reference/">📋 Référence</a>
            </nav>
            
            <div class="metrics-grid">
                <div class="metric-card">
                    <span class="metric-value">{{ metrics.total_modules }}</span>
                    <div>Modules Total</div>
                </div>
                <div class="metric-card">
                    <span class="metric-value">{{ metrics.agents_count }}</span>
                    <div>Agents IA</div>
                </div>
                <div class="metric-card">
                    <span class="metric-value">{{ metrics.tools_count }}</span>
                    <div>Outils d'Analyse</div>
                </div>
                <div class="metric-card">
                    <span class="metric-value">{{ metrics.entry_points_count }}</span>
                    <div>Points d'Entrée</div>
                </div>
            </div>
            
            <div class="category-section">
                <h2>🎯 Démarrage Rapide</h2>
                <p>Voici les modules recommandés pour commencer :</p>
                <ul class="module-list">
                {% for module in quick_start_modules %}
                    <li>
                        <strong>{{ module.name }}</strong> ({{ module.category }})
                        {% if module.docstring %}
                        <br><small>{{ module.docstring[:100] }}...</small>
                        {% endif %}
                    </li>
                {% endfor %}
                </ul>
            </div>
            
            <div class="category-section">
                <h2>📊 Répartition par Catégories</h2>
                {% for category, count in categories.items() %}
                <p><strong>{{ category|title }}</strong>: {{ count }} module(s)</p>
                {% endfor %}
            </div>
            
            <div class="category-section">
                <h2>🚀 Prochaines Étapes</h2>
                <ol>
                    <li><a href="tutorials/getting_started.html">📖 Guide de démarrage</a></li>
                    <li><a href="guides/extract_guide.html">🤖 Utiliser les agents d'extraction</a></li>
                    <li><a href="architecture.html">🏗️ Comprendre l'architecture</a></li>
                    <li><a href="tutorials/agent_development.html">⚙️ Développer un nouvel agent</a></li>
                </ol>
            </div>
        </body>
        </html>
        """

    def _get_module_reference_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <title>{{ module.name }} - Référence</title>
            <link rel="stylesheet" href="../style.css">
        </head>
        <body>
            <div class="header">
                <h1>📄 {{ module.name }}</h1>
                <p>{{ module.type|title }} - Catégorie: {{ module.category|title }}</p>
            </div>
            
            <nav class="nav-menu">
                <a href="../index.html">🏠 Accueil</a>
                <a href="../reference/">📋 Référence</a>
            </nav>
            
            {% if module.docstring %}
            <div class="category-section">
                <h2>📝 Description</h2>
                <p>{{ module.docstring }}</p>
            </div>
            {% endif %}
            
            <div class="category-section">
                <h2>ℹ️ Informations</h2>
                <ul>
                    <li><strong>Chemin:</strong> {{ module_path }}</li>
                    <li><strong>Type:</strong> {{ module.type }}</li>
                    <li><strong>Catégorie:</strong> {{ module.category }}</li>
                    <li><strong>Complexité:</strong> {{ module.complexity_score }}</li>
                </ul>
            </div>
            
            {% if module.classes %}
            <div class="category-section">
                <h2>🏗️ Classes</h2>
                <ul class="module-list">
                {% for class_name in module.classes %}
                    <li>{{ class_name }}</li>
                {% endfor %}
                </ul>
            </div>
            {% endif %}
            
            {% if module.functions %}
            <div class="category-section">
                <h2>⚙️ Fonctions</h2>
                <ul class="module-list">
                {% for func_name in module.functions %}
                    <li>{{ func_name }}</li>
                {% endfor %}
                </ul>
            </div>
            {% endif %}
            
            {% if dependencies %}
            <div class="dependencies">
                <h3>🔗 Dépendances</h3>
                <ul>
                {% for dep in dependencies %}
                    <li>{{ dep }}</li>
                {% endfor %}
                </ul>
            </div>
            {% endif %}
            
            {% if examples %}
            <div class="category-section">
                <h2>💡 Exemples d'utilisation</h2>
                {% for example in examples %}
                <p>{{ example }}</p>
                {% endfor %}
            </div>
            {% endif %}
        </body>
        </html>
        """

    def _get_agent_guide_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <title>{{ category_title }} - Guide</title>
            <link rel="stylesheet" href="../style.css">
        </head>
        <body>
            <div class="header">
                <h1>🤖 {{ category_title }}</h1>
                <p>{{ category_description }}</p>
            </div>
            
            <nav class="nav-menu">
                <a href="../index.html">🏠 Accueil</a>
                <a href="../guides/">📚 Guides</a>
            </nav>
            
            <div class="category-section">
                <h2>📋 Modules Disponibles</h2>
                <ul class="module-list">
                {% for module in modules %}
                    <li>
                        <strong>{{ module.name }}</strong>
                        <small>(Complexité: {{ module.complexity }})</small>
                    </li>
                {% endfor %}
                </ul>
            </div>
            
            {% if usage_examples %}
            <div class="category-section">
                <h2>💻 Exemples d'Utilisation</h2>
                {% for example in usage_examples %}
                <div class="code-block">{{ example }}</div>
                {% endfor %}
            </div>
            {% endif %}
            
            {% if best_practices %}
            <div class="category-section">
                <h2>✅ Bonnes Pratiques</h2>
                <ul>
                {% for practice in best_practices %}
                    <li>{{ practice }}</li>
                {% endfor %}
                </ul>
            </div>
            {% endif %}
        </body>
        </html>
        """

    def _get_tutorial_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <title>{{ title }} - Tutoriel</title>
            <link rel="stylesheet" href="../style.css">
        </head>
        <body>
            <div class="header">
                <h1>📖 {{ title }}</h1>
                <p>{{ description }}</p>
            </div>
            
            <nav class="nav-menu">
                <a href="../index.html">🏠 Accueil</a>
                <a href="../tutorials/">📖 Tutoriels</a>
            </nav>
            
            {% for step in steps %}
            <div class="step">
                <h3>{{ loop.index }}. {{ step.title }}</h3>
                <p>{{ step.description }}</p>
                {% if step.code %}
                <div class="code-block">{{ step.code }}</div>
                {% endif %}
            </div>
            {% endfor %}
        </body>
        </html>
        """

    def _get_architecture_overview_template(self) -> str:
        return """
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <title>Architecture - Vue d'ensemble</title>
            <link rel="stylesheet" href="style.css">
        </head>
        <body>
            <div class="header">
                <h1>🏗️ Architecture du Système</h1>
                <p>Vue d'ensemble de l'architecture d'IA symbolique</p>
            </div>
            
            <nav class="nav-menu">
                <a href="index.html">🏠 Accueil</a>
                <a href="architecture.html">🏗️ Architecture</a>
            </nav>
            
            <div class="category-section">
                <h2>📊 Vue d'ensemble des Composants</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <span class="metric-value">{{ component_overview.agents }}</span>
                        <div>Agents IA</div>
                    </div>
                    <div class="metric-card">
                        <span class="metric-value">{{ component_overview.orchestration }}</span>
                        <div>Orchestration</div>
                    </div>
                    <div class="metric-card">
                        <span class="metric-value">{{ component_overview.tools }}</span>
                        <div>Outils</div>
                    </div>
                </div>
            </div>
            
            <div class="category-section">
                <h2>🔄 Flux de Données</h2>
                <ol>
                {% for flow_step in data_flow %}
                    <li>{{ flow_step }}</li>
                {% endfor %}
                </ol>
            </div>
            
            <div class="category-section">
                <h2>🗂️ Structure du Projet</h2>
                <div class="code-block">
                {{ architecture_tree | pprint }}
                </div>
            </div>
            
            <div class="category-section">
                <h2>🔗 Graphe de Dépendances</h2>
                <p>{{ dependency_graph }}</p>
                <p><em>Note: Implémentation complète avec D3.js recommandée pour la visualisation interactive</em></p>
            </div>
        </body>
        </html>
        """


def main():
    """Fonction principale"""
    print("📚 Générateur de Documentation IA Symbolique")
    print("=" * 50)

    try:
        generator = DocumentationGenerator()
        output_dir = generator.generate_complete_documentation()

        print(f"\n Documentation générée avec succès !")
        print(f" Consultez: {output_dir}/index.html")
        print(f" Ouvrez dans votre navigateur pour voir le résultat")

    except Exception as e:
        print(f"❌ Erreur: {e}")


if __name__ == "__main__":
    main()
