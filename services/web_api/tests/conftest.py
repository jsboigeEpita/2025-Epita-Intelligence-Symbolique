import pytest
# from argumentation_analysis.services.web_api.app import app as flask_app # Importer l'instance de l'application

@pytest.fixture(scope='module')
def app():
    from argumentation_analysis.services.web_api.app import app as flask_app # Importer l'instance de l'application ICI
    """Instance of Main flask app"""
    # Configurer l'application pour les tests si nécessaire
    flask_app.config.update({
        "TESTING": True,
        # Autres configurations spécifiques aux tests si besoin
    })
    return flask_app

@pytest.fixture(scope='module')
def client(app):
    """A test client for the app."""
    return app.test_client()