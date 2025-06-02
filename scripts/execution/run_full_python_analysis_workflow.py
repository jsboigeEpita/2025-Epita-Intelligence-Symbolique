#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour exécuter un workflow d'analyse Python complet.

Ce script :
1. Charge une clé de chiffrement.
2. Déchiffre un corpus de textes (par exemple, tests/extract_sources_backup.enc).
3. Applique des outils d'analyse Python (sophismes, structure, etc.).
4. Génère un rapport structuré (JSON) des résultats.
"""

import os
import sys
import json
import logging
import argparse
import base64
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("FullPythonAnalysisWorkflow")

# Ajout du répertoire parent au chemin pour permettre l'import des modules du projet
# sys.path.insert(0, str(Path(__file__).resolve().parent.parent)) # Ancienne méthode
# Ajout du répertoire racine du projet au chemin pour permettre l'import des modules
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from cryptography.hazmat.primitives import hashes # Gardé car utilisé potentiellement par d'autres imports indirects ou futures utilisations
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC # Gardé pour la même raison
    from cryptography.hazmat.backends import default_backend # Gardé
    from cryptography.fernet import Fernet, InvalidToken
    import gzip
    
    from project_core.utils.crypto_utils import derive_encryption_key
    # MODIFIÉ: generate_markdown_report est maintenant generate_specific_rhetorical_markdown_report
    from project_core.utils.reporting_utils import generate_json_report, generate_specific_rhetorical_markdown_report

    # Importer directement depuis les modules du projet
    from argumentation_analysis.ui.file_operations import load_extract_definitions
    from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
    from argumentation_analysis.mocks.fallacy_detection import MockFallacyDetector
    from argumentation_analysis.mocks.rhetorical_analysis import MockRhetoricalAnalyzer
    from argumentation_analysis.mocks.argument_mining import MockArgumentMiner
    from argumentation_analysis.mocks.claim_mining import MockClaimMiner
    from argumentation_analysis.mocks.evidence_detection import MockEvidenceDetector
    from argumentation_analysis.mocks.bias_detection import MockBiasDetector
    from argumentation_analysis.mocks.emotional_tone_analysis import MockEmotionalToneAnalyzer
    from argumentation_analysis.mocks.engagement_analysis import MockEngagementAnalyzer
    from argumentation_analysis.mocks.clarity_scoring import MockClarityScorer
    from argumentation_analysis.mocks.coherence_analysis import MockCoherenceAnalyzer
    from argumentation_analysis.mocks.fallacy_categorization import MockFallacyCategorizer
    # Pour l'instant, on ne prévoit pas d'utiliser le Kernel sémantique directement ici.
    # from semantic_kernel import Kernel
except ImportError as e:
    logger.error(f"Erreur d'importation: {e}. Assurez-vous que PYTHONPATH est bien configuré et que les dépendances sont installées.")
    sys.exit(1)

# Clé de chiffrement par défaut. Pour une utilisation réelle, gérer les secrets de manière sécurisée.
DEFAULT_PASSPHRASE = os.getenv("TEXT_CONFIG_PASSPHRASE", "epita_ia_symb_2025_temp_key")

# FIXED_SALT et la fonction derive_encryption_key sont maintenant dans project_core.utils.crypto_utils
# Les imports de cryptography.hazmat sont conservés au cas où ils seraient nécessaires
# pour d'autres parties du script ou des imports indirects, bien que derive_encryption_key
# ne soit plus défini localement.

# La fonction decrypt_data_local n'est plus nécessaire si on utilise load_extract_definitions
# qui fait appel à decrypt_data de ui.utils.

def load_corpus_definitions(corpus_file_path: Path, encryption_key: bytes) -> Optional[List[Dict[str, Any]]]:
    """
    Charge et déchiffre les définitions de sources/extraits depuis un fichier .enc
    en utilisant la fonction load_extract_definitions du projet.
    """
    logger.info(f"Tentative de chargement des définitions de corpus depuis : {corpus_file_path}")
    # load_extract_definitions gère déjà la non-existence du fichier, la clé absente,
    # le déchiffrement, la décompression et le parsing JSON.
    # Elle retourne une liste de définitions de sources.
    definitions = load_extract_definitions(config_file=corpus_file_path, key=encryption_key)
    
    if not definitions: # load_extract_definitions peut retourner une liste vide ou des définitions par défaut
        logger.warning(f"Aucune définition de corpus chargée depuis {corpus_file_path} ou des définitions par défaut ont été utilisées.")
        # On considère que si c'est vide ou défaut, c'est un échec pour ce script qui attend des données spécifiques.
        # Cependant, load_extract_definitions retourne une liste (potentiellement de fallback)
        # donc on vérifie si elle contient quelque chose d'utile.
        # Si elle retourne les fallback_definitions, ce n'est pas ce qu'on veut pour ce script.
        # Il faudrait un moyen de distinguer le fallback du succès avec données vides.
        # Pour l'instant, si c'est vide, on considère comme un échec de chargement des données attendues.
        # La fonction load_extract_definitions logge déjà beaucoup.
        # On va se fier à sa capacité à retourner une liste, et on vérifiera son contenu plus tard.
        return definitions # Peut être une liste vide ou de fallback.
    
    logger.info(f"{len(definitions)} définitions de sources chargées depuis {corpus_file_path}.")
    return definitions

def run_rhetorical_analysis(texts_to_analyze: List[Tuple[str, str]], agent: InformalAgent) -> List[Dict[str, Any]]:
    """
    Exécute l'analyse rhétorique sur une liste de textes.
    Chaque élément de texts_to_analyze est un tuple (nom_source, texte_contenu).
    """
    analysis_results = []
    for source_name, text_content in texts_to_analyze:
        logger.info(f"Analyse de : {source_name}")
        if not text_content or not isinstance(text_content, str):
            logger.warning(f"Contenu textuel manquant ou invalide pour {source_name}. Analyse sautée.")
            analysis_results.append({
                "source_name": source_name,
                "error": "Contenu textuel manquant ou invalide",
                "analysis": None
            })
            continue
        try:
            # Utiliser perform_complete_analysis ou analyze_text de InformalAgent
            # perform_complete_analysis semble plus approprié pour un rapport structuré.
            # Il faudra peut-être mocker/fournir un kernel et un llm_service si l'agent en dépend.
            # Pour l'instant, on suppose qu'il peut fonctionner sans pour les analyses Python pures.
            result = agent.perform_complete_analysis(text=text_content) # Peut nécessiter un contexte
            analysis_results.append({
                "source_name": source_name,
                "analysis": result
            })
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de {source_name}: {e}", exc_info=True)
            analysis_results.append({
                "source_name": source_name,
                "error": str(e),
                "analysis": None
            })
    return analysis_results

# La fonction generate_markdown_report a été déplacée vers project_core.utils.reporting_utils
# et renommée en generate_specific_rhetorical_markdown_report.
# L'appel dans main() sera mis à jour.

def main():
    parser = argparse.ArgumentParser(description="Workflow d'analyse Python complet.")
    parser.add_argument(
        "--corpus-file",
        type=Path,
        default=Path("tests/extract_sources_with_full_text.enc"), # Modifié
        help="Chemin vers le fichier corpus chiffré (.enc) contenant full_text" # Modifié
    )
    parser.add_argument(
        "--output-report-json", # Modifié depuis --output-report
        type=Path,
        default=Path("results/full_python_analysis_report.json"),
        help="Chemin vers le fichier de rapport de sortie JSON." # Modifié
    )
    parser.add_argument(
        "--output-report-md", # Nouvel argument
        type=Path,
        default=Path("results/full_python_analysis_report.md"),
        help="Chemin vers le fichier de rapport de sortie Markdown (optionnel)."
    )
    parser.add_argument(
        "--passphrase",
        type=str,
        default=os.getenv("TEXT_CONFIG_PASSPHRASE", DEFAULT_PASSPHRASE),
        help="Phrase de passe pour dériver la clé de chiffrement."
    )
    args = parser.parse_args()

    logger.info("Démarrage du workflow d'analyse Python complet...")
    logger.info(f"Fichier corpus: {args.corpus_file}")
    if args.output_report_json: # Vérifier si l'argument est fourni
        logger.info(f"Rapport JSON: {args.output_report_json}")
    if args.output_report_md: # Vérifier si l'argument est fourni
        logger.info(f"Rapport Markdown: {args.output_report_md}")


    # 1. Charger/Dériver la clé de chiffrement
    if not args.passphrase or args.passphrase == DEFAULT_PASSPHRASE:
        logger.warning("Utilisation de la passphrase par défaut ou non fournie. Assurez-vous que c'est intentionnel.")
    
    encryption_key = derive_encryption_key(args.passphrase)
    if not encryption_key:
        logger.error("Impossible de dériver la clé de chiffrement. Arrêt.")
        sys.exit(1)
    logger.info("Clé de chiffrement dérivée.")

    # 2. Charger les définitions de corpus
    source_definitions = load_corpus_definitions(args.corpus_file, encryption_key)
    
    if not source_definitions:
        logger.error(f"Impossible de charger les définitions de corpus depuis {args.corpus_file} ou le fichier est vide/fallback. Arrêt.")
        sys.exit(1)

    texts_to_analyze: List[Tuple[str, str]] = []
    for i, source_def in enumerate(source_definitions):
        source_name = source_def.get("source_name", f"Source inconnue {i+1}")
        full_text = source_def.get("full_text")

        if full_text and isinstance(full_text, str):
            texts_to_analyze.append((source_name, full_text))
            logger.debug(f"Ajout de '{source_name}' (longueur: {len(full_text)}) à la liste d'analyse.")
        else:
            logger.warning(f"Texte ('full_text') manquant ou invalide pour la source '{source_name}'. Cette source sera ignorée.")

    if not texts_to_analyze:
        logger.error("Aucun texte 'full_text' valide trouvé dans les définitions de corpus. "
                       f"Vérifiez le contenu de {args.corpus_file} et assurez-vous qu'il a été généré "
                       "avec les textes sources embarqués.")
        sys.exit(1)
    
    logger.info(f"{len(texts_to_analyze)} textes extraits pour analyse.")

    # 3. Initialiser l'agent d'analyse
    try:
        mock_tools = {
            "fallacy_detector": MockFallacyDetector()
        }

        informal_agent = InformalAgent(
            agent_id="PythonWorkflowAgent",
            tools=mock_tools,
            semantic_kernel=None,
            informal_plugin=None,
            strict_validation=False
        )
        logger.info("Agent d'analyse rhétorique (InformalAgent) initialisé avec des outils mockés.")
    except Exception as e:
        logger.error(f"Erreur lors de l'initialisation de l'agent d'analyse (InformalAgent): {e}", exc_info=True)
        sys.exit(1)

    # 4. Exécuter l'analyse rhétorique
    analysis_results = run_rhetorical_analysis(texts_to_analyze, informal_agent)

    # 5. Générer les rapports
    if args.output_report_json: # Utiliser le nom d'argument mis à jour
        generate_json_report(analysis_results, args.output_report_json)
    
    if args.output_report_md: # Utiliser le nouvel argument
        generate_specific_rhetorical_markdown_report(analysis_results, args.output_report_md) # MODIFIÉ: Appel de la fonction renommée

    logger.info("Workflow d'analyse Python complet terminé.")

if __name__ == "__main__":
    main()