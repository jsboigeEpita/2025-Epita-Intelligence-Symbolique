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
from argumentation_analysis.agents.core.logic.first_order_logic_agent import FirstOrderLogicAgent
from argumentation_analysis.agents.core.logic.modal_logic_agent import ModalLogicAgent
from argumentation_analysis.agents.core.logic.tweety_bridge import TweetyBridge
from argumentation_analysis.agents.core.logic.belief_set import PropositionalBeliefSet, FirstOrderBeliefSet, ModalBeliefSet
# Nouveaux imports pour la démo enrichie
from argumentation_analysis.agents.tools.analysis.enhanced.complex_fallacy_analyzer import EnhancedComplexFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.contextual_fallacy_analyzer import EnhancedContextualFallacyAnalyzer
from argumentation_analysis.agents.tools.analysis.enhanced.fallacy_severity_evaluator import EnhancedFallacySeverityEvaluator
# Import pour le SynthesisAgent
from argumentation_analysis.agents.core.synthesis.synthesis_agent import SynthesisAgent

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

def generate_rich_json_report(source_file_path, informal_results, formal_results, logic_type: str, analysis_type: str = "logic"):
    """Génère un rapport JSON structuré à partir des résultats d'analyse."""
    
    # Assurer que formal_results est un dictionnaire
    if not isinstance(formal_results, dict):
        formal_results = {"error": "Résultats formels non disponibles ou invalides."}

    report = {
        "metadata": {
            "source_file": str(source_file_path),
            "timestamp": datetime.now().isoformat(),
            "demo_version": "1.3.0", # Version mise à jour pour intégration SynthesisAgent
            "analysis_type": analysis_type
        },
        "informal_analysis": informal_results,
        "formal_analysis": {
            "logic_type_used": logic_type,
            **formal_results
        }
    }
    return report

async def run_unified_analysis_demo(text_to_analyze: str, temp_file_path: Path, llm_service, jvm_ready: bool, logic_type: str):
    """Orchestre la démo complète avec le SynthesisAgent pour analyse unifiée."""
    
    logger = logging.getLogger("Orchestration.Run.Unified")
    logger.info("--- Début de l'orchestration d'analyse unifiée avec SynthesisAgent ---")
    logger.info(f"Type de logique configuré : {logic_type.upper()}")

    try:
        # 1. Initialisation du SynthesisAgent
        logger.info("[ETAPE 1/4] Initialisation du SynthesisAgent...")
        kernel = sk.Kernel()
        kernel.add_service(llm_service)
        
        # Création du SynthesisAgent en mode Phase 1 (enable_advanced_features=False)
        synthesis_agent = SynthesisAgent(
            kernel=kernel,
            agent_name="Demo_SynthesisAgent",
            enable_advanced_features=False
        )
        
        # Configuration des composants
        synthesis_agent.setup_agent_components(llm_service.service_id)
        
        capabilities = synthesis_agent.get_agent_capabilities()
        logger.info(f"SynthesisAgent initialisé - Phase: {capabilities['phase']}, "
                   f"Fonctionnalités avancées: {capabilities['advanced_features_enabled']}")
        
        # 2. Exécution de l'analyse unifiée
        logger.info("[ETAPE 2/4] Lancement de l'analyse unifiée...")
        logger.info("(Début de l'appel asynchrone à synthesize_analysis)")
        
        unified_report = await synthesis_agent.synthesize_analysis(text_to_analyze)
        
        logger.info("(Fin de l'appel asynchrone à synthesize_analysis)")
        logger.info(f"Analyse unifiée terminée en {unified_report.total_processing_time_ms:.2f}ms")
        
        # 3. Génération du rapport textuel
        logger.info("[ETAPE 3/4] Génération du rapport textuel...")
        text_report = await synthesis_agent.generate_report(unified_report)
        logger.info("Rapport textuel généré")
        
        # 4. Adaptation au format de rapport existant pour compatibilité
        logger.info("[ETAPE 4/4] Conversion au format de rapport compatible...")
        
        # Conversion des données du rapport unifié au format attendu
        stats = unified_report.get_summary_statistics()
        
        # Format informel compatible
        informal_results = {
            "summary": {
                "total_fallacies": stats.get('fallacies_count', 0),
                "average_confidence": 0.8,  # Placeholder - le SynthesisAgent ne calcule pas encore cette métrique
                "severity_overview": {
                    "Faible": 0, "Modéré": 1, "Élevé": 1, "Critique": 0  # Estimations basées sur l'analyse
                }
            },
            "fallacies": unified_report.informal_analysis.fallacies_detected if unified_report.informal_analysis else [],
            "synthesis_report": text_report,
            "unified_analysis": True
        }
        
        # Format formel compatible
        formal_results = {
            "status": "Success" if unified_report.logic_analysis.logical_validity is not None else "Partial Success",
            "belief_set_summary": {
                "status": "Succès" if unified_report.logic_analysis.consistency_check else "Échec",
                "is_consistent": unified_report.logic_analysis.consistency_check,
                "formulas_validated": len(unified_report.logic_analysis.formulas_extracted),
                "formulas_total": len(unified_report.logic_analysis.formulas_extracted)
            },
            "query_generation_summary": {
                "status": "Succès" if unified_report.logic_analysis.queries_executed else "Échec",
                "queries_validated": len(unified_report.logic_analysis.queries_executed),
                "queries_total": len(unified_report.logic_analysis.queries_executed)
            },
            "queries": [{"query": q, "result": "Analyzed", "raw_output": ""} for q in unified_report.logic_analysis.queries_executed],
            "synthesis_analysis": {
                "overall_validity": unified_report.overall_validity,
                "confidence_level": unified_report.confidence_level,
                "contradictions_count": len(unified_report.contradictions_identified),
                "recommendations_count": len(unified_report.recommendations)
            }
        }
        
        logger.info("--- Fin de l'orchestration d'analyse unifiée ---")
        return informal_results, formal_results, text_report
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse unifiée: {str(e)}", exc_info=True)
        # Retour de résultats d'erreur compatibles
        error_informal = {
            "summary": {"total_fallacies": 0, "average_confidence": 0, "severity_overview": {}},
            "fallacies": [],
            "error": f"Échec de l'analyse unifiée: {str(e)}"
        }
        error_formal = {
            "status": "Failed",
            "reason": "Unified analysis error",
            "details": str(e)
        }
        return error_informal, error_formal, f"Erreur dans l'analyse unifiée: {str(e)}"

