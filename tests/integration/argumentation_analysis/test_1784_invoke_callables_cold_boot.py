# -*- coding: utf-8 -*-
"""#1784 — les axes formels d'``invoke_callables`` ne dépendent plus de l'ordre d'appel.

Même contrat que le tripwire #1775 (``test_1775_axis_order_independence.py``)
pour ``tweety_logic_plugin``, transplanté aux 11 sites ``TweetyInitializer()``
nus d'``invoke_callables.py`` : processus frais, JVM démarrée par l'entrée de
production, AUCUN TweetyBridge construit (c'est lui qui pose
``_classes_loaded`` en effet de bord), puis appel direct d'un axe formel de
l'orchestration. La précondition « démarre froid » est assertée à
l'intérieur du sous-processus : si un import réchauffe le drapeau, le test
échoue sur sa précondition au lieu de passer à tort (#1019).

Avant le fix #1784, ce test échouait sur ``RuntimeError('...
unavailable: JVM/Tweety required')`` — le premier axe appelé sur un système
démarré se déclarait indisponible alors que la JVM tournait, parce que les
classes Tweety n'étaient pas chargées sur ce chemin.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Processus frais : JVM démarrée par l'entrée de production, zéro
# TweetyBridge au préalable, puis appel direct d'un axe de l'orchestration.
# _invoke_dl : site 1 du sweep #1784 — verdict à froid mesuré RUNTIME_JVM
# (« DLHandler » exige is_jvm_ready(), rejeté alors que la JVM tourne). Les
# axes à dégradation silencieuse (qbf : fallback dict ; dung_extensions :
# degraded=True) n'étaient pas de bons candidats : ils ne lèvent pas à froid.
_FRESH_INVOKE_SCRIPT = r"""
import json

import argumentation_analysis.core.dll_guard  # noqa: F401 — doit précéder jpype

from argumentation_analysis.core.jvm_setup import initialize_jvm
from argumentation_analysis.agents.core.logic.tweety_initializer import TweetyInitializer

assert initialize_jvm(), "initialize_jvm() a echoue"
assert not TweetyInitializer._classes_loaded, (
    "precondition violee : le processus frais demarre chaud — le test ne "
    "prouverait plus l'independance d'ordre"
)

import asyncio

from argumentation_analysis.orchestration.invoke_callables import _invoke_dl

out = asyncio.run(
    _invoke_dl(
        "test",
        {
            "tbox": [("Human", "Person")],
            "abox_concepts": [("alice", "Human")],
            "abox_roles": [],
        },
    )
)
assert isinstance(out, dict), f"reponse non-dict : {out}"
assert "error" not in out or not str(out.get("error", "")).startswith("JVM"), (
    f"axe rend une erreur JVM : {out}"
)
consistent = out.get("consistent")
assert consistent is not None, f"axe ne decide pas : {out}"
print("AXIS_OK:", json.dumps(out, default=str)[:300])
"""


@pytest.mark.integration
@pytest.mark.no_jvm_session
def test_orchestration_formal_axis_survives_cold_boot():
    """#1784 DoD : processus frais, JVM démarrée, zéro TweetyBridge au
    préalable — ``_invoke_dl`` doit décider. Avant le fix, la construction
    du ``DLHandler`` sur un ``TweetyInitializer()`` nu levait
    ``RuntimeError('... unavailable: JVM/Tweety required')`` alors que la JVM
    tournait (verdict RUNTIME_JVM mesuré, site 1 de la table #1784)."""
    env = os.environ.copy()
    # Le sous-processus simule un processus de production, pas un contexte
    # pytest (sinon ``ensure_jvm_and_components_are_ready`` exigirait une
    # fixture pour démarrer la JVM).
    env.pop("PYTEST_RUNNING", None)
    proc = subprocess.run(
        [sys.executable, "-c", _FRESH_INVOKE_SCRIPT],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=PROJECT_ROOT,
        env=env,
        timeout=420,
    )
    print("--- STDOUT (fresh-invoke subprocess) ---")
    print(proc.stdout[-3000:])
    print("--- STDERR (fresh-invoke subprocess) ---")
    print(proc.stderr[-3000:])
    assert proc.returncode == 0, (
        "l'axe DL de l'orchestration a echoue en cold boot — "
        f"voir sortie ci-dessus (rc={proc.returncode})"
    )
    assert "AXIS_OK:" in proc.stdout
