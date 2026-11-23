# -*- coding: utf-8 -*-
"""Rekey the SK-path cassettes the #3658 item 36c descent cap moved.

Why this script exists
----------------------
Item 36c (#3658, PR #3678) pins the shared ``PHASE_MAX_TOKENS`` ceiling on
the fallacy descent's two SK kernels via ``_with_phase_max_tokens`` — on
the DECLARED ``max_tokens`` field, because SK 1.44's
``OpenAIPromptExecutionSettings`` declares no ``max_completion_tokens``
(measured: ``model_fields`` has the former, not the latter), so the raw
path's key-neutral trick is unavailable here. ``_serialize_settings``
includes ``max_tokens``, so ``compute_cache_key`` moved for every descent
call, and the replay band reddened: run 45116893532 (2026-11-23),
miss_replay=2 in-process + one miss per CLI subprocess —
``FALLACY_DETECTION_FAILED: tier=llm, reason=Cache miss`` in the three
delegation e2e tests (R648/R651/R652), keys 4b56d08bceec1409 /
b05136b335a6937f / b61415c32d46ab69.

The request did not change — only the cap field was added — and every
recorded completion in the affected set sits far under the 8192 ceiling
(checked below; anything over it is named, never moved), so the recorded
responses are still the right responses. Only the key name moved. This
script moves each cassette to its new key at ZERO cost: no LLM call, no
record mode (the #2853 rekey precedent, coordinator decision there).

What it does
------------
1. Imports the committed fixtures into a scratch replay DB (``import.py``,
   provenance gate included) and drives the three delegation chains in
   replay mode against it:
   - R648 (``test_delegation_decides_firsthand_1471``) runs the chain
     in-process — captured through the ``rekey_capture`` pytest plugin;
   - R651/R652 drive the real CLI in a SUBPROCESS, so the pytest plugin
     cannot see their misses. The driver writes a small spy runner into
     the scratch dir and invokes ``run_orchestration.py`` with each test's
     own ``SIMPLE_TEXT`` (read from the test module at runtime, never
     duplicated here). The runner patches ``compute_cache_key`` the same
     way the plugin does and dumps the stashed payloads whose key is
     absent from the scratch DB.
   Replay misses raise ``LLMCacheMiss`` — the chain degrades — so the run
   makes no call. Like #2853, the move CASCADES: a first miss aborts the
   chain before later calls reach the cache, so each rekeyed cassette
   exposes the next one. Re-run the script until it reports ``moved: 0``.
2. For each distinct missed key it rebuilds the PRE-cap key from the same
   inputs (settings block minus ``max_tokens``) and loads the cassette
   stored under it. A miss whose settings block carries no ``max_tokens``
   equal to the ceiling is NOT a cap-drift miss — it is named and left to
   the coordinator, never silently rekeyed.
3. Provenance, per cassette: the value must be able to answer under the
   capped request and the model must hold.
   - ``usage.completion_tokens``, wherever the value records one, must be
     <= the ceiling (a completion the cap would truncate is NOT the right
     response for the capped key);
   - the model basis is the #2853 bar: value-recorded model must equal the
     new key's ``ai_model_id`` exactly, or (SK values record none) the
     session anchor must hold — no foreign model anywhere in the set, and
     the value's ``created`` inside the record session's span. The 36c
     payloads carry NO ``ai_model_id`` (measured: settings block is exactly
     ``{'max_tokens': 8192}``), so the anchor model is the set's single
     recorded one — a multi-model set anchors nothing and stops loud.
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
    python scripts/cassettes/rekey_phase_cap_3658_36c.py [--dry-run]
    python scripts/cassettes/rekey_phase_cap_3658_36c.py --refresh-manifest-only [--note ...]

Run it with the gate-stack interpreter (the import provenance gate checks
the openai package version — ``projet-is-lock`` on the worker seats).
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
DEFAULT_SCRATCH = REPO / ".cache" / "llm_rekey_phase_cap_36c"

# In-process chains whose misses reach the pytest plugin: the delegation
# e2e (R648) and the websocket deliberation band member — its fallacy
# descent misses are swallowed by the verdict's fallback (measured: the
# test passes on 6 misses), so only the capture plugin sees them.
CAPTURE_TESTS = (
    "tests/orchestration/hierarchical/test_delegation_decides_firsthand_1471_R648.py",
    "tests/integration/api/test_websocket_deliberation_genuine.py",
)

# The two subprocess-driven chains: (test module, text attribute). The texts
# are read from the modules at runtime so this table cannot drift from them.
CLI_TEXT_SOURCES = (
    (
        "tests/orchestration/hierarchical/test_cli_registry_wiring_1471_R651.py",
        "SIMPLE_TEXT",
    ),
    (
        "tests/orchestration/hierarchical/test_channel_registration_1471_R652.py",
        "SIMPLE_TEXT",
    ),
)

CLI_ARGV = ("--mode", "hierarchical", "--hierarchical-mode", "delegation")

# Deliberately not a secret (same dummy as the replay-band job): satisfies
# the requires_api presence check while leaving nothing real to call.
DUMMY_KEY = "replay-band-no-live-anti-1019"

# The ceiling the production code pins (invoke_callables._PHASE_MAX_TOKENS
# reads the same env with the same default; duplicated here so the tool
# stays import-light).
_CEILING = int(os.environ.get("PHASE_MAX_TOKENS", "8192") or 0)

# Byte-identical to what rekey_settings_class writes, minus the descent-cap
# specifics: the spy runner injected into the CLI subprocesses.
_SPY_RUNNER = '''"""Generated by rekey_phase_cap_3658_36c.py -- do not edit."""
import asyncio
import json
import os
import sys

import argumentation_analysis.services.llm_cache as llm

_orig = llm.compute_cache_key
_STASH = {}


def _spy(chat_history, settings=None):
    key = _orig(chat_history, settings)
    try:
        payload = json.dumps(
            {
                "messages": llm._serialize_messages(chat_history),
                "settings": llm._serialize_settings(settings),
            },
            sort_keys=True,
            ensure_ascii=False,
        )
    except Exception as exc:  # probe must not break the run
        payload = f"<unserializable: {exc!r}>"
    _STASH[key] = {
        "key": key,
        "path": "sk",
        "payload": payload,
        "settings_class": type(settings).__name__ if settings is not None else None,
    }
    return key


llm.compute_cache_key = _spy

from argumentation_analysis.run_orchestration import main  # noqa: E402

rc = 1
try:
    rc = asyncio.run(main()) or 0
finally:
    import diskcache

    cache = diskcache.Cache(os.environ["LLM_CACHE_DIR"])
    records = [
        rec
        for rec in _STASH.values()
        if "payload" in rec and cache.get(rec["key"]) is None
    ]
    with open(os.environ["REKEY_CAPTURE_OUT"], "w", encoding="utf-8") as fh:
        json.dump(
            {"misses": [r["key"][:16] for r in records], "records": records},
            fh,
            indent=2,
            ensure_ascii=False,
        )
    print(f"[cli-spy] miss_replay={len(records)}")
sys.exit(rc)
'''


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
        default="rekey: descent phase cap #3658 item 36c",
        help="note recorded in the manifest's sk_patches entry",
    )
    return p.parse_args(argv)


def _read_text_constant(module_rel: str, attr: str) -> str:
    """Read a module-level string constant without executing the module."""
    import ast

    path = REPO / module_rel
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if attr in targets:
                try:
                    return ast.literal_eval(node.value)
                except ValueError:
                    break
    raise SystemExit(f"{module_rel}: could not read constant {attr!r} via ast")


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


def _pre_cap_block(settings_block: dict) -> dict:
    """Settings block the pre-36c derivation saw: identical, minus the cap.

    Before item 36c the descent kernels sent no ``max_tokens`` at all, so
    the serializer omitted the key; every other field is unchanged by the
    cap.
    """
    block = dict(settings_block)
    block.pop("max_tokens", None)
    return block


def _models_in_value(value) -> set[str]:
    from scripts.cassettes.rekey_settings_class import _models_in_value as f

    return f(value)


def _created_in_value(value):
    from scripts.cassettes.rekey_settings_class import _created_in_value as f

    return f(value)


def _session_anchor(fixtures_dir: Path, model: str) -> tuple[set[str], int, int]:
    from scripts.cassettes.rekey_settings_class import _session_anchor as f

    return f(fixtures_dir, model)


def _set_models(fixtures_dir: Path) -> set[str]:
    """Every model any cassette in the set records about itself."""
    models: set[str] = set()
    for path in sorted(fixtures_dir.glob("*.json")):
        if path.name == "MANIFEST.json":
            continue
        value = json.loads(path.read_text(encoding="utf-8"))["value"]
        models |= _models_in_value(value)
    return models


def _completion_usage_in_value(value) -> list[int]:
    """Every ``usage.completion_tokens`` (or bare ``completion_tokens``) the
    value records, wherever a nested dict carries one."""
    found: list[int] = []

    def _scan(node) -> None:
        if isinstance(node, dict):
            usage = node.get("usage")
            if isinstance(usage, dict) and isinstance(
                usage.get("completion_tokens"), int
            ):
                found.append(usage["completion_tokens"])
            elif isinstance(node.get("completion_tokens"), int):
                found.append(node["completion_tokens"])
            for v in node.values():
                _scan(v)
        elif isinstance(node, list):
            for item in node:
                _scan(item)

    _scan(value)
    return found


def _capture(scratch_dir: Path) -> list[dict]:
    """Import fixtures into a scratch DB, drive the three chains in replay,
    and return the merged miss records (pytest plugin + CLI spy runners)."""
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

    records: list[dict] = []
    base_env = dict(os.environ)
    base_env.update(
        {
            "LLM_CACHE_MODE": "replay",
            "LLM_CACHE_DIR": str(scratch_dir),
            "OPENAI_API_KEY": DUMMY_KEY,
            "PYTHONPATH": str(REPO),
        }
    )

    # 1) in-process chain (R648) -- the pytest plugin sees its misses.
    pytest_out = scratch_dir / "capture_pytest.json"
    env = dict(base_env)
    env["REKEY_CAPTURE_OUT"] = str(pytest_out)
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
    print("\n".join(ret.stdout.splitlines()[-8:]))
    if pytest_out.exists():
        report = json.loads(pytest_out.read_text(encoding="utf-8"))
        records.extend(r for r in report["records"] if "payload" in r)

    # 2) subprocess chains (R651/R652) -- a spy runner stands in for the
    #    plugin: same stash, misses = keys absent from the scratch DB.
    runner_path = scratch_dir / "cli_spy_runner.py"
    runner_path.write_text(_SPY_RUNNER, encoding="utf-8", newline="\n")
    for module_rel, attr in CLI_TEXT_SOURCES:
        text = _read_text_constant(module_rel, attr)
        cli_out = scratch_dir / f"capture_cli_{attr}_{Path(module_rel).stem}.json"
        env = dict(base_env)
        env["REKEY_CAPTURE_OUT"] = str(cli_out)
        ret = subprocess.run(
            [
                sys.executable,
                "-u",
                str(runner_path),
                *CLI_ARGV,
                "--text",
                text,
            ],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
            timeout=900,
        )
        print(f"[cli {Path(module_rel).stem}] rc={ret.returncode}")
        print("\n".join(ret.stdout.splitlines()[-4:]))
        if not cli_out.exists():
            sys.stderr.write(ret.stderr[-2000:])
            raise SystemExit(
                f"CLI capture for {module_rel} produced no report (rc={ret.returncode})"
            )
        report = json.loads(cli_out.read_text(encoding="utf-8"))
        records.extend(r for r in report["records"] if "payload" in r)

    print(f"\ncaptured attributed misses across the three chains: {len(records)}")
    return records


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

    records = [r for r in _capture(args.scratch_dir) if r.get("path") == "sk"]

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
                "settings_class": rec.get("settings_class"),
            },
        )
        entry["calls"] += 1

    failures: list[str] = []
    moved: list[dict] = []
    anchors: dict[str, tuple[set[str], int, int]] = {}
    # Model the descent calls bind to, when the settings block carries none:
    # the 36c drift adds only ``max_tokens``, so the old and the new key
    # carry the SAME model identity (measured on the captured payloads:
    # ``{'max_tokens': 8192}`` and nothing else — no ai_model_id, no
    # service_id). The bar is then the session anchor against the set's
    # single recorded model; a set recording several models cannot anchor
    # anything and goes back to the coordinator.
    set_models_cache = _set_models(FIXTURES_DIR)
    for new_key in sorted(pairs):
        info = pairs[new_key]
        ai_model = info["settings"].get("ai_model_id")
        if not isinstance(ai_model, str) or not ai_model:
            if len(set_models_cache) != 1:
                failures.append(
                    f"{new_key[:16]}: the key carries no ai_model_id and the "
                    f"set records {sorted(set_models_cache)} — no single "
                    "session to anchor the relabel to"
                )
                continue
            ai_model = next(iter(set_models_cache))
        if info["settings"].get("max_tokens") != _CEILING:
            failures.append(
                f"{new_key[:16]}: settings carry max_tokens="
                f"{info['settings'].get('max_tokens')!r}, expected the shared "
                f"ceiling {_CEILING!r} — this miss is not the 36c cap drift; "
                "name it to the coordinator, do not rekey blind"
            )
            continue
        old_block = _pre_cap_block(info["settings"])
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
                f"{new_key[:16]}: no cassette under the pre-cap key "
                f"{old_key[:16]} — this call was never recorded, the rekey "
                "cannot cover it"
            )
            continue
        if new_path.exists():
            print(f"  {new_key[:16]}: already rekeyed (skipped)")
            continue
        old_bytes = old_path.read_bytes()
        value = json.loads(old_bytes)["value"]

        usages = _completion_usage_in_value(value)
        over = [u for u in usages if u > _CEILING]
        if over:
            failures.append(
                f"{old_key[:16]} -> {new_key[:16]}: the recorded completion "
                f"({over[0]} tokens) exceeds the {_CEILING} ceiling — the cap "
                "would truncate this answer; the cassette is NOT the right "
                "response for the capped key (re-record decision: coordinator)"
            )
            continue

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
        if usages:
            basis += f"; completion_tokens={usages[0]} <= {_CEILING}"

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
                "settings_class": info.get("settings_class"),
                "basis": basis,
            }
        )

    print(
        f"\nmoved: {len(moved)} cassette(s), {sum(m['calls'] for m in moved)} call(s)"
    )
    for m in moved:
        print(
            f"  {m['old']} -> {m['new']}  calls={m['calls']}  model={m['model']}  "
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
        if not args.dry_run:
            # Re-bind the manifest so the NEXT iteration's import passes the
            # #2323 gate (each moved cassette adds a file; the gate compares
            # count+digest). One sk_patches entry per moving run — the final
            # prune-or-keep decision gets its own --refresh-manifest-only.
            refresh_manifest(FIXTURES_DIR, note=f"{args.note} (moved {len(moved)})")
        print(
            "\nNext: re-run until moved: 0 (the move cascades), then decide "
            "the fate of the old files by measurement (band green with them "
            "absent from the import = unreachable), then re-bind the "
            "manifest: python scripts/cassettes/rekey_phase_cap_3658_36c.py "
            "--refresh-manifest-only"
        )
    return 4 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
