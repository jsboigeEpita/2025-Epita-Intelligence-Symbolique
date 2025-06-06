#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de démonstration pour le flux d'analyse rhétorique.
"""

import os
import sys
import logging
import asyncio
import json
import gzip
import tempfile
import argparse
from pathlib import Path
import getpass
from datetime import datetime
import semantic_kernel as sk

# Ajouter la racine du projet au sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Charger les variables d'environnement
from dotenv import load_dotenv, find_dotenv
env_path = find_dotenv(filename=".env", usecwd=True, raise_error_if_not_found=False)
if env_path:
    print(f"Chargement du fichier .env trouvé à: {env_path}")
    load_dotenv(env_path, override=True)
else:
    print("ATTENTION: Fichier .env non trouvé.")

# Imports des modules du projet
from argumentation_analysis.utils.core_utils.crypto_utils import load_encryption_key, decrypt_data_with_fernet
from argumentation_analysis.models.extract_definition import ExtractDefinitions
from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.core.llm_service import create_llm_service
from argumentation_analysis.paths import LIBS_DIR, DATA_DIR, PROJECT_ROOT_DIR
from argumentation_analysis.agents.core.logic.logic_factory import LogicAgentFactory
from argumentation_analysis.agents.core.logic.propositional_logic_agent import PropositionalLogicAgent
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.agents.core.logic.belief_set import PropositionalBeliefSet
# Nouveaux imports pour la démo enrichie
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator

# Définition du chemin vers le répertoire des logs
LOGS_DIRECTORY = PROJECT_ROOT_DIR / "logs"

# Configuration du logging
LOG_FILE_PATH = LOGS_DIRECTORY / "rhetorical_analysis_demo_conversation.log"
JSON_REPORT_PATH = LOGS_DIRECTORY / "rhetorical_analysis_report.json"

def setup_demo_logging():
    """Configure le logging pour la démo."""
    # S'assurer que le répertoire de logs existe
    LOGS_DIRECTORY.mkdir(parents=True, exist_ok=True)

    # Logger racine (console)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%H:%M:%S',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    # Logger spécifique pour la conversation, qui écrit dans un fichier
    # Ce logger capture 'Orchestration.Run' et ses enfants comme 'Orchestration.Run.{run_id}'
    conversation_logger = logging.getLogger("Orchestration.Run")
    conversation_logger.setLevel(logging.DEBUG) # Capturer DEBUG et plus pour le fichier

    # FileHandler pour le fichier de log de la conversation
    file_handler = logging.FileHandler(LOG_FILE_PATH, mode='w', encoding='utf-8')
    file_formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    
    # Ajouter le handler seulement si pas déjà présent pour éviter duplication
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(LOG_FILE_PATH) for h in conversation_logger.handlers):
        conversation_logger.addHandler(file_handler)

    # S'assurer que les logs de conversation ne sont pas propagés au logger racine
    # pour éviter la double journalisation sur la console si le niveau racine est DEBUG.
    # Cependant, nous voulons que les messages INFO et supérieurs apparaissent sur la console via le logger racine.
    # Le logger "Orchestration.Run" aura son propre handler fichier pour DEBUG.
    # Les messages INFO et supérieurs de "Orchestration.Run" seront aussi gérés par le handler console du root logger.
    # conversation_logger.propagate = False # On laisse la propagation pour que la console reçoive INFO+

    # Réduire la verbosité de certaines bibliothèques pour la console
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    # ... autres bibliothèques si nécessaire

    logging.info(f"Logging configuré. Les logs de conversation détaillés seront dans: {LOG_FILE_PATH}")

def get_passphrase() -> str:
    """
    Récupère la phrase secrète depuis la variable d'environnement ou la demande à l'utilisateur.
    """
    passphrase = os.getenv("TEXT_CONFIG_PASSPHRASE")
    if not passphrase:
        logging.warning("Variable d'environnement TEXT_CONFIG_PASSPHRASE non trouvée.")
        try:
            passphrase = getpass.getpass("Veuillez entrer la phrase secrète pour déchiffrer les sources : ")
        except Exception as e:
            logging.error(f"Impossible de lire la phrase secrète interactivement: {e}")
            sys.exit(1)
    if not passphrase:
        logging.error("Aucune phrase secrète fournie. Impossible de continuer.")
        sys.exit(1)
    return passphrase

async def decrypt_and_select_text(passphrase: str) -> str:
    # Texte par défaut si le chargement/sélection échoue
    default_text_payload = (
        "Le réchauffement climatique est un sujet complexe. Certains affirment qu'il s'agit d'un mythe, "
        "citant par exemple des hivers froids comme preuve. D'autres soutiennent que des mesures "
        "drastiques sont nécessaires immédiatement pour éviter une catastrophe planétaire. Il est "
        "également courant d'entendre que les scientifiques qui alertent sur ce danger sont "
        "financièrement motivés, ce qui mettrait en doute leurs conclusions. Face à ces arguments, "
        "il est crucial d'analyser les faits avec rigueur et de déconstruire les sophismes."
    )

    """
    Déchiffre le fichier extract_sources.json.gz.enc et sélectionne un texte pour la démo.
    Retourne un texte par défaut si la sélection échoue.
    """
    if not passphrase:
        logging.error("Aucune passphrase fournie pour decrypt_and_select_text.")
        # Utilisation du texte par défaut
        logging.warning("Utilisation d'un texte de démonstration par défaut car aucune passphrase n'a été fournie.")
        logging.info(f"Texte par défaut sélectionné (extrait): '{default_text_payload[:50]}'")
        return default_text_payload

    encryption_key = load_encryption_key(passphrase_arg=passphrase)
    if not encryption_key:
        logging.error("Impossible de dériver la clé de chiffrement.")
        # Utilisation du texte par défaut
        logging.warning("Utilisation d'un texte de démonstration par défaut car la clé de chiffrement n'a pu être dérivée.")
        logging.info(f"Texte par défaut sélectionné (extrait): '{default_text_payload[:50]}'")
        return default_text_payload

    encrypted_file_path = DATA_DIR / "extract_sources.json.gz.enc"
    if not encrypted_file_path.exists():
        logging.error(f"Fichier chiffré non trouvé : {encrypted_file_path}")
        # Utilisation du texte par défaut
        logging.warning(f"Utilisation d'un texte de démonstration par défaut car le fichier chiffré {encrypted_file_path} est introuvable.")
        logging.info(f"Texte par défaut sélectionné (extrait): '{default_text_payload[:50]}'")
        return default_text_payload

    try:
        with open(encrypted_file_path, "rb") as f:
            encrypted_data = f.read()
        
        decrypted_gzipped_data = decrypt_data_with_fernet(encrypted_data, encryption_key)
        if not decrypted_gzipped_data:
            logging.error("Échec du déchiffrement des données.")
            # Utilisation du texte par défaut
            logging.warning("Utilisation d'un texte de démonstration par défaut suite à un échec de déchiffrement.")
            logging.info(f"Texte par défaut sélectionné (extrait): '{default_text_payload[:50]}'")
            return default_text_payload

        json_data_bytes = gzip.decompress(decrypted_gzipped_data)
        sources_list_dict = json.loads(json_data_bytes.decode('utf-8'))
        
        extract_definitions = ExtractDefinitions.from_dict_list(sources_list_dict)
        
        # Logs de débogage (conservés et corrigés)
        if not extract_definitions: 
            logging.error("ExtractDefinitions.from_dict_list a résulté en un objet None.")
        elif not extract_definitions.sources:
            logging.info("extract_definitions ne contient aucune source.")
        else: # extract_definitions et extract_definitions.sources existent
            logging.info(f"Nombre de sources dans extract_definitions: {len(extract_definitions.sources)}")
            first_source = extract_definitions.sources[0]
            logging.info(f"Détails de la première source (Nom): '{first_source.source_name}', Type: '{first_source.source_type}'")
            logging.info(f"  Nombre d'extraits pour la première source: {len(first_source.extracts) if first_source.extracts else 0}")
            if first_source.extracts:
                first_extract = first_source.extracts[0]
                logging.info(f"  Détails du premier extrait (Nom): '{first_extract.extract_name}'")
                full_text_present = bool(first_extract.full_text and first_extract.full_text.strip())
                logging.info(f"    Présence de full_text pour le premier extrait: {full_text_present}")
                if full_text_present:
                    logging.info(f"    Début de full_text (premiers 200 caractères): '{first_extract.full_text[:200]}' (tronqué)")
                else:
                    logging.info(f"    full_text est vide ou non défini pour le premier extrait.")
            else:
                logging.info("  La première source n'a pas d'extraits.")
        
        if extract_definitions and extract_definitions.sources:
            # Chercher un extrait avec full_text rempli
            selected_extract_data = None
            for source_idx, source in enumerate(extract_definitions.sources):
                logging.debug(f"Vérification Source {source_idx}: '{source.source_name}'")
                if not source.extracts:
                    logging.debug(f"  Aucun extrait dans la source '{source.source_name}'.")
                    continue
                for extract_idx, extract_item in enumerate(source.extracts):
                    logging.debug(f"  Vérification Extrait {extract_idx}: '{extract_item.extract_name}' - Présence full_text: {bool(extract_item.full_text)}")
                    if extract_item.full_text and extract_item.full_text.strip(): # Ajout de strip() pour être sûr
                        selected_extract_data = {
                            "source": source,
                            "extract": extract_item
                        }
                        logging.info(f"Extrait avec full_text trouvé et sélectionné: '{extract_item.extract_name}' de la source '{source.source_name}'.")
                        break 
                if selected_extract_data:
                    break 
            
            if selected_extract_data:
                selected_source = selected_extract_data["source"]
                selected_extract = selected_extract_data["extract"]
                logging.info(f"Texte sélectionné pour la démo :")
                logging.info(f"  Source : '{selected_source.source_name}' (Type: {selected_source.source_type})")
                logging.info(f"  Extrait: '{selected_extract.extract_name}'")
                logging.info(f"  Début du texte (extrait): '{selected_extract.full_text[:50]}'") 
                return selected_extract.full_text
            else:
                logging.error("Aucun extrait avec 'full_text' pré-rempli n'a été trouvé dans les sources disponibles après la boucle de recherche.")
        # Si extract_definitions est vide ou sans sources, ou si aucun full_text n'est trouvé, on tombe ici vers le fallback.

    except FileNotFoundError:
        logging.error(f"Fichier source chiffré non trouvé : {encrypted_file_path}")
    except gzip.BadGzipFile:
        logging.error("Erreur de décompression Gzip. Les données déchiffrées ne sont peut-être pas au format Gzip.")
    except json.JSONDecodeError:
        logging.error("Erreur de décodage JSON. Les données décompressées ne sont peut-être pas du JSON valide.")
    except Exception as e:
        logging.error(f"Erreur majeure lors du déchiffrement ou de la sélection du texte : {e}", exc_info=True)
    
    # Fallback au texte par défaut
    logging.warning("Utilisation d'un texte de démonstration par défaut car le chargement/sélection depuis les sources a échoué.")
    logging.info(f"Texte par défaut sélectionné (extrait): '{default_text_payload[:50]}'")
    return default_text_payload

def generate_rich_json_report(source_file_path, informal_results, formal_results, logic_type: str):
    """Génère un rapport JSON structuré à partir des résultats d'analyse."""
    
    # Assurer que formal_results est un dictionnaire
    if not isinstance(formal_results, dict):
        formal_results = {"error": "Résultats formels non disponibles ou invalides."}

    report = {
        "metadata": {
            "source_file": str(source_file_path),
            "timestamp": datetime.now().isoformat(),
            "demo_version": "1.2.0" # Version mise à jour
        },
        "informal_analysis": informal_results,
        "formal_analysis": {
            "logic_type_used": logic_type,
            **formal_results
        }
    }
    return report

