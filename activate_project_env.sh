#!/bin/bash

# Déterminer le répertoire racine du script
SCRIPT_DIR_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
ENV_FILE=".env"
COMMAND_TO_RUN=""

# Analyser les arguments pour -CommandToRun (simpliste, pour correspondre à la version PS)
if [[ "$1" == "-CommandToRun" ]] && [[ -n "$2" ]]; then
    COMMAND_TO_RUN="$2"
    # Supposer que les arguments restants sont pour la commande
    shift 2
elif [[ "$1" != "" ]] && [[ "$1" != -* ]]; then
    # Si le premier argument n'est pas une option et n'est pas vide, le considérer comme la commande
    COMMAND_TO_RUN="$1"
    shift 1
fi
# Tous les arguments restants ($@) seront pour $COMMAND_TO_RUN

# Récupérer le nom de l'environnement Conda dynamiquement
ENV_NAME_SCRIPT_PATH="$SCRIPT_DIR_ROOT/scripts/get_env_name.py"
CONDA_ENV_NAME_FROM_SCRIPT=""
CONDA_ENV_NAME=""

if [[ -f "$ENV_NAME_SCRIPT_PATH" ]]; then
    # Tenter d'exécuter avec 'python'
    CONDA_ENV_NAME_FROM_SCRIPT=$(python "$ENV_NAME_SCRIPT_PATH" 2>&1)
    EXIT_CODE=$?
    if [[ $EXIT_CODE -ne 0 ]] || [[ "$CONDA_ENV_NAME_FROM_SCRIPT" == *"ERROR_GETTING_ENV_NAME"* ]] || [[ "$CONDA_ENV_NAME_FROM_SCRIPT" == *"CRITICAL_ERROR"* ]]; then
        echo "WARNING: Erreur lors de la récupération du nom de l'environnement Conda depuis '$ENV_NAME_SCRIPT_PATH': $CONDA_ENV_NAME_FROM_SCRIPT" >&2
        echo "WARNING: Utilisation du nom par défaut 'projet-is'." >&2
        CONDA_ENV_NAME="projet-is" # Fallback
    elif [[ "$CONDA_ENV_NAME_FROM_SCRIPT" =~ \ |\'|\" ]]; then # Vérifie les espaces ou guillemets
        echo "WARNING: Le nom de l'environnement récupéré ('$CONDA_ENV_NAME_FROM_SCRIPT') semble invalide. Utilisation du nom par défaut 'projet-is'." >&2
        CONDA_ENV_NAME="projet-is" # Fallback
    else
        CONDA_ENV_NAME=$(echo "$CONDA_ENV_NAME_FROM_SCRIPT" | tr -d '[:space:]') # Enlever les espaces/newlines
    fi
else
    echo "WARNING: Script '$ENV_NAME_SCRIPT_PATH' non trouvé. Utilisation du nom par défaut 'projet-is'." >&2
    CONDA_ENV_NAME="projet-is" # Fallback
fi
echo "[INFO] Nom de l'environnement Conda à utiliser: $CONDA_ENV_NAME"


# --- Chargement des Variables d'Environnement ---
ENV_FILE_PATH="$SCRIPT_DIR_ROOT/$ENV_FILE"
if [[ -f "$ENV_FILE_PATH" ]]; then
    echo "Chargement des variables d'environnement depuis '$ENV_FILE'..."
    # Exporter les variables, en gérant les commentaires et les lignes vides
    # Attention: cette méthode est basique et peut avoir des problèmes avec des valeurs complexes.
    export $(grep -vE "^\s*#|^\s*$" "$ENV_FILE_PATH" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' | xargs)
    
    # Résolution spécifique pour JAVA_HOME si c'est un chemin relatif
    if [[ -n "$JAVA_HOME" ]]; then
        ORIGINAL_JAVA_HOME="$JAVA_HOME"
        if [[ "$JAVA_HOME" == "./"* ]] || [[ "$JAVA_HOME" == ".\\"* ]]; then
            # Convertir en chemin absolu basé sur SCRIPT_DIR_ROOT
            # Supprimer le ./ ou .\ initial
            RELATIVE_PATH_JAVA_HOME="${JAVA_HOME#./}"
            RELATIVE_PATH_JAVA_HOME="${RELATIVE_PATH_JAVA_HOME#. \\}" # Pour .\
            
            # Utiliser realpath pour obtenir le chemin absolu
            # realpath doit être disponible sur le système
            RESOLVED_JAVA_HOME=$(realpath "$SCRIPT_DIR_ROOT/$RELATIVE_PATH_JAVA_HOME" 2>/dev/null)
            
            if [[ -n "$RESOLVED_JAVA_HOME" ]] && [[ -d "$RESOLVED_JAVA_HOME" ]]; then
                export JAVA_HOME="$RESOLVED_JAVA_HOME"
            else
                echo "WARNING: Impossible de résoudre le chemin relatif pour JAVA_HOME: $ORIGINAL_JAVA_HOME depuis $SCRIPT_DIR_ROOT. Utilisation de la valeur brute." >&2
                export JAVA_HOME="$ORIGINAL_JAVA_HOME" # Garder la valeur originale si la résolution échoue
            fi
        fi
        echo "Définition de export JAVA_HOME='$JAVA_HOME'"

        # Configuration spécifique pour PATH si JAVA_HOME est défini
        if [[ -d "$JAVA_HOME" ]]; then
            JDK_BIN_PATH="$JAVA_HOME/bin"
            if [[ -d "$JDK_BIN_PATH" ]]; then
                if [[ ":$PATH:" != *":$JDK_BIN_PATH:"* ]]; then # Vérifie si le chemin n'est pas déjà présent
                    echo "Ajout de '$JDK_BIN_PATH' au début du PATH."
                    export PATH="$JDK_BIN_PATH:$PATH"
                else
                    echo "'$JDK_BIN_PATH' semble déjà être dans le PATH."
                fi
            else
                echo "WARNING: Le répertoire bin du JDK ('$JDK_BIN_PATH') est introuvable. JAVA_HOME ('$JAVA_HOME') pourrait être incorrect." >&2
            fi
        else
             echo "WARNING: JAVA_HOME ('$JAVA_HOME') n'est pas un répertoire valide." >&2
        fi
    else
        echo "WARNING: JAVA_HOME n'est pas défini dans le fichier .env ou n'a pas pu être chargé." >&2
    fi
else
    echo "WARNING: Fichier '$ENV_FILE' ('$ENV_FILE_PATH') introuvable. Certaines variables d'environnement (comme JAVA_HOME) pourraient ne pas être configurées." >&2
fi

# --- Exécution de la commande dans l'environnement Conda ---
if [[ -n "$COMMAND_TO_RUN" ]]; then
    echo ""
    echo "Tentative d'exécution de la commande '$COMMAND_TO_RUN $@' dans l'environnement Conda '$CONDA_ENV_NAME'..."
    echo "Variables d'environnement actuelles (extrait):"
    echo "  JAVA_HOME=$JAVA_HOME"
    echo "  USE_REAL_JPYPE=$USE_REAL_JPYPE"
    echo "  PATH (début)= ${PATH:0:200}..."
    echo "---------------------------------------------------------------------"
    
    # Construire la commande complète avec ses arguments
    FULL_COMMAND_TO_EXECUTE="$COMMAND_TO_RUN"
    if [[ $# -gt 0 ]]; then
        # Échapper les arguments pour la commande
        # Ceci est une tentative basique, des cas plus complexes peuvent nécessiter une gestion plus robuste
        ARGS_ESCAPED=()
        for arg in "$@"; do
            # Si l'argument contient des espaces ou des caractères spéciaux, l'entourer de guillemets simples
            # et échapper les guillemets simples internes.
            if [[ "$arg" =~ \ |\' ]]; then
                ARGS_ESCAPED+=("'"$(echo "$arg" | sed "s/'/'\\\\''/g")"'")
            else
                ARGS_ESCAPED+=("$arg")
            fi
        done
        FULL_COMMAND_TO_EXECUTE="$COMMAND_TO_RUN ${ARGS_ESCAPED[*]}"
    fi

    CONDA_RUN_COMMAND="conda run -n \"$CONDA_ENV_NAME\" --no-capture-output --live-stream $FULL_COMMAND_TO_EXECUTE"
    echo "Exécution via: $CONDA_RUN_COMMAND"
    
    eval "$CONDA_RUN_COMMAND"
    EXIT_CODE=$?

    echo "---------------------------------------------------------------------"
    echo "Commande '$COMMAND_TO_RUN $@' terminée avec le code de sortie: $EXIT_CODE"
    exit $EXIT_CODE
else
    echo ""
    echo "---------------------------------------------------------------------"
    echo "Variables d'environnement du projet chargées (si .env trouvé)."
    echo "Aucune commande spécifiée à exécuter."
    echo ""
    echo "Pour activer manuellement l'environnement Conda '$CONDA_ENV_NAME' dans votre session actuelle :"
    echo "    conda activate \"$CONDA_ENV_NAME\""
    echo ""
    echo "Ou pour exécuter une commande spécifique dans l'environnement :"
    echo "    ./activate_project_env.sh \"votre_commande --arg1\""
    echo "    (Assurez-vous que Conda est initialisé pour votre shell: conda init bash ou conda init zsh)"
    echo "---------------------------------------------------------------------"
fi