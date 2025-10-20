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

# Charger les variables d'environnement depuis .env
from dotenv import load_dotenv

load_dotenv()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
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
            extract_definitions, status_message = decrypt_and_load_extracts(
                encryption_key
            )
        except Exception as e:
            logger.warning(
                f"Erreur lors du déchiffrement (clé différente?): {str(e)[:100]}..."
            )
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
            return await analyze_text_with_modules(
                fallback_text.strip(), "Texte de démonstration (fallback)"
            )

        if not extract_definitions:
            logger.warning(
                "Aucune définition d'extrait chargée - utilisation du fallback"
            )
            fallback_text = """
            L'analyse rhétorique moderne doit identifier les sophismes dans le discours politique.
            Par exemple, l'argument d'autorité fallacieux consiste à invoquer une autorité non qualifiée.
            L'ad hominem attaque la personne plutôt que l'argument.
            Ces techniques manipulatoires sont courantes dans les débats publics contemporains.
            """
            return await analyze_text_with_modules(
                fallback_text.strip(), "Texte de démonstration (fallback)"
            )

        # 3. Sélectionner un extrait aléatoire
        logger.info("Sélection d'un extrait aléatoire...")

        # Construire la liste de tous les extraits disponibles
        all_extracts = []
        for source_idx, source in enumerate(extract_definitions):
            source_name = source.get("source_name", f"Source_{source_idx}")
            extraits = source.get("extracts", [])

            # Ajouter le texte complet comme option
            if source.get("full_text"):
                all_extracts.append(
                    {
                        "source_name": source_name,
                        "extract_name": "Texte Complet",
                        "text": source["full_text"],
                        "type": "full_text",
                    }
                )

            # Ajouter les extraits spécifiques
            for extract_idx, extract in enumerate(extraits):
                extract_name = extract.get("extract_name", f"Extract_{extract_idx}")
                if extract.get("full_text"):
                    all_extracts.append(
                        {
                            "source_name": source_name,
                            "extract_name": extract_name,
                            "text": extract["full_text"],
                            "type": "extract",
                        }
                    )

        if not all_extracts:
            logger.error("Aucun extrait avec contenu trouvé")
            return False

        # Sélectionner aléatoirement
        selected_extract = random.choice(all_extracts)
        logger.info(
            f"Extrait sélectionné: {selected_extract['source_name']} -> {selected_extract['extract_name']}"
        )

        # 4. Lancer l'analyse avec l'analyseur modulaire
        return await analyze_text_with_modules(
            selected_extract["text"],
            f"{selected_extract['source_name']} - {selected_extract['extract_name']}",
        )

    except ImportError as e:
        logger.error(f"Erreur d'import: {e}")
        return False
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        return False


async def analyze_text_with_modules(text: str, description: str) -> bool:
    """
    Analyse un texte avec le pipeline unifié et GPT-4o-mini.

    Args:
        text: Le texte à analyser
        description: Description de la source

    Returns:
        bool: True si l'analyse a réussi
    """
    try:
        from argumentation_analysis.utils.unified_pipeline import (
            UnifiedAnalysisPipeline,
            AnalysisConfig,
            AnalysisMode,
            SourceType,
        )

        logger.info(f"🚀 Lancement de l'analyse avec GPT-4o-mini: {description}")
        logger.info(f"📝 Longueur du texte: {len(text)} caractères")

        # Configuration du modèle depuis .env
        llm_model = os.getenv("OPENAI_CHAT_MODEL_ID", "gpt-4o-mini")
        logger.info(f"🤖 Modèle configuré: {llm_model}")

        # Configuration de l'analyse avec GPT-4o-mini authentique
        config = AnalysisConfig(
            analysis_modes=[AnalysisMode.FALLACIES],  # Mode sophismes pour commencer
            llm_service="openai",
            llm_model=llm_model,
            llm_temperature=0.3,
            require_real_llm=True,  # ← CRITIQUE: Forcer l'utilisation réelle de l'LLM
            require_real_tweety=False,  # Désactiver TweetyProject pour éviter les erreurs Java
            enable_fallback=True,
            detailed_logging=True,
            retry_count=2,
            enable_parallel=False,  # Mode séquentiel pour debugging
        )

        # Créer le pipeline
        pipeline = UnifiedAnalysisPipeline(config)

        # Lancer l'analyse
        logger.info("🔥 Début de l'analyse avec GPT-4o-mini authentique...")
        result = await pipeline.analyze_text(text, SourceType.TEXT)

        # Afficher les résultats détaillés
        logger.info("🎯 === RÉSULTATS DE L'ANALYSE GPT-4o-mini ===")
        logger.info(f"📄 Source: {description}")
        logger.info(f"⏱️ Temps d'exécution: {result.execution_time:.2f}s")
        logger.info(f"✅ Statut: {result.status}")

        if result.errors:
            logger.error(f"❌ Erreurs: {result.errors}")

        if result.warnings:
            logger.warning(f"⚠️ Avertissements: {result.warnings}")

        # Afficher les résultats d'analyse
        for mode, analysis_result in result.results.items():
            logger.info(f"\n🔍 === RÉSULTATS {mode.upper()} ===")
            logger.info(f"🤖 Modèle utilisé: {analysis_result.get('model_used', 'N/A')}")
            logger.info(f"🎯 Authentique: {analysis_result.get('authentic', False)}")

            if analysis_result.get("fallacies_detected"):
                fallacies = analysis_result["fallacies_detected"]
                logger.info(f"🎭 Sophismes détectés: {len(fallacies)}")
                for fallacy in fallacies:
                    logger.info(f"  🚩 {fallacy}")

            if analysis_result.get("result"):
                logger.info(f"📊 Résultat: {analysis_result['result']}")

            if analysis_result.get("confidence"):
                logger.info(f"🎯 Confiance: {analysis_result['confidence']}")

        # Afficher le résumé de session
        session_summary = pipeline.get_session_summary()
        logger.info(f"\n📈 === RÉSUMÉ SESSION ===")
        logger.info(f"🆔 Session ID: {session_summary['session_id']}")
        logger.info(f"📊 Taux de succès: {session_summary['success_rate']:.2%}")
        logger.info(f"⏱️ Temps moyen: {session_summary['average_execution_time']:.2f}s")

        logger.info("🎉 === FIN DE L'ANALYSE ===")
        return result.status == "completed"

    except Exception as e:
        logger.error(f"💥 Erreur lors de l'analyse: {e}")
        import traceback

        logger.error(f"📋 Traceback: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = asyncio.run(analyze_random_extract())

    if success:
        logger.info("Analyse terminée avec succès!")
    else:
        logger.error("Analyse échouée")
        sys.exit(1)
