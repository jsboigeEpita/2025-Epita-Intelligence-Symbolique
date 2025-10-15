#!/usr/bin/env python3
"""
Moteur de Recherche Documentation - Version Web Moderne
========================================================

Interface web avancée pour explorer et rechercher dans la documentation
du projet d'IA symbolique avec serveur intégré sur localhost:8081.
"""

import os
import re
import json
import threading
import webbrowser
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime
import unicodedata
import difflib
from collections import defaultdict, Counter

try:
    from flask import (
        Flask,
        render_template_string,
        request,
        jsonify,
        send_from_directory,
    )

    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("Flask non disponible. Installez avec: pip install flask")


class AdvancedDocumentationSearcher:
    """Moteur de recherche avancé pour la documentation"""

    def __init__(self):
        self.documents = {}  # {filepath: content}
        self.metadata = {}  # {filepath: {size, lines, modified, etc.}}
        self.indexed_docs = {}  # {filepath: {word: positions}}
        self.file_tree = {}  # Structure hiérarchique
        self.stats = {
            "total_files": 0,
            "total_size": 0,
            "file_types": Counter(),
            "languages": Counter(),
            "last_scan": None,
        }

    def normalize_text(self, text: str) -> str:
        """Normalise le texte pour la recherche"""
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        return text.lower()

    def detect_language(self, filepath: str, content: str) -> str:
        """Détecte le langage de programmation ou type de fichier"""
        ext = Path(filepath).suffix.lower()

        language_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".html": "HTML",
            ".css": "CSS",
            ".md": "Markdown",
            ".rst": "reStructuredText",
            ".txt": "Text",
            ".json": "JSON",
            ".yml": "YAML",
            ".yaml": "YAML",
            ".xml": "XML",
            ".sql": "SQL",
            ".sh": "Shell",
            ".bat": "Batch",
            ".dockerfile": "Docker",
            ".java": "Java",
            ".c": "C",
            ".cpp": "C++",
            ".h": "C Header",
            ".cs": "C#",
            ".php": "PHP",
            ".rb": "Ruby",
            ".go": "Go",
            ".rs": "Rust",
            ".swift": "Swift",
            ".kt": "Kotlin",
        }

        return language_map.get(ext, "Unknown")

    def analyze_file_content(self, filepath: str, content: str) -> Dict:
        """Analyse le contenu d'un fichier pour extraire des métadonnées"""
        lines = content.split("\n")

        analysis = {
            "lines_count": len(lines),
            "chars_count": len(content),
            "words_count": len(re.findall(r"\b\w+\b", content)),
            "blank_lines": len([l for l in lines if not l.strip()]),
            "language": self.detect_language(filepath, content),
            "has_code": False,
            "has_comments": False,
            "complexity_score": 0,
        }

        # Détection de code
        code_indicators = [
            "def ",
            "class ",
            "function ",
            "import ",
            "from ",
            "= ",
            "{",
            "}",
            "()",
            ";",
        ]
        analysis["has_code"] = any(
            indicator in content for indicator in code_indicators
        )

        # Détection de commentaires
        comment_indicators = ["#", "//", "/*", "*/", "<!--", "-->", '"""', "'''"]
        analysis["has_comments"] = any(
            indicator in content for indicator in comment_indicators
        )

        # Score de complexité simple
        complexity_indicators = [
            "if ",
            "for ",
            "while ",
            "try:",
            "except:",
            "class ",
            "def ",
        ]
        analysis["complexity_score"] = sum(
            content.count(indicator) for indicator in complexity_indicators
        )

        return analysis

    def load_documents_from_directory(
        self, directory: str, max_file_size: int = 1024 * 1024
    ) -> None:
        """Charge et analyse tous les documents d'un répertoire"""
        print(f"🔍 Scan du répertoire : {directory}")

        supported_extensions = {
            ".md",
            ".txt",
            ".rst",
            ".py",
            ".js",
            ".ts",
            ".html",
            ".css",
            ".json",
            ".yml",
            ".yaml",
            ".xml",
            ".sql",
            ".sh",
            ".bat",
            ".java",
            ".c",
            ".cpp",
            ".h",
            ".cs",
            ".php",
            ".rb",
            ".go",
        }

        total_files = 0
        processed_files = 0
        skipped_files = 0

        for root, dirs, files in os.walk(directory):
            # Ignorer certains répertoires
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in {"__pycache__", "node_modules", "venv", "env", "build", "dist"}
            ]

            for file in files:
                if any(file.endswith(ext) for ext in supported_extensions):
                    total_files += 1
                    filepath = os.path.join(root, file)

                    try:
                        # Vérifier la taille du fichier
                        file_size = os.path.getsize(filepath)
                        if file_size > max_file_size:
                            skipped_files += 1
                            continue

                        # Lire et analyser le fichier
                        with open(
                            filepath, "r", encoding="utf-8", errors="ignore"
                        ) as f:
                            content = f.read()

                        # Stocker le document
                        rel_path = os.path.relpath(filepath, directory)
                        self.documents[rel_path] = content

                        # Analyser le contenu
                        analysis = self.analyze_file_content(rel_path, content)

                        # Métadonnées du fichier
                        stat = os.stat(filepath)
                        self.metadata[rel_path] = {
                            "size": file_size,
                            "modified": datetime.fromtimestamp(stat.st_mtime),
                            "extension": Path(filepath).suffix,
                            "directory": os.path.dirname(rel_path),
                            **analysis,
                        }

                        # Indexer pour la recherche
                        self.index_document(rel_path, content)

                        # Statistiques
                        self.stats["file_types"][Path(filepath).suffix] += 1
                        self.stats["languages"][analysis["language"]] += 1
                        self.stats["total_size"] += file_size

                        processed_files += 1

                        if processed_files % 50 == 0:
                            print(f"   Traité: {processed_files} fichiers...")

                    except Exception as e:
                        print(f"   ⚠️ Erreur {filepath}: {e}")
                        skipped_files += 1

        self.stats["total_files"] = processed_files
        self.stats["last_scan"] = datetime.now()

        # Construire l'arbre des fichiers
        self._build_file_tree()

        print(
            f" Scan terminé: {processed_files} fichiers traités, {skipped_files} ignorés"
        )

    def _build_file_tree(self):
        """Construit l'arborescence des fichiers"""
        self.file_tree = {}

        for filepath in self.documents.keys():
            parts = Path(filepath).parts
            current = self.file_tree

            for part in parts[:-1]:  # Répertoires
                if part not in current:
                    current[part] = {"type": "directory", "children": {}, "files": []}
                current = current[part]["children"]

            # Fichier final
            filename = parts[-1]
            if "files" not in current:
                current["files"] = []
            current["files"].append(
                {
                    "name": filename,
                    "path": filepath,
                    "size": self.metadata[filepath]["size"],
                    "language": self.metadata[filepath]["language"],
                }
            )

    def index_document(self, filepath: str, content: str) -> None:
        """Indexe un document pour la recherche rapide"""
        words = {}
        normalized_content = self.normalize_text(content)

        # Extraire les mots avec positions
        for match in re.finditer(r"\b\w+\b", normalized_content):
            word = match.group()
            if len(word) >= 2:  # Mots de 2+ caractères
                if word not in words:
                    words[word] = []
                words[word].append(match.start())

        self.indexed_docs[filepath] = words

    def advanced_search(
        self, query: str, filters: Dict = None, max_results: int = 50
    ) -> List[Dict]:
        """Recherche avancée avec filtres"""
        if not query.strip():
            return []

        filters = filters or {}
        query_words = [
            self.normalize_text(word)
            for word in re.findall(r"\b\w+\b", query.lower())
            if len(word) >= 2
        ]

        if not query_words:
            return []

        results = []

        for filepath, word_index in self.indexed_docs.items():
            # Appliquer les filtres
            if not self._passes_filters(filepath, filters):
                continue

            score = 0
            matches = []
            match_details = []

            # Recherche pour chaque mot
            for query_word in query_words:
                word_matches = self.find_word_matches(query_word, word_index)

                for matched_word, positions in word_matches.items():
                    word_score = len(positions)

                    # Bonus selon le type de correspondance
                    if matched_word == query_word:
                        word_score *= 3  # Exact
                    elif matched_word.startswith(query_word):
                        word_score *= 2  # Préfixe
                    elif query_word in matched_word:
                        word_score *= 1.5  # Contient

                    score += word_score
                    matches.extend(positions)
                    match_details.append(
                        {
                            "query_word": query_word,
                            "matched_word": matched_word,
                            "positions": positions,
                            "match_type": self.get_match_type(query_word, matched_word),
                        }
                    )

            if score > 0:
                contexts = self.extract_contexts(filepath, matches)
                metadata = self.metadata.get(filepath, {})

                results.append(
                    {
                        "filepath": filepath,
                        "filename": os.path.basename(filepath),
                        "directory": os.path.dirname(filepath),
                        "score": score,
                        "matches": len(matches),
                        "contexts": contexts,
                        "match_details": match_details,
                        "metadata": metadata,
                        "preview": self._generate_preview(filepath, contexts),
                    }
                )

        # Trier par score et filtrer
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:max_results]

    def _passes_filters(self, filepath: str, filters: Dict) -> bool:
        """Vérifie si un fichier passe les filtres"""
        metadata = self.metadata.get(filepath, {})

        # Filtre par extension
        if "extensions" in filters and filters["extensions"]:
            if metadata.get("extension", "") not in filters["extensions"]:
                return False

        # Filtre par langage
        if "languages" in filters and filters["languages"]:
            if metadata.get("language", "") not in filters["languages"]:
                return False

        # Filtre par taille
        if "min_size" in filters:
            if metadata.get("size", 0) < filters["min_size"]:
                return False

        if "max_size" in filters:
            if metadata.get("size", 0) > filters["max_size"]:
                return False

        # Filtre par date de modification
        if "date_from" in filters and filters["date_from"]:
            file_date = metadata.get("modified")
            if file_date and file_date < filters["date_from"]:
                return False

        # Filtre par répertoire
        if "directories" in filters and filters["directories"]:
            file_dir = os.path.dirname(filepath)
            if not any(file_dir.startswith(d) for d in filters["directories"]):
                return False

        return True

    def find_word_matches(
        self, query_word: str, word_index: Dict
    ) -> Dict[str, List[int]]:
        """Trouve les correspondances de mots avec différents types"""
        matches = {}

        for indexed_word, positions in word_index.items():
            # Correspondance exacte
            if indexed_word == query_word:
                matches[indexed_word] = positions

            # Correspondance par préfixe
            elif indexed_word.startswith(query_word):
                matches[indexed_word] = positions

            # Correspondance par sous-chaîne
            elif query_word in indexed_word and len(query_word) >= 3:
                matches[indexed_word] = positions

            # Correspondance floue
            elif len(query_word) >= 4 and self.is_fuzzy_match(query_word, indexed_word):
                matches[indexed_word] = positions

        return matches

    def is_fuzzy_match(self, query_word: str, indexed_word: str) -> bool:
        """Correspondance floue avec Levenshtein"""
        if abs(len(query_word) - len(indexed_word)) > 3:
            return False

        similarity = difflib.SequenceMatcher(None, query_word, indexed_word).ratio()
        threshold = 0.8 if len(query_word) <= 5 else 0.75

        return similarity >= threshold

    def get_match_type(self, query_word: str, matched_word: str) -> str:
        """Type de correspondance"""
        if matched_word == query_word:
            return "exact"
        elif matched_word.startswith(query_word):
            return "prefix"
        elif query_word in matched_word:
            return "substring"
        else:
            return "fuzzy"

    def extract_contexts(
        self, filepath: str, positions: List[int], context_size: int = 150
    ) -> List[str]:
        """Extrait des contextes autour des positions"""
        content = self.documents[filepath]
        contexts = []

        positions = sorted(set(positions))[:5]  # Limiter à 5 contextes

        for pos in positions:
            start = max(0, pos - context_size)
            end = min(len(content), pos + context_size)
            context = content[start:end].strip()

            # Nettoyer et améliorer le contexte
            context = re.sub(r"\s+", " ", context)
            if context and len(context) > 20:
                # Ajouter des points de suspension si tronqué
                if start > 0:
                    context = "..." + context
                if end < len(content):
                    context = context + "..."

                contexts.append(context)

        return contexts

    def _generate_preview(self, filepath: str, contexts: List[str]) -> str:
        """Génère un aperçu du fichier"""
        if contexts:
            return contexts[0][:200] + "..." if len(contexts[0]) > 200 else contexts[0]

        # Aperçu depuis le début du fichier
        content = self.documents[filepath]
        lines = content.split("\n")[:5]
        preview = "\n".join(lines)

        return preview[:300] + "..." if len(preview) > 300 else preview

    def get_statistics(self) -> Dict:
        """Retourne les statistiques du corpus"""
        return {
            "overview": self.stats,
            "top_languages": dict(self.stats["languages"].most_common(10)),
            "top_extensions": dict(self.stats["file_types"].most_common(10)),
            "size_distribution": self._get_size_distribution(),
            "directory_structure": self._get_directory_stats(),
        }

    def _get_size_distribution(self) -> Dict:
        """Distribution des tailles de fichiers"""
        sizes = [meta["size"] for meta in self.metadata.values()]

        return {
            "small": len([s for s in sizes if s < 1024]),  # < 1KB
            "medium": len([s for s in sizes if 1024 <= s < 10240]),  # 1-10KB
            "large": len([s for s in sizes if 10240 <= s < 102400]),  # 10-100KB
            "xlarge": len([s for s in sizes if s >= 102400]),  # > 100KB
        }

    def _get_directory_stats(self) -> Dict:
        """Statistiques par répertoire"""
        dir_stats = defaultdict(lambda: {"files": 0, "size": 0})

        for filepath, metadata in self.metadata.items():
            directory = os.path.dirname(filepath) or "root"
            dir_stats[directory]["files"] += 1
            dir_stats[directory]["size"] += metadata["size"]

        return dict(dir_stats)


