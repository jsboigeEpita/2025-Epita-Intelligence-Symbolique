# -*- coding: utf-8 -*-
# tests/integration/argumentation_analysis/workers/worker_hardening_cases.py
"""
Worker pour l'exécution des tests d'intégration "durcis" dans un sous-processus.
"""
import pytest
import logging
import os
import sys
import importlib
from argumentation_analysis.core.jvm_setup import JvmManager

# Configuration du logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
# Assurer que le chemin du projet est dans le sys.path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Marque tous les tests de ce fichier pour utiliser un LLM réel.
pytestmark = [
    pytest.mark.real_llm,
    pytest.mark.integration
]

@pytest.fixture(scope="module")
def jvm_session():
    """Fixture pour gérer le cycle de vie de la JVM pour le module de test."""
    jvm_manager = JvmManager()
    try:
        jvm_manager.start_jvm()
        logger.info("JVM démarrée pour la session de test du worker.")
        yield
    finally:
        if jvm_manager.is_jvm_started():
            logger.info("Arrêt de la JVM pour la session de test du worker.")
            jvm_manager.shutdown_jvm()

@pytest.fixture(scope="module")
def app(jvm_session): # Dépend de jvm_session pour l'ordre d'initialisation
    """
    Crée une instance de test de l'application Flask pour ce module worker.
    """
    logger.info("--- Création de l'application Flask pour les tests d'intégration (worker) ---")
    os.environ["FORCE_REAL_LLM_IN_TEST"] = "true"
    if "OPENAI_BASE_URL" in os.environ:
        del os.environ["OPENAI_BASE_URL"]

    # Rechargement des modules
    from argumentation_analysis.config import settings
    from argumentation_analysis.core import llm_service
    importlib.reload(settings)
    importlib.reload(llm_service)
    
    from argumentation_analysis.services.web_api.app import create_app
    test_app = create_app()
    test_app.config.update({"TESTING": True})
    
    yield test_app
    
    # Le nettoyage des variables d'env n'est pas nécessaire car le worker est éphémère.
    logger.info("--- Fin des tests d'intégration, nettoyage de l'app (worker) ---")
    
@pytest.fixture()
def client(app):
    """Un client de test pour l'application Flask."""
    return app.test_client()

def test_analyze_empty_string_graceful_handling(client):
    """
    Vérifie que l'API gère une chaîne d'entrée vide sans planter.
    """
    logger.info("--- Test API (worker): Analyse d'une chaîne vide ---")
    response = client.post('/api/analyze', json={'text': ''})
    
    assert response.status_code == 400
    json_data = response.get_json()
    assert "error" in json_data
    assert json_data["error"] == "Données invalides"

def test_analyze_non_argumentative_text(client):
    """
    Vérifie que l'API traite correctement un texte factuel et non argumentatif.
    """
    logger.info("--- Test API (worker): Analyse d'un texte non-argumentatif ---")
    input_text = "La tour Eiffel est une tour de fer puddlé de 330 mètres de hauteur."
    
    response = client.post('/api/analyze', json={'text': input_text, 'analysis_type': 'default'})
    
    assert response.status_code == 200
    json_data = response.get_json()
    
    fallacies = json_data.get("analysis", {}).get("identified_fallacies", {})
    assert len(fallacies) <= 1

def test_analyze_complex_argumentative_text(client):
    """
    Vérifie le comportement de l'API avec un texte complexe.
    """
    logger.info("--- Test API (worker): Analyse d'un texte argumentatif complexe ---")
    input_text = (
        "La proposition de loi sur l'eau est une nécessité absolue. Les experts de notre comité, "
        "tous titulaires d'un doctorat, sont formels. S'opposer c'est vouloir la ruine. "
        "D'ailleurs, mon adversaire est un hypocrite. Il est évident que nous devons agir."
    )
    
    response = client.post('/api/analyze', json={'text': input_text, 'analysis_type': 'default'})
    
    assert response.status_code == 200
    json_data = response.get_json()
    
    fallacies_list = json_data.get("fallacies", [])
    assert len(fallacies_list) > 0
    
    fallacy_names = {f.get('name', '').lower() for f in fallacies_list}
    assert any("ad hominem" in f_name or "appel à l'autorité" in f_name for f_name in fallacy_names)


def main():
    """Point d'entrée principal pour l'exécution des tests."""
    logger.info("Démarrage du worker pour Hardening Cases...")
    try:
        # Exécute tous les tests dans ce fichier
        result = pytest.main([__file__])
        
        if result == pytest.ExitCode.OK:
            logger.info("Tests Hardening Cases terminés avec succès.")
            sys.exit(0)
        else:
            logger.error(f"Les tests Hardening Cases ont échoué: {result}")
            sys.exit(int(result))
            
    except Exception as e:
        logger.critical(f"Erreur critique dans le worker Hardening Cases: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()