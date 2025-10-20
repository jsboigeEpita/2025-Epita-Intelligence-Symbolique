#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Solution de contournement pour les problèmes de pip/setuptools.
Configure manuellement le PYTHONPATH pour permettre l'importation du package.
"""

import sys
import os
from pathlib import Path


def fix_pythonpath():
    """Configure le PYTHONPATH pour inclure le projet."""
    project_root = Path(__file__).parent.parent.parent

    # Ajouter le répertoire racine du projet au PYTHONPATH
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        print(f"✅ Ajouté au PYTHONPATH: {project_root}")

    # Créer un fichier .pth pour rendre permanent
    try:
        import site

        user_site = site.getusersitepackages()
        os.makedirs(user_site, exist_ok=True)

        pth_file = Path(user_site) / "argumentation_analysis.pth"
        with open(pth_file, "w") as f:
            f.write(str(project_root))

        print(f"✅ Fichier .pth créé: {pth_file}")
        return True
    except Exception as e:
        print(f"⚠️  Impossible de créer le fichier .pth: {e}")
        return False


def test_import():
    """Teste l'importation du package."""
    try:
        pass

        print("✅ Import argumentation_analysis: OK")
        return True
    except ImportError as e:
        print(f"❌ Import argumentation_analysis: {e}")
        return False


def create_startup_script():
    """Crée un script de démarrage pour configurer l'environnement."""
    project_root = Path(__file__).parent.parent.parent

    startup_content = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de configuration automatique de l'environnement.
À exécuter avant d'utiliser le projet.
"""

import sys
from pathlib import Path

# Ajouter le projet au PYTHONPATH
project_root = Path(r"{project_root}")
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print("🚀 Environnement configuré pour le projet Intelligence Symbolique")
print(f"📁 Répertoire projet: {{project_root}}")

# Tester les imports essentiels
try:
    import argumentation_analysis
    print("✅ Package principal: OK")
except ImportError as e:
    print(f"❌ Package principal: {{e}}")

# Tester les dépendances essentielles
essential_deps = ["numpy", "pandas", "matplotlib", "cryptography"]
for dep in essential_deps:
    try:
        __import__(dep)
        print(f"✅ {{dep}}: OK")
    except ImportError:
        print(f"❌ {{dep}}: Manquant")

print("\\n🎯 Pour utiliser le projet:")
print("1. Exécutez ce script: python setup_env.py")
print("2. Puis utilisez Python normalement")
print("3. Ou importez ce module au début de vos scripts")
'''

    startup_file = project_root / "setup_env.py"
    with open(startup_file, "w", encoding="utf-8") as f:
        f.write(startup_content)

    print(f"✅ Script de démarrage créé: {startup_file}")
    return startup_file


def main():
    """Fonction principale."""
    print("🔧 Configuration manuelle de l'environnement...")
    print("=" * 50)

    # Configurer PYTHONPATH
    fix_pythonpath()

    # Tester l'import
    import_ok = test_import()

    # Créer script de démarrage
    startup_file = create_startup_script()

    print("=" * 50)
    if import_ok:
        print("🎉 SUCCÈS: Package accessible!")
        print("\\nVous pouvez maintenant:")
        print("  - Importer le package: import argumentation_analysis")
        print("  - Exécuter les tests avec le mock JPype")
        print(f"  - Utiliser le script: python {startup_file.name}")
    else:
        print("⚠️  PARTIEL: Configuration appliquée mais import échoue")
        print("\\nSolutions alternatives:")
        print(f"  - Exécutez: python {startup_file.name}")
        print("  - Ou ajoutez manuellement le projet au PYTHONPATH")

    return import_ok


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
