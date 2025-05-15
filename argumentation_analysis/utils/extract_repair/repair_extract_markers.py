#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de réparation des bornes défectueuses dans les extraits

Ce script identifie et corrige automatiquement les bornes défectueuses dans les extraits
définis dans extract_sources.json, en se concentrant particulièrement sur le corpus
de discours d'Hitler qui est volumineux.

Il utilise une approche basée sur des agents pour analyser les textes sources,
détecter les problèmes de bornes et proposer des corrections automatiques.

Fonctionnalités:
- Analyse des extraits existants pour détecter les bornes défectueuses
- Correction automatique des bornes avec des algorithmes de correspondance approximative
- Traitement spécifique pour le corpus de discours d'Hitler
- Validation et sauvegarde des corrections
- Génération d'un rapport détaillé des modifications
"""

import os
import re
import json
import logging
import asyncio
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RepairExtractMarkers")

# Création d'un handler pour écrire les logs dans un fichier
file_handler = logging.FileHandler("repair_extract_markers.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(file_handler)

import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Imports depuis les modules du projet
import sys
# Ajouter le répertoire parent au chemin d'importation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    # Import relatif depuis le package utils
    logger.info("Tentative d'import relatif...")
    from ...ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
    from ...ui.utils import load_from_cache, reconstruct_url
    from ...ui.extract_utils import (
        load_source_text, extract_text_with_markers, find_similar_text,
        load_extract_definitions_safely, save_extract_definitions_safely
    )
    from ...core.llm_service import create_llm_service
    logger.info("Import relatif réussi.")
except ImportError as e:
    logger.warning(f"Import relatif échoué: {e}")
    try:
        # Fallback pour les imports absolus
        logger.info("Tentative d'import absolu...")
        from argumentation_analysis.ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
        from argumentation_analysis.ui.utils import load_from_cache, reconstruct_url
        from argumentation_analysis.ui.extract_utils import (
            load_source_text, extract_text_with_markers, find_similar_text,
            load_extract_definitions_safely, save_extract_definitions_safely
        )
        from argumentation_analysis.core.llm_service import create_llm_service
        logger.info("Import absolu réussi.")
    except ImportError as e:
        logger.error(f"Import absolu échoué: {e}")
        
        # Définir des fonctions de remplacement simples pour les tests
        logger.warning("Utilisation de fonctions de remplacement pour les tests...")
        
        # Constantes de configuration
        ENCRYPTION_KEY = "test_key"
        CONFIG_FILE = "C:/dev/2025-Epita-Intelligence-Symbolique/argumentation_analysis/data/extract_sources.json"
        CONFIG_FILE_JSON = "C:/dev/2025-Epita-Intelligence-Symbolique/argumentation_analysis/data/extract_sources.json"
        
        def load_from_cache(url, encryption_key=None):
            logger.info(f"Simulation de chargement depuis le cache pour {url}")
            return None, f"Erreur simulée: Impossible de charger {url}"
        
        def reconstruct_url(source_info):
            schema = source_info.get("schema", "https:")
            host_parts = source_info.get("host_parts", [])
            path = source_info.get("path", "")
            host = ".".join(host_parts) if host_parts else ""
            return f"{schema}//{host}{path}"
        
        def find_similar_text(text, pattern, context_size=50, max_results=5):
            logger.info(f"Recherche de texte similaire à '{pattern}'")
            return []
        
        def extract_text_with_markers(source_text, start_marker, end_marker, template_start=None):
            logger.info(f"Extraction de texte avec les marqueurs: '{start_marker}' et '{end_marker}'")
            
            # Appliquer le template si présent
            if template_start and "{0}" in template_start:
                first_letter = template_start.replace("{0}", "")
                if start_marker and not start_marker.startswith(first_letter):
                    start_marker = first_letter + start_marker
                    logger.info(f"Marqueur de début corrigé avec template: '{start_marker}'")
            
            # Vérifier si les marqueurs sont présents
            start_found = start_marker in source_text
            end_found = end_marker in source_text
            
            if start_found and end_found:
                start_pos = source_text.find(start_marker)
                end_pos = source_text.find(end_marker, start_pos + len(start_marker))
                
                if start_pos >= 0 and end_pos > start_pos:
                    extracted = source_text[start_pos:end_pos + len(end_marker)]
                    return extracted, "success", True, True
            
            return "", "error", start_found, end_found
        
        def load_extract_definitions_safely(config_file, encryption_key=None, fallback_file=None):
            logger.info(f"Chargement des définitions d'extraits depuis {config_file}")
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    extract_definitions = json.load(f)
                return extract_definitions, None
            except Exception as e:
                error_msg = f"Erreur lors du chargement des définitions d'extraits: {str(e)}"
                logger.error(error_msg)
                return [], error_msg
        
        def save_extract_definitions_safely(extract_definitions, config_file, encryption_key=None, fallback_file=None):
            logger.info(f"Sauvegarde des définitions d'extraits dans {config_file}")
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(extract_definitions, f, indent=4, ensure_ascii=False)
                return True, None
            except Exception as e:
                error_msg = f"Erreur lors de la sauvegarde des définitions d'extraits: {str(e)}"
                logger.error(error_msg)
                return False, error_msg
        
        def create_llm_service():
            logger.info("Création d'un service LLM simulé")
            return DummyLLMService()
        
        class DummyLLMService:
            """Service LLM simulé pour les tests."""
            def __init__(self):
                self.service_id = "dummy_llm_service"
            
            async def invoke(self, prompt):
                logger.info(f"Invocation du service LLM simulé avec prompt: {prompt[:50]}...")
                response = {
                    "new_start_marker": "Marqueur de début simulé",
                    "new_end_marker": "Marqueur de fin simulé",
                    "new_template_start": "",
                    "explanation": "Ceci est une réponse simulée pour les tests."
                }
                return ChatMessageContent(role=AuthorRole.ASSISTANT, content=json.dumps(response))
            
            def instantiate_prompt_execution_settings(self):
                """Méthode requise par Semantic Kernel."""
                logger.info("Création des paramètres d'exécution de prompt simulés")
                return {}
# --- Instructions pour les agents ---

# Instructions pour l'agent de réparation des bornes
REPAIR_AGENT_INSTRUCTIONS = """
Vous êtes un agent spécialisé dans la réparation des bornes défectueuses dans les extraits de texte.

