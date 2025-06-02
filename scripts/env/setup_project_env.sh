#!/bin/bash

# Script d'installation de l'environnement du projet pour Bash

# --- Paramètres ---
FORCE_REINSTALL=false
INTERACTIVE_MODE=false

# Parsing simple des arguments
for arg in "$@"
do
    case $arg in
        -ForceReinstall|--ForceReinstall)
        FORCE_REINSTALL=true
        shift # Remove argument from processing
        ;;
        -InteractiveMode|--InteractiveMode)
        INTERACTIVE_MODE=true
        shift # Remove argument from processing
        ;;
        # Ignorer -Python310Path et -NonInteractiveLegacy pour l'instant
    esac
done

echo "Mode ForceReinstall: $FORCE_REINSTALL"
echo "Mode InteractiveMode: $INTERACTIVE_MODE"

# --- Configuration ---
CONDA_ENV_NAME="projet-is"
ENVIRONMENT_YML_FILE="environment.yml"

# Déterminer la racine du script et du projet
# Ce script est DANS scripts/env.
SCRIPT_DIR_SETUP_ENV_SH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(cd "$SCRIPT_DIR_SETUP_ENV_SH/../.." &> /dev/null && pwd)"
echo "Racine du projet détectée : $PROJECT_ROOT"

LIBS_DIR="$PROJECT_ROOT/libs"
ENV_FILE_PATH="$PROJECT_ROOT/.env"
ENV_TEMPLATE_FILE_PATH="$PROJECT_ROOT/.env.template"
ENVIRONMENT_YML_FILE_PATH="$PROJECT_ROOT/$ENVIRONMENT_YML_FILE"

# Configuration JDK
JDK_DIR_NAME_ONLY="portable_jdk"
JDK_DIR="$LIBS_DIR/$JDK_DIR_NAME_ONLY"
TWEETY_LIBS_DIR="$LIBS_DIR/tweety" # Nouvel emplacement pour les JARs Tweety
TWEETY_NATIVE_LIBS_DIR="$TWEETY_LIBS_DIR/native" # Pour les libs natives de Tweety

# Pourrait être différent pour Linux/Mac, mais gardons Windows pour l'instant pour la portabilité du JDK fourni
JDK_URL="https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_windows_hotspot_17.0.11_9.zip"
# Sur Linux/Mac, on pourrait utiliser sdkman ou télécharger une version tar.gz appropriée.
# Pour l'instant, on suppose que le ZIP Windows pourrait être utilisé via Wine ou que l'utilisateur gère son JDK.
# Ou mieux, on adapte l'URL pour Linux/Mac.
# Exemple pour Linux x64:
# JDK_URL_LINUX="https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_linux_hotspot_17.0.11_9.tar.gz"
# JDK_ARCHIVE_TYPE="tar.gz" # vs "zip"

# Configuration Octave (similaire, adapter pour Linux/Mac si nécessaire)
OCTAVE_DIR_NAME_ONLY="portable_octave"
OCTAVE_DIR="$LIBS_DIR/$OCTAVE_DIR_NAME_ONLY"
OCTAVE_VERSION_MAJOR_MINOR="10.1.0"
OCTAVE_ARCH="w64" # Adapter pour Linux/Mac (ex: "gnu-linux")
OCTAVE_ZIP_NAME="octave-$OCTAVE_VERSION_MAJOR_MINOR-$OCTAVE_ARCH.zip" # Adapter extension pour tar.gz
OCTAVE_DOWNLOAD_URL="https://ftp.gnu.org/gnu/octave/windows/$OCTAVE_ZIP_NAME"
OCTAVE_EXTRACTED_DIR_NAME="octave-$OCTAVE_VERSION_MAJOR_MINOR-$OCTAVE_ARCH"
OCTAVE_TEMP_DOWNLOAD_DIR="$LIBS_DIR/_temp_octave_download"


# --- Fonctions Utilitaires ---
test_conda_installation() {
    if command -v conda &> /dev/null; then
        CONDA_VERSION=$(conda --version)
        echo "Conda est installé. Version: $CONDA_VERSION"
        return 0
    else
        echo "AVERTISSEMENT: Conda ne semble pas être installé ou n'est pas dans le PATH."
        return 1
    fi
}

