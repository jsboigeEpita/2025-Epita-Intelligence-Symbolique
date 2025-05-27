#!/usr/bin/env python3
"""
Script pour corriger les constructeurs d'agents dans tous les tests
"""

import os
import re
import sys
from pathlib import Path

def find_test_files():
    """Trouve tous les fichiers de test"""
    test_files = []
    
    # Recherche dans le répertoire tests/
    for root, dirs, files in os.walk('tests'):
        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                test_files.append(os.path.join(root, file))
    
    return test_files

def fix_informal_agent_constructor(content):
    """Corrige les constructeurs InformalAgent"""
    
    # Pattern pour InformalAgent() sans paramètres
    pattern1 = r'InformalAgent\(\s*\)'
    replacement1 = 'InformalAgent(agent_id="test_agent", tools={})'
    
    # Pattern pour InformalAgent avec quelques paramètres mais manquant agent_id et tools
    pattern2 = r'InformalAgent\(\s*([^)]*)\s*\)'
    
    def replace_constructor(match):
        params = match.group(1).strip()
        if not params:
            return 'InformalAgent(agent_id="test_agent", tools={})'
        elif 'agent_id' not in params and 'tools' not in params:
            return f'InformalAgent(agent_id="test_agent", tools={{}}, {params})'
        elif 'agent_id' not in params:
            return f'InformalAgent(agent_id="test_agent", {params})'
        elif 'tools' not in params:
            return f'InformalAgent(tools={{}}, {params})'
        else:
            return match.group(0)  # Déjà correct
    
    content = re.sub(pattern1, replacement1, content)
    content = re.sub(pattern2, replace_constructor, content)
    
    return content

def fix_extract_agent_constructor(content):
    """Corrige les constructeurs ExtractAgent"""
    
    # Pattern pour ExtractAgent() sans paramètres
    pattern1 = r'ExtractAgent\(\s*\)'
    replacement1 = '''ExtractAgent(
        extract_agent=Mock(),
        validation_agent=Mock(),
        extract_plugin=Mock()
    )'''
    
    # Pattern pour ExtractAgent avec quelques paramètres
    pattern2 = r'ExtractAgent\(\s*([^)]*)\s*\)'
    
    def replace_extract_constructor(match):
        params = match.group(1).strip()
        if not params:
            return '''ExtractAgent(
        extract_agent=Mock(),
        validation_agent=Mock(),
        extract_plugin=Mock()
    )'''
        elif 'extract_agent' not in params:
            return f'''ExtractAgent(
        extract_agent=Mock(),
        validation_agent=Mock(),
        extract_plugin=Mock(),
        {params}
    )'''
        else:
            return match.group(0)  # Déjà correct
    
    content = re.sub(pattern1, replacement1, content)
    content = re.sub(pattern2, replace_extract_constructor, content)
    
    return content

def add_mock_import(content):
    """Ajoute l'import Mock si nécessaire"""
    
    if 'from unittest.mock import' in content:
        # Vérifie si Mock est déjà importé
        if 'Mock' not in content.split('from unittest.mock import')[1].split('\n')[0]:
            # Ajoute Mock à l'import existant
            content = re.sub(
                r'from unittest\.mock import ([^\n]+)',
                r'from unittest.mock import \1, Mock',
                content
            )
    elif 'import unittest.mock' in content:
        # Mock sera accessible via unittest.mock.Mock
        pass
    else:
        # Ajoute l'import Mock
        if 'import' in content:
            # Trouve la dernière ligne d'import
            lines = content.split('\n')
            last_import_line = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    last_import_line = i
            
            lines.insert(last_import_line + 1, 'from unittest.mock import Mock')
            content = '\n'.join(lines)
        else:
            # Ajoute au début du fichier après les commentaires
            lines = content.split('\n')
            insert_line = 0
            for i, line in enumerate(lines):
                if not line.strip().startswith('#') and line.strip():
                    insert_line = i
                    break
            
            lines.insert(insert_line, 'from unittest.mock import Mock')
            content = '\n'.join(lines)
    
    return content

def fix_test_file(file_path):
    """Corrige un fichier de test"""
    
    print(f"Correction de {file_path}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Ajoute l'import Mock si nécessaire
        if 'InformalAgent(' in content or 'ExtractAgent(' in content:
            content = add_mock_import(content)
        
        # Corrige les constructeurs
        content = fix_informal_agent_constructor(content)
        content = fix_extract_agent_constructor(content)
        
        # Sauvegarde si modifié
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  OK {file_path} corrigé")
            return True
        else:
            print(f"  - {file_path} déjà correct")
            return False
            
    except Exception as e:
        print(f"  ERREUR Erreur dans {file_path}: {str(e)}")
        return False

def main():
    """Fonction principale"""
    print("CORRECTION DES CONSTRUCTEURS D'AGENTS")
    print("=" * 50)
    
    test_files = find_test_files()
    print(f"Trouvé {len(test_files)} fichiers de test")
    
    corrected_files = 0
    for test_file in test_files:
        if fix_test_file(test_file):
            corrected_files += 1
    
    print(f"\nRésumé: {corrected_files}/{len(test_files)} fichiers corrigés")
    
    # Test rapide pour vérifier les corrections
    print("\nTest rapide des corrections...")
    try:
        from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
        from unittest.mock import Mock
        
        # Test InformalAgent
        agent = InformalAgent(agent_id="test", tools={})
        print("OK InformalAgent peut être créé avec les bons paramètres")
        
        # Test ExtractAgent
        from argumentation_analysis.agents.core.extract.extract_agent import ExtractAgent
        extract_agent = ExtractAgent(
            extract_agent=Mock(),
            validation_agent=Mock(),
            extract_plugin=Mock()
        )
        print("OK ExtractAgent peut être créé avec les bons paramètres")
        
    except Exception as e:
        print(f"ERREUR Erreur lors du test: {str(e)}")

if __name__ == "__main__":
    main()