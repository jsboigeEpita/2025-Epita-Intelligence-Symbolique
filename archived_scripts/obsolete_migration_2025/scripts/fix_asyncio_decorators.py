#!/usr/bin/env python3
"""
Script pour ajouter automatiquement les décorateurs @pytest.mark.asyncio manquants
"""

import os
import re
from pathlib import Path

def fix_asyncio_decorators():
    """Ajoute les décorateurs @pytest.mark.asyncio manquants"""
    test_dir = Path("tests/validation_sherlock_watson")
    fixed_files = []
    
    for test_file in test_dir.glob("*.py"):
        print(f"Traitement: {test_file}")
        
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Chercher les fonctions async test sans décorateur
        lines = content.split('\n')
        new_lines = []
        i = 0
        modified = False
        
        while i < len(lines):
            line = lines[i]
            
            # Si on trouve une fonction async test
            if re.match(r'async def test_', line.strip()):
                # Vérifier si la ligne précédente a déjà le décorateur
                prev_line = lines[i-1].strip() if i > 0 else ""
                if not prev_line.startswith('@pytest.mark.asyncio'):
                    # Ajouter le décorateur
                    indent = len(line) - len(line.lstrip())
                    decorator = ' ' * indent + '@pytest.mark.asyncio'
                    new_lines.append(decorator)
                    modified = True
                    print(f"  + Ajout décorateur à: {line.strip()}")
            
            new_lines.append(line)
            i += 1
        
        if modified:
            # Vérifier si pytest est importé
            new_content = '\n'.join(new_lines)
            if 'import pytest' not in new_content:
                # Ajouter l'import pytest au début
                import_line = "import pytest\n"
                # Insérer après les autres imports
                lines_with_import = new_content.split('\n')
                insert_pos = 0
                for j, line in enumerate(lines_with_import):
                    if line.startswith('import ') or line.startswith('from '):
                        insert_pos = j + 1
                    elif line.strip() == "":
                        continue
                    else:
                        break
                
                lines_with_import.insert(insert_pos, import_line.strip())
                new_content = '\n'.join(lines_with_import)
                print(f"  + Ajout import pytest")
            
            with open(test_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            fixed_files.append(str(test_file))
    
    print(f"\nFichiers modifiés: {len(fixed_files)}")
    for file in fixed_files:
        print(f"  - {file}")

if __name__ == "__main__":
    fix_asyncio_decorators()