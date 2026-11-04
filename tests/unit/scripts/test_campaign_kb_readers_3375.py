"""#3375 — the judge reads what the campaign wrote, under the id it recorded.

Two defects stopped the blind judge on the real cycle-0 run, before any call:

1. ``judge_panel.py`` defaulted to ``.analysis_kb/state_dumps``. The campaign
   (``run_corpus_batch.DEFAULT_KB``) writes ``analysis_kb/``; the dotted folder
   is an older one with no state dump and no signature. The judge therefore
   found no arm at all.
2. ``model_family`` read the bare prefix of the id, so the id the pipeline
   arm records through OpenRouter (``openai/gpt-5.6-luna``) had no family and
   the judge refused to run. The price table already reads that id through
   ``bare_model_id``; the family now reads the same key.

The census below keeps the first class shut: every string constant under
``scripts/dataset/`` that names the campaign's output root must name the
producer's own root, which is read from the producer's source (an AST read,
not an import: importing the batch runner initialises the crypto service).
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from argumentation_analysis.evaluation.model_family import (
    UnknownModelFamily,
    assert_judge_differs,
    model_family,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
DATASET_SCRIPTS = REPO_ROOT / "scripts" / "dataset"
PRODUCER = DATASET_SCRIPTS / "run_corpus_batch.py"

# A path component spelled like the campaign's root, dotted or not.
_KB_COMPONENT = re.compile(r"(?<![\w.])(\.?analysis_kb)(?=[/\\\s\]\"']|$)")


def _producer_root_name() -> str:
    """The folder name ``run_corpus_batch.DEFAULT_KB`` joins onto the root."""
    tree = ast.parse(PRODUCER.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "DEFAULT_KB" for t in node.targets
            )
            and isinstance(node.value, ast.BinOp)
            and isinstance(node.value.right, ast.Constant)
        ):
            return node.value.right.value
    raise AssertionError(
        "run_corpus_batch.py no longer assigns DEFAULT_KB = ROOT / '<name>'"
    )


def _kb_mentions():
    """(file, line, spelling) for every KB-root component in a string constant."""
    found = []
    for path in sorted(DATASET_SCRIPTS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for match in _KB_COMPONENT.finditer(node.value):
                    found.append((path.name, node.lineno, match.group(1)))
    return found


class TestTheJudgeReadsTheCampaignsFolders:
    def test_the_producer_root_is_read_from_its_source(self):
        assert _producer_root_name() == "analysis_kb"

    def test_the_census_sees_the_known_readers(self):
        # Positive control: a census that finds nothing proves nothing.
        files = {name for name, _, _ in _kb_mentions()}
        assert {
            "run_corpus_batch.py",
            "render_campaign_reading_folder.py",
            "rederive_surplus_aggregate.py",
            "build_pattern_report.py",
        } <= files

    def test_every_reader_names_the_producers_root(self):
        root = _producer_root_name()
        wrong = [m for m in _kb_mentions() if m[2] != root]
        assert not wrong, (
            f"these constants name a folder the campaign does not write "
            f"(the producer writes {root!r}): {wrong}"
        )

    def test_the_census_would_catch_the_dotted_folder(self):
        assert (
            _KB_COMPONENT.search(".analysis_kb/signatures").group(1) == ".analysis_kb"
        )
        assert _KB_COMPONENT.search('REPO / ".analysis_kb"') is not None

    def test_the_judge_defaults_are_the_fiche_folders(self):
        import scripts.dataset.judge_panel as jp
        import scripts.dataset.render_campaign_reading_folder as fiche

        assert jp.DEFAULT_STATES_DIR == fiche.STATES_DIR
        assert jp.DEFAULT_SIGNATURES_DIR == fiche.SIGNATURES_DIR
        assert jp.DEFAULT_ZEROSHOT_DIR == fiche.ZEROSHOT_DIR
        assert jp.DEFAULT_STATES_DIR.parent.name == _producer_root_name()


class TestARoutedIdHasAFamily:
    def test_the_openrouter_id_of_the_pipeline_arm(self):
        assert model_family("openai/gpt-5.6-luna") == "openai"

    def test_a_routed_anthropic_id(self):
        assert model_family("anthropic/claude-sonnet-5-5") == "anthropic"

    def test_the_bare_id_is_unchanged(self):
        assert model_family("gpt-5.6-luna") == "openai"

    def test_the_cycle0_pairing_is_another_family(self):
        assert assert_judge_differs("claude-sonnet-5-5", "openai/gpt-5.6-luna") == (
            "anthropic",
            "openai",
        )

    def test_a_routed_same_family_judge_is_still_refused(self):
        with pytest.raises(ValueError):
            assert_judge_differs("openai/gpt-5.6-luna", "gpt-5.6-luna")

    def test_a_router_alias_without_a_model_still_raises(self):
        with pytest.raises(UnknownModelFamily):
            model_family("openrouter/auto")

    def test_a_vendor_with_no_model_is_empty_and_raises(self):
        with pytest.raises(UnknownModelFamily):
            model_family("openai/")
