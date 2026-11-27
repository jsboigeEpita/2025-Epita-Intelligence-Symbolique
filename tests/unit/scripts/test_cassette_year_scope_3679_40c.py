"""The year rule of the export audit has a scope (#3679 item 40c).

Record run 45351057154 (head ``6b913b1b4``, Haiku route) answered 507 times
and its export refused 3 cassettes on the historical-year rule, so it wrote no
``MANIFEST.json`` and the run was lost for the band. The three findings are in
the run's own public log (lines 2886-2888), each with its token and its JSON
path, and each was traced to its request: two historical dates the model
supplied from general knowledge on public test fixtures, and one budget figure
restated without its currency word (a classification read from the tokens and
the requests — the surrounding prose is unrecoverable). None came from the
corpus: the band population never decrypts it (0 call to the dataset loader in
a local replay of the exact record population; 0 loader line in the CI run
log, where the INFO lines of other core modules do reach the log).

The rule is a hint detector with no provenance: a year in an answer is treated
as possible corpus prose. So it blocks whenever the recording run COULD read
the corpus, and is reported — not blocking — only for a run that could not: a
band record, whose step runs without the dataset passphrase (a runner's only
copy of the corpus is the encrypted file). The export learns that from the
record step itself. Nothing here is a switch of the export: the default stays
strict, and the two other rules block everywhere.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import diskcache
import pytest

from scripts.cassettes import export, privacy

# The word the record step writes to the export step when it withheld the
# passphrase — and the values that must NOT be read as it.
WITHHELD = "withheld"
ENV = "RECORD_DATASET_PASSPHRASE"

YEAR_PROSE = "Une réponse synthétique qui situe son exemple en 1974 seulement."
CLEAN_PROSE = "Une réponse synthétique qui porte un budget de 2000 euros."


def _db(tmp_path: Path, entries: dict) -> Path:
    db_dir = tmp_path / "db"
    db = diskcache.Cache(str(db_dir))
    for key, value in entries.items():
        db[key] = value
    db.close()
    return db_dir


def _export(tmp_path: Path, entries: dict):
    db_dir = _db(tmp_path, entries)
    fixtures = tmp_path / "fixtures"
    rc = export.main([str(db_dir), str(fixtures)])
    return rc, fixtures


def _a_name_the_detector_knows() -> str:
    """One sentence built on a word of the shared class vocabulary.

    The word is read from the vocabulary at run time, so no name is written
    here.
    """
    for word in re.findall(r"[A-Za-zÀ-ÿ]{3,}", privacy.PERSON_RE.pattern):
        sentence = f"La position de {word} sur le sujet est reprise ici."
        if privacy.PERSON_RE.search(sentence):
            return sentence
    raise AssertionError("no word of the class vocabulary matches on its own")


# --- The default is unchanged ------------------------------------------------


def test_by_default_a_year_hint_refuses_the_cassette_and_the_manifest(
    tmp_path, monkeypatch, capsys
):
    """The status quo, pinned: nothing in this PR relaxes it."""
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.delenv(ENV, raising=False)
    rc, fixtures = _export(tmp_path, {"9" * 32: [{"content": YEAR_PROSE}]})
    assert rc == 2
    assert not (fixtures / f"{'9' * 32}.json").exists()
    assert not (fixtures / "MANIFEST.json").exists()
    out, err = capsys.readouterr()
    assert "historical-year hint 1974" in err
    # The scope is named only where it was used: on a strict export, such a
    # line would tell the reader of the log that the hints were not refused.
    assert "without the dataset passphrase" not in out + err


def test_export_one_blocks_a_year_hint_by_default(tmp_path, monkeypatch):
    """The function's own default, with no caller and no environment."""
    monkeypatch.setenv(ENV, WITHHELD)  # the environment must not reach it
    key = "9" * 32
    db_dir = _db(tmp_path, {key: [{"content": YEAR_PROSE}]})
    db = diskcache.Cache(str(db_dir))
    try:
        status = export.export_one(
            db, key, db[key], tmp_path / "out", allow_unsafe=False
        )
    finally:
        db.close()
    assert status == "unsafe"
    assert not (tmp_path / "out" / f"{key}.json").exists()


@pytest.mark.parametrize("value", ["", "given", "Withheld", " withheld", "withheld "])
def test_no_spelling_but_the_record_step_s_scopes_the_rule(
    tmp_path, monkeypatch, value
):
    monkeypatch.setenv(ENV, value)
    rc, _ = _export(tmp_path, {"9" * 32: [{"content": YEAR_PROSE}]})
    assert rc == 2


