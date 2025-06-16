"""
Script d'analyse de documentation obsolète via liens internes brisés
Oracle Enhanced v2.1.0 - Maintenance Documentation
"""

import project_core.core_from_scripts.auto_env
import os
import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Set
from datetime import datetime
import glob

class DocumentationLinkAnalyzer:
    """Analyseur de liens dans la documentation"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.doc_extensions = {'.md', '.rst', '.txt', '.html'}
        self.link_patterns = [
            # Liens Markdown
            r'\[([^\]]+)\]\(([^)]+)\)',
            # Liens HTML
            r'<a\s+href="([^"]+)"',
            # Références de code avec chemins
            r'`([^`]+\.[a-zA-Z0-9]+)`',
            # Liens relatifs explicites
            r'(?:\.\.?/[^)\s]+)',
        ]
        
    def find_documentation_files(self) -> List[Path]:
        """Trouve tous les fichiers de documentation"""
        doc_files = []
        for ext in self.doc_extensions:
            pattern = f"**/*{ext}"
            doc_files.extend(self.project_root.glob(pattern))
        return doc_files
    
    def extract_links_from_file(self, file_path: Path) -> List[Tuple[str, int]]:
        """Extrait les liens internes d'un fichier"""
        links = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for line_num, line in enumerate(content.splitlines(), 1):
                for pattern in self.link_patterns:
                    matches = re.finditer(pattern, line)
                    for match in matches:
                        link = match.group(1) if len(match.groups()) > 1 else match.group(0)
                        if self.is_internal_link(link):
                            links.append((link, line_num))
        except Exception as e:
            print(f"Erreur lecture {file_path}: {e}")
            
        return links
    
    def is_internal_link(self, link: str) -> bool:
        """Détermine si un lien est interne au projet"""
        # Exclure les liens externes
        if link.startswith(('http://', 'https://', 'mailto:', 'ftp://')):
            return False
        # Exclure les ancres pures
        if link.startswith('#'):
            return False
        return True
    
    def resolve_link_path(self, link: str, from_file: Path) -> Path:
        """Résout le chemin absolu d'un lien relatif"""
        if link.startswith('/'):
            # Lien absolu depuis la racine du projet
            return self.project_root / link.lstrip('/')
        else:
            # Lien relatif depuis le fichier courant
            return (from_file.parent / link).resolve()
    
    def check_link_validity(self, link: str, from_file: Path) -> Dict:
        """Vérifie la validité d'un lien"""
        try:
            target_path = self.resolve_link_path(link, from_file)
            
            result = {
                'link': link,
                'target_path': str(target_path),
                'exists': target_path.exists(),
                'is_file': target_path.is_file() if target_path.exists() else False,
                'is_dir': target_path.is_dir() if target_path.exists() else False,
                'relative_to_project': str(target_path.relative_to(self.project_root)) if target_path.exists() else None
            }
            
            return result
            
        except Exception as e:
            return {
                'link': link,
                'target_path': 'ERREUR_RESOLUTION',
                'exists': False,
                'error': str(e)
            }
    
    def analyze_project_documentation(self) -> Dict:
        """Analyse complète de la documentation du projet"""
        print("[ANALYSE] Documentation Oracle Enhanced v2.1.0...")
        
        doc_files = self.find_documentation_files()
        print(f"[INFO] {len(doc_files)} fichiers de documentation trouves")
        
        results = {
            'project_root': str(self.project_root),
            'analysis_timestamp': datetime.now().isoformat(),
            'total_doc_files': len(doc_files),
            'files_analyzed': {},
            'broken_links': [],
            'valid_links': [],
            'summary': {}
        }
        
        total_links = 0
        broken_links = 0
        
        for doc_file in doc_files:
            print(f"[FICHIER] Analyse: {doc_file.relative_to(self.project_root)}")
            
            links = self.extract_links_from_file(doc_file)
            file_results = {
                'file_path': str(doc_file.relative_to(self.project_root)),
                'links_found': len(links),
                'links': []
            }
            
            for link, line_num in links:
                total_links += 1
                link_check = self.check_link_validity(link, doc_file)
                link_check['line_number'] = line_num
                link_check['source_file'] = str(doc_file.relative_to(self.project_root))
                
                file_results['links'].append(link_check)
                
                if not link_check['exists']:
                    broken_links += 1
                    results['broken_links'].append(link_check)
                else:
                    results['valid_links'].append(link_check)
            
            results['files_analyzed'][str(doc_file.relative_to(self.project_root))] = file_results
        
        results['summary'] = {
            'total_links': total_links,
            'broken_links': broken_links,
            'valid_links': total_links - broken_links,
            'broken_percentage': (broken_links / total_links * 100) if total_links > 0 else 0
        }
        
        return results
    
    def generate_report(self, results: Dict, output_file: str = None) -> str:
        """Génère un rapport de documentation obsolète"""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"logs/obsolete_documentation_report_{timestamp}.md"
        
        Path(output_file).parent.mkdir(parents=True, exist_ok=True)
        
        report = f"""# Rapport d'Analyse de Documentation Obsolete
## Oracle Enhanced v2.1.0

**Date d'analyse :** {results['analysis_timestamp']}  
**Racine du projet :** `{results['project_root']}`

## Resume Executif

- **Fichiers de documentation analysés :** {results['total_doc_files']}
- **Liens internes totaux :** {results['summary']['total_links']}
- **Liens brisés :** {results['summary']['broken_links']} ({results['summary']['broken_percentage']:.1f}%)
- **Liens valides :** {results['summary']['valid_links']}

## Liens Brises Detectes

"""
        
        if results['broken_links']:
            for broken_link in results['broken_links']:
                report += f"""### [ERREUR] `{broken_link['link']}`
- **Fichier source :** `{broken_link['source_file']}` (ligne {broken_link['line_number']})
- **Chemin cible :** `{broken_link['target_path']}`
- **Probleme :** Fichier/dossier n'existe pas

"""
        else:
            report += "[OK] **Aucun lien brise detecte !** La documentation est a jour.\n\n"
        
        report += f"""## Analyse par Fichier

"""
        
        for file_path, file_data in results['files_analyzed'].items():
            broken_in_file = [l for l in file_data['links'] if not l['exists']]
            status = "[ERREUR]" if broken_in_file else "[OK]"
            
            report += f"""### {status} `{file_path}`
- **Liens trouvés :** {file_data['links_found']}
- **Liens brisés :** {len(broken_in_file)}

"""
            
            if broken_in_file:
                for broken in broken_in_file:
                    report += f"  - [ERREUR] `{broken['link']}` (ligne {broken['line_number']})\n"
                report += "\n"
        
        report += f"""## Recommandations de Correction

### Actions Prioritaires
1. **Corriger les liens brisés** identifiés ci-dessus
2. **Mettre à jour les références** vers les nouveaux emplacements
3. **Supprimer la documentation obsolète** si elle n'est plus pertinente
4. **Exécuter ce script régulièrement** pour maintenir la qualité

### Script de Maintenance
```bash
# Analyse complète
python scripts/maintenance/analyze_obsolete_documentation.py --full-analysis

# Analyse rapide
python scripts/maintenance/analyze_obsolete_documentation.py --quick-scan

# Génération rapport JSON
python scripts/maintenance/analyze_obsolete_documentation.py --output-format json
```

---
*Rapport généré par Oracle Enhanced v2.1.0 Documentation Analyzer*
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"[RAPPORT] Rapport genere: {output_file}")
        return output_file


def main():
    parser = argparse.ArgumentParser(description="Analyse de documentation obsolète Oracle Enhanced v2.1.0")
    parser.add_argument('--project-root', default='.', help='Racine du projet')
    parser.add_argument('--output', help='Fichier de sortie du rapport')
    parser.add_argument('--output-format', choices=['markdown', 'json'], default='markdown')
    parser.add_argument('--quick-scan', action='store_true', help='Analyse rapide (fichiers .md uniquement)')
    parser.add_argument('--full-analysis', action='store_true', help='Analyse complète (tous formats)')
    
    args = parser.parse_args()
    
    analyzer = DocumentationLinkAnalyzer(args.project_root)
    
    if args.quick_scan:
        analyzer.doc_extensions = {'.md'}
        print("[MODE] Analyse rapide (Markdown uniquement)")
    
    results = analyzer.analyze_project_documentation()
    
    if args.output_format == 'json':
        output_file = args.output or f"logs/obsolete_documentation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"[RAPPORT] Rapport JSON genere: {output_file}")
    else:
        output_file = analyzer.generate_report(results, args.output)
    
    # Affichage résumé console
    print(f"\n[RESUME]:")
    print(f"   Fichiers analyses: {results['total_doc_files']}")
    print(f"   Liens totaux: {results['summary']['total_links']}")
    print(f"   Liens brises: {results['summary']['broken_links']}")
    print(f"   Pourcentage de liens valides: {100 - results['summary']['broken_percentage']:.1f}%")
    
    if results['summary']['broken_links'] > 0:
        print(f"\n[ATTENTION] Documentation obsolete detectee!")
        print(f"   Consulter le rapport: {output_file}")
        return 1
    else:
        print(f"\n[OK] Documentation a jour!")
        return 0


if __name__ == "__main__":
    exit(main())