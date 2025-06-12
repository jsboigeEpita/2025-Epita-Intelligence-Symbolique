"""
Script d'intégration pour la maintenance de documentation Oracle Enhanced v2.1.0
Coordonne les différents outils de maintenance documentaire
"""

import project_core.core_from_scripts.auto_env
import os
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime
import json

class DocumentationMaintenanceRunner:
    """Orchestrateur de maintenance de documentation"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.logs_dir = self.project_root / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        
    def run_obsolete_analysis(self, quick_scan: bool = False, output_format: str = 'markdown') -> dict:
        """Exécute l'analyse de documentation obsolète"""
        print("[MAINTENANCE] Lancement analyse documentation obsolete...")
        
        cmd = [
            sys.executable,
            "scripts/maintenance/analyze_obsolete_documentation.py",
            f"--output-format={output_format}"
        ]
        
        if quick_scan:
            cmd.append("--quick-scan")
        else:
            cmd.append("--full-analysis")
            
        try:
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
            
            return {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_maintenance_report(self, results: dict) -> str:
        """Génère un rapport de maintenance global"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.logs_dir / f"documentation_maintenance_report_{timestamp}.md"
        
        report = f"""# Rapport de Maintenance Documentation Oracle Enhanced v2.1.0

**Date :** {datetime.now().isoformat()}
**Racine projet :** `{self.project_root}`

## Résumé des Analyses

### Analyse Documentation Obsolète
"""
        
        if results['obsolete_analysis']['success']:
            report += """
✅ **Analyse complétée avec succès**

Détails dans les logs de sortie ci-dessous.
"""
        else:
            report += """
❌ **Échec de l'analyse**

Erreurs détectées - voir section diagnostic.
"""
        
        report += f"""

## Logs d'Exécution

### Sortie Standard
```
{results['obsolete_analysis'].get('stdout', 'Aucune sortie')}
```

### Erreurs
```
{results['obsolete_analysis'].get('stderr', 'Aucune erreur')}
```

## Recommandations

1. **Corriger les liens brisés prioritaires** identifiés dans l'analyse
2. **Mettre à jour les références** obsolètes
3. **Automatiser cette maintenance** via scheduled tasks
4. **Réviser la structure documentaire** si nécessaire

## Prochaines Actions

- [ ] Corriger les liens brisés critiques
- [ ] Mettre à jour la documentation principale
- [ ] Planifier maintenance régulière
- [ ] Intégrer aux outils CI/CD

---
*Rapport généré par Oracle Enhanced v2.1.0 Documentation Maintenance*
"""
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
            
        return str(report_file)
    
    def run_comprehensive_maintenance(self, quick_scan: bool = False) -> dict:
        """Exécute une maintenance complète de la documentation"""
        print("[MAINTENANCE] Démarrage maintenance complète documentation...")
        
        results = {}
        
        # 1. Analyse documentation obsolète
        print("[STEP 1] Analyse documentation obsolète...")
        results['obsolete_analysis'] = self.run_obsolete_analysis(quick_scan=quick_scan)
        
        # 2. Génération rapport global
        print("[STEP 2] Génération rapport maintenance...")
        report_file = self.generate_maintenance_report(results)
        results['maintenance_report'] = report_file
        
        # 3. Résumé final
        total_success = all(
            r.get('success', False) for r in results.values() 
            if isinstance(r, dict) and 'success' in r
        )
        
        print(f"\n[MAINTENANCE] Maintenance terminée")
        print(f"   Statut global: {'SUCCESS' if total_success else 'ERREURS'}")
        print(f"   Rapport: {report_file}")
        
        return {
            'global_success': total_success,
            'results': results,
            'report_file': report_file
        }


def main():
    parser = argparse.ArgumentParser(description="Maintenance documentation Oracle Enhanced v2.1.0")
    parser.add_argument('--project-root', default='.', help='Racine du projet')
    parser.add_argument('--quick-scan', action='store_true', help='Analyse rapide uniquement')
    parser.add_argument('--obsolete-only', action='store_true', help='Analyse obsolète uniquement')
    parser.add_argument('--output-format', choices=['markdown', 'json'], default='markdown')
    
    args = parser.parse_args()
    
    runner = DocumentationMaintenanceRunner(args.project_root)
    
    if args.obsolete_only:
        print("[MODE] Analyse documentation obsolète uniquement")
        result = runner.run_obsolete_analysis(
            quick_scan=args.quick_scan,
            output_format=args.output_format
        )
        exit_code = 0 if result['success'] else 1
    else:
        print("[MODE] Maintenance complète documentation")
        result = runner.run_comprehensive_maintenance(quick_scan=args.quick_scan)
        exit_code = 0 if result['global_success'] else 1
    
    return exit_code


if __name__ == "__main__":
    exit(main())