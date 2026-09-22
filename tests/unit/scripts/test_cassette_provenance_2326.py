"""#2326 provenance: the gate checks the RUN, not just the manifest's say-so.

Measured hole (run against pre-#2326 ``main``): a locally-harvested fixtures
dir with a ``MANIFEST.json`` carrying a FABRICATED ``record_run_id`` imports
with rc=0 — every structural check passes (count, digest, env signature are
all self-consistent) because they were written by the same hand that wrote
the manifest. ``#2325``'s gate verifies consistency, not provenance.

The repair, per the issue's DoD:

* ``import.py --verify-run`` resolves ``record_run_id`` against the GitHub
  Actions run's own logs (``Exported cassettes: N`` — the one line the run
  itself emitted, unwritable by the manifest's author) and derives the true
  job baseline from it;
* ``sk_patches`` is finally READ: the gate reports the declared non-job
  delta and reddens when the disk's non-job delta exceeds it;
* the replay lanes pass ``--verify-run`` (the import gate was #2323's design:
  the band verifies the guard itself).

The test fakes sit at the HTTP boundary (``urllib.request.urlopen``) — the
real zip parsing, redirect-following call path, and error mapping run for
real. No network, no LLM, no JVM.
"""

from __future__ import annotations

import importlib
import io
import json
import sys
import urllib.error
import zipfile
from pathlib import Path
from typing import Any, Callable

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from scripts.cassettes import export as cassette_export

cassette_import = importlib.import_module("scripts.cassettes.import")

FABRICATED_RUN_ID = "9999999999"  # exists in no repo, no API, no log


def _has(pkg: str) -> bool:
    import importlib.metadata as im

    try:
        im.version(pkg)
        return True
    except im.PackageNotFoundError:
        return False


def _env_signature() -> dict[str, str]:
    import importlib.metadata as im

    return {
        pkg: (im.version(pkg) if _has(pkg) else "absent")
        for pkg in cassette_export.KEY_DEP_PACKAGES
    }


def _make_cassette(fixtures_dir: Path, key: str, marker: str = "v1") -> None:
    (fixtures_dir / f"{key}.json").write_text(
        json.dumps({"key": key, "value": {"marker": marker}}), encoding="utf-8"
    )


def _write_manifest(
    fixtures_dir: Path, run_id: str = FABRICATED_RUN_ID, **overrides: Any
) -> None:
    keys = cassette_import._fixture_keys(fixtures_dir)
    manifest = {
        "schema": 1,
        "record_run_id": run_id,
        "record_sha": "0" * 40,
        "recorded_at": "2026-09-20T00:00:00Z",
        "cassette_count": len(keys),
        "keys_sha256": cassette_import._keys_digest(keys),
        "env_signature": _env_signature(),
    }
    manifest.update(overrides)
    (fixtures_dir / cassette_import.MANIFEST_NAME).write_text(
        json.dumps(manifest), encoding="utf-8"
    )


@pytest.fixture()
def harvest_dir(tmp_path: Path) -> Path:
    """A locally-harvested shape: cassettes no record job ever produced."""
    d = tmp_path / "fixtures"
    d.mkdir()
    for k in ("a" * 64, "b" * 64, "c" * 64, "d" * 64):
        _make_cassette(d, k, marker="harvested-locally")
    _write_manifest(d)
    return d


