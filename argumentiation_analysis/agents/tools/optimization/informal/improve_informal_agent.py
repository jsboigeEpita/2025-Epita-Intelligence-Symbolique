#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour améliorer directement l'agent Informel.

Ce script implémente les améliorations identifiées pour l'agent Informel :
1. Amélioration du prompt d'identification des arguments
2. Ajout de nouveaux prompts pour l'analyse des sophismes
3. Amélioration des instructions pour l'exploration de la taxonomie
4. Ajout de directives pour des justifications plus détaillées
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("ImproveInformalAgent")

# Répertoire pour les sauvegardes
BACKUP_DIR = Path("utils/informal_optimization/backups")
BACKUP_DIR.mkdir(exist_ok=True, parents=True)

def backup_original_files():
    """
    Crée une sauvegarde des fichiers originaux de l'agent Informel.
    """
    logger.info("Création de sauvegardes des fichiers originaux...")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    files_to_backup = [
        "informal/prompts.py",
        "informal/informal_definitions.py"
    ]
    
    for file_path in files_to_backup:
        src_path = Path(file_path)
        if not src_path.exists():
            logger.warning(f"Fichier source {src_path} non trouvé.")
            continue
        
        backup_path = BACKUP_DIR / f"{timestamp}_{src_path.name}"
        try:
            shutil.copy2(src_path, backup_path)
            logger.info(f"Sauvegarde créée: {backup_path}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de {src_path}: {e}")
    
    return timestamp

def improve_prompts(backup_timestamp):
    """
    Améliore les prompts de l'agent Informel.
    """
    logger.info("Amélioration des prompts...")
    
    # Charger le fichier prompts.py original
    prompts_path = Path("informal/prompts.py")
    if not prompts_path.exists():
        logger.error(f"Fichier {prompts_path} non trouvé.")
        return False
    
    try:
        # Créer une version améliorée du prompt d'identification des arguments
        improved_prompt = """# agents/informal/prompts.py
import logging

# --- Fonction Sémantique (Prompt) pour Identification Arguments (V8 - Amélioré) ---
prompt_identify_args_v8 = \"\"\"
[Instructions]
Analysez le texte argumentatif fourni ($input) et identifiez tous les arguments ou affirmations distincts.

Un bon argument doit:
1. Exprimer une position claire ou une affirmation défendable
2. Être concis (idéalement 10-20 mots)
3. Capturer une idée complète sans détails superflus
4. Être formulé de manière neutre et précise

Pour chaque argument identifié:
- Formulez-le comme une affirmation simple et directe
- Concentrez-vous sur les affirmations principales défendues ou attaquées
- Évitez les formulations trop longues ou trop complexes
- Assurez-vous de capturer tous les arguments importants, même secondaires

Retournez UNIQUEMENT la liste des arguments, un par ligne, sans numérotation, préambule ou commentaire.

[Texte à Analyser]
{{$input}}
+++++
[Arguments Identifiés (un par ligne)]
\"\"\"

# --- Fonction Sémantique (Prompt) pour Analyse de Sophismes (Nouveau) ---
prompt_analyze_fallacies_v1 = \"\"\"
[Instructions]
Analysez l'argument fourni ($input) et identifiez les sophismes potentiels qu'il contient.

Pour chaque sophisme identifié, vous devez:
1. Nommer précisément le type de sophisme selon la taxonomie standard
2. Expliquer pourquoi cet argument constitue ce type de sophisme
3. Citer la partie spécifique du texte qui illustre le sophisme
4. Proposer une reformulation non fallacieuse de l'argument (si possible)

Concentrez-vous sur les sophismes les plus évidents et significatifs. Soyez précis dans votre analyse.

[Argument à Analyser]
{{$input}}
+++++
[Sophismes Identifiés]
\"\"\"

# --- Fonction Sémantique (Prompt) pour Justification d'Attribution (Nouveau) ---
prompt_justify_fallacy_attribution_v1 = \"\"\"
[Instructions]
Vous devez justifier pourquoi l'argument fourni ($input) contient le sophisme spécifié.

Votre justification doit:
1. Expliquer clairement le mécanisme du sophisme indiqué
2. Montrer précisément comment l'argument correspond à ce type de sophisme
3. Citer des parties spécifiques de l'argument qui illustrent le sophisme
4. Fournir un exemple similaire pour clarifier (si pertinent)
5. Expliquer l'impact de ce sophisme sur la validité de l'argument

[Argument]
{{$input.argument}}

[Sophisme à Justifier]
{{$input.fallacy_type}}

[Définition du Sophisme]
{{$input.fallacy_definition}}
+++++
[Justification Détaillée]
\"\"\"

# Log de chargement
logging.getLogger(__name__).debug("Module agents.informal.prompts chargé (V8 - Amélioré).")
"""
        
        # Sauvegarder le nouveau contenu
        with open(prompts_path, "w", encoding="utf-8") as f:
            f.write(improved_prompt)
        
        logger.info(f"Prompts améliorés et sauvegardés dans {prompts_path}")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'amélioration des prompts: {e}")
        return False

