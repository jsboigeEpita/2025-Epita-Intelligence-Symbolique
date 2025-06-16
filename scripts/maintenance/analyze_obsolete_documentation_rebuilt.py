"""
Script d'analyse de documentation obsolète - Version reconstruite
Oracle Enhanced v2.1.0 - Reconstruction après crash
"""

import project_core.core_from_scripts.auto_env
import os
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime

class DocumentationAnalyzer:
    """Analyseur de documentation obsolète - Version robuste"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.doc_extensions = {'.md', '.rst', '.txt', '.html'}
        self.results = {
            'analysis_timestamp': datetime.now().isoformat(),
            'project_root': str(self.project_root),
            'broken_links': [],
            'valid_links': [],
            'files_analyzed': 0,
            'total_links': 0
        }
        
        # Répertoires à ignorer pour éviter l'enlisement
        self.ignore_dirs = {
            'libs/portable_jdk',
            '.git', '__pycache__', '.pytest_cache',
            'venv', 'venv_test', '.vscode', '.vs',
            'migration_output', '_archives', '_temp',
            'argumentation_analysis_project.egg-info',
            'argumentation_analysis.egg-info'
        }
        
    def find_documentation_files(self, quick_scan=False) -> List[Path]:
        """Trouve les fichiers de documentation de manière optimisée"""
        doc_files = []
        
        if quick_scan:
            # Scan ultra-rapide - seulement les fichiers .md prioritaires
            priority_patterns = [
                'README.md',
                'docs/**/*.md',
                'CHANGELOG*.md',
                'GUIDE*.md'
            ]
            
            for pattern in priority_patterns:
                try:
                    files = list(self.project_root.glob(pattern))
                    doc_files.extend(files)
                except Exception:
                    continue
        else:
            # Scan sécurisé avec exclusions
            for ext in self.doc_extensions:
                try:
                    for file_path in self.project_root.rglob(f"*{ext}"):
                        # Vérifier si le fichier est dans un répertoire ignoré
                        if any(ignore_dir in str(file_path) for ignore_dir in self.ignore_dirs):
                            continue
                        doc_files.append(file_path)
                except Exception:
                    continue
        
        return list(set(doc_files))  # Éliminer les doublons
    
    def extract_links_from_file(self, file_path: Path) -> List[Tuple[str, int]]:
        """Extrait les liens d'un fichier de manière robuste"""
        links = []
        
        try:
            # Essayer plusieurs encodages
            content = None
            for encoding in ['utf-8', 'latin-1', 'cp1252']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    break
                except UnicodeDecodeError:
                    continue
            
            if content is None:
                return links
            
            # Patterns de liens robustes
            patterns = [
                r'\[([^\]]+)\]\(([^)]+)\)',  # Markdown [text](url)
                r'<a\s+href="([^"]+)"',      # HTML href
                r'`([^`]+\.[a-zA-Z0-9]+)`'   # Code refs
            ]
            
            lines = content.splitlines()
            for line_num, line in enumerate(lines, 1):
                for pattern in patterns:
                    try:
                        matches = re.finditer(pattern, line, re.IGNORECASE)
                        for match in matches:
                            if len(match.groups()) >= 2:
                                link = match.group(2)
                            else:
                                link = match.group(1)
                            
                            if self.is_internal_link(link):
                                links.append((link, line_num))
                    except Exception:
                        continue
                        
        except Exception:
            pass
        
        return links
    
    def is_internal_link(self, link: str) -> bool:
        """Détermine si un lien est interne (conservateur)"""
        if not link:
            return False
            
        # Exclure les liens externes évidents
        external_prefixes = [
            'http://', 'https://', 'ftp://', 'mailto:',
            'tel:', 'sms:', 'javascript:', 'data:'
        ]
        
        for prefix in external_prefixes:
            if link.lower().startswith(prefix):
                return False
        
        # Exclure les ancres pures
        if link.startswith('#'):
            return False
            
        # Exclure les liens très courts
        if len(link) < 3:
            return False
            
        return True
    
    def check_link_exists(self, link: str, from_file: Path) -> bool:
        """Vérifie si un lien existe de manière robuste"""
        try:
            # Nettoyer le lien
            link = link.strip().split('#')[0]
            
            if not link:
                return True
            
            # Résolution du chemin
            if link.startswith('/'):
                # Lien absolu depuis la racine
                target_path = self.project_root / link.lstrip('/')
            else:
                # Lien relatif
                target_path = (from_file.parent / link).resolve()
            
            return target_path.exists()
            
        except Exception:
            # En cas de doute, considérer comme valide
            return True
    
    def analyze_documentation(self, quick_scan=False) -> Dict:
        """Analyse principale de la documentation"""
        print(f"Analyse {'rapide' if quick_scan else 'complète'} de la documentation...")
        
        doc_files = self.find_documentation_files(quick_scan)
        print(f"{len(doc_files)} fichiers de documentation trouvés")
        
        self.results['files_analyzed'] = len(doc_files)
        
        for i, doc_file in enumerate(doc_files):
            try:
                if i % 50 == 0:  # Progrès tous les 50 fichiers
                    print(f"Progress: {i+1}/{len(doc_files)}")
                
                links = self.extract_links_from_file(doc_file)
                
                for link, line_num in links:
                    self.results['total_links'] += 1
                    
                    link_info = {
                        'link': link,
                        'source_file': str(doc_file.relative_to(self.project_root)),
                        'line_number': line_num
                    }
                    
                    if self.check_link_exists(link, doc_file):
                        self.results['valid_links'].append(link_info)
                    else:
                        self.results['broken_links'].append(link_info)
                        
            except Exception:
                continue
        
        # Calculer les statistiques
        total_links = self.results['total_links']
        broken_count = len(self.results['broken_links'])
        valid_count = len(self.results['valid_links'])
        
        self.results['summary'] = {
            'total_links': total_links,
            'broken_links': broken_count,
            'valid_links': valid_count,
            'broken_percentage': (broken_count / total_links * 100) if total_links > 0 else 0
        }
        
        return self.results
    
    def generate_report(self, output_file: str = None) -> str:
        """Génère un rapport de documentation"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"logs/documentation_analysis_{timestamp}.md"
        
        # Créer le dossier si nécessaire
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        summary = self.results.get('summary', {})
        
        report = f"""# Rapport d'Analyse de Documentation
