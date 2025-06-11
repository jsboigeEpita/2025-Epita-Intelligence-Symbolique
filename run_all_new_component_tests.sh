#!/bin/bash

# =============================================================================
# Script de validation des nouveaux composants (Version Unix/Linux/MacOS)
# =============================================================================
#
# Lance la validation de tous les nouveaux composants du projet.
# Version refactorisée utilisant les modules Python mutualisés.
#
# Usage:
#   ./run_all_new_component_tests.sh [--authentic] [--fast] [--component NAME]
#   ./run_all_new_component_tests.sh --help
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
🧪 VALIDATION COMPLÈTE DES NOUVEAUX COMPOSANTS
==============================================

USAGE:
    ./run_all_new_component_tests.sh [OPTIONS]

OPTIONS:
    --authentic        Mode authentique (composants réels, API, etc.)
    --verbose          Affichage détaillé
    --fast             Tests unitaires rapides seulement
    --component NAME   Exécuter un composant spécifique
    --level LEVEL      Niveau de tests (unit|integration|all)
    --report FILE      Fichier de sortie pour le rapport JSON
    --output FILE      Alias pour --report
    --help             Afficher cette aide

EXEMPLES:
    ./run_all_new_component_tests.sh
    ./run_all_new_component_tests.sh --authentic --verbose
    ./run_all_new_component_tests.sh --fast
    ./run_all_new_component_tests.sh --component "TweetyErrorAnalyzer"
    ./run_all_new_component_tests.sh --report "validation_report.json"

COMPOSANTS DISPONIBLES:
    - TweetyErrorAnalyzer
    - UnifiedConfig
    - FirstOrderLogicAgent
    - AuthenticitySystem
    - UnifiedOrchestrations

DESCRIPTION:
    Lance la validation complète de tous les nouveaux composants du projet
    avec support des modes authentique/mock, tests rapides/complets, et
    génération de rapports détaillés.
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
AUTHENTIC=false
VERBOSE=false
FAST=false
COMPONENT=""
LEVEL="all"
REPORT_FILE=""

# Parsing des arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --authentic)
            AUTHENTIC=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --fast)
            FAST=true
            shift
            ;;
        --component)
            COMPONENT="$2"
            shift 2
            ;;
        --level)
            LEVEL="$2"
            shift 2
            ;;
        --report|--output)
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
case "$LEVEL" in
    unit|integration|all)
        ;;
    *)
        echo "Niveau de test invalide: $LEVEL"
        echo "Niveaux valides: unit, integration, all"
        exit 1
        ;;
esac

# Fonction principale
main() {
    log_message "INFO" "Validation complète des nouveaux composants..."
    
    # Préparation de la commande Python
    local python_command
    read -r -d '' python_command << 'EOF' || true
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'scripts', 'core'))

from test_runner import TestRunner
from validation_engine import ValidationEngine
from common_utils import setup_logging, print_colored

# Configuration du logging
logger = setup_logging(verbose=%s)

