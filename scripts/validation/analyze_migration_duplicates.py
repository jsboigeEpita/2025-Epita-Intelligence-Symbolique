#!/usr/bin/env python3
"""
Analyse des Scripts Dupliqués après Migration
==============================================

Ce script analyse les fichiers restaurés depuis archived_scripts/obsolete_migration_2025/
vers scripts/ et identifie les doublons, avec recommandations de nettoyage.

Fonctionnalités :
- Comparaison fichier par fichier (nom, taille, contenu, hash)
import argumentation_analysis.core.environment
- Identification des doublons exacts vs. modifiés
- Analyse des dépendances et références
- Génération de rapport détaillé avec recommandations
- Script de nettoyage sécurisé

Auteur: Roo
Date: 10/06/2025
"""

import os
import sys
import json
import hashlib
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
import difflib

# Fix encoding issues on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

@dataclass
class FileMetadata:
    """Métadonnées d'un fichier."""
    path: str
    size: int
    modified: float
    hash_md5: str
    hash_sha256: str
    line_count: int
    encoding: str = 'utf-8'

@dataclass
class DuplicateAnalysis:
    """Analyse d'un doublon détecté."""
    filename: str
    scripts_file: FileMetadata
    archived_file: FileMetadata
    is_exact_duplicate: bool
    size_difference: int
    time_difference: float
    content_similarity: float
    references_found: List[str]
    recommendation: str
    justification: str
    action_priority: int  # 1=urgent, 2=recommandé, 3=à évaluer

@dataclass
class AnalysisReport:
    """Rapport complet d'analyse."""
    timestamp: str
    total_scripts_files: int
    total_archived_files: int
    exact_duplicates: int
    modified_duplicates: int
    unique_scripts: int
    unique_archived: int
    recommendations: Dict[str, int]
    duplicates: List[DuplicateAnalysis]
    orphaned_files: List[str]

