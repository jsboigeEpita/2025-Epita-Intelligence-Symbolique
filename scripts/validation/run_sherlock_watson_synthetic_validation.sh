#!/bin/bash

# =============================================================================
# Script de validation Sherlock/Watson avec données synthétiques (Unix/Linux/MacOS)
# =============================================================================
#
# Lance la validation complète du système Sherlock/Watson en utilisant des datasets 
# synthétiques spécialement conçus pour détecter les mocks vs raisonnement réel.
# Version refactorisée utilisant les modules Python mutualisés.
#
# Usage:
#   ./run_sherlock_watson_synthetic_validation.sh [--mode MODE] [--report] [--verbose]
#   ./run_sherlock_watson_synthetic_validation.sh --help
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
🔍 VALIDATION SHERLOCK/WATSON - DONNÉES SYNTHÉTIQUES
===================================================

USAGE:
    ./run_sherlock_watson_synthetic_validation.sh [OPTIONS]

OPTIONS:
    --mode MODE        Mode de test (complete|quick|edge_cases|mock_detection)
    --report           Génère un rapport HTML en plus du JSON
    --verbose          Mode verbeux
    --help             Afficher cette aide

EXEMPLES:
    ./run_sherlock_watson_synthetic_validation.sh
    ./run_sherlock_watson_synthetic_validation.sh --mode quick --verbose
    ./run_sherlock_watson_synthetic_validation.sh --mode complete --report
    ./run_sherlock_watson_synthetic_validation.sh --mode mock_detection

MODES DE TEST:
    complete        Mode complet - Tous les tests synthétiques
    quick           Mode rapide - Tests essentiels uniquement
    edge_cases      Mode edge cases - Tests de robustesse uniquement
    mock_detection  Mode détection mocks - Focus sur l'identification des simulations

DESCRIPTION:
    Lance la validation complète du système Sherlock/Watson en utilisant des datasets
    synthétiques spécialement conçus pour détecter les mocks vs raisonnement réel.
    Analyse la cohérence logique, la qualité des réponses et la robustesse du système.
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
TEST_MODE="complete"
GENERATE_REPORT=false
VERBOSE=false

# Parsing des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            TEST_MODE="$2"
            shift 2
            ;;
        --report)
            GENERATE_REPORT=true
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

# Validation des arguments
case "$TEST_MODE" in
    complete|quick|edge_cases|mock_detection)
        ;;
    *)
        echo "Mode de test invalide: $TEST_MODE"
        echo "Modes valides: complete, quick, edge_cases, mock_detection"
        exit 1
        ;;
esac

# Fonction principale
main() {
    log_message "INFO" "Validation système Sherlock/Watson avec données synthétiques..."
    
    # Préparation de la commande Python
    local python_command
    read -r -d '' python_command << 'EOF' || true
import sys
import os
import glob
sys.path.append(os.path.join(os.getcwd(), 'scripts', 'core'))

from test_runner import TestRunner
from validation_engine import ValidationEngine
from common_utils import setup_logging, print_colored

# Configuration du logging
logger = setup_logging(verbose=%s)

try:
    print_colored("🔍 VALIDATION SHERLOCK/WATSON - DONNÉES SYNTHÉTIQUES", "blue")
    print_colored("=" * 60, "blue")
    print_colored(f"Mode de test: %s", "white")
    print_colored(f"Génération rapport HTML: %s", "white")
    print_colored(f"Mode verbeux: %s", "white")
    print_colored("=" * 60, "white")
    
    # Initialisation des modules
    validator = ValidationEngine()
    test_runner = TestRunner()
    
    # Configuration du mode de test
    test_config = {
        'target_script': 'test_sherlock_watson_synthetic_validation.py',
        'test_mode': '%s',
        'verbose': %s,
        'generate_html_report': %s
    }
    
    # Arguments spécifiques selon le mode
    test_args = []
    if '%s' == 'quick':
        test_args.append('--quick-mode')
        print_colored("Mode rapide: Tests essentiels uniquement", "yellow")
    elif '%s' == 'edge_cases':
        test_args.append('--edge-cases-only')
        print_colored("Mode edge cases: Tests de robustesse uniquement", "yellow")
    elif '%s' == 'mock_detection':
        test_args.append('--mock-detection-focus')
        print_colored("Mode détection mocks: Focus sur l'identification des simulations", "yellow")
    else:
        print_colored("Mode complet: Tous les tests synthétiques", "yellow")
        
    if %s:  # verbose
        test_args.append('--verbose')
    
    # Vérification des prérequis
    print_colored("Vérification des prérequis système...", "blue")
    prereq_result = validator.check_system_requirements()
    
    if not prereq_result['valid']:
        print_colored("❌ Prérequis non satisfaits:", "red")
        for issue in prereq_result['issues']:
            print_colored(f"  - {issue}", "red")
        sys.exit(1)
    
    print_colored("✅ Prérequis validés", "green")
    
    # Exécution de la validation
    print_colored("Lancement de la validation synthétique...", "blue")
    
    result = test_runner.run_specific_test(
        script_path=test_config['target_script'],
        test_args=test_args,
        working_dir=os.getcwd()
    )
    
    if result['success']:
        print_colored("✅ Validation terminée avec succès", "green")
        
        # Génération du rapport HTML si demandé
        if %s:  # generate_html_report
            print_colored("Génération du rapport HTML...", "blue")
            
            # Recherche du rapport JSON le plus récent
            json_reports = glob.glob('rapport_validation_sherlock_watson_synthetic_*.json')
            if json_reports:
                latest_report = max(json_reports, key=os.path.getmtime)
                validator.generate_html_report(latest_report)
                print_colored("📄 Rapport HTML généré", "green")
            else:
                print_colored("⚠️  Aucun rapport JSON trouvé pour la conversion HTML", "yellow")
        
        print_colored("🎉 MISSION ACCOMPLIE - Validation système Sherlock/Watson", "green")
        sys.exit(0)
    else:
        print_colored("❌ Échec de la validation", "red")
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
        "$TEST_MODE" \
        "$(echo "$GENERATE_REPORT" | tr '[:upper:]' '[:lower:]')" \
        "$(echo "$VERBOSE" | tr '[:upper:]' '[:lower:]')" \
        "$(echo "$GENERATE_REPORT" | tr '[:upper:]' '[:lower:]')" \
        "$TEST_MODE" \
        "$TEST_MODE" \
        "$(echo "$VERBOSE" | tr '[:upper:]' '[:lower:]')" \
        "$(echo "$GENERATE_REPORT" | tr '[:upper:]' '[:lower:]')" \
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
        log_message "INFO" "Mode de test: $TEST_MODE"
        log_message "INFO" "Génération rapport HTML: $GENERATE_REPORT"
    fi
    
    cd "$PROJECT_ROOT"
    echo "$formatted_command" | $python_cmd
    exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log_message "SUCCESS" "🎉 Validation Sherlock/Watson terminée avec succès !"
    else
        log_message "ERROR" "Échec de la validation (code: $exit_code)"
    fi
    
    exit $exit_code
}

# Point d'entrée
main "$@"