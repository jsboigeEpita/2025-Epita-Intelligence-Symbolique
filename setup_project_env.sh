#!/bin/bash

# Script wrapper Bash pour appeler le script d'installation Python principal.
# Gère la traduction des arguments de style GNU en arguments pour le script Python.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Le script setup_project_env.sh est à la racine du projet.
PROJECT_ROOT="$SCRIPT_DIR"

PYTHON_SCRIPT_PATH="$PROJECT_ROOT/scripts/setup_core/main_setup.py"
PYTHON_ARGS=()

# Initialisation des variables pour les options
FORCE_REINSTALL_ALL=0
FORCE_REINSTALL_TOOLS=0
FORCE_REINSTALL_ENV=0
INTERACTIVE=0
SKIP_TOOLS=0
SKIP_ENV=0
SKIP_CLEANUP=0
SKIP_PIP_INSTALL=0

# Parsing des arguments
# Utilisation d'une boucle simple pour la compatibilité et la lisibilité.
# Pour une gestion plus complexe, getopt pourrait être envisagé.
TEMP_ARGS=()
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --force-reinstall-all)
            FORCE_REINSTALL_ALL=1
            shift # L'argument a été traité
            ;;
        --force-reinstall-tools)
            FORCE_REINSTALL_TOOLS=1
            shift # L'argument a été traité
            ;;
        --force-reinstall-env)
            FORCE_REINSTALL_ENV=1
            shift # L'argument a été traité
            ;;
        --interactive)
            INTERACTIVE=1
            shift # L'argument a été traité
            ;;
        --skip-tools)
            SKIP_TOOLS=1
            shift # L'argument a été traité
            ;;
        --skip-env)
            SKIP_ENV=1
            shift # L'argument a été traité
            ;;
        --skip-cleanup)
            SKIP_CLEANUP=1
            shift # L'argument a été traité
            ;;
        --skip-pip-install)
            SKIP_PIP_INSTALL=1
            shift # L'argument a été traité
            ;;
        *)
            # Conserver les arguments inconnus pour les passer tels quels (si nécessaire)
            # ou afficher une erreur et quitter si seules les options définies sont autorisées.
            # Pour ce wrapper, nous allons supposer que le script Python gère les arguments inconnus.
            # Cependant, la spécification indique de traduire les arguments connus.
            # Les arguments non reconnus par ce wrapper ne seront pas passés au script python.
            echo "Option inconnue ou argument non pris en charge par le wrapper: $1" >&2
            # Pour une gestion stricte, décommenter la ligne suivante :
            # exit 1
            shift # Passer à l'argument suivant
            ;;
    esac
done

# Construction des arguments pour le script Python
if [[ "$FORCE_REINSTALL_ALL" -eq 1 ]]; then
    PYTHON_ARGS+=("--force-reinstall-tools")
    PYTHON_ARGS+=("--force-reinstall-env")
    # --force-reinstall-all est implicitement géré par les deux options ci-dessus
    # pour main_setup.py, mais on peut l'ajouter si main_setup.py le gère spécifiquement.
    # PYTHON_ARGS+=("--force-reinstall-all")
else
    if [[ "$FORCE_REINSTALL_TOOLS" -eq 1 ]]; then PYTHON_ARGS+=("--force-reinstall-tools"); fi
    if [[ "$FORCE_REINSTALL_ENV" -eq 1 ]]; then PYTHON_ARGS+=("--force-reinstall-env"); fi
fi

if [[ "$INTERACTIVE" -eq 1 ]]; then PYTHON_ARGS+=("--interactive"); fi
if [[ "$SKIP_TOOLS" -eq 1 ]]; then PYTHON_ARGS+=("--skip-tools"); fi
if [[ "$SKIP_ENV" -eq 1 ]]; then PYTHON_ARGS+=("--skip-env"); fi
if [[ "$SKIP_CLEANUP" -eq 1 ]]; then PYTHON_ARGS+=("--skip-cleanup"); fi
if [[ "$SKIP_PIP_INSTALL" -eq 1 ]]; then PYTHON_ARGS+=("--skip-pip-install"); fi

# Vérification de l'existence du script Python
if [ ! -f "$PYTHON_SCRIPT_PATH" ]; then
    echo "Erreur: Le script d'orchestration Python '$PYTHON_SCRIPT_PATH' est introuvable." >&2
    exit 1
fi

# Détection de l'exécutable Python
PYTHON_EXECUTABLE=$(command -v python3 || command -v python)

if [ -z "$PYTHON_EXECUTABLE" ]; then
    echo "Erreur: Python (python3 ou python) n'est pas trouvé dans le PATH." >&2
    echo "Veuillez vous assurer que Python est installé et accessible." >&2
    exit 1
fi

echo "Détection de Python : $PYTHON_EXECUTABLE"
echo "Lancement du script d'installation Python : $PYTHON_SCRIPT_PATH"
if [ ${#PYTHON_ARGS[@]} -gt 0 ]; then
    echo "Avec les arguments: ${PYTHON_ARGS[*]}"
else
    echo "Sans arguments spécifiques pour le script Python."
fi

# Exécution du script Python avec les arguments traduits
"$PYTHON_EXECUTABLE" "$PYTHON_SCRIPT_PATH" "${PYTHON_ARGS[@]}"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "Avertissement: Le script d'installation Python ($PYTHON_SCRIPT_PATH) a terminé avec le code d'erreur: $EXIT_CODE." >&2
else
    echo "Le script d'installation Python ($PYTHON_SCRIPT_PATH) a terminé avec succès."
fi

exit $EXIT_CODE