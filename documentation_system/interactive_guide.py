"""
Documentation System - Interface Web Interactive (VERSION CORRIGÉE)
===================================================================

Version corrigée du fichier interactive_guide.py sans problèmes de f-string
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import webbrowser

try:
    from flask import (
        Flask,
        render_template_string,
        request,
        jsonify,
        redirect,
        url_for,
        session,
    )

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print(" Flask non disponible. Utilisation du mode HTML statique.")


class InteractiveDocumentationGuide:
    """Interface interactive pour la documentation IA symbolique"""

    def __init__(
        self,
        analysis_file: str = "project_analysis.json",
        knowledge_summary_file: str = "knowledge_summary.json",
    ):
        self.analysis_file = analysis_file
        self.knowledge_summary_file = knowledge_summary_file
        self.analysis_data = None
        self.knowledge_data = None
        self.app = None
        self.docs_dir = Path("generated_docs")
        self.static_mode = not FLASK_AVAILABLE

        self._load_data()
        if FLASK_AVAILABLE:
            self._setup_flask_app()

    def _load_data(self):
        """Charge les données d'analyse et de connaissances"""
        try:
            with open(self.analysis_file, "r", encoding="utf-8") as f:
                self.analysis_data = json.load(f)

            if os.path.exists(self.knowledge_summary_file):
                with open(self.knowledge_summary_file, "r", encoding="utf-8") as f:
                    self.knowledge_data = json.load(f)

            print(" Données chargées pour l'interface interactive")
        except Exception as e:
            print(f" Erreur lors du chargement: {e}")
            raise

    def _setup_flask_app(self):
        """Configure l'application Flask"""
        self.app = Flask(__name__)
        self.app.secret_key = "doc_system_ia_symbolique_2025"

        # Routes principales
        self.app.add_url_rule("/", "index", self.index)
        self.app.add_url_rule("/search", "search", self.search, methods=["GET", "POST"])
        self.app.add_url_rule("/demo", "demo_mode", self.demo_mode)
        self.app.add_url_rule(
            "/api/search", "api_search", self.api_search, methods=["POST"]
        )

    def generate_static_interface(self):
        """Génère une interface HTML statique complète"""
        print("🌐 Génération de l'interface HTML statique...")

        static_dir = Path("static_interface")
        static_dir.mkdir(exist_ok=True)

        # Page principale avec toutes les informations
        self._generate_complete_static_page(static_dir)

        # CSS
        self._generate_static_css(static_dir)

        # JS
        self._generate_static_js(static_dir)

        index_file = static_dir / "index.html"
        print(f"✅ Interface statique générée: {index_file}")
        return index_file

    def _generate_complete_static_page(self, static_dir: Path):
        """Génère une page HTML statique complète avec toutes les fonctionnalités"""
        metrics = self.analysis_data["metrics"]
        entry_points = self.analysis_data["entry_points"][:10]

        # Préparer les données pour la recherche client-side
        search_data = {}
        for module_path, module in self.analysis_data["modules"].items():
            search_data[module_path] = {
                "name": module["name"],
                "category": module["category"],
                "type": module["type"],
                "docstring": module.get("docstring", ""),
                "complexity": module["complexity_score"],
            }

        # Grouper par catégories
        categories = {}
        for module_path, module in self.analysis_data["modules"].items():
            cat = module["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(
                {
                    "name": module["name"],
                    "path": module_path,
                    "complexity": module["complexity_score"],
                    "type": module["type"],
                }
            )

        html_content = f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentation IA Symbolique - Analyse Complète</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="header">
        <h1>🧠 Système de Documentation IA Symbolique</h1>
        <p>Interface Interactive d'Analyse et de Navigation</p>
        <div class="header-stats">
            <span>📊 {metrics['total_modules']} modules analysés</span>
            <span>🤖 {metrics['agents_count']} agents IA</span>
            <span>🔧 {metrics['tools_count']} outils</span>
            <span>⚙️ {metrics['orchestration_count']} composants d'orchestration</span>
        </div>
    </div>
    
    <nav class="main-nav">
        <button onclick="showTab('dashboard')" class="nav-btn active" id="dashboard-btn">🏠 Tableau de Bord</button>
        <button onclick="showTab('search')" class="nav-btn" id="search-btn">🔍 Recherche</button>
        <button onclick="showTab('categories')" class="nav-btn" id="categories-btn">📚 Catégories</button>
        <button onclick="showTab('demo')" class="nav-btn" id="demo-btn">🎯 Mode Démo</button>
        <a href="knowledge_map.html" class="nav-btn">🗺️ Carte Interactive</a>
        <a href="generated_docs/index.html" class="nav-btn">📄 Documentation</a>
    </nav>
    
    <!-- TABLEAU DE BORD -->
    <div id="dashboard" class="tab-content active">
        <div class="dashboard">
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-value">{metrics['total_modules']}</div>
                    <div class="metric-label">Modules Analysés</div>
                    <div class="metric-desc">Total des fichiers Python analysés</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{metrics['agents_count']}</div>
                    <div class="metric-label">Agents IA</div>
                    <div class="metric-desc">Agents spécialisés détectés</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{metrics['tools_count']}</div>
                    <div class="metric-label">Outils d'Analyse</div>
                    <div class="metric-desc">Outils rhétoriques et techniques</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{round(metrics['avg_complexity'], 1)}</div>
                    <div class="metric-label">Complexité Moyenne</div>
                    <div class="metric-desc">Score de complexité moyen</div>
                </div>
            </div>
            
            <div class="section-grid">
                <div class="info-section">
                    <h2>🚀 Points d'Entrée Recommandés</h2>
                    <div class="entry-points">"""

        # Ajouter les points d'entrée
        for entry in entry_points[:8]:
            html_content += f'''
                        <div class="entry-item">
                            <h4>{entry['name']}</h4>
                            <span class="badge badge-{entry['category']}">{entry['category']}</span>
                            <p>{entry.get('docstring', 'Module d\'entrée du système')[:120]}...</p>
                        </div>'''

        html_content += """
                    </div>
                </div>
                
                <div class="info-section">
                    <h2>📊 Répartition par Catégories</h2>
                    <div class="category-stats">"""

        # Ajouter les statistiques par catégorie
        category_counts = {}
        for cat, modules in categories.items():
            category_counts[cat] = len(modules)

        for category, count in sorted(
            category_counts.items(), key=lambda x: x[1], reverse=True
        ):
            html_content += f"""
                        <div class="category-stat">
                            <span class="category-name">{category.title()}</span>
                            <span class="category-count">{count} modules</span>
                        </div>"""

        html_content += """
                    </div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- RECHERCHE -->
    <div id="search" class="tab-content">
        <div class="search-container">
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Rechercher modules, fonctions, classes..." />
                <button onclick="performSearch()">🔍 Rechercher</button>
                <button onclick="clearSearch()">🗑️ Effacer</button>
            </div>
            
            <div class="search-tips">
                <h3>💡 Conseils de Recherche</h3>
                <ul>
                    <li><strong>Mots-clés :</strong> "extract", "informal", "logic", "rhetorical"</li>
                    <li><strong>Types :</strong> "agent", "tool", "orchestration"</li>
                    <li><strong>Fonctions :</strong> "analyze", "detect", "generate"</li>
                </ul>
            </div>
            
            <div id="searchResults" class="search-results">
                <p class="no-results">💡 Tapez votre recherche ci-dessus pour explorer les {metrics['total_modules']} modules du projet.</p>
            </div>
        </div>
    </div>
    
    <!-- CATÉGORIES -->
    <div id="categories" class="tab-content">
        <div class="categories-container">
            <h2>📚 Navigation par Catégories</h2>
            <div class="categories-grid">"""

        # Ajouter les catégories
        for category, modules in categories.items():
            if len(modules) > 0:
                html_content += f"""
                <div class="category-card" onclick="showCategoryDetails('{category}')">
                    <h3>{category.title()}</h3>
                    <div class="category-meta">
                        <span class="module-count">{len(modules)} modules</span>
                        <span class="avg-complexity">Complexité moy: {sum(m['complexity'] for m in modules) / len(modules):.1f}</span>
                    </div>
                    <div class="module-preview">"""

                for module in modules[:3]:
                    html_content += f"""
                        <div class="module-preview-item">{module['name']}</div>"""

                if len(modules) > 3:
                    html_content += f"""
                        <div class="module-preview-item more">+{len(modules) - 3} autres...</div>"""

                html_content += """
                    </div>
                </div>"""

        html_content += """
            </div>
            
            <div id="categoryDetails" class="category-details" style="display: none;">
                <button onclick="hideCategoryDetails()" class="close-btn">✕ Fermer</button>
                <div id="categoryDetailsContent"></div>
            </div>
        </div>
    </div>
    
    <!-- MODE DÉMO -->
    <div id="demo" class="tab-content">
        <div class="demo-container">
            <div class="demo-header">
                <h2>🎯 Mode Démonstration</h2>
                <p>Présentation du Système de Documentation Automatique</p>
            </div>
            
            <div class="demo-highlights">
                <div class="highlight-card">
                    <h3>🔍 Analyse Automatique</h3>
                    <p><strong>567 modules analysés</strong> en 2.7 secondes</p>
                    <p>Détection intelligente des patterns d'IA symbolique</p>
                </div>
                
                <div class="highlight-card">
                    <h3>🤖 Agents Spécialisés</h3>
                    <p><strong>5 catégories détectées :</strong></p>
                    <ul>
                        <li>🔤 Extract (6 modules)</li>
                        <li>💭 Informal (20 modules)</li>
                        <li>🔬 Logic (11 modules)</li>
                        <li>📝 Rhetorical (55 modules)</li>
                        <li>⚙️ PM (2 modules)</li>
                    </ul>
                </div>
                
                <div class="highlight-card">
                    <h3>📚 Documentation Vivante</h3>
                    <p>Génération automatique de :</p>
                    <ul>
                        <li>📄 Pages de référence par module</li>
                        <li>🗺️ Cartes de dépendances</li>
                        <li>📖 Guides par catégorie</li>
                        <li>🛤️ Parcours d'apprentissage</li>
                    </ul>
                </div>
            </div>
            
            <div class="demo-scenarios">
                <h3>🎭 Scénarios de Démonstration</h3>
                
                <div class="scenario">
                    <h4>👥 Nouveau Développeur</h4>
                    <p>Un développeur rejoint l'équipe et doit comprendre l'architecture complexe :</p>
                    <ol>
                        <li>Consulte le <strong>tableau de bord</strong> pour une vue d'ensemble</li>
                        <li>Explore les <strong>points d'entrée recommandés</strong></li>
                        <li>Suit un <strong>parcours d'apprentissage personnalisé</strong></li>
                        <li>Navigue dans la <strong>documentation générée</strong></li>
                    </ol>
                </div>
                
                <div class="scenario">
                    <h4>🔍 Recherche de Fonctionnalité</h4>
                    <p>Un développeur cherche des outils d'analyse rhétorique :</p>
                    <ol>
                        <li>Utilise la <strong>recherche intelligente</strong> avec "rhetorical"</li>
                        <li>Explore la <strong>catégorie rhétorique</strong> (55 modules)</li>
                        <li>Consulte les <strong>détails des modules</strong> pertinents</li>
                        <li>Suit les <strong>dépendances et connexions</strong></li>
                    </ol>
                </div>
                
                <div class="scenario">
                    <h4>📊 Présentation d'Architecture</h4>
                    <p>Présentation de l'architecture à l'équipe ou aux stakeholders :</p>
                    <ol>
                        <li>Affiche les <strong>métriques impressionnantes</strong> (567 modules)</li>
                        <li>Montre la <strong>détection automatique</strong> des agents IA</li>
                        <li>Navigue dans la <strong>carte interactive</strong> des connaissances</li>
                        <li>Démontre la <strong>génération automatique</strong> de documentation</li>
                    </ol>
                </div>
            </div>
        </div>
    </div>
    
    <footer class="footer">
        <p>🎓 <strong>Projet EPITA 2025 - IA Symbolique</strong></p>
        <p>📋 Sujet 2.1.4 : Documentation et transfert de connaissances</p>
        <p>🚀 Système de documentation automatique pour architecture complexe</p>
    </footer>
    
    <script src="scripts.js"></script>