def improve_instructions(backup_timestamp):
    """
    Améliore les instructions de l'agent Informel.
    """
    logger.info("Amélioration des instructions...")
    
    # Charger le fichier informal_definitions.py original
    defs_path = Path("informal/informal_definitions.py")
    if not defs_path.exists():
        logger.error(f"Fichier {defs_path} non trouvé.")
        return False
    
    try:
        with open(defs_path, "r", encoding="utf-8") as f:
            original_content = f.read()
        
        # Trouver la section des instructions
        start_marker = "INFORMAL_AGENT_INSTRUCTIONS_V13_TEMPLATE = \"\"\""
        end_marker = "\"\"\"\nINFORMAL_AGENT_INSTRUCTIONS = INFORMAL_AGENT_INSTRUCTIONS_V13_TEMPLATE.format("
        
        if start_marker not in original_content or end_marker not in original_content:
            logger.error("Marqueurs de section d'instructions non trouvés.")
            return False
        
        start_idx = original_content.find(start_marker) + len(start_marker)
        end_idx = original_content.find(end_marker)
        
        # Extraire les instructions originales
        original_instructions = original_content[start_idx:end_idx]
        
        # Créer des instructions améliorées
        improved_instructions = """
Votre Rôle: Spécialiste en analyse rhétorique informelle. Vous identifiez les arguments et analysez les sophismes en utilisant une taxonomie externe (via CSV).
Racine de la Taxonomie des Sophismes: PK={ROOT_PK}

**Fonctions Outils Disponibles:**
* `StateManager.*`: Fonctions pour lire et écrire dans l'état partagé (ex: `get_current_state_snapshot`, `add_identified_argument`, `add_identified_fallacy`, `add_answer`). **Utilisez ces fonctions pour enregistrer vos résultats.**
* `InformalAnalyzer.semantic_IdentifyArguments(input: str)`: Fonction sémantique (LLM) pour extraire les arguments d'un texte.
* `InformalAnalyzer.explore_fallacy_hierarchy(current_pk_str: str, max_children: int = 15)`: Fonction native (plugin) pour explorer la taxonomie CSV. Retourne JSON avec nœud courant et enfants.
* `InformalAnalyzer.get_fallacy_details(fallacy_pk_str: str)`: Fonction native (plugin) pour obtenir les détails d'un sophisme via son PK. Retourne JSON.

**Processus Général (pour chaque tâche assignée par le PM):**
1.  Lire DERNIER message du PM pour identifier votre tâche actuelle et son `task_id`.
2.  Exécuter l'action principale demandée en utilisant les fonctions outils appropriées.
3.  **Enregistrer les résultats** dans l'état partagé via les fonctions `StateManager`.
4.  **Signaler la fin de la tâche** au PM en appelant `StateManager.add_answer` avec le `task_id` reçu, un résumé de votre travail et les IDs des éléments ajoutés (`arg_id`, `fallacy_id`).

**Exemples de Tâches Spécifiques:**

* **Tâche "Identifier les arguments":**
    1.  Récupérer le texte brut (`raw_text`) depuis l'état (`StateManager.get_current_state_snapshot(summarize=False)`).
    2.  Appeler `InformalAnalyzer.semantic_IdentifyArguments(input=raw_text)`.
    3.  Pour chaque argument trouvé (chaque ligne de la réponse du LLM), appeler `StateManager.add_identified_argument(description=\\\"...\\\")`. Collecter les `arg_ids`.
    4.  Appeler `StateManager.add_answer` pour la tâche `[task_id reçu]`, avec un résumé et la liste des `arg_ids`.

* **Tâche "Explorer taxonomie [depuis PK]":**
    1.  Déterminer le PK de départ (fourni dans la tâche ou `{ROOT_PK}`).
    2.  Appeler `InformalAnalyzer.explore_fallacy_hierarchy(current_pk_str=\\\"[PK en string]\\\")`.
    3.  Analyser le JSON retourné (vérifier `error`). Formuler une réponse textuelle résumant le nœud courant (`current_node`) et les enfants (`children`) avec leur PK et label (`nom_vulgarisé` ou `text_fr`). Proposer des actions (explorer enfant, voir détails, attribuer).
    4.  Appeler `StateManager.add_answer` pour la tâche `[task_id reçu]`, avec la réponse textuelle et le PK exploré comme `source_ids`.

* **Tâche "Obtenir détails sophisme [PK]":**
    1.  Appeler `InformalAnalyzer.get_fallacy_details(fallacy_pk_str=\\\"[PK en string]\\\")`.
    2.  Analyser le JSON retourné (vérifier `error`). Formuler une réponse textuelle avec les détails pertinents (PK, labels, description, exemple, famille).
    3.  Appeler `StateManager.add_answer` pour la tâche `[task_id reçu]`, avec les détails formatés et le PK comme `source_ids`.

* **Tâche "Attribuer sophisme [PK] à argument [arg_id]":**
    1.  Appeler `InformalAnalyzer.get_fallacy_details(fallacy_pk_str=\\\"[PK en string]\\\")` pour obtenir le label (priorité: `nom_vulgarisé`, sinon `text_fr`) et la description complète. Vérifier `error`. Si pas de label valide ou erreur, signaler dans la réponse `add_answer` et **ne pas attribuer**.
    2.  Récupérer le texte de l'argument ciblé depuis l'état partagé.
    3.  Rédiger une justification détaillée pour l'attribution qui:
       - Explique clairement en quoi l'argument correspond à ce type de sophisme
       - Cite des parties spécifiques de l'argument qui illustrent le sophisme
       - Fournit un exemple similaire pour clarifier (si pertinent)
       - Explique l'impact de ce sophisme sur la validité de l'argument
    4.  Si label OK, appeler `StateManager.add_identified_fallacy(fallacy_type=\\\"[label trouvé]\\\", justification=\\\"...\\\", target_argument_id=\\\"[arg_id]\\\")`. Noter le `fallacy_id`.
    5.  Appeler `StateManager.add_answer` pour la tâche `[task_id reçu]`, avec confirmation (PK, label, arg_id, fallacy_id) ou message d'erreur si étape 1 échoue. Utiliser IDs pertinents (`fallacy_id`, `arg_id`) comme `source_ids`.

* **Tâche "Analyser sophismes dans argument [arg_id]":**
    1.  Récupérer le texte de l'argument depuis l'état partagé.
    2.  Explorer la taxonomie des sophismes en commençant par la racine (`{ROOT_PK}`).
    3.  Pour chaque catégorie pertinente de sophismes, explorer les sous-catégories.
    4.  Pour chaque sophisme potentiellement applicable:
       - Obtenir ses détails complets via `InformalAnalyzer.get_fallacy_details`
       - Évaluer si l'argument contient ce type de sophisme
       - Si oui, attribuer le sophisme avec une justification détaillée
    5.  Viser à identifier au moins 2-3 sophismes différents par argument quand c'est pertinent.
    6.  Appeler `StateManager.add_answer` avec un résumé des sophismes identifiés.

* **Si Tâche Inconnue/Pas Claire:** Signaler l'incompréhension via `StateManager.add_answer`.

**Directives pour l'Exploration de la Taxonomie:**
- Explorez systématiquement la taxonomie en profondeur, pas seulement les premiers niveaux.
- Utilisez une approche "top-down": commencez par les grandes catégories, puis explorez les sous-catégories pertinentes.
- Pour chaque argument, considérez au moins 3-5 branches différentes de la taxonomie.
- Ne vous limitez pas aux sophismes les plus évidents ou les plus connus.
- Documentez votre processus d'exploration dans vos réponses.

**Directives pour les Justifications:**
- Vos justifications doivent être détaillées (au moins 100 mots).
- Incluez toujours des citations spécifiques de l'argument qui illustrent le sophisme.
- Expliquez le mécanisme du sophisme et son impact sur la validité de l'argument.
- Quand c'est pertinent, fournissez un exemple similaire pour clarifier.
- Évitez les justifications vagues ou génériques.

**Important:** Toujours utiliser le `task_id` fourni par le PM pour `StateManager.add_answer`. Gérer les erreurs potentielles des appels de fonction (vérifier `error` dans JSON retourné par les fonctions natives, ou si une fonction retourne `FUNC_ERROR:`).
"""
        
        # Remplacer les instructions dans le contenu original
        new_content = original_content[:start_idx] + improved_instructions + original_content[end_idx:]
        
        # Mettre à jour la version des instructions
        new_content = new_content.replace("INFORMAL_AGENT_INSTRUCTIONS_V13_TEMPLATE", "INFORMAL_AGENT_INSTRUCTIONS_V14_TEMPLATE")
        new_content = new_content.replace("INFORMAL_AGENT_INSTRUCTIONS = INFORMAL_AGENT_INSTRUCTIONS_V13_TEMPLATE", "INFORMAL_AGENT_INSTRUCTIONS = INFORMAL_AGENT_INSTRUCTIONS_V14_TEMPLATE")
        new_content = new_content.replace("Instructions Système INFORMAL_AGENT_INSTRUCTIONS (V13)", "Instructions Système INFORMAL_AGENT_INSTRUCTIONS (V14)")
        
        # Mettre à jour l'import du prompt
        new_content = new_content.replace("from .prompts import prompt_identify_args_v7", "from .prompts import prompt_identify_args_v8")
        
        # Mettre à jour la fonction setup_informal_kernel
        new_content = new_content.replace("prompt=prompt_identify_args_v7", "prompt=prompt_identify_args_v8")
        
        # Sauvegarder le nouveau contenu
        with open(defs_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        logger.info(f"Instructions améliorées et sauvegardées dans {defs_path}")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'amélioration des instructions: {e}")
        return False

def update_kernel_function_registration():
    """
    Met à jour l'enregistrement des fonctions du kernel pour inclure les nouveaux prompts.
    """
    logger.info("Mise à jour de l'enregistrement des fonctions du kernel...")
    
    defs_path = Path("informal/informal_definitions.py")
    if not defs_path.exists():
        logger.error(f"Fichier {defs_path} non trouvé.")
        return False
    
    try:
        with open(defs_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Trouver la section d'enregistrement des fonctions
        setup_function_start = "def setup_informal_kernel(kernel: sk.Kernel, llm_service):"
        if setup_function_start not in content:
            logger.error("Section d'enregistrement des fonctions non trouvée.")
            return False
        
        # Ajouter l'enregistrement des nouvelles fonctions sémantiques
        setup_function_idx = content.find(setup_function_start)
        function_registration_idx = content.find("kernel.add_function(", setup_function_idx)
        
        if function_registration_idx == -1:
            logger.error("Section d'enregistrement des fonctions non trouvée.")
            return False
        
        # Trouver la fin de l'enregistrement actuel
        end_registration_idx = content.find("logger.debug(f\"Fonction {plugin_name}.semantic_IdentifyArguments ajoutée/mise à jour.\")", function_registration_idx)
        if end_registration_idx == -1:
            logger.error("Fin de l'enregistrement des fonctions non trouvée.")
            return False
        
        end_registration_idx = content.find("\n", end_registration_idx)
        
        # Ajouter l'enregistrement des nouvelles fonctions
        new_registrations = """
        # Ajouter la fonction d'analyse des sophismes
        try:
            kernel.add_function(
                prompt=prompt_analyze_fallacies_v1,
                plugin_name=plugin_name,
                function_name="semantic_AnalyzeFallacies",
                description="Analyse les sophismes dans un argument.",
                prompt_execution_settings=default_settings
            )
            logger.debug(f"Fonction {plugin_name}.semantic_AnalyzeFallacies ajoutée/mise à jour.")
        except ValueError as ve:
            logger.warning(f"Problème ajout/MàJ semantic_AnalyzeFallacies: {ve}")
            
        # Ajouter la fonction de justification d'attribution
        try:
            kernel.add_function(
                prompt=prompt_justify_fallacy_attribution_v1,
                plugin_name=plugin_name,
                function_name="semantic_JustifyFallacyAttribution",
                description="Justifie l'attribution d'un sophisme à un argument.",
                prompt_execution_settings=default_settings
            )
            logger.debug(f"Fonction {plugin_name}.semantic_JustifyFallacyAttribution ajoutée/mise à jour.")
        except ValueError as ve:
            logger.warning(f"Problème ajout/MàJ semantic_JustifyFallacyAttribution: {ve}")
        """
        
        # Insérer les nouvelles fonctions
        new_content = content[:end_registration_idx + 1] + new_registrations + content[end_registration_idx + 1:]
        
        # Mettre à jour l'import des prompts
        import_line = "from .prompts import prompt_identify_args_v8"
        new_import_line = "from .prompts import prompt_identify_args_v8, prompt_analyze_fallacies_v1, prompt_justify_fallacy_attribution_v1"
        new_content = new_content.replace(import_line, new_import_line)
        
        # Sauvegarder le nouveau contenu
        with open(defs_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        logger.info(f"Enregistrement des fonctions mis à jour dans {defs_path}")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de l'enregistrement des fonctions: {e}")
        return False

def main():
    """
    Fonction principale du script.
    """
    logger.info("Démarrage des améliorations de l'agent Informel...")
    
    # Créer des sauvegardes des fichiers originaux
    backup_timestamp = backup_original_files()
    
    # Améliorer les prompts
    prompts_improved = improve_prompts(backup_timestamp)
    
    # Améliorer les instructions
    instructions_improved = improve_instructions(backup_timestamp)
    
    # Mettre à jour l'enregistrement des fonctions
    functions_updated = update_kernel_function_registration()
    
    logger.info("Améliorations de l'agent Informel terminées.")
    logger.info(f"Prompts améliorés: {prompts_improved}")
    logger.info(f"Instructions améliorées: {instructions_improved}")
    logger.info(f"Fonctions mises à jour: {functions_updated}")

if __name__ == "__main__":
    main()