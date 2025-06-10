#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SCRIPT DE STANDARDISATION D'ORCHESTRATION
========================================

Standardise tous les usages d'orchestration sur semantic_kernel.agents.AgentGroupChat
et nettoie les imports redondants selon le diagnostic.

OBJECTIF: Résoudre les incohérences d'orchestration identifiées
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Tuple
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OrchestrationStandardizer:
    """Standardise les approches d'orchestration dans le projet."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.files_to_fix = []
        self.backup_dir = self.project_root / "backup_orchestration_fixes"
        
    def analyze_orchestration_usage(self) -> Dict[str, List[str]]:
        """Analyse l'utilisation des différents systèmes d'orchestration."""
        
        analysis = {
            "agent_group_chat_usage": [],
            "group_chat_orchestration_usage": [],
            "compatibility_imports": [],
            "direct_sk_imports": [],
            "mixed_usage_files": []
        }
        
        # Rechercher tous les fichiers Python
        python_files = list(self.project_root.rglob("*.py"))
        
        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                file_str = str(file_path.relative_to(self.project_root))
                
                # Analyser les imports et usages
                if "from argumentation_analysis.utils.semantic_kernel_compatibility import" in content:
                    if "AgentGroupChat" in content:
                        analysis["compatibility_imports"].append(file_str)
                
                if "from semantic_kernel.agents import" in content:
                    if "AgentGroupChat" in content:
                        analysis["direct_sk_imports"].append(file_str)
                
                if "AgentGroupChat(" in content:
                    analysis["agent_group_chat_usage"].append(file_str)
                
                if "GroupChatOrchestration(" in content:
                    analysis["group_chat_orchestration_usage"].append(file_str)
                
                # Détecter les fichiers avec usage mixte
                has_agent_group_chat = "AgentGroupChat" in content
                has_group_chat_orchestration = "GroupChatOrchestration" in content
                
                if has_agent_group_chat and has_group_chat_orchestration:
                    analysis["mixed_usage_files"].append(file_str)
                    
            except Exception as e:
                logger.warning(f"Erreur lors de l'analyse de {file_path}: {e}")
        
        return analysis
    
    def create_backup(self, file_path: Path) -> None:
        """Crée une sauvegarde d'un fichier avant modification."""
        
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)
        
        backup_path = self.backup_dir / file_path.name
        counter = 1
        while backup_path.exists():
            name_parts = file_path.stem, counter, file_path.suffix
            backup_path = self.backup_dir / f"{name_parts[0]}_backup_{name_parts[1]}{name_parts[2]}"
            counter += 1
        
        with open(file_path, 'r', encoding='utf-8') as src:
            with open(backup_path, 'w', encoding='utf-8') as dst:
                dst.write(src.read())
        
        logger.info(f"Sauvegarde créée: {backup_path}")
    
    def standardize_imports(self, file_path: Path) -> bool:
        """Standardise les imports d'orchestration dans un fichier."""
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            
            # 1. Remplacer les imports depuis le module de compatibilité
            compatibility_pattern = r'from argumentation_analysis\.utils\.semantic_kernel_compatibility import[^;]*AgentGroupChat[^;]*'
            
            if re.search(compatibility_pattern, content):
                # Extraire les autres imports nécessaires
                match = re.search(r'from argumentation_analysis\.utils\.semantic_kernel_compatibility import\s+\(([^)]+)\)', content, re.MULTILINE | re.DOTALL)
                if not match:
                    match = re.search(r'from argumentation_analysis\.utils\.semantic_kernel_compatibility import\s+([^\n]+)', content)
                
                if match:
                    imports_text = match.group(1)
                    imports_list = [imp.strip() for imp in imports_text.replace('\n', '').split(',')]
                    
                    # Séparer les imports SK des imports personnalisés
                    sk_imports = []
                    custom_imports = []
                    
                    for imp in imports_list:
                        imp = imp.strip()
                        if imp in ['Agent', 'AgentGroupChat', 'ChatCompletionAgent']:
                            sk_imports.append(imp)
                        else:
                            custom_imports.append(imp)
                    
                    # Construire les nouveaux imports
                    new_imports = []
                    if sk_imports:
                        new_imports.append(f"from semantic_kernel.agents import {', '.join(sk_imports)}")
                    if custom_imports:
                        new_imports.append(f"from argumentation_analysis.utils.semantic_kernel_compatibility import {', '.join(custom_imports)}")
                    
                    # Remplacer l'import original
                    content = re.sub(compatibility_pattern, '\n'.join(new_imports), content)
            
            # 2. Ajouter les imports manquants si nécessaire
            if "AgentGroupChat(" in content and "from semantic_kernel.agents import" not in content:
                # Ajouter l'import au bon endroit
                import_section = self._find_import_section(content)
                if import_section:
                    new_import = "from semantic_kernel.agents import AgentGroupChat"
                    content = content.replace(import_section, f"{import_section}\n{new_import}")
            
            # 3. Nettoyer les imports dupliqués
            content = self._clean_duplicate_imports(content)
            
            if content != original_content:
                self.create_backup(file_path)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                logger.info(f"✅ Standardisé les imports dans: {file_path.relative_to(self.project_root)}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la standardisation de {file_path}: {e}")
            return False
    
    def _find_import_section(self, content: str) -> str:
        """Trouve la section d'imports dans le contenu."""
        lines = content.split('\n')
        import_lines = []
        
        for line in lines:
            if line.strip().startswith(('import ', 'from ')) and 'semantic_kernel' in line:
                import_lines.append(line)
        
        return '\n'.join(import_lines) if import_lines else ""
    
    def _clean_duplicate_imports(self, content: str) -> str:
        """Nettoie les imports dupliqués."""
        lines = content.split('\n')
        seen_imports = set()
        cleaned_lines = []
        
        for line in lines:
            if line.strip().startswith(('import ', 'from ')):
                if line.strip() not in seen_imports:
                    seen_imports.add(line.strip())
                    cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def generate_migration_report(self, analysis: Dict[str, List[str]]) -> str:
        """Génère un rapport de migration."""
        
        report = []
        report.append("# RAPPORT DE STANDARDISATION D'ORCHESTRATION")
        report.append("=" * 50)
        report.append("")
        
        report.append("## 📊 ANALYSE ACTUELLE:")
        report.append(f"- Fichiers utilisant AgentGroupChat: {len(analysis['agent_group_chat_usage'])}")
        report.append(f"- Fichiers utilisant GroupChatOrchestration: {len(analysis['group_chat_orchestration_usage'])}")
        report.append(f"- Fichiers avec imports de compatibilité: {len(analysis['compatibility_imports'])}")
        report.append(f"- Fichiers avec imports SK directs: {len(analysis['direct_sk_imports'])}")
        report.append(f"- Fichiers avec usage mixte: {len(analysis['mixed_usage_files'])}")
        report.append("")
        
        report.append("## 🔧 FICHIERS À CORRIGER:")
        
        if analysis["compatibility_imports"]:
            report.append("### Imports de compatibilité à standardiser:")
            for file_path in analysis["compatibility_imports"]:
                report.append(f"  - {file_path}")
            report.append("")
        
        if analysis["mixed_usage_files"]:
            report.append("### Fichiers avec usage mixte nécessitant attention:")
            for file_path in analysis["mixed_usage_files"]:
                report.append(f"  - {file_path}")
            report.append("")
        
        report.append("## ✅ ACTIONS EFFECTUÉES:")
        report.append("- Standardisation des imports vers semantic_kernel.agents")
        report.append("- Nettoyage des imports redondants")
        report.append("- Création de sauvegardes automatiques")
        
        return '\n'.join(report)
    
    def run_standardization(self) -> bool:
        """Lance la standardisation complète."""
        
        logger.info("🚀 Début de la standardisation d'orchestration")
        
        # 1. Analyser l'état actuel
        analysis = self.analyze_orchestration_usage()
        
        # 2. Afficher le rapport d'analyse
        logger.info("📊 Analyse terminée:")
        logger.info(f"  - AgentGroupChat: {len(analysis['agent_group_chat_usage'])} fichiers")
        logger.info(f"  - GroupChatOrchestration: {len(analysis['group_chat_orchestration_usage'])} fichiers")
        logger.info(f"  - Imports de compatibilité: {len(analysis['compatibility_imports'])} fichiers")
        
        # 3. Standardiser les fichiers identifiés
        files_fixed = 0
        for file_str in analysis["compatibility_imports"]:
            file_path = self.project_root / file_str
            if self.standardize_imports(file_path):
                files_fixed += 1
        
        # 4. Générer le rapport final
        report = self.generate_migration_report(analysis)
        report_path = self.project_root / "RAPPORT_STANDARDISATION_ORCHESTRATION.md"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        logger.info(f"✅ Standardisation terminée: {files_fixed} fichiers corrigés")
        logger.info(f"📄 Rapport généré: {report_path}")
        
        return files_fixed > 0


def main():
    """Point d'entrée principal."""
    
    # Détecter le répertoire racine du projet
    current_dir = Path(__file__).parent.absolute()
    project_root = current_dir.parent
    
    logger.info(f"🔧 Standardisation d'orchestration dans: {project_root}")
    
    # Créer et lancer le standardisateur
    standardizer = OrchestrationStandardizer(str(project_root))
    success = standardizer.run_standardization()
    
    if success:
        logger.info("🎉 Standardisation terminée avec succès!")
        print("\n✅ NEXT STEPS:")
        print("1. Vérifiez les fichiers modifiés")
        print("2. Lancez les tests: pytest tests/integration/ -v")
        print("3. Consultez RAPPORT_STANDARDISATION_ORCHESTRATION.md")
    else:
        logger.info("ℹ️ Aucune correction nécessaire - Code déjà standardisé")
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())