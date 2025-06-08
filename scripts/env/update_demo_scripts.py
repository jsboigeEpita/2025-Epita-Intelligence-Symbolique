#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Mise à jour des scripts de démonstration pour l'environnement dédié.

Met à jour les scripts existants pour qu'ils utilisent automatiquement
l'environnement dédié et affichent des messages de transparence.
"""

import sys
import os
from pathlib import Path
import re

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Template pour l'en-tête des scripts
ENVIRONMENT_HEADER_TEMPLATE = '''#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
{description}

ENVIRONNEMENT DÉDIÉ REQUIS: conda activate projet-is
Ou utilisation via: .\\setup_project_env.ps1 -CommandToRun "python {script_path}"
"""

import sys
import os
from pathlib import Path

# Configuration automatique environnement dédié
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Vérification environnement (optionnel - commentaire pour éviter les erreurs)
try:
    from scripts.env.environment_helpers import print_environment_warning
    print_environment_warning()
except ImportError:
    print("ℹ️  Pour un environnement optimal: .\\\\setup_project_env.ps1 -CommandToRun \\"python {script_path}\\"")

'''

def update_script_with_environment_check(script_path: Path):
    """Met à jour un script Python avec la vérification d'environnement."""
    if not script_path.exists() or script_path.suffix != '.py':
        return False
    
    try:
        content = script_path.read_text(encoding='utf-8')
        
        # Vérifier si déjà mis à jour
        if "ENVIRONNEMENT DÉDIÉ REQUIS" in content:
            print(f"✅ Déjà mis à jour: {script_path.relative_to(PROJECT_ROOT)}")
            return False
        
        # Trouver la description existante
        description_match = re.search(r'"""([^"]+)"""', content)
        description = description_match.group(1).strip() if description_match else script_path.name
        
        # Créer le nouvel en-tête
        relative_path = script_path.relative_to(PROJECT_ROOT)
        new_header = ENVIRONMENT_HEADER_TEMPLATE.format(
            description=description,
            script_path=str(relative_path).replace('\\', '\\\\')
        )
        
        # Remplacer l'en-tête existant
        if content.startswith('#!'):
            # Garder le shebang et remplacer le reste
            lines = content.split('\n')
            shebang = lines[0] if lines[0].startswith('#!') else ''
            
            # Trouver la fin de l'en-tête
            start_idx = 1 if shebang else 0
            
            # Chercher la première ligne de code réel (après les imports et docstrings)
            code_start = start_idx
            for i, line in enumerate(lines[start_idx:], start_idx):
                if (line.strip() and 
                    not line.startswith('#') and 
                    not line.startswith('"""') and
                    not line.startswith("'''") and
                    'import' not in line and
                    'from' not in line and
                    line.strip() != ''):
                    code_start = i
                    break
            
            # Reconstruire le fichier
            new_content = new_header + '\n' + '\n'.join(lines[code_start:])
        else:
            new_content = new_header + '\n' + content
        
        # Sauvegarder
        script_path.write_text(new_content, encoding='utf-8')
        print(f"🔧 Mis à jour: {script_path.relative_to(PROJECT_ROOT)}")
        return True
        
    except Exception as e:
        print(f"❌ Erreur mise à jour {script_path}: {e}")
        return False

def find_demo_scripts():
    """Trouve tous les scripts de démonstration."""
    demo_dirs = [
        PROJECT_ROOT / "demos",
        PROJECT_ROOT / "scripts" / "sherlock_watson",
        PROJECT_ROOT / "scripts" / "demo",
        PROJECT_ROOT / "examples"
    ]
    
    demo_scripts = []
    for demo_dir in demo_dirs:
        if demo_dir.exists():
            for script in demo_dir.rglob("*.py"):
                if not script.name.startswith('__') and 'test' not in script.name.lower():
                    demo_scripts.append(script)
    
    return demo_scripts

