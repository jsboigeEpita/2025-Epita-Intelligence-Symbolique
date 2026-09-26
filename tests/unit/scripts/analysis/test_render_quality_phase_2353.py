"""#2353 — the quality-phase render has a tracked producer.

Offline guards of ``scripts/analysis/render_quality_phase.py``. The real
render needs the encrypted corpus and an LLM route, so it is not run here;
what is pinned is everything a second seat relies on to compare two renders:

1. the provenance header carries every key (route and model included — two
   renders are comparable only through it);
2. a wired arm that did not run wired is flagged at the top of the render,
   never left for the reader to infer from a table;
3. a virtue scored on every unit and non-zero on none is named
   ``uniformly_null`` (the property #2353 asks to find again);
4. the lexical arm reaches the REAL phase, resolved through the production
   registry, as the phase's own named degraded path — and the factory is
   restored afterwards;
5. the producer refuses an output path git would track (positive control: the
   default results directory is accepted);
6. the header names the spaCy stack the lexical detectors run on, and names
   its absence rather than dropping the key (#2675).
"""

from importlib import metadata
from pathlib import Path
from typing import Any, Dict

import pytest

from scripts.analysis import render_quality_phase as rqp

_PROVENANCE: Dict[str, Any] = {
    "producer": rqp.PRODUCER,
    "command": "python scripts/analysis/render_quality_phase.py --doc B",
    "head": "0" * 40,
    "tree_dirty": False,
    "date_utc": "2026-09-23T00:00:00Z",
    "corpus_label": "doc_B",
    "source_index": 3,
    "route": "openrouter",
    "model_resolved": "openai/gpt-5.6-luna",
    "sdk_versions": {"openai": "x", "semantic_kernel": "y", "httpx": "z"},
}

_EXTRACTION = {
    "status": "ok",
    "argument_count": 2,
    "llm_requests": 1,
    "wall_seconds": 1.0,
    "unit_texts": {"arg_1": "Unité synthétique un.", "arg_2": "Unité deux."},
}


def _unit(note: float, structure: float) -> Dict[str, Any]:
    return {
        "note_finale": note,
        "note_max_applicable": 5.0,
        "scores_par_vertu": {"clarte": 1.0, "structure_logique": structure},
        "statuts_par_vertu": {"clarte": "evaluee", "structure_logique": "evaluee"},
        "rapport_detaille": {"structure_logique": "exhibit localisé"},
    }


def _arm(mode: str, units: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "output": {
            "per_argument_scores": units,
            "agentic_wiring": {
                "mode": mode,
                "model": "openai/gpt-5.6-luna",
                "units_evaluated": len(units),
                "units_degraded": {},
            },
        },
        "llm_requests": 3,
        "wall_seconds": 2.0,
    }


def _arms(wired_mode: str = "wired") -> Dict[str, Any]:
    return {
        "wired": _arm(wired_mode, {"arg_1": _unit(4.5, 1.0), "arg_2": _unit(1.0, 0.0)}),
        "lexical": _arm(
            "degraded_forced_lexical",
            {"arg_1": _unit(1.0, 0.0), "arg_2": _unit(1.0, 0.0)},
        ),
    }


def test_the_render_opens_with_every_provenance_key():
    markdown = rqp.render_markdown(_PROVENANCE, _EXTRACTION, _arms())
    header = markdown.split("## Discrimination")[0]

    for key in rqp._HEADER_KEYS:
        assert f"**{key}**: `{_PROVENANCE[key]}`" in header, key
    assert "**sdk_versions**" in header
    assert "arm `wired`**: mode `wired`" in header
    assert "arm `lexical`**: mode `degraded_forced_lexical`" in header


def test_a_wired_arm_that_did_not_run_wired_is_flagged_at_the_top():
    flagged = rqp.render_markdown(
        _PROVENANCE, _EXTRACTION, _arms(wired_mode="degraded_no_route")
    )
    first_block = flagged.split("## Provenance")[0]
    assert "did not run wired" in first_block
    assert "degraded_no_route" in first_block

    # Witness: a wired run carries no such line anywhere.
    assert "did not run wired" not in rqp.render_markdown(
        _PROVENANCE, _EXTRACTION, _arms()
    )


def test_a_uniformly_null_virtue_is_named_not_averaged():
    summary = rqp.discrimination_summary(
        {arm: data["output"] for arm, data in _arms().items()}
    )

    lexical, wired = summary["lexical"], summary["wired"]
    assert lexical["virtues"]["structure_logique"]["uniformly_null"] is True
    assert wired["virtues"]["structure_logique"]["uniformly_null"] is False
    assert wired["virtues"]["structure_logique"]["non_zero"] == 1
    # Units become discernible on the wired arm only.
    assert lexical["distinct_notes"] == 1
    assert (wired["note_min"], wired["note_max"], wired["distinct_notes"]) == (
        1.0,
        4.5,
        2,
    )


class _SpyEvaluator:
    """Records the wiring the phase constructs its evaluator with."""

    constructed_with: Any = "__never__"

    def __init__(self, detectors: Any = None, agentic_llm: Any = None) -> None:
        _SpyEvaluator.constructed_with = agentic_llm

    def evaluate(self, text: str, **_: Any) -> Dict[str, Any]:
        return _unit(1.0, 0.0)


