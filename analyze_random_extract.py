#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script pour lancer l'analyse rhétorique sur un extrait aléatoire du corpus
en utilisant l'analyseur modulaire existant.
"""

import os
import sys
import asyncio
import random
import logging
from pathlib import Path

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Ajouter le répertoire racine au sys.path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

async def analyze_random_extract():
    """
    Lance l'analyse sur un extrait aléatoire en utilisant les analyseurs existants.
    """
    try:
        # Import des modules d'analyse
        from scripts.consolidated.universal_rhetorical_analyzer import UniversalRhetoricalAnalyzer
        from scripts.data_processing.decrypt_extracts import decrypt_and_load_extracts
        
        logger.info("=== Analyse d'un Extrait Aléatoire ===")
        
        # 1. Charger la clé de chiffrement
        encryption_key = os.getenv("TEXT_CONFIG_PASSPHRASE")
        if not encryption_key:
            logger.error("Variable d'environnement TEXT_CONFIG_PASSPHRASE requise")
            return False
        
        # 2. Déchiffrer et charger les extraits
        logger.info("Chargement du corpus...")
        try:
            extract_definitions, status_message = decrypt_and_load_extracts(encryption_key)
        except Exception as e:
            logger.warning(f"Erreur lors du déchiffrement (clé différente?): {str(e)[:100]}...")
            # Utiliser un texte de fallback pour la démonstration
            fallback_text = """
            L'analyse rhétorique moderne doit identifier les sophismes dans le discours politique.
            Par exemple, l'argument d'autorité fallacieux consiste à invoquer une autorité non qualifiée.
            L'ad hominem attaque la personne plutôt que l'argument.
            Ces techniques manipulatoires sont courantes dans les débats publics contemporains.
            De plus, l'appel à l'émotion détourne l'attention des faits vers les sentiments.
            Le faux dilemme présente seulement deux options alors qu'il en existe d'autres.
            """
            logger.info("Utilisation d'un texte de fallback pour la démonstration")
            return await analyze_text_with_modules(fallback_text.strip(), "Texte de démonstration (fallback)")
        
        if not extract_definitions:
            logger.warning("Aucune définition d'extrait chargée - utilisation du fallback")
            fallback_text = """
            L'analyse rhétorique moderne doit identifier les sophismes dans le discours politique.
            Par exemple, l'argument d'autorité fallacieux consiste à invoquer une autorité non qualifiée.
            L'ad hominem attaque la personne plutôt que l'argument.
            Ces techniques manipulatoires sont courantes dans les débats publics contemporains.
            """
            return await analyze_text_with_modules(fallback_text.strip(), "Texte de démonstration (fallback)")
        
        # 3. Sélectionner un extrait aléatoire
        logger.info("Sélection d'un extrait aléatoire...")
        
        # Construire la liste de tous les extraits disponibles
        all_extracts = []
        for source_idx, source in enumerate(extract_definitions):
            source_name = source.get("source_name", f"Source_{source_idx}")
            extraits = source.get("extracts", [])
            
            # Ajouter le texte complet comme option
            if source.get("full_text"):
                all_extracts.append({
                    "source_name": source_name,
                    "extract_name": "Texte Complet",
                    "text": source["full_text"],
                    "type": "full_text"
                })
            
            # Ajouter les extraits spécifiques
            for extract_idx, extract in enumerate(extraits):
                extract_name = extract.get("extract_name", f"Extract_{extract_idx}")
                if extract.get("full_text"):
                    all_extracts.append({
                        "source_name": source_name,
                        "extract_name": extract_name,
                        "text": extract["full_text"],
                        "type": "extract"
                    })
        
        if not all_extracts:
            logger.error("Aucun extrait avec contenu trouvé")
            return False
        
        # Sélectionner aléatoirement
        selected_extract = random.choice(all_extracts)
        logger.info(f"Extrait sélectionné: {selected_extract['source_name']} -> {selected_extract['extract_name']}")
        
        # 4. Lancer l'analyse avec l'analyseur modulaire
        return await analyze_text_with_modules(
            selected_extract["text"],
            f"{selected_extract['source_name']} - {selected_extract['extract_name']}"
        )
        
    except ImportError as e:
        logger.error(f"Erreur d'import: {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return False

async def analyze_text_with_modules(text: str, description: str) -> bool:
    """
    Analyse un texte avec l'analyseur rhétorique modulaire.
    
    Args:
        text: Le texte à analyser
        description: Description de la source
        
    Returns:
        bool: True si l'analyse a réussi
    """
    try:
        from scripts.consolidated.universal_rhetorical_analyzer import UniversalRhetoricalAnalyzer, AnalysisConfig, SourceType, WorkflowMode
        
        logger.info(f"Lancement de l'analyse: {description}")
        logger.info(f"Longueur du texte: {len(text)} caractères")
        
        # Configuration de l'analyse
        config = AnalysisConfig(
            source_type=SourceType.TEXT,
            workflow_mode=WorkflowMode.ANALYSIS,
            require_authentic=False,
            enable_decryption=False,
            parallel_workers=1
        )
        
        # Créer l'analyseur avec la configuration
        analyzer = UniversalRhetoricalAnalyzer(config)
        
        # Lancer l'analyse
        logger.info("Début de l'analyse rhétorique...")
        results = await analyzer.analyze(text)
        
        # Afficher les résultats
        logger.info("=== RÉSULTATS DE L'ANALYSE ===")
        logger.info(f"Source: {description}")
        
        if results.get("fallacies"):
            logger.info(f"Sophismes détectés: {len(results['fallacies'])}")
            for fallacy in results["fallacies"][:3]:  # Afficher les 3 premiers
                logger.info(f"  - {fallacy.get('type', 'N/A')}: {fallacy.get('description', 'N/A')}")
        
        if results.get("sentiment"):
            sentiment = results["sentiment"]
            logger.info(f"Sentiment: {sentiment.get('polarity', 'N/A')} (confiance: {sentiment.get('confidence', 'N/A')})")
        
        if results.get("analysis_summary"):
            summary = results["analysis_summary"]
            logger.info(f"Résumé: {summary}")
        
        logger.info("=== FIN DE L'ANALYSE ===")
        return True
        
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(analyze_random_extract())
    
    if success:
        logger.info("Analyse terminée avec succès!")
    else:
        logger.error("Analyse échouée")
        sys.exit(1)