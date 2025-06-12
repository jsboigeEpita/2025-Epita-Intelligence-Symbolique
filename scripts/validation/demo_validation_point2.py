#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Démonstration Validation Point d'Entrée 2
==========================================

Script de démonstration rapide pour valider l'utilisation
authentique de GPT-4o-mini dans l'API web.

Usage:
    python scripts/demo_validation_point2.py
    python scripts/demo_validation_point2.py --start-only
"""

import sys
import argparse
from pathlib import Path

# Ajouter le répertoire du projet au path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

# Import direct pour éviter les conflits de dépendances
sys.path.insert(0, str(project_root / "scripts" / "webapp"))
from simple_web_orchestrator import SimpleWebOrchestrator

def main():
    parser = argparse.ArgumentParser(description="Demo Validation Point d'Entree 2")
    parser.add_argument('--start-only', action='store_true', 
                       help='Demarre seulement l\'API (mode interactif)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("[DEMO] VALIDATION POINT D'ENTREE 2")
    print("=" * 60)
    print("Objectif: Prouver utilisation authentique GPT-4o-mini")
    print("API: FastAPI simplifiee avec OpenAI direct")
    print("")
    
    orchestrator = SimpleWebOrchestrator()
    
    try:
        if args.start_only:
            print("Mode interactif - API sera maintenue active...")
            success = orchestrator.run_validation(start_only=True)
        else:
            print("Mode automatique - validation complete...")
            success = orchestrator.run_validation(start_only=False)
        
        if success:
            print("")
            print("[SUCCESS] DEMONSTRATION REUSSIE!")
            print("L'API utilise authentiquement GPT-4o-mini")
            print("")
            print("Rapport complet: _temp/validation_point2/rapport_validation_api_web.md")
        else:
            print("")
            print("[ERROR] DEMONSTRATION ECHEC")
            print("Verifiez la configuration OpenAI et l'environnement conda")
            
    except KeyboardInterrupt:
        print("\n[STOP] Demo interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n[ERROR] Erreur demo: {e}")
        return 1
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())