# Fonction pour trouver le sous-répertoire du JDK (ex: jdk-17.0.11+9)
get_jdk_sub_dir() {
    local base_dir="$1"
    if [ ! -d "$base_dir" ]; then
        # echo "Le répertoire de base pour get_jdk_sub_dir '$base_dir' n'existe pas." >&2 # Rediriger vers stderr
        return 1
    fi
    # Trouve le premier répertoire qui commence par jdk-
    local jdk_sub_dir=$(find "$base_dir" -maxdepth 1 -type d -name "jdk-*" -print -quit)
    if [ -n "$jdk_sub_dir" ]; then
        echo "$jdk_sub_dir"
        return 0
    else
        return 1
    fi
}

download_and_extract() {
    local url="$1"
    local target_base_dir="$2" # ex: $JDK_DIR ou $OCTAVE_DIR
    local temp_download_dir_name="$3" # ex: _temp_jdk_download
    local archive_name="$4" # ex: jdk.zip ou octave.zip
    # local extracted_main_dir_name_pattern="$5" # Optionnel, pour vérifier après extraction

    local temp_full_download_path="$LIBS_DIR/$temp_download_dir_name"
    local zip_file_path="$temp_full_download_path/$archive_name"

    mkdir -p "$target_base_dir"
    mkdir -p "$temp_full_download_path"

    echo "Téléchargement depuis $url vers $zip_file_path..."
    if curl -L "$url" -o "$zip_file_path"; then
        echo "Téléchargement réussi."
        echo "Extraction de $zip_file_path vers '$target_base_dir'..."
        if [[ "$archive_name" == *.zip ]]; then
            if unzip -q "$zip_file_path" -d "$target_base_dir"; then
                echo "Extraction ZIP réussie."
                rm "$zip_file_path" # Nettoyage
                return 0
            else
                echo "ERREUR: Échec de l'extraction ZIP." >&2
                return 1
            fi
        elif [[ "$archive_name" == *.tar.gz ]]; then
            # tar xzf "$zip_file_path" -C "$target_base_dir" --strip-components=1 # Si on veut enlever le premier niveau
            if tar xzf "$zip_file_path" -C "$target_base_dir"; then
                 echo "Extraction TAR.GZ réussie."
                 rm "$zip_file_path" # Nettoyage
                 return 0
            else
                echo "ERREUR: Échec de l'extraction TAR.GZ." >&2
                return 1
            fi
        else
            echo "ERREUR: Type d'archive non supporté: $archive_name" >&2
            return 1
        fi
    else
        echo "ERREUR: Échec du téléchargement depuis $url." >&2
        return 1
    fi
}

# --- Nettoyage et déplacement (si applicable pour Bash) ---
# Moins pertinent car on installe directement dans libs/
echo ""
echo "--- Nettoyage et déplacement des anciennes installations portables (Bash) ---"
# Assurer que libs existe
mkdir -p "$LIBS_DIR"
mkdir -p "$TWEETY_LIBS_DIR"
mkdir -p "$TWEETY_NATIVE_LIBS_DIR"
# La logique de déplacement des dossiers de la racine vers libs/ est spécifique à la transition Windows.
# Pour un script Bash propre, on assume que les outils sont soit gérés par le système, soit installés dans libs/ directement.
echo "Nettoyage et déplacement (Bash) terminés."
echo "--- Fin Nettoyage (Bash) ---"
echo ""


# --- Vérification Conda ---
if ! test_conda_installation; then
    echo "ERREUR: Conda n'est pas installé ou accessible. Veuillez l'installer et relancer." >&2
    exit 1
fi

# --- Installation JDK ---
echo "Vérification du JDK portable dans '$JDK_DIR'..."
EXTRACTED_JDK_PATH=$(get_jdk_sub_dir "$JDK_DIR")

if [ "$FORCE_REINSTALL" = true ] && [ -n "$EXTRACTED_JDK_PATH" ]; then
    echo "Mode ForceReinstall : Suppression du JDK existant dans '$JDK_DIR'..."
    rm -rf "$JDK_DIR"
    EXTRACTED_JDK_PATH="" # Forcer la réinstallation
fi

