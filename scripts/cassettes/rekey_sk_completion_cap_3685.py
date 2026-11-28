# -*- coding: utf-8 -*-
"""Rekey the SK cassette the #3685 completion-cap key change moves.

Why this script exists
----------------------
#3685 adds ``max_completion_tokens`` to ``_serialize_settings``. The two SK
sites pass their cap under that spelling on ``OpenAIPromptExecutionSettings``
— the Sherlock enquiry agent (2000), the logic assistant (400). SK's kernel
promotes the value from the site's ``extension_data`` to a declared field of
``OpenAIChatPromptExecutionSettings`` before the wrapper keys the call, so the
cap was ALREADY on the wire: the request did not change, only the key name
moved, and the recorded response is still the right response. This script
moves each affected cassette at ZERO cost — no LLM call, no record mode.

Measured on the band's population (2026-11-25, record run 45513278355's set):
one capped SK lookup in 1745 — the Sherlock site at cap 2000, reached once by
the cluedo group-chat test; no Watson (cap 400) consumer in the band. The
fix's band run shows exactly one miss, and this script moves exactly that
cassette.

What it does
------------
1. Imports the committed fixtures into a scratch replay DB (``import.py``,
   provenance gate included) and runs the replay band's OWN pytest argv — read
   from ``requires_api_band.yml`` through ``band_record_argv.replay_argv`` —
   in replay mode with ``rekey_capture`` loaded. Replay misses raise
   ``LLMCacheMiss`` (the tests degrade to their fallback path) so the run
   makes no call. The capture plugin records, per missed key, the serialized
   ``messages`` + ``settings`` the live derivation consumed.
2. For each missed key it rebuilds the PRE-#3685 key from the same inputs
   (the settings block minus ``max_completion_tokens`` — unset adds nothing,
   so that is exactly what the old derivation hashed) and loads the cassette
   stored under it.
3. Provenance, per cassette:
   - the captured settings block must carry an integer cap (a miss without it
     is another drift: named and refused, never relabelled);
   - the cassette under the pre-#3685 key must exist (a call that was never
     recorded cannot be covered by a rename);
   - a recorded completion usage may not exceed the cap.
   The request/cap link itself rides the code — in record mode the very
   settings object that computed the key is the one handed to the inner
   service (``llm_cache.py``, RECORD branch) — and is pinned by
   ``tests/unit/argumentation_analysis/services/test_sk_key_completion_cap_3685.py``,
   whose wire witness reads the request body that went out.
4. Writes ``<new_key>.json`` with the value byte-identical: the old file's
   bytes with the single ``"key"`` literal swapped.
5. The old files are NOT touched here. Whether any derivation still reaches
   them is decided by measurement (band green with them absent from the
   import = unreachable), then ``--refresh-manifest-only`` re-binds
   MANIFEST.json to the final set — without it the #2323 import gate reddens
   on count/digest drift.

Usage
-----
    python scripts/cassettes/rekey_sk_completion_cap_3685.py [--dry-run]
    python scripts/cassettes/rekey_sk_completion_cap_3685.py --refresh-manifest-only [--note ...]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURES_DIR = REPO / "tests" / "fixtures" / "llm_cassettes"
IMPORT_SCRIPT = Path(__file__).resolve().parent / "import.py"
DEFAULT_SCRATCH = REPO / ".cache" / "llm_rekey_sk_cap_3685"
BAND_YML = REPO / ".github" / "workflows" / "requires_api_band.yml"

FIELD = "max_completion_tokens"

# Deliberately not a secret (same dummy as the replay-band job): satisfies the
# requires_api presence check while leaving nothing real to call.
DUMMY_KEY = "replay-band-no-live-anti-1019"

# The route the record run and the replay band both resolve (#3679). The model
# id is part of the raw-path key; the SK-key material this script rebuilds
# does not carry it, but the replay population must build the same requests.
NAMED_ROUTE_MODEL = "claude-haiku-5-5"

# A Claude Code seat exports ANTHROPIC_BASE_URL (its own proxy), which
# ``llm_service`` reads as the named route: a non-Anthropic base URL turns
# ``response_format`` on for JSON calls and every raw-path key drifts
# (measured 2026-11-25: 20 misses that CI does not see). The capture env must
# be the band's, not the seat's. The preflight guide gap this exposes is its
# own issue; until it lands, the child env drops the variable here.
SEAT_ROUTE_VARS = ("ANTHROPIC_BASE_URL",)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "--scratch-dir",
        type=Path,
        default=DEFAULT_SCRATCH,
        help=f"scratch replay DB + capture output (wiped first). Default: {DEFAULT_SCRATCH}",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="capture + provenance checks, write nothing",
    )
    p.add_argument(
        "--refresh-manifest-only",
        action="store_true",
        help="no capture run: only re-bind MANIFEST.json to the current set "
        "(run after the prune-or-keep decision so the import gate verifies)",
    )
    p.add_argument(
        "--note",
        default="rekey: SK completion-cap key #3685 (max_completion_tokens)",
        help="note recorded in the manifest's sk_patches entry",
    )
    return p.parse_args(argv)


def _key_from_payload(payload: str) -> tuple[str, dict, dict]:
    """Split a capture payload into (sha256 key, messages, settings block).

    The rebuild mirrors ``compute_cache_key`` exactly: same ``json.dumps``
    flags over ``{"messages": ..., "settings": ...}``.
    """
    data = json.loads(payload)
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return (
        hashlib.sha256(raw.encode("utf-8")).hexdigest(),
        data["messages"],
        data["settings"],
    )


def _pre_3685_block(settings_block: dict) -> dict:
    """The settings block the pre-#3685 serializer produced for the same call.

    The cap is the only field #3685 added, and unset adds nothing: dropping it
    from the captured block is exactly what the old derivation hashed.
    """
    return {k: v for k, v in settings_block.items() if k != FIELD}


def _completion_tokens_in_value(value) -> list[int]:
    """Completion token counts a cassette value records about itself."""
    counts: list[int] = []
    entries = value if isinstance(value, list) else [value]
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        metadata = entry.get("metadata")
        if not isinstance(metadata, dict):
            continue
        usage = metadata.get("usage")
        if isinstance(usage, dict) and isinstance(usage.get("completion_tokens"), int):
            counts.append(usage["completion_tokens"])
    return counts


def _band_argv(scratch_dir: Path) -> list[str]:
    """The replay band's own pytest argv, read from the workflow file.

    The marker token is filled in; the junit output is redirected into the
    scratch dir (the capture run must not leave the band's report behind).
    """
    from scripts.cassettes.band_record_argv import replay_argv

    marker, argv = replay_argv(BAND_YML.read_text(encoding="utf-8"))
    filled: list[str] = []
    for token in argv:
        if token == "$marker":
            filled.append(marker)
        elif token.startswith("--junitxml="):
            filled.append(f"--junitxml={scratch_dir / 'capture_junit.xml'}")
        else:
            filled.append(token)
    return filled


def _capture(scratch_dir: Path) -> tuple[Path, Path]:
    """Import fixtures into a scratch DB, run the capture tests, return
    (capture report, replay stats)."""
    if scratch_dir.exists():
        shutil.rmtree(scratch_dir)
    scratch_dir.mkdir(parents=True)

    ret = subprocess.run(
        [
            sys.executable,
            str(IMPORT_SCRIPT),
            str(FIXTURES_DIR),
            str(scratch_dir),
            "--purge",
        ],
        capture_output=True,
        text=True,
    )
    sys.stdout.write(ret.stdout)
    if ret.returncode != 0:
        sys.stderr.write(ret.stderr)
        raise SystemExit(f"import.py failed (rc={ret.returncode}) — DB not populated")

    capture_out = scratch_dir / "capture.json"
    stats_out = scratch_dir / "replay_stats.json"
    env = dict(os.environ)
    for name in SEAT_ROUTE_VARS:
        env.pop(name, None)
    env.update(
        {
            "LLM_CACHE_MODE": "replay",
            "LLM_CACHE_DIR": str(scratch_dir),
            "OPENAI_API_KEY": DUMMY_KEY,
            "ANTHROPIC_API_KEY": DUMMY_KEY,
            "ANTHROPIC_CHAT_MODEL_ID": NAMED_ROUTE_MODEL,
            # The band's env has no .env and no OpenRouter pair: the plugin
            # neutralises the seat's .env (CI condition), and a real key in
            # the seat's environment must not route a single call.
            "REKEY_CAPTURE_NO_DOTENV": "1",
            "REPLAY_GATE": "1",
            "REPLAY_STATS_OUT": str(stats_out),
            "REKEY_CAPTURE_OUT": str(capture_out),
            "PYTHONPATH": str(REPO),
        }
    )
    for name in ("OPENROUTER_API_KEY", "OPENROUTER_BASE_URL"):
        env.pop(name, None)
    ret = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *_band_argv(scratch_dir),
            "-p",
            "scripts.cassettes.rekey_capture",
            "-q",
            "--timeout=900",
            "--timeout-method=thread",
            "-p",
            "no:cacheprovider",
        ],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=3600,
    )
    tail = "\n".join(ret.stdout.splitlines()[-15:])
    print(tail)
    if not capture_out.exists():
        sys.stderr.write(ret.stderr[-2000:])
        raise SystemExit(
            f"capture run produced no report (pytest rc={ret.returncode}) — "
            "nothing was migrated"
        )
    return capture_out, stats_out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    # Bound early: running this file as a script puts scripts/cassettes on
    # sys.path, and binding the name before the app imports is immune to the
    # downstream ModuleNotFoundError that a late import dies of.
    from scripts.cassettes.export import refresh_manifest

    if args.refresh_manifest_only:
        return 0 if refresh_manifest(FIXTURES_DIR, note=args.note) else 1

    report_path, stats_path = _capture(args.scratch_dir)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    stats = (
        json.loads(stats_path.read_text(encoding="utf-8"))
        if stats_path.exists()
        else {}
    )
    records = [r for r in report["records"] if "payload" in r and r["path"] == "sk"]
    print(
        f"\ncaptured misses: {len(report['misses'])} ({len(records)} attributed, "
        f"SK path) — replay stats miss_replay={stats.get('miss_replay', '?')}"
    )
    if len(records) != len(report["misses"]):
        print(
            f"REFUSED: {len(report['misses']) - len(records)} miss(es) came back "
            "unattributed or not on the SK path — this script rekeys SK "
            "completion-cap drifts only. Nothing was migrated.",
            file=sys.stderr,
        )
        return 4

    # Group by distinct new key, sanity-checking the rebuild against the key
    # the live derivation reported for the same payload.
    pairs: dict[str, dict] = {}
    for rec in records:
        try:
            rebuilt, messages, settings_block = _key_from_payload(rec["payload"])
        except (json.JSONDecodeError, KeyError) as exc:
            print(
                f"UNREBUILDABLE miss {rec.get('key', '?')[:16]}: {exc!r}",
                file=sys.stderr,
            )
            return 4
        if rebuilt != rec["key"]:
            print(
                f"REBUILD DIVERGES for {rec['key'][:16]}: payload hashes to "
                f"{rebuilt[:16]} — the rebuild does not mirror the live derivation",
                file=sys.stderr,
            )
            return 4
        entry = pairs.setdefault(
            rebuilt,
            {
                "settings": settings_block,
                "messages": messages,
                "calls": 0,
                "stacks": [],
            },
        )
        entry["calls"] += 1
        entry["stacks"].append(rec["stack"][-2:])

    failures: list[str] = []
    moved: list[dict] = []
    for new_key in sorted(pairs):
        info = pairs[new_key]
        cap = info["settings"].get(FIELD)
        if not isinstance(cap, int):
            failures.append(
                f"{new_key[:16]}: the new key carries no integer {FIELD} — the "
                "miss is not a completion-cap drift"
            )
            continue
        old_block = _pre_3685_block(info["settings"])
        old_raw = json.dumps(
            {"messages": info["messages"], "settings": old_block},
            sort_keys=True,
            ensure_ascii=False,
        )
        old_key = hashlib.sha256(old_raw.encode("utf-8")).hexdigest()
        old_path = FIXTURES_DIR / f"{old_key}.json"
        new_path = FIXTURES_DIR / f"{new_key}.json"
        if not old_path.exists():
            failures.append(
                f"{new_key[:16]}: no cassette under the pre-#3685 key "
                f"{old_key[:16]} — this call was never recorded under the "
                "cap-blind key, the rekey cannot cover it"
            )
            continue
        if new_path.exists():
            print(f"  {new_key[:16]}: already rekeyed (skipped)")
            continue
        old_bytes = old_path.read_bytes()
        value = json.loads(old_bytes)["value"]

        counts = _completion_tokens_in_value(value)
        if counts and max(counts) > cap:
            failures.append(
                f"{old_key[:16]} -> {new_key[:16]}: the cassette records "
                f"{max(counts)} completion token(s), above the {cap} cap it "
                "would be relabelled to — not the response of this request"
            )
            continue
        basis = f"cap {cap}; recorded completion tokens {counts or 'none'}" f" (≤ cap)"

        old_lit = f'"key": "{old_key}"'.encode("utf-8")
        key_lit = f'"{old_key}"'.encode("utf-8")
        lit_count = old_bytes.count(key_lit)
        if lit_count != 1:
            failures.append(
                f"{old_key[:16]}: the key literal appears {lit_count}x in the "
                "file — byte-swap is not safe"
            )
            continue
        if not args.dry_run:
            # Bytes in, bytes out: text-mode newline translation must never
            # touch anything but the swapped literal.
            new_path.write_bytes(
                old_bytes.replace(old_lit, f'"key": "{new_key}"'.encode("utf-8"))
            )
        moved.append(
            {
                "old": old_key[:16],
                "new": new_key[:16],
                "calls": info["calls"],
                "cap": cap,
                "basis": basis,
            }
        )

    print(
        f"\nmoved: {len(moved)} cassette(s), {sum(m['calls'] for m in moved)} call(s)"
    )
    for m in moved:
        print(
            f"  {m['old']} -> {m['new']}  calls={m['calls']}  cap={m['cap']}  "
            f"[{m['basis']}]"
        )
    if failures:
        print(
            f"\n{len(failures)} pair(s) came back un-relabelled (coordinator "
            "decision required):",
            file=sys.stderr,
        )
        for f in failures:
            print(f"  - {f}", file=sys.stderr)

    if moved:
        print(
            "\nNext: decide the fate of the old files by measurement (band "
            "green with them absent = unreachable), then re-bind the "
            "manifest: python scripts/cassettes/rekey_sk_completion_cap_3685.py "
            "--refresh-manifest-only"
        )
    return 4 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
