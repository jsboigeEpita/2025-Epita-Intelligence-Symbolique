#!/bin/bash

# =============================================================================
# Script d'activation de l'environnement projet (Version Unix/Linux/MacOS)
# =============================================================================
#
# Activation de l'environnement conda/venv du projet avec gestion des erreurs
# Version refactorisée utilisant les modules Python mutualisés
#
# Usage:
#   ./activate_project_env.sh [--command "commande à exécuter"]
#   ./activate_project_env.sh --help
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
NC='\033[0m' # No Color

# Fonction d'aide
show_help() {
    cat << EOF
🚀 ACTIVATION ENVIRONNEMENT PROJET
==================================

USAGE:
    ./activate_project_env.sh [OPTIONS]

OPTIONS:
    --command "cmd"     Exécuter une commande dans l'environnement activé
    --verbose          Mode verbeux
    --help             Afficher cette aide

EXEMPLES:
    ./activate_project_env.sh
    ./activate_project_env.sh --command "python --version"
    ./activate_project_env.sh --command "python run_tests.py" --verbose

DESCRIPTION:
    Active l'environnement conda/venv du projet et permet d'exécuter
    des commandes dans cet environnement ou de lancer un shell interactif.
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
COMMAND_TO_RUN=""
VERBOSE=false

# Parsing des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --command)
            COMMAND_TO_RUN="$2"
            shift 2
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
    log_message "INFO" "Activation de l'environnement projet..."
    
    # Préparation de la commande Python
    local python_command
    read -r -d '' python_command << 'EOF' || true
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'scripts', 'core'))

from environment_manager import EnvironmentManager
from common_utils import setup_logging, print_colored

# Configuration du logging
logger = setup_logging(verbose=%s)

try:
    # Initialisation du gestionnaire d'environnement
    env_manager = EnvironmentManager()
    
    print_colored("🚀 ACTIVATION ENVIRONNEMENT PROJET", "blue")
    print_colored("=" * 40, "blue")
    
    # Activation de l'environnement
    print_colored("Activation de l'environnement...", "blue")
    result = env_manager.activate_environment()
    
    if result['success']:
        print_colored("✅ Environnement activé avec succès", "green")
        
        # Affichage des informations sur l'environnement
        env_info = env_manager.get_environment_info()
        print_colored(f"Python: {env_info.get('python_version', 'N/A')}", "white")
        print_colored(f"Environnement: {env_info.get('env_name', 'N/A')}", "white")
        print_colored(f"Chemin: {env_info.get('env_path', 'N/A')}", "white")
        
        # Exécution de la commande si spécifiée
        command = "%s"
        if command:
            print_colored(f"Exécution de: {command}", "blue")
            exit_code = env_manager.run_command_in_environment(command)
            sys.exit(exit_code)
        else:
            print_colored("🎯 Environnement prêt ! Lancez vos commandes Python.", "green")
            sys.exit(0)
    else:
        print_colored("❌ Échec de l'activation de l'environnement", "red")
        if 'error' in result:
            print_colored(f"Erreur: {result['error']}", "red")
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
        "$COMMAND_TO_RUN" \
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
    fi
    
    cd "$PROJECT_ROOT"
    echo "$formatted_command" | $python_cmd
    exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        if [[ -z "$COMMAND_TO_RUN" ]]; then
            log_message "SUCCESS" "🎉 Environnement activé ! Utilisez 'python' pour vos commandes."
        fi
    else
        log_message "ERROR" "Échec de l'activation (code: $exit_code)"
    fi
    
    exit $exit_code
}

# Point d'entrée
main "$@"