"""Round-trip probe for LLM cassettes (#1603).

Proves that an LLM response, once recorded into a `diskcache` runtime DB,
can be exported to JSON, then imported into a fresh DB, and replayed
without making any outbound API call. The anti-#1019 metric is `live == 0`
in replay: a non-zero value means a cache miss silently fell through to
the API.

The test is hermetic — it does NOT call the real LLM. It uses the cassette
committed to `tests/fixtures/llm_cassettes/` and proves it round-trips.

If new cassettes are committed, extend ``CASSETTE_FIXTURE`` to the most
recent key (sorted by mtime) so the test exercises the latest fixture.
The intent is to *verify* the export/import scripts, not to re-record the
fixture — re-recording is a manual workflow described in
``tests/fixtures/llm_cassettes/README.md``.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[4]  # tests/unit/.../test_*.py -> repo root
SCRIPTS = REPO / "scripts" / "cassettes"
FIXTURES_DIR = REPO / "tests" / "fixtures" / "llm_cassettes"


def _list_cassette_keys() -> list[str]:
    """Return cassette file stems (sha256 keys) sorted by mtime, newest first."""
    return sorted(
        (p.stem for p in FIXTURES_DIR.glob("*.json")),
        key=lambda stem: (FIXTURES_DIR / f"{stem}.json").stat().st_mtime,
        reverse=True,
    )


class TestCassetteRoundTrip:
    """Recorded cassettes must replay without any outbound API call."""

    def test_at_least_one_cassette_is_committed(self):
        """The fixture directory has at least one cassette.

        If this fails, either the cassettes were never recorded or they
        were committed to a different path. See
        ``tests/fixtures/llm_cassettes/README.md``.
        """
        cassettes = list(FIXTURES_DIR.glob("*.json"))
        assert cassettes, f"No cassettes found in {FIXTURES_DIR}"

    def test_cassette_value_is_well_formed(self):
        """Each cassette is ``{"key": sha256, "value": list | dict}``."""
        for path in FIXTURES_DIR.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            assert isinstance(data, dict), path
            assert "key" in data and "value" in data, path
            assert isinstance(data["key"], str) and len(data["key"]) == 64, path
            assert isinstance(data["value"], (list, dict)), path

    def test_export_then_import_round_trip_preserves_value(self, tmp_path: Path):
        """A cassette reaches a fresh DB identical to the source.

        Probes the two scripts as plain subprocesses (matches the workflow
        committed by po-2025 in #1603). Probes the *first* committed
        cassette — the value is bytes-identical after the round trip.
        """
        keys = _list_cassette_keys()
        assert keys, "no cassette fixture present"
        first_key = keys[0]

        src_db = tmp_path / "src_db"
        dst_db = tmp_path / "dst_db"
        src_db.mkdir()
        dst_db.mkdir()

        # 1. Re-create source DB from the cassette fixture (one entry).
        import diskcache  # type: ignore[import-not-found]

        src = diskcache.Cache(str(src_db))
        try:
            cassette = json.loads(
                (FIXTURES_DIR / f"{first_key}.json").read_text(encoding="utf-8")
            )
            src.set(cassette["key"], cassette["value"])
        finally:
            src.close()

        # 2. Export (DB → JSON onto a fresh dir).
        exported_dir = tmp_path / "exported"
        exported_dir.mkdir()
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
        assert (exported_dir / f"{first_key}.json").exists()

        # 3. Import (JSON → DB).
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
            assert first_key in set(dst.iterkeys())
            round_tripped = dst[first_key]
        finally:
            dst.close()
        assert round_tripped == cassette["value"], (
            "round-trip changed the value — export/import scripts are not "
            "lossless; check for pydantic / JSON normalization drift."
        )


class TestCassetteReplayHitsCache:
    """End-to-end: the cached LLM response replays without `live`."""

    def test_replay_path_uses_cache(self, monkeypatch, tmp_path: Path):
        """Given a populated cache, replay yields `hit=1, live=0`."""
        keys = _list_cassette_keys()
        if not keys:
            pytest.skip("no cassette committed")
        first_key = keys[0]

        # Configure llm_cache to use a fresh DB populated from the cassette.
        replay_db = tmp_path / "replay_db"
        replay_db.mkdir()
        _populate_db_from_first_cassette(replay_db, first_key)

        monkeypatch.setenv("LLM_CACHE_MODE", "replay")
        monkeypatch.setenv("LLM_CACHE_DIR", str(replay_db))

        # Reload llm_cache + llm_service so the env vars take effect.
        import importlib
        import argumentation_analysis.services.llm_cache as llm_cache_mod
        importlib.reload(llm_cache_mod)

        assert llm_cache_mod.get_cache_mode() == "replay"
        llm_cache_mod.reset_cache_stats()

        # Spy on httpx so any outbound call would raise.
        import httpx
        real_send = httpx.AsyncClient.send

        async def anti_theatre(self, request, *a, **kw):
            if "openrouter" in str(request.url) or "openai.com" in str(request.url):
                raise RuntimeError(
                    f"OUTBOUND CALL DETECTED in replay mode to {request.url}"
                )
            return await real_send(self, request, *a, **kw)

        httpx.AsyncClient.send = anti_theatre
        try:
            from semantic_kernel import Kernel
            from argumentation_analysis.core.llm_service import create_llm_service
            from argumentation_analysis.plugins.narrative_synthesis_plugin import (
                NarrativeSynthesisPlugin,
            )
            from tests.unit.argumentation_analysis.plugins.test_narrate_convergence import (
                _convergent_state_json,
            )

            kernel = Kernel()
            # force_authentic=True: bypass the test-env mock so we exercise
            # the real CachedChatCompletion wrap (the cassette is the layer
            # under test, not the LLM provider).
            svc = create_llm_service(
                "narration_test_replay_unit", force_authentic=True
            )
            assert getattr(svc, "mode", None) == "replay", (
                "service was not wrapped in replay mode — cache wiring failed"
            )
            kernel.add_service(svc)
            plugin = NarrativeSynthesisPlugin(kernel=kernel)

            result = asyncio.run(
                plugin.narrate_convergence(state_json=_convergent_state_json())
            )
        finally:
            httpx.AsyncClient.send = real_send

        # Stats — anti-#1019: `live` must be 0 in replay.
        stats = llm_cache_mod.get_cache_stats()
        assert stats["live"] == 0, (
            f"replay triggered a live API call (live={stats['live']}); "
            "either the cache miss wasn't a hit or the cache.get returned None"
        )
        assert stats["hit"] >= 1, (
            f"replay did not hit the cache (hit={stats['hit']}); "
            f"miss_record={stats['miss_record']} miss_replay={stats['miss_replay']}"
        )
        assert result, "replay returned an empty string — cache value is broken"


def _populate_db_from_first_cassette(db_dir: Path, key: str) -> None:
    """Materialize the first cassette into a fresh diskcache DB."""
    import diskcache  # type: ignore[import-not-found]

    cassette = json.loads(
        (FIXTURES_DIR / f"{key}.json").read_text(encoding="utf-8")
    )
    cache = diskcache.Cache(str(db_dir))
    try:
        cache.set(cassette["key"], cassette["value"])
    finally:
        cache.close()