def update_all_demo_scripts():
    """Met à jour tous les scripts de démonstration."""
    print("🔧 MISE À JOUR SCRIPTS DÉMONSTRATION")
    print("=" * 50)
    
    demo_scripts = find_demo_scripts()
    updated_count = 0
    
    for script in demo_scripts:
        if update_script_with_environment_check(script):
            updated_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 RÉSUMÉ: {updated_count} scripts mis à jour sur {len(demo_scripts)} trouvés")
    
    if updated_count > 0:
        print("\n💡 NOUVELLES RECOMMANDATIONS:")
        print("   Utilisez maintenant: .\\setup_project_env.ps1 -CommandToRun \"python <script>\"")
        print("   Au lieu de: python <script>")

def create_corrected_recommendations_doc():
    """Crée un document avec les recommandations corrigées."""
    doc_content = """# Recommandations Corrigées - Environnement Dédié

## 🎯 Nouvelles Instructions de Démarrage

### ✅ Commandes Corrigées

| Ancien (Incorrect) | Nouveau (Correct) |
|-------------------|------------------|
| `python demos/webapp/run_webapp.py` | `.\\setup_project_env.ps1 -CommandToRun "python demos/webapp/run_webapp.py"` |
| `python scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py` | `.\\setup_project_env.ps1 -CommandToRun "python scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py"` |
| `python -m pytest tests/` | `.\\setup_project_env.ps1 -CommandToRun "python -m pytest tests/"` |
| `pip install -r requirements.txt` | `conda env create -f environment.yml` puis `conda activate projet-is` |

### 🚀 Démarrage Rapide Corrigé

```powershell
# 1. Créer l'environnement (première fois seulement)
conda env create -f environment.yml

# 2. Lancer des démonstrations
.\\setup_project_env.ps1 -CommandToRun "python demos/webapp/run_webapp.py"
.\\setup_project_env.ps1 -CommandToRun "python scripts/sherlock_watson/run_sherlock_watson_moriarty_robust.py"

# 3. Exécuter des tests
.\\setup_project_env.ps1 -CommandToRun "python -m pytest tests/unit/ -v"

# 4. Vérification environnement
.\\setup_project_env.ps1 -CommandToRun "python scripts/env/check_environment.py"
```

### ⚠️ Erreurs Précédentes Corrigées

1. **Installation pip vs conda**: Utiliser `environment.yml` au lieu de `requirements.txt`
2. **Python système**: Toujours utiliser l'environnement dédié `projet-is`
3. **PYTHONPATH manuel**: Automatiquement configuré par `setup_project_env.ps1`
4. **Dépendances manquantes**: Toutes incluses dans `environment.yml`

### 🔍 Diagnostic et Résolution

```powershell
# Diagnostic rapide
.\\setup_project_env.ps1 -CommandToRun "python scripts/env/check_environment.py"

# Diagnostic complet
.\\setup_project_env.ps1 -CommandToRun "python scripts/env/diagnose_environment.py --full"

# Réinstallation si problème
conda env remove -n projet-is
conda env create -f environment.yml
```

### 📝 Pour les Nouveaux Agents

1. **TOUJOURS** utiliser `setup_project_env.ps1` pour l'exécution
2. **JAMAIS** exécuter directement avec `python <script>`
3. **VÉRIFIER** l'environnement avec `check_environment.py`
4. **CRÉER** l'environnement avec `conda env create -f environment.yml`

---
**Mise à jour**: 08/06/2025 - Corrections environnement dédié
"""
    
    doc_path = PROJECT_ROOT / "CORRECTED_RECOMMENDATIONS.md"
    doc_path.write_text(doc_content, encoding='utf-8')
    print(f"📄 Document créé: {doc_path.relative_to(PROJECT_ROOT)}")

def main():
    """Point d'entrée principal."""
    print("🔧 CORRECTION RECOMMANDATIONS ENVIRONNEMENT")
    print("=" * 60)
    
    # 1. Mettre à jour les scripts de démonstration
    update_all_demo_scripts()
    
    print()
    
    # 2. Créer le document de recommandations corrigées
    create_corrected_recommendations_doc()
    
    print("\n" + "=" * 60)
    print("✅ CORRECTIONS TERMINÉES")
    print("\nProchaines étapes:")
    print("1. Vérifier avec: .\\setup_project_env.ps1 -CommandToRun \"python scripts/env/check_environment.py\"")
    print("2. Lire: CORRECTED_RECOMMENDATIONS.md")
    print("3. Utiliser uniquement les nouvelles commandes")

if __name__ == "__main__":
    main()