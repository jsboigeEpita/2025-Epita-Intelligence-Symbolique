#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de vérification de la qualité des extraits avec un LLM

Ce script vérifie que tous les extraits définis dans extract_sources.json.gz.enc
sont correctement reconstitués et conformes aux attentes en utilisant un LLM
pour évaluer leur qualité, cohérence et pertinence.

Il génère un rapport détaillé des résultats de cette vérification.
"""

import os
import re
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional, Union

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("VerifyExtractsLLM")

# Création d'un handler pour écrire les logs dans un fichier
file_handler = logging.FileHandler("verify_extracts_llm.log")
file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(file_handler)

import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent
from semantic_kernel.contents import AuthorRole
# CORRECTIF COMPATIBILITÉ: Utilisation du module de compatibilité
from autogen.agentchat.contrib.llm_assistant_agent import LLMAssistantAgent
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
        CONFIG_FILE = "C:/dev/2025-Epita-Intelligence-Symbolique/argumentation_analysis/data/extract_sources.json.gz.enc"
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
        
        def load_source_text(source_info):
            """Charge le texte source d'une définition."""
            logger.info(f"Chargement du texte source pour {source_info.get('source_name', 'Source inconnue')}")
            
            # Reconstruire l'URL
            url = reconstruct_url(source_info)
            
            # Simuler le chargement depuis le cache
            source_text = f"Texte source simulé pour {source_info.get('source_name')}"
            return source_text, url
        
        def extract_text_with_markers(source_text, start_marker, end_marker, template_start=None):
            """Extrait le texte avec les marqueurs."""
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
        
        def find_similar_text(text, pattern, context_size=50, max_results=5):
            logger.info(f"Recherche de texte similaire à '{pattern}'")
            return []
        
        def load_extract_definitions_safely(config_file, encryption_key=None, fallback_file=None):
            logger.info(f"Chargement des définitions d'extraits depuis {config_file}")
            try:
                with open(fallback_file or "extract_repair/docs/extract_sources_updated.json", 'r', encoding='utf-8') as f:
                    extract_definitions = json.load(f)
                return extract_definitions, None
            except Exception as e:
                error_msg = f"Erreur lors du chargement des définitions d'extraits: {str(e)}"
                logger.error(error_msg)
                return [], error_msg
        
        def save_extract_definitions_safely(extract_definitions, config_file, encryption_key=None, fallback_file=None):
            logger.info(f"Sauvegarde des définitions d'extraits dans {config_file}")
            try:
                with open(fallback_file or "extract_repair/docs/extract_sources_updated.json", 'w', encoding='utf-8') as f:
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
                    "valid": True,
                    "coherence": 5,
                    "relevance": 4,
                    "integrity": 5,
                    "comments": "Ceci est une réponse simulée pour les tests."
                }
                return ChatMessageContent(role=AuthorRole.ASSISTANT, content=json.dumps(response))
            
            def instantiate_prompt_execution_settings(self):
                """Méthode requise par Semantic Kernel."""
                logger.info("Création des paramètres d'exécution de prompt simulés")
                return {}
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Imports depuis les modules du projet
import sys
# Ajouter le répertoire parent au chemin d'importation
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
# Instructions pour l'agent d'évaluation des extraits
EVALUATION_AGENT_INSTRUCTIONS = """
Vous êtes un agent spécialisé dans l'évaluation de la qualité des extraits de texte.

Votre tâche est d'analyser un extrait de texte et de déterminer s'il est cohérent, pertinent et complet.

Processus à suivre :
1. Analyser l'extrait fourni
2. Vérifier sa cohérence interne (l'extrait a-t-il un sens complet ?)
3. Vérifier sa pertinence par rapport au sujet indiqué
4. Vérifier son intégrité (l'extrait semble-t-il tronqué ou incomplet ?)

Critères d'évaluation :
- L'extrait doit avoir un début et une fin clairs
- L'extrait doit être compréhensible en lui-même
- L'extrait doit correspondre au sujet indiqué
- L'extrait ne doit pas être tronqué au milieu d'une phrase ou d'une idée

Répondez au format JSON avec les champs suivants :
- valid: true/false (l'extrait est-il valide ?)
- coherence: 1-5 (niveau de cohérence interne)
- relevance: 1-5 (niveau de pertinence par rapport au sujet)
- integrity: 1-5 (niveau d'intégrité de l'extrait)
- comments: commentaires sur l'extrait
"""

