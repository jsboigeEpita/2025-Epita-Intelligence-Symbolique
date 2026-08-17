# -*- coding: utf-8 -*-
"""#1775 — l'ordre d'appel ne doit plus décider de la disponibilité d'un axe formel.

``TweetyInitializer._classes_loaded`` est un attribut de CLASSE : il survit
entre les tests d'un même processus et n'importe quel autre test peut l'avoir
posé (construction d'un ``TweetyBridge``, runner PM, fixture JVM). Un test en
isolation de processus est donc la seule preuve honnête que le PREMIER axe
formel appelé sur un système démarré fonctionne — cf. l'avertissement du
body de #1775 : « un test rouge en isolation processus, sinon il serait vert
à tort ».
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Sous-processus : processus frais, JVM démarrée par l'entrée de production,
# AUCUN TweetyBridge construit (c'est lui qui pose le drapeau en effet de bord),
# puis appel direct du premier axe formel. La précondition « démarre froid »
# est assertée à l'intérieur : si un jour un import réchauffe le drapeau, le
# test échoue sur sa précondition au lieu de passer à tort (#1019).
_FRESH_AXIS_SCRIPT = r"""
import json

import argumentation_analysis.core.dll_guard  # noqa: F401 — doit précéder jpype

from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.agents.core.logic.tweety_initializer import TweetyInitializer

assert initialize_jvm(), "initialize_jvm() a echoue"
assert not TweetyInitializer._classes_loaded, (
    "precondition violee : le processus frais demarre chaud — le test ne "
    "prouverait plus l'independance d'ordre"
)

from argumentation_analysis.plugins.tweety_logic_plugin import TweetyLogicPlugin

result = TweetyLogicPlugin().analyze_dung_framework(
    '{"arguments": ["a", "b"], "attacks": [["a", "b"]]}'
)
data = json.loads(result)
assert isinstance(data, dict), f"reponse non-dict : {result[:200]}"
assert "error" not in data, f"axe rend une erreur : {data}"
extensions = data.get("extensions") or {}
assert extensions, f"axe rend une charge d'extensions vide : {data}"
print("AXIS_OK:", json.dumps(data)[:300])
"""


@pytest.mark.integration
@pytest.mark.no_jvm_session
def test_first_formal_axis_survives_cold_boot():
    """#1775 DoD : processus frais, JVM démarrée, zéro TweetyBridge au
    préalable — ``analyze_dung_framework`` doit réussir. Avant le fix, il
    levait ``RuntimeError('AFHandler instantiated before JVM is ready.')``
    alors que la JVM tournait depuis le bootstrap."""
    env = os.environ.copy()
    # Le sous-processus simule un processus de production, pas un contexte
    # pytest (sinon ``ensure_jvm_and_components_are_ready`` exigerait une
    # fixture pour démarrer la JVM).
    env.pop("PYTEST_RUNNING", None)
    proc = subprocess.run(
        [sys.executable, "-c", _FRESH_AXIS_SCRIPT],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=PROJECT_ROOT,
        env=env,
        timeout=420,
    )
    print("--- STDOUT (fresh-axis subprocess) ---")
    print(proc.stdout[-3000:])
    print("--- STDERR (fresh-axis subprocess) ---")
    print(proc.stderr[-3000:])
    assert (
        proc.returncode == 0
    ), f"l'axe formel a echoue en processus frais (code {proc.returncode})"
    assert "AXIS_OK" in proc.stdout
