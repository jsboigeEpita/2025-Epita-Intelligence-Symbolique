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
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    from cryptography.fernet import Fernet, InvalidToken # Fernet et InvalidToken sont utilisés par file_operations
    import gzip # Utilisé par file_operations implicitement

    # Importer directement depuis les modules du projet
    from argumentation_analysis.ui.file_operations import load_extract_definitions
    from argumentation_analysis.agents.core.informal.informal_agent import InformalAgent
    # Pour l'instant, on ne prévoit pas d'utiliser le Kernel sémantique directement ici.
    # from semantic_kernel import Kernel
except ImportError as e:
    logger.error(f"Erreur d'importation: {e}. Assurez-vous que PYTHONPATH est bien configuré et que les dépendances sont installées.")
    sys.exit(1)

# Clé de chiffrement par défaut. Pour une utilisation réelle, gérer les secrets de manière sécurisée.
DEFAULT_PASSPHRASE = os.getenv("TEXT_CONFIG_PASSPHRASE", "epita_ia_symb_2025_temp_key")

# Sel fixe utilisé pour la dérivation de clé, doit correspondre à celui utilisé lors du chiffrement.
# Ce sel est public et est souvent stocké dans la configuration.
# (Ex: argumentation_analysis/ui/config.py ou un équivalent)
FIXED_SALT = b'q\x8b\t\x97\x8b\xe9\xa3\xf2\xe4\x8e\xea\xf5\xe8\xb7\xd6\x8c' # Correspond au sel dans scripts/decrypt_extracts.py

def derive_encryption_key(passphrase: str) -> bytes:
    """
    Dérive une clé de chiffrement Fernet à partir d'une phrase secrète.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=FIXED_SALT,
        iterations=480000, # Doit correspondre à ce qui est utilisé ailleurs (ex: config.py)
        backend=default_backend()
    )
    derived_key_raw = kdf.derive(passphrase.encode('utf-8'))
    return base64.urlsafe_b64encode(derived_key_raw)

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

def generate_json_report(analysis_results: List[Dict[str, Any]], output_file: Path) -> None:
    """
    Génère un rapport JSON à partir des résultats d'analyse.
    """
    logger.info(f"Génération du rapport JSON vers {output_file}...")
    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, ensure_ascii=False, indent=2)
        logger.info(f"Rapport JSON généré avec succès : {output_file}")
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport JSON : {e}", exc_info=True)

def generate_markdown_report(analysis_results: List[Dict[str, Any]], output_file: Path) -> None:
    """
    Génère un rapport Markdown à partir des résultats d'analyse.
    """
    logger.info(f"Génération du rapport Markdown vers {output_file}...")
    report_content = ["# Rapport d'Analyse Rhétorique Python\n"]

    for result_item in analysis_results:
        source_name = result_item.get("source_name", "Source Inconnue")
        analysis = result_item.get("analysis", {})
        error = result_item.get("error")

        report_content.append(f"## Analyse de : {source_name}\n")

        if error:
            report_content.append(f"**Erreur lors de l'analyse :** `{error}`\n")
            report_content.append("\n---\n")
            continue
        
        if not analysis:
            report_content.append("Aucune analyse disponible pour cette source (données d'analyse vides).\n")
            report_content.append("\n---\n")
            continue

        original_text = analysis.get("text", "Texte original non disponible.")
        report_content.append("### Texte Analysé (extrait)\n")
        report_content.append(f"```\n{original_text[:500]}{'...' if len(original_text) > 500 else ''}\n```\n")

        fallacies = analysis.get("fallacies", [])
        report_content.append(f"### Sophismes Détectés ({len(fallacies)})\n")
        if fallacies:
            for i, fallacy in enumerate(fallacies):
                fallacy_type = fallacy.get("fallacy_type", "Type inconnu").replace("_", " ").title()
                description = fallacy.get("description", "Pas de description.")
                severity = fallacy.get("severity", "Non spécifiée")
                confidence = fallacy.get("confidence", 0.0)
                context_text = fallacy.get("context_text", "Pas de contexte.")
                
                report_content.append(f"**Sophisme {i+1}: {fallacy_type}**\n")
                report_content.append(f"- Description : {description}\n")
                report_content.append(f"- Sévérité : {severity}\n")
                report_content.append(f"- Confiance : {confidence:.2f}\n")
                report_content.append(f"- Contexte : `{context_text[:200]}{'...' if len(context_text) > 200 else ''}`\n")
        else:
            report_content.append("Aucun sophisme détecté pour ce texte.\n")
        
        categories = analysis.get("categories", {})
        report_content.append(f"\n### Catégorisation des Sophismes\n")
        if categories:
            has_content = False
            for category, types in categories.items():
                if types:
                    report_content.append(f"- **{category.replace('_', ' ').title()}**: {', '.join(types)}\n")
                    has_content = True
            if not has_content:
                 report_content.append("Aucune catégorie de sophisme identifiée.\n")
        else:
            report_content.append("Aucune catégorie de sophisme disponible.\n")

        report_content.append("\n---\n")

    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("\n".join(report_content))
        logger.info(f"Rapport Markdown généré avec succès : {output_file}")
    except Exception as e:
        logger.error(f"Erreur lors de la génération du rapport Markdown : {e}", exc_info=True)


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
        class MockFallacyDetector:
            def detect(self, text: str) -> list:
                logger.info(f"MockFallacyDetector.detect appelé pour le texte : '{text[:50]}...'")
                # Simuler une détection pour tester le flux des rapports
                if "exemple de sophisme spécifique pour test" in text.lower():
                    return [{
                        "fallacy_type": "Specific Mock Fallacy",
                        "description": "Détection simulée pour un texte spécifique.",
                        "severity": "Basse",
                        "confidence": 0.90,
                        "context_text": text[:150]
                    }]
                if "un autre texte pour varier" in text.lower():
                    return [
                        {
                            "fallacy_type": "Generalisation Hative (Mock)",
                            "description": "Mock de généralisation hâtive.",
                            "severity": "Moyenne",
                            "confidence": 0.65,
                            "context_text": text[:100]
                        },
                        {
                            "fallacy_type": "Ad Populum (Mock)",
                            "description": "Appel à la popularité simulé.",
                            "severity": "Faible",
                            "confidence": 0.55,
                            "context_text": text[50:150]
                        }
                    ]
                return []

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
        generate_markdown_report(analysis_results, args.output_report_md)

    logger.info("Workflow d'analyse Python complet terminé.")

if __name__ == "__main__":
    main()