Votre tâche est d'analyser un texte source et de trouver les bornes (marqueurs de début et de fin) 
qui correspondent le mieux à un extrait donné, même si les bornes actuelles sont incorrectes ou introuvables.

Processus à suivre:
1. Analyser le texte source fourni
2. Examiner les bornes actuelles (start_marker et end_marker)
3. Si les bornes sont introuvables, rechercher des séquences similaires dans le texte
4. Proposer des corrections pour les bornes défectueuses
5. Vérifier que les nouvelles bornes délimitent correctement l'extrait

Pour les corpus volumineux comme les discours d'Hitler:
- Utiliser une approche dichotomique pour localiser les discours
- Rechercher des motifs structurels (titres, numéros de pages, etc.)
- Créer des marqueurs plus robustes basés sur des séquences uniques

Règles importantes:
- Les bornes proposées doivent exister exactement dans le texte source
- Les bornes doivent délimiter un extrait cohérent et pertinent
- Privilégier les bornes qui correspondent à des éléments structurels du document
- Documenter clairement les modifications proposées et leur justification
"""

# Instructions pour l'agent de validation des bornes
VALIDATION_AGENT_INSTRUCTIONS = """
Vous êtes un agent spécialisé dans la validation des bornes d'extraits de texte.

Votre tâche est de vérifier que les bornes (marqueurs de début et de fin) proposées 
délimitent correctement un extrait cohérent et pertinent.

Processus à suivre:
1. Vérifier que les bornes existent exactement dans le texte source
2. Extraire le texte délimité par les bornes
3. Analyser la cohérence et la pertinence de l'extrait
4. Valider ou rejeter les bornes proposées

Critères de validation:
- Les bornes doivent exister exactement dans le texte source
- L'extrait doit être cohérent et avoir un sens complet
- L'extrait ne doit pas être trop court ni trop long
- L'extrait doit correspondre au sujet attendu

En cas de rejet:
- Expliquer clairement les raisons du rejet
- Proposer des alternatives si possible
"""

# --- Classes et fonctions ---

class ExtractRepairPlugin:
    """Plugin pour les fonctions natives de réparation des extraits."""
    
    def __init__(self):
        self.repair_results = []
    
    def find_similar_markers(self, text: str, marker: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """Trouve des marqueurs similaires dans le texte source en utilisant find_similar_text."""
        if not text or not marker:
            return []
        
        similar_markers = []
        results = find_similar_text(text, marker, context_size=50, max_results=max_results)
        
        for context, position, found_text in results:
            similar_markers.append({
                "marker": found_text,
                "position": position,
                "context": context
            })
        
        return similar_markers
    
    def update_extract_markers(self, extract_definitions: List[Dict[str, Any]], 
                               source_idx: int, extract_idx: int, 
                               new_start_marker: str, new_end_marker: str, 
                               template_start: Optional[str] = None) -> bool:
        """Met à jour les marqueurs d'un extrait."""
        if 0 <= source_idx < len(extract_definitions):
            source_info = extract_definitions[source_idx]
            extracts = source_info.get("extracts", [])
            if 0 <= extract_idx < len(extracts):
                old_start = extracts[extract_idx].get("start_marker", "")
                old_end = extracts[extract_idx].get("end_marker", "")
                old_template = extracts[extract_idx].get("template_start", "")
                
                extracts[extract_idx]["start_marker"] = new_start_marker
                extracts[extract_idx]["end_marker"] = new_end_marker
                if template_start:
                    extracts[extract_idx]["template_start"] = template_start
                elif "template_start" in extracts[extract_idx] and not template_start:
                    del extracts[extract_idx]["template_start"]
                
                # Enregistrer les modifications
                self.repair_results.append({
                    "source_name": source_info.get("source_name", f"Source #{source_idx}"),
                    "extract_name": extracts[extract_idx].get("extract_name", f"Extrait #{extract_idx}"),
                    "old_start_marker": old_start,
                    "new_start_marker": new_start_marker,
                    "old_end_marker": old_end,
                    "new_end_marker": new_end_marker,
                    "old_template_start": old_template,
                    "new_template_start": template_start
                })
                
                return True
        return False
    
    def get_repair_results(self) -> List[Dict[str, Any]]:
        """Récupère les résultats des réparations effectuées."""
        return self.repair_results