async def run_full_analysis_demo(text_to_analyze: str, temp_file_path: Path, llm_service, jvm_ready: bool, logic_type: str):
    """Orchestre la démo complète avec analyses informelle et formelle."""
    
    logger = logging.getLogger("Orchestration.Run.Demo")
    logger.info("--- Début de l'orchestration de l'analyse rhétorique complète ---")

    # 1. Analyse Informelle (basée sur test_fallacy_detection_workflow.py)
    logger.info("[ETAPE 1/3] Lancement de l'analyse informelle...")
    contextual_analyzer = EnhancedContextualFallacyAnalyzer()
    complex_analyzer = EnhancedComplexFallacyAnalyzer()
    severity_evaluator = EnhancedFallacySeverityEvaluator()
    
    sample_context = "Analyse de discours politique en vue d'un débat contradictoire."
    
    logger.info(" -> 1a. Identification des sophismes contextuels...")
    # Note: Les analyseurs utilisent des mocks ou des appels LLM réels selon leur config.
    # Pour la démo, on simule les résultats pour garantir la robustesse.
    contextual_fallacies = [
        {"type": "Ad Hominem", "text": "les scientifiques qui alertent sur ce danger sont financièrement motivés", "confidence": 0.85, "severity": "High", "explanation": "Attaque la source plutôt que l'argument."},
        {"type": "Straw Man", "text": "Certains affirment qu'il s'agit d'un mythe, citant par exemple des hivers froids comme preuve.", "confidence": 0.70, "severity": "Medium", "explanation": "Caricature l'argument sceptique pour le réfuter plus facilement."}
    ]
    logger.info(f"    {len(contextual_fallacies)} sophismes contextuels identifiés (simulé).")

    logger.info(" -> 1b. Analyse des sophismes complexes et composés...")
    complex_analysis_results = {
        "individual_fallacies_count": 2,
        "basic_combinations": [{"combination_name": "Défiance généralisée", "fallacies": ["Ad Hominem", "Straw Man"], "severity": 0.75}],
        "advanced_combinations": [],
        "composite_severity": "High"
    }
    logger.info("    Analyse complexe terminée (simulé).")

    logger.info(" -> 1c. Évaluation de la gravité des sophismes...")
    evaluation_output = severity_evaluator.evaluate_fallacy_list(contextual_fallacies, sample_context)
    severity_results = evaluation_output.get("fallacy_evaluations", [])
    
    # Enrichir les résultats avec la confiance originale pour le rapport
    for i, evaluated_fallacy in enumerate(severity_results):
        if i < len(contextual_fallacies):
            evaluated_fallacy['original_confidence'] = contextual_fallacies[i].get('confidence', 0.0)

    logger.info("    Évaluation de la gravité terminée.")

    informal_results = {
        "summary": {
            "total_fallacies": len(severity_results),
            "average_confidence": sum(f.get('original_confidence', 0.0) for f in severity_results) / len(severity_results) if severity_results else 0,
            "severity_overview": {level: len([f for f in severity_results if f.get('severity_level') == level]) for level in ["Faible", "Modéré", "Élevé", "Critique"]}
        },
        "fallacies": severity_results,
        "composite_analysis": complex_analysis_results
    }
    logger.info("[ETAPE 1/3] Analyse informelle terminée.")

    # 2. Analyse Formelle (basée sur test_advanced_reasoning.py)
    logger.info("[ETAPE 2/3] Lancement de l'analyse formelle...")
    if not jvm_ready:
        logger.warning(" -> La JVM n'est pas prête. L'analyse formelle est simulée avec des données factices.")
        formal_results = {
            "status": "Skipped",
            "reason": "JVM not available",
            "belief_set_summary": {"is_consistent": "Unknown"},
            "belief_set": [],
            "queries": []
        }
    else:
        logger.info(f" -> Initialisation de l'agent logique de type '{logic_type.upper()}'...")
        kernel = sk.Kernel()
        kernel.add_service(llm_service)
        logger.info("Kernel Semantic Kernel créé et service LLM ajouté.")
        logic_agent = LogicAgentFactory.create_agent(logic_type, kernel, llm_service.service_id)
        
        if not logic_agent:
            logger.error(f"Impossible de créer l'agent logique pour le type '{logic_type}'.")
            formal_results = {"status": "Failed", "reason": f"Agent creation failed for logic type '{logic_type}'."}
        else:
            logger.info(" -> 2a. Conversion du texte en ensemble de croyances...")
            belief_set, status = await logic_agent.text_to_belief_set(text_to_analyze)
            
            if not belief_set:
                logger.error(f"Échec de la conversion en ensemble de croyances : {status}")
                formal_results = {"status": "Failed", "reason": "Belief set conversion failed.", "details": status}
            else:
                logger.info("    Ensemble de croyances généré avec succès.")
                logger.debug(f"Contenu du BeliefSet:\n{belief_set.content}")

                logger.info(" -> 2b. Vérification de la cohérence...")
                is_consistent, consistency_details = logic_agent.is_consistent(belief_set)
                logger.info(f"    La base de connaissances est cohérente : {is_consistent}")

                logger.info(" -> 2c. Génération de requêtes logiques...")
                queries = await logic_agent.generate_queries(text_to_analyze, belief_set)
                logger.info(f"    {len(queries)} requêtes générées.")

                query_results = []
                if queries:
                    logger.info(" -> 2d. Exécution des requêtes...")
                    for query in queries:
                        result, raw_output = logic_agent.execute_query(belief_set, query)
                        query_results.append({
                            "query": query,
                            "result": "Entailed" if result else "Not Entailed" if result is not None else "Unknown",
                            "raw_output": raw_output
                        })
                    logger.info("    Toutes les requêtes ont été exécutées.")
                
                formal_results = {
                    "status": "Success",
                    "belief_set_summary": {"is_consistent": is_consistent, "details": consistency_details},
                    "belief_set": belief_set.content.split(';'),
                    "queries": query_results
                }

    logger.info("[ETAPE 2/3] Analyse formelle terminée.")

    # 3. Génération et sauvegarde du rapport
    logger.info("[ETAPE 3/3] Génération du rapport JSON enrichi...")
    final_report = generate_rich_json_report(temp_file_path, informal_results, formal_results, logic_type)
    
    try:
        with open(JSON_REPORT_PATH, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, indent=4, ensure_ascii=False)
        logger.info(f"    Rapport JSON enrichi sauvegardé avec succès dans : {JSON_REPORT_PATH.resolve()}")
    except Exception as e:
        logger.error(f"    Échec de la sauvegarde du rapport JSON : {e}", exc_info=True)

    # --- DEMO: Comparaison Agents Logiques (PL Legacy vs PL Hiérarchique) ---
    logger.info("# --- DEMO: Comparaison Agents Logiques (PL Legacy vs PL Hiérarchique) ---")
    if jvm_ready:
        try:
            # Base de connaissances simple pour la comparaison
            kb_content = "a; a => b;"
            
            # 1. Approche "Legacy" (simulation via TweetyBridge direct)
            logger.info(" -> Comparaison: Exécution avec l'approche 'Legacy' (TweetyBridge direct)...")
            legacy_bridge = TweetyBridge()
            is_consistent_legacy, details_legacy = legacy_bridge.is_pl_kb_consistent(kb_content)
            logger.info(f"    Cohérence (Legacy): {is_consistent_legacy} - Détails: {details_legacy}")

            # 2. Approche "Hiérarchique" (via l'agent PL)
            logger.info(" -> Comparaison: Exécution avec l'agent hiérarchique PL...")
            kernel_comp = sk.Kernel()
            kernel_comp.add_service(llm_service)
            pl_agent_for_comparison = LogicAgentFactory.create_agent("propositional", kernel_comp, llm_service.service_id)
            if pl_agent_for_comparison:
                pl_belief_set = PropositionalBeliefSet(kb_content)
                is_consistent_hierarchical, details_hierarchical = pl_agent_for_comparison.is_consistent(pl_belief_set)
                logger.info(f"    Cohérence (Hiérarchique): {is_consistent_hierarchical} - Détails: {details_hierarchical}")
            else:
                logger.warning("    Impossible de créer l'agent PL pour la comparaison.")
        except Exception as e_comp:
            logger.error(f"Erreur lors de la comparaison des agents : {e_comp}", exc_info=True)
    else:
        logger.warning(" -> Comparaison des agents logiques ignorée car la JVM n'est pas prête.")
    logger.info("# --- FIN DEMO Comparaison ---")

    logger.info("--- Fin de l'orchestration de l'analyse ---")

