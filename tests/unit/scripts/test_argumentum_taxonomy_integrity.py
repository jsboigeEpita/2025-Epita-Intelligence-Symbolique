"""Guards for the Argumentum taxonomy snapshot integrity (#1956).

The two Argumentum taxonomies (fallacies + virtues) are vendored from a public
upstream repository (ArgumentumGames/Argumentum @ c86b71ff). A drift here means
downstream readers see a different taxonomy than upstream, with no automatic
detection. The snapshot JSON records the row/column counts and the content
hashes (with and without BOM) at the pinned upstream commit; these tests
re-derive those counts and hashes locally and refuse any silent regression.

Why we record *both* upstream_blob_sha1 (with BOM) and
upstream_content_sha1_no_bom: the upstream CSV carries a UTF-8 BOM at the
start of the first header column ('\\ufeffPK'). Our local copy is stored without
the BOM to match the rest of the repo's encodings. Any future ingest must
strip the BOM at copy time — these tests pin that decision so a later
"round-trip" cannot silently flip it back.

The test exercises only the *local* CSVs (always present in the repo) and the
snapshot JSON; it never re-fetches upstream. A drift in upstream therefore
turns into a test failure when the next re-pull happens — which is the right
direction: the operator sees "expected vs got", not a silent new release.

Mutation contract (proved elsewhere): removing the first column from either
local CSV must turn the test red. The local sha is computed over the raw bytes
on disk, so column surgery changes the hash; the assertion that the local sha
matches the snapshot catches it.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]  # tests/unit/scripts/ → repo root
DATA = REPO / "argumentation_analysis" / "data"
SNAPSHOT_PATH = DATA / "argumentum_taxonomy_provenance.json"


def _load_snapshot() -> dict:
    with SNAPSHOT_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _rows_and_columns(csv_path: Path) -> tuple[int, int, list[str]]:
    text = csv_path.read_text(encoding="utf-8")
    rows = list(csv.reader(text.splitlines()))
    columns = max(len(r) for r in rows) if rows else 0
    return len(rows), columns, rows[0] if rows else []


def _sha1_bytes(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def test_fallacies_match_snapshot() -> None:
    """Local fallacies CSV matches the snapshot at c86b71ff."""
    snap = _load_snapshot()
    expected = snap["fallacies"]
    csv_path = DATA / Path(expected["local_path"]).name
    rows, cols, header = _rows_and_columns(csv_path)
    assert rows == expected["rows"], (
        f"fallacies rows drifted: snapshot={expected['rows']} local={rows}"
    )
    assert cols == expected["columns"], (
        f"fallacies columns drifted: snapshot={expected['columns']} local={cols}"
    )
    assert _sha1_bytes(csv_path) == expected["upstream_content_sha1_no_bom"], (
        f"fallacies content sha drifted: snapshot={expected['upstream_content_sha1_no_bom']} "
        f"local={_sha1_bytes(csv_path)}"
    )


def test_virtues_match_snapshot() -> None:
    """Local virtues CSV matches the snapshot at c86b71ff."""
    snap = _load_snapshot()
    expected = snap["virtues"]
    csv_path = DATA / Path(expected["local_path"]).name
    rows, cols, header = _rows_and_columns(csv_path)
    assert rows == expected["rows"], (
        f"virtues rows drifted: snapshot={expected['rows']} local={rows}"
    )
    assert cols == expected["columns"], (
        f"virtues columns drifted: snapshot={expected['columns']} local={cols}"
    )
    assert _sha1_bytes(csv_path) == expected["upstream_content_sha1_no_bom"], (
        f"virtues content sha drifted: snapshot={expected['upstream_content_sha1_no_bom']} "
        f"local={_sha1_bytes(csv_path)}"
    )


def test_required_columns_present_fallacies() -> None:
    """All required columns are present in local fallacies CSV."""
    snap = _load_snapshot()
    expected = snap["fallacies"]
    csv_path = DATA / Path(expected["local_path"]).name
    _, _, header = _rows_and_columns(csv_path)
    missing = [c for c in snap["required_columns_fallacies"] if c not in header]
    assert not missing, (
        f"fallacies missing required columns: {missing}. "
        f"Re-pull from {snap['fallacies']['upstream_repo']}@{snap['fallacies']['upstream_commit']}"
    )


def test_required_columns_present_virtues() -> None:
    """All required columns are present in local virtues CSV."""
    snap = _load_snapshot()
    expected = snap["virtues"]
    csv_path = DATA / Path(expected["local_path"]).name
    _, _, header = _rows_and_columns(csv_path)
    missing = [c for c in snap["required_columns_virtues"] if c not in header]
    assert not missing, (
        f"virtues missing required columns: {missing}. "
        f"Re-pull from {snap['virtues']['upstream_repo']}@{snap['virtues']['upstream_commit']}"
    )


def test_no_utf8_bom_in_local_csvs() -> None:
    """Local CSVs are stored without the upstream BOM (encoding consistency).

    The upstream CSVs begin with ``\\xef\\xbb\\xbf`` (UTF-8 BOM glued to the first
    column header). Our local copy strips the BOM at ingest to match the rest
    of the repo. If a future re-pull forgets to strip, the local content_sha1
    test above will already fail; this test gives a more pointed diagnostic.
    """
    for csv_name in ("argumentum_fallacies_taxonomy.csv", "argumentum_virtues_taxonomy.csv"):
        path = DATA / csv_name
        first_bytes = path.read_bytes()[:3]
        assert first_bytes != b"\xef\xbb\xbf", (
            f"{csv_name} has a UTF-8 BOM at start of file; the ingest must strip it"
        )


def test_snapshot_references_valid_upstream() -> None:
    """Snapshot's upstream commit is a 40-char hex SHA."""
    snap = _load_snapshot()
    for key in ("fallacies", "virtues"):
        commit = snap[key]["upstream_commit"]
        assert len(commit) == 40, f"{key}.upstream_commit is not a full SHA: {commit!r}"
        int(commit, 16)  # raises if not hex


def test_fallacies_upstream_blob_sha_consistent() -> None:
    """upstream_blob_sha1 == sha1(local_bytes + BOM). Guards the BOM policy."""
    snap = _load_snapshot()
    expected = snap["fallacies"]
    csv_path = DATA / Path(expected["local_path"]).name
    local_bytes = csv_path.read_bytes()
    reconstructed = b"\xef\xbb\xbf" + local_bytes
    sha = hashlib.sha1(reconstructed).hexdigest()
    assert sha == expected["upstream_blob_sha1"], (
        f"fallacies upstream_blob_sha1 mismatch: snapshot says {expected['upstream_blob_sha1']}, "
        f"recomputing local+BOM gives {sha}. Either snapshot or ingest is wrong."
    )


def test_virtues_upstream_blob_sha_consistent() -> None:
    """upstream_blob_sha1 == sha1(local_bytes + BOM). Guards the BOM policy."""
    snap = _load_snapshot()
    expected = snap["virtues"]
    csv_path = DATA / Path(expected["local_path"]).name
    local_bytes = csv_path.read_bytes()
    reconstructed = b"\xef\xbb\xbf" + local_bytes
    sha = hashlib.sha1(reconstructed).hexdigest()
    assert sha == expected["upstream_blob_sha1"], (
        f"virtues upstream_blob_sha1 mismatch: snapshot says {expected['upstream_blob_sha1']}, "
        f"recomputing local+BOM gives {sha}. Either snapshot or ingest is wrong."
    )