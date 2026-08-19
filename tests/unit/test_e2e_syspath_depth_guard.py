"""Garde — la profondeur ``sys.path`` de ``tests/e2e`` ne doit pas retomber sur ``tests/``.

Le fichier ``tests/e2e/python/test_interface_web_complete.py`` fait un
``sys.path.insert`` au niveau module pour importer l'orchestrateur.
``Path(__file__).parent.parent.parent`` depuis ``tests/e2e/python/``
résout **``<root>/tests``**, pas la racine : ``tests/`` se retrouvait en
``sys.path[0]``, ombrageant le vrai package ``scripts`` par ``tests/scripts/``
et empoisonnant ``sys.modules`` pour toute la session (le même motif
cassait ``interface_web_dir`` et le ``cwd`` Playwright, plus
``tests/e2e/demos/demo_service_manager_validated.py`` où l'import ne
survivait que par le cwd de l'appelant — ``tests/project_core`` n'a
jamais contenu ``service_manager``).

Le correctif épingle ``parents[3]`` (= racine du dépôt). Ce garde
exécute le module réel dans un process vierge et vérifie la géométrie :
la racine dans le path, ``tests/`` absent de la position 0, et le
``project_root`` du module égal à la racine.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

E2E_MODULE = REPO_ROOT / "tests/e2e/python/test_interface_web_complete.py"

PROBE = """
import importlib.util, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("e2e_syspath_probe", {module!r})
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print("RESULT:" + json.dumps({{
    "project_root": str(mod.project_root),
    "path0": sys.path[0],
}}))
"""


def test_e2e_module_puts_repo_root_on_sys_path_not_tests():
    assert E2E_MODULE.exists(), f"module under guard missing: {E2E_MODULE}"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            PROBE.format(module=str(E2E_MODULE)),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        cwd=str(REPO_ROOT),
    )
    payload = next(
        (line for line in result.stdout.splitlines() if line.startswith("RESULT:")),
        None,
    )
    assert payload is not None, (
        "probe did not report — module exec failed:\n"
        + (result.stdout + result.stderr)[-600:]
    )
    data = json.loads(payload[len("RESULT:") :])

    root = str(REPO_ROOT)
    assert data["project_root"] == root, (
        f"project_root resolves to {data['project_root']!r}, expected repo "
        f"root {root!r} — the parents[N] depth regressed (cf. stash #3147)"
    )
    assert data["path0"] != str(REPO_ROOT / "tests"), (
        "sys.path[0] is <root>/tests — the insert shadows the real `scripts` "
        "package with tests/scripts/ and poisons sys.modules for the session"
    )
