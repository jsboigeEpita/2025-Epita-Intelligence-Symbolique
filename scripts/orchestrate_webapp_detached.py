#!/usr/bin/env python3
"""
Orchestrateur webapp détaché - utilise les outils de haut niveau existants
Démarre backend/frontend en arrière-plan et retourne immédiatement le contrôle
"""

import os
import sys
import time
import subprocess
import logging
from pathlib import Path

# Import du gestionnaire de haut niveau existant
sys.path.insert(0, str(Path(__file__).parent))
from project_core.service_manager import InfrastructureServiceManager, ServiceConfig

def setup_logging():
    """Configuration logging pour orchestrateur"""
    logger = logging.getLogger('WebAppOrchestrator')
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger

def create_backend_config() -> ServiceConfig:
    """Configuration backend Uvicorn avec a2wsgi"""
    # Détection de l'interpréteur Python Conda
    python_exe = "python"
    
    # Chercher l'environnement Conda projet-is
    conda_base = os.path.expanduser("~/miniconda3")
    if not os.path.exists(conda_base):
        conda_base = "C:/Users/MYIA/miniconda3"
    
    projet_is_python = os.path.join(conda_base, "envs", "projet-is", "python.exe")
    if os.path.exists(projet_is_python):
        python_exe = projet_is_python
    
    return ServiceConfig(
        name="backend-uvicorn",
        command=[
            python_exe, 
            "-m", "uvicorn", 
            "argumentation_analysis.services.web_api.app:app",
            "--host", "0.0.0.0",
            "--port", "5003"
        ],
        working_dir=str(Path(__file__).parent),
        port=5003,
        health_check_url="http://localhost:5003/api/status",
        startup_timeout=45,
        max_port_attempts=4
    )

def start_webapp_detached():
    """Démarre la webapp en mode détaché avec gestionnaire de haut niveau"""
    logger = setup_logging()
    logger.info("🚀 Orchestration webapp détachée - DEBUT")
    
    try:
        # Initialisation du gestionnaire de services
        manager = InfrastructureServiceManager(log_level=logging.INFO)
        
        # Configuration du backend
        backend_config = create_backend_config()
        manager.register_service(backend_config)
        
        # Nettoyage préventif
        logger.info("🧹 Nettoyage préventif des processus...")
        cleaned = manager.process_cleanup.stop_backend_processes(["uvicorn", "app.py", "web_api"])
        if cleaned > 0:
            logger.info(f"✅ {cleaned} processus backend nettoyés")
        
        # Démarrage backend avec failover intelligent
        logger.info("🔄 Démarrage backend avec failover...")
        success, actual_port = manager.start_service_with_failover("backend-uvicorn")
        
        if success:
            logger.info(f"✅ Backend démarré avec succès sur port {actual_port}")
            logger.info(f"📡 Health check: http://localhost:{actual_port}/api/status")
            
            # Test de connectivité final
            if manager.test_service_health(f"http://localhost:{actual_port}/api/status"):
                logger.info("✅ Backend répond aux health checks")
                return True, actual_port, manager
            else:
                logger.warning("⚠️  Backend démarré mais health check échoue")
                return True, actual_port, manager
        else:
            logger.error("❌ Échec démarrage backend")
            return False, None, manager
            
    except Exception as e:
        logger.error(f"❌ Erreur orchestration détachée: {e}")
        return False, None, None

def get_service_status():
    """Récupère le statut des services sans bloquer"""
    logger = setup_logging()
    
    try:
        manager = InfrastructureServiceManager()
        
        # Test des ports standards
        ports_to_check = [5003, 5004, 5005, 5006]
        active_services = []
        
        for port in ports_to_check:
            if not manager.port_manager.is_port_free(port):
                if manager.test_service_health(f"http://localhost:{port}/api/status"):
                    active_services.append({
                        'port': port,
                        'status': 'healthy',
                        'url': f"http://localhost:{port}/api/status"
                    })
                else:
                    active_services.append({
                        'port': port, 
                        'status': 'occupied_not_responding',
                        'url': f"http://localhost:{port}"
                    })
        
        return active_services
        
    except Exception as e:
        logger.error(f"Erreur récupération statut: {e}")
        return []

def cleanup_all_services():
    """Nettoie tous les services webapp"""
    logger = setup_logging()
    logger.info("🧹 Nettoyage complet des services webapp...")
    
    try:
        manager = InfrastructureServiceManager()
        manager.process_cleanup.cleanup_all()
        logger.info("✅ Nettoyage terminé")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur nettoyage: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "start":
            success, port, manager = start_webapp_detached()
            if success:
                print(f"✅ Webapp démarrée sur port {port}")
                sys.exit(0)
            else:
                print("❌ Échec démarrage webapp")
                sys.exit(1)
                
        elif command == "status":
            services = get_service_status()
            if services:
                print("📊 Services actifs:")
                for svc in services:
                    print(f"  Port {svc['port']}: {svc['status']} - {svc['url']}")
            else:
                print("📊 Aucun service actif détecté")
                
        elif command == "cleanup":
            if cleanup_all_services():
                print("✅ Nettoyage terminé")
            else:
                print("❌ Erreur nettoyage")
                sys.exit(1)
        else:
            print("Usage: python orchestrate_webapp_detached.py [start|status|cleanup]")
            sys.exit(1)
    else:
        # Démarrage par défaut
        success, port, manager = start_webapp_detached()
        if success:
            print(f"✅ Webapp orchestrée avec succès sur port {port}")
            print(f"📡 Health check: http://localhost:{port}/api/status")
        else:
            print("❌ Échec orchestration webapp")
            sys.exit(1)