if [ -z "$EXTRACTED_JDK_PATH" ]; then
    echo "JDK non trouvé ou réinstallation forcée. Téléchargement et extraction..."
    # Adapter JDK_URL et nom de l'archive pour Linux/Mac ici si nécessaire
    JDK_ARCHIVE_FOR_DOWNLOAD="jdk.zip" # Nom par défaut pour le fichier téléchargé
    JDK_URL_OS="$JDK_URL" # URL par défaut (Windows)

    if [[ "$(uname -s)" == "Linux" ]]; then
        JDK_URL_OS="https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_linux_hotspot_17.0.11_9.tar.gz"
        JDK_ARCHIVE_FOR_DOWNLOAD="jdk_linux.tar.gz"
    elif [[ "$(uname -s)" == "Darwin" ]]; then # macOS
        # Détecter l'architecture pour Mac (Intel x64 ou Apple Silicon arm64/aarch64)
        if [[ "$(uname -m)" == "arm64" || "$(uname -m)" == "aarch64" ]]; then
             JDK_URL_OS="https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-aarch64_mac_hotspot_17.0.11_9.tar.gz"
        else
             JDK_URL_OS="https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-x64_mac_hotspot_17.0.11_9.tar.gz"
        fi
        JDK_ARCHIVE_FOR_DOWNLOAD="jdk_mac.tar.gz"
    fi

    if download_and_extract "$JDK_URL_OS" "$JDK_DIR" "_temp_jdk_download" "$JDK_ARCHIVE_FOR_DOWNLOAD"; then
        EXTRACTED_JDK_PATH=$(get_jdk_sub_dir "$JDK_DIR")
        if [ -z "$EXTRACTED_JDK_PATH" ]; then
            echo "ERREUR: Impossible de déterminer le nom du répertoire JDK extrait dans '$JDK_DIR'." >&2
            # exit 1 # Ne pas quitter, laisser l'utilisateur gérer
        else
            echo "JDK disponible dans : $EXTRACTED_JDK_PATH"
        fi
    else
        echo "AVERTISSEMENT: Échec de l'installation du JDK. JAVA_HOME ne sera pas configuré." >&2
    fi
else
    echo "JDK portable déjà présent dans : $EXTRACTED_JDK_PATH"
fi
FINAL_JDK_DIR_NAME=$(basename "$EXTRACTED_JDK_PATH" 2>/dev/null || echo "")


# --- Installation Octave ---
# Similaire au JDK, adapter pour Linux/Mac. Octave est plus dépendant de l'OS.
# Sur Linux, 'sudo apt-get install octave' est souvent plus simple.
# Sur Mac, 'brew install octave'.
# Cette section pour Octave portable est plus pertinente pour Windows.
# On la garde pour la complétude mais avec des avertissements.
echo ""
echo "--- Configuration d'Octave Portable (Bash) ---"
EXPECTED_OCTAVE_CLI_PATH_WIN="$OCTAVE_DIR/$OCTAVE_EXTRACTED_DIR_NAME/mingw64/bin/octave-cli.exe" # Chemin Windows

if [[ "$(uname -s)" == "Linux" || "$(uname -s)" == "Darwin" ]]; then
    echo "INFO: Pour Linux/Mac, il est recommandé d'installer Octave via le gestionnaire de paquets (apt, brew, etc.)."
    echo "INFO: La section de téléchargement portable d'Octave est principalement pour Windows."
    # On pourrait essayer de trouver octave dans le PATH
    if command -v octave-cli &> /dev/null; then
        echo "Octave (octave-cli) trouvé dans le PATH."
        # On pourrait définir une variable OCTAVE_HOME si nécessaire pour d'autres scripts
    elif command -v octave &> /dev/null; then
         echo "Octave (commande 'octave') trouvé dans le PATH."
    else
        echo "AVERTISSEMENT: Octave non trouvé. La fonctionnalité Octave pourrait ne pas être disponible."
    fi
