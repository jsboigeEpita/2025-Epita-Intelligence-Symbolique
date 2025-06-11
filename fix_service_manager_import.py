#!/usr/bin/env python3
"""
Correction du problème d'import dans ServiceManager
"""
import sys
from pathlib import Path

# Ajouter le répertoire racine du projet au sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

print(f"✅ Chemin racine ajouté: {project_root}")

# Test maintenant ServiceManager
try:
    from argumentation_analysis.orchestration.service_manager import ServiceManager
    print("✅ ServiceManager importé avec succès !")
    
    # Test instanciation basique
    sm = ServiceManager(config={'test': True})
    print("✅ ServiceManager instancié avec succès !")
    
except Exception as e:
    print(f"❌ Erreur ServiceManager: {e}")
    import traceback
    traceback.print_exc()