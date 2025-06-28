#!/usr/bin/env python3
"""
Script de migration vers ServiceManager
Identifie tous les usages des anciens patterns PowerShell/CMD
Génère un rapport de migration et propose le remplacement des scripts

Patterns détectés basés sur la cartographie :
- start_web_application_simple.ps1
- backend_failover_non_interactive.ps1  
- integration_tests_with_failover.ps1
- run_integration_tests.ps1
- run_backend.cmd
- run_frontend.cmd

Auteur: Projet Intelligence Symbolique EPITA
Date: 07/06/2025
"""

import os
import re
import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime

# Import du ServiceManager pour les exemples
try:
    from project_core.service_manager import ServiceManager, ServiceConfig
    from project_core.test_runner import TestRunner
except ImportError:
    print("Modules ServiceManager non trouvés. Assurez-vous d'être dans le bon répertoire.")
    sys.exit(1)


@dataclass
class PatternMatch:
    """Représente une correspondance de pattern trouvée"""
    file_path: str
    pattern_type: str
    line_number: int
    matched_content: str
    confidence: float
    replacement_suggestion: str


@dataclass
class MigrationReport:
    """Rapport complet de migration"""
    scan_date: str
    total_files_scanned: int
    obsolete_scripts_found: List[str]
    pattern_matches: List[PatternMatch]
    migration_priority: Dict[str, int]
    estimated_effort_hours: Dict[str, int]
    replacement_commands: Dict[str, str]


