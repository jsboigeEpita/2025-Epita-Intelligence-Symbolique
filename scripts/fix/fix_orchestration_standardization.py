import project_core.core_from_scripts.auto_env
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
                if "from argumentation_analysis.utils.semantic_kernel_compatibility import {', '.join(custom_imports)}");]*AgentGroupChat[^;]*'
            
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