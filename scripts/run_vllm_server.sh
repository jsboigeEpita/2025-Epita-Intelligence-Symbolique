#!/bin/bash

# ==============================================================================
# Script de Lancement pour le Serveur d'Inférence vLLM
#
# Auteur : Roo, Code Agent
# Date   : 1er Août 2025
#
# Description :
# Ce script lance le serveur vLLM avec le modèle Unsloth Qwen3 quantisé.
# Il est conçu pour être exécuté à l'intérieur d'un environnement WSL 2
# ayant accès au GPU de l'hôte.
#
# Prérequis :
# 1. Un environnement virtuel (ex: venv) contenant les dépendances:
#    pip install "unsloth[vllm-linux]>=2025.7" huggingface_hub hf_transfer transformers
# 2. Accès au GPU configuré dans WSL (vérifiable avec `nvidia-smi`).
#
# Usage :
# 1. (Optionnel) Activer l'environnement virtuel: source /chemin/vers/venv/bin/activate
# 2. Exécuter ce script: ./scripts/run_vllm_server.sh
# ==============================================================================

# Active les "erreurs strictes" pour le script.
# -e: Quitte immédiatement si une commande échoue.
# -u: Traite les variables non définies comme des erreurs.
# -o pipefail: Le code de sortie d'un pipeline est celui de la dernière commande à échouer.
set -euo pipefail

# Détection de l'activation de l'environnement virtuel.
# Si la variable VIRTUAL_ENV n'est pas définie, tente d'activer un venv local.
if [ -z "${VIRTUAL_ENV-}" ]; then
    VENV_PATH="./venv_vllm"
    if [ -d "$VENV_PATH" ]; then
        echo "Environnement virtuel non détecté. Tentative d'activation de '$VENV_PATH'..."
        # L'activation nécessite d'utiliser 'source', qui ne peut pas être appelé directement
        # de manière portable. On informe l'utilisateur.
        echo "ERREUR: Veuillez activer manuellement l'environnement virtuel avant de lancer le script."
        echo "Exemple: source $VENV_PATH/bin/activate"
        exit 1
    else
        echo "AVERTISSEMENT: Aucun environnement virtuel ('$VENV_PATH') trouvé et VIRTUAL_ENV n'est pas défini."
        echo "Le script continue, en supposant que 'vllm' est dans le PATH global."
    fi
fi

echo "Lancement du serveur vLLM..."
echo "Modèle : unsloth/Qwen3-1.7B-Base-unsloth-bnb-4bit"
echo "API exposée sur : http://0.0.0.0:8000"

# Lancer le serveur vLLM avec les paramètres optimisés pour Qwen3 et le Function Calling.
vllm serve unsloth/Qwen3-1.7B-Base-unsloth-bnb-4bit \
    --model-name "Qwen3-1.7B-Toulmin-Analyzer" \
    --host 0.0.0.0 \
    --port 8000 \
    --gpu-memory-utilization 0.90 \
    --max-model-len 32768 \
    \
    # --- Optimisations spécifiques à Qwen3 pour le raisonnement ---
    --enable-reasoning \
    --reasoning-parser qwen3 \
    \
    # --- Optimisations pour le Tool Calling (Function Calling) ---
    --enable-auto-tool-choice \
    --tool-call-parser hermes

echo "Serveur vLLM arrêté."
