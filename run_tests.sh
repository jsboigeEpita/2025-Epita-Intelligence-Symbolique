#!/bin/bash

# =============================================================================
# Script d'exécution des tests (Version Unix/Linux/MacOS)
# =============================================================================
#
# Orchestrateur pour l'exécution de tous les types de tests du projet
# Version refactorisée utilisant les modules Python mutualisés
#
# Usage:
#   ./run_tests.sh [--type TYPE] [--component COMPONENT] [--verbose]
#   ./run_tests.sh --help
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
🧪 ORCHESTRATEUR DE TESTS
========================

USAGE:
    ./run_tests.sh [OPTIONS]

OPTIONS:
    --type TYPE        Type de tests (unit|integration|validation|all)
    --component COMP   Composant spécifique à tester
    --pattern PATTERN  Pattern de fichiers de test
    --verbose          Mode verbeux
    --report FILE      Fichier de rapport de sortie
    --help             Afficher cette aide

EXEMPLES:
    ./run_tests.sh                                    # Tous les tests
    ./run_tests.sh --type unit --verbose              # Tests unitaires uniquement
    ./run_tests.sh --component "TweetyErrorAnalyzer"  # Tests d'un composant
    ./run_tests.sh --pattern "test_*_simple.py"      # Tests avec pattern
    ./run_tests.sh --report "test_report.json"       # Avec rapport

TYPES DE TESTS:
    unit         Tests unitaires rapides
    integration  Tests d'intégration
    validation   Tests de validation système
    all          Tous les types de tests
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
TEST_TYPE="all"
COMPONENT=""
PATTERN=""
VERBOSE=false
REPORT_FILE=""

# Parsing des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --type)
            TEST_TYPE="$2"
            shift 2
            ;;
        --component)
            COMPONENT="$2"
            shift 2
            ;;
        --pattern)
            PATTERN="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --report)
            REPORT_FILE="$2"
            shift 2
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

# Validation des arguments
case "$TEST_TYPE" in
    unit|integration|validation|all)
        ;;
    *)
        echo "Type de test invalide: $TEST_TYPE"
        echo "Types valides: unit, integration, validation, all"
        exit 1
        ;;
esac

# Fonction principale
main() {
    log_message "INFO" "Lancement de l'orchestrateur de tests..."
    
    # Préparation de la commande Python
    local python_command
    read -r -d '' python_command << 'EOF' || true
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'scripts', 'core'))

from test_runner import TestRunner
from common_utils import setup_logging, print_colored

# Configuration du logging
logger = setup_logging(verbose=%s)

try:
    print_colored("🧪 ORCHESTRATEUR DE TESTS", "blue")
    print_colored("=" * 30, "blue")
    print_colored(f"Type de tests: %s", "white")
    print_colored(f"Composant: %s", "white")
    print_colored(f"Pattern: %s", "white")
    print_colored(f"Mode verbeux: %s", "white")
    print_colored(f"Rapport: %s", "white")
    print_colored("=" * 30, "white")
    
    # Initialisation du runner de tests
    test_runner = TestRunner()
    
    # Configuration des tests
    test_config = {
        'test_type': '%s',
        'component': '%s' if '%s' else None,
        'pattern': '%s' if '%s' else None,
        'verbose': %s,
        'report_file': '%s' if '%s' else None
    }
    
    # Exécution des tests selon le type
    print_colored("🚀 Lancement des tests...", "blue")
    
    if test_config['test_type'] == 'all':
        # Exécution de tous les types de tests
        result = test_runner.run_all_tests(
            component=test_config['component'],
            pattern=test_config['pattern'],
            verbose=test_config['verbose'],
            report_file=test_config['report_file']
        )
    else:
        # Exécution d'un type spécifique
        result = test_runner.run_tests_by_type(
            test_type=test_config['test_type'],
            component=test_config['component'],
            pattern=test_config['pattern'],
            verbose=test_config['verbose'],
            report_file=test_config['report_file']
        )
    
    # Affichage des résultats
    print_colored("📊 RÉSULTATS DES TESTS", "blue")
    if result['success']:
        print_colored("✅ Tous les tests sont passés avec succès", "green")
        print_colored(f"📋 Tests exécutés: {result.get('total_tests', 'N/A')}", "white")
        print_colored(f"✅ Succès: {result.get('passed_tests', 'N/A')}", "green")
        print_colored(f"❌ Échecs: {result.get('failed_tests', 0)}", "red" if result.get('failed_tests', 0) > 0 else "white")
        print_colored(f"⏱️  Durée: {result.get('duration', 'N/A')}s", "white")
        
        if test_config['report_file'] and os.path.exists(test_config['report_file']):
            print_colored(f"📄 Rapport généré: {test_config['report_file']}", "cyan")
        
        print_colored("🎉 MISSION ACCOMPLIE - Tests terminés !", "green")
        sys.exit(0)
    else:
        print_colored("❌ Des tests ont échoué", "red")
        if 'error' in result:
            print_colored(f"Erreur: {result['error']}", "red")
        
        # Affichage des détails même en cas d'échec
        if 'total_tests' in result:
            print_colored(f"📋 Tests exécutés: {result['total_tests']}", "white")
            print_colored(f"✅ Succès: {result.get('passed_tests', 0)}", "green")
            print_colored(f"❌ Échecs: {result.get('failed_tests', 0)}", "red")
        
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
        "$TEST_TYPE" \
        "$COMPONENT" "$COMPONENT" \
        "$PATTERN" "$PATTERN" \
        "$(echo "$VERBOSE" | tr '[:upper:]' '[:lower:]')" \
        "$REPORT_FILE" "$REPORT_FILE" \
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
        log_message "INFO" "Type de tests: $TEST_TYPE"
        [[ -n "$COMPONENT" ]] && log_message "INFO" "Composant: $COMPONENT"
        [[ -n "$PATTERN" ]] && log_message "INFO" "Pattern: $PATTERN"
        [[ -n "$REPORT_FILE" ]] && log_message "INFO" "Rapport: $REPORT_FILE"
    fi
    
    cd "$PROJECT_ROOT"
    echo "$formatted_command" | $python_cmd
    exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log_message "SUCCESS" "🎉 Tests terminés avec succès !"
    else
        log_message "ERROR" "Des tests ont échoué (code: $exit_code)"
    fi
    
    exit $exit_code
}

# Point d'entrée
main "$@"