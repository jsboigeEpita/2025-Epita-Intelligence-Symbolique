#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test direct de lancement de l'API pour debug
"""

import subprocess
import sys
import os
from pathlib import Path

def test_direct_launch():
    print("=== TEST LANCEMENT DIRECT ===")
    
    # Configuration environnement
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path.cwd())
    
    # Commande de test
    cmd = ['python', '-m', 'argumentation_analysis.services.web_api.app', '--port', '5003']
    
    print(f"Commande: {' '.join(cmd)}")
    print(f"PYTHONPATH: {env.get('PYTHONPATH')}")
    print(f"Répertoire courant: {Path.cwd()}")
    
    try:
        # Lancement avec capture output
        result = subprocess.run(
            cmd,
            env=env,
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            timeout=10  # Timeout court pour voir l'erreur rapidement
        )
        
        print(f"\nCode de retour: {result.returncode}")
        
        if result.stdout:
            print(f"\nStdout:\n{result.stdout}")
            
        if result.stderr:
            print(f"\nStderr:\n{result.stderr}")
            
    except subprocess.TimeoutExpired as e:
        print(f"\nTimeout après 10s - probablement démarré avec succès")
        print(f"Stdout disponible: {e.stdout}")
        print(f"Stderr disponible: {e.stderr}")
        
    except Exception as e:
        print(f"\nErreur: {e}")

if __name__ == "__main__":
    test_direct_launch()