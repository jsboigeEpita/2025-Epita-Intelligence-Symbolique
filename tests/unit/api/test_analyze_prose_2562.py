# -*- coding: utf-8 -*-
"""#2562 — né-rouge : ``/api/analyze`` confiait le prose au ``AspicParser`` de
Tweety (syntaxe de règles) et rendait une structure vide avec un résumé de
comptes jamais extraits (« 0 prémisses et 1 conclusion extraites. », statut 200).

Les textes sont ceux du fichier e2e du reconstructeur
(``tests/e2e/python/test_argument_reconstructor.py``), plus le texte sans
marqueur de son test d'erreur. Sur l'arbre pristine (``main``) ces tests
rougissent **en valeurs** : le ``AspicParser`` factice ne rend aucun argument
(le comportement mesuré du vrai sur du prose), donc prémisses et conclusion
sont vides et le résumé est faux.

Correctif mesuré ici : le prose va au composant de marqueurs de
``argumentation_analysis`` (``ArgumentParser``) — prémisses en liste, casse
d'origine, marqueurs à frontière de lettre ; un texte sans aucun marqueur
argumentatif est refusé avec sa raison (422), jamais maquillé en succès ;
l'entrée formelle ASPIC+ (flèches de règle) continue d'aller au
``AspicParser``, et la réponse nomme le chemin emprunté.
"""

import re
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.endpoints import router as api_router
from api.errors import install_error_handlers

# Les trois textes des tests e2e rouges du reconstructeur (verbatim, incluant
# l'indentation du premier — c'est ce que l'UI envoie).
E2E_SOCRATE = """
    Tous les hommes sont mortels. Socrate est un homme.
    Donc Socrate est mortel.
    """
E2E_PLANETES = (
    "Les planètes sont rondes. La Terre est une planète. "
    "Par conséquent, la Terre est ronde."
)
E2E_PINGOUINS = (
    "Tous les oiseaux ont des ailes. Les pingouins sont des oiseaux. "
    "Donc les pingouins ont des ailes."
)
# Le texte du test d'erreur e2e : aucun marqueur argumentatif.
E2E_SANS_MARQUEUR = "Ce texte provoquera une erreur."

# Une base ASPIC+ formelle (flèches de règle) : elle doit continuer d'aller
# au AspicParser de Tweety.
ASPIC_FORMAL = (
    "tous_les_hommes_sont_mortels => socrate_est_mortel;\n"
    "socrate_est_un_homme => socrate_est_mortel;"
)


@pytest.fixture
def client():
    """L'app de la route, avec le AspicParser factice du harnais #2525/#2526.

    Le kb factice ne rend AUCUN argument : c'est le comportement mesuré du
    vrai ``AspicParser`` sur du prose — la raison d'être de #2562.
    """
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


class TestProseE2ETexts:
    """Les 3 textes e2e : structure extraite par le composant de marqueurs."""

    def test_socrate_extrait_les_deux_premisses_et_la_conclusion(self, client):
        response = client.post("/api/analyze", json={"text": E2E_SOCRATE})

        assert response.status_code == 200, response.text
        structure = response.json()["results"]["argument_structure"]
        assert structure["premises"] == [
            "Tous les hommes sont mortels",
            "Socrate est un homme",
        ], structure
        assert structure["conclusion"] == "Donc Socrate est mortel", structure

    def test_planetes_extrait_premisses_et_conclusion(self, client):
        response = client.post("/api/analyze", json={"text": E2E_PLANETES})

        assert response.status_code == 200, response.text
        structure = response.json()["results"]["argument_structure"]
        assert structure["premises"] == [
            "Les planètes sont rondes",
            "La Terre est une planète",
        ], structure
        assert re.search(r"la Terre est ronde", structure["conclusion"]), structure

    def test_pingouins_extrait_premisses_et_conclusion(self, client):
        response = client.post("/api/analyze", json={"text": E2E_PINGOUINS})

        assert response.status_code == 200, response.text
        structure = response.json()["results"]["argument_structure"]
        assert structure["premises"] == [
            "Tous les oiseaux ont des ailes",
            "Les pingouins sont des oiseaux",
        ], structure
        assert "les pingouins ont des ailes" in structure["conclusion"], structure


class TestSummaryCountsRealValues:
    """Le résumé rend les comptes réellement extraits, jamais d'autres."""

    def test_le_resume_compte_les_deux_premisses_reelles(self, client):
        response = client.post("/api/analyze", json={"text": E2E_SOCRATE})

        summary = response.json()["results"]["summary"]
        assert "2" in summary, summary
        assert not re.search(r"0 pr", summary), summary


class TestMarkerlessText:
    """Un texte sans marqueur : refus avec sa raison, pas un succès vide."""

    def test_sans_marqueur_refuse_avec_raison(self, client):
        response = client.post("/api/analyze", json={"text": E2E_SANS_MARQUEUR})

        assert response.status_code == 422, (
            f"le texte sans marqueur doit être refusé, pas rendu vide : "
            f"{response.status_code} {response.text[:300]}"
        )
        body = response.json()
        assert body["error_code"] == "unanalyzable_input", body
        assert "marqueur" in body["detail"].lower(), body

    def test_sans_marqueur_ne_passe_pas_par_tweety(self, client):
        client.post("/api/analyze", json={"text": E2E_SANS_MARQUEUR})

        aspic = client.app.state.project_context.tweety_classes["AspicParser"]
        aspic.parseBeliefBase.assert_not_called()


class TestFormalAspicStillGoesToTweety:
    """L'entrée formelle ASPIC+ reste au AspicParser ; le chemin est nommé."""

    @pytest.fixture
    def aspic_client(self):
        app = FastAPI()
        install_error_handlers(app)
        app.include_router(api_router, prefix="/api")

        context = Mock()
        context.jvm_initialized = True
        aspic = Mock()
        aspic.parseBeliefBase.return_value.getArguments.return_value = [
            "premise1",
            "premise2",
            "conclusion1",
        ]
        context.tweety_classes = {"AspicParser": aspic}
        app.state.project_context = context

        with TestClient(app, raise_server_exceptions=False) as c:
            yield c

        app.state.project_context = None

    def test_entree_formelle_passe_au_aspicparser(self, aspic_client):
        response = aspic_client.post("/api/analyze", json={"text": ASPIC_FORMAL})

        assert response.status_code == 200, response.text
        aspic = aspic_client.app.state.project_context.tweety_classes["AspicParser"]
        aspic.parseBeliefBase.assert_called_once_with(ASPIC_FORMAL)
        structure = response.json()["results"]["argument_structure"]
        assert structure["premises"] == ["premise1", "premise2"], structure
        assert structure["conclusion"] == "conclusion1", structure

    def test_la_reponse_nomme_le_chemin_pris(self, aspic_client, client):
        formal = aspic_client.post("/api/analyze", json={"text": ASPIC_FORMAL})
        prose = client.post("/api/analyze", json={"text": E2E_SOCRATE})

        assert (
            formal.json()["results"]["extraction_path"] == "aspic_formal"
        ), formal.json()["results"]
        assert (
            prose.json()["results"]["extraction_path"] == "prose_markers"
        ), prose.json()["results"]