class MigrationDuplicateAnalyzer:
    """Analyseur de doublons de migration."""
    
    def __init__(self):
        # Si on exécute depuis scripts/, remonter à la racine du projet
        current_dir = Path.cwd()
        if current_dir.name == "scripts":
            self.project_root = current_dir.parent
        else:
            self.project_root = current_dir
            
        self.scripts_dir = self.project_root / "scripts"
        self.archived_dir = self.project_root / "archived_scripts" / "obsolete_migration_2025"
        self.archived_scripts_dir = self.archived_dir / "scripts"
        
        # Patterns de fichiers à ignorer
        self.ignore_patterns = {
            r'__pycache__',
            r'\.pyc$',
            r'\.pyo$',
            r'\.log$',
            r'\.tmp$',
            r'\.bak$'
        }
        
        # Patterns de scripts temporaires/obsolètes
        self.obsolete_patterns = {
            r'^fix_.*\.py$',
            r'^migrate_.*\.py$',
            r'^diagnostic_.*\.py$',
            r'^temp_.*\.py$',
            r'^old_.*\.py$',
            r'^backup_.*\.py$'
        }
        
        # Cache pour éviter de relire les fichiers
        self.file_cache: Dict[str, FileMetadata] = {}
        
    def should_ignore_file(self, filepath: Path) -> bool:
        """Détermine si un fichier doit être ignoré."""
        file_str = str(filepath)
        return any(re.search(pattern, file_str) for pattern in self.ignore_patterns)
    
    def is_likely_obsolete(self, filename: str) -> bool:
        """Détermine si un fichier semble obsolète par son nom."""
        return any(re.match(pattern, filename) for pattern in self.obsolete_patterns)
    
    def calculate_file_hash(self, filepath: Path) -> Tuple[str, str]:
        """Calcule les hash MD5 et SHA256 d'un fichier."""
        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()
        
        try:
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    md5_hash.update(chunk)
                    sha256_hash.update(chunk)
        except Exception as e:
            print(f"[WARNING] Erreur lecture {filepath}: {e}")
            return "error", "error"
            
        return md5_hash.hexdigest(), sha256_hash.hexdigest()
    
    def get_file_metadata(self, filepath: Path) -> Optional[FileMetadata]:
        """Récupère les métadonnées complètes d'un fichier."""
        if not filepath.exists() or not filepath.is_file():
            return None
            
        cache_key = str(filepath)
        if cache_key in self.file_cache:
            return self.file_cache[cache_key]
        
        try:
            stat = filepath.stat()
            md5_hash, sha256_hash = self.calculate_file_hash(filepath)
            
            # Compter les lignes si c'est un fichier texte
            line_count = 0
            encoding = 'utf-8'
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    line_count = sum(1 for _ in f)
            except UnicodeDecodeError:
                try:
                    with open(filepath, 'r', encoding='latin-1') as f:
                        line_count = sum(1 for _ in f)
                        encoding = 'latin-1'
                except Exception:
                    line_count = -1  # Fichier binaire
                    encoding = 'binary'
            
            metadata = FileMetadata(
                path=str(filepath),
                size=stat.st_size,
                modified=stat.st_mtime,
                hash_md5=md5_hash,
                hash_sha256=sha256_hash,
                line_count=line_count,
                encoding=encoding
            )
            
            self.file_cache[cache_key] = metadata
            return metadata
            
        except Exception as e:
            print(f"⚠️ Erreur métadonnées {filepath}: {e}")
            return None
    
    def find_all_files(self, directory: Path) -> Dict[str, FileMetadata]:
        """Trouve tous les fichiers dans un répertoire avec leurs métadonnées."""
        files = {}
        
        if not directory.exists():
            print(f"[WARNING] Répertoire inexistant: {directory}")
            return files
        
        for filepath in directory.rglob("*"):
            if filepath.is_file() and not self.should_ignore_file(filepath):
                # Utilise le chemin relatif comme clé
                rel_path = filepath.relative_to(directory)
                metadata = self.get_file_metadata(filepath)
                if metadata:
                    files[str(rel_path)] = metadata
                    
        return files
    
    def calculate_content_similarity(self, file1: Path, file2: Path) -> float:
        """Calcule la similarité de contenu entre deux fichiers texte."""
        try:
            with open(file1, 'r', encoding='utf-8') as f1:
                content1 = f1.readlines()
            with open(file2, 'r', encoding='utf-8') as f2:
                content2 = f2.readlines()
                
            # Utilise difflib pour calculer la similarité
            matcher = difflib.SequenceMatcher(None, content1, content2)
            return matcher.ratio()
            
        except Exception:
            # Si erreur de lecture, compare juste les hash
            return 1.0 if file1.stat().st_size == file2.stat().st_size else 0.0
    
    def find_references_to_file(self, filename: str) -> List[str]:
        """Recherche les références à un fichier dans le projet."""
        references = []
        base_name = Path(filename).stem
        
        # Recherche dans plusieurs répertoires
        search_dirs = [
            self.project_root / "scripts",
            self.project_root / "project_core",
            self.project_root / "tests",
            self.project_root / "config",
            self.project_root / "docs"
        ]
        
        patterns = [
            f'import.*{base_name}',
            f'from.*{base_name}',
            f'{base_name}\\.py',
            f'"{filename}"',
            f"'{filename}'"
        ]
        
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue
                
            for py_file in search_dir.rglob("*.py"):
                if py_file.name == filename:
                    continue  # Ignore le fichier lui-même
                
                # Ignore les fichiers d'analyse/nettoyage
                if any(x in py_file.name for x in ['analyze_migration_duplicates', 'cleanup_migration_duplicates']):
                    continue
                    
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    for pattern in patterns:
                        if re.search(pattern, content, re.IGNORECASE):
                            references.append(str(py_file.relative_to(self.project_root)))
                            break
                            
                except Exception:
                    continue
                    
        return references
    
    def analyze_duplicate(self, filename: str, scripts_meta: FileMetadata, 
                         archived_meta: FileMetadata) -> DuplicateAnalysis:
        """Analyse un doublon détecté."""
        
        # Vérifications de base
        is_exact = (scripts_meta.hash_sha256 == archived_meta.hash_sha256)
        size_diff = scripts_meta.size - archived_meta.size
        time_diff = scripts_meta.modified - archived_meta.modified
        
        # Similarité de contenu si pas exactement identique
        similarity = 1.0 if is_exact else self.calculate_content_similarity(
            Path(scripts_meta.path), Path(archived_meta.path)
        )
        
        # Recherche de références
        references = self.find_references_to_file(filename)
        
        # Détermine la recommandation
        recommendation, justification, priority = self._determine_recommendation(
            filename, is_exact, time_diff, references, similarity
        )
        
        return DuplicateAnalysis(
            filename=filename,
            scripts_file=scripts_meta,
            archived_file=archived_meta,
            is_exact_duplicate=is_exact,
            size_difference=size_diff,
            time_difference=time_diff,
            content_similarity=similarity,
            references_found=references,
            recommendation=recommendation,
            justification=justification,
            action_priority=priority
        )
    
    def _determine_recommendation(self, filename: str, is_exact: bool, 
                                time_diff: float, references: List[str],
                                similarity: float) -> Tuple[str, str, int]:
        """Détermine la recommandation pour un fichier."""
        
        # Cas 1: Doublon exact
        if is_exact:
            if len(references) == 0:
                return ("SUPPRIMER",
                       "Doublon exact sans références actives", 1)
            elif len(references) <= 2 and time_diff > 0:
                # Peu de références et modifié après archivage (restauration automatique)
                return ("SUPPRIMER",
                       f"Doublon exact avec seulement {len(references)} références mineures", 1)
            else:
                return ("ÉVALUER",
                       f"Doublon exact mais {len(references)} références trouvées", 3)
        
        # Cas 2: Fichier modifié récemment (< 1 jour)
        if time_diff > 0 and time_diff < 86400:  # 24h
            return ("CONSERVER", 
                   "Modifié récemment, probablement version active", 1)
        
        # Cas 3: Fichier non modifié depuis archivage
        if time_diff <= 0:
            if self.is_likely_obsolete(filename):
                return ("SUPPRIMER", 
                       "Non modifié depuis archivage et pattern obsolète", 1)
            else:
                return ("ÉVALUER", 
                       "Non modifié mais nom ne suggère pas obsolescence", 2)
        
        # Cas 4: Modifications mineures
        if similarity > 0.95:
            return ("ÉVALUER", 
                   f"Modifications mineures (similarité {similarity:.1%})", 2)
        
        # Cas 5: Modifications substantielles
        return ("CONSERVER", 
               f"Modifications substantielles (similarité {similarity:.1%})", 1)
    
    def run_analysis(self) -> AnalysisReport:
        """Lance l'analyse complète."""
        print("[ANALYSE] Démarrage de l'analyse des doublons de migration...")
        
        # 1. Collecte des fichiers
        print("[SCAN] Collecte des fichiers scripts/...")
        scripts_files = self.find_all_files(self.scripts_dir)
        
        print("[SCAN] Collecte des fichiers archived_scripts/obsolete_migration_2025/scripts/...")
        archived_files = self.find_all_files(self.archived_scripts_dir)
        
        print(f"[INFO] {len(scripts_files)} fichiers dans scripts/")
        print(f"[INFO] {len(archived_files)} fichiers dans archived/")
        
        # 2. Identification des doublons
        print("[COMPARE] Identification des doublons...")
        duplicates = []
        
        for filename, scripts_meta in scripts_files.items():
            if filename in archived_files:
                archived_meta = archived_files[filename]
                duplicate_analysis = self.analyze_duplicate(
                    filename, scripts_meta, archived_meta
                )
                duplicates.append(duplicate_analysis)
        
        # 3. Fichiers orphelins
        scripts_only = set(scripts_files.keys()) - set(archived_files.keys())
        archived_only = set(archived_files.keys()) - set(scripts_files.keys())
        
        # 4. Statistiques
        exact_dupes = sum(1 for d in duplicates if d.is_exact_duplicate)
        modified_dupes = len(duplicates) - exact_dupes
        
        recommendations = {
            "SUPPRIMER": sum(1 for d in duplicates if d.recommendation == "SUPPRIMER"),
            "CONSERVER": sum(1 for d in duplicates if d.recommendation == "CONSERVER"),
            "ÉVALUER": sum(1 for d in duplicates if d.recommendation == "ÉVALUER")
        }
        
        report = AnalysisReport(
            timestamp=datetime.now().isoformat(),
            total_scripts_files=len(scripts_files),
            total_archived_files=len(archived_files),
            exact_duplicates=exact_dupes,
            modified_duplicates=modified_dupes,
            unique_scripts=len(scripts_only),
            unique_archived=len(archived_only),
            recommendations=recommendations,
            duplicates=duplicates,
            orphaned_files=list(scripts_only) + [f"archived:{f}" for f in archived_only]
        )
        
        return report
    
    def generate_report(self, report: AnalysisReport) -> str:
        """Génère un rapport markdown détaillé."""
        
        md_content = f"""# Rapport d'Analyse des Doublons de Migration

**Généré le** : {report.timestamp}

## Résumé Exécutif

- **Fichiers dans scripts/** : {report.total_scripts_files}
- **Fichiers dans archived/** : {report.total_archived_files}
- **Doublons exacts** : {report.exact_duplicates}
- **Doublons modifiés** : {report.modified_duplicates}
- **Fichiers uniques scripts/** : {report.unique_scripts}
- **Fichiers uniques archived/** : {report.unique_archived}

## Recommandations d'Action

"""
        
        for action, count in report.recommendations.items():
            emoji = {"SUPPRIMER": "🗑️", "CONSERVER": "✅", "ÉVALUER": "⚠️"}
            md_content += f"- **{emoji.get(action, '❓')} {action}** : {count} fichiers\n"
        
        md_content += "\n## Analyse Détaillée des Doublons\n\n"
        
        # Groupe par recommandation
        for action in ["SUPPRIMER", "ÉVALUER", "CONSERVER"]:
            action_duplicates = [d for d in report.duplicates if d.recommendation == action]
            if not action_duplicates:
                continue
                
            emoji = {"SUPPRIMER": "🗑️", "CONSERVER": "✅", "ÉVALUER": "⚠️"}
            md_content += f"### {emoji.get(action, '❓')} Action Recommandée : {action}\n\n"
            
            for dup in sorted(action_duplicates, key=lambda x: x.action_priority):
                status = "EXACT" if dup.is_exact_duplicate else f"SIMILAIRE ({dup.content_similarity:.1%})"
                
                md_content += f"""#### `{dup.filename}`

- **Statut** : {status}
- **Taille** : scripts={dup.scripts_file.size}B, archived={dup.archived_file.size}B (diff: {dup.size_difference:+d}B)
- **Modification** : {dup.time_difference:+.1f}s après archivage
- **Références** : {len(dup.references_found)} trouvées
- **Justification** : {dup.justification}

"""
                if dup.references_found:
                    md_content += "**Fichiers référençant** :\n"
                    for ref in dup.references_found:
                        md_content += f"  - `{ref}`\n"
                    md_content += "\n"
        
        md_content += "\n## Fichiers Orphelins\n\n"
        
        if report.orphaned_files:
            for orphan in sorted(report.orphaned_files):
                md_content += f"- `{orphan}`\n"
        else:
            md_content += "*Aucun fichier orphelin détecté.*\n"
        
        return md_content
    
    def generate_cleanup_script(self, report: AnalysisReport) -> str:
        """Génère un script de nettoyage sécurisé."""
        
        files_to_delete = [d.filename for d in report.duplicates 
                          if d.recommendation == "SUPPRIMER"]
        
        script_content = f'''#!/usr/bin/env python3
"""
Script de Nettoyage Sécurisé - Doublons de Migration
===================================================

Script généré automatiquement le {report.timestamp}
Supprime {len(files_to_delete)} fichiers identifiés comme doublons obsolètes.

ATTENTION: Ce script crée une sauvegarde avant suppression !
"""

import os
import shutil
import json
from datetime import datetime
from pathlib import Path

def create_backup():
    """Crée une sauvegarde complète avant suppression."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"backup_before_cleanup_{{timestamp}}")
    backup_dir.mkdir(exist_ok=True)
    
    print(f"📦 Création de la sauvegarde dans {{backup_dir}}")
    
    # Sauvegarde du répertoire scripts complet
    scripts_backup = backup_dir / "scripts"
    shutil.copytree("scripts", scripts_backup)
    
    # Sauvegarde du rapport d'analyse
    shutil.copy("reports/migration_duplicates_analysis.md", backup_dir)
    
    print(f"✅ Sauvegarde créée: {{backup_dir}}")
    return backup_dir

def main():
    """Exécute le nettoyage sécurisé."""
    
    files_to_delete = {files_to_delete}
    
    print(f"🗑️ Nettoyage de {{len(files_to_delete)}} doublons identifiés")
    
    # 1. Créer la sauvegarde
    backup_dir = create_backup()
    
    # 2. Confirmation utilisateur
    print("\\n📋 Fichiers à supprimer:")
    for filename in sorted(files_to_delete):
        print(f"  - {{filename}}")
    
    confirm = input("\\n❓ Confirmer la suppression ? (yes/NO): ")
    if confirm.lower() != 'yes':
        print("❌ Nettoyage annulé")
        return
    
    # 3. Suppression avec log
    deleted_files = []
    errors = []
    
    for filename in files_to_delete:
        filepath = Path("scripts") / filename
        try:
            if filepath.exists():
                filepath.unlink()
                deleted_files.append(filename)
                print(f"✅ Supprimé: {{filename}}")
            else:
                print(f"⚠️ Déjà absent: {{filename}}")
        except Exception as e:
            errors.append(f"{{filename}}: {{e}}")
            print(f"❌ Erreur: {{filename}} - {{e}}")
    
    # 4. Rapport final
    report = {{
        "timestamp": datetime.now().isoformat(),
        "backup_location": str(backup_dir),
        "files_deleted": deleted_files,
        "errors": errors,
        "total_deleted": len(deleted_files)
    }}
    
    # Sauvegarde du rapport
    with open(backup_dir / "cleanup_report.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\\n📊 Nettoyage terminé:")
    print(f"  - {{len(deleted_files)}} fichiers supprimés")
    print(f"  - {{len(errors)}} erreurs")
    print(f"  - Sauvegarde: {{backup_dir}}")

if __name__ == "__main__":
    main()
'''
        
        return script_content