class PatternDetector:
    """Détecteur de patterns PowerShell/CMD obsolètes"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        
        # Patterns PowerShell critiques identifiés dans la cartographie
        self.powershell_patterns = {
            'start_process_pattern': {
                'regex': r'Start-Process.*python.*app\.py',
                'description': 'Démarrage backend via Start-Process',
                'confidence': 0.9,
                'replacement': 'service_manager.start_service_with_failover("backend-flask")'
            },
            'start_job_pattern': {
                'regex': r'Start-Job.*python.*app\.py',
                'description': 'Démarrage backend via Start-Job',
                'confidence': 0.9,
                'replacement': 'service_manager.start_service_with_failover("backend-flask")'
            },
            'npm_start_pattern': {
                'regex': r'Start-Process.*npm.*start',
                'description': 'Démarrage frontend via npm start',
                'confidence': 0.9,
                'replacement': 'service_manager.start_service_with_failover("frontend-react")'
            },
            'cleanup_services_pattern': {
                'regex': r'function\s+Cleanup-Services',
                'description': 'Pattern Cleanup-Services détecté',
                'confidence': 1.0,
                'replacement': 'service_manager.stop_all_services()'
            },
            'free_port_pattern': {
                'regex': r'function\s+Free-Port',
                'description': 'Pattern Free-Port détecté',
                'confidence': 1.0,
                'replacement': 'port_manager.free_port(port, force=True)'
            },
            'stop_process_pattern': {
                'regex': r'Get-Process.*Stop-Process.*Force',
                'description': 'Arrêt processus PowerShell générique',
                'confidence': 0.8,
                'replacement': 'process_cleanup.stop_backend_processes() ou stop_frontend_processes()'
            },
            'test_netconnection_pattern': {
                'regex': r'Test-NetConnection.*-Port',
                'description': 'Test de port PowerShell',
                'confidence': 0.8,
                'replacement': 'port_manager.is_port_free(port)'
            },
            'invoke_webrequest_pattern': {
                'regex': r'Invoke-WebRequest.*localhost',
                'description': 'Health check PowerShell',
                'confidence': 0.7,
                'replacement': 'service_manager.test_service_health(url)'
            }
        }
        
        # Patterns CMD simples
        self.cmd_patterns = {
            'python_direct_pattern': {
                'regex': r'python.*app\.py',
                'description': 'Démarrage Python direct',
                'confidence': 0.8,
                'replacement': 'service_manager.start_service_with_failover("backend-flask")'
            },
            'npm_direct_pattern': {
                'regex': r'npm\s+start',
                'description': 'Démarrage npm direct',
                'confidence': 0.8,
                'replacement': 'service_manager.start_service_with_failover("frontend-react")'
            }
        }
        
        # Scripts cibles identifiés dans la cartographie
        self.target_scripts = {
            'start_web_application_simple.ps1': {
                'priority': 1,
                'effort_hours': 6,
                'replacement': 'python -m project_core.test_runner start-app --wait'
            },
            'backend_failover_non_interactive.ps1': {
                'priority': 1,
                'effort_hours': 8,
                'replacement': 'python -c "from project_core.service_manager import *; sm = ServiceManager(); sm.start_service_with_failover(\'backend-flask\')"'
            },
            'integration_tests_with_failover.ps1': {
                'priority': 2,
                'effort_hours': 12,
                'replacement': 'python -m project_core.test_runner integration'
            },
            'run_integration_tests.ps1': {
                'priority': 2,
                'effort_hours': 4,
                'replacement': 'python -m project_core.test_runner integration'
            },
            'run_backend.cmd': {
                'priority': 1,
                'effort_hours': 2,
                'replacement': 'python -m project_core.test_runner start-app'
            },
            'run_frontend.cmd': {
                'priority': 1,
                'effort_hours': 2,
                'replacement': 'python -m project_core.test_runner start-app'
            }
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Configuration du logging"""
        logger = logging.getLogger('MigrationDetector')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def scan_directory(self, base_path: Path) -> List[PatternMatch]:
        """Scanne un répertoire pour détecter les patterns obsolètes"""
        matches = []
        
        # Fichiers PowerShell
        for ps_file in base_path.rglob("*.ps1"):
            matches.extend(self._scan_powershell_file(ps_file))
        
        # Fichiers CMD
        for cmd_file in base_path.rglob("*.cmd"):
            matches.extend(self._scan_cmd_file(cmd_file))
        
        # Fichiers BAT
        for bat_file in base_path.rglob("*.bat"):
            matches.extend(self._scan_cmd_file(bat_file))
        
        return matches
    
    def _scan_powershell_file(self, file_path: Path) -> List[PatternMatch]:
        """Scanne un fichier PowerShell pour détecter les patterns"""
        matches = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                for pattern_name, pattern_info in self.powershell_patterns.items():
                    if re.search(pattern_info['regex'], line, re.IGNORECASE):
                        match = PatternMatch(
                            file_path=str(file_path),
                            pattern_type=pattern_name,
                            line_number=line_num,
                            matched_content=line.strip(),
                            confidence=pattern_info['confidence'],
                            replacement_suggestion=pattern_info['replacement']
                        )
                        matches.append(match)
        
        except Exception as e:
            self.logger.warning(f"Erreur lecture {file_path}: {e}")
        
        return matches
    
    def _scan_cmd_file(self, file_path: Path) -> List[PatternMatch]:
        """Scanne un fichier CMD/BAT pour détecter les patterns"""
        matches = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                for pattern_name, pattern_info in self.cmd_patterns.items():
                    if re.search(pattern_info['regex'], line, re.IGNORECASE):
                        match = PatternMatch(
                            file_path=str(file_path),
                            pattern_type=pattern_name,
                            line_number=line_num,
                            matched_content=line.strip(),
                            confidence=pattern_info['confidence'],
                            replacement_suggestion=pattern_info['replacement']
                        )
                        matches.append(match)
        
        except Exception as e:
            self.logger.warning(f"Erreur lecture {file_path}: {e}")
        
        return matches
    
    def identify_obsolete_scripts(self, base_path: Path) -> List[str]:
        """Identifie les scripts obsolètes basés sur la cartographie"""
        obsolete_scripts = []
        
        for script_name in self.target_scripts.keys():
            script_path = base_path / script_name
            if script_path.exists():
                obsolete_scripts.append(str(script_path))
            
            # Recherche dans sous-répertoires
            found_scripts = list(base_path.rglob(script_name))
            for found_script in found_scripts:
                if str(found_script) not in obsolete_scripts:
                    obsolete_scripts.append(str(found_script))
        
        return obsolete_scripts


