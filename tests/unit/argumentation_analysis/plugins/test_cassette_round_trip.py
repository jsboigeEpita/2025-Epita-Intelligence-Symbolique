"""Cassette probes for the LLM replay loop (#1603), split by failure regime (#1950).

This module carries **two properties that must not share a test**, because a
red on one calls for the opposite action of a red on the other:

- **A — do the export/import scripts round-trip losslessly?**
  ``TestExportImportScriptsRoundTrip``. Must ALWAYS be green. It builds its
  own synthetic ``(key, value)`` pairs, so it depends on no production
  prompt, no quality contract, and not even on which cassettes are
  committed. A red here means the scripts are broken — fix the scripts.

- **B — are the committed cassettes still fresh w.r.t. the production
  prompt?** ``TestCommittedCassettesStillReplay``. This is a **drift
  detector**, and it is *meant* to redden when a contract changes. A red
  here means: RE-RECORD the cassette. It does NOT mean the code is wrong.

Fusing them (the pre-#1950 shape) made B block any PR that legitimately
improved a contract: #1942/#1946 changed the quality wording, that wording
descends into the ``narrate_convergence`` prompt, the prompt is hashed into
the cache key, so the cassette recorded against the old contract could no
longer replay — and three PRs were held on a test that was telling the truth
about the wrong thing.

How B actually detects drift. ``narrate_convergence`` catches every exception
around ``invoke_prompt`` and falls back to the template narrative (see
``narrative_synthesis_plugin.py``), so on a cache miss the call still
*succeeds* and returns a non-empty string; and ``live`` stays 0 because replay
mode raises instead of calling out. The only signal that survives that
fallback is the ``hit`` counter — assertions on the result, or on ``live``
alone, cannot see the drift.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]  # tests/unit/.../test_*.py -> repo root
SCRIPTS = REPO / "scripts" / "cassettes"
FIXTURES_DIR = REPO / "tests" / "fixtures" / "llm_cassettes"

RECORD_SCRIPT = "python scripts/cassettes/record_sk_cassette.py"


def _cassette_stems(*, value_is: str | None = None) -> list[str]:
    """Return cassette file stems (sha256 keys), sorted by stem.

    ``value_is="list"`` filters to SK-path cassettes (role/content lists — the
    shape ``_deserialize_response`` expects); ``value_is="dict"`` filters to
    raw-path cassettes (``ChatCompletion.model_dump()`` dicts). The fixture dir
    mixes both shapes since the pipeline lane records raw-path values (#1603).

    Sorted by **stem**, deliberately not by mtime (#1950 defect 2). On a fresh
    ``git clone`` every file gets essentially the same mtime, so mtime order is
    arbitrary; the pre-#1950 code took ``[0]`` of that order and stayed
    deterministic only by the accident of there being exactly one list-shaped
    cassette. No caller selects an element any more — B loads them all — but a
    stable order keeps failure output reproducible.
    """
    stems = [p.stem for p in FIXTURES_DIR.glob("*.json")]
    if value_is is not None:
        want = list if value_is == "list" else dict
        stems = [
            s
            for s in stems
            if isinstance(
                json.loads((FIXTURES_DIR / f"{s}.json").read_text(encoding="utf-8"))[
                    "value"
                ],
                want,
            )
        ]
    return sorted(stems)


class TestCommittedCassettesAreWellFormed:
    """Shape invariants on what is committed. Independent of A and B."""

    def test_at_least_one_cassette_is_committed(self):
        """The fixture directory has at least one cassette.

        If this fails, either the cassettes were never recorded or they were
        committed to a different path. See
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
    def test_round_trip_preserves_a_synthetic_value(self, shape: str, tmp_path: Path):
        """A synthetic value reaches a fresh DB identical to the source.

        Probes the two scripts as plain subprocesses (matches the workflow
        committed by po-2025 in #1603), once per cassette shape.
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

        # 2. Export (DB -> JSON onto a fresh dir).
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


class TestCommittedCassettesStillReplay:
    """Property B — drift detector between committed cassettes and the prompt.

    A red here is NOT a code defect. It means the production prompt moved and
    the committed cassette no longer matches it. The expected action is to
    re-record. Do not answer it with ``xfail(strict=True)`` (which swallows any
    outcome) or a skip (worse than a red — it goes invisible).
    """

    def test_replay_path_uses_cache(self, monkeypatch, tmp_path: Path):
        """Given the committed SK-path cassettes, replay yields hit>=1, live=0."""
        # The SK-service path deserializes LIST values (role/content). A
        # raw-path DICT cassette would iterate its keys and crash — so only
        # list-shaped cassettes are loaded here (#1603).
        stems = _cassette_stems(value_is="list")
        if not stems:
            pytest.skip("no SK-path (list-valued) cassette committed")

        # Load them ALL. There is no "pick one" step left to be non-deterministic
        # about (#1950 defect 2): committing a second list-shaped cassette can no
        # longer change which one is exercised, because every one is present.
        replay_db = tmp_path / "replay_db"
        replay_db.mkdir()
        _populate_db(replay_db, stems)

        monkeypatch.setenv("LLM_CACHE_MODE", "replay")
        monkeypatch.setenv("LLM_CACHE_DIR", str(replay_db))

        # CACHE_DIR is computed at llm_cache import time and used as the fallback
        # by CachedChatCompletion.__init__ — it does NOT re-read the env var.
        # When llm_cache was first imported during an earlier test (no env var
        # set), CACHE_DIR is frozen to the default and a later monkeypatch.setenv
        # has no effect on the wrap's cache_dir. Patch the module attribute too
        # so the wrap opens the populated replay_db, not an empty default.
        import argumentation_analysis.services.llm_cache as llm_cache_mod

        monkeypatch.setattr(llm_cache_mod, "CACHE_DIR", replay_db)
        llm_cache_mod.reset_raw_cache()

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
            # force_authentic=True: bypass the test-env mock so we exercise the
            # real CachedChatCompletion wrap (the cassette is the layer under
            # test, not the LLM provider).
            svc = create_llm_service("narration_test_replay_unit", force_authentic=True)
            assert (
                getattr(svc, "mode", None) == "replay"
            ), "service was not wrapped in replay mode — cache wiring failed"
            kernel.add_service(svc)
            plugin = NarrativeSynthesisPlugin(kernel=kernel)

            result = asyncio.run(
                plugin.narrate_convergence(state_json=_convergent_state_json())
            )
        finally:
            httpx.AsyncClient.send = real_send

        stats = llm_cache_mod.get_cache_stats()

        # anti-#1019: `live` must be 0 in replay.
        assert stats["live"] == 0, (
            f"replay triggered a live API call (live={stats['live']}); "
            "either the cache miss wasn't a hit or the cache.get returned None"
        )

        # The drift signal. `result` is NOT a witness here: narrate_convergence
        # catches the replay miss and returns the template narrative, so it
        # stays non-empty under full drift. Only `hit` sees it.
        assert stats["hit"] >= 1, (
            f"DRIFT, not a code defect: none of the {len(stems)} committed "
            "SK-path cassette(s) matched the current production prompt "
            f"(hit={stats['hit']}, miss_replay={stats['miss_replay']}).\n"
            "The narration prompt embeds the quality wording, so any deliberate "
            "contract change moves the cache key.\n"
            f"Expected action: RE-RECORD with `{RECORD_SCRIPT}`, then commit the "
            "new <sha256>.json (see tests/fixtures/llm_cassettes/README.md).\n"
            "Do NOT patch production to match a stale cassette, and do NOT "
            "answer this with xfail/skip."
        )
        assert result, "replay returned an empty string — cache value is broken"


def _populate_db(db_dir: Path, keys: list[str]) -> None:
    """Materialize the named cassettes into a fresh diskcache DB."""
    import diskcache  # type: ignore[import-not-found]

    cache = diskcache.Cache(str(db_dir))
    try:
        for key in keys:
            cassette = json.loads(
                (FIXTURES_DIR / f"{key}.json").read_text(encoding="utf-8")
            )
            cache.set(cassette["key"], cassette["value"])
    finally:
        cache.close()
