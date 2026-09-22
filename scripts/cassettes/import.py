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

#2326 closes the remaining door: the #2323 checks are CONSISTENCY checks —
every one compares the manifest against a disk the manifest's author also
wrote, so a locally-harvested dir with a fabricated ``record_run_id`` passed
them all (measured: rc=0). ``--verify-run`` resolves the run id against the
GitHub Actions run's own logs — the ``Exported cassettes: N`` line the run
emitted, which no manifest author can rewrite — derives the true job
baseline from it, and reddens when the disk's non-job delta exceeds what
``sk_patches`` declares. The replay lanes pass the flag: the band verifies
the guard itself (#2323's design).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

# Allow `python scripts/cassettes/import.py` invocation from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import diskcache

MANIFEST_NAME = "MANIFEST.json"

# The one line the record job's export step writes (record-llm-cassettes.yml,
# "Export cassettes" step) — the only baseline the run's author cannot forge
# after the fact.
_EXPORT_LINE_RE = re.compile(r"Exported cassettes:\s*(\d+)")
# export.py's own report of the manifest it wrote (#2323). Since #2323 the
# manifest sits INSIDE the staging dir the line above globs, so from #2323 to
# #2405 that line counted it as a cassette (run 35792294382: 277 for 276).
# The run printed this line too — the manifest's author cannot rewrite it.
_MANIFEST_LINE_RE = re.compile(r"Manifest: .*\(run (\d+), (\d+) cassettes\)")


class RunLogError(Exception):
    """The run's logs could not serve a cassette-export count (#2326)."""


def _run_export_count(
    api_url: str,
    repo: str,
    token: str,
    run_id: str,
    urlopen: Optional[Callable[..., Any]] = None,
) -> int:
    """Fetch a record run's logs and derive the cassettes its export wrote.

    A run recorded before #2323 carries only the ``Exported cassettes: N``
    line, and N is the baseline. A later run also carries export.py's
    ``Manifest: ... (run R, N cassettes)`` line: N is the baseline, R must be
    this run, and the glob line must read N (#2405 producer) or N+1 (the
    manifest counted as a cassette, #2323 to #2405).

    Raises:
        RunLogError: the run does not exist (404 — a fabricated run id),
            its logs are unreachable, they carry no export line, or the two
            lines disagree. Every failure mode is a provenance verdict, never
            a silent skip.
    """
    if urlopen is None:
        # Resolved at CALL time, not def time — a default argument bound at
        # module load would pin the original and defeat patching.
        urlopen = urllib.request.urlopen
    url = f"{api_url.rstrip('/')}/repos/{repo}/actions/runs/{run_id}/logs"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urlopen(req, timeout=30) as resp:
            data = resp.read()
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise RunLogError(
                f"run {run_id} does not exist in {repo} (API 404) — the "
                "manifest's record_run_id is fabricated or mistyped"
            ) from exc
        raise RunLogError(f"run {run_id} logs unavailable (HTTP {exc.code})") from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RunLogError(f"run {run_id} logs unreachable: {exc}") from exc
    glob_count: Optional[int] = None
    manifest_line: Optional[Tuple[str, int]] = None
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for name in zf.namelist():
                text = zf.read(name).decode("utf-8", errors="replace")
                match = _EXPORT_LINE_RE.search(text)
                if match and glob_count is None:
                    glob_count = int(match.group(1))
                match = _MANIFEST_LINE_RE.search(text)
                if match and manifest_line is None:
                    manifest_line = (match.group(1), int(match.group(2)))
    except zipfile.BadZipFile as exc:
        raise RunLogError(f"run {run_id} logs are not a zip archive: {exc}") from exc
    if glob_count is None:
        raise RunLogError(
            f"run {run_id} logs carry no 'Exported cassettes:' line — cannot "
            "derive the job baseline"
        )
    if manifest_line is None:
        return glob_count
    line_run, cassettes = manifest_line
    if line_run != str(run_id):
        raise RunLogError(
            f"run {run_id}'s export wrote a manifest for run {line_run} — the "
            "logs do not belong to the manifest's record run"
        )
    if glob_count not in (cassettes, cassettes + 1):
        raise RunLogError(
            f"run {run_id}'s export lines disagree: 'Exported cassettes: "
            f"{glob_count}' vs the manifest's {cassettes} cassettes (expected "
            f"{cassettes}, or {cassettes + 1} with MANIFEST.json counted)"
        )
    return cassettes


def verify_run_provenance(
    fixtures_dir: Path, *, api_url: str, repo: str, token: str
) -> Tuple[List[str], Optional[str]]:
    """Verify the manifest's run id against the run itself (#2326).

    Returns:
        (violations, note): ``violations`` empty means verified; ``note``
        carries the reported provenance line (baseline, declared non-job
        delta, disk count) for the lane log.
    """
    manifest_path = fixtures_dir / MANIFEST_NAME
    if not manifest_path.exists():
        return (
            [f"no {MANIFEST_NAME} in {fixtures_dir} — cannot verify provenance"],
            None,
        )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return ([f"unreadable {MANIFEST_NAME}: {exc}"], None)

    run_id = str(manifest.get("record_run_id", "")).strip()
    if not run_id:
        return (["manifest carries no record_run_id"], None)

    try:
        baseline = _run_export_count(api_url, repo, token, run_id)
    except RunLogError as exc:
        return ([f"provenance: {exc}"], None)

    disk_count = len(_fixture_keys(fixtures_dir))
    patches = manifest.get("sk_patches") or []
    declared = 0
    if patches:
        try:
            declared = max(0, int(patches[-1].get("cassette_count", 0)) - baseline)
        except (TypeError, ValueError):
            return (
                ["provenance: sk_patches entry carries a non-integer cassette_count"],
                None,
            )
    non_job = disk_count - baseline
    note = (
        f"provenance: run {run_id} exported {baseline} cassettes; declared "
        f"non-job delta {declared} (sk_patches: {len(patches)}); disk "
        f"carries {disk_count}"
    )
    violations: List[str] = []
    if non_job < 0:
        violations.append(
            f"provenance: disk carries {disk_count} cassettes but run {run_id} "
            f"exported {baseline} — cassettes were REMOVED after the "
            "recorded export"
        )
    elif non_job > declared:
        violations.append(
            f"provenance: non-job delta {non_job} exceeds the manifest's "
            f"declared {declared} — cassettes on disk come from neither run "
            f"{run_id} nor a declared sk_patch (#2326)"
        )
    return violations, note


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
    p.add_argument(
        "--verify-run",
        action="store_true",
        help=(
            "verify record_run_id against the GitHub Actions run's own logs "
            "(#2326): the run's 'Exported cassettes: N' line is the only "
            "baseline the manifest's author cannot rewrite. The replay "
            "lanes' contract. Requires GITHUB_TOKEN/GH_TOKEN and "
            "GITHUB_REPOSITORY"
        ),
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

    if args.verify_run:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
        if not token or not repo:
            print(
                "PROVENANCE GATE FAILED — --verify-run requires "
                "GITHUB_TOKEN/GH_TOKEN and GITHUB_REPOSITORY (present on "
                "every Actions runner; locally, export GH_TOKEN from "
                "`gh auth token`)",
                file=sys.stderr,
            )
            return 3
        run_violations, note = verify_run_provenance(
            args.fixtures_dir, api_url=api_url, repo=repo, token=token
        )
        if note:
            print(note)
        if run_violations:
            print(
                "PROVENANCE GATE FAILED — run verification refused these "
                f"cassettes ({len(run_violations)} violation(s)):",
                file=sys.stderr,
            )
            for v in run_violations:
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
