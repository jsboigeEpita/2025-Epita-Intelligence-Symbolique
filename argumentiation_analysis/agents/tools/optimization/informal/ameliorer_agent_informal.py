#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour améliorer l'agent Informel en fonction de l'analyse des traces.

Ce script permet de:
1. Implémenter les améliorations identifiées dans l'analyse des traces
2. Mettre à jour les prompts et les instructions de l'agent Informel
3. Tester les améliorations sur les mêmes extraits de texte
"""

import os
import sys
import json
import shutil
import logging
import asyncio
from pathlib import Path
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("AmeliorerAgentInformal")

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
def improve_prompts():
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
        # Créer une version améliorée des prompts
        improved_prompts = """# agents/informal/prompts.py
import logging

# --- Fonction Sémantique (Prompt) pour Identification Arguments (V9 - Optimisé) ---
prompt_identify_args_v9 = \"\"\"
[Instructions]
Analysez le texte argumentatif fourni ($input) et identifiez tous les arguments ou affirmations distincts.

Un bon argument doit:
1. Exprimer une position claire ou une affirmation défendable
2. Être concis (idéalement 10-20 mots)
3. Capturer une idée complète sans détails superflus
4. Être formulé de manière neutre et précise
5. Représenter une seule idée ou affirmation à la fois

Pour chaque argument identifié:
- Formulez-le comme une affirmation simple et directe
- Concentrez-vous sur les affirmations principales défendues ou attaquées
- Évitez les formulations trop longues ou trop complexes
- Assurez-vous de capturer tous les arguments importants, même secondaires
- Séparez les idées complexes en plusieurs arguments distincts

Retournez UNIQUEMENT la liste des arguments, un par ligne, sans numérotation, préambule ou commentaire.

[Texte à Analyser]
{{$input}}
+++++
[Arguments Identifiés (un par ligne)]
\"\"\"

# --- Fonction Sémantique (Prompt) pour Analyse de Sophismes (V2 - Optimisé) ---
prompt_analyze_fallacies_v2 = \"\"\"
[Instructions]
Analysez l'argument fourni ($input) et identifiez les sophismes potentiels qu'il contient.

Pour cette analyse, vous devez:
1. Explorer systématiquement au moins 5 branches différentes de la taxonomie des sophismes
2. Considérer les sophismes à tous les niveaux de profondeur, pas seulement les catégories générales
3. Identifier au moins 2-3 sophismes différents si pertinent
4. Documenter votre processus d'exploration de la taxonomie

Pour chaque sophisme identifié, vous devez:
1. Nommer précisément le type de sophisme selon la taxonomie standard
2. Expliquer pourquoi cet argument constitue ce type de sophisme
3. Citer la partie spécifique du texte qui illustre le sophisme
4. Expliquer l'impact de ce sophisme sur la validité de l'argument
5. Proposer une reformulation non fallacieuse de l'argument (si possible)

[Argument à Analyser]
{{$input}}
+++++
[Sophismes Identifiés]
\"\"\"

# --- Fonction Sémantique (Prompt) pour Justification d'Attribution (V2 - Optimisé) ---
prompt_justify_fallacy_attribution_v2 = \"\"\"
[Instructions]
Vous devez justifier pourquoi l'argument fourni contient le sophisme spécifié.

Votre justification doit:
1. Expliquer clairement le mécanisme du sophisme indiqué (au moins 50 mots)
2. Montrer précisément comment l'argument correspond à ce type de sophisme (au moins 50 mots)
3. Citer des parties spécifiques de l'argument qui illustrent le sophisme (utiliser des guillemets)
4. Fournir un exemple similaire pour clarifier (au moins 30 mots)
5. Expliquer l'impact de ce sophisme sur la validité de l'argument (au moins 30 mots)

Votre justification complète doit faire au moins 150 mots et être détaillée, précise et convaincante.

[Argument]
{{$argument}}

[Sophisme à Justifier]
{{$fallacy_type}}

[Définition du Sophisme]
{{$fallacy_definition}}
+++++
[Justification Détaillée]
\"\"\"

# --- Fonction Sémantique (Prompt) pour Exploration Taxonomie (Nouveau) ---
prompt_explore_taxonomy_v1 = \"\"\"
[Instructions]
Explorez systématiquement la taxonomie des sophismes pour identifier les catégories pertinentes pour l'analyse de l'argument fourni.