else # Windows (ou via WSL simulant Windows pour les chemins)
    if [ "$FORCE_REINSTALL" = true ] && [ -d "$OCTAVE_DIR" ]; then
        echo "Mode ForceReinstall : Suppression d'Octave existant dans '$OCTAVE_DIR'..."
        rm -rf "$OCTAVE_DIR"
    fi

    if [ ! -f "$EXPECTED_OCTAVE_CLI_PATH_WIN" ]; then
        echo "Octave CLI non trouvé ou réinstallation forcée. Tentative de téléchargement et extraction (pour Windows)..."
        if download_and_extract "$OCTAVE_DOWNLOAD_URL" "$OCTAVE_DIR" "_temp_octave_download" "$OCTAVE_ZIP_NAME"; then
            if [ ! -f "$EXPECTED_OCTAVE_CLI_PATH_WIN" ]; then
                echo "AVERTISSEMENT: Octave CLI toujours introuvable à '$EXPECTED_OCTAVE_CLI_PATH_WIN' après extraction." >&2
            else
                echo "Octave portable (Windows) disponible et CLI trouvé à : $EXPECTED_OCTAVE_CLI_PATH_WIN"
            fi
        else
            echo "AVERTISSEMENT: Échec de l'installation d'Octave portable (Windows)." >&2
        fi
    else
        echo "Octave portable (Windows) déjà présent et CLI trouvé à : $EXPECTED_OCTAVE_CLI_PATH_WIN"
    fi
fi
echo "--- Fin Configuration Octave (Bash) ---"


# --- Nettoyage anciens venv (Python standard) ---
# Moins critique si on utilise Conda, mais on garde une logique similaire.
echo ""
echo "Nettoyage des anciens répertoires d'environnements virtuels (venv)..."
OLD_VENV_DIRS=("venv" ".venv" "venv_py310")
for dir_name in "${OLD_VENV_DIRS[@]}"; do
    full_old_venv_path="$PROJECT_ROOT/$dir_name"
    if [ -d "$full_old_venv_path" ]; then
        if [ "$FORCE_REINSTALL" = true ]; then
            echo "Mode ForceReinstall : Suppression automatique de l'ancien répertoire $full_old_venv_path..."
            rm -rf "$full_old_venv_path" && echo "Répertoire $full_old_venv_path supprimé." || echo "AVERTISSEMENT: Impossible de supprimer $full_old_venv_path." >&2
        elif [ "$INTERACTIVE_MODE" = true ]; then
            read -p "L'ancien répertoire d'environnement virtuel '$dir_name' a été trouvé. Voulez-vous le supprimer ? (o/N) " confirmation
            if [[ "$confirmation" == "o" || "$confirmation" == "O" ]]; then
                echo "Suppression de l'ancien répertoire $full_old_venv_path..."
                rm -rf "$full_old_venv_path" && echo "Répertoire $full_old_venv_path supprimé." || echo "AVERTISSEMENT: Impossible de supprimer $full_old_venv_path." >&2
            else
                echo "Le répertoire '$full_old_venv_path' n'a pas été supprimé."
            fi
        else
            echo "Ancien répertoire d'environnement virtuel '$dir_name' trouvé. Non supprimé (mode par défaut)."
        fi
    fi
done
echo "Nettoyage des anciens venv terminé."

echo ""
echo "--- Nettoyage de l'ancien répertoire des JARs Tweety (argumentation_analysis/libs) ---"
OLD_TWEETY_DIR="$PROJECT_ROOT/argumentation_analysis/libs"
if [ -d "$OLD_TWEETY_DIR" ]; then
    echo "Ancien répertoire des JARs Tweety trouvé: $OLD_TWEETY_DIR."
    if [ "$FORCE_REINSTALL" = true ]; then
        echo "Suppression automatique de '$OLD_TWEETY_DIR' (mode ForceReinstall)..."
        rm -rf "$OLD_TWEETY_DIR" && echo "Répertoire '$OLD_TWEETY_DIR' supprimé." || echo "AVERTISSEMENT: Impossible de supprimer '$OLD_TWEETY_DIR'." >&2
    elif [ "$INTERACTIVE_MODE" = true ]; then
        read -p "L'ancien répertoire des JARs Tweety '$OLD_TWEETY_DIR' a été trouvé. Voulez-vous le supprimer ? (o/N) " confirmation
        if [[ "$confirmation" == "o" || "$confirmation" == "O" ]]; then
            echo "Suppression de '$OLD_TWEETY_DIR'..."
            rm -rf "$OLD_TWEETY_DIR" && echo "Répertoire '$OLD_TWEETY_DIR' supprimé." || echo "AVERTISSEMENT: Impossible de supprimer '$OLD_TWEETY_DIR'." >&2
        else
            echo "Le répertoire '$OLD_TWEETY_DIR' n'a pas été supprimé."
        fi
    else
        echo "Ancien répertoire des JARs Tweety '$OLD_TWEETY_DIR' trouvé. Non supprimé (mode par défaut)."
    fi
