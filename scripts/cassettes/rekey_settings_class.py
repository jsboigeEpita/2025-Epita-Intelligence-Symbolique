# -*- coding: utf-8 -*-
"""Rekey the SK-path cassettes the #2853 settings-class forwarding moved.

Why this script exists
----------------------
PR #2853 forwards ``get_prompt_execution_settings_class()`` to the wrapped
service. Kernel-built settings — the ``kernel_function_from_prompt`` path —
are therefore instantiated as ``OpenAIChatPromptExecutionSettings`` instead
of the generic base class, and ``_serialize_settings`` now reads
``ai_model_id`` as a top-level field (it used to sit in ``extension_data``,
invisible). The SK cache key became what it always should have been — a
function of the effective request, model included — and the cassettes
recorded under the old model-blind key stopped being found: the replay band
reddened with ``miss_replay=9`` (9 calls, 5 distinct keys, in the two
authentic logic-agent test files).

The request did not change — measured on both sides,
``prepare_settings_dict()`` gives the same dict — so the recorded responses
are still the right responses. Only the key name moved. This script moves
each cassette to its new key at ZERO cost: no LLM call, no record mode (the
rekey decision, coordinator comment on PR #2853). The move CASCADES: the
first 9 misses degraded their tests onto fallback paths, so calls downstream
of a miss never reached the cache at all. Each rekeyed cassette lets its
test replay further and exposes the next model-blind key — the 5 first-order
cassettes unmasked 5 more (18 calls total over 10 cassettes, measured
2026-09-30). Re-run the script until it reports ``moved: 0`` (fixpoint).

What it does
------------
1. Imports the committed fixtures into a scratch replay DB (``import.py``,
   provenance gate included) and runs the two authentic test files in
   replay mode against it, with ``rekey_capture`` loaded. Replay misses
   raise ``LLMCacheMiss`` — the tests degrade to their fallback path — so
   the run makes no call. The capture plugin records, per missed key, the
   serialized ``messages`` + ``settings`` the live derivation consumed.
2. For each distinct missed key it rebuilds the PRE-retouch key from the
   same inputs (settings block reduced to ``service_id`` — the only field a
   generic ``PromptExecutionSettings`` exposes to the serializer) and loads
   the cassette stored under it.
3. Provenance, per cassette: the relabel must prove the cassette answered
   the model the new key carries (the captured ``ai_model_id``).
   - If the value records a model (raw-path dict, or SK ``metadata.model``),
     it must equal ``ai_model_id`` exactly.
   - The SK-path serializer never wrote a model (measured over the set:
     123/123 SK values carry none, 537/537 raw values carry
     ``gpt-5.6-luna``). For those, the script anchors the cassette to the
     record session: every cassette in the set that records a model must
     record exactly ``ai_model_id`` (no cassette answered another model),
     and the cassette's ``metadata.created`` must fall inside that session's
     ``created`` span. A cassette outside the span, or any foreign model in
     the set, is named and the run stops — that pair goes back to the
     coordinator, unrelabelled.
4. Writes ``<new_key>.json`` with the value byte-identical: the old file's
   bytes with the single ``"key"`` literal swapped. A round-trip through
   ``json`` is never trusted to preserve bytes.
5. The old files are NOT touched here. Whether any derivation still reaches
   them is decided by measurement (band green with them absent from the
   import = unreachable), then ``--refresh-manifest-only`` re-binds
   MANIFEST.json to the final set — without it the #2323 import gate
   reddens on count/digest drift.

Usage
-----
    python scripts/cassettes/rekey_settings_class.py [--dry-run]
    python scripts/cassettes/rekey_settings_class.py --refresh-manifest-only [--note ...]
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
DEFAULT_SCRATCH = REPO / ".cache" / "llm_rekey_settings_class"

# The two files whose authentic tests produced the 9 misses (band 2026-09-29,
# prefixes 86743d2c x3 / 3a6d2e3d x3 / ef85006e / 2e6d7772 / 44d872b1). A
# superset of their calls is fine — every non-miss call hits its cassette.
CAPTURE_TESTS = (
    "tests/agents/core/logic/test_modal_logic_agent_authentic.py",
    "tests/agents/core/logic/test_propositional_logic_agent_authentic.py",
)

# Deliberately not a secret (same dummy as the replay-band job): satisfies
# the requires_api presence check while leaving nothing real to call.
DUMMY_KEY = "replay-band-no-live-anti-1019"


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
        default="rekey: settings-class forwarding #2853",
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


def _pre_retouch_block(settings_block: dict) -> dict:
    """Settings block the pre-#2853 derivation saw for kernel-built settings.

    The generic ``PromptExecutionSettings`` exposes ``service_id`` to
    ``_serialize_settings``; ``ai_model_id`` lived in ``extension_data``,
    which the serializer never reads. Everything else (temperature etc.) was
    already None for these calls — the captured block carries only
    ``ai_model_id`` + ``service_id``.
    """
    block = {}
    if settings_block.get("service_id") is not None:
        block["service_id"] = settings_block["service_id"]
    return block


def _models_in_value(value) -> set[str]:
    """Models a cassette value records about itself, wherever it may carry one."""
    models: set[str] = set()
    if isinstance(value, dict) and isinstance(value.get("model"), str):
        models.add(value["model"])
    if isinstance(value, list):
        for item in value:
            md = item.get("metadata") if isinstance(item, dict) else None
            if isinstance(md, dict) and isinstance(md.get("model"), str):
                models.add(md["model"])
    return models


def _created_in_value(value):
    if isinstance(value, dict) and isinstance(value.get("created"), int):
        return value["created"]
    if isinstance(value, list):
        for item in value:
            md = item.get("metadata") if isinstance(item, dict) else None
            if isinstance(md, dict) and isinstance(md.get("created"), int):
                return md["created"]
    return None


def _session_anchor(fixtures_dir: Path, model: str) -> tuple[set[str], int, int]:
    """(models recorded anywhere in the set, min created, max created).

    The span covers the cassettes that record ``model`` — the sessions whose
    configured model is proven. Any model-bearing cassette naming something
    else is returned in the set for the caller to bounce on.
    """
    models: set[str] = set()
    span: list[int] = []
    for path in sorted(fixtures_dir.glob("*.json")):
        if path.name == "MANIFEST.json":
            continue
        value = json.loads(path.read_text(encoding="utf-8"))["value"]
        models |= _models_in_value(value)
        created = _created_in_value(value)
        if _models_in_value(value) == {model} and created is not None:
            span.append(created)
    if not span:
        return models, -1, -1
    return models, min(span), max(span)


def _capture(scratch_dir: Path) -> Path:
    """Import fixtures into a scratch DB, run the capture tests, return the report."""
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
    env = dict(os.environ)
    env.update(
        {
            "LLM_CACHE_MODE": "replay",
            "LLM_CACHE_DIR": str(scratch_dir),
            "OPENAI_API_KEY": DUMMY_KEY,
            "REKEY_CAPTURE_OUT": str(capture_out),
            "PYTHONPATH": str(REPO),
        }
    )
    ret = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *CAPTURE_TESTS,
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
        timeout=1800,
    )
    tail = "\n".join(ret.stdout.splitlines()[-15:])
    print(tail)
    if not capture_out.exists():
        sys.stderr.write(ret.stderr[-2000:])
        raise SystemExit(
            f"capture run produced no report (pytest rc={ret.returncode}) — "
            "nothing was migrated"
        )
    return capture_out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    # Bound early (see record_sk_cassette.py's import-order note).
    from scripts.cassettes.export import refresh_manifest

    if args.refresh_manifest_only:
        return 0 if refresh_manifest(FIXTURES_DIR, note=args.note) else 1

    report_path = _capture(args.scratch_dir)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    records = [r for r in report["records"] if "payload" in r and r["path"] == "sk"]
    print(
        f"\ncaptured misses: {len(report['misses'])} ({len(records)} attributed, SK path)"
    )

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
    anchors: dict[str, tuple[set[str], int, int]] = {}
    for new_key in sorted(pairs):
        info = pairs[new_key]
        ai_model = info["settings"].get("ai_model_id")
        if not isinstance(ai_model, str) or not ai_model:
            failures.append(
                f"{new_key[:16]}: the new key carries no ai_model_id — the "
                "relabel would bind to no model"
            )
            continue
        old_block = _pre_retouch_block(info["settings"])
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
                f"{new_key[:16]}: no cassette under the pre-retouch key "
                f"{old_key[:16]} — this call was never recorded, the rekey "
                "cannot cover it"
            )
            continue
        if new_path.exists():
            print(f"  {new_key[:16]}: already rekeyed (skipped)")
            continue
        old_bytes = old_path.read_bytes()
        value = json.loads(old_bytes)["value"]

        models = _models_in_value(value)
        if models:
            basis = f"value records model {sorted(models)}"
            if models != {ai_model}:
                failures.append(
                    f"{old_key[:16]} -> {new_key[:16]}: cassette answered "
                    f"{sorted(models)}, the new key carries {ai_model!r} — "
                    "cannot be relabelled"
                )
                continue
        else:
            if ai_model not in anchors:
                anchors[ai_model] = _session_anchor(FIXTURES_DIR, ai_model)
            set_models, span_min, span_max = anchors[ai_model]
            created = _created_in_value(value)
            if set_models - {ai_model}:
                failures.append(
                    f"{old_key[:16]} -> {new_key[:16]}: value carries no model "
                    f"and the set records foreign models {sorted(set_models - {ai_model})} "
                    "— session anchor broken"
                )
                continue
            if created is None or not (span_min <= created <= span_max):
                failures.append(
                    f"{old_key[:16]} -> {new_key[:16]}: value carries no model "
                    f"and created={created} falls outside the {ai_model} session "
                    f"span [{span_min}, {span_max}] — cannot be anchored"
                )
                continue
            basis = (
                f"SK value carries no model; anchored to the record session "
                f"(created={created} in [{span_min}, {span_max}], set records "
                f"only {ai_model})"
            )

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
                "model": ai_model,
                "basis": basis,
            }
        )

    print(
        f"\nmoved: {len(moved)} cassette(s), {sum(m['calls'] for m in moved)} call(s)"
    )
    for m in moved:
        print(
            f"  {m['old']} -> {m['new']}  calls={m['calls']}  model={m['model']}  [{m['basis']}]"
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
            "manifest: python scripts/cassettes/rekey_settings_class.py "
            "--refresh-manifest-only"
        )
    return 4 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