class MigrationPlanner:
    """Planificateur de migration"""
    
    def __init__(self):
        self.detector = PatternDetector()
        self.logger = self.detector.logger
    
    def generate_migration_report(self, base_path: Path) -> MigrationReport:
        """Génère un rapport complet de migration"""
        self.logger.info(f"Analyse du répertoire: {base_path}")
        
        # Scan des patterns
        pattern_matches = self.detector.scan_directory(base_path)
        
        # Identification des scripts obsolètes
        obsolete_scripts = self.detector.identify_obsolete_scripts(base_path)
        
        # Calcul des priorités et efforts
        migration_priority = {}
        estimated_effort = {}
        replacement_commands = {}
        
        for script_path in obsolete_scripts:
            script_name = Path(script_path).name
            if script_name in self.detector.target_scripts:
                info = self.detector.target_scripts[script_name]
                migration_priority[script_path] = info['priority']
                estimated_effort[script_path] = info['effort_hours']
                replacement_commands[script_path] = info['replacement']
        
        # Création du rapport
        report = MigrationReport(
            scan_date=datetime.now().isoformat(),
            total_files_scanned=self._count_script_files(base_path),
            obsolete_scripts_found=obsolete_scripts,
            pattern_matches=pattern_matches,
            migration_priority=migration_priority,
            estimated_effort_hours=estimated_effort,
            replacement_commands=replacement_commands
        )
        
        return report
    
    def _count_script_files(self, base_path: Path) -> int:
        """Compte le nombre total de fichiers de script"""
        count = 0
        for pattern in ["*.ps1", "*.cmd", "*.bat"]:
            count += len(list(base_path.rglob(pattern)))
        return count
    
    def save_report(self, report: MigrationReport, output_path: Path):
        """Sauvegarde le rapport au format JSON"""
        # Conversion en dictionnaire sérialisable
        report_dict = asdict(report)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Rapport sauvegardé: {output_path}")
    
    def generate_replacement_scripts(self, report: MigrationReport, output_dir: Path):
        """Génère les scripts de remplacement Python"""
        output_dir.mkdir(exist_ok=True)
        
        # Script principal de démarrage unifié
        self._create_unified_startup_script(output_dir)
        
        # Scripts de remplacement individuels
        for script_path, replacement_cmd in report.replacement_commands.items():
            script_name = Path(script_path).stem
            self._create_individual_replacement_script(
                output_dir, script_name, replacement_cmd
            )
    
    def _create_unified_startup_script(self, output_dir: Path):
        """Crée un script de démarrage unifié"""
        script_content = '''#!/usr/bin/env python3
"""
Script de démarrage unifié - remplace tous les scripts PowerShell/CMD
Généré automatiquement par migrate_to_service_manager.py
"""

import sys
import argparse
from pathlib import Path

# Ajout du chemin du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

from project_core.service_manager import ServiceManager, create_default_configs
from project_core.test_runner import TestRunner


def main():
    parser = argparse.ArgumentParser(description="Script de démarrage unifié")
    parser.add_argument("action", choices=[
        "start-backend", "start-frontend", "start-app", 
        "test-integration", "test-unit", "stop-all"
    ])
    parser.add_argument("--wait", action="store_true", help="Attendre après démarrage")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")
    
    args = parser.parse_args()
    
    if args.action == "start-backend":
        sm = ServiceManager()
        for config in create_default_configs():
            if config.name == "backend-flask":
                sm.register_service(config)
                success, port = sm.start_service_with_failover("backend-flask")
                if success:
                    print(f"Backend démarré sur port {port}")
                    if args.wait:
                        input("Appuyez sur Entrée pour arrêter...")
                        sm.stop_all_services()
                return 0 if success else 1
    
    elif args.action == "start-frontend":
        sm = ServiceManager()
        for config in create_default_configs():
            if config.name == "frontend-react":
                sm.register_service(config)
                success, port = sm.start_service_with_failover("frontend-react")
                if success:
                    print(f"Frontend démarré sur port {port}")
                    if args.wait:
                        input("Appuyez sur Entrée pour arrêter...")
                        sm.stop_all_services()
                return 0 if success else 1
    
    elif args.action == "start-app":
        runner = TestRunner()
        results = runner.start_web_application(wait=args.wait)
        return 0 if all(success for success, _ in results.values()) else 1
    
    elif args.action == "test-integration":
        runner = TestRunner()
        return runner.run_tests("integration")
    
    elif args.action == "test-unit":
        runner = TestRunner()
        return runner.run_tests("unit")
    
    elif args.action == "stop-all":
        sm = ServiceManager()
        sm.stop_all_services()
        print("Tous les services arrêtés")
        return 0


if __name__ == "__main__":
    sys.exit(main())
'''
        
        script_path = output_dir / "unified_startup.py"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # Rendre exécutable sur Unix
        if hasattr(os, 'chmod'):
            os.chmod(script_path, 0o755)
        
        self.logger.info(f"Script unifié créé: {script_path}")
    
    def _create_individual_replacement_script(self, output_dir: Path, script_name: str, replacement_cmd: str):
        """Crée un script de remplacement individuel"""
        script_content = f'''#!/usr/bin/env python3
"""
Remplacement pour {script_name}
Généré automatiquement par migrate_to_service_manager.py
"""

import sys
import subprocess
from pathlib import Path

# Ajout du chemin du projet
sys.path.insert(0, str(Path(__file__).parent.parent))

def main():
    """Exécute le remplacement pour {script_name}"""
    print(f"Exécution du remplacement pour {script_name}")
    print(f"Commande: {replacement_cmd}")
    
    try:
        if replacement_cmd.startswith("python -m"):
            # Commande module Python
            parts = replacement_cmd.split()
            result = subprocess.run(parts, check=True)
            return result.returncode
        elif replacement_cmd.startswith("python -c"):
            # Code Python direct
            code = replacement_cmd[11:-1]  # Enlever 'python -c "' et '"'
            exec(code)
            return 0
        else:
            # Commande shell générique
            result = subprocess.run(replacement_cmd, shell=True, check=True)
            return result.returncode
    
    except subprocess.CalledProcessError as e:
        print(f"Erreur exécution: {{e}}")
        return e.returncode
    except Exception as e:
        print(f"Erreur: {{e}}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
'''
        
        script_path = output_dir / f"{script_name}_replacement.py"
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        self.logger.info(f"Script de remplacement créé: {script_path}")


