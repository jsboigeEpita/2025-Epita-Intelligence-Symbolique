#!/bin/bash

# =============================================================================
# Script de configuration de l'environnement projet (Version Unix/Linux/MacOS)
# =============================================================================
#
# Configuration complète de l'environnement conda/venv du projet
# Version refactorisée utilisant les modules Python mutualisés
#
# Usage:
#   ./setup_project_env.sh [--force] [--verbose]
#   ./setup_project_env.sh --help
#
# Auteur: Intelligence Symbolique EPITA
# Date: 09/06/2025 - Version refactorisée

set -euo pipefail  # Mode strict bash

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Fonction d'aide
show_help() {
    cat << EOF
⚙️  CONFIGURATION ENVIRONNEMENT PROJET
====================================

USAGE:
    ./setup_project_env.sh [OPTIONS]

OPTIONS:
    --force            Force la recréation de l'environnement
    --verbose          Mode verbeux
    --help             Afficher cette aide

EXEMPLES:
    ./setup_project_env.sh
    ./setup_project_env.sh --force --verbose

DESCRIPTION:
    Configure automatiquement l'environnement conda/venv du projet avec
    toutes les dépendances nécessaires. Installe les packages Python,
    configure les variables d'environnement et vérifie l'installation.
EOF
}

# Fonction de logging
log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case "$level" in
        "INFO")  echo -e "${BLUE}[$timestamp] [INFO] $message${NC}" ;;
        "SUCCESS") echo -e "${GREEN}[$timestamp] [SUCCESS] $message${NC}" ;;
        "WARNING") echo -e "${YELLOW}[$timestamp] [WARNING] $message${NC}" ;;
        "ERROR") echo -e "${RED}[$timestamp] [ERROR] $message${NC}" ;;
        *) echo "[$timestamp] [$level] $message" ;;
    esac
}

# Variables par défaut
FORCE_RECREATE=false
VERBOSE=false

# Parsing des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE_RECREATE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "Option inconnue: $1"
            show_help
            exit 1
            ;;
    esac
done

# Fonction principale
main() {
    log_message "INFO" "Configuration de l'environnement projet..."
    
    # Préparation de la commande Python
    local python_command
    read -r -d '' python_command << 'EOF' || true
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'scripts', 'core'))

from project_setup import ProjectSetup
from environment_manager import EnvironmentManager
from common_utils import setup_logging, print_colored

# Configuration du logging
logger = setup_logging(verbose=%s)

try:
    print_colored("⚙️  CONFIGURATION ENVIRONNEMENT PROJET", "blue")
    print_colored("=" * 42, "blue")
    print_colored(f"Force recréation: %s", "white")
    print_colored(f"Mode verbeux: %s", "white")
    print_colored("=" * 42, "white")
    
    # Initialisation des gestionnaires
    project_setup = ProjectSetup()
    env_manager = EnvironmentManager()
    
    # Configuration du projet
    print_colored("🔧 Configuration du projet...", "blue")
    setup_result = project_setup.setup_complete_environment(
        force_recreate=%s,
        verbose=%s
    )
    
    if setup_result['success']:
        print_colored("✅ Configuration terminée avec succès", "green")
        
        # Vérification de l'environnement
        print_colored("🔍 Vérification de l'environnement...", "blue")
        verify_result = env_manager.verify_environment()
        
        if verify_result['valid']:
            print_colored("✅ Environnement validé", "green")
            
            # Affichage des informations
            env_info = env_manager.get_environment_info()
            print_colored("📋 Informations sur l'environnement:", "cyan")
            print_colored(f"  Python: {env_info.get('python_version', 'N/A')}", "white")
            print_colored(f"  Environnement: {env_info.get('env_name', 'N/A')}", "white")
            print_colored(f"  Chemin: {env_info.get('env_path', 'N/A')}", "white")
            print_colored(f"  Packages installés: {len(env_info.get('packages', []))}", "white")
            
            print_colored("🎉 MISSION ACCOMPLIE - Environnement prêt !", "green")
            sys.exit(0)
        else:
            print_colored("❌ Erreurs de validation détectées", "red")
            for issue in verify_result.get('issues', []):
                print_colored(f"  - {issue}", "red")
            sys.exit(1)
    else:
        print_colored("❌ Échec de la configuration", "red")
        if 'error' in setup_result:
            print_colored(f"Erreur: {setup_result['error']}", "red")
        sys.exit(1)
        
except Exception as e:
    print_colored(f"❌ Erreur critique: {str(e)}", "red")
    if %s:  # verbose
        import traceback
        print_colored(f"Stack trace: {traceback.format_exc()}", "red")
    sys.exit(2)
EOF

    # Formatage de la commande Python avec les variables
    local formatted_command
    formatted_command=$(printf "$python_command" \
        "$(echo "$VERBOSE" | tr '[:upper:]' '[:lower:]')" \
        "$(echo "$FORCE_RECREATE" | tr '[:upper:]' '[:lower:]')" \
        "$(echo "$FORCE_RECREATE" | tr '[:upper:]' '[:lower:]')" \
        "$(echo "$VERBOSE" | tr '[:upper:]' '[:lower:]')" \
        "$(echo "$VERBOSE" | tr '[:upper:]' '[:lower:]')")
    
    # Vérification de Python
    if ! command -v python3 >/dev/null 2>&1 && ! command -v python >/dev/null 2>&1; then
        log_message "ERROR" "Python non trouvé. Veuillez installer Python."
        exit 1
    fi
    
    # Déterminer la commande Python à utiliser
    local python_cmd
    if command -v python3 >/dev/null 2>&1; then
        python_cmd="python3"
    else
        python_cmd="python"
    fi
    
    # Exécution
    if [[ "$VERBOSE" == "true" ]]; then
        log_message "INFO" "Utilisation de: $python_cmd"
        log_message "INFO" "Répertoire de travail: $PROJECT_ROOT"
        log_message "INFO" "Force recréation: $FORCE_RECREATE"
    fi
    
    cd "$PROJECT_ROOT"
    echo "$formatted_command" | $python_cmd
    exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log_message "SUCCESS" "🎉 Configuration terminée avec succès !"
    else
        log_message "ERROR" "Échec de la configuration (code: $exit_code)"
    fi
    
    exit $exit_code
}

# Point d'entrée
main "$@"