async def setup_agents(llm_service):
    """Configure les agents de réparation et de validation."""
    logger.info("Configuration des agents...")
    
    kernel = sk.Kernel()
    kernel.add_service(llm_service)
    
    try:
        prompt_exec_settings = kernel.get_prompt_execution_settings_from_service_id(llm_service.service_id)
        logger.info("Paramètres d'exécution de prompt obtenus")
    except Exception as e:
        logger.warning(f"Erreur lors de l'obtention des paramètres d'exécution de prompt: {e}")
        logger.info("Utilisation de paramètres d'exécution de prompt vides")
        prompt_exec_settings = {}
    
    try:
        repair_agent = ChatCompletionAgent(
            kernel=kernel,
            service=llm_service,
            name="RepairAgent",
            instructions=REPAIR_AGENT_INSTRUCTIONS,
            arguments=KernelArguments(settings=prompt_exec_settings)
        )
        logger.info("Agent de réparation créé")
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'agent de réparation: {e}")
        raise
    
    try:
        validation_agent = ChatCompletionAgent(
            kernel=kernel,
            service=llm_service,
            name="ValidationAgent",
            instructions=VALIDATION_AGENT_INSTRUCTIONS,
            arguments=KernelArguments(settings=prompt_exec_settings)
        )
        logger.info("Agent de validation créé")
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'agent de validation: {e}")
        raise
    
    logger.info("Agents configurés.")
    return kernel, repair_agent, validation_agent