else
    echo "Ancien répertoire des JARs Tweety '$OLD_TWEETY_DIR' non trouvé. Aucun nettoyage nécessaire."
fi
echo "--- Fin Nettoyage ancien répertoire JARs Tweety ---"
echo ""

# --- Configuration de l'environnement Conda ---
echo ""
echo "--- Configuration de l'environnement Conda '$CONDA_ENV_NAME' ---"
CONDA_ENV_EXISTS=$(conda env list | grep -E "\s$CONDA_ENV_NAME\s" || true) # || true pour éviter l'échec si grep ne trouve rien

if [ "$FORCE_REINSTALL" = true ] && [ -n "$CONDA_ENV_EXISTS" ]; then
    echo "Mode ForceReinstall : Suppression de l'environnement Conda '$CONDA_ENV_NAME'..."
    conda env remove --name "$CONDA_ENV_NAME" -y && echo "Environnement Conda '$CONDA_ENV_NAME' supprimé." || echo "AVERTISSEMENT: Problème lors de la suppression de l'env Conda." >&2
    CONDA_ENV_EXISTS=""
elif [ -n "$CONDA_ENV_EXISTS" ] && [ "$INTERACTIVE_MODE" = true ]; then
    read -p "L'environnement Conda '$CONDA_ENV_NAME' existe déjà. Voulez-vous le supprimer pour une installation propre ? (o/N) " cleanup_confirmation
    if [[ "$cleanup_confirmation" == "o" || "$cleanup_confirmation" == "O" ]]; then
        echo "Suppression de l'environnement Conda '$CONDA_ENV_NAME'..."
        conda env remove --name "$CONDA_ENV_NAME" -y && echo "Environnement Conda '$CONDA_ENV_NAME' supprimé." || echo "AVERTISSEMENT: Problème lors de la suppression de l'env Conda." >&2
        CONDA_ENV_EXISTS=""
    else
        echo "L'environnement Conda '$CONDA_ENV_NAME' ne sera pas supprimé. Tentative de mise à jour."
    fi
fi

if [ ! -f "$ENVIRONMENT_YML_FILE_PATH" ]; then
    echo "ERREUR: Le fichier d'environnement '$ENVIRONMENT_YML_FILE' est introuvable à '$ENVIRONMENT_YML_FILE_PATH'" >&2
    exit 1
fi

CONDA_ENV_EXISTS_AFTER_CLEANUP=$(conda env list | grep -E "\s$CONDA_ENV_NAME\s" || true)

if [ -n "$CONDA_ENV_EXISTS_AFTER_CLEANUP" ]; then
    echo "L'environnement Conda '$CONDA_ENV_NAME' existe. Mise à jour..."
    if conda env update --name "$CONDA_ENV_NAME" --file "$ENVIRONMENT_YML_FILE_PATH" --prune; then
        echo "Environnement Conda '$CONDA_ENV_NAME' mis à jour avec succès."
    else
        echo "ERREUR: Échec de la mise à jour de l'environnement Conda '$CONDA_ENV_NAME'." >&2
        exit 1
    fi
else
    echo "L'environnement Conda '$CONDA_ENV_NAME' n'existe pas. Création..."
    if conda env create -f "$ENVIRONMENT_YML_FILE_PATH"; then
        echo "Environnement Conda '$CONDA_ENV_NAME' créé avec succès."
    else
        echo "ERREUR: Échec de la création de l'environnement Conda '$CONDA_ENV_NAME'." >&2
        echo "Tentative de suppression de l'environnement '$CONDA_ENV_NAME' suite à l'échec..."
        conda env remove --name "$CONDA_ENV_NAME" -y
        exit 1
    fi
fi
echo "--- Fin Configuration Conda ---"
echo ""


# --- Mise à jour du fichier .env ---
echo "Vérification du fichier .env..."
if [ ! -f "$ENV_FILE_PATH" ]; then
    if [ -f "$ENV_TEMPLATE_FILE_PATH" ]; then
        echo "Copie de .env.template vers .env..."
        cp "$ENV_TEMPLATE_FILE_PATH" "$ENV_FILE_PATH"
    else
        echo "AVERTISSEMENT: Le fichier .env.template est introuvable. Création d'un fichier .env vide."
        touch "$ENV_FILE_PATH"
    fi
