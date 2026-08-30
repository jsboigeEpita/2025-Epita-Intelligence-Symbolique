# -*- coding: utf-8 -*-
"""Re-record the SK-path cassette for ``narrate_convergence`` (#1950).

Why this script exists
----------------------
The procedure documented in ``tests/fixtures/llm_cassettes/README.md`` used to
point at ``test_narrate_convergence.py::TestNarrateConvergenceIntegration``.
That test calls ``create_llm_service("narration_test")`` **without**
``force_authentic``, so under pytest it is mocked and records *nothing* — the
README said so itself, forty lines below the command. The documented command
could therefore never refresh an SK-path cassette, which is why the only
refresh ever performed had to be a throwaway script (#1950 defect 3).

This script is that workflow, made reproducible: it drives the real
``narrate_convergence`` with ``force_authentic=True`` in ``record`` mode over
the same synthetic fixture the tests use, then exports the resulting DB to the
committed fixture directory through ``export.py`` (which runs the blocking
privacy audit).

WHEN TO RUN IT
--------------
Only when ``TestCommittedCassettesStillReplay::test_replay_path_uses_cache``
reddens with the DRIFT message. That red means the production prompt moved and
the committed cassette no longer matches its key. It does **not** mean the code
is wrong.

⚠ This makes a REAL LLM call and costs money (order of $0.0005). Under #1603,
re-recording the broad cassette bands is barred until the record pass is
hermetic — this script deliberately records **one** SK-path cassette from a
purely synthetic fixture, which is the narrow case that exception covers. Do
not generalize it into a bulk re-record.

Usage
-----
    python scripts/cassettes/record_sk_cassette.py            # record + export
    python scripts/cassettes/record_sk_cassette.py --no-export  # record only
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_CACHE_DIR = REPO / ".cache" / "llm_record_sk"
FIXTURES_DIR = REPO / "tests" / "fixtures" / "llm_cassettes"
EXPORT_SCRIPT = Path(__file__).resolve().parent / "export.py"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE_DIR,
        help=f"scratch record DB (wiped first). Default: {DEFAULT_CACHE_DIR}",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=FIXTURES_DIR,
        help=f"fixture dir to export into. Default: {FIXTURES_DIR}",
    )
    p.add_argument(
        "--no-export",
        action="store_true",
        help="record into the scratch DB but do not export to the fixture dir",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # The repo root must be importable: this script drives production code and
    # reuses the tests' synthetic fixture builder.
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))

    from dotenv import load_dotenv

    load_dotenv(REPO / ".env")

    cache_dir: Path = args.cache_dir
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True)

    # Set BEFORE importing llm_cache: CACHE_DIR is frozen at import time.
    os.environ["LLM_CACHE_MODE"] = "record"
    os.environ["LLM_CACHE_DIR"] = str(cache_dir)

    import argumentation_analysis.services.llm_cache as llm_cache_mod

    llm_cache_mod.CACHE_DIR = cache_dir
    llm_cache_mod.reset_raw_cache()
    mode = llm_cache_mod.get_cache_mode()
    if mode != "record":
        print(f"ERROR: cache mode is {mode!r}, expected 'record'", file=sys.stderr)
        return 1
    llm_cache_mod.reset_cache_stats()

    from semantic_kernel import Kernel

    from argumentation_analysis.core.llm_service import create_llm_service
    from argumentation_analysis.plugins.narrative_synthesis_plugin import (
        NarrativeSynthesisPlugin,
    )
    from tests.unit.argumentation_analysis.plugins.test_narrate_convergence import (
        _convergent_state_json,
    )

    kernel = Kernel()
    # force_authentic=True is the whole point: without it the service is mocked
    # under a test-shaped environment and records nothing.
    svc = create_llm_service("narration_record_sk", force_authentic=True)
    svc_mode = getattr(svc, "mode", None)
    if svc_mode != "record":
        print(
            f"ERROR: service was not wrapped in record mode (mode={svc_mode!r}); "
            "cache wiring failed — nothing would be recorded.",
            file=sys.stderr,
        )
        return 1
    kernel.add_service(svc)

    plugin = NarrativeSynthesisPlugin(kernel=kernel)
    state_json = _convergent_state_json()
    print(f"fixture (synthetic, {len(state_json)} chars): {state_json[:160]}...")

    result = asyncio.run(plugin.narrate_convergence(state_json=state_json))

    stats = llm_cache_mod.get_cache_stats()
    print(f"cache stats after record: {stats}")

    # narrate_convergence swallows LLM failures and falls back to the template
    # narrative, so a non-empty result is NOT proof that anything was recorded.
    # The write counter is.
    written = sorted(p.name for p in cache_dir.rglob("*") if p.is_file())
    if not stats.get("miss_record") and not written:
        print(
            "ERROR: nothing was recorded. narrate_convergence falls back to its "
            "template on any LLM error, so an apparently successful run proves "
            "nothing — check the API key and the service mode above.",
            file=sys.stderr,
        )
        return 1

    print(f"recorded narration ({len(result)} chars): {result[:300]}...")

    if args.no_export:
        print(f"\nrecorded into {cache_dir} (export skipped: --no-export)")
        return 0

    before = {p.name for p in args.out.glob("*.json")}
    ret = subprocess.run(
        [sys.executable, str(EXPORT_SCRIPT), str(cache_dir), str(args.out)],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(ret.stdout)
    if ret.returncode != 0:
        sys.stderr.write(ret.stderr)
        print(
            "\nexport failed — most often the blocking privacy audit "
            "(scripts/cassettes/privacy.py). Do NOT retry with --allow-unsafe: "
            "open an issue and discuss documented-bounded leakage first.",
            file=sys.stderr,
        )
        return ret.returncode

    after = {p.name for p in args.out.glob("*.json")}
    new = sorted(after - before)
    print(f"\nnew cassette file(s) in {args.out}: {new or '(none — key unchanged)'}")
    if new:
        print(
            "Next: delete the cassette this one supersedes (the previous "
            "list-shaped file), then commit. A stale sibling is harmless to the "
            "test — it loads them all — but it is dead weight in the fixture dir."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
