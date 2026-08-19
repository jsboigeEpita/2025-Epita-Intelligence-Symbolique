"""Garde — la profondeur ``sys.path`` de ``tests/e2e`` ne doit pas retomber sur ``tests/``.

Les fichiers sous ``tests/e2e/`` font un ``sys.path.insert`` au niveau module
pour importer l'orchestrateur ou les scripts de service.
``Path(__file__).parent.parent.parent`` depuis ``tests/e2e/<sub>/``
résout **``<root>/tests``**, pas la racine : ``tests/`` se retrouvait en
``sys.path[0]``, ombrageant le vrai package ``scripts`` par ``tests/scripts/``
et empoisonnant ``sys.modules`` pour toute la session (le même motif
cassait ``interface_web_dir`` et le ``cwd`` Playwright, plus
``tests/e2e/demos/demo_service_manager_validated.py`` où l'import ne
survivait que par le cwd de l'appelant — ``tests/project_core`` n'a
jamais contenu ``service_manager``).

Le correctif épingle ``parents[3]`` (= racine du dépôt). Ce garde
exécute chaque module réel dans un process vierge et vérifie la
géométrie : la racine dans le path, ``tests/`` absent de la position 0,
et le ``project_root`` du module égal à la racine.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# (module relatif, attribut portant la racine calculée)
GUARDED_MODULES = [
    ("tests/e2e/python/test_interface_web_complete.py", "project_root"),
    ("tests/e2e/demos/demo_service_manager_validated.py", "project_root"),
    ("tests/e2e/web_api/test_interfaces_integration.py", "PROJECT_ROOT"),
    ("tests/e2e/web_api/test_management_scripts.py", "PROJECT_ROOT"),
    ("tests/e2e/web_api/test_interface_simple_playwright.py", "PROJECT_ROOT"),
]

PROBE = """
import importlib.util, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("e2e_syspath_probe", {module!r})
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print("RESULT:" + json.dumps({{
    "project_root": str(getattr(mod, {attr!r})),
    "path0": sys.path[0],
}}))
"""


@pytest.mark.parametrize(
    "module_rel, attr",
    GUARDED_MODULES,
    ids=lambda value: Path(value).name if isinstance(value, str) else value,
)
def test_e2e_module_puts_repo_root_on_sys_path_not_tests(module_rel, attr):
    module_path = REPO_ROOT / module_rel
    assert module_path.exists(), f"module under guard missing: {module_path}"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            PROBE.format(module=str(module_path), attr=attr),
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
        f"{module_rel}: {attr} resolves to {data['project_root']!r}, expected repo "
        f"root {root!r} — the parents[N] depth regressed (cf. stash #3147)"
    )
    assert data["path0"] != str(REPO_ROOT / "tests"), (
        f"{module_rel}: sys.path[0] is <root>/tests — the insert shadows the real "
        "`scripts` package with tests/scripts/ and poisons sys.modules for the session"
    )