async def test_the_lexical_arm_is_the_phase_named_degraded_path(monkeypatch):
    import argumentation_analysis.orchestration.invoke_callables as ic
    from argumentation_analysis.agents.core.quality import quality_evaluator
    from argumentation_analysis.orchestration.registry_setup import setup_registry

    monkeypatch.setattr(quality_evaluator, "ArgumentQualityEvaluator", _SpyEvaluator)
    # The enrichment pass must not reach the network (#1583).
    monkeypatch.setattr(ic, "_get_openai_client", lambda: (None, ""))
    factory = ic._make_agentic_llm_callable
    invoke = rqp.resolve_phase_invoke(
        setup_registry(include_optional=False), "argument_quality"
    )
    context = {
        "phase_extract_output": {
            "arguments": [{"text": "Une unité synthétique suffisamment longue."}]
        }
    }

    with rqp.forced_lexical():
        output = await invoke("texte", context)

    assert _SpyEvaluator.constructed_with is None
    assert output["agentic_wiring"]["mode"] == "degraded_forced_lexical"
    assert ic._make_agentic_llm_callable is factory, "factory not restored"


def test_the_producer_refuses_an_output_path_git_would_track():
    with pytest.raises(rqp.RenderRefused, match="not gitignored"):
        rqp.ensure_gitignored(Path(rqp.REPO_ROOT) / "scripts/analysis/render.md")

    # Positive control: the default results directory is accepted.
    rqp.ensure_gitignored(rqp.RESULTS_DIR / "render.md")


def _na_unit(note: float, note_max: float) -> Dict[str, Any]:
    """A unit too short for the structural virtues, in the evaluator's REAL
    shape: an n/a virtue has NO key in ``scores_par_vertu`` (measured on the
    #2353 render: 2 score keys, 9 status keys) — only its status says so."""
    return {
        "note_finale": note,
        "note_max_applicable": note_max,
        "scores_par_vertu": {"clarte": 1.0},
        "statuts_par_vertu": {
            "clarte": "evaluated",
            "structure_logique": "not_applicable",
        },
        "rapport_detaille": {},
    }


def test_absence_is_counted_not_folded_into_the_nulls():
    """Measured on the first real render (#2353): 6 of 7 units were n/a.

    ``uniformly_null`` then rested on ONE unit while the stdout line read as
    a verdict on the virtue. The summary counts absence separately, and the
    note ratio divides by the applicable maximum.
    """
    unit_evaluated = _unit(2.5, 0.0)
    unit_evaluated["note_max_applicable"] = 5.0
    output = {
        "per_argument_scores": {
            "arg_1": unit_evaluated,
            "arg_2": _na_unit(2.0, 2.0),
            "arg_3": _na_unit(2.0, 2.0),
        }
    }
    summary = rqp.discrimination_summary({"wired": output})["wired"]
    structure = summary["virtues"]["structure_logique"]

    assert structure == {
        "scored": 1,
        "non_zero": 0,
        "not_applicable": 2,
        "unavailable": 0,
        "uniformly_null": True,
    }
    # Raw notes say 2.0..2.5; per applicable maximum the evaluated unit is
    # the LOWEST (0.5 against 1.0).
    assert (summary["ratio_min"], summary["ratio_max"]) == (0.5, 1.0)

    markdown = rqp.render_markdown(
        _PROVENANCE, _EXTRACTION, {"wired": {"output": output, "llm_requests": 1}}
    )
    assert "0/1 > 0 **null** · 2 n/a" in markdown


def test_unit_shape_records_word_counts_never_the_text():
    """What the phase judges is ``text``; its length decides applicability."""
    shape = rqp.unit_shape(
        [
            {"text": "trois mots ici", "source_quote": ""},
            {"text": "un", "source_quote": "deux mots"},
            "une chaîne nue",
        ]
    )
    assert shape == {
        "arg_1": {"text_words": 3, "source_quote_words": 0},
        "arg_2": {"text_words": 1, "source_quote_words": 2},
        "arg_3": {"text_words": 3, "source_quote_words": 0},
    }
    assert "trois" not in repr(shape)


def test_the_header_names_the_spacy_stack_the_lexical_arm_runs_on():
    """#2675: two seats with different spaCy stacks score the lexical arm
    differently; the header is what lets a reader of two renders see it."""
    versions = rqp.collect_provenance("doc_B", 0, "cmd")["sdk_versions"]
    assert versions["spacy"] == metadata.version("spacy")
    assert versions["fr_core_news_sm"] == metadata.version("fr_core_news_sm")


def test_an_absent_model_is_named_in_the_header_not_dropped(monkeypatch):
    installed = metadata.version

    def _version(dist):
        if dist == "fr_core_news_sm":
            raise metadata.PackageNotFoundError(dist)
        return installed(dist)

    monkeypatch.setattr(metadata, "version", _version)
    versions = rqp.collect_provenance("doc_B", 0, "cmd")["sdk_versions"]
    assert versions["fr_core_news_sm"].startswith("unavailable ("), versions
