#!/usr/bin/env python3
"""
Script de récupération massive de documentation Oracle Enhanced v2.1.0
Basé sur l'analyse exhaustive qui a détecté 50,135 liens brisés
"""

import project_core.core_from_scripts.auto_env
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

@dataclass
class DocumentationFix:
    file_path: str
    line_number: int
    original_link: str
    corrected_link: str
    fix_type: str
    confidence: float

class ComprehensiveDocumentationRecovery:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.fixes_applied = []
        self.fixes_failed = []
        self.stats = {
            'files_processed': 0,
            'fixes_applied': 0,
            'fixes_failed': 0,
            'links_analyzed': 0
        }
        
        # Configuration du logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Patterns de correction basés sur l'analyse initiale
        self.correction_patterns = self._build_comprehensive_patterns()
        
    def _build_comprehensive_patterns(self) -> Dict[str, Dict]:
        """Construit les patterns de correction basés sur l'analyse exhaustive"""
        return {
            # 1. Fichiers PowerShell manquants - Redirection vers équivalents Python
            'powershell_to_python': {
                'pattern': r'`([^`]*\.ps1)`',
                'replacements': {
                    'setup_project_env.ps1': 'scripts/setup/setup_environment.py',
                    'activate_project_env.ps1': 'scripts/setup/activate_environment.py',
                    'start_web_application_simple.ps1': 'scripts/startup/start_webapp.py',
                    'backend_failover_non_interactive.ps1': 'scripts/failover/backend_failover.py',
                    'integration_tests_with_failover.ps1': 'scripts/testing/integration_tests.py',
                    'run_integration_tests.ps1': 'scripts/testing/run_tests.py',
                    'clean_project.ps1': 'scripts/maintenance/clean_project.py',
                    'run_backend.cmd': 'scripts/startup/run_backend.py',
                    'run_frontend.cmd': 'scripts/startup/run_frontend.py',
                    'test_backend_fixed.ps1': 'scripts/testing/test_backend.py',
                    'backend_validation_script.ps1': 'scripts/validation/backend_validation.py',
                    'web_application_launcher.ps1': 'scripts/startup/webapp_launcher.py'
                }
            },
            
            # 2. Fichiers de configuration manquants
            'config_files': {
                'pattern': r'`([^`]*\.(yml|yaml|env|ini|toml|json))`',
                'replacements': {
                    'environment.yml': 'config/environment.yml',
                    '.env.template': 'config/.env.template',
                    '.env.example': 'config/.env.example',
                    '.env.test': 'config/.env.test',
                    'pytest.ini': 'config/pytest.ini',
                    'pyproject.toml': 'pyproject.toml',
                    'jpype.config': 'config/jpype.config'
                }
            },
            
            # 3. Scripts Python manquants - Redirection vers modules existants
            'python_scripts': {
                'pattern': r'`([^`]*\.py)`',
                'replacements': {
                    'main_orchestrator.py': 'argumentation_analysis/main_orchestrator.py',
                    'run_analysis.py': 'argumentation_analysis/run_analysis.py',
                    'demonstration_epita.py': 'scripts/demo/demonstration_epita.py',
                    'check_jpype_env.py': 'scripts/setup/check_jpype_env.py',
                    'test_framework_builder.py': 'tests/functional/test_framework_builder.py',
                    'test_integration_workflows.py': 'tests/functional/test_integration_workflows.py',
                    'test_validation_form.py': 'tests/functional/test_validation_form.py',
                    'conftest.py': 'tests/conftest.py',
                    'final_system_validation.py': 'scripts/validation/final_system_validation.py',
                    'test_oracle_enhanced_compatibility.py': 'tests/integration/test_oracle_enhanced_compatibility.py',
                    'refactor_review_files.py': 'scripts/maintenance/refactor_review_files.py',
                    'safe_file_deletion.py': 'scripts/maintenance/safe_file_deletion.py',
                    'integrate_recovered_code.py': 'scripts/integration/integrate_recovered_code.py',
                    'git_files_inventory.py': 'scripts/git/git_files_inventory.py',
                    'orphan_files_processor.py': 'scripts/maintenance/orphan_files_processor.py',
                    'organize_orphan_tests.py': 'scripts/testing/organize_orphan_tests.py'
                }
            },
            
            # 4. Tests manquants - Redirection vers structure de tests
            'test_files': {
                'pattern': r'`(test_[^`]*\.py)`',
                'replacements': {
                    'test_api.py': 'tests/integration/test_api.py',
                    'test_final_validation.py': 'tests/integration/test_final_validation.py',
                    'test_sophismes_detection.py': 'tests/unit/test_sophismes_detection.py',
                    'test_web_api_direct.py': 'tests/integration/test_web_api_direct.py',
                    'test_corrected_patterns.py': 'tests/unit/test_corrected_patterns.py',
                    'test_fallacy_debug.py': 'tests/unit/test_fallacy_debug.py',
                    'test_french_contractions.py': 'tests/unit/test_french_contractions.py',
                    'test_integration_detailed.py': 'tests/integration/test_integration_detailed.py',
                    'test_integration_trace_working.py': 'tests/integration/test_integration_trace_working.py',
                    'test_service_manager_simple.py': 'tests/unit/test_service_manager_simple.py'
                }
            },
            
            # 5. Documentation manquante - Redirection vers docs/
            'documentation': {
                'pattern': r'`([^`]*\.md)`',
                'replacements': {
                    'README.md': 'README.md',
                    'GUIDE_INSTALLATION_ETUDIANTS.md': 'docs/GUIDE_INSTALLATION_ETUDIANTS.md',
                    'cartographie_scripts_fonctionnels.md': 'docs/cartographie_scripts_fonctionnels.md',
                    'MIGRATION_POWERSHELL_TO_PYTHON.md': 'docs/MIGRATION_POWERSHELL_TO_PYTHON.md',
                    'RAPPORT_ANALYSE_77_FICHIERS.md': 'docs/reports/RAPPORT_ANALYSE_77_FICHIERS.md',
                    'TEST_MAPPING.md': 'docs/testing/TEST_MAPPING.md',
                    'test_execution_trace.md': 'docs/testing/test_execution_trace.md',
                    'test_execution_trace_complete_working.md': 'docs/testing/test_execution_trace_complete_working.md'
                }
            },
            
            # 6. Liens vers sections (ancres) - Nettoyage des caractères invalides
            'section_links': {
                'pattern': r'`([^`#]*#[^`]*)`',
                'cleanup': True
            },
            
            # 7. Liens malformés avec guillemets doubles
            'malformed_quotes': {
                'pattern': r'``([^`]*)``',
                'cleanup': True
            },
            
            # 8. Répertoires vers structure actuelle
            'directories': {
                'pattern': r'`([^`]*/)(?!.*\.)',
                'replacements': {
                    'docs/': 'docs/',
                    'scripts/': 'scripts/',
                    'tests/': 'tests/',
                    'argumentation_analysis/': 'argumentation_analysis/',
                    'project_core/': 'project_core/',
                    'migration_output/': 'migration_output/',
                    'logs/': 'logs/'
                }
            }
        }
    
    def analyze_file(self, file_path: Path) -> List[DocumentationFix]:
        """Analyse un fichier et génère les corrections nécessaires"""
        fixes = []
        
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.splitlines()
            
            for line_num, line in enumerate(lines, 1):
                self.stats['links_analyzed'] += len(re.findall(r'`[^`]*`', line))
                
                # Appliquer tous les patterns de correction
                for category, pattern_data in self.correction_patterns.items():
                    pattern = pattern_data['pattern']
                    matches = re.finditer(pattern, line)
                    
                    for match in matches:
                        original_link = match.group(1) if match.groups() else match.group(0)
                        corrected_link = self._get_correction(original_link, pattern_data)
                        
                        if corrected_link and corrected_link != original_link:
                            fix = DocumentationFix(
                                file_path=str(file_path.relative_to(self.project_root)),
                                line_number=line_num,
                                original_link=original_link,
                                corrected_link=corrected_link,
                                fix_type=category,
                                confidence=self._calculate_confidence(original_link, corrected_link)
                            )
                            fixes.append(fix)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse de {file_path}: {e}")
        
        return fixes
    
    def _get_correction(self, original_link: str, pattern_data: Dict) -> str:
        """Détermine la correction appropriée pour un lien"""
        if 'replacements' in pattern_data:
            # Recherche exacte d'abord
            if original_link in pattern_data['replacements']:
                return pattern_data['replacements'][original_link]
            
            # Recherche par correspondance partielle
            for key, value in pattern_data['replacements'].items():
                if original_link.endswith(key) or key in original_link:
                    return value
        
        if pattern_data.get('cleanup'):
            # Nettoyage des liens malformés
            cleaned = original_link.strip('`').strip('"').strip("'")
            cleaned = re.sub(r'[^\w\-./]', '_', cleaned)
            return cleaned
        
        return original_link
    
    def _calculate_confidence(self, original: str, corrected: str) -> float:
        """Calcule le niveau de confiance pour une correction"""
        if original == corrected:
            return 0.0
        
        # Confidence élevée pour les correspondances exactes
        if any(original in replacements for replacements in 
               [p.get('replacements', {}) for p in self.correction_patterns.values()]):
            return 0.95
        
        # Confidence moyenne pour les nettoyages
        if len(corrected) > len(original) * 0.8:
            return 0.7
        
        return 0.5
    
    def apply_fixes(self, fixes: List[DocumentationFix]) -> None:
        """Applique les corrections aux fichiers"""
        files_to_fix = {}
        
        # Grouper les corrections par fichier
        for fix in fixes:
            if fix.file_path not in files_to_fix:
                files_to_fix[fix.file_path] = []
            files_to_fix[fix.file_path].append(fix)
        
        # Appliquer les corrections fichier par fichier
        for file_path, file_fixes in files_to_fix.items():
            try:
                self._apply_file_fixes(Path(self.project_root / file_path), file_fixes)
                self.stats['fixes_applied'] += len(file_fixes)
                self.fixes_applied.extend(file_fixes)
            except Exception as e:
                self.logger.error(f"Erreur lors de l'application des corrections dans {file_path}: {e}")
                self.fixes_failed.extend(file_fixes)
                self.stats['fixes_failed'] += len(file_fixes)
    
    def _apply_file_fixes(self, file_path: Path, fixes: List[DocumentationFix]) -> None:
        """Applique les corrections dans un fichier spécifique"""
        content = file_path.read_text(encoding='utf-8')
        lines = content.splitlines()
        
        # Trier les corrections par numéro de ligne (décroissant pour éviter les décalages)
        fixes.sort(key=lambda f: f.line_number, reverse=True)
        
        for fix in fixes:
            if fix.line_number <= len(lines):
                line_index = fix.line_number - 1
                old_line = lines[line_index]
                
                # Remplacer le lien dans la ligne
                new_line = old_line.replace(f'`{fix.original_link}`', f'`{fix.corrected_link}`')
                lines[line_index] = new_line
                
                self.logger.info(f"Correction appliquée dans {file_path}:{fix.line_number}")
                self.logger.info(f"  {fix.original_link} -> {fix.corrected_link}")
        
        # Sauvegarder le fichier modifié
        file_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    
    def process_documentation(self) -> None:
        """Traite toute la documentation du projet"""
        self.logger.info("Début du traitement de récupération massive de documentation")
        
        # Patterns de fichiers à traiter (basés sur l'analyse initiale)
        file_patterns = [
            '*.md',
            '*.rst', 
            '*.txt',
            'argumentation_analysis/**/*.md',
            'docs/**/*.md',
            'tests/**/*.md'
        ]
        
        all_fixes = []
        
        for pattern in file_patterns:
            files = list(self.project_root.glob(pattern))
            for file_path in files:
                if file_path.is_file() and not any(exclude in str(file_path) for exclude in 
                    ['node_modules', '.git', '__pycache__', 'venv']):
                    
                    self.stats['files_processed'] += 1
                    fixes = self.analyze_file(file_path)
                    all_fixes.extend(fixes)
                    
                    if len(fixes) > 0:
                        self.logger.info(f"Trouvé {len(fixes)} corrections dans {file_path}")
        
        self.logger.info(f"Total de {len(all_fixes)} corrections identifiées")
        
        # Filtrer les corrections par niveau de confiance
        high_confidence_fixes = [f for f in all_fixes if f.confidence >= 0.7]
        medium_confidence_fixes = [f for f in all_fixes if 0.4 <= f.confidence < 0.7]
        
        self.logger.info(f"Corrections haute confiance: {len(high_confidence_fixes)}")
        self.logger.info(f"Corrections confiance moyenne: {len(medium_confidence_fixes)}")
        
        # Appliquer les corrections haute confiance
        self.apply_fixes(high_confidence_fixes)
        
        # Générer un rapport pour les corrections moyennes
        self._generate_report(all_fixes)
    
    def _generate_report(self, all_fixes: List[DocumentationFix]) -> None:
        """Génère un rapport complet des corrections"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.project_root / f"logs/comprehensive_recovery_report_{timestamp}.md"
        json_path = self.project_root / f"logs/comprehensive_recovery_report_{timestamp}.json"
        
        # Rapport Markdown
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("# Rapport de Récupération Massive de Documentation\n\n")
            f.write(f"**Date de génération:** {datetime.now().isoformat()}\n\n")
            
            f.write("## Statistiques\n\n")
            f.write(f"- Fichiers traités: {self.stats['files_processed']}\n")
            f.write(f"- Liens analysés: {self.stats['links_analyzed']}\n")
            f.write(f"- Corrections appliquées: {self.stats['fixes_applied']}\n")
            f.write(f"- Corrections échouées: {self.stats['fixes_failed']}\n")
            f.write(f"- Total corrections identifiées: {len(all_fixes)}\n\n")
            
            f.write("## Corrections Appliquées\n\n")
            for fix in self.fixes_applied:
                f.write(f"### {fix.file_path}:{fix.line_number}\n")
                f.write(f"- **Type:** {fix.fix_type}\n")
                f.write(f"- **Confiance:** {fix.confidence:.2f}\n")
                f.write(f"- **Original:** `{fix.original_link}`\n")
                f.write(f"- **Corrigé:** `{fix.corrected_link}`\n\n")
            
            f.write("## Corrections Nécessitant Validation Manuelle\n\n")
            manual_fixes = [f for f in all_fixes if f.confidence < 0.7 and f not in self.fixes_applied]
            for fix in manual_fixes:
                f.write(f"### {fix.file_path}:{fix.line_number}\n")
                f.write(f"- **Type:** {fix.fix_type}\n")
                f.write(f"- **Confiance:** {fix.confidence:.2f}\n")
                f.write(f"- **Original:** `{fix.original_link}`\n")
                f.write(f"- **Suggestion:** `{fix.corrected_link}`\n\n")
        
        # Rapport JSON
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'statistics': self.stats,
            'fixes_applied': [asdict(fix) for fix in self.fixes_applied],
            'fixes_failed': [asdict(fix) for fix in self.fixes_failed],
            'all_fixes': [asdict(fix) for fix in all_fixes]
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Rapport généré: {report_path}")
        self.logger.info(f"Données JSON: {json_path}")

def main():
    """Point d'entrée principal"""
    project_root = Path(__file__).parent.parent.parent
    
    recovery = ComprehensiveDocumentationRecovery(project_root)
    recovery.process_documentation()
    
    print(f"\n🎯 RÉCUPÉRATION MASSIVE TERMINÉE")
    print(f"✅ Corrections appliquées: {recovery.stats['fixes_applied']}")
    print(f"❌ Corrections échouées: {recovery.stats['fixes_failed']}")
    print(f"📁 Fichiers traités: {recovery.stats['files_processed']}")
    print(f"🔗 Liens analysés: {recovery.stats['links_analyzed']}")

if __name__ == "__main__":
    main()