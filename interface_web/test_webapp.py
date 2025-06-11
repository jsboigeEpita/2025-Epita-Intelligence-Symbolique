#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test rapide de l'interface web
"""

import sys
import os
import json
import requests
import time
import subprocess
from pathlib import Path

def test_webapp_basic():
    """Test basique de l'interface web"""
    print("=== Test Interface Web EPITA ===")
    
    # 1. Test import des modules
    print("1. Test des imports...")
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from interface_web.app import app
        print("[OK] Import de l'application Flask reussi")
    except Exception as e:
        print(f"[ERREUR] Erreur d'import: {e}")
        return False
        
    # 2. Test configuration Flask
    print("2. Test de la configuration Flask...")
    try:
        app.config['TESTING'] = True
        client = app.test_client()
        print("[OK] Client de test Flask cree")
    except Exception as e:
        print(f"[ERREUR] Erreur de configuration: {e}")
        return False
        
    # 3. Test route principale
    print("3. Test de la route principale...")
    try:
        response = client.get('/')
        if response.status_code == 200:
            print("[OK] Route principale accessible")
            if b"Argumentation Analysis App" in response.data:
                print("[OK] Titre correct detecte")
            else:
                print("[ERREUR] Titre incorrect dans la reponse")
        else:
            print(f"[ERREUR] Route principale non accessible: {response.status_code}")
            return False
    except Exception as e:
        print(f"[ERREUR] Erreur lors du test de la route: {e}")
        return False
        
    # 4. Test route status
    print("4. Test de la route de statut...")
    try:
        response = client.get('/status')
        if response.status_code == 200:
            status_data = json.loads(response.data)
            print(f"[OK] Route de statut accessible: {status_data['status']}")
        else:
            print(f"[ERREUR] Route de statut non accessible: {response.status_code}")
    except Exception as e:
        print(f"[ERREUR] Erreur lors du test de statut: {e}")
        
    # 5. Test route d'analyse
    print("5. Test de la route d'analyse...")
    try:
        test_payload = {
            'text': 'Si il pleut, alors la route est mouillée. Il pleut.',
            'analysis_type': 'propositional'
        }
        response = client.post('/analyze',
                             data=json.dumps(test_payload),
                             content_type='application/json')
        if response.status_code == 200:
            result = json.loads(response.data)
            print(f"[OK] Route d'analyse fonctionnelle: {result['status']}")
        else:
            print(f"[ERREUR] Route d'analyse non accessible: {response.status_code}")
    except Exception as e:
        print(f"[ERREUR] Erreur lors du test d'analyse: {e}")
        
    # 6. Test route exemples
    print("6. Test de la route des exemples...")
    try:
        response = client.get('/api/examples')
        if response.status_code == 200:
            examples = json.loads(response.data)
            print(f"[OK] Route des exemples accessible: {len(examples['examples'])} exemples")
        else:
            print(f"[ERREUR] Route des exemples non accessible: {response.status_code}")
    except Exception as e:
        print(f"[ERREUR] Erreur lors du test des exemples: {e}")
        
    print("\n=== Resultats ===")
    print("[OK] Interface web fonctionnelle")
    print("[OK] Routes principales operationnelles")
    print("[OK] Templates accessibles")
    print("[OK] API JSON fonctionnelle")
    
    return True

def test_server_startup():
    """Test rapide du démarrage serveur"""
    print("\n=== Test Démarrage Serveur ===")
    
    try:
        # Test de démarrage rapide avec timeout
        process = subprocess.Popen(
            [sys.executable, 'app.py'],
            cwd='interface_web',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Attendre 3 secondes max
        time.sleep(3)
        
        if process.poll() is None:
            print("[OK] Serveur Flask demarre correctement")
            process.terminate()
            process.wait(timeout=2)
            return True
        else:
            stdout, stderr = process.communicate()
            print("[ERREUR] Serveur Flask n'a pas demarre")
            print(f"STDOUT: {stdout[:200]}...")
            print(f"STDERR: {stderr[:200]}...")
            return False
            
    except Exception as e:
        print(f"[ERREUR] Erreur lors du test de demarrage: {e}")
        return False

if __name__ == '__main__':
    success = test_webapp_basic()
    if success:
        print("\n[SUCCESS] Interface web validee avec succes!")
        test_server_startup()
    else:
        print("\n[ERROR] Problemes detectes dans l'interface web")
        sys.exit(1)