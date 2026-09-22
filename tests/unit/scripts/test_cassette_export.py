"""Export-boundary refusal tests for LLM cassettes (#1603, #1792 rework).

A dict value carrying ``_fallback`` is the marker ``_serialize_chat_completion``
writes when it gives up on a response. Such a cassette replays as a
``str``/choices-less value — an unusable cassette wearing the shape of a real
one. The refusal lives at the export boundary (``export_one`` returns
``"degraded"``) so ``llm_cache.py`` stays free of record-shape guards and the
BO-3 replay invariants stay un-widened.
"""

from __future__ import annotations

import json
from pathlib import Path

import diskcache
import pytest

from scripts.cassettes.export import export_one, main


def _sk_value() -> list[dict]:
    # Minimal SK-path shape (list of dicts): passes the privacy audit.
    return [
        {
            "role": "assistant",
            "content": "Réponse synthétique de test.",
        }
    ]


def test_fallback_marker_dict_is_refused_as_degraded(tmp_path: Path) -> None:
    value = {"_fallback": "non-serializable response", "model": "gpt-5-mini"}
    status = export_one(None, "a" * 32, value, tmp_path, allow_unsafe=False)
    assert status == "degraded"
    assert not (tmp_path / ("a" * 32 + ".json")).exists()


def test_degraded_refusal_takes_precedence_over_privacy_audit(
    tmp_path: Path,
) -> None:
    # A degraded marker containing privacy-violating prose must still be
    # classified "degraded" (the more specific diagnosis), not "unsafe".
    value = {"_fallback": "raw_text: corpus_A."}
    status = export_one(None, "b" * 32, value, tmp_path, allow_unsafe=False)
    assert status == "degraded"


def test_clean_dict_value_still_exports(tmp_path: Path) -> None:
    value = {"model": "gpt-5-mini", "note": "réponse synthétique."}
    status = export_one(None, "c" * 32, value, tmp_path, allow_unsafe=False)
    assert status == "ok"
    assert (tmp_path / ("c" * 32 + ".json")).exists()


def test_clean_list_value_still_exports(tmp_path: Path) -> None:
    status = export_one(None, "d" * 32, _sk_value(), tmp_path, allow_unsafe=False)
    assert status == "ok"
    assert (tmp_path / ("d" * 32 + ".json")).exists()


def test_allow_unsafe_does_not_bypass_degraded_refusal(tmp_path: Path) -> None:
    # --allow-unsafe skips the privacy audit, never the degraded check: an
    # unusable cassette must not enter the fixtures even under explicit review.
    value = {"_fallback": "x"}
    status = export_one(None, "e" * 32, value, tmp_path, allow_unsafe=True)
    assert status == "degraded"


def test_main_reports_degraded_but_does_not_exit_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Only privacy violations gate the exit code (#1603). A degraded-only run
    # is an informational refusal: exit 0, degraded count in the summary.
    #
    # #2323: pin the CI shape explicitly. GitHub Actions exports GITHUB_RUN_ID
    # into every job — including pytest processes — so an export invoked by a
    # test inside CI emits MANIFEST.json (measured: this very test reddened on
    # the PR's CI with a surprise manifest in the empty fixtures dir). Setting
    # it here makes every box assert the real contract: NO cassette is written,
    # and the manifest is emitted with cassette_count=0.
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    db_dir = tmp_path / "db"
    db = diskcache.Cache(str(db_dir))
    db["f" * 32] = {"_fallback": "x"}
    db.close()

    fixtures = tmp_path / "fixtures"
    rc = main([str(db_dir), str(fixtures)])
    assert rc == 0
    assert not [
        p for p in fixtures.glob("*.json") if p.name != "MANIFEST.json"
    ], "a degraded value must not produce a cassette"
    manifest = json.loads((fixtures / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["cassette_count"] == 0
    assert manifest["record_run_id"] == "42"


def test_main_names_why_each_cassette_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    # Record run 35783523640 refused 3 cassettes and printed only their key
    # prefixes: the runner was gone, the values unrecoverable, and the run
    # (which writes no MANIFEST on refusal) lost for an unreadable reason. The
    # refusal must name its rule, its hint and its path — never the prose.
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    db_dir = tmp_path / "db"
    db = diskcache.Cache(str(db_dir))
    prose = "Une réponse synthétique qui situe son exemple en 1999 seulement."
    db["9" * 32] = [{"role": "assistant", "content": prose}]
    db.close()

    rc = main([str(db_dir), str(tmp_path / "fixtures")])

    err = capsys.readouterr().err
    assert rc == 2
    assert "historical-year hint 1999" in err, err
    assert "content" in err, err
    assert "situe son exemple" not in err, "the refusal log must not carry prose"
