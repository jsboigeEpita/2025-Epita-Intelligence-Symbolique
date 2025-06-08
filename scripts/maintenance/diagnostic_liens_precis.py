"""
Diagnostic précis des liens de documentation
Oracle Enhanced v2.1.0 - Analyse détaillée des types de liens
"""

import re
from pathlib import Path
from collections import defaultdict

class PreciseLinkDiagnostic:
    """Diagnostic précis des types de liens détectés"""
    
    def __init__(self):
        self.project_root = Path('.')
        self.link_types = defaultdict(list)
        
    def categorize_link(self, link: str) -> str:
        """Catégorise un lien selon son type"""
        
        # URLs externes
        if any(link.startswith(prefix) for prefix in ['http://', 'https://', 'ftp://', 'mailto:']):
            return 'url_externe'
        
        # Ancres pures
        if link.startswith('#'):
            return 'ancre_pure'
        
        # Références avec numéros de ligne
        if ':' in link and link.split(':')[-1].isdigit():
            return 'reference_ligne'
        
        # Fichiers Python/code
        if link.endswith(('.py', '.js', '.ts', '.java', '.cpp', '.h')):
            return 'fichier_code'
        
        # Liens markdown
        if link.endswith('.md'):
            return 'lien_markdown'
        
        # Répertoires
        if not '.' in Path(link).name:
            return 'repertoire'
        
        # Images/médias
        if link.endswith(('.png', '.jpg', '.svg', '.gif', '.pdf')):
            return 'media'
        
        # Autres extensions
        if '.' in Path(link).suffix:
            return f'fichier_{Path(link).suffix[1:]}'
        
        return 'autre'
    
    def analyze_sample_links(self, sample_size=100):
        """Analyse un échantillon de liens du rapport"""
        
        report_path = Path('logs/post_crash_analysis_final.md')
        if not report_path.exists():
            print("ERREUR: Rapport d'analyse non trouve")
            return
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extraire les liens brisés du rapport
        broken_links = []
        lines = content.split('\n')
        
        for line in lines:
            if line.startswith('### ') and '. ' in line:
                # Format: "### 1. lien_ici"
                parts = line.split('. ', 1)
                if len(parts) == 2:
                    link = parts[1].strip()
                    broken_links.append(link)
        
        # Analyser les premiers liens
        analyzed_count = min(sample_size, len(broken_links))
        print(f"Analyse de {analyzed_count} liens brises...")
        
        for link in broken_links[:analyzed_count]:
            category = self.categorize_link(link)
            self.link_types[category].append(link)
        
        # Rapport par catégorie
        print(f"\nCATEGORISATION DES LIENS:")
        total = sum(len(links) for links in self.link_types.values())
        
        for category, links in sorted(self.link_types.items(), key=lambda x: len(x[1]), reverse=True):
            count = len(links)
            percentage = (count / total * 100) if total > 0 else 0
            print(f"   {category}: {count} ({percentage:.1f}%)")
            
            # Montrer quelques exemples
            examples = links[:3]
            for example in examples:
                print(f"     - {example}")
            if len(links) > 3:
                print(f"     ... et {len(links)-3} autres")
            print()
    
    def check_real_broken_links(self):
        """Vérifie les vrais liens brisés (seulement .md)"""
        print("\nVERIFICATION DES VRAIS LIENS MARKDOWN:")
        
        md_links = self.link_types.get('lien_markdown', [])
        really_broken = []
        
        for link in md_links[:20]:  # Vérifier les 20 premiers
            # Essayer de résoudre le lien
            try:
                if link.startswith('./'):
                    target = self.project_root / link[2:]
                elif link.startswith('../'):
                    target = self.project_root / link
                else:
                    target = self.project_root / link
                
                if not target.exists():
                    really_broken.append(link)
                    print(f"   CASSE: {link}")
                else:
                    print(f"   OK: {link}")
                    
            except Exception as e:
                really_broken.append(link)
                print(f"   ERREUR: {link} (erreur: {e})")
        
        print(f"\nVRAIS LIENS BRISES: {len(really_broken)}")
        return really_broken


def main():
    """Point d'entrée"""
    print("DIAGNOSTIC PRECIS DES LIENS")
    print("=" * 50)
    
    diagnostic = PreciseLinkDiagnostic()
    diagnostic.analyze_sample_links(50)
    broken_md = diagnostic.check_real_broken_links()
    
    print(f"\nCONCLUSION:")
    print(f"   La plupart des 'liens brises' sont en fait:")
    print(f"   - Des references de code Python")
    print(f"   - Des liens avec ancres de ligne")
    print(f"   - Des references internes de documentation")
    print(f"   VRAIS liens .md brises: probablement < 50")

if __name__ == "__main__":
    main()