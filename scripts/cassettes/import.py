"""Import LLM cassettes from JSON fixtures into a runtime diskcache DB.

Usage::

    python scripts/cassettes/import.py <fixtures_dir> <target_db_dir>

Target DB layout (consumed by `llm_cache.CachedChatCompletion` at replay):

    <target_db_dir>/cache.db        # SQLite, opened as diskcache.Cache

Each fixture file `<sha256>.json` holds ``{"key": sha256, "value": ...}``
— the ``value`` is the literal output of `_serialize_response` /
`_serialize_chat_completion`. Round-tripped through the matching
`_deserialize_*` at replay.

This is the inverse of ``export.py``. No privacy audit is run on import
because the audit ran at export time and any new cassette written to the
fixtures dir would have failed it. Re-running the export after an import
should be idempotent.

#2323 provenance gate: the fixtures dir must carry the MANIFEST.json the
record job's export step emits (run id + env signature + cassette-set
digest), and the importing environment must match the recording one. This is
the structural repair for the recorder != replayer drift (#2320's entry
door: 211 cassettes harvested on a worker box while the record job had not
succeeded since 2026-08-17). Local harvests produce no manifest and fail
loud here by design — record via the job, commit its export WITH the
manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

# Allow `python scripts/cassettes/import.py` invocation from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import diskcache  # type: ignore[import-not-found]

MANIFEST_NAME = "MANIFEST.json"


def _fixture_keys(fixtures_dir: Path) -> list[str]:
    return sorted(
        p.stem for p in fixtures_dir.glob("*.json") if p.name != MANIFEST_NAME
    )


def _keys_digest(keys: list[str]) -> str:
    blob = "\n".join(sorted(keys)).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def verify_manifest(fixtures_dir: Path) -> list[str]:
    """Return the list of provenance violations (empty = verified).

    Checks: manifest exists and is well-formed; the cassette set on disk
    matches the manifest's count AND digest (adding/removing a cassette
    locally without re-recording reddens); the importing env matches the
    recording env on every key-drift-relevant package (#2320: a differing
    spacy stack computed different scores, i.e. different keys).
    """
    violations: list[str] = []
    manifest_path = fixtures_dir / MANIFEST_NAME
    if not manifest_path.exists():
        violations.append(
            f"no {MANIFEST_NAME} in {fixtures_dir} — these cassettes are not "
            "provenance-tracked. Record via the record-llm-cassettes job and "
            "commit its export WITH the manifest (#2323); local harvests are "
            "the drift door this gate closes."
        )
        return violations

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"unreadable {MANIFEST_NAME}: {exc}"]

    if not str(manifest.get("record_run_id", "")).strip():
        violations.append("manifest carries no record_run_id")
    if manifest.get("schema") != 1:
        violations.append(f"unexpected manifest schema: {manifest.get('schema')!r}")

    disk_keys = _fixture_keys(fixtures_dir)
    if len(disk_keys) != manifest.get("cassette_count"):
        violations.append(
            f"cassette count drift: manifest says {manifest.get('cassette_count')}, "
            f"disk has {len(disk_keys)}"
        )
    disk_digest = _keys_digest(disk_keys)
    if disk_digest != manifest.get("keys_sha256"):
        violations.append(
            "cassette-set digest mismatch — the fixtures were modified after "
            "the recorded export"
        )

    import importlib.metadata as im

    recorded_sig = manifest.get("env_signature") or {}
    if not recorded_sig:
        violations.append("manifest carries no env_signature")
    for pkg, recorded_version in sorted(recorded_sig.items()):
        try:
            local_version = im.version(pkg)
        except im.PackageNotFoundError:
            local_version = "absent"
        if local_version != recorded_version:
            violations.append(
                f"env drift on {pkg}: cassettes recorded with {recorded_version}, "
                f"this env has {local_version} — replay keys would not match "
                "(#2320 class)"
            )
    return violations


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "fixtures_dir",
        type=Path,
        help="Directory containing <sha256>.json cassette files",
    )
    p.add_argument(
        "target_dir",
        type=Path,
        help="Runtime diskcache directory to populate (e.g. .cache/llm_responses)",
    )
    p.add_argument(
        "--purge",
        action="store_true",
        help="Purge the target DB before import (otherwise merge)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.fixtures_dir.exists():
        print(f"Fixtures dir does not exist: {args.fixtures_dir}", file=sys.stderr)
        return 1

    provenance = verify_manifest(args.fixtures_dir)
    if provenance:
        print(
            f"PROVENANCE GATE FAILED — cassettes not importable ({len(provenance)} "
            "violation(s)):",
            file=sys.stderr,
        )
        for v in provenance:
            print(f"  - {v}", file=sys.stderr)
        return 3

    args.target_dir.mkdir(parents=True, exist_ok=True)

    db = diskcache.Cache(str(args.target_dir))
    try:
        if args.purge:
            db.clear()
        existing = set(db.iterkeys())

        written = 0
        skipped = 0
        bad = 0
        for path in sorted(args.fixtures_dir.glob("*.json")):
            if path.name == MANIFEST_NAME:
                continue
            data = json.loads(path.read_text(encoding="utf-8"))
            key = data.get("key")
            value = data.get("value")
            if not isinstance(key, str) or value is None:
                print(f"Malformed cassette: {path.name}", file=sys.stderr)
                bad += 1
                continue
            if key in existing:
                skipped += 1
                continue
            db.set(key, value)
            written += 1
    finally:
        db.close()

    print(f"Fixtures: {args.fixtures_dir}")
    print(f"Target: {args.target_dir}")
    print(f"Written: {written}")
    print(f"Skipped (already present): {skipped}")
    print(f"Malformed: {bad}")
    return 0 if bad == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
