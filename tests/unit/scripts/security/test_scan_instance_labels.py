# -*- coding: utf-8 -*-
"""Unit tests of the instance-label probe (#3575).

Every fixture here is SYNTHETIC — invented names, invented text. The real
census labels never enter a tracked file, not even a test's: the probe's own
contract is that its derivation works on any definitions, so these tests
feed it the same shapes with made-up vocabulary.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from argumentation_analysis.evaluation.corpus_instance_tokens import (
    derive_instance_tokens,
)

SPEC = importlib.util.spec_from_file_location(
    "scan_instance_labels",
    Path(__file__).resolve().parents[4] / "scripts/security/scan_instance_labels.py",
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod  # dataclasses resolves annotations via sys.modules
SPEC.loader.exec_module(mod)

REPO_ROOT = Path(__file__).resolve().parents[4]

# Synthetic census — the two shapes a source_name takes (plain words, and a
# title whose short function words must not become tokens).
DEFS = [
    {"source_name": "Alpha Corpus Speech"},
    {"source_name": "Kappa Symposium Keynote Address"},
]

QUOTE = "the eastern tariffs and the northern fleet"  # 42 chars, inside raw_text
LONG_WORD = "theeasterntariffsandthenorthernfleet"  # 36 chars, no space


def synth_state() -> dict:
    return {
        "raw_text": (
            "zzz filler open. The General Borax addressed the Meridian Assembly "
            f"at length about {QUOTE}. qqq filler close."
        ),
        "strategic_read": {
            "players": [{"name": "General Borax"}, {"name": "Tarquin Vox"}],
            "preferences": {"General Borax": [], "Eastern Coalition": []},
        },
        "stakes_and_stakeholders": {"stakeholders": [{"name": "Northern League"}]},
        "source_metadata": {"speaker": "General Borax"},
    }


def write(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def probe(
    tmp_path,
    *,
    target_body,
    definitions=None,
    states=None,
    baseline=(),
    df_threshold=mod.DEFAULT_DF_THRESHOLD,
    window=None,
):
    target = write(tmp_path, "target.md", target_body)
    kwargs = dict(
        baseline=list(baseline),
        targets=[target],
        definitions=definitions,
        states=states,
        df_threshold=df_threshold,
    )
    if window is not None:
        kwargs["window"] = window
    return mod.run_probe(**kwargs)


# --- derivation ------------------------------------------------------------
def test_normalize_collapses_case_accents_and_punctuation():
    assert mod.normalize("Ïlévanne-Pörtyge (XQZ)") == "ilevanne portyge xqz"
    assert mod.normalize("Café\r\ndu  Commerce") == "cafe du commerce"


def test_token_ids_and_repr_are_opaque():
    tokens = mod.derive_dataset_tokens(DEFS)
    assert [t.opaque for t in tokens] == [
        "src0:name0",  # the whole label first
        "src0:name0:w0",  # alpha
        "src0:name0:w1",  # corpus
        "src0:name0:w2",  # speech
        "src1:name0",
        "src1:name0:w0",  # kappa
        "src1:name0:w1",  # symposium
        "src1:name0:w2",  # keynote
        "src1:name0:w3",  # address
    ]
    for token in tokens:  # a traceback must not leak the vocabulary either
        assert token.text not in repr(token)


def test_dataset_rule_is_the_canonical_one():
    # #2187: capitalised runs of >= 4 chars — "Beta" and "Forum" are in, the
    # lower-case function words and the bare year are not
    tokens = mod.derive_dataset_tokens([{"source_name": "Beta Forum of 1997"}])
    assert [t.opaque for t in tokens] == [
        "src0:name0",
        "src0:name0:w0",
        "src0:name0:w1",
    ]


def test_dataset_vocabulary_is_the_canonical_derivation():
    """One father (#3575): the probe's dataset vocabulary IS #2187's, normalised.

    Also pins the rule itself: a capitalised 4-char run belongs to the
    vocabulary — a second, stricter rule in the probe would silently shrink
    it while the scrubber kept redacting with the full one.
    """
    defs = DEFS + [
        {"source_name": "Beta Forum of 1997"},
        {"source_name": "Käprikarne Sömance"},
    ]
    canonical = {mod.normalize(t) for t in derive_instance_tokens(defs)}
    probe_vocab = {t.text for t in mod.derive_dataset_tokens(defs)}
    assert probe_vocab == canonical
    assert "beta" in probe_vocab and "forum" in probe_vocab


# --- label matching --------------------------------------------------------
def test_scan_counts_full_name_and_distinctive_words(tmp_path):
    result = probe(
        tmp_path,
        target_body="The report cites the Alpha Corpus Speech and its corpus; speech alone.\n",
        definitions=DEFS,
    )
    assert result.hits[0].labels == {
        "src0:name0": 1,  # the whole label, once
        "src0:name0:w0": 1,  # alpha: inside the label
        "src0:name0:w1": 2,  # corpus: inside the label + bare
        "src0:name0:w2": 2,  # speech: inside the label + bare
    }


def test_word_embedded_in_a_longer_word_never_matches(tmp_path):
    result = probe(
        tmp_path,
        target_body="speechcraft and corpuspeak are not labels\n",
        definitions=DEFS,
    )
    assert result.hits == []
    assert not mod.contains_phrase("lesclaves everywhere", "esclave")
    assert mod.contains_phrase("l esclavage everywhere", "esclavage")


def test_accented_label_matches_its_ascii_form(tmp_path):
    result = probe(
        tmp_path,
        definitions=[{"source_name": "Käprikarne Sömance"}],
        target_body="see Kaprikarne Somance in the export\n",
    )
    assert result.hits[0].labels["src0:name0"] == 1


# --- the generic-word filter (document frequency) ---------------------------
def test_df_filter_drops_repo_vocabulary(tmp_path):
    baseline = [
        write(tmp_path, f"b{i}.md", "common notes about the Zephyr Vortane Address\n")
        for i in range(mod.DEFAULT_DF_THRESHOLD + 2)
    ]
    result = probe(
        tmp_path,
        definitions=[{"source_name": "Zephyr Vortane Address"}],
        target_body="a leaked line naming the Zephyr Vortane Address\n",
        baseline=baseline,
    )
    assert result.live_ids == []
    assert result.generic_ids  # the phrase and its words are all repo vocabulary
    assert result.hits == []


def test_df_filter_keeps_rare_tokens(tmp_path):
    baseline = [
        write(tmp_path, f"b{i}.md", "unrelated note\n")
        for i in range(mod.DEFAULT_DF_THRESHOLD + 2)
    ]
    result = probe(
        tmp_path,
        definitions=[{"source_name": "Zephyr Vortane Address"}],
        target_body="a leaked line naming the Zephyr Vortane Address\n",
        baseline=baseline,
    )
    assert "src0:name0" in result.live_ids
    assert result.hits[0].labels["src0:name0"] == 1


# --- the raw-text window channel -------------------------------------------
def test_window_channel_counts_one_quote_whatever_its_length(tmp_path):
    result = probe(
        tmp_path,
        states=[synth_state()],
        target_body=f"quotation body >> {QUOTE} << end of body\n",
    )
    runs, chars = result.hits[0].windows["state0:window"]
    assert runs == 1  # one passage, however long — not one leak per gram
    assert chars >= len(QUOTE)  # the run covers the whole quote (it may run a
    # char or two past it when both sides continue with a space)


def test_window_below_the_threshold_does_not_fire(tmp_path):
    result = probe(
        tmp_path,
        states=[
            {
                "raw_text": f"aaaa {LONG_WORD} bbbb",
                "strategic_read": {},
            }
        ],
        target_body=f"xx{LONG_WORD[:27]}yy\n",
    )
    assert result.hits == []


def test_window_matches_a_rewrapped_quote(tmp_path):
    rewrapped = QUOTE.replace(" tariffs", "\ntariffs")
    result = probe(
        tmp_path,
        states=[synth_state()],
        target_body=f"replay notes: {rewrapped} — recorded\n",
    )
    assert result.hits[0].windows["state0:window"][0] == 1


# --- recorded-state name channel -------------------------------------------
def test_state_tokens_cover_players_parties_and_preferences():
    tokens = mod.derive_state_tokens(synth_state(), "state0")
    assert {t.opaque for t in tokens} == {
        "state0:player0",
        "state0:player0:w0",  # General Borax + general
        "state0:player1",
        "state0:player1:w0",  # Tarquin Vox + tarquin
        "state0:player2",
        "state0:player2:w0",
        "state0:player2:w1",  # Eastern Coalition
        "state0:party0",
        "state0:party0:w0",
        "state0:party0:w1",  # Northern League
    }  # the speaker duplicates player0: deduplicated, no second id


def test_state_scan_hits_names_in_a_target(tmp_path):
    result = probe(
        tmp_path,
        states=[synth_state()],
        target_body="The replay shows Tarquin Vox meeting the Northern League.\n",
    )
    labels = result.hits[0].labels
    assert labels["state0:player1"] == 1
    assert labels["state0:party0"] == 1


# --- CLI: exit codes and opacity -------------------------------------------
@pytest.fixture(autouse=False)
def no_passphrase(monkeypatch):
    """Hermetic main() tests: a seat may export the passphrase globally, and a
    unit test must not depend on which seat runs it."""
    monkeypatch.delenv("TEXT_CONFIG_PASSPHRASE", raising=False)


def test_main_states_only_returns_1_on_a_hit(tmp_path, capsys, no_passphrase):
    states_dir = tmp_path / "states"
    states_dir.mkdir()
    (states_dir / "state_full_synth.json").write_text(
        json.dumps(synth_state()), encoding="utf-8"
    )
    body = write(
        tmp_path, "body.md", f"free replay quotes >> {QUOTE} << and Tarquin Vox\n"
    )
    code = mod.main(["--from-states", str(states_dir), str(body)])
    out = capsys.readouterr().out
    assert code == 1
    assert "state0:window" in out and "state0:player1" in out


def test_main_clean_target_returns_0(tmp_path, capsys, no_passphrase):
    states_dir = tmp_path / "states"
    states_dir.mkdir()
    (states_dir / "state_full_synth.json").write_text(
        json.dumps(synth_state()), encoding="utf-8"
    )
    body = write(tmp_path, "body.md", "an ordinary PR body about refactoring\n")
    assert mod.main(["--from-states", str(states_dir), str(body)]) == 0
    assert "[HIT]" not in capsys.readouterr().out


def test_main_without_any_vocabulary_source_refuses_to_run_clean(
    tmp_path, capsys, no_passphrase
):
    code = mod.main(["--env-file", str(tmp_path / ".env"), str(tmp_path / "body.md")])
    assert code == 2
    assert "no vocabulary source" in capsys.readouterr().out


def test_missing_target_is_an_instrument_error(tmp_path):
    result = mod.run_probe(
        baseline=[],
        targets=[tmp_path / "absent.md"],
        definitions=DEFS,
    )
    assert result.errors and "target not found" in result.errors[0]


def test_output_publishes_counts_and_ids_only(tmp_path, capsys):
    states_dir = tmp_path / "states"
    states_dir.mkdir()
    (states_dir / "state_full_synth.json").write_text(
        json.dumps(synth_state()), encoding="utf-8"
    )
    body = write(
        tmp_path,
        "body.md",
        f"replay: {QUOTE} — signed Tarquin Vox of the Northern League\n",
    )
    mod.main(["--from-states", str(states_dir), str(body)])
    out = capsys.readouterr().out
    for secret in ("Tarquin", "Northern League", QUOTE, "General Borax"):
        assert secret not in out
    assert "state0:" in out