def print_migration_summary(report: MigrationReport):
    """Affiche un résumé de migration lisible - Compatible encodage Windows"""
    print("\n" + "="*80)
    print("RAPPORT DE MIGRATION VERS SERVICEMANAGER")
    print("="*80)
    
    print(f"\nDate d'analyse: {report.scan_date}")
    print(f"Fichiers scannes: {report.total_files_scanned}")
    print(f"Scripts obsoletes trouves: {len(report.obsolete_scripts_found)}")
    print(f"Patterns detectes: {len(report.pattern_matches)}")
    
    if report.obsolete_scripts_found:
        print("\nSCRIPTS OBSOLETES A MIGRER:")
        for i, script in enumerate(report.obsolete_scripts_found, 1):
            script_name = Path(script).name
            priority = report.migration_priority.get(script, 0)
            effort = report.estimated_effort_hours.get(script, 0)
            
            priority_marker = "[URGENT]" if priority == 1 else "[MOYEN]" if priority == 2 else "[FAIBLE]"
            print(f"  {i}. {priority_marker} {script_name}")
            print(f"     Chemin: {script}")
            print(f"     Priorite: {priority} | Effort: {effort}h")
            
            if script in report.replacement_commands:
                print(f"     Remplacement: {report.replacement_commands[script]}")
            print()
    
    if report.pattern_matches:
        print("\nPATTERNS DETECTES PAR TYPE:")
        pattern_counts = {}
        for match in report.pattern_matches:
            pattern_counts[match.pattern_type] = pattern_counts.get(match.pattern_type, 0) + 1
        
        for pattern_type, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {pattern_type}: {count} occurrences")
    
    # Calcul effort total
    total_effort = sum(report.estimated_effort_hours.values())
    print(f"\nEFFORT TOTAL ESTIME: {total_effort} heures")
    
    # Recommandations prioritaires
    print("\nRECOMMANDATIONS PRIORITAIRES:")
    priority_1_scripts = [s for s, p in report.migration_priority.items() if p == 1]
    if priority_1_scripts:
        print("  1. Migrer immediatement (Priorite 1):")
        for script in priority_1_scripts:
            print(f"     - {Path(script).name}")
    
    print("\n  2. Utiliser les scripts de remplacement generes dans 'migration_output/'")
    print("  3. Tester chaque remplacement avant suppression des anciens scripts")
    print("  4. Documenter les changements pour l'equipe")
    
    print("\n" + "="*80)


def main():
    """Point d'entrée principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration vers ServiceManager")
    parser.add_argument("--scan-dir", default=".", help="Répertoire à scanner")
    parser.add_argument("--output-dir", default="migration_output", help="Répertoire de sortie")
    parser.add_argument("--report-only", action="store_true", help="Génère seulement le rapport")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux")
    
    args = parser.parse_args()
    
    # Configuration logging
    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    
    base_path = Path(args.scan_dir).resolve()
    output_dir = Path(args.output_dir)
    
    if not base_path.exists():
        print(f"Erreur: Répertoire '{base_path}' non trouvé")
        return 1
    
    # Génération du rapport
    planner = MigrationPlanner()
    report = planner.generate_migration_report(base_path)
    
    # Sauvegarde du rapport
    output_dir.mkdir(exist_ok=True)
    report_path = output_dir / "migration_report.json"
    planner.save_report(report, report_path)
    
    # Affichage du résumé
    print_migration_summary(report)
    
    # Génération des scripts de remplacement
    if not args.report_only:
        planner.generate_replacement_scripts(report, output_dir)
        print(f"\nScripts de remplacement generes dans: {output_dir}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())