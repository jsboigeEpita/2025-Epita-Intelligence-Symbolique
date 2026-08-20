"""Contrôle #1794/#1817 : l'import d'un fichier test_*.py ne doit pas semer os.environ.

Toute bande qui collecte ``tests/integration`` importe chaque ``test_*.py`` ;
un ``load_dotenv()`` au niveau module d'un de ces fichiers charge alors le
``.env`` local dans l'environnement du process pour toute la session pytest ;
la clé réelle devient lisible par chaque test qui suit. C'est la victime
canonique : ``test_authenticite_finale_gpt4o.py`` (script — pytest n'y
collecte aucun test, mais l'importe quand même).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VICTIM = REPO_ROOT / "tests" / "integration" / "test_authenticite_finale_gpt4o.py"

# La sonde vit dans un subprocess à environnement MINIMAL : le process pytest
# a typiquement déjà chargé le .env (conftest / plugin dotenv), et un
# subprocess héritier repartirait d'un os.environ déjà saturé — la fuite
# serait invisible. Env réduit au strict nécessaire Windows + cwd = racine du
# dépôt pour que l'éventuel load_dotenv() de la victime trouve le vrai .env —
# c'est le chemin de la fuite. Seuls les NOMS de clés remontent, jamais les
# valeurs.
_PROBE = """
import importlib.util, json, os
before = dict(os.environ)
spec = importlib.util.spec_from_file_location("authenticite_victim", {victim!r})
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
after = dict(os.environ)
gained = sorted(k for k in after if before.get(k) != after[k])
print("GAINED:" + json.dumps(gained))
"""

_CHILD_ENV = {
    k: os.environ[k]
    for k in ("SYSTEMROOT", "SYSTEMDRIVE", "TEMP", "TMP", "COMSPEC")
    if k in os.environ
}


def test_import_of_test_module_does_not_seed_os_environ():
    result = subprocess.run(
        [sys.executable, "-c", _PROBE.format(victim=str(VICTIM))],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=_CHILD_ENV,
        timeout=120,
    )
    marker = next(
        (line for line in result.stdout.splitlines() if line.startswith("GAINED:")),
        None,
    )
    assert marker is not None, (
        "la sonde n'a pas rendu son bilan — "
        f"returncode={result.returncode} "
        f"stdout={result.stdout[-500:]!r} stderr={result.stderr[-500:]!r}"
    )
    gained = json.loads(marker[len("GAINED:") :])
    assert gained == [], (
        f"l'import a semé os.environ : {gained} — un load_dotenv() au niveau "
        "module d'un fichier test_*.py charge le .env local pour toute la "
        "session (#1794/#1817)"
    )
