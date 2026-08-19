"""Garde #1804 — la paire minimale, dans l'ordre qui échouait.

`tests/integration/.../test_fol_handler_config.py` exécutait
``importlib.reload(config)`` sans restauration : le module partagé
``argumentation_analysis.core.config`` recevait un NOUVEL objet ``settings``
lors de chaque reload, orphelinant la référence figée que détient
``test_invoke_modal_logic_reaches_solver`` (import top-level, l.34). La
victime est le tripwire anti-force-SPASS : sa fixture force
``modal_solver=TWEETY`` / ``prefer_spass=False`` sur l'objet figé, mais le
lecteur différé ``invoke_callables.py:7597`` (``from ...config import
settings`` dans le corps de la fonction) re-résout l'attribut de module à
chaque appel — il voit donc le nouvel objet et ses défauts
(``modal_prefer_spass_when_available: bool = True``, config.py:74) : SPASS
gagne, la victime rougit *uniquement parce qu'un test antérieur a tourné*.

Le garde exécute les deux fichiers réels dans cet ordre, en sous-processus
(même pattern que ``test_1796_adf_eaf_decide``) : si un ``reload`` non
restauré est réintroduit dans le pollueur, la paire rougit à nouveau.

Sans le correctif (reload encore présent dans le pollueur) : rc=1, 6 failed.
Avec le correctif : rc=0.
"""

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[6]

POLLUTER = (
    REPO_ROOT
    / "tests/integration/argumentation_analysis/agents/core/logic/test_fol_handler_config.py"
)
VICTIM = (
    REPO_ROOT
    / "tests/integration/argumentation_analysis/agents/core/logic/test_invoke_modal_logic_reaches_solver.py"
)


def test_pair_fol_config_then_invoke_modal_green():
    for path in (POLLUTER, VICTIM):
        assert path.exists(), f"pair member missing: {path}"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(POLLUTER),
            str(VICTIM),
            "-m",
            "not slow and not requires_api",
            "-q",
            "--no-header",
            "--tb=no",
        ],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(REPO_ROOT),
    )
    tail = (result.stdout + result.stderr)[-600:]
    assert result.returncode == 0, (
        "La paire minimale (pollueur puis victime, l'ordre qui échouait en "
        "sweep) est rouge — un état partagé fuit à nouveau entre ces deux "
        "fichiers (cf. #1804) :\n" + tail
    )
