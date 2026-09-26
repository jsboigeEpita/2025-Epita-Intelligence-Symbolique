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


class TestPremiseMarkerOpeningTheSentence:
    """#2600 review — « Puisque X, Y » : la route rend le partage de main.

    Le marqueur ouvre la phrase : la coupe ne peut pas s'y appliquer (rien ne
    le précède), et la prémisse ne doit pas contenir la conclusion.
    """

    def test_puisque_route_keeps_the_clause_split(self, client):
        response = client.post(
            "/api/analyze", json={"text": "Puisque il pleut, il faut partir."}
        )

        assert response.status_code == 200, response.text
        structure = response.json()["results"]["argument_structure"]
        assert structure["premises"] == ["Puisque il pleut"], structure
        assert structure["conclusion"] == "il faut partir", structure


class TestPremiseMarkerOpeningAnotherSentence:
    """#2671 — « Il faut partir. Car il pleut. » : la route rendait
    l'argument inversé, la phrase du marqueur en conclusion."""

    def test_route_puts_the_marker_sentence_in_the_premise(self, client):
        response = client.post(
            "/api/analyze", json={"text": "Il faut partir. Car il pleut."}
        )

        assert response.status_code == 200, response.text
        structure = response.json()["results"]["argument_structure"]
        assert structure["premises"] == ["il pleut"], structure
        assert structure["conclusion"] == "Il faut partir", structure
        assert structure["conclusion"] not in structure["premises"], structure


class TestPremiseMarkerStandingAlone:
    """#2678 — « Car il pleut. » : la route rendait 200 avec un argument
    circulaire ; elle refuse désormais, et son message est vrai du texte
    (un marqueur y apparaît : le message « aucun marqueur » serait faux)."""

    def test_route_refuses_a_lone_premise_marker_and_names_why(self, client):
        response = client.post("/api/analyze", json={"text": "Car il pleut."})

        assert response.status_code == 422, response.text
        body = response.json()
        assert body["error_code"] == "unanalyzable_input", body
        assert body["context"]["reason"] == "premise_marker_alone", body
        assert "n'apparaît dans le texte" not in body["detail"], body

    def test_route_keeps_the_no_marker_message_for_the_no_marker_case(self, client):
        response = client.post(
            "/api/analyze", json={"text": "Il fait beau aujourd'hui."}
        )

        assert response.status_code == 422, response.text
        body = response.json()
        assert body["context"]["reason"] == "no_marker", body
        assert "n'apparaît dans le texte" in body["detail"], body