async def setup_evaluation_agent(llm_service):
    """Configure l'agent d'évaluation des extraits."""
    logger.info("Configuration de l'agent d'évaluation...")
    
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
        evaluation_agent = LLMAssistantAgent(
            kernel=kernel,
            service=llm_service,
            name="EvaluationAgent",
            instructions=EVALUATION_AGENT_INSTRUCTIONS,
            arguments=KernelArguments(settings=prompt_exec_settings)
        )
        logger.info("Agent d'évaluation créé")
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'agent d'évaluation: {e}")
        raise
    
    logger.info("Agent configuré.")
    return kernel, evaluation_agent

async def evaluate_extract(
    evaluation_agent: ChatCompletionAgent,
    source_info: Dict[str, Any],
    extract_info: Dict[str, Any],
    extracted_text: str
) -> Dict[str, Any]:
    """Évalue un extrait à l'aide d'un LLM."""
    source_name = source_info.get("source_name", "Source inconnue")
    extract_name = extract_info.get("extract_name", "Extrait inconnu")
    extract_subject = extract_info.get("extract_subject", "Sujet non spécifié")
    
    logger.info(f"Évaluation de l'extrait '{extract_name}' de la source '{source_name}'...")
    
    # Préparation du prompt pour l'agent d'évaluation
    evaluation_prompt = f"""
    Évaluez la qualité de cet extrait de texte.
    
    SOURCE: {source_name}
    EXTRAIT: {extract_name}
    SUJET: {extract_subject}
    
    TEXTE EXTRAIT:
    {extracted_text}
    
    Analysez cet extrait selon les critères suivants:
    1. Cohérence interne: l'extrait a-t-il un sens complet?
    2. Pertinence: l'extrait correspond-il au sujet indiqué?
    3. Intégrité: l'extrait est-il complet ou semble-t-il tronqué?
    
    Répondez au format JSON avec les champs:
    - valid: true/false (l'extrait est-il valide?)
    - coherence: 1-5 (niveau de cohérence interne)
    - relevance: 1-5 (niveau de pertinence par rapport au sujet)
    - integrity: 1-5 (niveau d'intégrité de l'extrait)
    - comments: commentaires sur l'extrait
    """
    
    # Utiliser invoke() avec le prompt
    evaluation_content = ""
    try:
        logger.info(f"Invocation de l'agent d'évaluation pour l'extrait '{extract_name}'...")
        # Invoquer l'agent avec le prompt
        async_gen = evaluation_agent.invoke(evaluation_prompt)
        logger.info(f"Générateur asynchrone obtenu, itération sur les chunks...")
        # Itérer sur le générateur asynchrone
        chunk_count = 0
        async for chunk in async_gen:
            chunk_count += 1
            logger.info(f"Chunk {chunk_count} reçu: {type(chunk)}")
            if hasattr(chunk, 'content') and chunk.content:
                evaluation_content = chunk.content
                logger.info(f"Contenu extrait du chunk: {evaluation_content[:100]}...")
                break  # Prendre seulement la première réponse complète
        logger.info(f"Itération terminée, {chunk_count} chunks traités")
    except Exception as e:
        logger.error(f"Erreur lors de l'invocation de l'agent d'évaluation: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        evaluation_content = f"Erreur: {str(e)}"
    
    # Extraire la réponse JSON de l'agent
    try:
        # Rechercher un bloc JSON dans la réponse
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', evaluation_content)
        if json_match:
            evaluation_json = json.loads(json_match.group(1))
        else:
            # Essayer de parser directement la réponse
            evaluation_json = json.loads(evaluation_content)
    except json.JSONDecodeError:
        # Si le JSON n'est pas valide, essayer d'extraire les informations avec des regex
        valid_match = re.search(r'"valid"\s*:\s*(true|false)', evaluation_content)
        coherence_match = re.search(r'"coherence"\s*:\s*(\d+)', evaluation_content)
        relevance_match = re.search(r'"relevance"\s*:\s*(\d+)', evaluation_content)
        integrity_match = re.search(r'"integrity"\s*:\s*(\d+)', evaluation_content)
        comments_match = re.search(r'"comments"\s*:\s*"([^"]*)"', evaluation_content)
        
        evaluation_json = {
            "valid": valid_match.group(1).lower() == "true" if valid_match else False,
            "coherence": int(coherence_match.group(1)) if coherence_match else 0,
            "relevance": int(relevance_match.group(1)) if relevance_match else 0,
            "integrity": int(integrity_match.group(1)) if integrity_match else 0,
            "comments": comments_match.group(1) if comments_match else "Commentaires non disponibles"
        }
    
    # Récupérer les résultats de l'évaluation
    is_valid = evaluation_json.get("valid", False)
    coherence = evaluation_json.get("coherence", 0)
    relevance = evaluation_json.get("relevance", 0)
    integrity = evaluation_json.get("integrity", 0)
    comments = evaluation_json.get("comments", "Aucun commentaire fourni")
    
    # Créer le résultat de l'évaluation
    result = {
        "source_name": source_name,
        "extract_name": extract_name,
        "extract_subject": extract_subject,
        "status": "valid" if is_valid else "invalid",
        "coherence": coherence,
        "relevance": relevance,
        "integrity": integrity,
        "comments": comments,
        "extracted_length": len(extracted_text)
    }
    
    logger.info(f"Évaluation terminée pour l'extrait '{extract_name}': {result['status']}")
    return result
async def verify_extracts_with_llm(extract_definitions: List[Dict[str, Any]], llm_service) -> List[Dict[str, Any]]:
    """Vérifie tous les extraits à l'aide d'un LLM."""
    logger.info("Initialisation de la vérification des extraits avec LLM...")
    
    # Configurer l'agent d'évaluation
    kernel, evaluation_agent = await setup_evaluation_agent(llm_service)
    
    # Liste pour stocker les résultats
    results = []
    
    # Parcourir toutes les sources et leurs extraits
    for source_idx, source_info in enumerate(extract_definitions):
        source_name = source_info.get("source_name", f"Source #{source_idx}")
        logger.info(f"Analyse de la source '{source_name}'...")
        
        # Chargement du texte source
        source_text, url = load_source_text(source_info)
        if not source_text:
            logger.error(f"Impossible de charger le texte source pour '{source_name}': {url}")
            continue
        
        extracts = source_info.get("extracts", [])
        for extract_idx, extract_info in enumerate(extracts):
            extract_name = extract_info.get("extract_name", f"Extrait #{extract_idx}")
            start_marker = extract_info.get("start_marker", "")
            end_marker = extract_info.get("end_marker", "")
            template_start = extract_info.get("template_start", "")
            
            logger.info(f"Analyse de l'extrait '{extract_name}'...")
            
            # Extraction du texte avec les marqueurs
            extracted_text, status, start_found, end_found = extract_text_with_markers(
                source_text, start_marker, end_marker, template_start
            )
            
            # Si l'extraction a échoué, enregistrer l'erreur et passer à l'extrait suivant
            if not (start_found and end_found):
                error_message = "Marqueurs introuvables: "
                if not start_found and not end_found:
                    error_message += "les deux marqueurs sont introuvables."
                elif not start_found:
                    error_message += "le marqueur de début est introuvable."
                else:
                    error_message += "le marqueur de fin est introuvable."
                
                results.append({
                    "source_name": source_name,
                    "extract_name": extract_name,
                    "status": "error",
                    "message": error_message,
                    "start_found": start_found,
                    "end_found": end_found
                })
                continue
            
            # Si l'extraction a réussi, évaluer l'extrait avec le LLM
            result = await evaluate_extract(
                evaluation_agent, source_info, extract_info, extracted_text
            )
            
            results.append(result)
    
    logger.info(f"Vérification terminée. {len(results)} résultats obtenus.")
    return results

def generate_report(results: List[Dict[str, Any]], output_file: str = "verify_extracts_llm_report.html") -> None:
    """Génère un rapport HTML des résultats de la vérification."""
    logger.info(f"Génération du rapport dans '{output_file}'...")
    
    # Compter les différents statuts
    status_counts = {
        "valid": 0,
        "invalid": 0,
        "error": 0
    }
    
    # Calculer les scores moyens
    total_coherence = 0
    total_relevance = 0
    total_integrity = 0
    valid_count = 0
    
    for result in results:
        status = result.get("status", "error")
        if status in status_counts:
            status_counts[status] += 1
        
        # Calculer les scores moyens pour les extraits valides et invalides (mais pas les erreurs)
        if status != "error":
            total_coherence += result.get("coherence", 0)
            total_relevance += result.get("relevance", 0)
            total_integrity += result.get("integrity", 0)
            valid_count += 1
    
    # Calculer les moyennes
    avg_coherence = total_coherence / valid_count if valid_count > 0 else 0
    avg_relevance = total_relevance / valid_count if valid_count > 0 else 0
    avg_integrity = total_integrity / valid_count if valid_count > 0 else 0
    
    # Générer le contenu HTML
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Rapport de vérification des extraits avec LLM</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2, h3 {{ color: #333; }}
            .summary {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .valid {{ color: green; }}
            .invalid {{ color: orange; }}
            .error {{ color: red; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .details {{ margin-top: 5px; font-size: 0.9em; color: #666; }}
            .scores {{ margin-top: 10px; padding: 10px; background-color: #e8f4f8; border-radius: 5px; }}
            .score-bar {{ height: 15px; background-color: #4CAF50; border-radius: 2px; margin-top: 5px; }}
            .score-container {{ width: 100px; background-color: #f1f1f1; border-radius: 2px; }}
        </style>
    </head>
    <body>
        <h1>Rapport de vérification des extraits avec LLM</h1>
        
        <div class="summary">
            <h2>Résumé</h2>
            <p>Total des extraits vérifiés: <strong>{len(results)}</strong></p>
            <p>Extraits valides: <strong class="valid">{status_counts["valid"]}</strong></p>
            <p>Extraits invalides: <strong class="invalid">{status_counts["invalid"]}</strong></p>
            <p>Erreurs: <strong class="error">{status_counts["error"]}</strong></p>
            
            <div class="scores">
                <h3>Scores moyens</h3>
                <p>Cohérence: <strong>{avg_coherence:.2f}/5</strong></p>
                <div class="score-container">
                    <div class="score-bar" style="width: {avg_coherence*20}%;"></div>
                </div>
                <p>Pertinence: <strong>{avg_relevance:.2f}/5</strong></p>
                <div class="score-container">
                    <div class="score-bar" style="width: {avg_relevance*20}%;"></div>
                </div>
                <p>Intégrité: <strong>{avg_integrity:.2f}/5</strong></p>
                <div class="score-container">
                    <div class="score-bar" style="width: {avg_integrity*20}%;"></div>
                </div>
            </div>
        </div>
        
        <h2>Détails des vérifications</h2>
        <table>
            <tr>
                <th>Source</th>
                <th>Extrait</th>
                <th>Statut</th>
                <th>Scores</th>
                <th>Commentaires</th>
            </tr>
    """
    
    # Ajouter une ligne pour chaque résultat
    for result in results:
        source_name = result.get("source_name", "Source inconnue")
        extract_name = result.get("extract_name", "Extrait inconnu")
        status = result.get("status", "error")
        
        # Préparer les scores et commentaires
        scores_html = ""
        comments_html = ""
        
        if status == "error":
            message = result.get("message", "Erreur inconnue")
            scores_html = "N/A"
            comments_html = f"<strong>Erreur:</strong> {message}"
        else:
            coherence = result.get("coherence", 0)
            relevance = result.get("relevance", 0)
            integrity = result.get("integrity", 0)
            comments = result.get("comments", "Aucun commentaire")
            
            scores_html = f"""
            <div class="details">
                <p><strong>Cohérence:</strong> {coherence}/5</p>
                <div class="score-container">
                    <div class="score-bar" style="width: {coherence*20}%;"></div>
                </div>
                <p><strong>Pertinence:</strong> {relevance}/5</p>
                <div class="score-container">
                    <div class="score-bar" style="width: {relevance*20}%;"></div>
                </div>
                <p><strong>Intégrité:</strong> {integrity}/5</p>
                <div class="score-container">
                    <div class="score-bar" style="width: {integrity*20}%;"></div>
                </div>
            </div>
            """
            
            comments_html = comments
        
        html_content += f"""
        <tr class="{status}">
            <td>{source_name}</td>
            <td>{extract_name}</td>
            <td>{status}</td>
            <td>{scores_html}</td>
            <td>{comments_html}</td>
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
# La fonction main() et la section if __name__ == "__main__": ont été déplacées
# vers argumentation_analysis/scripts/run_verify_extracts_llm.py