fi

update_env_var() {
    local key_to_update="$1"
    local new_value_line="$2"
    local env_file="$3"
    local temp_env_file="${env_file}.tmp"

    # Utiliser awk pour remplacer ou ajouter la ligne, gérant les commentaires
    awk -v key="$key_to_update" -v newline="$new_value_line" '
    BEGIN { found=0 }
    {
        if ($0 ~ ("^#?[[:space:]]*" key "=")) {
            print newline;
            found=1;
        } else {
            print $0;
        }
    }
    END { if (found==0) print newline }
    ' "$env_file" > "$temp_env_file" && mv "$temp_env_file" "$env_file"
}

if [ -n "$FINAL_JDK_DIR_NAME" ]; then
    echo "Mise à jour de JAVA_HOME dans le fichier .env..."
    # Chemin relatif depuis la racine du projet
    RELATIVE_PATH_TO_JDK_IN_LIBS="libs/$JDK_DIR_NAME_ONLY/$FINAL_JDK_DIR_NAME"
    JAVA_HOME_LINE="JAVA_HOME=./$RELATIVE_PATH_TO_JDK_IN_LIBS"
    update_env_var "JAVA_HOME" "$JAVA_HOME_LINE" "$ENV_FILE_PATH"
    echo "Fichier .env mis à jour avec : $JAVA_HOME_LINE"
else
    echo "AVERTISSEMENT: FINAL_JDK_DIR_NAME est vide, JAVA_HOME non mis à jour dans .env."
fi

echo "Mise à jour de USE_REAL_JPYPE dans le fichier .env..."
USE_REAL_JPYPE_LINE="USE_REAL_JPYPE=true"
update_env_var "USE_REAL_JPYPE" "$USE_REAL_JPYPE_LINE" "$ENV_FILE_PATH"
echo "Fichier .env mis à jour concernant USE_REAL_JPYPE."


# --- Installation du projet en mode édition ---
echo ""
echo "Appel du script d'activation (activate_project_env.sh) pour exécuter 'pip install -e .' dans l'environnement..."
PIP_INSTALL_COMMAND="pip install -e ."
# Le script activate_project_env.sh est dans le même répertoire (scripts/env)
ACTIVATE_SCRIPT_PATH_FOR_SETUP="$SCRIPT_DIR_SETUP_ENV_SH/activate_project_env.sh"

if [ -f "$ACTIVATE_SCRIPT_PATH_FOR_SETUP" ]; then
    echo "Exécution de: bash \"$ACTIVATE_SCRIPT_PATH_FOR_SETUP\" \"$PIP_INSTALL_COMMAND\""
    # Exécuter dans un sous-shell pour que les exports de activate_project_env.sh ne polluent pas ce script
    (bash "$ACTIVATE_SCRIPT_PATH_FOR_SETUP" "$PIP_INSTALL_COMMAND")
    EXIT_CODE_PIP=$?
    if [ $EXIT_CODE_PIP -ne 0 ]; then
        echo "ERREUR: L'exécution de '$PIP_INSTALL_COMMAND' via activate_project_env.sh a échoué avec le code $EXIT_CODE_PIP." >&2
    else
        echo "'$PIP_INSTALL_COMMAND' exécuté avec succès via activate_project_env.sh."
    fi
else
    echo "ERREUR: Le script '$ACTIVATE_SCRIPT_PATH_FOR_SETUP' est introuvable." >&2
fi


# --- Instructions Finales ---
echo ""
echo "---------------------------------------------------------------------"
echo "Installation et configuration de l'environnement Conda '$CONDA_ENV_NAME' terminées!"
echo "---------------------------------------------------------------------"
echo ""
echo "Fin du script setup_project_env.sh."
echo "L'environnement '$CONDA_ENV_NAME' devrait être configuré et le projet installé en mode édition."
echo "Pour utiliser l'environnement, activez-le dans un nouveau terminal :"
echo "    conda activate $CONDA_ENV_NAME"
echo "Ou utilisez directement le raccourci à la racine activate_project_env.sh avec votre commande en argument."
echo "---------------------------------------------------------------------"