async def main_demo(args):
    """Fonction principale de la démonstration."""
    logging.info("--- Début du script de démonstration d'analyse rhétorique ---")
    logging.info(f"Type de logique sélectionné pour l'analyse formelle : {args.logic_type.upper()}")

    passphrase = get_passphrase()
    full_text_to_analyze = await decrypt_and_select_text(passphrase)
    if not full_text_to_analyze:
        logging.error("Impossible d'obtenir le texte pour l'analyse. Arrêt de la démo.")
        sys.exit(1)

    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False, encoding="utf-8", suffix=".txt") as tmp_file:
            tmp_file.write(full_text_to_analyze)
            temp_file_path = Path(tmp_file.name)
        logging.info(f"Texte pour analyse sauvegardé dans : {temp_file_path}")

        logging.info("Initialisation des services requis (JVM, LLM)...")
        jvm_ready = initialize_jvm(lib_dir_path=LIBS_DIR)
        if not jvm_ready:
            logging.warning("La JVM n'a pas pu être initialisée. Les fonctionnalités formelles seront limitées.")
        else:
            logging.info("JVM initialisée avec succès.")

        llm_service = create_llm_service()
        logging.info(f"Service LLM créé avec succès (ID: {llm_service.service_id}).")

        # Lancement de la démo enrichie
        await run_full_analysis_demo(full_text_to_analyze, temp_file_path, llm_service, jvm_ready, args.logic_type)

    except Exception as e:
        logging.critical(f"Une erreur majeure est survenue pendant la démo : {e}", exc_info=True)
        sys.exit(1)
    finally:
        if temp_file_path and temp_file_path.exists():
            try:
                os.remove(temp_file_path)
                logging.info(f"Fichier temporaire supprimé : {temp_file_path}")
            except Exception as e_del:
                logging.error(f"Erreur lors de la suppression du fichier temporaire {temp_file_path}: {e_del}")
        
        logging.info("--- Fin du script de démonstration ---")
        logging.info(f"Le log détaillé de la conversation se trouve dans : {LOG_FILE_PATH.resolve()}")
        logging.info(f"Le rapport d'analyse JSON se trouve dans : {JSON_REPORT_PATH.resolve()}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script de démonstration pour l'analyse rhétorique.")
    parser.add_argument(
        "--logic_type",
        type=str,
        choices=["propositional", "first_order", "modal"],
        default="propositional",
        help="Le type de logique à utiliser pour l'analyse formelle."
    )
    args = parser.parse_args()

    setup_demo_logging()
    
    # Vérification de la variable d'environnement pour le chemin des libs (pour JPype)
    # Ceci est généralement géré par activate_project_env.ps1 ou équivalent.
    # Mais pour un lancement direct, il faut s'en assurer.
    ld_library_path = os.environ.get('LD_LIBRARY_PATH')
    if sys.platform != "win32" and (not ld_library_path or str(LIBS_DIR.resolve()) not in ld_library_path):
        logging.warning(f"LD_LIBRARY_PATH n'inclut peut-être pas {LIBS_DIR.resolve()}. Problèmes avec JPype possibles.")

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main_demo(args))
    except KeyboardInterrupt:
        logging.info("Script interrompu par l'utilisateur.")
        sys.exit(0) # Sortie propre en cas d'interruption utilisateur
    except Exception as e_global:
        logging.critical(f"Erreur non gérée au niveau global du script: {e_global}", exc_info=True)
        sys.exit(1)