def main():
    """Fonction principale."""
    analyzer = MigrationDuplicateAnalyzer()
    
    # Création des répertoires de sortie
    reports_dir = analyzer.project_root / "reports"
    reports_dir.mkdir(exist_ok=True)
    
    # Lance l'analyse
    report = analyzer.run_analysis()
    
    # Génère le rapport Markdown
    print("📝 Génération du rapport...")
    md_report = analyzer.generate_report(report)
    
    report_file = reports_dir / "migration_duplicates_analysis.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(md_report)
    
    # Génère le script de nettoyage
    print("🛠️ Génération du script de nettoyage...")
    cleanup_script = analyzer.generate_cleanup_script(report)
    
    cleanup_file = reports_dir / "cleanup_migration_duplicates.py"
    with open(cleanup_file, 'w', encoding='utf-8') as f:
        f.write(cleanup_script)
    
    # Sauvegarde des données JSON pour analyse programmatique
    json_file = reports_dir / "migration_duplicates_data.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False)
    
    print(f"\n🎉 Analyse terminée !")
    print(f"📄 Rapport détaillé : {report_file}")
    print(f"🛠️ Script de nettoyage : {cleanup_file}")
    print(f"📊 Données JSON : {json_file}")
    
    # Résumé rapide
    print(f"\n📊 Résumé:")
    print(f"  - {report.exact_duplicates} doublons exacts")
    print(f"  - {report.modified_duplicates} doublons modifiés")
    print(f"  - {report.recommendations['SUPPRIMER']} fichiers à supprimer")
    print(f"  - {report.recommendations['ÉVALUER']} fichiers à évaluer")
    print(f"  - {report.recommendations['CONSERVER']} fichiers à conserver")

if __name__ == "__main__":
    main()