def _zip_response(log_text: str) -> io.BytesIO:
    """An HTTP response body shaped like a GitHub run-logs archive."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("record job/5_Export cassettes/5_export.txt", log_text)
    buf.seek(0)
    return buf


def _fake_urlopen_with_log(
    log_text: str,
) -> Callable[[Any], io.BytesIO]:
    def _urlopen(req: Any, timeout: float = 30.0) -> io.BytesIO:
        return _zip_response(log_text)

    return _urlopen


def _fake_urlopen_404(req: Any, timeout: float = 30.0) -> io.BytesIO:
    raise urllib.error.HTTPError(
        str(getattr(req, "full_url", req)), 404, "Not Found", None, None
    )


class TestRunExportCount:
    """The one honest baseline: the line the run itself emitted."""

    def test_parses_the_export_line_from_the_logs_zip(self) -> None:
        count = cassette_import._run_export_count(
            "https://api.github.com",
            "o/r",
            "tok",
            "35474667181",
            urlopen=_fake_urlopen_with_log("Setup Miniconda\nExported cassettes: 33\n"),
        )
        assert count == 33

    def test_missing_line_is_an_error_not_a_guess(self) -> None:
        with pytest.raises(cassette_import.RunLogError, match="no.*Exported cassettes"):
            cassette_import._run_export_count(
                "https://api.github.com",
                "o/r",
                "tok",
                "1",
                urlopen=_fake_urlopen_with_log("nothing relevant here"),
            )

    def test_404_names_the_fabricated_run(self) -> None:
        with pytest.raises(cassette_import.RunLogError, match="9999999999.*404"):
            cassette_import._run_export_count(
                "https://api.github.com",
                "o/r",
                "tok",
                FABRICATED_RUN_ID,
                urlopen=_fake_urlopen_404,
            )


# The export step's log since #2323 (#2325), three lines as run 35792294382
# printed them: export.py wrote MANIFEST.json INTO the staging dir, and the
# step's ``*.json`` glob then counted it as a cassette (#2405).
def _post_2323_log(run_id: str, cassettes: int, glob_count: int) -> str:
    return (
        f"Exported: {cassettes}\n"
        f"Manifest: staging_cassettes\\MANIFEST.json (run {run_id}, "
        f"{cassettes} cassettes)\n"
        f"Exported cassettes: {glob_count}\n"
    )


class TestManifestInTheStagingDir:
    """#2405: since #2323 the staging dir carries the manifest, and the
    record line counted it — every honest record read as 'REMOVED'."""

    def test_the_manifest_is_not_a_cassette(self) -> None:
        # the measured band failure: 276 cassettes + MANIFEST.json → line 277
        count = cassette_import._run_export_count(
            "https://api.github.com",
            "o/r",
            "tok",
            "35792294382",
            urlopen=_fake_urlopen_with_log(_post_2323_log("35792294382", 276, 277)),
        )
        assert count == 276

    def test_the_repaired_producer_line_agrees(self) -> None:
        count = cassette_import._run_export_count(
            "https://api.github.com",
            "o/r",
            "tok",
            "1",
            urlopen=_fake_urlopen_with_log(_post_2323_log("1", 276, 276)),
        )
        assert count == 276

    def test_a_disagreeing_line_is_an_error_not_a_guess(self) -> None:
        with pytest.raises(cassette_import.RunLogError, match="disagree"):
            cassette_import._run_export_count(
                "https://api.github.com",
                "o/r",
                "tok",
                "1",
                urlopen=_fake_urlopen_with_log(_post_2323_log("1", 276, 280)),
            )

    def test_a_manifest_for_another_run_is_refused(self) -> None:
        with pytest.raises(cassette_import.RunLogError, match="run 2"):
            cassette_import._run_export_count(
                "https://api.github.com",
                "o/r",
                "tok",
                "1",
                urlopen=_fake_urlopen_with_log(_post_2323_log("2", 276, 277)),
            )

    def test_the_real_run_shape_imports_green(
        self, harvest_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # disk = the run's 4 cassettes; the line counted 5 (manifest included)
        monkeypatch.setattr(
            "urllib.request.urlopen",
            _fake_urlopen_with_log(_post_2323_log(FABRICATED_RUN_ID, 4, 5)),
        )
        violations, note = cassette_import.verify_run_provenance(
            harvest_dir, api_url="https://api.github.com", repo="o/r", token="tok"
        )
        assert violations == []
        assert note is not None and "exported 4 cassettes" in note

    def test_a_really_removed_cassette_still_reddens(
        self, harvest_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # control: the run exported 5 cassettes (line 6); disk carries 4
        monkeypatch.setattr(
            "urllib.request.urlopen",
            _fake_urlopen_with_log(_post_2323_log(FABRICATED_RUN_ID, 5, 6)),
        )
        violations, _ = cassette_import.verify_run_provenance(
            harvest_dir, api_url="https://api.github.com", repo="o/r", token="tok"
        )
        assert any("REMOVED" in v for v in violations)


class TestVerifyRunProvenance:
    """Delta declared vs delta actual — sk_patches finally read."""

    def _manifest_with_patch(self, harvest_dir: Path, baseline: int) -> None:
        manifest = json.loads(
            (harvest_dir / cassette_import.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        manifest["sk_patches"] = [
            {
                "note": "SK refresh #1950",
                "at": "2026-09-20T01:00:00Z",
                "recorded_env": _env_signature(),
                "cassette_count": baseline + 1,
                "keys_sha256": manifest["keys_sha256"],
            }
        ]
        (harvest_dir / cassette_import.MANIFEST_NAME).write_text(
            json.dumps(manifest), encoding="utf-8"
        )

    def test_declared_delta_passes_and_is_reported(
        self, harvest_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # run exported 33; one declared SK patch brought the set to 34 = disk
        _make_cassette(harvest_dir, "e" * 64, marker="sk-patch")  # 5 cassettes
        _write_manifest(harvest_dir)
        self._manifest_with_patch(harvest_dir, baseline=4)
        monkeypatch.setattr(
            "urllib.request.urlopen",
            _fake_urlopen_with_log("Exported cassettes: 4\n"),
        )
        violations, note = cassette_import.verify_run_provenance(
            harvest_dir,
            api_url="https://api.github.com",
            repo="o/r",
            token="tok",
        )
        assert violations == []
        assert note is not None and "declared non-job delta 1" in note
        assert "sk_patches: 1" in note

    def test_undeclared_delta_reddens(
        self, harvest_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # run exported 2; disk carries 4 with NO patch declared
        monkeypatch.setattr(
            "urllib.request.urlopen",
            _fake_urlopen_with_log("Exported cassettes: 2\n"),
        )
        violations, _ = cassette_import.verify_run_provenance(
            harvest_dir, api_url="https://api.github.com", repo="o/r", token="tok"
        )
        assert any("exceeds the manifest" in v for v in violations)
        assert any("#2326" in v for v in violations)

    def test_disk_below_the_run_export_reddens(
        self, harvest_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # run exported 8; disk carries 4 — cassettes removed after export
        monkeypatch.setattr(
            "urllib.request.urlopen",
            _fake_urlopen_with_log("Exported cassettes: 8\n"),
        )
        violations, _ = cassette_import.verify_run_provenance(
            harvest_dir, api_url="https://api.github.com", repo="o/r", token="tok"
        )
        assert any("REMOVED" in v for v in violations)

    def test_no_patch_exact_run_set_passes(
        self, harvest_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            "urllib.request.urlopen",
            _fake_urlopen_with_log("Exported cassettes: 4\n"),
        )
        violations, note = cassette_import.verify_run_provenance(
            harvest_dir, api_url="https://api.github.com", repo="o/r", token="tok"
        )
        assert violations == []
        assert note is not None and "declared non-job delta 0" in note


class TestNegativeControl:
    """The DoD's mandatory negative control: a fabricated run id reddens.

    Measured against pre-#2326 main() this exact directory imported rc=0
    (the hole). With --verify-run the run must be resolvable — 404 is a
    provenance violation, not a skip.
    """

    def test_fabricated_run_id_refuses_import(
        self,
        harvest_dir: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr("urllib.request.urlopen", _fake_urlopen_404)
        monkeypatch.setenv("GITHUB_TOKEN", "ci-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "jsboigeEpita/repo")
        rc = cassette_import.main(
            [str(harvest_dir), str(tmp_path / "db"), "--verify-run"]
        )
        assert rc == 3

    def test_verify_run_without_credentials_fails_loud(
        self, harvest_dir: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        monkeypatch.delenv("GH_TOKEN", raising=False)
        rc = cassette_import.main(
            [str(harvest_dir), str(tmp_path / "db"), "--verify-run"]
        )
        assert rc == 3

    def test_real_run_shape_imports_green(
        self,
        harvest_dir: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # the live shape: run exported exactly the disk set, no patches
        monkeypatch.setattr(
            "urllib.request.urlopen",
            _fake_urlopen_with_log("Exported cassettes: 4\n"),
        )
        monkeypatch.setenv("GITHUB_TOKEN", "ci-token")
        monkeypatch.setenv("GITHUB_REPOSITORY", "jsboigeEpita/repo")
        rc = cassette_import.main(
            [str(harvest_dir), str(tmp_path / "db"), "--verify-run"]
        )
        assert rc == 0


class TestStructuralGateUnchanged:
    """Non-regression: without --verify-run the #2323 behaviour is intact
    (structural checks only — no token sniffing, no network)."""

    def test_valid_manifest_without_flag_still_imports(
        self, harvest_dir: Path, tmp_path: Path
    ) -> None:
        rc = cassette_import.main([str(harvest_dir), str(tmp_path / "db")])
        assert rc == 0


class TestRecordSkAppendMode:
    """#2326 root repair, script half: the record job needs the SK-path
    cassette to land in the DB the pytest record run already filled."""

    def test_append_preserves_the_existing_db(self, tmp_path: Path) -> None:
        from scripts.cassettes.record_sk_cassette import _prepare_cache_dir

        cache = tmp_path / "shared_db"
        cache.mkdir()
        sentinel = cache / "pytest_recorded.json"
        sentinel.write_text("{}", encoding="utf-8")
        _prepare_cache_dir(cache, append=True)
        assert sentinel.exists()

    def test_default_wipes_the_scratch_db(self, tmp_path: Path) -> None:
        from scripts.cassettes.record_sk_cassette import _prepare_cache_dir

        cache = tmp_path / "scratch"
        cache.mkdir()
        stale = cache / "stale.json"
        stale.write_text("{}", encoding="utf-8")
        _prepare_cache_dir(cache, append=False)
        assert not stale.exists()

    def test_append_creates_a_missing_dir(self, tmp_path: Path) -> None:
        from scripts.cassettes.record_sk_cassette import _prepare_cache_dir

        cache = tmp_path / "fresh"
        _prepare_cache_dir(cache, append=True)
        assert cache.is_dir()