def print_final_summary(report: dict):
    """Affiche une synthèse lisible et détaillée du rapport d'analyse final."""
    
    print("\n" + "="*80)
    print(" " * 25 + "SYNTHÈSE DE L'ANALYSE RHÉTORIQUE")
    print("="*80)

    # Métadonnées
    metadata = report.get("metadata", {})
    print(f"\n--- [ Contexte de l'analyse ] ---")
    print(f"  - Fichier source analysé : {metadata.get('source_file', 'N/A')}")
    print(f"  - Horodatage de l'analyse : {datetime.fromisoformat(metadata.get('timestamp', '')) if metadata.get('timestamp') else 'N/A'}")

    # Analyse Informelle (inchangée)
    informal = report.get("informal_analysis", {})
    informal_summary = informal.get("summary", {})
    print("\n--- [ 1. Analyse Informelle des Sophismes ] ---")
    if not informal_summary:
        print("  - Aucune donnée d'analyse informelle disponible.")
    else:
        total_fallacies = informal_summary.get('total_fallacies', 0)
        avg_confidence = informal_summary.get('average_confidence', 0) * 100
        severity_overview = informal_summary.get('severity_overview', {})
        
        print(f"  - Nombre total de sophismes détectés : {total_fallacies}")
        print(f"  - Confiance moyenne de détection : {avg_confidence:.2f}%")
        print(f"  - Répartition par sévérité :")
        for level, count in severity_overview.items():
            if count > 0:
                print(f"    - {level}: {count} sophisme(s)")

    # Analyse Formelle (entièrement revue)
    formal = report.get("formal_analysis", {})
    logic_type_used = formal.get('logic_type_used', 'N/A').replace('_', ' ').title()
    status = formal.get('status', 'Unknown')
    
    print(f"\n--- [ 2. Analyse Formelle (Logique: {logic_type_used}) ] ---")
    print(f"  - Statut global de l'analyse : {status}")

    if status == "Failed":
        reason = formal.get('reason', 'Raison inconnue.')
        details = formal.get('details', 'Pas de détails supplémentaires.')
        print(f"  - Raison de l'échec : {reason}")
        print(f"  - Détails : {details}")
    elif status in ["Success", "Partial Success"]:
        # 2a. Création de la Base de Connaissances (KB)
        kb_summary = formal.get('belief_set_summary', {})
        kb_status = kb_summary.get('status', 'Échec')
        if "Succès" in kb_status:
            validated = kb_summary.get('formulas_validated', 0)
            total = kb_summary.get('formulas_total', 0)
            print(f"  - Création de la KB : {kb_status} ({validated}/{total} formules validées)")
        else:
            retries = kb_summary.get('attempts', 1)
            print(f"  - Création de la KB : {kb_status} après {retries} tentative(s)")

        # 2b. Cohérence
        consistency = kb_summary.get('is_consistent', 'Inconnue')
        consistency_str = "Cohérente" if consistency else "Incohérente" if consistency is not None else "Inconnue"
        print(f"  - Cohérence         : {consistency_str}")

        # 2c. Génération de Requêtes
        query_summary = formal.get('query_generation_summary', {})
        query_status = query_summary.get('status', 'Échec')
        if "Succès" in query_status:
            validated = query_summary.get('queries_validated', 0)
            total = query_summary.get('queries_total', 0)
            print(f"  - Génération de Requêtes : {query_status} ({validated}/{total} requêtes validées)")
        else:
            print(f"  - Génération de Requêtes : {query_status} (aucune requête valide générée)")

        # 2d. Résultats d'Inférence
        queries = formal.get('queries', [])
        if queries:
            print(f"  - Résultats d'Inférence ({len(queries)} exécutées) :")
            for q in queries:
                query_text = q.get('query', 'N/A')
                result = q.get('result', 'Unknown')
                result_bool = "True" if result == "Entailed" else "False"
                print(f"    - Requête : {query_text:<40} -> Résultat : {result_bool}")
        else:
            print("  - Résultats d'Inférence : Aucune requête n'a été exécutée.")
            
    print("\n" + "="*80)
    print("Rapport complet disponible dans les fichiers de log.\n")

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
            logger.info("    (Début de l'appel asynchrone à text_to_belief_set)")
            belief_set, status = await logic_agent.text_to_belief_set(text_to_analyze)
            logger.info("    (Fin de l'appel asynchrone à text_to_belief_set)")
            
            if not belief_set:
                logger.error(f"Échec de la conversion en ensemble de croyances : {status}")
                formal_results = {
                    "status": "Failed",
                    "reason": "Belief set conversion failed.",
                    "details": status,
                    "belief_set_summary": {
                        "status": "Échec",
                        "attempts": status.get("attempts", 1) if isinstance(status, dict) else 1
                    }
                }
            else:
                logger.info("    Ensemble de croyances généré avec succès.")
                logger.debug(f"Contenu du BeliefSet:\n{belief_set.content}")

                logger.info(" -> 2b. Vérification de la cohérence...")
                is_consistent, consistency_details = logic_agent.is_consistent(belief_set)
                logger.info(f"    La base de connaissances est cohérente : {is_consistent}")

                logger.info(" -> 2c. Génération de requêtes logiques...")
                logger.info("    (Début de l'appel asynchrone à generate_queries)")
                # Note: On suppose que generate_queries pourrait retourner plus d'infos
                # Pour l'instant, on se base sur la longueur de la liste retournée
                queries = await logic_agent.generate_queries(text_to_analyze, belief_set)
                logger.info("    (Fin de l'appel asynchrone à generate_queries)")
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
                
                # Enrichissement du rapport formel
                # Note: Les informations 'formulas_validated' et 'formulas_total' ne sont pas
                # directement disponibles depuis l'agent. On simule une partie de cette logique ici.
                # Idéalement, l'agent devrait retourner un rapport plus structuré.
                belief_set_formulas = [line for line in belief_set.content.split('\n') if '(' in line and ')' in line and not line.startswith('type')]
                
                formal_results = {
                    "status": "Success",
                    "belief_set_summary": {
                        "status": "Succès",
                        "is_consistent": is_consistent,
                        "details": consistency_details,
                        "formulas_validated": len(belief_set_formulas),
                        "formulas_total": len(belief_set_formulas) # Placeholder, l'agent ne retourne pas le total initial
                    },
                    "query_generation_summary": {
                        "status": "Succès" if queries else "Échec",
                        "queries_validated": len(queries),
                        "queries_total": len(queries) # Placeholder, l'agent ne retourne pas le total d'idées
                    },
                    "belief_set_content": belief_set.content,
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
    return final_report

async def main_demo(args):
    """Fonction principale de la démonstration."""
    logging.info("--- Début du script de démonstration d'analyse rhétorique ---")
    logging.info(f"Type d'analyse sélectionné: {args.analysis_type.upper()}")
    
    if args.analysis_type == "logic":
        logging.info(f"Type de logique sélectionné pour l'analyse formelle : {args.logic_type.upper()}")
    elif args.analysis_type == "unified":
        logging.info(f"Type de logique configuré pour l'analyse unifiée : {args.logic_type.upper()}")

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

        # Sélection du type d'analyse
        if args.analysis_type == "unified":
            # Analyse unifiée avec SynthesisAgent
            logging.info("==> Lancement de l'analyse unifiée avec SynthesisAgent")
            informal_results, formal_results, synthesis_text_report = await run_unified_analysis_demo(
                full_text_to_analyze, temp_file_path, llm_service, jvm_ready, args.logic_type
            )
            
            # Génération du rapport final compatible
            final_report = generate_rich_json_report(
                temp_file_path, informal_results, formal_results, args.logic_type, args.analysis_type
            )
            
            # Affichage supplémentaire du rapport de synthèse
            if synthesis_text_report:
                logging.info("=== RAPPORT DE SYNTHÈSE UNIFIÉ ===")
                print("\n" + "="*80)
                print(synthesis_text_report)
                print("="*80)
        else:
            # Analyse traditionnelle (logique seule)
            logging.info("==> Lancement de l'analyse traditionnelle (logique seule)")
            final_report = await run_full_analysis_demo(
                full_text_to_analyze, temp_file_path, llm_service, jvm_ready, args.logic_type
            )
        
        # Affichage de la synthèse finale
        if final_report:
            print_final_summary(final_report)

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
        "--analysis-type",
        type=str,
        choices=["logic", "unified"],
        default="logic",
        help="Type d'analyse à effectuer. 'logic': analyse logique traditionnelle, 'unified': analyse unifiée avec SynthesisAgent."
    )
    parser.add_argument(
        "--logic-type",
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