class DocumentationWebServer:
    """Serveur web moderne pour l'interface de recherche"""

    def __init__(self, port: int = 8081):
        self.port = port
        self.searcher = AdvancedDocumentationSearcher()
        self.app = Flask(__name__)
        self.app.secret_key = "documentation_search_2025"
        self._setup_routes()

    def _setup_routes(self):
        """Configure les routes Flask"""
        self.app.add_url_rule("/", "index", self.index)
        self.app.add_url_rule(
            "/api/search", "search", self.api_search, methods=["POST"]
        )
        self.app.add_url_rule("/api/stats", "stats", self.api_stats)
        self.app.add_url_rule(
            "/api/file/<path:filepath>", "get_file", self.api_get_file
        )
        self.app.add_url_rule("/api/tree", "file_tree", self.api_file_tree)
        self.app.add_url_rule("/scan/<path:directory>", "scan", self.scan_directory)

    def load_project(self, project_path: str = "."):
        """Charge et indexe un projet"""
        print(f" Chargement du projet depuis : {project_path}")
        self.searcher.load_documents_from_directory(project_path)
        print(f" Projet indexé : {self.searcher.stats['total_files']} fichiers")

    def index(self):
        """Page principale de l'interface"""
        return render_template_string(self._get_main_template())

    def api_search(self):
        """API de recherche avancée"""
        data = request.get_json()
        query = data.get("query", "")
        filters = data.get("filters", {})
        max_results = data.get("max_results", 50)

        results = self.searcher.advanced_search(query, filters, max_results)

        return jsonify(
            {
                "status": "success",
                "query": query,
                "total_results": len(results),
                "results": results,
                "stats": self.searcher.get_statistics()["overview"],
            }
        )

    def api_stats(self):
        """API des statistiques"""
        return jsonify(self.searcher.get_statistics())

    def api_get_file(self, filepath):
        """API pour récupérer le contenu d'un fichier"""
        if filepath in self.searcher.documents:
            content = self.searcher.documents[filepath]
            metadata = self.searcher.metadata[filepath]

            return jsonify(
                {
                    "status": "success",
                    "filepath": filepath,
                    "content": content,
                    "metadata": metadata,
                }
            )

        return jsonify({"status": "error", "message": "Fichier non trouvé"}), 404

    def api_file_tree(self):
        """API pour l'arborescence des fichiers"""
        return jsonify(
            {
                "status": "success",
                "tree": self.searcher.file_tree,
                "stats": self.searcher.get_statistics(),
            }
        )

    def scan_directory(self, directory):
        """Rescanner un répertoire"""
        try:
            self.searcher.load_documents_from_directory(directory)
            return jsonify(
                {
                    "status": "success",
                    "message": f"Répertoire {directory} scanné avec succès",
                    "stats": self.searcher.stats,
                }
            )
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    def _get_main_template(self):
        """Template HTML principal moderne"""
        return """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentation Search Engine - Advanced</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #667eea;
            --secondary-color: #764ba2;
            --success-color: #28a745;
            --warning-color: #ffc107;
            --danger-color: #dc3545;
            --dark-color: #343a40;
            --light-color: #f8f9fa;
            --border-radius: 12px;
            --shadow: 0 4px 20px rgba(0,0,0,0.1);
            --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, var(--primary-color) 0%, var(--secondary-color) 100%);
            min-height: 100vh;
            line-height: 1.6;
        }

        .header {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(20px);
            padding: 2rem 0;
            text-align: center;
            color: white;
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            text-shadow: 0 2px 4px rgba(0,0,0,0.3);
        }

        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 2rem;
        }

        .search-section {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: var(--border-radius);
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: var(--shadow);
        }

        .search-bar {
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
        }

        .search-input {
            flex: 1;
            padding: 1rem;
            border: 2px solid #e9ecef;
            border-radius: var(--border-radius);
            font-size: 1rem;
            transition: var(--transition);
        }

        .search-input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .search-btn {
            padding: 1rem 2rem;
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            border: none;
            border-radius: var(--border-radius);
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .search-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
        }

        .filters-panel {
            display: none;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            padding: 1.5rem;
            background: #f8f9fa;
            border-radius: var(--border-radius);
            margin-top: 1rem;
        }

        .filters-panel.active {
            display: grid;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .filter-group label {
            font-weight: 600;
            color: var(--dark-color);
            font-size: 0.9rem;
        }

        .filter-select, .filter-input {
            padding: 0.7rem;
            border: 1px solid #ddd;
            border-radius: 8px;
            background: white;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: rgba(255, 255, 255, 0.95);
            padding: 1.5rem;
            border-radius: var(--border-radius);
            text-align: center;
            box-shadow: var(--shadow);
            transition: var(--transition);
        }

        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary-color);
            display: block;
        }

        .stat-label {
            color: #666;
            font-weight: 500;
            margin-top: 0.5rem;
        }

        .results-section {
            background: rgba(255, 255, 255, 0.95);
            border-radius: var(--border-radius);
            box-shadow: var(--shadow);
            overflow: hidden;
        }

        .results-header {
            padding: 1.5rem;
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-bottom: 1px solid #dee2e6;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .results-list {
            max-height: 600px;
            overflow-y: auto;
        }

        .result-item {
            padding: 1.5rem;
            border-bottom: 1px solid #eee;
            transition: var(--transition);
        }

        .result-item:hover {
            background: #f8f9fa;
        }

        .result-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1rem;
        }

        .result-title {
            font-weight: 600;
            color: var(--primary-color);
            font-size: 1.1rem;
        }

        .result-path {
            color: #666;
            font-size: 0.9rem;
            margin-top: 0.2rem;
        }

        .result-meta {
            display: flex;
            gap: 1rem;
            font-size: 0.85rem;
            color: #666;
        }

        .result-preview {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin-top: 1rem;
            border-left: 4px solid var(--primary-color);
            font-family: 'Fira Code', monospace;
            font-size: 0.9rem;
            line-height: 1.4;
        }

        .badges {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
        }

        .badge {
            padding: 0.25rem 0.6rem;
            border-radius: 15px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .badge-language {
            background: var(--primary-color);
            color: white;
        }

        .badge-match {
            background: var(--success-color);
            color: white;
        }

        .badge-score {
            background: var(--warning-color);
            color: var(--dark-color);
        }

        .toggle-btn {
            background: transparent;
            border: 1px solid var(--primary-color);
            color: var(--primary-color);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            cursor: pointer;
            transition: var(--transition);
        }

        .toggle-btn:hover {
            background: var(--primary-color);
            color: white;
        }

        .loading {
            text-align: center;
            padding: 2rem;
            color: #666;
        }

        .loading i {
            font-size: 2rem;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        .no-results {
            text-align: center;
            padding: 3rem;
            color: #666;
        }

        .no-results i {
            font-size: 3rem;
            margin-bottom: 1rem;
            opacity: 0.5;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            .search-bar {
                flex-direction: column;
            }

            .filters-panel {
                grid-template-columns: 1fr;
            }

            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .result-header {
                flex-direction: column;
                align-items: flex-start;
            }
        }

        /* Mode sombre */
        .dark-mode {
            --primary-color: #7c3aed;
            --secondary-color: #a855f7;
            background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
        }

        .dark-mode .search-section,
        .dark-mode .stat-card,
        .dark-mode .results-section {
            background: rgba(31, 41, 55, 0.95);
            color: #e5e7eb;
        }

        .dark-mode .result-item:hover {
            background: rgba(55, 65, 81, 0.5);
        }

        .dark-mode .result-preview {
            background: rgba(17, 24, 39, 0.8);
            color: #d1d5db;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1><i class="fas fa-search"></i> Documentation Search Engine</h1>
        <p>Moteur de recherche avancé pour votre documentation</p>
    </div>

    <div class="container">
        <!-- Section de recherche -->
        <div class="search-section">
            <div class="search-bar">
                <input type="text" id="searchInput" class="search-input" 
                       placeholder="Rechercher dans la documentation..." 
                       autocomplete="off">
                <button id="searchBtn" class="search-btn">
                    <i class="fas fa-search"></i> Rechercher
                </button>
                <button id="filtersBtn" class="toggle-btn">
                    <i class="fas fa-filter"></i> Filtres
                </button>
                <button id="themeBtn" class="toggle-btn">
                    <i class="fas fa-moon"></i>
                </button>
            </div>

            <!-- Panneau de filtres -->
            <div id="filtersPanel" class="filters-panel">
                <div class="filter-group">
                    <label>Langages</label>
                    <select id="languageFilter" class="filter-select" multiple>
                        <option value="">Tous les langages</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Extensions</label>
                    <select id="extensionFilter" class="filter-select" multiple>
                        <option value="">Toutes les extensions</option>
                    </select>
                </div>
                <div class="filter-group">
                    <label>Taille min (bytes)</label>
                    <input type="number" id="minSize" class="filter-input" placeholder="0">
                </div>
                <div class="filter-group">
                    <label>Taille max (bytes)</label>
                    <input type="number" id="maxSize" class="filter-input" placeholder="∞">
                </div>
            </div>
        </div>

        <!-- Statistiques -->
        <div id="statsGrid" class="stats-grid">
            <!-- Statistiques chargées dynamiquement -->
        </div>

        <!-- Résultats -->
        <div class="results-section">
            <div class="results-header">
                <h3 id="resultsTitle">Prêt à rechercher</h3>
                <div>
                    <button id="exportBtn" class="toggle-btn" style="display: none;">
                        <i class="fas fa-download"></i> Exporter
                    </button>
                </div>
            </div>
            <div id="resultsContainer" class="results-list">
                <div class="no-results">
                    <i class="fas fa-book"></i>
                    <h3>Bienvenue dans le moteur de recherche</h3>
                    <p>Tapez votre recherche ci-dessus pour commencer</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Variables globales
        let currentResults = [];
        let currentStats = {};
        let darkMode = false;

        // Initialisation
        document.addEventListener('DOMContentLoaded', function() {
            loadInitialStats();
            setupEventListeners();
        });

        function setupEventListeners() {
            document.getElementById('searchBtn').addEventListener('click', performSearch);
            document.getElementById('searchInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') performSearch();
            });
            
            document.getElementById('filtersBtn').addEventListener('click', toggleFilters);
            document.getElementById('themeBtn').addEventListener('click', toggleTheme);
            document.getElementById('exportBtn').addEventListener('click', exportResults);
        }

        async function loadInitialStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                currentStats = data;
                renderStats(data);
                populateFilters(data);
            } catch (error) {
                console.error('Erreur lors du chargement des stats:', error);
            }
        }

        function renderStats(stats) {
            const overview = stats.overview;
            const statsHtml = `
                <div class="stat-card">
                    <span class="stat-value">${overview.total_files}</span>
                    <div class="stat-label">Fichiers indexés</div>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${formatFileSize(overview.total_size)}</span>
                    <div class="stat-label">Taille totale</div>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${Object.keys(stats.top_languages).length}</span>
                    <div class="stat-label">Langages détectés</div>
                </div>
                <div class="stat-card">
                    <span class="stat-value">${Object.keys(stats.top_extensions).length}</span>
                    <div class="stat-label">Types de fichiers</div>
                </div>
            `;
            document.getElementById('statsGrid').innerHTML = statsHtml;
        }

        function populateFilters(stats) {
            const languageSelect = document.getElementById('languageFilter');
            const extensionSelect = document.getElementById('extensionFilter');

            // Peupler les langages
            Object.keys(stats.top_languages).forEach(lang => {
                const option = document.createElement('option');
                option.value = lang;
                option.textContent = `${lang} (${stats.top_languages[lang]})`;
                languageSelect.appendChild(option);
            });

            // Peupler les extensions
            Object.keys(stats.top_extensions).forEach(ext => {
                const option = document.createElement('option');
                option.value = ext;
                option.textContent = `${ext} (${stats.top_extensions[ext]})`;
                extensionSelect.appendChild(option);
            });
        }

        async function performSearch() {
            const query = document.getElementById('searchInput').value.trim();
            if (!query) return;

            showLoading();

            const filters = getFilters();
            
            try {
                const response = await fetch('/api/search', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        query: query,
                        filters: filters,
                        max_results: 50
                    })
                });

                const data = await response.json();
                currentResults = data.results;
                renderResults(data);

            } catch (error) {
                console.error('Erreur de recherche:', error);
                showError('Erreur lors de la recherche');
            }
        }

        function getFilters() {
            const filters = {};

            const languages = Array.from(document.getElementById('languageFilter').selectedOptions)
                .map(option => option.value).filter(v => v);
            if (languages.length > 0) filters.languages = languages;

            const extensions = Array.from(document.getElementById('extensionFilter').selectedOptions)
                .map(option => option.value).filter(v => v);
            if (extensions.length > 0) filters.extensions = extensions;

            const minSize = document.getElementById('minSize').value;
            if (minSize) filters.min_size = parseInt(minSize);

            const maxSize = document.getElementById('maxSize').value;
            if (maxSize) filters.max_size = parseInt(maxSize);

            return filters;
        }

        function renderResults(data) {
            const container = document.getElementById('resultsContainer');
            const title = document.getElementById('resultsTitle');
            const exportBtn = document.getElementById('exportBtn');

            if (data.results.length === 0) {
                container.innerHTML = `
                    <div class="no-results">
                        <i class="fas fa-search-minus"></i>
                        <h3>Aucun résultat trouvé</h3>
                        <p>Essayez avec d'autres termes de recherche</p>
                    </div>
                `;
                title.textContent = 'Aucun résultat';
                exportBtn.style.display = 'none';
                return;
            }

            title.textContent = `${data.results.length} résultat(s) pour "${data.query}"`;
            exportBtn.style.display = 'inline-block';

            const resultsHtml = data.results.map(result => `
                <div class="result-item">
                    <div class="result-header">
                        <div>
                            <div class="result-title">${result.filename}</div>
                            <div class="result-path">${result.filepath}</div>
                            <div class="badges">
                                <span class="badge badge-language">${result.metadata.language || 'Unknown'}</span>
                                <span class="badge badge-match">${result.matches} correspondances</span>
                                <span class="badge badge-score">Score: ${result.score}</span>
                            </div>
                        </div>
                        <div class="result-meta">
                            <span><i class="fas fa-weight-hanging"></i> ${formatFileSize(result.metadata.size || 0)}</span>
                            <span><i class="fas fa-code"></i> ${result.metadata.lines_count || 0} lignes</span>
                        </div>
                    </div>
                    ${result.preview ? `<div class="result-preview">${escapeHtml(result.preview)}</div>` : ''}
                </div>
            `).join('');

            container.innerHTML = resultsHtml;
        }

        function showLoading() {
            document.getElementById('resultsContainer').innerHTML = `
                <div class="loading">
                    <i class="fas fa-spinner"></i>
                    <p>Recherche en cours...</p>
                </div>
            `;
            document.getElementById('resultsTitle').textContent = 'Recherche...';
        }

        function showError(message) {
            document.getElementById('resultsContainer').innerHTML = `
                <div class="no-results">
                    <i class="fas fa-exclamation-triangle"></i>
                    <h3>Erreur</h3>
                    <p>${message}</p>
                </div>
            `;
        }

        function toggleFilters() {
            const panel = document.getElementById('filtersPanel');
            panel.classList.toggle('active');
        }

        function toggleTheme() {
            darkMode = !darkMode;
            document.body.classList.toggle('dark-mode', darkMode);
            const icon = document.getElementById('themeBtn').querySelector('i');
            icon.className = darkMode ? 'fas fa-sun' : 'fas fa-moon';
        }

        function exportResults() {
            if (currentResults.length === 0) return;

            const data = currentResults.map(result => ({
                filename: result.filename,
                filepath: result.filepath,
                score: result.score,
                matches: result.matches,
                language: result.metadata.language,
                size: result.metadata.size,
                lines: result.metadata.lines_count
            }));

            const csv = convertToCSV(data);
            downloadCSV(csv, 'search_results.csv');
        }

        function convertToCSV(data) {
            const headers = Object.keys(data[0]);
            const csvContent = [
                headers.join(','),
                ...data.map(row => headers.map(header => `"${row[header]}"`).join(','))
            ].join('\\n');
            return csvContent;
        }

        function downloadCSV(csv, filename) {
            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.setAttribute('hidden', '');
            a.setAttribute('href', url);
            a.setAttribute('download', filename);
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
        """

    def run(self, host: str = "127.0.0.1", debug: bool = False):
        """Lance le serveur web"""
        print(f" Démarrage du serveur sur http://{host}:{self.port}")
        print(f" Interface accessible à l'adresse : http://{host}:{self.port}")
        print(" Utilisez Ctrl+C pour arrêter le serveur")

        # Ouvrir automatiquement le navigateur
        if not debug:
            threading.Timer(
                1.5, lambda: webbrowser.open(f"http://{host}:{self.port}")
            ).start()

        try:
            self.app.run(host=host, port=self.port, debug=debug)
        except KeyboardInterrupt:
            print("\n Serveur arrêté")


def main():
    """Fonction principale"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Documentation Search Engine - Version Web Moderne"
    )
    parser.add_argument(
        "--port", type=int, default=8081, help="Port du serveur (défaut: 8081)"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Host du serveur (défaut: 127.0.0.1)"
    )
    parser.add_argument(
        "--project", default=".", help="Chemin du projet à analyser (défaut: .)"
    )
    parser.add_argument("--debug", action="store_true", help="Mode debug Flask")

    args = parser.parse_args()

    if not FLASK_AVAILABLE:
        print(" Flask requis pour le serveur web")
        print(" Installation : pip install flask")
        return

    print(" Documentation Search Engine - Version Web Moderne")
    print("=" * 60)

    # Créer et configurer le serveur
    server = DocumentationWebServer(port=args.port)

    # Charger le projet
    server.load_project(args.project)

    # Lancer le serveur
    server.run(host=args.host, debug=args.debug)


if __name__ == "__main__":
    main()
