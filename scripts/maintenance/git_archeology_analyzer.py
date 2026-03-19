#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script pour l'archéologie Git automatisée du système d'analyse rhétorique.
Ce script explore l'historique Git de manière itérative pour identifier les
fichiers et les commits les plus pertinents liés à une fonctionnalité donnée.
"""

import subprocess
import re
from collections import defaultdict
from dataclasses import dataclass, field, asdict
import json
from pathlib import Path
from datetime import datetime

# Mots-clés initiaux pour démarrer la recherche
INITIAL_KEYWORDS = [
    'rhetoric',
    'argumentation',
    'fallacy',
    'fallacies',
    'persuasion',
    'tweety',
    'propositional',
    'first_order',
    'logique',
    'sherlock',
    'watson',
    'main_orchestrator'
]

# Patterns de fichiers à ignorer pour réduire le bruit
# Les fichiers de documentation, de configuration générale, etc.
EXCLUDED_FILE_PATTERNS = [
    r'\.md$', 
    r'README.*', 
    r'\.gitignore$', 
    r'requirements\.txt$',
    r'pyproject\.toml$',
    r'poetry\.lock$',
    r'docs/',
    r'\.vscode/'
]

# Mots-clés dans les messages de commit qui augmentent le score de pertinence
COMMIT_MESSAGE_BOOST = {
    'refactor': 2.0,
    'architecture': 3.0,
    'feat': 1.5,
    'fix': 1.0,
    'perf': 1.5,
    'rework': 2.5,
    'design': 2.5
}

# --- Constantes pour le Caching ---
CACHE_ENABLED = True
CACHE_DIR = "_temp/git_archeology_cache"


@dataclass
class AnalyzedFile:
    path: str
    relevance_score: float = 0.0
    commit_count: int = 0
    last_modified: str = ""
    creation_commit: str = ""

@dataclass
class AnalyzedCommit:
    sha: str
    message: str
    date: str
    author: str
    relevance_score: float = 0.0
    files_changed: list[str] = field(default_factory=list)
    
class GitArcheologyAnalyzer:
    """
    Analyse l'historique Git pour reconstruire l'évolution d'une fonctionnalité.
    """
    def __init__(self, project_root="."):
        self.project_root = Path(project_root).resolve()
        self.cache_path = self.project_root / CACHE_DIR
        if CACHE_ENABLED:
            self.cache_path.mkdir(exist_ok=True)
            
        self.analyzed_files = {}
        self.analyzed_commits = {}
        self.processed_commits = set()

    def run_git_command(self, command: list[str]) -> str:
        """Exécute une commande Git et retourne sa sortie."""
        try:
            result = subprocess.run(
                ['git'] + command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=False, # Ne pas lever d'erreur si le code de sortie n'est pas 0
                encoding='utf-8'
            )
            if result.returncode != 0 and "fatal:" in result.stderr:
                 print(f"Erreur Git: {result.stderr.strip()}")
                 return ""
            return result.stdout.strip()
        except FileNotFoundError as e:
            print(f"Erreur : git n'est pas installé ou n'est pas dans le PATH. {e}")
            return ""

    def is_file_excluded(self, file_path: str) -> bool:
        """Vérifie si un fichier doit être exclu de l'analyse."""
        for pattern in EXCLUDED_FILE_PATTERNS:
            if re.search(pattern, file_path, re.IGNORECASE):
                return True
        return False

    def get_file_creation_info(self, file_path: str) -> tuple[str, str]:
        """Retourne le SHA et la date du commit de création d'un fichier."""
        # --follow est important pour suivre les renommages
        # --diff-filter=A pour ne montrer que l'ajout
        format_str = "%H%x1f%ad"
        command = ['log', '--all', '--follow', '--diff-filter=A', f'--pretty=format:{format_str}', '--', file_path]
        output = self.run_git_command(command)
        
        if not output:
            return "unknown", "unknown"
            
        # Le premier commit est le plus récent, on prend le dernier de la liste
        first_commit_line = output.split('\n')[-1]
        try:
            sha, date = first_commit_line.split('\x1f')
            return sha, date
        except ValueError:
            return "unknown", "unknown"

    def find_initial_commits(self) -> list[str]:
        """Trouve les SHAs des commits initiaux en se basant sur les chemins de fichiers correspondants aux mots-clés."""
        print(f"🔍 Recherche des commits initiaux via les chemins de fichiers contenant les mots-clés...")

        # Construire des 'pathspecs' pour git log. Exemple: '*keyword*'
        pathspecs = [f'*{keyword}*' for keyword in INITIAL_KEYWORDS]
        
        format_str = "%H"
        command = [
            'log',
            '--all',
            f'--pretty=format:{format_str}',
            '--', # Séparateur pour indiquer que ce qui suit sont des chemins
        ] + pathspecs
        
        output = self.run_git_command(command)
        
        if not output:
            print("Aucun commit initial trouvé via les chemins de fichiers.")
            return []
            
        # Utiliser un set pour dédupliquer les commits
        commits = sorted(list(set(output.split('\n'))))
        print(f"✅ {len(commits)} commits initiaux trouvés.")
        return commits

    def run_analysis(self):
        """Orchestre le processus d'analyse archéologique."""
        print("🚀 Démarrage de l'analyse archéologique Git...")
        
        initial_commits = self.find_initial_commits()
        if not initial_commits:
            # S'il n'y a pas de commits, on génère un rapport vide et on arrête.
            print("Aucun commit initial n'a été trouvé. L'analyse ne peut pas continuer.")
            # La génération du rapport est maintenant gérée à la fin de la méthode.
            return

        commit_queue = list(initial_commits)
        
        while commit_queue:
            commit_sha = commit_queue.pop(0)
            if commit_sha in self.processed_commits:
                continue
            
            commit_data = self.analyze_commit(commit_sha)
            if not commit_data:
                continue

            # Trouver de nouveaux commits liés aux fichiers de ce commit
            related_commits = self.find_related_commits(commit_data.files_changed)
            for related_sha in related_commits:
                if related_sha not in self.processed_commits:
                    commit_queue.append(related_sha)
            
            # Mettre à jour les scores
            self.score_commit(commit_data)
            for file_path in commit_data.files_changed:
                self.score_file(self.analyzed_files[file_path])

        print(f"✅ Analyse terminée. {len(self.processed_commits)} commits traités.")
        
        # Toujours générer un rapport, même s'il est vide
        self.generate_report(output_dir="docs/audit")

    def analyze_commit(self, commit_sha: str) -> AnalyzedCommit or None:
        """
        Analyse un commit en utilisant un système de cache pour éviter de répéter les appels Git.
        """
        if commit_sha in self.processed_commits:
            return None

        # --- Logique de Cache ---
        commit_cache_file = self.cache_path / f"{commit_sha}.json"
        if CACHE_ENABLED and commit_cache_file.exists():
            print(f"... Cache hit for commit {commit_sha[:7]}")
            with open(commit_cache_file, 'r', encoding='utf-8') as f:
                commit_dict = json.load(f)
                commit_data = AnalyzedCommit(**commit_dict)
        else:
            print(f"🔬 Analysing commit {commit_sha[:7]}...")
            # Format: Author<sep>Date<sep>Message Body<sep>Liste Fichiers
            format_str = "%an%x1f%aI%x1f%B" # aI: date ISO 8601, B: corps du message
            command = ['show', f'--pretty=format:{format_str}', '--name-only', commit_sha]
            
            output = self.run_git_command(command)
            if not output:
                self.processed_commits.add(commit_sha)
                return None
            try:
                header_and_files = output.split('\n\n', 1)
                header_full = header_and_files[0]
                files_part = header_and_files[1] if len(header_and_files) > 1 else ""
                
                header_fields = header_full.split('\x1f')
                author = header_fields[0]
                date = header_fields[1]
                message = '\n'.join(header_fields[2:])
                files_changed = [f for f in files_part.split('\n') if f and not self.is_file_excluded(f)]
            except (ValueError, IndexError) as e:
                print(f"  Skipping commit {commit_sha[:7]}: malformed output. Error: {e}")
                self.processed_commits.add(commit_sha)
                return None

            if not files_changed:
                self.processed_commits.add(commit_sha)
                return None

            commit_data = AnalyzedCommit(
                sha=commit_sha,
                author=author.strip(),
                date=date.strip(),
                message=message.strip(),
                files_changed=files_changed
            )
            
            if CACHE_ENABLED:
                with open(commit_cache_file, 'w', encoding='utf-8') as f:
                    json.dump(asdict(commit_data), f, indent=2)

        # --- Traitement post-analyse (commun au cache et à la nouvelle analyse) ---
        self.analyzed_commits[commit_sha] = commit_data
        self.processed_commits.add(commit_sha)
        
        for file_path in commit_data.files_changed:
            if file_path not in self.analyzed_files:
                self.analyzed_files[file_path] = AnalyzedFile(path=file_path)
            self.analyzed_files[file_path].commit_count += 1
        
        return commit_data

    def find_related_commits(self, file_paths: list[str]) -> list[str]:
        """Trouve tous les commits qui ont modifié les fichiers donnés."""
        if not file_paths:
            return []
            
        # On ne veut que le SHA des commits
        command = ['log', '--pretty=%H', '--all', '--'] + file_paths
        output = self.run_git_command(command)
        
        return output.split('\n') if output else []

    def score_commit(self, commit: AnalyzedCommit):
        """Calcule et met à jour le score de pertinence d'un commit."""
        score = 1.0 # Score de base
        
        # Augmenter le score pour les mots-clés dans le message
        commit_message_lower = commit.message.lower()
        for keyword, boost in COMMIT_MESSAGE_BOOST.items():
            if keyword in commit_message_lower:
                score *= boost
        
        # Augmenter le score en fonction du nombre de fichiers modifiés
        score += len(commit.files_changed) * 0.1
        
        commit.relevance_score = score

    def score_file(self, file_analysis: AnalyzedFile):
        """Calcule et met à jour le score de pertinence d'un fichier."""
        # Score basé sur le nombre de commits
        score = file_analysis.commit_count * 1.0
        
        # Ajouter le score des commits qui ont modifié ce fichier
        total_commit_score = 0
        commits_for_file = self.run_git_command(['log', '--pretty=%H', '--', file_analysis.path]).split('\n')
        
        for commit_sha in commits_for_file:
            if commit_sha in self.analyzed_commits:
                total_commit_score += self.analyzed_commits[commit_sha].relevance_score
        
        score += total_commit_score * 0.2
        
        file_analysis.relevance_score = score

    def enrich_file_data(self):
        """Ajoute des informations supplémentaires aux fichiers analysés."""
        print("Enriching file data...")
        for i, file_analysis in enumerate(self.analyzed_files.values()):
            print(f"  ({i+1}/{len(self.analyzed_files)}) Enriching {file_analysis.path}...")
            sha, date = self.get_file_creation_info(file_analysis.path)
            file_analysis.creation_commit = sha
            file_analysis.last_modified = date # Note: this is creation date, should be improved

    def generate_report(self, output_dir="."):
        """Génère les rapports finaux de l'analyse."""
        report_path = Path(output_dir) / "git_archeology_report.json"
        
        self.enrich_file_data()
        
        # Trier les fichiers et commits par score de pertinence
        sorted_files = sorted(
            self.analyzed_files.values(),
            key=lambda f: f.relevance_score,
            reverse=True
        )
        
        sorted_commits = sorted(
            self.analyzed_commits.values(),
            key=lambda c: c.relevance_score,
            reverse=True
        )

        report_data = {
            "metadata": {
                "project": "Analyse Rhétorique",
                "generated_at": datetime.now().isoformat(),
                "initial_keywords": INITIAL_KEYWORDS,
                "total_files_analyzed": len(self.analyzed_files),
                "total_commits_processed": len(self.processed_commits)
            },
            "key_components": [asdict(f) for f in sorted_files[:50]], # Top 50 files
            "architectural_timeline": [asdict(c) for c in sorted_commits[:100]] # Top 100 commits
        }
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
            
        print(f"📄 Rapport d'archéologie généré : {report_path}")


def main():
    """Point d'entrée principal du script."""
    output_directory = "docs/audit"
    Path(output_directory).mkdir(exist_ok=True)
    
    analyzer = GitArcheologyAnalyzer()
    analyzer.run_analysis()

if __name__ == "__main__":
    main()
