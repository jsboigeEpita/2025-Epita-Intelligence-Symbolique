# -*- coding: utf-8 -*-
"""#2600 — né-rouge : ``/api/analyze`` rendait une prémisse ÉGALE à sa
conclusion pour une phrase dont le seul marqueur est un marqueur de prémisse
(« X car Y »).

Le parseur de prose retenu en #2562 (``ArgumentParser.parse_prose``) ne
coupait qu'aux marqueurs de conclusion : sans marqueur de conclusion, la
phrase entière revenait des deux côtés, et l'onglet Reconstructeur affichait
un argument circulaire que le texte ne contient pas.

Sur l'arbre pristine ce fichier rougit **en valeurs** : ``premises ==
[conclusion]``. Le harnais est celui du fichier voisin
``test_analyze_prose_2562.py`` (le ``AspicParser`` factice du harnais
#2525/#2526 ne rend aucun argument — la route ne l'appelle que pour l'entrée
formelle).
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock

from api.endpoints import router as api_router
from api.errors import install_error_handlers

# Le texte de l'issue, plus un « parce que » à plusieurs mots (le marqueur le
# plus long de la liste : sa coupure ne doit pas laisser « que » derrière).
PROSE_CAR = "Il faut partir car il pleut."
PROSE_PARCE_QUE = "Le sol est mouillé parce que la pluie tombe."


@pytest.fixture
def client():
    app = FastAPI()
    install_error_handlers(app)
    app.include_router(api_router, prefix="/api")

    context = Mock()
    context.jvm_initialized = True
    aspic = Mock()
    aspic.parseBeliefBase.return_value.getArguments.return_value = []
    context.tweety_classes = {"AspicParser": aspic}
    app.state.project_context = context

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.state.project_context = None


class TestPremiseMarkerOnlyProse:
    """Le prose « X car Y » : prémisse et conclusion distinctes."""

    def test_car_premise_and_conclusion_are_distinct(self, client):
        response = client.post("/api/analyze", json={"text": PROSE_CAR})

        assert response.status_code == 200, response.text
        structure = response.json()["results"]["argument_structure"]
        assert structure["premises"] == ["il pleut"], structure
        assert structure["conclusion"] == "Il faut partir", structure

    def test_car_still_goes_through_prose_markers(self, client):
        response = client.post("/api/analyze", json={"text": PROSE_CAR})

        assert (
            response.json()["results"]["extraction_path"] == "prose_markers"
        ), response.json()["results"]

    def test_parce_que_leaves_no_marker_fragment(self, client):
        response = client.post("/api/analyze", json={"text": PROSE_PARCE_QUE})

        structure = response.json()["results"]["argument_structure"]
        assert structure["premises"] == ["la pluie tombe"], structure
        assert structure["conclusion"] == "Le sol est mouillé", structure
