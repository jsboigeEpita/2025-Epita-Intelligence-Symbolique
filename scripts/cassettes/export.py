"""Export LLM cache entries from a runtime diskcache DB to JSON fixtures.

Usage::

    python scripts/cassettes/export.py <source_db_dir> <fixtures_dir>

Source DB layout (produced by `llm_cache.CachedChatCompletion` at runtime):

    <source_db_dir>/cache.db        # SQLite, opened as diskcache.Cache

Each entry has:
- key: hex sha256 string (32 chars)
- value: JSON list-of-dicts (SK-path: `_serialize_response`)
       OR JSON dict (raw-path: `_serialize_chat_completion`)

The fixtures layout is:

    <fixtures_dir>/<sha256>.json    # {"key": "...", "value": [...] or {...}}

If `value` fails the privacy audit (see ``privacy.audit_value``), the
script refuses to write that cassette and exits with code 2. A summary is
printed at the end (cassettes exported, refused, total).

Why one-file-per-cassette: PR diffs become readable; partial fixes can be
targeted; git blame stays useful. The DB format (SQLite) is opaque to the
auditor — JSON files make the privacy check possible without parsing
SQLite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

# Allow `python scripts/cassettes/export.py` invocation from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import diskcache  # type: ignore[import-not-found]

from scripts.cassettes.privacy import assert_safe, audit_value

# Packages whose versions feed the LLM cache keys (measured #2320: spacy-stack
# virtue scores enter quality prompts; openai shapes the raw request path;
# numpy pins the binary stack). All pinned in environment.yml so recorder and
# replayer match by construction. NOT msgpack: since #2321 the srsly wheel
# vendors its msgpack, so the external msgpack version never touches the keys.
KEY_DEP_PACKAGES = (
    "spacy",
    "thinc",
    "srsly",
    "fr-core-news-sm",
    "openai",
    "numpy",
)

MANIFEST_NAME = "MANIFEST.json"


def env_signature() -> dict[str, str]:
    """Versions of the key-drift-relevant packages in THIS recording env."""
    import importlib.metadata as im

    sig: dict[str, str] = {}
    for pkg in KEY_DEP_PACKAGES:
        try:
            sig[pkg] = im.version(pkg)
        except im.PackageNotFoundError:
            sig[pkg] = "absent"
    return sig


def keys_digest(keys: list[str]) -> str:
    """Stable digest binding a manifest to an exact cassette set."""
    blob = "\n".join(sorted(keys)).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def refresh_manifest(fixtures_dir: Path, *, note: str) -> bool:
    """Re-bind an existing manifest to the dir's current cassette set (#2323).

    The one legitimate writer besides a record job is the surgical SK-path
    refresh (``record_sk_cassette.py`` — the record job cannot record the SK
    path: pytest mocks it, #1603 constat A). Such a patch changes the cassette
    set, which would leave the manifest's count/digest stale and the import
    gate red. This function re-computes them over the dir AS IT NOW STANDS and
    declares the patch in ``sk_patches`` (with the patching env's signature —
    SK-path cache keys embed prompt wording, not spacy-computed scores, so the
    patch env is recorded for provenance but not gated: ``env_signature``
    stays the record job's, which the raw-path cassettes still are).

    Returns False (and warns) when the dir carries no manifest — a manifest-less
    dir is not this function's to bless; record via the job first.
    """
    import time

    manifest_path = fixtures_dir / MANIFEST_NAME
    if not manifest_path.exists():
        print(
            f"refresh_manifest: no {MANIFEST_NAME} in {fixtures_dir} — this dir "
            "is not provenance-tracked; run the record-llm-cassettes job and "
            "commit its export WITH the manifest before patching it (#2323).",
            file=sys.stderr,
        )
        return False
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    keys = sorted(
        p.stem for p in fixtures_dir.glob("*.json") if p.name != MANIFEST_NAME
    )
    patch = {
        "note": note,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "recorded_env": env_signature(),
        "cassette_count": len(keys),
        "keys_sha256": keys_digest(keys),
    }
    manifest.setdefault("sk_patches", []).append(patch)
    manifest["cassette_count"] = len(keys)
    manifest["keys_sha256"] = patch["keys_sha256"]
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"refresh_manifest: {manifest_path} re-bound ({len(keys)} cassettes, "
        f"patch #{len(manifest['sk_patches'])}: {note})"
    )
    return True


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument(
        "source_dir",
        type=Path,
        help="Runtime diskcache directory (e.g. .cache/llm_responses)",
    )
    p.add_argument(
        "fixtures_dir",
        type=Path,
        help="Destination directory for JSON cassette fixtures",
    )
    p.add_argument(
        "--allow-unsafe",
        action="store_true",
        help="Skip privacy audit (DO NOT USE without explicit review, #1603)",
    )
    return p.parse_args(argv)


def export_one(
    db: diskcache.Cache, key: str, value, fixtures_dir: Path, *, allow_unsafe: bool
) -> str:
    """Write one cassette. Returns 'ok' | 'unsafe' | 'already' | 'degraded'.

    ``degraded`` (#1603 R826 review): a dict value carrying ``_fallback`` is
    the marker ``_serialize_chat_completion`` writes when it gives up on a
    response — such a cassette replays as a ``str``/choices-less value, i.e.
    an unusable cassette wearing the shape of a real one. The marker is
    apposed by the serializer itself, so no legitimate cassette can escape
    this check (no false negative by construction). Refusing at the export
    boundary keeps ``llm_cache.py`` free of record-shape guards and the BO-3
    replay invariants un-widened.
    """
    out = fixtures_dir / f"{key}.json"
    if out.exists():
        return "already"
    if isinstance(value, dict) and "_fallback" in value:
        return "degraded"
    if not allow_unsafe:
        violations = audit_value(value, source=f"cassette {key[:16]}")
        if violations:
            return "unsafe"
    out.write_text(
        json.dumps({"key": key, "value": value}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return "ok"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.source_dir.exists():
        print(f"Source DB dir does not exist: {args.source_dir}", file=sys.stderr)
        return 1
    args.fixtures_dir.mkdir(parents=True, exist_ok=True)

    db = diskcache.Cache(str(args.source_dir))
    try:
        total = len(db)
        if total == 0:
            print(
                f"No entries in {args.source_dir}; nothing to export.", file=sys.stderr
            )
            return 0

        counts: dict[str, int] = {"ok": 0, "already": 0, "unsafe": 0, "degraded": 0}
        unsafe_keys: list[str] = []
        degraded_keys: list[str] = []
        for key in db.iterkeys():
            value = db[key]
            status = export_one(
                db, key, value, args.fixtures_dir, allow_unsafe=args.allow_unsafe
            )
            counts[status] = counts.get(status, 0) + 1
            if status == "unsafe":
                unsafe_keys.append(key[:16])
            if status == "degraded":
                degraded_keys.append(key[:16])
    finally:
        db.close()

    print(f"Source: {args.source_dir}")
    print(f"Fixtures: {args.fixtures_dir}")
    print(f"Total entries: {total}")
    print(f"Exported: {counts['ok']}")
    print(f"Already present: {counts['already']}")
    print(f"Refused (privacy): {counts['unsafe']}")
    print(f"Refused (degraded value — unusable cassette): {counts['degraded']}")
    if degraded_keys:
        print(
            f"Degraded cassettes (first 16 chars of key): {degraded_keys}",
            file=sys.stderr,
        )
    if unsafe_keys:
        print(
            f"Refused cassettes (first 16 chars of key): {unsafe_keys}", file=sys.stderr
        )
        return 2

    # #2323 provenance manifest: in a record-job run GITHUB_RUN_ID is set
    # automatically, so the artifact carries its own birth certificate with no
    # workflow change. Local exports (harvest) produce no manifest — importing
    # those then fails loud on the replay side (see import.py), which is the
    # point: the recorder must be the replayer.
    run_id = os.environ.get("GITHUB_RUN_ID")
    if run_id:
        fixture_keys = sorted(
            p.stem for p in args.fixtures_dir.glob("*.json") if p.name != MANIFEST_NAME
        )
        manifest = {
            "schema": 1,
            "record_run_id": run_id,
            "record_sha": os.environ.get("GITHUB_SHA", "unknown"),
            "recorded_at": os.environ.get("GITHUB_RUN_STARTED_AT", ""),
            "cassette_count": len(fixture_keys),
            "keys_sha256": keys_digest(fixture_keys),
            "env_signature": env_signature(),
        }
        manifest_path = args.fixtures_dir / MANIFEST_NAME
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"Manifest: {manifest_path} (run {run_id}, {len(fixture_keys)} cassettes)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
