# -*- coding: utf-8 -*-
"""#1985: chaque symbole registry.<methode> cite dans api_outils.md doit exister.

La page docs/technical/api_outils.md porte deja une note d'exactitude nee d'une
derive anterieure (elle decrivait des classes inexistantes). Cette garde cible
la famille de defauts restante : les exemples copiables qui appellent des
methodes inexistantes du CapabilityRegistry. Instrument minimal — pas un linter
full-page : on extrait les appels `registry.<name>(` des blocs python et on
verifie que <name> est un attribut reel de la classe citee comme source.
"""

import re
from pathlib import Path

import pytest

from argumentation_analysis.core.capability_registry import CapabilityRegistry

DOC = Path(__file__).resolve().parents[3] / "docs" / "technical" / "api_outils.md"


def _registry_calls_in_doc() -> list[str]:
    text = DOC.read_text(encoding="utf-8")
    python_blocks = re.findall(r"```python\n(.*?)```", text, flags=re.DOTALL)
    calls: list[str] = []
    for block in python_blocks:
        calls.extend(re.findall(r"\bregistry\.(\w+)\(", block))
    return sorted(set(calls))


def test_doc_cites_at_least_one_registry_call():
    """Controle non-vacuite : sans appel cite, la garde ne mesurerait rien."""
    calls = _registry_calls_in_doc()
    assert calls, (
        "api_outils.md ne cite plus aucun registry.<methode>( — la garde "
        "test_api_outils_symbols_1985 est devenue vacuous, la retirer ou "
        "l'elargir."
    )


@pytest.mark.parametrize("method_name", _registry_calls_in_doc())
def test_cited_registry_method_exists(method_name: str):
    assert hasattr(CapabilityRegistry, method_name), (
        f"api_outils.md cite registry.{method_name}() qui n'existe pas sur "
        f"CapabilityRegistry (source declaree : "
        f"argumentation_analysis/core/capability_registry.py)."
    )
