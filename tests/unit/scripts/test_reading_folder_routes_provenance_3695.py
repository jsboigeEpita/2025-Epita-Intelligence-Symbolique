"""#3695 — the fiche routes a record's provenance the way the judge reads it.

The judged text is documented as the fiche's full-text section: one producer,
two callers (#3375 tranche 3). The judge's entry point routes a record by
``provenance.mode`` to the engine that produced it (#3470, #3472). The fiche
called the pipeline's producer directly, so on a ``conversation_real`` or a
``hierarchical_delegation`` record the reader met the pipeline's four absence
lines — and the pipeline's facts, read as zeros — where the judge had read the
engine's own findings.

The guards run the reader's own path (the folder's ``main`` on a planted
campaign, then the fiche on disk) as well as the two callers. Every record
here is invented; no corpus text, no model call.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.dataset import judge_panel  # noqa: E402
from scripts.dataset import render_campaign_reading_folder as folder  # noqa: E402

#: The heading every harvested pipeline fiche carries, and the one that ends
#: the section.
PIPELINE_HEADING = "## Le pipeline, en texte intégral"
END_HEADING = "## La réponse zero-shot, intégrale"
FACTS_HEADING = "## Faits mesurés (lus dans l'état de la campagne)"

#: The two other engines, the heading their fiche carries (the producer's own
#: first words: « Le moteur conversationnel … », « La chaîne de délégation … »).
ENGINE_HEADINGS: Dict[str, str] = {
    "conversation_real": "## Le moteur conversationnel, en texte intégral",
    "hierarchical_delegation": "## La chaîne de délégation, en texte intégral",
}

#: What the pipeline's producer prints for an act no state carries — the text
#: an engine's fiche used to show in place of the engine's findings.
ABSENCE_LINE = "absent de l'état — acte i — cadrage non produit"

PIPELINE_ID = "corpus_fix_pipeline"

#: A pipeline state as a campaign dump carries it (acts branch).
PIPELINE_STATE: Dict[str, Any] = {
    "raw_text": "Texte synthétique inventé pour la garde, sans corpus.",
    "identified_arguments": {"arg_1": "un argument inventé"},
    "identified_fallacies": {"soph_1": "un sophisme inventé"},
    "fol_analysis_results": [],
    "propositional_analysis_results": [],
    "modal_analysis_results": [],
    "act1_framing": "Acte I inventé : le cadre.",
    "act2_narrative": "Acte II inventé : le récit.",
    "act3_conclusion": "Acte III inventé : la conclusion.",
    "narrative_synthesis": "Synthèse narrative inventée.",
    "interpretive_question": "Question interprétative inventée ?",
    "reading_window_status": None,
    "restitution_acts_degraded": None,
}

#: The two other engines, as their adapters normalise a record (#3470, #3472):
#: no act, no ``raw_text``, no pipeline collection.
ENGINE_STATES: Dict[str, Dict[str, Any]] = {
    "conversation_real": {
        "fallacies": [
            {"type": "appel à l'autorité", "justification": "inventée pour la garde"}
        ],
        "fallacies_count": 1,
        "fol": {"formulas": ["une formule inventée"], "consistency": True},
        "analysis_errors": ["un incident inventé"],
    },
    "hierarchical_delegation": {
        "objectives": [{"id": "obj_1", "description": "un objectif inventé"}],
        "tasks": [
            {
                "task_id": "t1",
                "capability": "inventée",
                "status": "done",
                "outputs": {"un_champ": "un produit inventé"},
            }
        ],
        "task_counts": {"planned": 2, "productive": 1, "failed": 0, "degraded": 0},
        "conclusion": "une conclusion inventée",
        "degraded": True,
        "degradation_reasons": ["un manque inventé"],
        "partial": False,
    },
}

#: One document per arm, ids in reading order.
DOCS: Dict[str, Optional[str]] = {
    "corpus_fix_conversation": "conversation_real",
    "corpus_fix_delegation": "hierarchical_delegation",
    PIPELINE_ID: None,
}


def _state(doc_id: str) -> Dict[str, Any]:
    mode = DOCS[doc_id]
    return dict(ENGINE_STATES[mode] if mode else PIPELINE_STATE)


def _signature(doc_id: str) -> Dict[str, Any]:
    """The signature a campaign writes, reduced to what the render reads."""
    mode = DOCS[doc_id]
    signature: Dict[str, Any] = {
        "opaque_id": doc_id,
        "document_classification": None,
        "outcome": {"status": "ok"},
    }
    if mode:
        signature["provenance"] = {"mode": mode}
    return signature


def _engine_id(mode: str) -> str:
    return next(doc for doc, engine in DOCS.items() if engine == mode)


# ---------------------------------------------------------------------------
# The reader's path: the folder's main, then the fiche on disk
# ---------------------------------------------------------------------------


def _plant_campaign(tmp_path: Path) -> None:
    """A three-record campaign under tmp_path, one per arm."""
    folders = {name: tmp_path / name for name in ("signatures", "states", "zeroshot")}
    folders["results"] = tmp_path / "results"
    for path in folders.values():
        path.mkdir(parents=True)
    for doc_id, mode in DOCS.items():
        signature = {
            **_signature(doc_id),
            "metadata": {"title": "Titre inventé", "speaker": "Orateur inventé"},
            "workflow": mode or "spectacular",
            "wall_clock_s": 12.5,
            # 2000 prompt + 1000 completion tokens on the haiku standard row.
            "llm_usage": {
                "act1_framing": {
                    "prompt_tokens": 2000,
                    "completion_tokens": 1000,
                    "calls": 1,
                }
            },
        }
        (folders["signatures"] / f"signature_{doc_id}.json").write_text(
            json.dumps(signature, ensure_ascii=False), encoding="utf-8"
        )
        (folders["states"] / f"state_full_{doc_id}.json").write_text(
            json.dumps(_state(doc_id), ensure_ascii=False), encoding="utf-8"
        )
        zeroshot = {
            "provenance": {"model": "claude-haiku-5-5", "git_head": "synthetic-3695"},
            "opaque_id": doc_id,
            "answer": "Réponse zero-shot inventée.",
            "elapsed_seconds": 1.0,
        }
        (folders["zeroshot"] / f"{doc_id}.json").write_text(
            json.dumps(zeroshot, ensure_ascii=False), encoding="utf-8"
        )


def _run_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """The folder's own ``main`` on the planted campaign; returns ``02_rendus``."""
    _plant_campaign(tmp_path)
    out = tmp_path / "results" / "lecture"
    monkeypatch.setattr(folder, "RESULTS_ROOT", tmp_path / "results")
    rc = folder.main(
        [
            "--signatures-dir",
            str(tmp_path / "signatures"),
            "--states-dir",
            str(tmp_path / "states"),
            "--zeroshot-dir",
            str(tmp_path / "zeroshot"),
            "--out",
            str(out),
        ]
    )
    assert rc == 0
    return out / "02_rendus"