# --- A record that ran without the passphrase --------------------------------


def test_a_record_that_ran_without_the_passphrase_exports_and_reports(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.setenv(ENV, WITHHELD)
    rc, fixtures = _export(
        tmp_path,
        {"9" * 32: [{"content": YEAR_PROSE}], "8" * 32: [{"content": CLEAN_PROSE}]},
    )
    assert rc == 0
    assert (fixtures / f"{'9' * 32}.json").exists()
    assert (fixtures / f"{'8' * 32}.json").exists()
    out, err = capsys.readouterr()
    assert "Refused (privacy): 0" in out
    assert (
        "Year hints reported (the record ran without the dataset passphrase): 1 on 1 "
        "cassette(s)"
    ) in out
    assert (
        "The record step ran this record without the dataset passphrase: "
        "historical-year hints are reported, not refused."
    ) in out
    # The scope is named before the counts: « Refused: 0 » is not the full audit.
    assert out.index("without the dataset passphrase") < out.index("Refused (privacy)")
    # The hint is still named — rule, token, path; never the prose.
    assert "historical-year hint 1974" in err
    assert "content" in err
    assert "situe son exemple" not in err


def test_the_manifest_of_such_a_record_names_the_scope_and_the_cassettes(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.setenv(ENV, WITHHELD)
    _rc, fixtures = _export(tmp_path, {"9" * 32: [{"content": YEAR_PROSE}]})
    manifest = json.loads((fixtures / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["record_dataset_passphrase"] == WITHHELD
    assert manifest["year_hint_cassettes"] == ["9" * 16]
    assert manifest["cassette_count"] == 1


def test_a_manifest_of_an_ordinary_record_carries_no_scope(tmp_path, monkeypatch):
    """The keys above exist only where the scope was used."""
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    monkeypatch.delenv(ENV, raising=False)
    _rc, fixtures = _export(tmp_path, {"7" * 32: [{"content": CLEAN_PROSE}]})
    manifest = json.loads((fixtures / "MANIFEST.json").read_text(encoding="utf-8"))
    assert "record_dataset_passphrase" not in manifest
    assert "year_hint_cassettes" not in manifest


# --- Only the year rule is scoped --------------------------------------------


def test_a_source_name_still_refuses_under_the_scope(tmp_path, monkeypatch, capsys):
    """A name is a stronger hint than a year, and none was measured false."""
    monkeypatch.setenv(ENV, WITHHELD)
    named = _a_name_the_detector_knows()
    # A year next to the name does not hide it behind the reported hints.
    rc, fixtures = _export(
        tmp_path, {"9" * 32: [{"content": named + " " + YEAR_PROSE}]}
    )
    assert rc == 2
    assert not (fixtures / f"{'9' * 32}.json").exists()
    assert "source-name hint" in capsys.readouterr().err


def test_a_forbidden_key_still_refuses_under_the_scope(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV, WITHHELD)
    rc, fixtures = _export(tmp_path, {"9" * 32: {"raw_text": "x", "note": "clean"}})
    assert rc == 2
    assert not (fixtures / f"{'9' * 32}.json").exists()


def test_a_degraded_value_is_still_refused_under_the_scope(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setenv(ENV, WITHHELD)
    rc, fixtures = _export(tmp_path, {"9" * 32: {"_fallback": "x"}})
    assert rc == 0  # degraded is informational, as before
    assert not (fixtures / f"{'9' * 32}.json").exists()
    assert "Refused (degraded value — unusable cassette): 1" in capsys.readouterr().out


# --- The rules, by name ------------------------------------------------------


def test_the_two_audit_entry_points_say_the_same_thing():
    value = [
        {"raw_text": "x"},
        {"content": _a_name_the_detector_knows() + " " + YEAR_PROSE},
    ]
    findings = privacy.audit_findings(value, source="t")
    assert [description for _rule, description in findings] == privacy.audit_value(
        value, source="t"
    )
    assert [rule for rule, _description in findings] == [
        privacy.RULE_FORBIDDEN_KEY,
        privacy.RULE_SOURCE_NAME,
        privacy.RULE_HISTORICAL_YEAR,
    ]


def test_only_the_year_rule_is_scoped():
    """A fourth rule must be classed here before it exists silently."""
    assert privacy.RULES == frozenset(
        {
            privacy.RULE_FORBIDDEN_KEY,
            privacy.RULE_SOURCE_NAME,
            privacy.RULE_HISTORICAL_YEAR,
        }
    )
    assert privacy.SCOPED_RULES == frozenset({privacy.RULE_HISTORICAL_YEAR})
