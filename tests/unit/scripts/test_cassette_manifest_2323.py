"""#2323 provenance manifest: export emits it, import enforces it.

The recorder must be the replayer. The 211 cassettes committed on 18-19/09
were harvested on a worker box while the record job had not succeeded since
2026-08-17 — that door let the #2320 key drift in. The manifest binds a
fixtures dir to the record job run that produced it (run id + env signature
+ cassette-set digest); import refuses anything unbound or drifted.
"""

from __future__ import annotations

import importlib
import importlib.metadata as im
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from scripts.cassettes import export as cassette_export

# `import` is a keyword — the CLI module needs importlib.
cassette_import = importlib.import_module("scripts.cassettes.import")


def _make_cassette(fixtures_dir: Path, key: str, marker: str = "v1") -> None:
    (fixtures_dir / f"{key}.json").write_text(
        json.dumps({"key": key, "value": {"marker": marker}}), encoding="utf-8"
    )


def _write_manifest(fixtures_dir: Path, **overrides) -> None:
    keys = cassette_import._fixture_keys(fixtures_dir)
    manifest = {
        "schema": 1,
        "record_run_id": "35474667181",
        "record_sha": "333ee1d4" + "0" * 32,
        "recorded_at": "2026-09-19T22:55:09Z",
        "cassette_count": len(keys),
        "keys_sha256": cassette_import._keys_digest(keys),
        "env_signature": {
            pkg: im.version(pkg) if _has(pkg) else "absent"
            for pkg in cassette_export.KEY_DEP_PACKAGES
        },
    }
    manifest.update(overrides)
    (fixtures_dir / cassette_import.MANIFEST_NAME).write_text(
        json.dumps(manifest), encoding="utf-8"
    )


def _has(pkg: str) -> bool:
    try:
        im.version(pkg)
        return True
    except im.PackageNotFoundError:
        return False


@pytest.fixture()
def fixtures_dir(tmp_path: Path) -> Path:
    d = tmp_path / "fixtures"
    d.mkdir()
    _make_cassette(d, "a" * 64)
    _make_cassette(d, "b" * 64)
    return d


