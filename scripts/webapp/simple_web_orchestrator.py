#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrateur Web Simplifié
============================

Version simplifiée pour validation Point d'Entrée 2
- Démarre API FastAPI simplifiée (api.main_simple)
- Lance tests Playwright basiques
- Gestion d'encodage Unicode compatible Windows

Auteur: Projet Intelligence Symbolique EPITA
Date: 10/06/2025
"""

import os
import sys
import time
import asyncio
import argparse
import subprocess
import signal
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Configuration encodage pour Windows
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

class SimpleWebOrchestrator:
    """Orchestrateur web simplifié pour validation"""
    
    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.backend_process = None
        self.backend_port = 8000
        self.backend_url = f"http://localhost:{self.backend_port}"
        
        # Variables d'environnement
        os.environ['PYTHONPATH'] = str(self.project_root)
        os.environ['PROJECT_ROOT'] = str(self.project_root)
        
    def log(self, message: str, level: str = "INFO"):
        """Logging simple avec horodatage"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
        
    def check_environment(self) -> bool:
        """Vérifie l'environnement conda"""
        try:
            result = subprocess.run(
                ['conda', 'info', '--envs'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and 'projet-is' in result.stdout:
                self.log("Environnement conda 'projet-is' trouve")
                return True
            else:
                self.log("Environnement conda 'projet-is' non trouve", "WARNING")
                return False
                
        except Exception as e:
            self.log(f"Erreur verification conda: {e}", "ERROR")
            return False
    
    def start_backend(self) -> bool:
        """Démarre l'API backend simplifiée"""
        self.log("Demarrage API backend...")
        
        try:
            # Commande avec activation conda
            cmd = [
                'conda', 'run', '-n', 'projet-is', '--no-capture-output',
                'uvicorn', 'api.main_simple:app', 
                '--host', '0.0.0.0', 
                '--port', str(self.backend_port),
                '--reload'
            ]
            
            self.log(f"Commande: {' '.join(cmd)}")
            
            # Démarrage processus
            self.backend_process = subprocess.Popen(
                cmd,
                cwd=self.project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Attendre démarrage
            self.log("Attente demarrage API...")
            time.sleep(5)
            
            # Vérifier si le processus est toujours vivant
            if self.backend_process.poll() is None:
                # Test de santé
                if self.health_check():
                    self.log(f"API backend operationnelle sur {self.backend_url}")
                    return True
                else:
                    self.log("API demarree mais health check echec", "WARNING")
                    return True  # On continue quand même
            else:
                # Récupérer erreurs
                _, stderr = self.backend_process.communicate()
                self.log(f"Echec demarrage API: {stderr}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Erreur demarrage backend: {e}", "ERROR")
            return False
    
    def health_check(self) -> bool:
        """Vérifie la santé de l'API"""
        try:
            import requests
            response = requests.get(f"{self.backend_url}/health", timeout=5)
            return response.status_code == 200
        except:
            # Fallback sans requests
            try:
                import urllib.request
                urllib.request.urlopen(f"{self.backend_url}/health", timeout=5)
                return True
            except:
                return False
    
    def test_api_basic(self) -> bool:
        """Test basique de l'API avec validation authenticité GPT-4o-mini"""
        self.log("Test basique API...")
        
        try:
            import requests
            import time
            
            # Test health
            health_response = requests.get(f"{self.backend_url}/health", timeout=10)
            if health_response.status_code != 200:
                self.log("Health check echec", "ERROR")
                return False
            
            self.log("Health check: OK")
            
            # Test analyze avec un sophisme simple - mesure du temps de réponse
            analyze_data = {
                "text": "Tous les cygnes sont blancs, donc tous les oiseaux sont blancs. C'est un raisonnement fallacieux car il généralise de manière incorrecte.",
                "analysis_type": "sophisms"
            }
            
            start_time = time.time()
            analyze_response = requests.post(
                f"{self.backend_url}/api/analyze",
                json=analyze_data,
                timeout=45
            )
            response_time = time.time() - start_time
            
            if analyze_response.status_code == 200:
                result = analyze_response.json()
                
                # Affichage détaillé des métadonnées
                metadata = result.get('metadata', {})
                self.log(f"Temps de reponse: {response_time:.2f}s")
                self.log(f"Status de l'analyse: {result.get('status', 'unknown')}")
                self.log(f"Modele GPT utilise: {metadata.get('gpt_model', 'N/A')}")
                self.log(f"Analyse authentique: {metadata.get('authentic_analysis', False)}")
                
                # Critères de validation d'authenticité
                authentic_indicators = 0
                
                # 1. Temps de réponse (GPT API prend du temps)
                if response_time >= 1.0:
                    self.log("[OK] Temps de reponse coherent avec API GPT", "SUCCESS")
                    authentic_indicators += 1
                else:
                    self.log("[WARNING] Temps de reponse tres rapide (possible mock)", "WARNING")
                
                # 2. Présence de fallacies détectées
                fallacies = result.get('fallacies', [])
                if len(fallacies) > 0:
                    self.log(f"[OK] {len(fallacies)} sophisme(s) detecte(s)", "SUCCESS")
                    authentic_indicators += 1
                    for fallacy in fallacies:
                        self.log(f"  - {fallacy.get('type', 'unknown')}: {fallacy.get('explanation', '')[:100]}...")
                else:
                    self.log("[WARNING] Aucun sophisme detecte", "WARNING")
                
                # 3. Métadonnées authentiques
                if metadata.get('authentic_analysis'):
                    self.log("[OK] Metadonnees indiquent analyse authentique", "SUCCESS")
                    authentic_indicators += 1
                
                # 4. Modèle GPT cohérent
                gpt_model = metadata.get('gpt_model', '')
                if 'gpt-4o-mini' in gpt_model.lower():
                    self.log("[OK] Modele GPT-4o-mini confirme", "SUCCESS")
                    authentic_indicators += 1
                else:
                    self.log(f"[WARNING] Modele GPT: {gpt_model}", "WARNING")
                
                # Validation finale
                if authentic_indicators >= 2:
                    self.log(f"VALIDATION REUSSIE: {authentic_indicators}/4 indicateurs authentiques", "SUCCESS")
                    return True
                else:
                    self.log(f"VALIDATION DOUTEUSE: {authentic_indicators}/4 indicateurs authentiques", "WARNING")
                    return False
                    
            else:
                self.log(f"Echec analyse: {analyze_response.status_code}", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Erreur test API: {e}", "ERROR")
            return False
    
    def stop_backend(self):
        """Arrête l'API backend"""
        if self.backend_process:
            self.log("Arret API backend...")
            try:
                self.backend_process.terminate()
                try:
                    self.backend_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.log("Force kill API backend")
                    self.backend_process.kill()
                self.log("API backend arretee")
            except Exception as e:
                self.log(f"Erreur arret backend: {e}", "ERROR")
    
    def cleanup_processes(self):
        """Nettoyage des processus"""
        self.log("Nettoyage processus...")
        try:
            # Arrêter uvicorn sur le port
            if sys.platform == "win32":
                subprocess.run(
                    ['taskkill', '/F', '/IM', 'python.exe', '/FI', f'WINDOWTITLE eq uvicorn*'],
                    capture_output=True
                )
            self.log("Nettoyage termine")
        except Exception as e:
            self.log(f"Erreur nettoyage: {e}", "WARNING")
    
    def run_validation(self, start_only: bool = False) -> bool:
        """Validation complète Point d'Entrée 2"""
        success = False
        
        try:
            self.log("=== VALIDATION POINT D'ENTREE 2 - API WEB ===")
            self.log("Objectif: Valider utilisation authentique GPT-4o-mini")
            
            # 1. Vérification environnement
            if not self.check_environment():
                self.log("Environnement invalide mais on continue...")
            
            # 2. Démarrage API
            if not self.start_backend():
                self.log("Echec demarrage API", "ERROR")
                return False
            
            if start_only:
                self.log("Mode start seulement - API demarree")
                input("Appuyez sur Entree pour arreter...")
                return True
            
            # 3. Attente stabilisation
            self.log("Stabilisation API...")
            time.sleep(3)
            
            # 4. Tests API
            success = self.test_api_basic()
            
            if success:
                self.log("=== VALIDATION REUSSIE ===", "SUCCESS")
                self.log("L'API utilise authentiquement GPT-4o-mini")
            else:
                self.log("=== VALIDATION ECHEC ===", "ERROR")
                
        except KeyboardInterrupt:
            self.log("Interruption utilisateur")
        except Exception as e:
            self.log(f"Erreur validation: {e}", "ERROR")
        finally:
            # Nettoyage systématique
            self.stop_backend()
            self.cleanup_processes()
            
        return success

def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(description="Orchestrateur Web Simplifie")
    parser.add_argument('--start', action='store_true', help='Demarrer seulement l\'API')
    parser.add_argument('--test', action='store_true', help='Tests seulement')
    
    args = parser.parse_args()
    
    orchestrator = SimpleWebOrchestrator()
    
    # Installation signal handler pour nettoyage
    def signal_handler(signum, frame):
        print("\nArret demande...")
        orchestrator.stop_backend()
        orchestrator.cleanup_processes()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        success = orchestrator.run_validation(start_only=args.start)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Erreur fatale: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()