def _fiche_on_disk(renders: Path, doc_id: str) -> str:
    matches = [path for path in renders.glob("*.md") if f"_{doc_id}_" in path.name]
    assert len(matches) == 1, [path.name for path in matches]
    return matches[0].read_text(encoding="utf-8")


def _render(doc_id: str, provenance: Optional[Dict[str, Any]] = None) -> str:
    """``render_fiche`` on a document of the campaign, as the folder's main calls it."""
    state = _state(doc_id)
    signature = {**_signature(doc_id), "metadata": {}}
    if provenance is not None:
        signature["provenance"] = provenance
    facts = folder.doc_facts(signature, dict(state))
    return folder.render_fiche(facts, state, None, "abc1234", "witness", "cmd")


def _section(fiche: str, heading: str) -> Optional[str]:
    """The text between a heading and the zero-shot's; ``None`` when absent."""
    start = fiche.find(heading + "\n\n")
    if start < 0:
        return None
    body = fiche[start + len(heading) + 2 :]
    end = body.find("\n" + END_HEADING)
    return None if end < 0 else body[:end]


def _facts_block(fiche: str) -> str:
    after = fiche.split(FACTS_HEADING + "\n\n", 1)[1]
    return after.split("\n## ", 1)[0]


class TestTheFolderReadsEachRecordInItsOwnVoice:
    def test_an_engine_record_is_rendered_in_its_own_voice(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Born red: the fiche used to print the pipeline's absence lines."""
        renders = _run_folder(tmp_path, monkeypatch)

        for mode, heading in ENGINE_HEADINGS.items():
            doc_id = _engine_id(mode)
            judged = judge_panel.pipeline_text_from_state(
                _state(doc_id), _signature(doc_id)
            )
            fiche = _fiche_on_disk(renders, doc_id)

            assert _section(fiche, heading) == judged
            assert ABSENCE_LINE not in fiche
            assert PIPELINE_HEADING not in fiche

    def test_the_pipeline_record_of_the_same_folder_keeps_its_text(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regression guard (green before the fix): the pipeline's fiche does not move."""
        renders = _run_folder(tmp_path, monkeypatch)
        fiche = _fiche_on_disk(renders, PIPELINE_ID)
        facts = folder.doc_facts(_signature(PIPELINE_ID), dict(PIPELINE_STATE))
        direct = folder.pipeline_full_text(
            dict(PIPELINE_STATE),
            facts["classification"],
            PIPELINE_ID,
            facts["outcome"],
            chars=facts["chars"],
        )

        assert _section(fiche, PIPELINE_HEADING) == direct
        for heading in ENGINE_HEADINGS.values():
            assert heading not in fiche


class TestOneRoutingTwoCallers:
    def test_both_callers_go_through_one_routing_function(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The judge's entry point and the fiche call the same function (#3695)."""
        seen: List[Tuple[Optional[str], Optional[int]]] = []

        def routing(state: Any, signature: Any, chars: Optional[int] = None) -> str:
            seen.append((signature.get("opaque_id"), chars))
            return "TEXTE DU ROUTAGE"

        monkeypatch.setattr(folder, "arm_text_from_state", routing)
        state = dict(PIPELINE_STATE)

        judged = judge_panel.pipeline_text_from_state(state, _signature(PIPELINE_ID))
        fiche = _render(PIPELINE_ID)

        assert judged == "TEXTE DU ROUTAGE"
        assert _section(fiche, PIPELINE_HEADING) == "TEXTE DU ROUTAGE"
        assert [row[0] for row in seen] == [PIPELINE_ID, PIPELINE_ID]
        # The fiche hands the length it already measured; the judge does not.
        assert seen[0][1] is None
        assert seen[1][1] == len(PIPELINE_STATE["raw_text"])

    @pytest.mark.parametrize("mode", sorted(ENGINE_HEADINGS))
    def test_an_engine_signature_reads_its_own_producer(self, mode: str) -> None:
        state = dict(ENGINE_STATES[mode])
        signature = {"outcome": {"status": "ok"}, "provenance": {"mode": mode}}
        producer = (
            folder.conversation_real_full_text
            if mode == "conversation_real"
            else folder.hierarchical_delegation_full_text
        )

        assert folder.arm_text_from_state(state, signature) == producer(
            state, {"status": "ok"}
        )

    @pytest.mark.parametrize(
        "provenance",
        [
            None,
            {},
            {"mode": "pipeline"},
            {"mode": "an_engine_no_producer_knows"},
            {"engine": "conversation_real"},
        ],
    )
    def test_every_other_signature_reads_the_pipeline_producer(
        self, provenance: Optional[Dict[str, Any]]
    ) -> None:
        """The judge's rule, unchanged: anything but the two known modes is the pipeline."""
        signature: Dict[str, Any] = {"outcome": {"status": "ok"}}
        if provenance is not None:
            signature["provenance"] = provenance

        routed = folder.arm_text_from_state(dict(PIPELINE_STATE), signature)

        assert routed == folder.pipeline_full_text(
            dict(PIPELINE_STATE), None, "", {"status": "ok"}
        )

    @pytest.mark.parametrize("mode", sorted(ENGINE_HEADINGS))
    def test_an_engine_mode_wins_over_a_pipeline_classification(
        self, mode: str
    ) -> None:
        """The judge's precedence, unchanged: the mode is read before the classification."""
        state = dict(ENGINE_STATES[mode])
        signature = {
            "document_classification": "non_argumentative",
            "provenance": {"mode": mode},
        }

        routed = folder.arm_text_from_state(state, signature)

        assert "Classification terminale" not in routed
        assert routed == folder.arm_text_from_state(
            state, {"provenance": {"mode": mode}}
        )

    @pytest.mark.parametrize("mode", sorted(ENGINE_HEADINGS))
    def test_the_state_is_unwrapped_once_whatever_the_record_s_shape(
        self, mode: str
    ) -> None:
        """A harvested record nests its state; a caller may hand it flat."""
        state = dict(ENGINE_STATES[mode])
        signature = {"provenance": {"mode": mode}, "outcome": {"status": "partial"}}
        producer = (
            folder.conversation_real_full_text
            if mode == "conversation_real"
            else folder.hierarchical_delegation_full_text
        )
        expected = producer(state, {"status": "partial"})

        assert folder.arm_text_from_state({"state": dict(state)}, signature) == expected
        assert folder.arm_text_from_state(dict(state), signature) == expected

    def test_the_pipeline_branch_keeps_the_length_the_caller_measured(self) -> None:
        """``chars`` is the caller's own measure: given, it is used, not re-read."""
        state = {
            "raw_text": "x" * 300,
            "source_metadata": {
                "event": "une décision inventée",
                "participants": ["un rapport inventé"],
                "report_title": "",
            },
            "interpretive_question": "Question inventée ?",
        }
        signature = {
            "document_classification": "non_argumentative",
            "outcome": {},
        }

        measured = folder.arm_text_from_state(state, signature, chars=999)

        assert measured == folder.pipeline_full_text(
            state, "non_argumentative", "", {}, chars=999
        )
        assert measured != folder.arm_text_from_state(state, signature)


class TestTheFicheIsCoherentOnAnEngineRecord:
    @pytest.mark.parametrize("mode", sorted(ENGINE_HEADINGS))
    def test_the_section_is_named_after_what_it_holds(self, mode: str) -> None:
        """A section titled « Le pipeline » must not hold an engine's text."""
        fiche = _render(_engine_id(mode))

        assert ENGINE_HEADINGS[mode] + "\n\n" in fiche
        assert PIPELINE_HEADING not in fiche

    def test_the_pipeline_heading_is_unchanged(self) -> None:
        """Regression guard: the heading every harvested fiche carries."""
        assert PIPELINE_HEADING + "\n\n" in _render(PIPELINE_ID)

    @pytest.mark.parametrize("mode", sorted(ENGINE_HEADINGS))
    def test_an_engine_fiche_does_not_print_the_pipeline_s_facts(
        self, mode: str
    ) -> None:
        """Born red: an engine's state holds none of the pipeline's collections, and
        reading them printed « 0 » above a text that lists its findings."""
        block = _facts_block(_render(_engine_id(mode)))
        bullets = [line for line in block.splitlines() if line.startswith("- ")]

        # The pipeline's three lines are not read off an engine's record.
        for line_start in (
            "- Longueur du document",
            "- Verdicts formels",
            "- Fenêtre de lecture",
        ):
            assert line_start not in block
        # What replaces them, and the run's own line, naming its engine.
        assert len(bullets) == 2
        assert bullets[0].startswith(f"- Moteur `{mode}` : ")
        assert "ils ne sont pas affichés" in bullets[0]
        assert bullets[1].startswith("- Durée : ")
        assert "appels LLM" in bullets[1]
        assert f"coût recalculé : moteur `{mode}` **" in bullets[1]
        assert "coût recalculé : pipeline" not in bullets[1]

    def test_the_pipeline_fiche_keeps_its_facts(self) -> None:
        """Regression guard (green before the fix)."""
        block = _facts_block(_render(PIPELINE_ID))

        for fact in (
            "Longueur du document",
            "arguments extraits",
            "Verdicts formels",
            "Fenêtre de lecture",
            "appels LLM",
        ):
            assert fact in block
        assert "ne sont pas affichés" not in block


class TestTheFactsCarryTheProvenance:
    def test_the_facts_carry_the_signature_s_provenance(self) -> None:
        engine = folder.doc_facts(
            _signature(_engine_id("conversation_real")), {"fallacies": []}
        )
        pipeline = folder.doc_facts(_signature(PIPELINE_ID), dict(PIPELINE_STATE))

        assert engine["provenance"] == {"mode": "conversation_real"}
        assert pipeline["provenance"] == {}

    def test_facts_built_by_hand_stay_on_the_pipeline(self) -> None:
        """Regression guard: callers that build ``facts`` without the new key."""
        facts = folder.doc_facts(_signature(PIPELINE_ID), dict(PIPELINE_STATE))
        del facts["provenance"]

        fiche = folder.render_fiche(facts, dict(PIPELINE_STATE), None, "a", "m", "c")

        assert _section(fiche, PIPELINE_HEADING) == folder.pipeline_full_text(
            dict(PIPELINE_STATE), None, PIPELINE_ID, {}, chars=facts["chars"]
        )
        assert "ne sont pas affichés" not in fiche
