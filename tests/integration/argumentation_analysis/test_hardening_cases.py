# -*- coding: utf-8 -*-
"""
Tests d'intégration "durcis" pour le pipeline d'analyse rhétorique.

Ces tests valident le comportement du système face à des cas limites et complexes,
en utilisant une configuration d'intégration complète (LLM + JVM réels).
"""

import pytest
import pytest_asyncio
import logging

# Configure logging for tests
from argumentation_analysis.core.utils.logging_utils import setup_logging
setup_logging()
logger = logging.getLogger(__name__)

# Import the main analysis pipeline orchestrator
from argumentation_analysis.analytics.text_analyzer import TextAnalyzer

# Ensure JVM is ready for these tests
pytestmark = pytest.mark.usefixtures("jvm_session")

@pytest_asyncio.fixture
async def authentic_text_analyzer():
    """
    Fixture pour initialiser le TextAnalyzer avec des services réels (LLM et JVM).
    La fixture jvm_session garantit que la JVM est démarrée.
    """
    try:
        # Configuration minimale pour lancer une analyse réelle
        # Les services (LLM, JVM) sont initialisés par TextAnalyzer en se basant
        # sur la configuration par défaut du projet.
        analyzer = TextAnalyzer(log_level=logging.INFO)
        return analyzer
    except Exception as e:
        pytest.fail(f"Échec de la configuration du TextAnalyzer authentique: {e}")

@pytest.mark.integration
@pytest.mark.asyncio
async def test_analyze_empty_string_graceful_handling(authentic_text_analyzer: TextAnalyzer):
    """
    Vérifie que le pipeline gère une chaîne d'entrée vide sans planter.
    
    ATTENTE: L'analyse doit se terminer avec un statut de succès (ou un
             état indiquant une entrée non valide) mais sans lever d'exception.
    """
    logger.info("--- Test: Analyse d'une chaîne vide ---")
    input_text = ""
    
    result = await authentic_text_analyzer.analyze_text(input_text, analysis_type="default")
    
    assert result is not None, "Le résultat de l'analyse ne doit pas être None."
    assert result.get("status") in ["success", "no_text_to_analyze"], \
           f"Le statut attendu était 'success' ou 'no_text_to_analyze', mais était '{result.get('status')}'"
    logger.info(f"Analyse de la chaîne vide terminée avec succès. Statut: {result.get('status')}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analyze_non_argumentative_text(authentic_text_analyzer: TextAnalyzer):
    """
    Vérifie que le pipeline traite correctement un texte factuel et non argumentatif.

    ATTENTE: L'analyse doit réussir et identifier idéalement aucun sophisme.
             S'il en identifie, leur nombre doit être très faible.
    """
    logger.info("--- Test: Analyse d'un texte non-argumentatif ---")
    input_text = (
        "La tour Eiffel est une tour de fer puddlé de 330 mètres de hauteur "
        "située à Paris, à l’extrémité nord-ouest du parc du Champ-de-Mars en "
        "bordure de la Seine. Construite en deux ans par Gustave Eiffel et ses "
        "collaborateurs pour l’Exposition universelle de Paris de 1889, et "
        "initialement nommée « tour de 300 mètres », elle est devenue le "
        "symbole de la capitale française et un site touristique de premier plan."
    )
    
    result = await authentic_text_analyzer.analyze_text(input_text, analysis_type="default")
    
    assert result is not None
    assert result.get("status") == "success", f"L'analyse a échoué avec le statut: {result.get('status')}"
    
    # Vérifier que peu ou pas de sophismes sont détectés
    final_state = result.get("analysis", {})
    fallacies = final_state.get("identified_fallacies", {})
    
    assert len(fallacies) <= 1, f"Trop de sophismes ({len(fallacies)}) détectés dans un texte non argumentatif."
    logger.info(f"Analyse du texte non-argumentatif terminée. {len(fallacies)} sophisme(s) détecté(s).")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_analyze_complex_argumentative_text(authentic_text_analyzer: TextAnalyzer):
    """
    Vérifie le comportement du pipeline avec un texte complexe contenant
    plusieurs arguments, des sophismes et des distracteurs.

    ATTENTE: L'analyse doit réussir et identifier les sophismes pertinents.
    """
    logger.info("--- Test: Analyse d'un texte argumentatif complexe ---")
    input_text = (
        "La proposition de loi sur l'eau est une nécessité absolue. Les experts de notre comité, "
        "tous titulaires d'un doctorat, sont formels : sans cette loi, nos réserves d'eau seront "
        "à sec d'ici 2050. S'opposer à cette loi, c'est vouloir la ruine de notre agriculture. "
        "D'ailleurs, mon adversaire politique, qui critique cette loi, a lui-même été vu en train "
        "d'arroser son jardin en pleine journée. Peut-on vraiment faire confiance à un tel hypocrite ? "
        "Il est évident pour toute personne sensée que nous devons agir maintenant."
    )
    
    result = await authentic_text_analyzer.analyze_text(input_text, analysis_type="default")
    
    assert result is not None
    assert result.get("status") == "success", f"L'analyse a échoué avec le statut: {result.get('status')}"
    
    final_state = result.get("analysis", {})
    fallacies = final_state.get("identified_fallacies", {})
    
    assert len(fallacies) > 0, "Aucun sophisme n'a été détecté dans un texte qui devrait en contenir."
    
    fallacy_types = {f.get('type', '').lower() for f in fallacies.values()}
    logger.info(f"Sophismes détectés: {fallacy_types}")

    # On s'attend à détecter au moins un appel à l'autorité ou une attaque personnelle.
    # Note : Le nom exact peut varier selon le LLM.
    assert any(
        "ad hominem" in f_type or "autorité" in f_type or "ad verecundiam" in f_type
        for f_type in fallacy_types
    ), "Devrait détecter un sophisme de type Ad Hominem ou Appel à l'Autorité."
