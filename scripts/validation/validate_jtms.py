#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Raccourci - Validation JTMS Web Interface
=========================================

Script de raccourci pour lancer facilement la validation JTMS
depuis la racine du projet.

Usage: python validate_jtms.py
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Lance le validateur JTMS depuis la racine"""
    project_root = Path(__file__).resolve().parent
    validator_path = project_root / "validation" / "web_interface" / "validate_jtms_web_interface.py"
    
    if not validator_path.exists():
        print(f"❌ Validateur JTMS non trouvé: {validator_path}")
        return 1
    
    print("🚀 Lancement Validation JTMS Web Interface...")
    print(f"📍 Localisation: {validator_path}")
    print()
    
    # Exécution du validateur
    try:
        result = subprocess.run([sys.executable, str(validator_path)], 
                              cwd=str(project_root))
        return result.returncode
    except KeyboardInterrupt:
        print("\n🛑 Validation interrompue")
        return 1
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())