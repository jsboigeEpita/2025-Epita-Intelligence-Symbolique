#!/usr/bin/env python3
"""
Script d'intégration du code récupéré - Oracle Enhanced v2.1.0
Traite l'intégration du code récupéré identifié dans les phases précédentes
"""

import project_core.core_from_scripts.auto_env
import os
import sys
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import subprocess

class RecoveredCodeIntegrator:
    """Gestionnaire d'intégration du code récupéré"""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.recovered_files = {}
        self.integration_log = []
        self.test_results = {}
        
    def scan_recovered_directories(self) -> Dict[str, List[str]]:
        """Scanner tous les répertoires */recovered/ pour inventaire"""
        recovered_dirs = [
            "docs/recovered",
            "tests/comparison/recovered", 
            "tests/integration/recovered",
            "tests/unit/recovered",
            "scripts/maintenance/recovered"
        ]
        
        inventory = {}
        for dir_path in recovered_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                files = []
                for file_path in full_path.rglob("*"):
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        relative_path = file_path.relative_to(self.project_root)
                        files.append(str(relative_path))
                inventory[dir_path] = files
                
        # Ajouter le fichier de validation
        validation_file = "tests/validation/test_recovered_code_validation.py"
        if (self.project_root / validation_file).exists():
            inventory["tests/validation"] = [validation_file]
            
        return inventory
    
    def analyze_file_content(self, file_path: str) -> Dict[str, Any]:
        """Analyser le contenu d'un fichier récupéré"""
        full_path = self.project_root / file_path
        
        analysis = {
            "path": file_path,
            "exists": full_path.exists(),
            "size": 0,
            "type": "unknown",
            "priority": "medium",
            "oracle_related": False,
            "imports": [],
            "functions": [],
            "classes": [],
            "dependencies": []
        }
        
        if not full_path.exists():
            return analysis
            
        analysis["size"] = full_path.stat().st_size
        
        # Déterminer le type de fichier
        if file_path.endswith('.py'):
            analysis["type"] = "python_test" if "test_" in file_path else "python_script"
        elif file_path.endswith('.md'):
            analysis["type"] = "documentation"
        else:
            analysis["type"] = "other"
            
        # Analyser contenu Python
        if analysis["type"].startswith("python"):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # Détecter Oracle/Sherlock
                oracle_keywords = ["oracle", "sherlock", "watson", "moriarty", "cluedo"]
                analysis["oracle_related"] = any(keyword.lower() in content.lower() 
                                                for keyword in oracle_keywords)
                
                # Priorité selon Oracle/Sherlock
                if analysis["oracle_related"]:
                    analysis["priority"] = "high"
                    
                # Extraire imports basiques
                import_lines = [line.strip() for line in content.split('\n') 
                              if line.strip().startswith('import ') or line.strip().startswith('from ')]
                analysis["imports"] = import_lines[:10]  # Limite pour éviter trop de données
                
            except Exception as e:
                analysis["error"] = str(e)
                
        return analysis
    
    def test_file_functionality(self, file_path: str) -> Dict[str, Any]:
        """Tester la fonctionnalité d'un fichier Python"""
        full_path = self.project_root / file_path
        
        test_result = {
            "file": file_path,
            "syntax_check": False,
            "import_check": False,
            "pytest_collect": False,
            "errors": []
        }
        
        if not file_path.endswith('.py'):
            test_result["errors"].append("Not a Python file")
            return test_result
            
        # Test syntaxe Python
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            compile(content, file_path, 'exec')
            test_result["syntax_check"] = True
        except SyntaxError as e:
            test_result["errors"].append(f"Syntax error: {e}")
        except Exception as e:
            test_result["errors"].append(f"Compile error: {e}")
            
        # Test imports (basique)
        if test_result["syntax_check"]:
            try:
                # Utiliser subprocess pour éviter les effets de bord
                cmd = [sys.executable, "-c", f"import sys; sys.path.insert(0, '.'); exec(open('{full_path}').read())"]
                result = subprocess.run(cmd, cwd=self.project_root, 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    test_result["import_check"] = True
                else:
                    test_result["errors"].append(f"Import error: {result.stderr}")
            except subprocess.TimeoutExpired:
                test_result["errors"].append("Import test timeout")
            except Exception as e:
                test_result["errors"].append(f"Import test error: {e}")
                
        # Test pytest collect si c'est un test
        if "test_" in file_path and test_result["syntax_check"]:
            try:
                cmd = [sys.executable, "-m", "pytest", "--collect-only", file_path]
                result = subprocess.run(cmd, cwd=self.project_root,
                                      capture_output=True, text=True, timeout=15)
                test_result["pytest_collect"] = result.returncode == 0
                if result.returncode != 0:
                    test_result["errors"].append(f"Pytest collect error: {result.stderr}")
            except Exception as e:
                test_result["errors"].append(f"Pytest collect test error: {e}")
                
        return test_result
    
    def determine_integration_target(self, file_path: str, analysis: Dict[str, Any]) -> str:
        """Déterminer la destination d'intégration"""
        
        # Tests d'intégration Oracle/Cluedo
        if "test_cluedo" in file_path or "test_oracle_integration" in file_path:
            return "tests/integration/"
            
        # Tests unitaires agents
        if "test_oracle_base_agent" in file_path or "test_oracle_behavior" in file_path:
            return "tests/unit/argumentation_analysis/agents/core/oracle/"
            
        # Tests de validation
        if "test_recovered_code_validation" in file_path or "validation" in file_path:
            return "tests/validation_sherlock_watson/"
            
        # Scripts de maintenance
        if file_path.startswith("scripts/maintenance/recovered/"):
            return "scripts/maintenance/"
            
        # Tests de comparaison
        if "test_mock_vs_real_behavior" in file_path:
            return "tests/unit/mocks/"
            
        # Configuration enhanced
        if "conftest_gpt_enhanced" in file_path:
            return "tests/integration/"
            
        # Documentation
        if file_path.endswith('.md'):
            return "docs/sherlock_watson/"
            
        # Par défaut selon le type
        if analysis["type"] == "python_test":
            if analysis["oracle_related"]:
                return "tests/unit/argumentation_analysis/agents/core/oracle/"
            else:
                return "tests/unit/"
        elif analysis["type"] == "python_script":
            return "scripts/maintenance/"
        else:
            return "docs/recovered_integration/"
    
    def integrate_file(self, source_path: str, target_dir: str, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Intégrer un fichier dans sa destination"""
        source_full = self.project_root / source_path
        target_full = self.project_root / target_dir
        
        # Créer le répertoire de destination
        target_full.mkdir(parents=True, exist_ok=True)
        
        # Déterminer le nom de fichier
        source_name = Path(source_path).name
        target_path = target_full / source_name
        
        # Éviter les conflits de noms
        counter = 1
        while target_path.exists():
            name_parts = source_name.rsplit('.', 1)
            if len(name_parts) == 2:
                new_name = f"{name_parts[0]}_recovered{counter}.{name_parts[1]}"
            else:
                new_name = f"{source_name}_recovered{counter}"
            target_path = target_full / new_name
            counter += 1
            
        integration_result = {
            "source": source_path,
            "target": str(target_path.relative_to(self.project_root)),
            "status": "pending",
            "backup_created": False,
            "modernized": False
        }
        
        try:
            # Copier le fichier
            shutil.copy2(source_full, target_path)
            integration_result["status"] = "copied"
            
            # Moderniser si nécessaire (ajouter headers v2.1.0)
            if source_path.endswith('.py'):
                self._modernize_python_file(target_path)
                integration_result["modernized"] = True
                
            integration_result["status"] = "integrated"
            
        except Exception as e:
            integration_result["status"] = "failed"
            integration_result["error"] = str(e)
            
        return integration_result
    
    def _modernize_python_file(self, file_path: Path):
        """Moderniser un fichier Python avec headers v2.1.0"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Ajouter header Oracle Enhanced v2.1.0 si absent
            oracle_header = '''"""
Oracle Enhanced v2.1.0 - Fichier intégré depuis recovered/
Compatible avec la structure Oracle Enhanced v2.1.0
"""

'''
            
            if "Oracle Enhanced v2.1.0" not in content:
                # Chercher le premier import ou class/def
                lines = content.split('\n')
                insert_line = 0
                
                # Chercher après les commentaires de début
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('"""'):
                        insert_line = i
                        break
                        
                lines.insert(insert_line, oracle_header)
                content = '\n'.join(lines)
                
            # Mettre à jour les imports pour Oracle Enhanced v2.1.0
            content = self._update_imports_for_v2_1_0(content)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            print(f"Erreur lors de la modernisation de {file_path}: {e}")
    
    def _update_imports_for_v2_1_0(self, content: str) -> str:
        """Mettre à jour les imports pour Oracle Enhanced v2.1.0"""
        # Corrections d'imports courantes
        replacements = {
            "from argumentation_analysis.agents.core.oracle.oracle_base_agent": "from argumentation_analysis.agents.core.oracle.base",
            "from argumentation_analysis.agents.core.oracle.dataset_access_manager": "from argumentation_analysis.agents.core.oracle.data_access",
            "from tests.unit.argumentation_analysis.agents.core.oracle": "from tests.unit.argumentation_analysis.agents.core.oracle",
        }
        
        for old_import, new_import in replacements.items():
            content = content.replace(old_import, new_import)
            
        return content
    
    def generate_integration_report(self, inventory: Dict, analyses: Dict, 
                                   test_results: Dict, integrations: Dict) -> str:
        """Générer le rapport d'intégration"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""# Rapport d'Intégration du Code Récupéré
**Date:** {timestamp}
**Oracle Enhanced:** v2.1.0

## Résumé de l'Inventaire

"""
        
        total_files = sum(len(files) for files in inventory.values())
        report += f"**Total fichiers récupérés:** {total_files}\n\n"
        
        for directory, files in inventory.items():
            report += f"### {directory}\n"
            for file in files:
                analysis = analyses.get(file, {})
                priority = analysis.get("priority", "unknown")
                oracle_related = analysis.get("oracle_related", False)
                oracle_indicator = " 🔮" if oracle_related else ""
                report += f"- `{file}` ({priority}){oracle_indicator}\n"
            report += "\n"
        
        # Résultats des tests
        report += "## Résultats des Tests de Fonctionnalité\n\n"
        
        successful_tests = sum(1 for result in test_results.values() 
                             if result.get("syntax_check", False))
        report += f"**Fichiers avec syntaxe valide:** {successful_tests}/{len(test_results)}\n\n"
        
        for file_path, result in test_results.items():
            status = "✅" if result.get("syntax_check", False) else "❌"
            report += f"### {status} `{file_path}`\n"
            
            if result.get("syntax_check"):
                report += "- ✅ Syntaxe Python valide\n"
            else:
                report += "- ❌ Erreurs de syntaxe\n"
                
            if result.get("import_check"):
                report += "- ✅ Imports fonctionnels\n"
            elif "import" in str(result.get("errors", [])):
                report += "- ⚠️ Problèmes d'imports\n"
                
            if result.get("pytest_collect"):
                report += "- ✅ Collecte pytest réussie\n"
            elif "test_" in file_path:
                report += "- ⚠️ Problèmes avec pytest\n"
                
            if result.get("errors"):
                report += "**Erreurs:**\n"
                for error in result["errors"][:3]:  # Limite à 3 erreurs
                    report += f"- {error}\n"
            report += "\n"
        
        # Résultats d'intégration
        report += "## Résultats d'Intégration\n\n"
        
        successful_integrations = sum(1 for result in integrations.values() 
                                    if result.get("status") == "integrated")
        report += f"**Intégrations réussies:** {successful_integrations}/{len(integrations)}\n\n"
        
        for source, result in integrations.items():
            status_icon = "✅" if result.get("status") == "integrated" else "❌"
            report += f"### {status_icon} `{source}`\n"
            report += f"**Destination:** `{result.get('target', 'N/A')}`\n"
            report += f"**Statut:** {result.get('status', 'unknown')}\n"
            
            if result.get("modernized"):
                report += "- ✅ Modernisé pour v2.1.0\n"
            if result.get("error"):
                report += f"**Erreur:** {result['error']}\n"
            report += "\n"
        
        return report
    
    def cleanup_recovered_directories(self, integrations: Dict[str, Any]):
        """Nettoyer les répertoires recovered après intégration réussie"""
        successful_integrations = [source for source, result in integrations.items()
                                 if result.get("status") == "integrated"]
        
        directories_to_remove = set()
        
        for source_path in successful_integrations:
            # Marquer le répertoire parent pour suppression
            parent_dir = Path(source_path).parent
            if "recovered" in str(parent_dir):
                directories_to_remove.add(parent_dir)
        
        cleanup_report = []
        for dir_path in directories_to_remove:
            full_path = self.project_root / dir_path
            try:
                if full_path.exists():
                    shutil.rmtree(full_path)
                    cleanup_report.append(f"✅ Supprimé: {dir_path}")
            except Exception as e:
                cleanup_report.append(f"❌ Erreur suppression {dir_path}: {e}")
        
        return cleanup_report

def main():
    """Fonction principale d'intégration"""
    integrator = RecoveredCodeIntegrator()
    
    print("🔄 Intégration du Code Récupéré - Oracle Enhanced v2.1.0")
    print("=" * 60)
    
    # Phase 1: Inventaire
    print("\n📋 Phase 1: Inventaire du code récupéré...")
    inventory = integrator.scan_recovered_directories()
    
    total_files = sum(len(files) for files in inventory.values())
    print(f"📁 Trouvé {total_files} fichiers dans {len(inventory)} répertoires")
    
    # Phase 2: Analyse du contenu
    print("\n🔍 Phase 2: Analyse du contenu...")
    analyses = {}
    all_files = []
    for files in inventory.values():
        all_files.extend(files)
    
    for file_path in all_files:
        print(f"   Analyse: {file_path}")
        analyses[file_path] = integrator.analyze_file_content(file_path)
    
    # Phase 3: Tests de fonctionnalité
    print("\n🧪 Phase 3: Tests de fonctionnalité...")
    test_results = {}
    python_files = [f for f in all_files if f.endswith('.py')]
    
    for file_path in python_files:
        print(f"   Test: {file_path}")
        test_results[file_path] = integrator.test_file_functionality(file_path)
    
    # Phase 4: Intégration
    print("\n🔧 Phase 4: Intégration dans la structure principale...")
    integrations = {}
    
    for file_path in all_files:
        analysis = analyses[file_path]
        target_dir = integrator.determine_integration_target(file_path, analysis)
        print(f"   Intégration: {file_path} → {target_dir}")
        integrations[file_path] = integrator.integrate_file(file_path, target_dir, analysis)
    
    # Phase 5: Génération du rapport
    print("\n📄 Phase 5: Génération des rapports...")
    
    # Rapport de tests
    test_report_path = integrator.project_root / "logs/recovered_code_testing_report.md"
    test_report = integrator.generate_integration_report(inventory, analyses, test_results, integrations)
    
    with open(test_report_path, 'w', encoding='utf-8') as f:
        f.write(test_report)
    
    # Mapping d'intégration
    mapping_path = integrator.project_root / "logs/recovered_code_integration_mapping.json"
    mapping_data = {
        "timestamp": datetime.now().isoformat(),
        "inventory": inventory,
        "analyses": analyses,
        "test_results": test_results,
        "integrations": integrations
    }
    
    with open(mapping_path, 'w', encoding='utf-8') as f:
        json.dump(mapping_data, f, indent=2, ensure_ascii=False)
    
    # Phase 6: Nettoyage
    print("\n🧹 Phase 6: Nettoyage des répertoires recovered...")
    cleanup_report = integrator.cleanup_recovered_directories(integrations)
    
    for item in cleanup_report:
        print(f"   {item}")
    
    # Résumé final
    print("\n" + "=" * 60)
    print("📊 RÉSUMÉ DE L'INTÉGRATION")
    print("=" * 60)
    
    successful_integrations = sum(1 for result in integrations.values() 
                                if result.get("status") == "integrated")
    successful_tests = sum(1 for result in test_results.values() 
                         if result.get("syntax_check", False))
    oracle_files = sum(1 for analysis in analyses.values() 
                      if analysis.get("oracle_related", False))
    
    print(f"📁 Fichiers traités: {total_files}")
    print(f"🧪 Tests réussis: {successful_tests}/{len(test_results)}")
    print(f"🔮 Fichiers Oracle/Sherlock: {oracle_files}")
    print(f"✅ Intégrations réussies: {successful_integrations}/{len(integrations)}")
    print(f"📄 Rapport généré: {test_report_path}")
    print(f"🗺️ Mapping sauvé: {mapping_path}")
    
    if successful_integrations == len(integrations):
        print("\n🎉 INTÉGRATION COMPLÈTE RÉUSSIE!")
    else:
        print(f"\n⚠️ {len(integrations) - successful_integrations} intégrations ont échoué")
    
    return successful_integrations == len(integrations)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)