Pour cette exploration, vous devez:
1. Commencer par la racine de la taxonomie (PK=0)
2. Explorer au moins 5 branches différentes de la taxonomie
3. Pour chaque branche, descendre jusqu'aux niveaux les plus profonds (au moins niveau 3-4)
4. Documenter votre processus d'exploration
5. Identifier les sophismes potentiellement applicables à l'argument

Pour chaque sophisme potentiellement applicable, notez:
1. Son PK dans la taxonomie
2. Son nom (nom_vulgarisé ou text_fr)
3. Une brève explication de sa pertinence pour l'argument

[Argument à Analyser]
{{$input}}
+++++
[Résultats de l'Exploration]
\"\"\"

# Log de chargement
logging.getLogger(__name__).debug("Module agents.informal.prompts chargé (V9 - Optimisé).")
"""
        
        # Sauvegarder le nouveau contenu
        with open(prompts_path, "w", encoding="utf-8") as f:
            f.write(improved_prompts)
        
        logger.info(f"Prompts améliorés et sauvegardés dans {prompts_path}")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'amélioration des prompts: {e}")
        return False
def improve_instructions():
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
        
        # Mettre à jour les imports des prompts
        updated_content = original_content.replace(
            "from .prompts import prompt_identify_args_v8, prompt_analyze_fallacies_v1, prompt_justify_fallacy_attribution_v1",
            "from .prompts import prompt_identify_args_v9, prompt_analyze_fallacies_v2, prompt_justify_fallacy_attribution_v2, prompt_explore_taxonomy_v1"
        )
        
        # Mettre à jour les références aux prompts
        updated_content = updated_content.replace("prompt_identify_args_v8", "prompt_identify_args_v9")
        updated_content = updated_content.replace("prompt_analyze_fallacies_v1", "prompt_analyze_fallacies_v2")
        updated_content = updated_content.replace("prompt_justify_fallacy_attribution_v1", "prompt_justify_fallacy_attribution_v2")
        
        # Ajouter la nouvelle fonction sémantique pour l'exploration de la taxonomie
        kernel_setup_end = "logger.debug(f\"Fonction {plugin_name}.semantic_JustifyFallacyAttribution ajoutée/mise à jour.\")"
        new_function_registration = """
        # Ajouter la fonction d'exploration de la taxonomie
        try:
            kernel.add_function(
                prompt=prompt_explore_taxonomy_v1,
                plugin_name=plugin_name,
                function_name="semantic_ExploreTaxonomy",
                description="Explore systématiquement la taxonomie des sophismes.",
                prompt_execution_settings=default_settings
            )
            logger.debug(f"Fonction {plugin_name}.semantic_ExploreTaxonomy ajoutée/mise à jour.")
        except ValueError as ve:
            logger.warning(f"Problème ajout/MàJ semantic_ExploreTaxonomy: {ve}")
        """
        updated_content = updated_content.replace(kernel_setup_end, kernel_setup_end + new_function_registration)
        
        # Mettre à jour les instructions système
        instructions_start = "INFORMAL_AGENT_INSTRUCTIONS_V14_TEMPLATE = \"\"\""
        instructions_end = "\"\"\"\n\nINFORMAL_AGENT_INSTRUCTIONS = INFORMAL_AGENT_INSTRUCTIONS_V14_TEMPLATE.format(ROOT_PK=0)"
        
        improved_instructions = """
Votre Rôle: Spécialiste en analyse rhétorique informelle. Vous identifiez les arguments et analysez les sophismes en utilisant une taxonomie externe (via CSV).
Racine de la Taxonomie des Sophismes: PK={ROOT_PK}

**Fonctions Outils Disponibles:**
* `StateManager.*`: Fonctions pour lire et écrire dans l'état partagé (ex: `get_current_state_snapshot`, `add_identified_argument`, `add_identified_fallacy`, `add_answer`). **Utilisez ces fonctions pour enregistrer vos résultats.**
* `InformalAnalyzer.semantic_IdentifyArguments(input: str)`: Fonction sémantique (LLM) pour extraire les arguments d'un texte.
* `InformalAnalyzer.semantic_AnalyzeFallacies(input: str)`: Fonction sémantique (LLM) pour analyser les sophismes dans un argument.
* `InformalAnalyzer.semantic_JustifyFallacyAttribution(argument: str, fallacy_type: str, fallacy_definition: str)`: Fonction sémantique (LLM) pour justifier l'attribution d'un sophisme.
* `InformalAnalyzer.semantic_ExploreTaxonomy(input: str)`: Fonction sémantique (LLM) pour explorer systématiquement la taxonomie.
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
    3.  Appeler `InformalAnalyzer.semantic_JustifyFallacyAttribution` avec l'argument, le type de sophisme et sa définition.
    4.  Si label OK, appeler `StateManager.add_identified_fallacy(fallacy_type=\\\"[label trouvé]\\\", justification=\\\"...\\\", target_argument_id=\\\"[arg_id]\\\")`. Noter le `fallacy_id`.
    5.  Appeler `StateManager.add_answer` pour la tâche `[task_id reçu]`, avec confirmation (PK, label, arg_id, fallacy_id) ou message d'erreur si étape 1 échoue. Utiliser IDs pertinents (`fallacy_id`, `arg_id`) comme `source_ids`.

* **Tâche "Analyser sophismes dans argument [arg_id]":**
    1.  Récupérer le texte de l'argument depuis l'état partagé.
    2.  Appeler `InformalAnalyzer.semantic_ExploreTaxonomy(input=argument_text)` pour explorer systématiquement la taxonomie.
    3.  Pour chaque catégorie pertinente identifiée, explorer les sous-catégories via `InformalAnalyzer.explore_fallacy_hierarchy`.
    4.  Pour chaque sophisme potentiellement applicable:
       - Obtenir ses détails complets via `InformalAnalyzer.get_fallacy_details`
       - Appeler `InformalAnalyzer.semantic_JustifyFallacyAttribution` pour évaluer et justifier l'attribution
       - Si pertinent, attribuer le sophisme avec la justification détaillée
    5.  Viser à identifier au moins 2-3 sophismes différents par argument quand c'est pertinent.
    6.  Appeler `StateManager.add_answer` avec un résumé des sophismes identifiés et le processus d'exploration suivi.

* **Si Tâche Inconnue/Pas Claire:** Signaler l'incompréhension via `StateManager.add_answer`.

**Directives pour l'Exploration de la Taxonomie:**
- Explorez systématiquement la taxonomie en profondeur, pas seulement les premiers niveaux.
- Utilisez une approche "top-down": commencez par les grandes catégories, puis explorez les sous-catégories pertinentes.
- Pour chaque argument, considérez au moins 5 branches différentes de la taxonomie.
- Pour chaque branche, descendez jusqu'aux niveaux les plus profonds (au moins niveau 3-4).
- Ne vous limitez pas aux sophismes les plus évidents ou les plus connus.
- Documentez votre processus d'exploration dans vos réponses.

**Directives pour les Justifications:**
- Vos justifications doivent être détaillées (au moins 150 mots au total).
- Expliquez clairement le mécanisme du sophisme (au moins 50 mots).
- Montrez précisément comment l'argument correspond à ce type de sophisme (au moins 50 mots).
- Incluez toujours des citations spécifiques de l'argument qui illustrent le sophisme (utilisez des guillemets).
- Fournissez un exemple similaire pour clarifier (au moins 30 mots).
- Expliquez l'impact de ce sophisme sur la validité de l'argument (au moins 30 mots).
- Évitez les justifications vagues ou génériques.

**Important:** Toujours utiliser le `task_id` fourni par le PM pour `StateManager.add_answer`. Gérer les erreurs potentielles des appels de fonction (vérifier `error` dans JSON retourné par les fonctions natives, ou si une fonction retourne `FUNC_ERROR:`).
"""
        
        # Remplacer les instructions dans le contenu original
        start_idx = original_content.find(instructions_start) + len(instructions_start)
        end_idx = original_content.find(instructions_end)
        updated_content = original_content[:start_idx] + improved_instructions + original_content[end_idx:]
        
        # Mettre à jour la version des instructions
        updated_content = updated_content.replace("INFORMAL_AGENT_INSTRUCTIONS_V14_TEMPLATE", "INFORMAL_AGENT_INSTRUCTIONS_V15_TEMPLATE")
        updated_content = updated_content.replace("INFORMAL_AGENT_INSTRUCTIONS = INFORMAL_AGENT_INSTRUCTIONS_V14_TEMPLATE", "INFORMAL_AGENT_INSTRUCTIONS = INFORMAL_AGENT_INSTRUCTIONS_V15_TEMPLATE")
        updated_content = updated_content.replace("Instructions Système INFORMAL_AGENT_INSTRUCTIONS (V14)", "Instructions Système INFORMAL_AGENT_INSTRUCTIONS (V15)")
        
        # Sauvegarder le nouveau contenu
        with open(defs_path, "w", encoding="utf-8") as f:
            f.write(updated_content)
        
        logger.info(f"Instructions améliorées et sauvegardées dans {defs_path}")
        
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'amélioration des instructions: {e}")
        return False
async def test_improved_agent():
    """
    Teste l'agent Informel amélioré.
    """
    logger.info("Test de l'agent Informel amélioré...")
    
    script_path = Path("test_informal_agent.py")
    if not script_path.exists():
        logger.error(f"Script de test de l'agent non trouvé: {script_path}")
        return False
    
    try:
        # Exécuter le script de test
        import subprocess
        
        result = subprocess.run(
            ["python", script_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        for line in result.stdout.splitlines():
            logger.info(f"[TEST] {line}")
        
        if result.stderr:
            for line in result.stderr.splitlines():
                logger.warning(f"[TEST ERROR] {line}")
        
        logger.info("Test de l'agent Informel amélioré terminé.")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Erreur lors du test de l'agent: {e}")
        if e.stdout:
            for line in e.stdout.splitlines():
                logger.info(f"[TEST] {line}")
        if e.stderr:
            for line in e.stderr.splitlines():
                logger.error(f"[TEST ERROR] {line}")
        return False
    except Exception as e:
        logger.error(f"Erreur lors du test de l'agent: {e}")
        return False

def create_documentation():
    """
    Crée une documentation des améliorations apportées.
    """
    logger.info("Création de la documentation des améliorations...")
    
    doc_path = Path("utils/informal_optimization/documentation_v2.md")
    
    try:
        documentation = """# Documentation des Améliorations de l'Agent Informel (V2)

## Introduction

Ce document présente les améliorations apportées à l'agent Informel suite à l'analyse des traces de conversation. Ces améliorations visent à optimiser sa contribution à la conversation en utilisant au mieux la taxonomie des sophismes fournie.

## Problèmes Identifiés dans l'Analyse des Traces

L'analyse des traces de conversation de l'agent Informel a révélé plusieurs problèmes:

1. **Identification des arguments**: Les arguments identifiés étaient souvent trop longs et manquaient de précision.
2. **Exploration de la taxonomie**: L'agent n'explorait pas suffisamment en profondeur la taxonomie des sophismes.
3. **Diversité des sophismes**: L'agent utilisait un nombre limité de types de sophismes.
4. **Qualité des justifications**: Les justifications manquaient souvent de détails, d'exemples et d'explications.
5. **Processus d'analyse**: L'agent ne disposait pas d'un workflow structuré pour analyser les sophismes dans un argument.

## Améliorations Apportées

### 1. Prompts d'Identification des Arguments (V9)

Le prompt d'identification des arguments a été amélioré pour:

- Définir plus clairement les critères d'un bon argument
- Encourager la formulation d'arguments plus précis et concis (10-20 mots)
- Demander explicitement de séparer les idées complexes en plusieurs arguments distincts

**Ajouts spécifiques**:
- Critère supplémentaire: "Représenter une seule idée ou affirmation à la fois"
- Directive supplémentaire: "Séparez les idées complexes en plusieurs arguments distincts"

### 2. Prompts d'Analyse des Sophismes (V2)

Le prompt d'analyse des sophismes a été amélioré pour:

- Exiger l'exploration systématique d'au moins 5 branches différentes de la taxonomie
- Demander explicitement de considérer les sophismes à tous les niveaux de profondeur
- Viser l'identification d'au moins 2-3 sophismes différents par argument
- Demander la documentation du processus d'exploration

### 3. Prompts de Justification d'Attribution (V2)

Le prompt de justification d'attribution a été amélioré pour:

- Spécifier des exigences minimales de longueur pour chaque partie de la justification
- Demander explicitement des citations entre guillemets
- Exiger une justification complète d'au moins 150 mots

### 4. Nouveau Prompt d'Exploration de la Taxonomie (V1)

Un nouveau prompt a été créé spécifiquement pour l'exploration systématique de la taxonomie:

- Demande l'exploration d'au moins 5 branches différentes
- Exige de descendre jusqu'aux niveaux les plus profonds (au moins niveau 3-4)
- Demande la documentation du processus d'exploration
- Vise l'identification des sophismes potentiellement applicables à l'argument

### 5. Instructions Système Améliorées (V15)

Les instructions système de l'agent ont été améliorées pour:

- Intégrer les nouvelles fonctions sémantiques
- Définir un workflow plus structuré pour l'analyse des sophismes
- Renforcer les directives pour l'exploration de la taxonomie
- Spécifier des exigences plus précises pour les justifications

**Directives pour l'Exploration de la Taxonomie**:
- Explorer au moins 5 branches différentes (au lieu de 3-5)
- Descendre jusqu'aux niveaux 3-4 au minimum
- Documenter systématiquement le processus d'exploration

**Directives pour les Justifications**:
- Longueur totale d'au moins 150 mots
- Explication du mécanisme: au moins 50 mots
- Correspondance avec l'argument: au moins 50 mots
- Exemple similaire: au moins 30 mots
- Impact sur la validité: au moins 30 mots
- Citations spécifiques entre guillemets

## Résultats Attendus

Les améliorations apportées devraient permettre à l'agent Informel de:

1. **Identifier des arguments plus précis et pertinents**
   - Arguments plus concis (10-20 mots)
   - Séparation des idées complexes en arguments distincts

2. **Utiliser une plus grande diversité de sophismes**
   - Exploration d'au moins 5 branches différentes par argument
   - Considération des sophismes à tous les niveaux de profondeur
   - Identification d'au moins 2-3 sophismes différents par argument

3. **Fournir des justifications plus détaillées et convaincantes**
   - Justifications d'au moins 150 mots au total
   - Structure claire avec des exigences minimales pour chaque partie
   - Citations spécifiques entre guillemets
   - Exemples similaires pour clarifier

4. **Suivre un processus d'analyse plus structuré**
   - Exploration systématique de la taxonomie
   - Documentation du processus d'exploration
   - Workflow clair pour l'analyse des sophismes

## Conclusion

Les améliorations apportées à l'agent Informel visent à résoudre les problèmes identifiés dans l'analyse des traces de conversation. En optimisant les prompts, en ajoutant de nouvelles fonctionnalités et en renforçant les directives, nous espérons améliorer significativement la qualité des analyses produites par l'agent.

Pour valider l'efficacité de ces améliorations, il est recommandé de:
1. Exécuter à nouveau les tests sur les mêmes extraits
2. Comparer les résultats avant et après les modifications
3. Évaluer particulièrement la diversité des sophismes identifiés et la qualité des justifications
"""
        
        # Sauvegarder la documentation
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write(documentation)
        
        logger.info(f"Documentation des améliorations créée: {doc_path}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la création de la documentation: {e}")
        return False

async def main():
    """
    Fonction principale du script.
    """
    logger.info("Démarrage des améliorations de l'agent Informel...")
    
    # Créer des sauvegardes des fichiers originaux
    backup_timestamp = backup_original_files()
    
    # Améliorer les prompts
    prompts_improved = improve_prompts()
    
    # Améliorer les instructions
    instructions_improved = improve_instructions()
    
    # Créer la documentation
    documentation_created = create_documentation()
    
    # Tester l'agent amélioré
    if prompts_improved and instructions_improved:
        agent_tested = await test_improved_agent()
    else:
        agent_tested = False
        logger.warning("Impossible de tester l'agent car certaines améliorations ont échoué.")
    
    logger.info("Améliorations de l'agent Informel terminées.")
    logger.info(f"Prompts améliorés: {prompts_improved}")
    logger.info(f"Instructions améliorées: {instructions_improved}")
    logger.info(f"Documentation créée: {documentation_created}")
    logger.info(f"Agent testé: {agent_tested}")

if __name__ == "__main__":
    asyncio.run(main())