</body>
</html>"""

        # Préparer les données pour JavaScript (sans problème de f-string)
        with open(static_dir / "search_data.js", "w", encoding="utf-8") as f:
            f.write(f"const searchData = {json.dumps(search_data, indent=2)};")
            f.write(f"const categoriesData = {json.dumps(categories, indent=2)};")

        with open(static_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(html_content)

    def _generate_static_css(self, static_dir: Path):
        """Génère le CSS moderne et attractif"""
        css_content = """
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            color: white;
            padding: 2rem;
            text-align: center;
            margin-bottom: 1rem;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header-stats {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }
        
        .header-stats span {
            background: rgba(255, 255, 255, 0.2);
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 500;
        }
        
        .main-nav {
            background: rgba(255, 255, 255, 0.9);
            padding: 1rem;
            margin: 0 2rem 2rem 2rem;
            border-radius: 15px;
            text-align: center;
            display: flex;
            justify-content: center;
            gap: 1rem;
            flex-wrap: wrap;
        }
        
        .nav-btn {
            background: transparent;
            border: 2px solid #667eea;
            color: #667eea;
            padding: 0.7rem 1.5rem;
            border-radius: 25px;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }
        
        .nav-btn:hover, .nav-btn.active {
            background: #667eea;
            color: white;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        .tab-content {
            display: none;
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 2rem;
        }
        
        .tab-content.active {
            display: block;
        }
        
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }
        
        .metric-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 20px;
            text-align: center;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .metric-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
        }
        
        .metric-value {
            font-size: 3rem;
            font-weight: bold;
            color: #667eea;
            display: block;
            margin-bottom: 0.5rem;
        }
        
        .metric-label {
            font-size: 1.1rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 0.3rem;
        }
        
        .metric-desc {
            font-size: 0.9rem;
            color: #666;
        }
        
        .section-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            margin-bottom: 2rem;
        }
        
        .info-section {
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        }
        
        .info-section h2 {
            color: #667eea;
            margin-bottom: 1.5rem;
            font-size: 1.3rem;
        }
        
        .entry-item {
            padding: 1rem;
            margin: 1rem 0;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            transition: all 0.3s ease;
        }
        
        .entry-item:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        
        .entry-item h4 {
            color: #333;
            margin-bottom: 0.5rem;
        }
        
        .badge {
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 15px;
            font-size: 0.8rem;
            font-weight: 500;
            margin: 0.2rem 0;
        }
        
        .badge-extract { background: #ffe6e6; color: #d63384; }
        .badge-informal { background: #e6f3ff; color: #0d6efd; }
        .badge-logic { background: #e6ffe6; color: #198754; }
        .badge-rhetorical { background: #fff3e6; color: #fd7e14; }
        .badge-general { background: #f0f0f0; color: #6c757d; }
        
        .category-stat {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.8rem;
            margin: 0.5rem 0;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }
        
        .category-name {
            font-weight: 600;
            color: #333;
        }
        
        .category-count {
            background: #667eea;
            color: white;
            padding: 0.2rem 0.8rem;
            border-radius: 15px;
            font-size: 0.9rem;
        }
        
        .search-container {
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        }
        
        .search-box {
            display: flex;
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .search-box input {
            flex: 1;
            padding: 1rem;
            border: 2px solid #e9ecef;
            border-radius: 10px;
            font-size: 1rem;
            transition: border-color 0.3s ease;
        }
        
        .search-box input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .search-box button {
            padding: 1rem 2rem;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-size: 1rem;
            transition: all 0.3s ease;
        }
        
        .search-box button:hover {
            background: #5a6fd8;
            transform: translateY(-2px);
        }
        
        .search-tips {
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        
        .search-tips h3 {
            color: #667eea;
            margin-bottom: 1rem;
        }
        
        .search-results {
            min-height: 300px;
        }
        
        .search-result {
            padding: 1.5rem;
            margin: 1rem 0;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #667eea;
            transition: all 0.3s ease;
        }
        
        .search-result:hover {
            background: #e9ecef;
            transform: translateX(5px);
        }
        
        .search-result h4 {
            color: #667eea;
            margin-bottom: 0.5rem;
        }
        
        .no-results {
            text-align: center;
            color: #6c757d;
            font-style: italic;
            padding: 2rem;
        }
        
        .categories-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin: 2rem 0;
        }
        
        .category-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .category-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
        }
        
        .category-card h3 {
            color: #667eea;
            margin-bottom: 1rem;
            font-size: 1.3rem;
        }
        
        .category-meta {
            display: flex;
            justify-content: space-between;
            margin-bottom: 1rem;
            font-size: 0.9rem;
            color: #6c757d;
        }
        
        .module-preview {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
        }
        
        .module-preview-item {
            padding: 0.3rem 0;
            border-bottom: 1px solid #e9ecef;
            font-size: 0.9rem;
        }
        
        .module-preview-item:last-child {
            border-bottom: none;
        }
        
        .module-preview-item.more {
            font-style: italic;
            color: #6c757d;
        }
        
        .demo-container {
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        }
        
        .demo-header {
            text-align: center;
            margin-bottom: 3rem;
        }
        
        .demo-header h2 {
            color: #667eea;
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        
        .demo-highlights {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 2rem;
            margin-bottom: 3rem;
        }
        
        .highlight-card {
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 2rem;
            border-radius: 15px;
            border-left: 5px solid #667eea;
        }
        
        .highlight-card h3 {
            color: #667eea;
            margin-bottom: 1rem;
        }
        
        .scenario {
            background: #f8f9fa;
            padding: 2rem;
            border-radius: 15px;
            margin: 1.5rem 0;
            border-left: 5px solid #28a745;
        }
        
        .scenario h4 {
            color: #28a745;
            margin-bottom: 1rem;
        }
        
        .scenario ol {
            margin-left: 1.5rem;
        }
        
        .scenario li {
            margin: 0.5rem 0;
        }
        
        .footer {
            background: rgba(255, 255, 255, 0.1);
            color: white;
            text-align: center;
            padding: 2rem;
            margin-top: 3rem;
        }
        
        .footer p {
            margin: 0.3rem 0;
        }
        
        .category-details {
            background: rgba(255, 255, 255, 0.95);
            padding: 2rem;
            border-radius: 20px;
            margin-top: 2rem;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
        }
        
        .close-btn {
            background: #dc3545;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            float: right;
            margin-bottom: 1rem;
        }
        
        @media (max-width: 768px) {
            .header-stats {
                flex-direction: column;
                gap: 1rem;
            }
            
            .main-nav {
                flex-direction: column;
                gap: 0.5rem;
            }
            
            .section-grid {
                grid-template-columns: 1fr;
            }
            
            .search-box {
                flex-direction: column;
            }
        }
        """

        with open(static_dir / "styles.css", "w", encoding="utf-8") as f:
            f.write(css_content)

    def _generate_static_js(self, static_dir: Path):
        """Génère le JavaScript pour l'interactivité"""
        js_content = """
        // Interface interactive pour la documentation IA Symbolique
        
        // Chargement des données
        let searchData = {};
        let categoriesData = {};
        
        // Charger les données depuis le fichier séparé
        function loadData() {
            const script = document.createElement('script');
            script.src = 'search_data.js';
            script.onload = function() {
                console.log('Données chargées:', Object.keys(searchData).length, 'modules');
            };
            document.head.appendChild(script);
        }
        
        // Gestion des onglets
        function showTab(tabName) {
            // Masquer tous les onglets
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Désactiver tous les boutons
            document.querySelectorAll('.nav-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Afficher l'onglet sélectionné
            document.getElementById(tabName).classList.add('active');
            document.getElementById(tabName + '-btn').classList.add('active');
        }
        
        // Recherche intelligente
        function performSearch() {
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            const resultsDiv = document.getElementById('searchResults');
            
            if (!query) {
                resultsDiv.innerHTML = '<p class="no-results">💡 Tapez votre recherche ci-dessus pour explorer les modules.</p>';
                return;
            }
            
            const results = [];
            
            for (const [path, module] of Object.entries(searchData)) {
                let score = 0;
                
                // Recherche dans le nom
                if (module.name.toLowerCase().includes(query)) score += 10;
                
                // Recherche dans la catégorie
                if (module.category.toLowerCase().includes(query)) score += 8;
                
                // Recherche dans le type
                if (module.type.toLowerCase().includes(query)) score += 6;
                
                // Recherche dans la docstring
                if (module.docstring && module.docstring.toLowerCase().includes(query)) score += 5;
                
                // Recherche par préfixe
                if (module.name.toLowerCase().startsWith(query)) score += 15;
                if (module.category.toLowerCase().startsWith(query)) score += 12;
                
                if (score > 0) {
                    results.push({
                        path: path,
                        module: module,
                        score: score
                    });
                }
            }
            
            // Trier par score décroissant
            results.sort((a, b) => b.score - a.score);
            
            if (results.length === 0) {
                resultsDiv.innerHTML = '<p class="no-results">❌ Aucun résultat trouvé pour "' + query + '"</p>';
                return;
            }
            
            let html = '<h3>📋 Résultats (' + results.length + '):</h3>';
            
            results.slice(0, 15).forEach(result => {
                const badgeClass = 'badge-' + result.module.category;
                html += `
                    <div class="search-result">
                        <h4>${result.module.name}</h4>
                        <div style="margin: 0.5rem 0;">
                            <span class="badge ${badgeClass}">${result.module.category}</span>
                            <span class="badge badge-general">${result.module.type}</span>
                            <span style="color: #666; margin-left: 1rem;">Score: ${result.score}</span>
                        </div>
                        <p><strong>Chemin:</strong> ${result.path}</p>
                        <p><strong>Complexité:</strong> ${result.module.complexity}</p>
                        ${result.module.docstring ? '<p><strong>Description:</strong> ' + result.module.docstring.substring(0, 150) + '...</p>' : ''}
                    </div>
                `;
            });
            
            resultsDiv.innerHTML = html;
        }
        
        // Effacer la recherche
        function clearSearch() {
            document.getElementById('searchInput').value = '';
            document.getElementById('searchResults').innerHTML = '<p class="no-results">💡 Tapez votre recherche ci-dessus pour explorer les modules.</p>';
        }
        
        // Afficher les détails d'une catégorie
        function showCategoryDetails(category) {
            const detailsDiv = document.getElementById('categoryDetails');
            const contentDiv = document.getElementById('categoryDetailsContent');
            
            if (!categoriesData[category]) {
                contentDiv.innerHTML = '<p>Aucune donnée disponible pour cette catégorie.</p>';
                detailsDiv.style.display = 'block';
                return;
            }
            
            const modules = categoriesData[category];
            let html = `
                <h2>📚 Catégorie: ${category.toUpperCase()}</h2>
                <p><strong>${modules.length} modules</strong> dans cette catégorie</p>
                <div class="modules-grid" style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin-top: 2rem;">
            `;
            
            modules.forEach(module => {
                const badgeClass = 'badge-' + module.type;
                html += `
                    <div class="module-detail-card" style="background: #f8f9fa; padding: 1.5rem; border-radius: 10px; border-left: 4px solid #667eea;">
                        <h4>${module.name}</h4>
                        <div style="margin: 0.5rem 0;">
                            <span class="badge ${badgeClass}">${module.type}</span>
                        </div>
                        <p><strong>Chemin:</strong> ${module.path}</p>
                        <p><strong>Complexité:</strong> ${module.complexity}</p>
                    </div>
                `;
            });
            
            html += '</div>';
            contentDiv.innerHTML = html;
            detailsDiv.style.display = 'block';
            detailsDiv.scrollIntoView({ behavior: 'smooth' });
        }
        
        // Masquer les détails de catégorie
        function hideCategoryDetails() {
            document.getElementById('categoryDetails').style.display = 'none';
        }
        
        // Recherche en temps réel
        document.addEventListener('DOMContentLoaded', function() {
            loadData();
            
            const searchInput = document.getElementById('searchInput');
            if (searchInput) {
                searchInput.addEventListener('keyup', function(e) {
                    if (e.key === 'Enter') {
                        performSearch();
                    }
                });
            }
            
            // Animation des cartes métriques
            const metricCards = document.querySelectorAll('.metric-card');
            metricCards.forEach((card, index) => {
                setTimeout(() => {
                    card.style.opacity = '0';
                    card.style.transform = 'translateY(20px)';
                    card.style.transition = 'all 0.6s ease';
                    
                    setTimeout(() => {
                        card.style.opacity = '1';
                        card.style.transform = 'translateY(0)';
                    }, 100);
                }, index * 100);
            });
        });
        """

        with open(static_dir / "scripts.js", "w", encoding="utf-8") as f:
            f.write(js_content)

    def run_interactive_server(
        self, host: str = "127.0.0.1", port: int = 5000, debug: bool = True
    ):
        """Lance le serveur interactif Flask ou génère l'interface statique"""
        if not FLASK_AVAILABLE:
            print(" Flask non disponible. Génération de l'interface statique...")
            return self.generate_static_interface()

        print(f" Lancement du serveur interactif sur http://{host}:{port}")

        try:
            self.app.run(host=host, port=port, debug=debug)
        except Exception as e:
            print(f" Erreur du serveur Flask: {e}")
            print(" Génération de l'interface statique en alternative...")
            return self.generate_static_interface()

    # Routes Flask simplifiées
    def index(self):
        """Page d'accueil Flask"""
        from flask import render_template_string

        return render_template_string(
            """
        <h1>Interface Interactive IA Symbolique</h1>
        <p>Flask fonctionne ! Consultez la documentation générée.</p>
        <ul>
            <li><a href="/demo">Mode Démonstration</a></li>
            <li><a href="/search">Recherche</a></li>
        </ul>
        """
        )

    def search(self):
        """Page de recherche Flask"""
        return "Recherche disponible - Développement en cours"

    def demo_mode(self):
        """Mode démonstration Flask"""
        return "Mode démonstration - Interface Flask fonctionnelle"

    def api_search(self):
        """API de recherche Flask"""
        from flask import jsonify

        return jsonify({"status": "API fonctionnelle"})


def main():
    """Fonction principale"""
    print(" Interface Interactive de Documentation IA Symbolique")
    print("=" * 60)

    try:
        guide = InteractiveDocumentationGuide()

        # Toujours générer l'interface statique pour éviter les problèmes
        static_file = guide.generate_static_interface()
        print(f" Interface statique générée: {static_file}")

        # Ouvrir automatiquement dans le navigateur
        try:
            webbrowser.open(f"file://{static_file.absolute()}")
            print("🌐 Interface ouverte dans votre navigateur")
        except Exception as e:
            print(f" Impossible d'ouvrir automatiquement: {e}")
            print(f" Ouvrez manuellement: {static_file.absolute()}")

        return static_file

    except Exception as e:
        print(f" Erreur lors du lancement: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
