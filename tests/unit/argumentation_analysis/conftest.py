# conftest.py pour les tests unitaires de argumentation_analysis

import pytest
from unittest.mock import patch
from argumentation_analysis.models.extract_result import ExtractResult


@pytest.fixture
def extract_result_dict():
    """Dictionnaire de données pour un résultat d'extraction."""
    return {
        "source_name": "Test Source",
        "extract_name": "Test Extract",
        "status": "valid",
        "message": "Extraction réussie",
        "start_marker": "DEBUT_EXTRAIT",
        "end_marker": "FIN_EXTRAIT",
        "template_start": "T{0}",
        "explanation": "Explication de l'extraction",
        "extracted_text": "Texte extrait de test",
    }


@pytest.fixture
def valid_extract_result(extract_result_dict):
    """Fixture pour un résultat d'extraction valide."""
    return ExtractResult.from_dict(extract_result_dict)


@pytest.fixture
def error_extract_result():
    """Fixture pour un résultat d'extraction en erreur."""
    return ExtractResult(
        source_name="Error Source",
        extract_name="Error Extract",
        status="error",
        message="Erreur lors de l'extraction",
    )


@pytest.fixture
def rejected_extract_result():
    """Fixture pour un résultat d'extraction rejeté."""
    return ExtractResult(
        source_name="Rejected Source",
        extract_name="Rejected Extract",
        status="rejected",
        message="Extraction rejetée",
    )


@pytest.fixture
def sample_definitions():
    """Fixture pour des définitions d'extraits simples."""
    from argumentation_analysis.models.extract_definition import (
        Extract,
        SourceDefinition,
        ExtractDefinitions,
    )

    extract = Extract(
        extract_name="Test Extract",
        start_marker="DEBUT_EXTRAIT",
        end_marker="FIN_EXTRAIT",
        template_start="T{0}",
    )

    source = SourceDefinition(
        source_name="Test Source",
        source_type="url",
        schema="https",
        host_parts=["example", "com"],
        path="/test",
        extracts=[extract],
    )

    return ExtractDefinitions(sources=[source])


@pytest.fixture
def mock_parse_args():
    """Fixture pour mocker la fonction `parse_args` d'argparse."""
    with patch("argparse.ArgumentParser.parse_args") as mock:
        yield mock


@pytest.fixture
def dung_attacks_offline():
    """Stub the Dung attack derivation so a unit test does not reach the network.

    Since #1698, ``_invoke_dung_extensions`` (and the social / probabilistic /
    EAF axes) no longer mint their attack pairs locally: they derive them from
    the text through the id-validated translator, i.e. through the LLM. A unit
    test that exercises those axes without stubbing the derivation therefore
    issues a real request — measured on ``7898d66b``: **+8 requests over 9
    tests in 3 files** against the pre-#1761 tree, all of them family (a) of
    the #1590 discriminator (the suite is byte-identical with the network
    closed, so no assertion reads what the request returns).

    Yields the patch so a test may give it genuine pairs
    (``dung_attacks_offline.return_value = [["a", "b"]]``); the default is an
    empty graph, which the axis treats as "nothing was *shown* to be attacked"
    rather than as a failure.

    Deliberately **not** autouse (#1591 anti-pendule): a test whose verdict
    depends on a real derivation is family (b) and must keep failing when the
    API is absent. Opt in per file or per class with
    ``pytest.mark.usefixtures("dung_attacks_offline")``.
    """
    with patch(
        "argumentation_analysis.orchestration.invoke_callables._derive_dung_attacks"
    ) as stub:
        stub.return_value = []
        yield stub


@pytest.fixture(autouse=True)
def _shutdown_leaked_communication_threads():
    """Arrête les threads d'arrière-plan de communication fuyants après chaque test.

    Root cause du hang CI (#1341) : les tests de communication créent des
    MessageMiddleware (et donc des PublishSubscribeProtocol /
    RequestResponseProtocol) sans appeler ``shutdown()``. Leurs threads
    daemon (cleanup 60s pour pub_sub, monitor 0.1s pour request_response)
    fuient à travers la session ; sous la réentrance ``nest_asyncio`` du
    conftest global, ils bloquent la boucle asyncio des tests async suivants
    → le job ``automated-tests`` hang >5h et ne complète jamais.

    Ce balayage (O(instances vivantes), négligeable sur les ~14k tests où
    la WeakSet est vide) arrête les threads fuyants après chaque test. Les
    protocoles enregistrent leurs instances dans une WeakSet faible
    (``shutdown_all``) ; la WeakSet auto-retire les instances GC-ées.
    """
    yield
    try:
        from argumentation_analysis.core.communication.pub_sub import (
            PublishSubscribeProtocol,
        )

        PublishSubscribeProtocol.shutdown_all()
    except Exception:
        pass
    try:
        from argumentation_analysis.core.communication.request_response import (
            RequestResponseProtocol,
        )

        RequestResponseProtocol.shutdown_all()
    except Exception:
        pass
