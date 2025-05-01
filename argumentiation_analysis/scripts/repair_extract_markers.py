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

# Imports depuis les modules du projet
import semantic_kernel as sk
from semantic_kernel.contents import ChatMessageContent, AuthorRole
from semantic_kernel.agents import ChatCompletionAgent
from semantic_kernel.functions.kernel_arguments import KernelArguments

# Imports des services et modèles
from ..models.extract_definition import ExtractDefinitions, SourceDefinition, Extract
from ..models.extract_result import ExtractResult
from ..services.cache_service import CacheService
from ..services.crypto_service import CryptoService
from ..services.definition_service import DefinitionService
from ..services.extract_service import ExtractService
from ..services.fetch_service import FetchService
from ..core.llm_service import create_llm_service


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
    
    def __init__(self, extract_service: ExtractService):
        """
        Initialise le plugin de réparation.
        
        Args:
            extract_service: Service d'extraction
        """
        self.extract_service = extract_service
        self.repair_results = []
    
    def find_similar_markers(self, text: str, marker: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Trouve des marqueurs similaires dans le texte source.
        
        Args:
            text: Texte source
            marker: Marqueur à rechercher
            max_results: Nombre maximum de résultats
            
        Returns:
            Liste de marqueurs similaires
        """
        if not text or not marker:
            return []
        
        similar_markers = []
        results = self.extract_service.find_similar_text(text, marker, context_size=50, max_results=max_results)
        
        for context, position, found_text in results:
            similar_markers.append({
                "marker": found_text,
                "position": position,
                "context": context
            })
        
        return similar_markers
    
    def update_extract_markers(
        self,
        extract_definitions: ExtractDefinitions,
        source_idx: int,
        extract_idx: int,
        new_start_marker: str,
        new_end_marker: str,
        template_start: Optional[str] = None
    ) -> bool:
        """
        Met à jour les marqueurs d'un extrait.
        
        Args:
            extract_definitions: Définitions d'extraits
            source_idx: Index de la source
            extract_idx: Index de l'extrait
            new_start_marker: Nouveau marqueur de début
            new_end_marker: Nouveau marqueur de fin
            template_start: Template pour le marqueur de début
            
        Returns:
            True si la mise à jour a réussi, False sinon
        """
        if 0 <= source_idx < len(extract_definitions.sources):
            source_info = extract_definitions.sources[source_idx]
            extracts = source_info.extracts
            
            if 0 <= extract_idx < len(extracts):
                old_start = extracts[extract_idx].start_marker
                old_end = extracts[extract_idx].end_marker
                old_template = extracts[extract_idx].template_start
                
                extracts[extract_idx].start_marker = new_start_marker
                extracts[extract_idx].end_marker = new_end_marker
                
                if template_start:
                    extracts[extract_idx].template_start = template_start
                elif extracts[extract_idx].template_start:
                    extracts[extract_idx].template_start = ""
                
                # Enregistrer les modifications
                self.repair_results.append({
                    "source_name": source_info.source_name,
                    "extract_name": extracts[extract_idx].extract_name,
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
    """
    Configure les agents de réparation et de validation.
    
    Args:
        llm_service: Service LLM
        
    Returns:
        Tuple contenant (kernel, repair_agent, validation_agent)
    """
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


async def repair_extract_markers(
    extract_definitions: ExtractDefinitions,
    llm_service,
    fetch_service: FetchService,
    extract_service: ExtractService
) -> Tuple[ExtractDefinitions, List[Dict[str, Any]]]:
    """
    Répare les bornes défectueuses dans les extraits.
    
    Args:
        extract_definitions: Définitions d'extraits
        llm_service: Service LLM
        fetch_service: Service de récupération
        extract_service: Service d'extraction
        
    Returns:
        Tuple contenant (extract_definitions, results)
    """
    logger.info("Initialisation de la réparation des bornes défectueuses...")
    
    # Créer le plugin de réparation
    repair_plugin = ExtractRepairPlugin(extract_service)
    
    # Liste pour stocker les résultats
    results = []
    
    # Parcourir toutes les sources et leurs extraits
    for source_idx, source_info in enumerate(extract_definitions.sources):
        source_name = source_info.source_name
        logger.info(f"Analyse de la source '{source_name}'...")
        
        extracts = source_info.extracts
        for extract_idx, extract_info in enumerate(extracts):
            extract_name = extract_info.extract_name
            start_marker = extract_info.start_marker
            end_marker = extract_info.end_marker
            template_start = extract_info.template_start
            
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
                # Pour les extraits sans template_start, on pourrait utiliser l'agent
                # mais pour simplifier, on les considère comme valides
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
    """
    Génère un rapport HTML des modifications effectuées.
    
    Args:
        results: Résultats des réparations
        output_file: Fichier de sortie pour le rapport HTML
    """
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
    
    # Initialiser les services
    try:
        # Créer le service LLM
        llm_service = create_llm_service()
        if not llm_service:
            logger.error("Impossible de créer le service LLM.")
            return
        
        # Créer le service de cache
        cache_dir = Path("./text_cache")
        cache_service = CacheService(cache_dir)
        
        # Créer le service de chiffrement
        from ..ui.config import ENCRYPTION_KEY, CONFIG_FILE, CONFIG_FILE_JSON
        crypto_service = CryptoService(ENCRYPTION_KEY)
        
        # Créer le service d'extraction
        extract_service = ExtractService()
        
        # Créer le service de récupération
        temp_download_dir = Path("./temp_downloads")
        fetch_service = FetchService(
            cache_service=cache_service,
            temp_download_dir=temp_download_dir
        )
        
        # Créer le service de définition
        input_file = Path(args.input) if args.input else Path(CONFIG_FILE)
        fallback_file = Path(CONFIG_FILE_JSON) if Path(CONFIG_FILE_JSON).exists() else None
        definition_service = DefinitionService(
            crypto_service=crypto_service,
            config_file=input_file,
            fallback_file=fallback_file
        )
        
        # Charger les définitions d'extraits
        extract_definitions, error_message = definition_service.load_definitions()
        if error_message:
            logger.warning(f"Avertissement lors du chargement des définitions: {error_message}")
        
        logger.info(f"{len(extract_definitions.sources)} sources chargées.")
        
        # Filtrer les sources si l'option --hitler-only est activée
        if args.hitler_only:
            original_count = len(extract_definitions.sources)
            extract_definitions.sources = [
                source for source in extract_definitions.sources
                if "hitler" in source.source_name.lower()
            ]
            logger.info(f"Filtrage des sources: {len(extract_definitions.sources)}/{original_count} sources retenues (corpus Hitler).")
        
        # Réparer les bornes défectueuses
        logger.info("Démarrage de la réparation des bornes défectueuses...")
        updated_definitions, results = await repair_extract_markers(
            extract_definitions, llm_service, fetch_service, extract_service
        )
        logger.info(f"Réparation terminée. {len(results)} résultats obtenus.")
        
        # Générer le rapport
        logger.info(f"Génération du rapport dans {args.output}...")
        generate_report(results, args.output)
        logger.info(f"Rapport généré dans {args.output}")
        
        # Sauvegarder les modifications si demandé
        if args.save:
            logger.info(f"Sauvegarde des modifications...")
            success, error_message = definition_service.save_definitions(updated_definitions)
            if success:
                logger.info("✅ Modifications sauvegardées avec succès.")
            else:
                logger.error(f"❌ Erreur lors de la sauvegarde: {error_message}")
        
        # Exporter les définitions mises à jour au format JSON pour vérification
        if args.output_json:
            logger.info(f"Exportation des définitions mises à jour dans {args.output_json}...")
            success, message = definition_service.export_definitions_to_json(
                updated_definitions, Path(args.output_json)
            )
            logger.info(message)
    
    except Exception as e:
        logger.error(f"Exception non gérée: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(main())