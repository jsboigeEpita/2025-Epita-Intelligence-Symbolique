"""Synthetic guards for the equal-input panel variants (#3477)."""

import json

import compare_orchestration_modes as harness
import pytest
from scripts.dataset import judge_panel
from scripts.dataset import run_zeroshot_arm as arm
from scripts.dataset.run_corpus_batch import expand_corpus


def test_panel_records_match_batch_expansion_and_preserve_order(monkeypatch):
    from argumentation_analysis.core import io_manager
    from argumentation_analysis.core.utils import crypto_utils

    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-salt-3477")
    definitions = [
        {
            "source_name": "synthetic-source",
            "metadata": {"genre": "synthetic-genre", "title": "source-title"},
            "extracts": [
                {"extract_text": "first", "metadata": {"title": "extract-title"}},
                {"extract_text": "second"},
            ],
        }
    ]
    docs, _, _ = expand_corpus(definitions)
    panel = [docs[1]["opaque_id"], docs[0]["opaque_id"]]
    monkeypatch.setattr(judge_panel, "_passphrase_or_exit", lambda: "synthetic")
    monkeypatch.setattr(crypto_utils, "derive_encryption_key", lambda _: b"synthetic")
    monkeypatch.setattr(
        io_manager, "load_extract_definitions", lambda **kwargs: definitions
    )
    records = judge_panel.load_document_records(panel)
    assert list(records) == panel
    assert records[panel[1]]["metadata"] == docs[0]["metadata"]
    assert records[panel[1]]["metadata"]["title"] == "extract-title"
    assert judge_panel.load_document_texts(panel) == {
        panel[0]: "second",
        panel[1]: "first",
    }
    with pytest.raises(SystemExit, match="missing-id"):
        judge_panel.load_document_records(["missing-id"])


def test_plain_prompt_remains_exactly_the_historical_prompt():
    text = "Texte synthétique."
    assert arm.build_prompt(text) == arm.ZEROSHOT_PROMPT.format(text=text)


def test_header_metadata_reaches_the_payload_without_changing_the_text():
    text = "Texte synthétique."
    metadata = {"author": "synthetic-author", "genre": "synthetic-genre"}
    prompt = arm.build_payload("model", text, source_metadata=metadata)["messages"][0][
        "content"
    ]
    header, historical = prompt.split("\n\n", 1)
    assert json.loads(header.removeprefix("Métadonnées de la source : ")) == metadata
    assert historical == arm.ZEROSHOT_PROMPT.format(text=text)


async def test_resume_keeps_plain_and_header_outputs_separate(monkeypatch, tmp_path):
    monkeypatch.setattr(arm, "RESULTS_DIR", tmp_path / "plain")
    monkeypatch.setattr(arm, "load_definitions", lambda: [])
    monkeypatch.setattr(arm, "parse_doc_ids", lambda *args: None)
    monkeypatch.setattr(
        arm,
        "expand_corpus",
        lambda *args: (
            [
                {
                    "opaque_id": "doc_A",
                    "full_text": "synthetic text",
                    "metadata": {"genre": "synthetic"},
                }
            ],
            [],
            0,
        ),
    )
    monkeypatch.setattr(
        arm,
        "resolve_arm_endpoint",
        lambda: {
            "model_id": "model",
            "base_url": "https://example.invalid",
            "api_key": "synthetic",
        },
    )
    calls = []

    async def fake_call(endpoint, text, timeout, **kwargs):
        calls.append(kwargs)
        return {
            "status_code": 200,
            "answer": "synthetic answer",
            "finish_reason": "stop",
        }

    monkeypatch.setattr(arm, "call_zeroshot", fake_call)
    assert await arm.run_arm(["--skip-existing"]) == 0
    assert await arm.run_arm(["--skip-existing", "--with-source-header"]) == 0
    assert len(calls) == 2
    assert "source_metadata" not in calls[0]
    assert calls[1]["source_metadata"] == {"genre": "synthetic"}
    plain = json.loads((tmp_path / "plain" / "doc_A.json").read_text(encoding="utf-8"))
    header = json.loads(
        (tmp_path / "plain_with_header" / "doc_A.json").read_text(encoding="utf-8")
    )
    assert "source_header" not in plain["provenance"]
    assert header["provenance"]["source_header"] is True
    assert "--with-source-header" in header["provenance"]["command"]
    assert await arm.run_arm(["--skip-existing", "--with-source-header"]) == 0
    assert len(calls) == 2


async def test_panel_dispatch_passes_metadata_to_every_stateful_runner(
    monkeypatch, tmp_path
):
    from argumentation_analysis.core import jvm_setup

    monkeypatch.setattr(jvm_setup, "initialize_jvm", lambda: None)
    seen = {}

    def make_runner(name):
        async def runner(text, corpus_id, **kwargs):
            seen[name] = (text, corpus_id, kwargs)
            return harness.ModeResult(mode=name, corpus_id=corpus_id, success=True)

        return runner

    modes = sorted(harness.PANEL_STATEFUL_MODES)
    for mode in modes:
        monkeypatch.setitem(harness.MODE_RUNNERS, mode, make_runner(mode))
    metadata = {"genre": "synthetic", "author": "synthetic-author"}
    await harness.run_all(
        modes=modes,
        corpora=["doc_A"],
        document_texts={"doc_A": "synthetic text"},
        document_metadata={"doc_A": metadata},
        panel_out_dir=tmp_path,
        panel_judge_model="synthetic-model",
    )
    assert set(seen) == set(modes)
    for text, corpus_id, kwargs in seen.values():
        assert text == "synthetic text"
        assert corpus_id == "doc_A"
        assert kwargs["source_metadata"] == {
            **metadata,
            "opaque_id": "doc_A",
            "source_id": "doc_A",
        }