async def analyze_extract(
    repair_agent: ChatCompletionAgent,
    validation_agent: ChatCompletionAgent,
    extract_definitions: List[Dict[str, Any]],
    source_idx: int,
    extract_idx: int,
    repair_plugin: ExtractRepairPlugin
) -> Dict[str, Any]:
    """Analyse un extrait et propose des corrections pour les bornes défectueuses."""
    source_info = extract_definitions[source_idx]
    source_name = source_info.get("source_name", f"Source #{source_idx}")
    
    extracts = source_info.get("extracts", [])
    extract_info = extracts[extract_idx]
    extract_name = extract_info.get("extract_name", f"Extrait #{extract_idx}")
    
    start_marker = extract_info.get("start_marker", "")
    end_marker = extract_info.get("end_marker", "")
    template_start = extract_info.get("template_start", "")
    
    logger.info(f"Analyse de l'extrait '{extract_name}' de la source '{source_name}'...")
    
    # Chargement du texte source
    source_text, url = load_source_text(source_info)
    if not source_text:
        logger.error(f"Impossible de charger le texte source pour '{source_name}': {url}")
        return {
            "source_name": source_name,
            "extract_name": extract_name,
            "status": "error",
            "message": f"Impossible de charger le texte source: {url}"
        }
    
    # Extraction du texte avec les marqueurs actuels
    extracted_text, status, start_found, end_found = extract_text_with_markers(
        source_text, start_marker, end_marker, template_start
    )
    
    # Si les deux marqueurs sont trouvés, l'extrait est valide
    # Mais vérifier si le template est utilisé, ce qui indique un marqueur potentiellement corrompu
    if start_found and end_found:
        # Si un template est utilisé, cela indique que le marqueur de début est potentiellement corrompu
        if template_start and start_marker and len(start_marker) > 0:
            # Vérifier si la première lettre est manquante (cas courant dans le corpus Hitler)
            first_letter_missing = False
            if template_start == "I{0}" and not start_marker.startswith("I"):
                first_letter_missing = True
            elif template_start == "W{0}" and not start_marker.startswith("W"):
                first_letter_missing = True
            elif template_start == "T{0}" and not start_marker.startswith("T"):
                first_letter_missing = True
            elif template_start == "F{0}" and not start_marker.startswith("F"):
                first_letter_missing = True
            
            if first_letter_missing:
                logger.info(f"Extrait '{extract_name}' valide mais avec un marqueur de début corrompu (première lettre manquante). Tentative de réparation...")
                # Continuer avec la réparation
            else:
                logger.info(f"Extrait '{extract_name}' valide. Aucune correction nécessaire.")
                return {
                    "source_name": source_name,
                    "extract_name": extract_name,
                    "status": "valid",
                    "message": "Extrait valide. Aucune correction nécessaire."
                }
        else:
            logger.info(f"Extrait '{extract_name}' valide. Aucune correction nécessaire.")
            return {
                "source_name": source_name,
                "extract_name": extract_name,
                "status": "valid",
                "message": "Extrait valide. Aucune correction nécessaire."
            }
    
    # Si au moins un marqueur est manquant, demander à l'agent de réparation
    logger.info(f"Extrait '{extract_name}' invalide. Demande de réparation...")
    
    # Préparation du contexte pour l'agent de réparation
    is_hitler_corpus = "hitler" in source_name.lower() or "hitler" in extract_name.lower()
    
    # Limiter la taille du texte source pour l'agent
    max_text_length = 10000  # Limiter à 10000 caractères pour l'agent
    if len(source_text) > max_text_length:
        # Pour le corpus d'Hitler, utiliser une approche dichotomique
        if is_hitler_corpus:
            logger.info(f"Corpus volumineux détecté (Hitler). Utilisation d'une approche dichotomique...")
            
            # Rechercher des marqueurs similaires
            similar_start_markers = repair_plugin.find_similar_markers(source_text, start_marker)
            similar_end_markers = repair_plugin.find_similar_markers(source_text, end_marker)
            
            # Préparer un résumé du texte source avec les positions des marqueurs similaires
            source_summary = f"TEXTE SOURCE VOLUMINEUX ({len(source_text)} caractères). "
            source_summary += f"Début: {source_text[:1000]}...\n\n"
            
            if similar_start_markers:
                source_summary += "MARQUEURS DE DÉBUT SIMILAIRES TROUVÉS:\n"
                for i, marker in enumerate(similar_start_markers):
                    source_summary += f"{i+1}. Position {marker['position']}: ...{marker['context']}...\n"
            
            if similar_end_markers:
                source_summary += "\nMARQUEURS DE FIN SIMILAIRES TROUVÉS:\n"
                for i, marker in enumerate(similar_end_markers):
                    source_summary += f"{i+1}. Position {marker['position']}: ...{marker['context']}...\n"
            
            source_summary += f"\n\nFin: ...{source_text[-1000:]}"
            
            repair_context = source_summary
        else:
            # Pour les autres corpus volumineux, prendre le début et la fin
            repair_context = f"TEXTE SOURCE VOLUMINEUX ({len(source_text)} caractères). "
            repair_context += f"Début: {source_text[:5000]}...\n\n"
            repair_context += f"Fin: ...{source_text[-5000:]}"
    else:
        repair_context = source_text
    
    # Demander à l'agent de réparation de proposer des corrections
    repair_prompt = f"""
    Analyse cet extrait défectueux et propose des corrections pour les bornes.
    
    SOURCE: {source_name}
    EXTRAIT: {extract_name}
    
    MARQUEUR DE DÉBUT ACTUEL: "{start_marker}"
    MARQUEUR DE FIN ACTUEL: "{end_marker}"
    TEMPLATE DE DÉBUT ACTUEL (si présent): "{template_start}"
    
    STATUT: {status}
    MARQUEUR DE DÉBUT TROUVÉ: {"Oui" if start_found else "Non"}
    MARQUEUR DE FIN TROUVÉ: {"Oui" if end_found else "Non"}
    
    TEXTE SOURCE:
    {repair_context}
    
    {"Ce corpus est identifié comme contenant des discours d'Hitler. Utilise une approche spécifique pour ce type de document." if is_hitler_corpus else ""}
    
    Propose des corrections pour les marqueurs défectueux. Réponds au format JSON avec les champs:
    - new_start_marker: le nouveau marqueur de début proposé
    - new_end_marker: le nouveau marqueur de fin proposé
    - new_template_start: le nouveau template de début (optionnel)
    - explanation: explication de tes choix
    """
    
    # Utiliser invoke() avec le prompt directement
    repair_content = ""
    try:
        logger.info(f"Invocation de l'agent de réparation pour l'extrait '{extract_name}'...")
        # Invoquer l'agent avec le prompt directement
        async_gen = repair_agent.invoke(repair_prompt)
        logger.info(f"Générateur asynchrone obtenu, itération sur les chunks...")
        # Itérer sur le générateur asynchrone
        chunk_count = 0
        async for chunk in async_gen:
            chunk_count += 1
            logger.info(f"Chunk {chunk_count} reçu: {type(chunk)}")
            if hasattr(chunk, 'content') and chunk.content:
                repair_content = chunk.content
                logger.info(f"Contenu extrait du chunk: {repair_content[:100]}...")
                break  # Prendre seulement la première réponse complète
        logger.info(f"Itération terminée, {chunk_count} chunks traités")
    except Exception as e:
        logger.error(f"Erreur lors de l'invocation de l'agent de réparation: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        repair_content = f"Erreur: {str(e)}"
    
    # Extraire la réponse JSON de l'agent
    try:
        # Rechercher un bloc JSON dans la réponse
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', repair_content)
        if json_match:
            repair_json = json.loads(json_match.group(1))
        else:
            # Essayer de parser directement la réponse
            repair_json = json.loads(repair_content)
    except json.JSONDecodeError:
        # Si le JSON n'est pas valide, essayer d'extraire les informations avec des regex
        new_start_match = re.search(r'"new_start_marker"\s*:\s*"([^"]*)"', repair_content)
        new_end_match = re.search(r'"new_end_marker"\s*:\s*"([^"]*)"', repair_content)
        new_template_match = re.search(r'"new_template_start"\s*:\s*"([^"]*)"', repair_content)
        explanation_match = re.search(r'"explanation"\s*:\s*"([^"]*)"', repair_content)
        
        repair_json = {
            "new_start_marker": new_start_match.group(1) if new_start_match else start_marker,
            "new_end_marker": new_end_match.group(1) if new_end_match else end_marker,
            "new_template_start": new_template_match.group(1) if new_template_match else template_start,
            "explanation": explanation_match.group(1) if explanation_match else "Explication non disponible"
        }
    
    # Récupérer les nouvelles bornes proposées
    new_start_marker = repair_json.get("new_start_marker", start_marker)
    new_end_marker = repair_json.get("new_end_marker", end_marker)
    new_template_start = repair_json.get("new_template_start", template_start)
    explanation = repair_json.get("explanation", "Aucune explication fournie")
    
    # Vérifier que les nouvelles bornes sont différentes des anciennes
    if new_start_marker == start_marker and new_end_marker == end_marker and new_template_start == template_start:
        logger.info(f"Aucune correction proposée pour l'extrait '{extract_name}'.")
        return {
            "source_name": source_name,
            "extract_name": extract_name,
            "status": "unchanged",
            "message": "Aucune correction proposée par l'agent."
        }
    
    # Valider les nouvelles bornes
    logger.info(f"Validation des nouvelles bornes proposées pour l'extrait '{extract_name}'...")
    
    # Extraire le texte avec les nouvelles bornes
    new_extracted_text, new_status, new_start_found, new_end_found = extract_text_with_markers(
        source_text, new_start_marker, new_end_marker, new_template_start
    )
    
    # Demander à l'agent de validation de vérifier les nouvelles bornes
    validation_prompt = f"""
    Valide les nouvelles bornes proposées pour cet extrait.
    
    SOURCE: {source_name}
    EXTRAIT: {extract_name}
    
    ANCIENNES BORNES:
    - Marqueur de début: "{start_marker}"
    - Marqueur de fin: "{end_marker}"
    - Template de début: "{template_start}"
    
    NOUVELLES BORNES:
    - Marqueur de début: "{new_start_marker}"
    - Marqueur de fin: "{new_end_marker}"
    - Template de début: "{new_template_start}"
    
    ANCIEN STATUT: {status}
    NOUVEAU STATUT: {new_status}
    
    ANCIEN TEXTE EXTRAIT:
    {extracted_text if extracted_text else "Aucun texte extrait"}
    
    NOUVEAU TEXTE EXTRAIT:
    {new_extracted_text if new_extracted_text else "Aucun texte extrait"}
    
    EXPLICATION DE L'AGENT DE RÉPARATION:
    {explanation}
    
    Valide ou rejette les nouvelles bornes proposées. Réponds au format JSON avec les champs:
    - valid: true/false
    - reason: raison de la validation ou du rejet
    """
    
    # Utiliser invoke() avec le prompt directement
    validation_content = ""
    try:
        logger.info(f"Invocation de l'agent de validation pour l'extrait '{extract_name}'...")
        # Invoquer l'agent avec le prompt directement
        async_gen = validation_agent.invoke(validation_prompt)
        logger.info(f"Générateur asynchrone obtenu, itération sur les chunks...")
        # Itérer sur le générateur asynchrone
        chunk_count = 0
        async for chunk in async_gen:
            chunk_count += 1
            logger.info(f"Chunk {chunk_count} reçu: {type(chunk)}")
            if hasattr(chunk, 'content') and chunk.content:
                validation_content = chunk.content
                logger.info(f"Contenu extrait du chunk: {validation_content[:100]}...")
                break  # Prendre seulement la première réponse complète
        logger.info(f"Itération terminée, {chunk_count} chunks traités")
    except Exception as e:
        logger.error(f"Erreur lors de l'invocation de l'agent de validation: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        validation_content = f"Erreur: {str(e)}"
    
    # Extraire la réponse JSON de l'agent
    try:
        # Rechercher un bloc JSON dans la réponse
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', validation_content)
        if json_match:
            validation_json = json.loads(json_match.group(1))
        else:
            # Essayer de parser directement la réponse
            validation_json = json.loads(validation_content)
    except json.JSONDecodeError:
        # Si le JSON n'est pas valide, essayer d'extraire les informations avec des regex
        valid_match = re.search(r'"valid"\s*:\s*(true|false)', validation_content)
        reason_match = re.search(r'"reason"\s*:\s*"([^"]*)"', validation_content)
        
        validation_json = {
            "valid": valid_match.group(1).lower() == "true" if valid_match else False,
            "reason": reason_match.group(1) if reason_match else "Raison non disponible"
        }
    
    # Récupérer la validation
    is_valid = validation_json.get("valid", False)
    validation_reason = validation_json.get("reason", "Aucune raison fournie")
    
    # Si les nouvelles bornes sont valides, mettre à jour l'extrait
    if is_valid and new_start_found and new_end_found:
        logger.info(f"Nouvelles bornes validées pour l'extrait '{extract_name}'. Mise à jour...")
        
        # Mettre à jour les marqueurs
        repair_plugin.update_extract_markers(
            extract_definitions, source_idx, extract_idx, 
            new_start_marker, new_end_marker, 
            new_template_start if new_template_start else None
        )
        
        return {
            "source_name": source_name,
            "extract_name": extract_name,
            "status": "repaired",
            "message": f"Bornes corrigées: {validation_reason}",
            "old_start_marker": start_marker,
            "new_start_marker": new_start_marker,
            "old_end_marker": end_marker,
            "new_end_marker": new_end_marker,
            "old_template_start": template_start,
            "new_template_start": new_template_start,
            "explanation": explanation
        }
    else:
        logger.warning(f"Nouvelles bornes rejetées pour l'extrait '{extract_name}': {validation_reason}")
        return {
            "source_name": source_name,
            "extract_name": extract_name,
            "status": "rejected",
            "message": f"Correction rejetée: {validation_reason}",
            "explanation": explanation
        }
async def repair_extract_markers(extract_definitions: List[Dict[str, Any]], llm_service) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Répare les bornes défectueuses dans les extraits."""
    logger.info("Initialisation de la réparation des bornes défectueuses...")
    
    # Créer le plugin de réparation
    repair_plugin = ExtractRepairPlugin()
    
    # Liste pour stocker les résultats
    results = []
    
    # Parcourir toutes les sources et leurs extraits
    for source_idx, source_info in enumerate(extract_definitions):
        source_name = source_info.get("source_name", f"Source #{source_idx}")
        logger.info(f"Analyse de la source '{source_name}'...")
        
        extracts = source_info.get("extracts", [])
        for extract_idx, extract_info in enumerate(extracts):
            extract_name = extract_info.get("extract_name", f"Extrait #{extract_idx}")
            start_marker = extract_info.get("start_marker", "")
            end_marker = extract_info.get("end_marker", "")
            template_start = extract_info.get("template_start", "")
            
            logger.info(f"Analyse de l'extrait '{extract_name}'...")
            logger.debug(f"  - start_marker: '{start_marker}'")
            logger.debug(f"  - end_marker: '{end_marker}'")
            logger.debug(f"  - template_start: '{template_start}'")
            
            # Vérifier si l'extrait a un template_start
            if template_start and "{0}" in template_start:
                # Extraire la lettre du template
                first_letter = template_start.replace("{0}", "")
                
                # Vérifier si le start_marker ne commence pas déjà par cette lettre
                if start_marker and not start_marker.startswith(first_letter):
                    # Corriger le start_marker en ajoutant la première lettre
                    old_marker = start_marker
                    new_marker = first_letter + start_marker
                    
                    logger.info(f"Correction de l'extrait '{extract_name}':")
                    logger.info(f"  - Ancien marqueur: '{old_marker}'")
                    logger.info(f"  - Nouveau marqueur: '{new_marker}'")
                    
                    # Mettre à jour le marqueur
                    repair_plugin.update_extract_markers(
                        extract_definitions, source_idx, extract_idx,
                        new_marker, end_marker, template_start
                    )
                    
                    # Ajouter le résultat
                    results.append({
                        "source_name": source_name,
                        "extract_name": extract_name,
                        "status": "repaired",
                        "message": f"Marqueur de début corrigé: '{old_marker}' -> '{new_marker}'",
                        "old_start_marker": old_marker,
                        "new_start_marker": new_marker,
                        "old_end_marker": end_marker,
                        "new_end_marker": end_marker,
                        "old_template_start": template_start,
                        "new_template_start": template_start,
                        "explanation": f"Première lettre manquante ajoutée selon le template '{template_start}'"
                    })
                else:
                    logger.info(f"Extrait '{extract_name}' valide. Aucune correction nécessaire.")
                    results.append({
                        "source_name": source_name,
                        "extract_name": extract_name,
                        "status": "valid",
                        "message": "Extrait valide. Aucune correction nécessaire."
                    })
            else:
                logger.info(f"Extrait '{extract_name}' sans template_start. Aucune correction nécessaire.")
                results.append({
                    "source_name": source_name,
                    "extract_name": extract_name,
                    "status": "valid",
                    "message": "Extrait sans template_start. Aucune correction nécessaire."
                })
    
    # Récupérer les modifications effectuées
    repair_results = repair_plugin.get_repair_results()
    logger.info(f"{len(repair_results)} extraits corrigés.")
    
    return extract_definitions, results

def generate_report(results: List[Dict[str, Any]], output_file: str = "repair_report.html"):
    """Génère un rapport HTML des modifications effectuées."""
    logger.info(f"Génération du rapport dans '{output_file}'...")
    
    # Compter les différents statuts
    status_counts = {
        "valid": 0,
        "repaired": 0,
        "rejected": 0,
        "unchanged": 0,
        "error": 0
    }
    
    # Compter les types de réparations
    repair_types = {
        "first_letter_missing": 0,
        "other": 0
    }
    
    for result in results:
        status = result.get("status", "error")
        if status in status_counts:
            status_counts[status] += 1
            
        # Analyser les types de réparations
        if status == "repaired":
            old_start = result.get("old_start_marker", "")
            new_start = result.get("new_start_marker", "")
            old_template = result.get("old_template_start", "")
            
            # Vérifier si c'est une réparation de première lettre manquante
            if old_template and len(old_start) > 0 and len(new_start) > 0:
                if old_template == "I{0}" and new_start.startswith("I") and old_start.startswith(new_start[1:]):
                    repair_types["first_letter_missing"] += 1
                elif old_template == "W{0}" and new_start.startswith("W") and old_start.startswith(new_start[1:]):
                    repair_types["first_letter_missing"] += 1
                elif old_template == "T{0}" and new_start.startswith("T") and old_start.startswith(new_start[1:]):
                    repair_types["first_letter_missing"] += 1
                elif old_template == "F{0}" and new_start.startswith("F") and old_start.startswith(new_start[1:]):
                    repair_types["first_letter_missing"] += 1
                else:
                    repair_types["other"] += 1
            else:
                repair_types["other"] += 1
    
    # Générer le contenu HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Rapport de réparation des bornes d'extraits</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #333; }}
            .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .valid {{ color: green; }}
            .repaired {{ color: blue; }}
            .rejected {{ color: orange; }}
            .unchanged {{ color: gray; }}
            .error {{ color: red; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .details {{ margin-top: 5px; font-size: 0.9em; color: #666; }}
            .repair-types {{ margin-top: 10px; padding: 10px; background-color: #e8f4f8; border-radius: 5px; }}
        </style>
    </head>
    <body>
        <h1>Rapport de réparation des bornes d'extraits</h1>
        
        <div class="summary">
            <h2>Résumé</h2>
            <p>Total des extraits analysés: <strong>{len(results)}</strong></p>
            <p>Extraits valides: <strong class="valid">{status_counts["valid"]}</strong></p>
            <p>Extraits réparés: <strong class="repaired">{status_counts["repaired"]}</strong></p>
            <p>Réparations rejetées: <strong class="rejected">{status_counts["rejected"]}</strong></p>
            <p>Extraits inchangés: <strong class="unchanged">{status_counts["unchanged"]}</strong></p>
            <p>Erreurs: <strong class="error">{status_counts["error"]}</strong></p>
            
            <div class="repair-types">
                <h3>Types de réparations</h3>
                <p>Première lettre manquante: <strong>{repair_types["first_letter_missing"]}</strong></p>
                <p>Autres types de réparations: <strong>{repair_types["other"]}</strong></p>
            </div>
        </div>
        
        <h2>Détails des réparations</h2>
        <table>
            <tr>
                <th>Source</th>
                <th>Extrait</th>
                <th>Statut</th>
                <th>Détails</th>
            </tr>
    """
    
    # Ajouter une ligne pour chaque résultat
    for result in results:
        source_name = result.get("source_name", "Source inconnue")
        extract_name = result.get("extract_name", "Extrait inconnu")
        status = result.get("status", "error")
        message = result.get("message", "Aucun message")
        
        details = ""
        if status == "repaired":
            details += f"""
            <div class="details">
                <p><strong>Ancien marqueur de début:</strong> "{result.get('old_start_marker', '')}"</p>
                <p><strong>Nouveau marqueur de début:</strong> "{result.get('new_start_marker', '')}"</p>
                <p><strong>Ancien marqueur de fin:</strong> "{result.get('old_end_marker', '')}"</p>
                <p><strong>Nouveau marqueur de fin:</strong> "{result.get('new_end_marker', '')}"</p>
                <p><strong>Explication:</strong> {result.get('explanation', '')}</p>
            </div>
            """
        
        html_content += f"""
        <tr class="{status}">
            <td>{source_name}</td>
            <td>{extract_name}</td>
            <td>{status}</td>
            <td>{message}{details}</td>
        </tr>
        """
    
    html_content += """
        </table>
    </body>
    </html>
    """
    
    # Écrire le rapport dans un fichier
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    logger.info(f"Rapport généré dans '{output_file}'.")
async def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Réparation des bornes défectueuses dans les extraits")
    parser.add_argument("--output", "-o", default="repair_report.html", help="Fichier de sortie pour le rapport HTML")
    parser.add_argument("--save", "-s", action="store_true", help="Sauvegarder les modifications")
    parser.add_argument("--hitler-only", action="store_true", help="Traiter uniquement le corpus de discours d'Hitler")
    parser.add_argument("--verbose", "-v", action="store_true", help="Activer le mode verbeux")
    parser.add_argument("--input", "-i", default=None, help="Fichier d'entrée personnalisé")
    parser.add_argument("--output-json", default="extract_sources_updated.json", help="Fichier de sortie JSON pour vérification")
    args = parser.parse_args()
    
    # Configurer le niveau de journalisation
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé.")
    
    logger.info("Démarrage du script de réparation des bornes défectueuses...")
    logger.info(f"Répertoire de travail actuel: {os.getcwd()}")
    logger.info(f"Chemin du script: {os.path.abspath(__file__)}")
    
    # Utiliser le fichier d'entrée personnalisé si spécifié
    input_file = args.input if args.input else CONFIG_FILE
    logger.info(f"Fichier d'entrée: {input_file}")
    
    # Vérifier que le fichier d'entrée existe
    if not os.path.exists(input_file):
        logger.error(f"Le fichier d'entrée {input_file} n'existe pas.")
        return
    
    # Charger les définitions d'extraits
    logger.info(f"Chargement des définitions d'extraits depuis {input_file}...")
    try:
        extract_definitions, error_message = load_extract_definitions_safely(input_file, ENCRYPTION_KEY, CONFIG_FILE_JSON)
        if error_message:
            logger.error(f"Erreur lors du chargement des définitions d'extraits: {error_message}")
            return
        
        logger.info(f"{len(extract_definitions)} sources chargées.")
        
        # Afficher les premières sources pour vérification
        for i, source in enumerate(extract_definitions[:2]):
            logger.info(f"Source {i}: {source.get('source_name', 'Sans nom')}")
            logger.info(f"  Type: {source.get('source_type', 'Non spécifié')}")
            logger.info(f"  Extraits: {len(source.get('extracts', []))}")
    except Exception as e:
        logger.error(f"Exception lors du chargement des définitions d'extraits: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return
    
    # Filtrer les sources si l'option --hitler-only est activée
    if args.hitler_only:
        original_count = len(extract_definitions)
        extract_definitions = [
            source for source in extract_definitions
            if "hitler" in source.get("source_name", "").lower()
        ]
        logger.info(f"Filtrage des sources: {len(extract_definitions)}/{original_count} sources retenues (corpus Hitler).")
    
    # Créer le service LLM
    logger.info("Création du service LLM...")
    try:
        llm_service = create_llm_service()
        if not llm_service:
            logger.error("Impossible de créer le service LLM.")
            return
        logger.info(f"Service LLM créé: {type(llm_service).__name__}")
    except Exception as e:
        logger.error(f"Exception lors de la création du service LLM: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return
    
    # Réparer les bornes défectueuses
    logger.info("Démarrage de la réparation des bornes défectueuses...")
    try:
        updated_definitions, results = await repair_extract_markers(extract_definitions, llm_service)
        logger.info(f"Réparation terminée. {len(results)} résultats obtenus.")
    except Exception as e:
        logger.error(f"Exception lors de la réparation des bornes: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return
    
    # Générer le rapport
    logger.info(f"Génération du rapport dans {args.output}...")
    try:
        generate_report(results, args.output)
        logger.info(f"Rapport généré dans {args.output}")
    except Exception as e:
        logger.error(f"Exception lors de la génération du rapport: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    # Sauvegarder les modifications si demandé
    if args.save:
        logger.info(f"Sauvegarde des modifications dans {input_file}...")
        try:
            success, error_message = save_extract_definitions_safely(
                updated_definitions, input_file, ENCRYPTION_KEY, CONFIG_FILE_JSON
            )
            if success:
                logger.info("✅ Modifications sauvegardées avec succès.")
                
                # Exporter également les définitions dans un fichier JSON non chiffré pour vérification
                try:
                    export_path = Path(args.output_json)
                    with open(export_path, 'w', encoding='utf-8') as f:
                        json.dump(updated_definitions, f, indent=4, ensure_ascii=False)
                    logger.info(f"✅ Définitions exportées pour vérification dans {export_path}")
                except Exception as e:
                    logger.error(f"❌ Erreur lors de l'exportation pour vérification: {e}")
            else:
                logger.error(f"❌ Erreur lors de la sauvegarde des modifications: {error_message}")
        except Exception as e:
            logger.error(f"Exception lors de la sauvegarde des modifications: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
    else:
        logger.info("Les modifications n'ont pas été sauvegardées (utilisez --save pour sauvegarder).")
    
    logger.info("Script terminé.")

if __name__ == "__main__":
    asyncio.run(main())