try:
    print_colored("🧪 VALIDATION COMPLÈTE DES NOUVEAUX COMPOSANTS", "blue")
    print_colored("=" * 50, "blue")
    print_colored(f"Mode authentique: %s", "white")
    print_colored(f"Mode verbose: %s", "white")
    print_colored(f"Mode rapide: %s", "white")
    component_display = '%s' if '%s' else 'Tous'
    print_colored(f"Composant spécifique: {component_display}", "white")
    print_colored(f"Niveau: %s", "white")
    report_display = '%s' if '%s' else 'Console uniquement'
    print_colored(f"Rapport: {report_display}", "white")
    print_colored("=" * 50, "white")
    
    # Initialisation des modules
    validator = ValidationEngine()
    test_runner = TestRunner()
    
    # Configuration du test
    test_config = {
        'target_script': 'run_all_new_component_tests.py',
        'authentic': %s,
        'verbose': %s,
        'fast': %s,
        'component': '%s' if '%s' else None,
        'level': '%s',
        'report_file': '%s' if '%s' else None
    }
    
    # Construction des arguments
    test_args = []
    if %s:  # authentic
        test_args.append('--authentic')
    if %s:  # verbose
        test_args.append('--verbose')
    if %s:  # fast
        test_args.append('--fast')
    if '%s':  # component
        test_args.extend(['--component', '%s'])
    if '%s' != 'all':  # level
        test_args.extend(['--level', '%s'])
    if '%s':  # report_file
        test_args.extend(['--report', '%s'])
    
    # Vérification des prérequis système
    print_colored("Vérification des prérequis système...", "blue")
    prereq_result = validator.check_system_requirements()
    
    if not prereq_result['valid']:
        print_colored("❌ Prérequis non satisfaits:", "red")
        for issue in prereq_result['issues']:
            print_colored(f"  - {issue}", "red")
        
        # En mode non-authentique, on peut continuer en mode dégradé
        if not %s:  # not authentic
            print_colored("⚠️  Passage en mode dégradé possible", "yellow")
        else:
            print_colored("❌ Impossible de continuer en mode authentique", "red")
            sys.exit(1)
    else:
        print_colored("✅ Prérequis validés", "green")
    
    # Vérifications spécifiques au mode authentique
    if %s:  # authentic
        print_colored("Vérifications mode authentique...", "blue")
        auth_checks = validator.check_authentic_requirements()
        
        if not auth_checks['valid']:
            print_colored("❌ Prérequis mode authentique non satisfaits:", "red")
            for issue in auth_checks['issues']:
                print_colored(f"  - {issue}", "red")
            sys.exit(1)
        else:
            print_colored("✅ Mode authentique validé", "green")
    
    # Vérification de l'existence du script Python cible
    script_path = os.path.join(os.getcwd(), test_config['target_script'])
    if not os.path.exists(script_path):
        print_colored(f"❌ Script Python principal introuvable: {script_path}", "red")
        print_colored("Assurez-vous que run_all_new_component_tests.py est présent.", "red")
        sys.exit(1)
    
    # Exécution des tests
    print_colored("Lancement de la validation des composants...", "blue")
    
    result = test_runner.run_specific_test(
        script_path=test_config['target_script'],
        test_args=test_args,
        working_dir=os.getcwd()
    )
    
    # Rapport final
    print_colored("📊 RAPPORT FINAL", "blue")
    if result['success']:
        print_colored("✅ Tous les tests sont passés avec succès", "green")
        print_colored("🚀 Système prêt pour la production", "green")
        
        if '%s' and os.path.exists('%s'):  # report_file
            print_colored(f"📄 Rapport JSON disponible: %s", "cyan")
        
        print_colored("🎉 MISSION ACCOMPLIE - Validation des nouveaux composants", "green")
        sys.exit(0)
    else:
        print_colored("❌ Des erreurs ont été détectées", "red")
        print_colored("🔍 Vérifiez les logs pour plus de détails", "yellow")
        
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
        "$(echo "$AUTHENTIC" | tr '[:upper:]' '[:lower:]')" \
        "$(echo "$VERBOSE" | tr '[:upper:]' '[:lower:]')" \
        "$(echo "$FAST" | tr '[:upper:]' '[:lower:]')" \
        "$COMPONENT" "$COMPONENT" \
        "$LEVEL" \
        "$REPORT_FILE" "$REPORT_FILE" \
        "$(echo "$AUTHENTIC" | tr '[:upper:]' '[:lower:]')" \
        "$(echo "$VERBOSE" | tr '[:upper:]' '[:lower:]')" \
        "$(echo "$FAST" | tr '[:upper:]' '[:lower:]')" \
        "$COMPONENT" "$COMPONENT" \
        "$LEVEL" "$LEVEL" \
        "$REPORT_FILE" "$REPORT_FILE" \
        "$(echo "$AUTHENTIC" | tr '[:upper:]' '[:lower:]')" \
        "$(echo "$AUTHENTIC" | tr '[:upper:]' '[:lower:]')" \
        "$REPORT_FILE" "$REPORT_FILE" "$REPORT_FILE" \
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
        log_message "INFO" "Mode authentique: $AUTHENTIC"
        log_message "INFO" "Mode rapide: $FAST"
        [[ -n "$COMPONENT" ]] && log_message "INFO" "Composant: $COMPONENT"
        log_message "INFO" "Niveau: $LEVEL"
        [[ -n "$REPORT_FILE" ]] && log_message "INFO" "Rapport: $REPORT_FILE"
    fi
    
    cd "$PROJECT_ROOT"
    echo "$formatted_command" | $python_cmd
    exit_code=$?
    
    if [[ $exit_code -eq 0 ]]; then
        log_message "SUCCESS" "🎉 Validation des nouveaux composants terminée avec succès !"
    else
        log_message "ERROR" "Des erreurs ont été détectées (code: $exit_code)"
    fi
    
    exit $exit_code
}

# Point d'entrée
main "$@"