"""#1651 — garde de la sonde de chargement DLL torch.

La sonde (``scripts/diagnostics/probe_torch_dll_load.py``) existe pour
attraper un échec de chargement que torch transforme en exception SEH muette
(0xc0000138, STATUS_ORDINAL_NOT_FOUND). Son propre chemin d'échec doit donc
être EXÉCUTÉ, pas supposé : si le catch OSError/WinError de la sonde casse,
elle rapporterait "OK" sur un run qui crashe — le faux-vert exact que le
garde #1385 existe pour empêcher.

Le ``--selftest`` construit un arbre avec une fausse DLL (octets de texte)
qui DOIT être nommée en échec, et une copie d'une vraie DLL système qui DOIT
charger. Exit 0 seulement si les deux comportements sont observés.

Le mode ``--probe-dir`` (diagnostic ciblé) doit mapper un échec de DLL sur
le code de sortie EXIT_DLL_FAILURE (3) pour qu'un wrapper non-Python puisse
le discriminer d'un crash de la sonde elle-même.
"""

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.no_jvm_session,
    pytest.mark.skipif(sys.platform != "win32", reason="sonde DLL Windows"),
]

PROBE = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "diagnostics"
    / "probe_torch_dll_load.py"
)


def _run_probe(*args):
    return subprocess.run(
        [sys.executable, str(PROBE), *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_selftest_catches_bogus_dll(tmp_path):
    result = _run_probe("--selftest", "--log", str(tmp_path / "selftest.log"))
    assert result.returncode == 0, result.stdout + result.stderr
    log = (tmp_path / "selftest.log").read_text(encoding="utf-8")
    # Né-rouge du chemin d'échec : la fausse DLL doit être NOMMÉE en FAIL.
    assert "FAIL bogus_ordinal_probe.dll" in log
    assert "OK good_system_copy.dll" in log
    assert "SELFTEST PASSED" in log


def test_probe_dir_dll_failure_exit_code(tmp_path):
    bad_dir = tmp_path / "broken"
    bad_dir.mkdir()
    (bad_dir / "not_a_pe.dll").write_bytes(b"definitely not a PE image")
    result = _run_probe(
        "--probe-dir", str(bad_dir), "--log", str(tmp_path / "probedir.log")
    )
    assert result.returncode == 3, result.stdout + result.stderr
    log = (tmp_path / "probedir.log").read_text(encoding="utf-8")
    assert "FAIL not_a_pe.dll" in log