## Oracle Enhanced v2.1.0 - Reconstruction

**Date d'analyse :** {self.results['analysis_timestamp']}  
**Racine du projet :** `{self.results['project_root']}`

## Résumé

- **Fichiers analysés :** {self.results['files_analyzed']}
- **Liens totaux :** {summary.get('total_links', 0)}
- **Liens brisés :** {summary.get('broken_links', 0)} ({summary.get('broken_percentage', 0):.1f}%)
- **Liens valides :** {summary.get('valid_links', 0)}

## Liens Brisés (Top 20)

"""
        
        # Afficher les 20 premiers liens brisés
        broken_links = self.results['broken_links'][:20]
        
        if broken_links:
            for i, broken_link in enumerate(broken_links, 1):
                report += f"""### {i}. {broken_link['link']}
- **Fichier :** `{broken_link['source_file']}` (ligne {broken_link['line_number']})

"""
        else:
            report += "Aucun lien brisé détecté !\n\n"
        
        if len(self.results['broken_links']) > 20:
            report += f"\n*... et {len(self.results['broken_links']) - 20} autres liens brisés*\n\n"
        
        report += """## Actions Recommandées

1. **Examiner les liens brisés** listés ci-dessus
2. **Corriger ou supprimer** les références obsolètes
3. **Re-exécuter l'analyse** après corrections

---
*Rapport généré par Oracle Enhanced v2.1.0 Documentation Analyzer (Version reconstruite)*
"""
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report)
            print(f"Rapport sauvegardé: {output_file}")
        except Exception as e:
            print(f"Erreur sauvegarde rapport: {e}")
        
        return output_file


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="Analyse de documentation obsolète (Version reconstruite)")
    parser.add_argument('--quick-scan', action='store_true', help='Analyse rapide (.md prioritaires)')
    parser.add_argument('--full-analysis', action='store_true', help='Analyse complète')
    parser.add_argument('--output', help='Fichier de sortie')
    
    args = parser.parse_args()
    
    analyzer = DocumentationAnalyzer()
    
    # Mode d'analyse
    quick_mode = args.quick_scan or not args.full_analysis
    
    try:
        results = analyzer.analyze_documentation(quick_scan=quick_mode)
        report_file = analyzer.generate_report(args.output)
        
        # Résumé console
        summary = results.get('summary', {})
        print(f"\nRÉSULTATS:")
        print(f"   Fichiers: {results['files_analyzed']}")
        print(f"   Liens totaux: {summary.get('total_links', 0)}")
        print(f"   Liens brisés: {summary.get('broken_links', 0)}")
        print(f"   Qualité: {100 - summary.get('broken_percentage', 0):.1f}%")
        print(f"   Rapport: {report_file}")
        
        return 0 if summary.get('broken_links', 0) == 0 else 1
        
    except Exception as e:
        print(f"Erreur analyse: {e}")
        return 2


if __name__ == "__main__":
    exit(main())