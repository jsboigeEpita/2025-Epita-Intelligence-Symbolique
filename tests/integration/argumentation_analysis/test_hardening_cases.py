# -*- coding: utf-8 -*-
"""
Tests d'intégration "durcis" pour le pipeline d'analyse rhétorique.

Ces tests valident le comportement du système face à des cas limites et complexes,
en utilisant une configuration d'intégration complète (LLM + JVM réels).
"""

import pytest
import logging
import os
from unittest.mock import patch

# Import de la factory de l'application Flask et de son initialisation
from argumentation_analysis.services.web_api.app import create_app, initialize_heavy_dependencies
from argumentation_analysis.core.bootstrap import initialize_project_environment

# Configuration du logging
logger = logging.getLogger(__name__)

# Marque tous les tests de ce fichier pour utiliser une JVM et un LLM réel.
pytestmark = [
    pytest.mark.usefixtures("jvm_session"),
    pytest.mark.real_llm
]

@pytest.fixture(scope="module")
def app():
    """
    Crée une instance de test de l'application Flask.
    Cette fixture est configurée au niveau du module et force l'utilisation
    d'un vrai LLM pour tous les tests de ce module en positionnant une variable
    d'environnement *avant* la création de l'application.
    """
    logger.info("--- Création de l'application Flask pour les tests d'intégration ---")

    # Force la logique interne de `create_llm_service` à utiliser un vrai LLM
    # en positionnant la variable d'environnement AVANT l'appel à `create_app()`.
    # On utilise os.environ directement et on gère le nettoyage manuellement.
    original_env_value = os.environ.get("FORCE_REAL_LLM_IN_TEST")
    os.environ["FORCE_REAL_LLM_IN_TEST"] = "true"

    try:
        # Crée l'application Flask. Elle lira la variable d'environnement lors de son initialisation.
        test_app = create_app()
        test_app.config.update({"TESTING": True})
        yield test_app
    finally:
        # Nettoyage de la variable d'environnement après les tests du module
        logger.info("--- Nettoyage de la variable d'environnement ---")
        if original_env_value is None:
            del os.environ["FORCE_REAL_LLM_IN_TEST"]
        else:
            os.environ["FORCE_REAL_LLM_IN_TEST"] = original_env_value
        logger.info("--- Fin des tests d'intégration, nettoyage de l'app ---")
    
@pytest.fixture()
def client(app):
    """Un client de test pour l'application Flask."""
    return app.test_client()

@pytest.mark.integration
def test_analyze_empty_string_graceful_handling(client):
    """
    Vérifie que l'API gère une chaîne d'entrée vide sans planter.
    """
    logger.info("--- Test API: Analyse d'une chaîne vide ---")
    response = client.post('/api/analyze', json={'text': ''})
    
    assert response.status_code == 400, f"Le code de statut attendu était 400, mais était {response.status_code}"
    json_data = response.get_json()
    assert "error" in json_data
    assert json_data["error"] == "Données invalides"
    logger.info(f"Réponse pour chaîne vide OK: {json_data}")

@pytest.mark.integration
def test_analyze_non_argumentative_text(client):
    """
    Vérifie que l'API traite correctement un texte factuel et non argumentatif.
    """
    logger.info("--- Test API: Analyse d'un texte non-argumentatif ---")
    input_text = (
        "La tour Eiffel est une tour de fer puddlé de 330 mètres de hauteur "
        "située à Paris, à l’extrémité nord-ouest du parc du Champ-de-Mars en "
        "bordure de la Seine. Construite en deux ans par Gustave Eiffel et ses "
        "collaborateurs pour l’Exposition universelle de Paris de 1889."
    )
    
    response = client.post('/api/analyze', json={'text': input_text, 'analysis_type': 'default'})
    
    assert response.status_code == 200, f"L'analyse a échoué avec le statut: {response.status_code}"
    json_data = response.get_json()
    
    fallacies = json_data.get("analysis", {}).get("identified_fallacies", {})
    assert len(fallacies) <= 1, f"Trop de sophismes ({len(fallacies)}) détectés dans un texte non argumentatif."
    logger.info(f"Analyse du texte non-argumentatif terminée. {len(fallacies)} sophisme(s) détecté(s).")

@pytest.mark.integration
def test_analyze_complex_argumentative_text(client):
    """
    Vérifie le comportement de l'API avec un texte complexe.
    """
    logger.info("--- Test API: Analyse d'un texte argumentatif complexe ---")
    input_text = (
        "La proposition de loi sur l'eau est une nécessité absolue. Les experts de notre comité, "
        "tous titulaires d'un doctorat, sont formels : sans cette loi, nos réserves d'eau seront "
        "à sec d'ici 2050. S'opposer à cette loi, c'est vouloir la ruine de notre agriculture. "
        "D'ailleurs, mon adversaire politique, qui critique cette loi, a lui-même été vu en train "
        "d'arroser son jardin en pleine journée. Peut-on vraiment faire confiance à un tel hypocrite ? "
        "Il est évident pour toute personne sensée que nous devons agir maintenant."
    )
    
    response = client.post('/api/analyze', json={'text': input_text, 'analysis_type': 'default'})
    
    assert response.status_code == 200, f"L'analyse a échoué avec le statut: {response.status_code}"
    json_data = response.get_json()

    fallacies = json_data.get("analysis", {}).get("identified_fallacies", {})
    assert len(fallacies) > 0, "Aucun sophisme n'a été détecté dans un texte qui devrait en contenir."
    
    fallacy_types = {f.get('type', '').lower() for f in fallacies.values()}
    logger.info(f"Sophismes détectés: {fallacy_types}")

    assert any(
        "ad hominem" in f_type or "autorité" in f_type or "ad verecundiam" in f_type
        for f_type in fallacy_types
    ), "Devrait détecter un sophisme de type Ad Hominem ou Appel à l'Autorité."
