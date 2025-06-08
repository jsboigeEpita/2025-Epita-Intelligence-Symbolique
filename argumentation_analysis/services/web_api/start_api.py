#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de démarrage pour l'API Web d'analyse argumentative.

Ce script facilite le lancement de l'API avec différentes configurations
et fournit des informations utiles pour les étudiants.
"""

import os
import sys
import argparse
import logging
from pathlib import Path
import io

# Force UTF-8 encoding for stdout and stderr
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Ajouter le répertoire racine au chemin Python
current_dir = Path(__file__).parent
root_dir = current_dir.parent.parent
if str(root_dir) not in sys.path:
    sys.path.append(str(root_dir))

def setup_logging(debug: bool = False) -> None:
    """Configure le système de logging de base pour le script."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%H:%M:%S'
    )

def check_dependencies():
    """Vérifie si les dépendances Python requises pour l'API sont installées."""
    required_packages = ['flask', 'flask_cors', 'pydantic']
    missing = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"❌ Dépendances manquantes: {', '.join(missing)}")
        print("📦 Installez-les avec: pip install -r requirements.txt")
        return False
    
    print("[OK] Toutes les dépendances sont installées")
    return True

def check_port(port: int):
    """Vérifie si un port TCP donné est disponible sur localhost."""
    import socket
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
        return True
    except OSError:
        return False

def print_startup_info(port: int, debug: bool):
    """Affiche les informations de démarrage de l'API dans la console."""
    print("\n" + "="*60)
    print("🚀 API Web d'Analyse Argumentative")
    print("="*60)
    print(f"📍 URL locale: http://localhost:{port}")
    print(f"🔧 Mode debug: {'Activé' if debug else 'Désactivé'}")
    print(f"📚 Documentation: http://localhost:{port}/api/endpoints")
    print(f"❤️  Health check: http://localhost:{port}/api/health")
    print("\n📋 Endpoints disponibles:")
    print("   • POST /api/analyze     - Analyse complète de texte")
    print("   • POST /api/validate    - Validation d'argument")
    print("   • POST /api/fallacies   - Détection de sophismes")
    print("   • POST /api/framework   - Framework de Dung")
    print("   • GET  /api/health      - État de l'API")
    print("   • GET  /api/endpoints   - Liste des endpoints")
    print("\n💡 Conseils:")
    print("   • Utilisez Postman ou curl pour tester l'API")
    print("   • Consultez le README.md pour des exemples")
    print("   • Activez CORS pour les appels depuis React")
    print("="*60)

def main():
    """Fonction principale."""
    # Configuration de base du logging pour attraper les erreurs précoces
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    logger = logging.getLogger("StartAPI.bootstrap")

    try:
        parser = argparse.ArgumentParser(
            description="Démarre l'API Web d'analyse argumentative",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Exemples d'utilisation:
  python start_api.py                    # Démarrage standard (port 5000)
  python start_api.py --port 8080        # Port personnalisé
  python start_api.py --debug             # Mode debug activé
  python start_api.py --host 0.0.0.0     # Accessible depuis l'extérieur
            """
        )
        
        parser.add_argument(
            '--port', '-p',
            type=int,
            default=5000,
            help='Port du serveur (défaut: 5000)'
        )
        
        parser.add_argument(
            '--host',
            default='127.0.0.1',
            help='Adresse d\'écoute (défaut: 127.0.0.1)'
        )
        
        parser.add_argument(
            '--debug', '-d',
            action='store_true',
            help='Active le mode debug'
        )
        
        parser.add_argument(
            '--no-check',
            action='store_true',
            help='Ignore les vérifications de dépendances'
        )
        
        parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Mode silencieux (moins de logs)'
        )
        
        args = parser.parse_args()
        
        # Reconfiguration du logging avec les paramètres de l'utilisateur
        setup_logging(args.debug and not args.quiet)
        logger = logging.getLogger("StartAPI") # Logger principal
        
        # Vérifications préliminaires
        if not args.no_check:
            logger.info("🔍 Vérification des dépendances...")
            if not check_dependencies():
                logger.error("Dépendances manquantes. Arrêt.")
                sys.exit(1)
        
        if not check_port(args.port):
            logger.error(f"Le port {args.port} est déjà utilisé. Arrêt.")
            sys.exit(1)
        
        os.environ['PORT'] = str(args.port)
        os.environ['DEBUG'] = str(args.debug)
        
        if not args.quiet:
            print_startup_info(args.port, args.debug)
        
        from argumentation_analysis.services.web_api.app import app
        
        logger.info(f"Démarrage de l'API sur {args.host}:{args.port}")
        
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug,
            use_reloader=args.debug,
            threaded=True
        )
            
    except KeyboardInterrupt:
        logger.info("Arrêt de l'API demandé par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erreur fatale lors de l'initialisation: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()