#!/bin/bash
# Raccourci vers le script d'activation principal pour Bash
SCRIPT_DIR_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
REAL_SCRIPT_PATH="$SCRIPT_DIR_ROOT/scripts/env/activate_project_env.sh"

# Transférer tous les arguments
"$REAL_SCRIPT_PATH" "$@"
exit $?