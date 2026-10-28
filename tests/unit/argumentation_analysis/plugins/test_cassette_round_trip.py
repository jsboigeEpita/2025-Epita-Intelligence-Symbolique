"""Cassette probes for the LLM replay loop (#1603), split by failure regime (#1950).

This module carries the property that must be **green under every contract
change**, plus the shape invariants on what is committed:

- **A — do the export/import scripts round-trip losslessly?**
  ``TestExportImportScriptsRoundTrip``. Must ALWAYS be green. It builds its
  own synthetic ``(key, value)`` pairs, so it depends on no production
  prompt, no quality contract, and not even on which cassettes are
  committed. A red here means the scripts are broken — fix the scripts.

- **Shape invariants** on the committed fixture dir,
  ``TestCommittedCassettesAreWellFormed``. Also contract-independent.

Property B — "are the committed cassettes still fresh w.r.t. the production
prompt?" — **was retired with its subject** (#3266). It drove
``narrate_convergence`` and read the ``hit`` counter, because that function
caught every exception around ``invoke_prompt`` and fell back to the template:
on a cache miss the call still *succeeded* and returned a non-empty string, so
only ``hit`` could see the drift. With that function gone there is no single
prompt left to drive, and the detector has no mechanism.

What still guards replay is not a test but the band itself: the replay job
runs the SK-path and raw-path cassettes through ``replay_stats_plugin`` and
fails on ``live != 0`` and on a miss, so a drifted key reddens the record lane
with its own ``hit``/``miss_replay`` attribution. That is a weaker statement
than B's — B named the exact prompt — and it is the honest one after the
retirement.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]  # tests/unit/.../test_*.py -> repo root
SCRIPTS = REPO / "scripts" / "cassettes"
FIXTURES_DIR = REPO / "tests" / "fixtures" / "llm_cassettes"

# The provenance manifest (#2323) is NOT a cassette: it shares the fixtures dir
# but holds run/env metadata, not {"key", "value"}. Every cassette-shaped glob
# must exclude it (same exclusion as import.py's _fixture_keys).
MANIFEST_NAME = "MANIFEST.json"


class TestCommittedCassettesAreWellFormed:
    """Shape invariants on what is committed. Independent of A."""

    def test_at_least_one_cassette_is_committed(self):
        """The fixture directory has at least one cassette.

        If this fails, either the cassettes were never recorded or they were
        committed to a different path. See
        ``tests/fixtures/llm_cassettes/README.md``. The manifest does not
        count: a manifest alone would make this vacuously green (#2323).
        """
        cassettes = [p for p in FIXTURES_DIR.glob("*.json") if p.name != MANIFEST_NAME]
        assert cassettes, f"No cassettes found in {FIXTURES_DIR}"

    def test_cassette_value_is_well_formed(self):
        """Each cassette is ``{"key": sha256, "value": list | dict}``."""
        for path in FIXTURES_DIR.glob("*.json"):
            if path.name == MANIFEST_NAME:
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            assert isinstance(data, dict), path
            assert "key" in data and "value" in data, path
            assert isinstance(data["key"], str) and len(data["key"]) == 64, path
            assert isinstance(data["value"], (list, dict)), path


def _synthetic_cassette(shape: str) -> dict:
    """Build a cassette that exists only for this test.

    Property A must not borrow a committed fixture: doing so couples "are the
    scripts lossless?" to "which cassettes happen to be on disk", which is how
    a prompt change came to redden a script probe (#1950). The key is a real
    sha256 so any 64-hex validation passes; the value mirrors the two shapes
    the scripts must survive (SK-path list, raw-path dict).

    Content is deliberately neutral: these values pass through
    ``scripts/cassettes/privacy.py`` during the export step below.
    """
    key = hashlib.sha256(f"synthetic-round-trip-probe-{shape}".encode()).hexdigest()
    value: list | dict
    if shape == "list":
        value = [
            {
                "role": "assistant",
                "content": "synthetic probe value for the round-trip test",
                "metadata": {"id": "synthetic", "logprobs": None},
            }
        ]
    else:
        value = {
            "id": "synthetic",
            "object": "chat.completion",
            "model": "synthetic-model",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "content": "synthetic probe value for the round-trip test",
                    },
                }
            ],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        }
    return {"key": key, "value": value}


class TestExportImportScriptsRoundTrip:
    """Property A — the export/import scripts are lossless.

    Green under every contract change, by construction: nothing here reads a
    committed cassette or a production prompt.
    """

    @pytest.mark.parametrize("shape", ["list", "dict"])
    def test_round_trip_preserves_a_synthetic_value(
        self, shape: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """A synthetic value reaches a fresh DB identical to the source.

        Probes the two scripts as plain subprocesses (matches the workflow
        committed by po-2025 in #1603), once per cassette shape. The export
        runs under a synthetic ``GITHUB_RUN_ID`` (#2323) so it emits the
        provenance manifest the record job emits — and the import step must
        then pass the manifest gate, exactly like the CI replay lanes. Without
        the manifest the import would exit 3; that is the gate working, not a
        transport defect, so the probe exercises the real job shape instead of
        bypassing it.
        """
        import diskcache  # type: ignore[import-not-found]

        cassette = _synthetic_cassette(shape)
        key = cassette["key"]

        src_db = tmp_path / "src_db"
        dst_db = tmp_path / "dst_db"
        exported_dir = tmp_path / "exported"
        for directory in (src_db, dst_db, exported_dir):
            directory.mkdir()

        # 1. Source DB holding exactly the synthetic entry.
        src = diskcache.Cache(str(src_db))
        try:
            src.set(key, cassette["value"])
        finally:
            src.close()

        # 2. Export (DB -> JSON onto a fresh dir), in the record-job shape:
        #    subprocesses inherit os.environ, so these env vars reach export.py.
        monkeypatch.setenv("GITHUB_RUN_ID", "synthetic-round-trip-probe")
        monkeypatch.setenv("GITHUB_SHA", "0" * 40)
        ret = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "export.py"),
                str(src_db),
                str(exported_dir),
            ],
            capture_output=True,
            text=True,
        )
        assert ret.returncode == 0, f"export failed: {ret.stderr}"
        assert (exported_dir / f"{key}.json").exists()
        assert (exported_dir / MANIFEST_NAME).exists(), (
            "export under GITHUB_RUN_ID emitted no manifest — the record job's "
            "provenance birth certificate is missing (#2323)"
        )

        # 3. Import (JSON -> DB).
        ret = subprocess.run(
            [
                sys.executable,
                str(SCRIPTS / "import.py"),
                str(exported_dir),
                str(dst_db),
                "--purge",
            ],
            capture_output=True,
            text=True,
        )
        assert ret.returncode == 0, f"import failed: {ret.stderr}"

        # 4. Read back from the destination DB. The value must equal the source.
        dst = diskcache.Cache(str(dst_db))
        try:
            assert key in set(dst.iterkeys())
            round_tripped = dst[key]
        finally:
            dst.close()
        assert round_tripped == cassette["value"], (
            f"round-trip changed the {shape}-shaped value — export/import "
            "scripts are not lossless; check for pydantic / JSON normalization "
            "drift."
        )