class TestVerifyManifest:
    def test_missing_manifest_fails_loud(self, fixtures_dir: Path) -> None:
        violations = cassette_import.verify_manifest(fixtures_dir)
        assert any("not provenance-tracked" in v for v in violations)
        assert any("local harvests" in v for v in violations)

    def test_valid_manifest_passes(self, fixtures_dir: Path) -> None:
        _write_manifest(fixtures_dir)
        assert cassette_import.verify_manifest(fixtures_dir) == []

    def test_count_drift_reddens(self, fixtures_dir: Path) -> None:
        _write_manifest(fixtures_dir)
        _make_cassette(fixtures_dir, "c" * 64)  # cassette added after export
        violations = cassette_import.verify_manifest(fixtures_dir)
        assert any("cassette count drift" in v for v in violations)
        assert any("digest mismatch" in v for v in violations)

    def test_digest_drift_reddens_despite_matching_count(
        self, fixtures_dir: Path
    ) -> None:
        _write_manifest(fixtures_dir)
        # Replace a cassette's key file: same count, different set.
        (fixtures_dir / ("a" * 64 + ".json")).unlink()
        _make_cassette(fixtures_dir, "d" * 64)
        violations = cassette_import.verify_manifest(fixtures_dir)
        assert any("digest mismatch" in v for v in violations)
        assert not any("count drift" in v for v in violations)

    def test_env_drift_names_the_package(self, fixtures_dir: Path) -> None:
        _write_manifest(fixtures_dir)
        manifest = json.loads(
            (fixtures_dir / cassette_import.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        some_pkg = sorted(manifest["env_signature"])[0]
        manifest["env_signature"][some_pkg] = "0.0.0-different"
        (fixtures_dir / cassette_import.MANIFEST_NAME).write_text(
            json.dumps(manifest), encoding="utf-8"
        )
        violations = cassette_import.verify_manifest(fixtures_dir)
        assert any(f"env drift on {some_pkg}" in v for v in violations)
        assert any("#2320 class" in v for v in violations)

    def test_missing_run_id_reddens(self, fixtures_dir: Path) -> None:
        _write_manifest(fixtures_dir, record_run_id="")
        assert any(
            "no record_run_id" in v
            for v in cassette_import.verify_manifest(fixtures_dir)
        )


class TestImportGate:
    def test_import_exit_3_without_manifest(
        self, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        rc = cassette_import.main([str(fixtures_dir), str(tmp_path / "db")])
        assert rc == 3

    def test_import_succeeds_with_valid_manifest(
        self, fixtures_dir: Path, tmp_path: Path
    ) -> None:
        _write_manifest(fixtures_dir)
        rc = cassette_import.main([str(fixtures_dir), str(tmp_path / "db")])
        assert rc == 0


class TestRefreshManifest:
    """The surgical SK-patch path (#2323): record_sk_cassette.py changes the
    cassette set, so the manifest must re-bind in the same transaction."""

    def test_refresh_rebinds_after_a_patch(self, fixtures_dir: Path) -> None:
        _write_manifest(fixtures_dir)
        _make_cassette(fixtures_dir, "c" * 64, marker="sk-patch")  # surgical add
        # Before refresh: the gate reddens (count/digest drift) — that is the
        # defect refresh_manifest exists to close.
        assert cassette_import.verify_manifest(fixtures_dir) != []
        assert (
            cassette_export.refresh_manifest(fixtures_dir, note="SK refresh #1950")
            is True
        )
        assert cassette_import.verify_manifest(fixtures_dir) == []
        manifest = json.loads(
            (fixtures_dir / cassette_import.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        assert manifest["cassette_count"] == 3
        assert len(manifest["sk_patches"]) == 1
        assert manifest["sk_patches"][0]["note"] == "SK refresh #1950"

    def test_refresh_declares_the_patching_env(self, fixtures_dir: Path) -> None:
        _write_manifest(fixtures_dir)
        _make_cassette(fixtures_dir, "c" * 64, marker="sk-patch")
        cassette_export.refresh_manifest(fixtures_dir, note="patch")
        manifest = json.loads(
            (fixtures_dir / cassette_import.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        # The patch env is recorded for provenance (SK keys embed prompt
        # wording, not env-computed scores — so it is declared, not gated).
        assert (
            manifest["sk_patches"][0]["recorded_env"] == cassette_export.env_signature()
        )

    def test_refresh_without_manifest_warns_and_refuses(
        self, fixtures_dir: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert cassette_export.refresh_manifest(fixtures_dir, note="x") is False
        assert "not provenance-tracked" in capsys.readouterr().err


class TestExportEmitsManifest:
    def test_export_writes_manifest_under_github_run_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import diskcache

        db_dir = tmp_path / "record_db"
        db = diskcache.Cache(str(db_dir))
        db.set("e" * 64, {"marker": "recorded"})
        db.close()

        fixtures = tmp_path / "fixtures"
        monkeypatch.setenv("GITHUB_RUN_ID", "4242424242")
        monkeypatch.setenv("GITHUB_SHA", "deadbeef" + "0" * 32)
        rc = cassette_export.main([str(db_dir), str(fixtures)])

        assert rc == 0
        manifest = json.loads(
            (fixtures / cassette_export.MANIFEST_NAME).read_text(encoding="utf-8")
        )
        assert manifest["record_run_id"] == "4242424242"
        assert manifest["record_sha"].startswith("deadbeef")
        assert manifest["cassette_count"] == 1
        # Round-trip: the emitted manifest must satisfy the import gate.
        assert cassette_import.verify_manifest(fixtures) == []

    def test_export_local_harvest_emits_no_manifest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import diskcache

        db_dir = tmp_path / "record_db"
        db = diskcache.Cache(str(db_dir))
        db.set("f" * 64, {"marker": "harvested"})
        db.close()

        fixtures = tmp_path / "fixtures"
        monkeypatch.delenv("GITHUB_RUN_ID", raising=False)
        rc = cassette_export.main([str(db_dir), str(fixtures)])

        assert rc == 0
        assert not (fixtures / cassette_export.MANIFEST_NAME).exists()
