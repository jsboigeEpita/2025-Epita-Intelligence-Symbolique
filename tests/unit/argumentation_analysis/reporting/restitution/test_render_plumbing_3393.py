"""#3393 — render plumbing: nine deterministic defects, nine witnesses.

The first 10-document panel (#2841, #3375) rendered 9 analysed fiches, and
the audit measured the same classes on 9 of 9 renders: a section printed
twice, internal keys on the reader surface, a window read as a reading,
spans that disagree with each other, artifact anchors dumped raw, an
unexplained Greek letter, internal workflow names, and a stamp that names
a probe as the route. Every item is a producer mis-wiring, not a writer
habit — so every fix is a producer fix, no prompt rule added, and every
witness below is offline (no JVM, no network; LLM stubs return recorded
synthetic prose).

Born red on ``origin/main`` where the defect is reachable from a fixture;
a control render with none of these defects stays byte-identical.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[5]))

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.evaluation.env_manifest import render_environment_stamp
from argumentation_analysis.orchestration.invoke_callables import (
    _record_per_argument_reading,
)
from argumentation_analysis.orchestration.selection import (
    SelectableUnit,
    select_for_budget,
)
from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    COVERAGE_HEADING,
    build_act1_framing,
    refresh_coverage_passage,
)
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_narrative,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_conclusion,
)
from argumentation_analysis.reporting.restitution.reading_record import (
    build_reading_record,
    format_reader_bounds_passage,
)


def _stub_llm(text: str):
    async def _call(_prompt: str) -> str:
        return text

    return _call


# ============================================================================
# Item 1 — the bounds passage is printed ONCE, by Act III (#3134, #3374)
# ============================================================================


def _bounds_state() -> UnifiedAnalysisState:
    state = UnifiedAnalysisState("x" * 12_000)
    state.add_argument("Le locuteur disqualifie l'adversaire.")
    state.reading_window_status = {
        "fact_extraction": {"status": "selected", "offset": 0, "window": 3000},
        "fallacy_widenet": {"status": "selected", "offset": 0, "window": 8000},
    }
    return state


_WOVEN_2 = (
    "### Ce que le discours dit vraiment\n\n"
    "Le locuteur défend une lecture ordonnée de ses engagements.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    "La position résiste à l'examen croisé des axes.\n\n"
    "### Comment se faire son avis\n\n"
    "Les bornes de lecture sont portées par le passage qui suit ce récit."
)

_WOVEN_3 = (
    "### Ce que le discours dit vraiment\n\n"
    "Le locuteur défend une lecture ordonnée de ses engagements.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    "La position résiste à l'examen croisé des axes.\n\n"
    "### Comment se faire son avis\n\n"
    "L'analyse localise un dérapage ; la caractérisation reste assurée."
)


class TestBoundsPrintedOnce:
    def test_the_whole_report_carries_one_bounds_passage(self):
        """On main both acts graft the same passage — the reader read the
        run's bounds twice, word for word, on 9 of 9 renders."""
        state = _bounds_state()
        act2 = asyncio.run(
            build_act2_narrative(state, llm_callable=_stub_llm(_WOVEN_2))
        )
        act3 = asyncio.run(
            build_act3_conclusion(state, llm_callable=_stub_llm(_WOVEN_3))
        )
        combined = act2.narrative + "\n\n" + act3.narrative
        assert combined.count("**Bornes de lecture du run**") == 1, (
            "the reading bounds are printed "
            f"{combined.count('**Bornes de lecture du run**')} times across "
            "the acts — a reserve is said once"
        )
        # The one print closes the report, where #3134's §4 gate reads it.
        assert "**Bornes de lecture du run**" not in act2.narrative
        assert "**Bornes de lecture du run**" in act3.narrative


# ============================================================================
# Item 2 — the coverage section is said once, at its first position
# ============================================================================


def _act1_state(**fields) -> SimpleNamespace:
    base = dict(
        act1_framing="",
        act2_narrative="",
        act3_conclusion="",
        source_metadata={"genre": "discours politique"},
        stakes_and_stakeholders={
            "stakes": [{"stake_type": "décision", "description": f"point {i}"}]
            for i in range(6)
        },
        stakeholders=[],
        identified_arguments={"arg_a": "thèse"},
        identified_fallacies={},
        analysis_coverage={"nl_to_logic": {"k": 3, "N": 90}},
        reading_window_status=None,
        raw_text="x" * 1000,
    )
    base.update(fields)
    return SimpleNamespace(**base)


_DOUBLED_NARRATIVE = (
    "### Le texte\n\n"
    "Le propos vient d'un locuteur en autorité devant une assemblée.\n\n"
    f"**{COVERAGE_HEADING}**\n"
    "Couverture : phrase de couverture périmée, recopiée par le rédacteur.\n\n"
    "### Les enjeux\n\n"
    "Ce qui se joue est l'adhésion d'une audience hésitante.\n\n"
    f"**{COVERAGE_HEADING}**\n"
    "Couverture : de 6 à 10 unités selon les mod\n\n"
    "### Comment se faire son avis\n\n"
    "Prudence sur les conclusions.\n\n"
    "QUESTION INTERPRÉTATIVE : Ce propos gagne-t-il l'adhésion par l'autorité ?"
)

_SINGLE_NARRATIVE = (
    "### Le texte\n\n"
    "Le propos vient d'un locuteur en autorité devant une assemblée.\n\n"
    f"**{COVERAGE_HEADING}**\n"
    "Couverture : phrase de couverture périmée, recopiée par le rédacteur.\n\n"
    "### Comment se faire son avis\n\n"
    "Prudence sur les conclusions.\n\n"
    "QUESTION INTERPRÉTATIVE : Ce propos gagne-t-il l'adhésion par l'autorité ?"
)


class TestCoverageSectionSaidOnce:
    def test_a_doubled_section_is_kept_once_at_its_first_position(self):
        """On main the refresh replaced only the FIRST occurrence: the
        writer's truncated copy of the section survived below it."""
        refreshed = refresh_coverage_passage(_DOUBLED_NARRATIVE, _act1_state())
        assert refreshed.count(f"**{COVERAGE_HEADING}**") == 1, (
            "the coverage section appears "
            f"{refreshed.count(f'**{COVERAGE_HEADING}**')} times — one "
            "section, said once"
        )
        # The surviving occurrence is at its FIRST position (the writer's
        # truncated copy below « Les enjeux » is the one that goes).
        assert refreshed.index(COVERAGE_HEADING) < refreshed.index("### Les enjeux")
        # The stale sentence and its truncated twin are both gone — the
        # producer's fresh sentence is the only coverage prose left.
        assert "phrase de couverture périmée" not in refreshed
        assert "selon les mod" not in refreshed
        assert "Couverture :" in refreshed
        assert refreshed.index("Couverture :") < refreshed.index("### Les enjeux")
        # The closing question stays the report's last line.
        last = [ln for ln in refreshed.splitlines() if ln.strip()][-1]
        assert last.startswith("QUESTION INTERPRÉTATIVE")

    def test_a_single_section_render_is_unchanged_by_the_dedup(self):
        """The control: one occurrence in, one occurrence out — the
        first-position replacement semantics a single-section render has
        always had."""
        state = _act1_state()
        refreshed = refresh_coverage_passage(_SINGLE_NARRATIVE, state)
        assert refreshed.count(f"**{COVERAGE_HEADING}**") == 1
        assert "phrase de couverture périmée" not in refreshed
        # Idempotent on its own output.
        assert refresh_coverage_passage(refreshed, state) == refreshed


# ============================================================================
# Item 3 — the coverage parenthesis names modules by reader label
# ============================================================================


_WOVEN_ACT1 = (
    "### Le texte\n\n"
    "Le propos vient d'un locuteur en autorité devant une assemblée.\n\n"
    "### Les enjeux\n\n"
    "Ce qui se joue est l'adhésion d'une audience hésitante.\n\n"
    "QUESTION INTERPRÉTATIVE : Ce propos gagne-t-il l'adhésion par l'autorité ?"
)


class TestCoverageNamesReaderLabels:
    def test_the_prompt_carries_reader_labels_not_state_keys(self):
        """On main the parenthesis printed the state keys (« nl_to_logic :
        6/90 unités », « atms : 4/90 unités ») — internal vocabulary on the
        reader surface, measured on 9 of 9 renders."""
        prompts: list = []

        async def _capture(prompt: str) -> str:
            prompts.append(prompt)
            return _WOVEN_ACT1

        state = _act1_state(
            analysis_coverage={
                "nl_to_logic": {"k": 6, "N": 90},
                "atms": {"k": 4, "N": 90},
            }
        )
        result = asyncio.run(build_act1_framing(state, llm_callable=_capture))
        assert result.status == "woven"
        assert prompts, "the writer was never called"
        prompt = prompts[0]
        assert "traduction en formules logiques : 6/90 unités" in prompt
        assert "maintenance des hypothèses (ATMS) : 4/90 unités" in prompt
        assert "nl_to_logic" not in prompt, "a state key reached the writer"
        # The label table writes « (ATMS) »; a lowercase bare key is the
        # defect's own shape and must be absent.
        assert " atms" not in prompt


# ============================================================================
# Item 4 — an oversized window reads the document, and says its count
# ============================================================================


class TestOversizedWindowReadsTheDocument:
    def test_the_line_names_what_was_read_never_the_request(self):
        """On main a 921-character document under an 8000-character
        window rendered « lecture de 8000 des 921 caractères » — the
        REQUEST printed as a reading."""
        state = UnifiedAnalysisState("x" * 921)
        state.reading_window_status = {
            "fact_extraction": {"status": "selected", "offset": 0, "window": 8000}
        }
        passage = format_reader_bounds_passage(build_reading_record(state))
        assert "document lu en entier (921 caractères)" in passage
        assert "8000" not in passage, (
            "the window is the requested size, not a read size — it does "
            "not belong in the reader's bounds"
        )


# ============================================================================
# Item 5 — every span in the report shares ONE convention
# ============================================================================


class TestSpansShareOneConvention:
    def test_the_selection_span_ends_where_the_last_unit_ends(self):
        """On main the extent's end was the last unit's START: Act I said
        0.00–0.73 next to the bounds' own 0.00–1.00 for the same units."""
        units = [
            SelectableUnit(
                unit_id="a",
                text="Une première unité située au début du texte.",
                offset=0,
            ),
            SelectableUnit(unit_id="b", text="y" * 2500, offset=7500),
        ]
        sel = select_for_budget(units, 2, text_length=10_000)
        # A unit COVERS [offset, offset + len(text)) — the last unit ends
        # at 7500 + 2500 = 10000, i.e. the whole document.
        assert sel.span == (0.0, 1.0)

    def test_the_basis_line_ends_where_the_last_unit_ends(self):
        """On main the basis line took the max START offset for its end
        (0.00–0.75 next to site lines saying 0.00–1.00)."""
        state = UnifiedAnalysisState("x" * 10_000)
        # The passage renders when it has at least one reading line; the
        # basis line rides under it.
        state.reading_window_status = {
            "fact_extraction": {"status": "selected", "offset": 0, "window": 3000}
        }
        state.add_argument(
            "Un début de thèse défendu dès l'ouverture du texte.",
            producer="llm_extract",
            offset=0,
        )
        state.add_argument(
            "La fin " + "y" * 2493,  # len == 2500 : 7500 + 2500 == 10000
            producer="llm_extract",
            offset=7500,
        )
        passage = format_reader_bounds_passage(build_reading_record(state))
        assert "0.00–1.00" in passage, (
            "the basis line must end where the last unit ENDS — the same "
            "convention the site lines use"
        )

    def test_the_per_argument_site_records_document_coordinates(self):
        """On main the site found each needle inside the phase's WINDOW
        and divided by the DOCUMENT length — 0.00–0.03 next to the other
        sites' 0.00–1.00 for the same units."""
        text = "Une thèse située très loin dans le document, ici."
        state = UnifiedAnalysisState("x" * 30_000)
        arg_id = state.add_argument(text, producer="llm_extract", offset=20_000)
        _record_per_argument_reading({"_state_object": state}, [(arg_id, text)])
        entry = state.reading_window_status["fallacy_per_argument"]
        assert entry["span_lo"] == 20_000
        assert entry["span_hi"] == 20_000 + len(text), (
            "the span is computed from the state's recorded offsets, in "
            "document coordinates — never from the phase's window"
        )


# ============================================================================
# Item 6 — an artifact anchor becomes a numbered note (FB-18)
# ============================================================================


class TestAnchorsBecomeNotes:
    def test_the_same_anchor_keeps_its_number_across_acts(self):
        # Lazy: the helpers are this branch's — importing them here keeps
        # the file collectable on main, where the witnesses redden one
        # item at a time instead of dying at collection.
        from scripts.dataset.render_campaign_reading_folder import (
            anchors_to_notes,
            notes_section,
        )

        notes: dict = {}
        once = anchors_to_notes(
            "Prose avec ancre [artifact:fallacy_per_argument.arg_7] dedans.", notes
        )
        twice = anchors_to_notes(
            "Autre acte, même ancre [artifact:fallacy_per_argument.arg_7] ici.",
            notes,
        )
        assert once == "Prose avec ancre [1] dedans."
        assert twice == "Autre acte, même ancre [1] ici."
        section = notes_section(notes)
        assert "### Notes du pipeline (ancres du run)" in section
        assert (
            "- [1] fait ancré dans l'état du run : `fallacy_per_argument.arg_7`"
            in section
        )

    def test_the_fiche_prints_no_raw_anchor(self):
        """On main the reader met ``[artifact:…]`` 40-64 times per fiche —
        debug vocabulary on the reading surface."""
        from scripts.dataset.render_campaign_reading_folder import render_fiche

        facts = {
            "title": "Doc",
            "speaker": "Orateur",
            "year": "2026",
            "opaque_id": "doc_A",
            "workflow": "spectacular",
            "status": "ok",
            "chars": 921,
            "args": 3,
            "fallacies": 1,
            "fol": 2,
            "pl": 1,
            "modal": 0,
            "wall_s": 12.0,
            "calls": 4,
            "cost": 0.01,
            "reading_window_status": None,
            "restitution_acts_degraded": None,
        }
        state = {
            "act1_framing": (
                "Cadrage portant une ancre "
                "[artifact:fallacy_per_argument.arg_7] dans le texte."
            ),
            "act2_narrative": "Récit propre, sans ancre.",
            "act3_conclusion": (
                "Conclusion qui cite la même ancre "
                "[artifact:fallacy_per_argument.arg_7] encore."
            ),
            "narrative_synthesis": None,
            "interpretive_question": (
                "Question qui porte une autre ancre [artifact:stakes.count] ?"
            ),
        }
        out = render_fiche(facts, state, None, "abc1234", "gpt-x", "run")
        # The notes section names each anchor as data (in backticks); the
        # PROSE carries numbers — the raw spelling is gone everywhere.
        assert out.count("[artifact:") == 0, (
            "raw anchors in the fiche body: the reader meets debug "
            "vocabulary on the reading surface"
        )
        assert "### Notes du pipeline (ancres du run)" in out
        assert (
            "- [1] fait ancré dans l'état du run : `fallacy_per_argument.arg_7`" in out
        )
        assert "- [2] fait ancré dans l'état du run : `stakes.count`" in out
        assert "ancre [1] dans le texte" in out
        assert "même ancre [1] encore" in out
        assert "autre ancre [2] ?" in out

    def test_the_judge_reads_the_fiche_section_and_no_raw_anchor(self):
        """R1141 placement rule: the numbering runs INSIDE ``pipeline_full_text``.

        ``pipeline_text_from_state`` is the judge's arm; it must be the very
        string the fiche prints, notes included. Numbering done AROUND the
        producer — in ``render_fiche`` — would leave the judge reading raw
        ``[artifact:…]`` while the reader read numbered notes: the divergence
        the single producer exists to close (#3375 tranche 3).
        """
        from scripts.dataset.judge_panel import pipeline_text_from_state
        from scripts.dataset.render_campaign_reading_folder import render_fiche

        raw = "Le document intégral, lu par le pipeline. " * 25
        state = {
            "raw_text": raw,
            "act1_framing": "Cadrage [artifact:fallacy_per_argument.arg_7] ici.",
            "act2_narrative": "Récit [artifact:stakes.count] là.",
            "act3_conclusion": "Conclusion [artifact:fallacy_per_argument.arg_7].",
            "narrative_synthesis": None,
            "interpretive_question": "Question [artifact:stakes.count] ?",
        }
        facts = {
            "title": "Doc",
            "speaker": "Orateur",
            "year": "2026",
            "opaque_id": "doc_A",
            "workflow": "spectacular",
            "status": "ok",
            "classification": None,
            "outcome": {},
            "chars": len(raw),
            "args": 3,
            "fallacies": 1,
            "fol": 2,
            "pl": 1,
            "modal": 0,
            "wall_s": 12.0,
            "calls": 4,
            "cost": 0.01,
            "reading_window_status": None,
            "restitution_acts_degraded": None,
        }
        judged = pipeline_text_from_state(
            state,
            {
                "document_classification": None,
                "opaque_id": "doc_A",
                "outcome": {},
            },
        )
        assert "[artifact:" not in judged
        assert "fait ancré dans l'état du run : `stakes.count`" in judged

        fiche = render_fiche(facts, state, None, "abc1234", "gpt-x", "run")
        section = fiche.split("## Le pipeline, en texte intégral\n\n", 1)[1]
        section = section.split("## La réponse zero-shot, intégrale", 1)[0]
        # Exactly the printed string, then the join's newline before the
        # next heading — byte-for-byte, not a similarity.
        assert section == judged + "\n"


# ============================================================================
# Item 7 — Act III's unexplained letter gets the bounded retry Act II has
# ============================================================================


_WOVEN_3_GAMMA = (
    "### Ce que le discours dit vraiment\n\n"
    "Le locuteur défend une lecture ordonnée de ses engagements.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    "La position résiste à l'examen croisé des axes.\n\n"
    "### Comment se faire son avis\n\n"
    "Pour γ, la conclusion tient sur la base examinée ; le reste suit."
)

_WOVEN_3_CLEAN = (
    "### Ce que le discours dit vraiment\n\n"
    "Le locuteur défend une lecture ordonnée de ses engagements.\n\n"
    "### Ce qui tient et ce qui ne tient pas\n\n"
    "La position résiste à l'examen croisé des axes.\n\n"
    "### Comment se faire son avis\n\n"
    "La conclusion tient sur la base examinée ; le reste suit."
)


class TestAct3LetterGetsItsRetry:
    def test_a_greek_letter_prose_triggers_one_correction_demand(self):
        """On main #3317's letter retry was wired into Act II only — Act
        III printed « Pour γ, … » with no legend anywhere near it."""
        state = _bounds_state()
        prompts: list = []

        async def _capture(prompt: str) -> str:
            prompts.append(prompt)
            return _WOVEN_3_GAMMA if len(prompts) == 1 else _WOVEN_3_CLEAN

        result = asyncio.run(build_act3_conclusion(state, llm_callable=_capture))
        assert len(prompts) == 2, (
            "a conclusion printing a designation letter earned exactly one "
            "bounded retry (#3343)"
        )
        assert "lettre de désignation" in prompts[1]
        # The retry is bounded: one correction demand, never a loop.
        assert len(prompts) <= 2
        assert "Pour γ" not in result.narrative


# ============================================================================
# Item 8 — the reader surface names no workflow id and no issue number
# ============================================================================


class TestReaderSurfaceNamesNoWorkflowId:
    def test_the_fiche_header_carries_the_reader_label(self):
        """On main the fiche said « spectacular » and « #3123 » — the
        pipeline's internal names on the reader's surface."""
        from scripts.dataset.render_campaign_reading_folder import (
            WORKFLOW_LABELS_FR,
            render_fiche,
        )

        facts = {
            "title": "Doc",
            "speaker": "Orateur",
            "year": "2026",
            "opaque_id": "doc_A",
            "workflow": "spectacular",
            "status": "ok",
            "chars": 921,
            "args": 3,
            "fallacies": 1,
            "fol": 2,
            "pl": 1,
            "modal": 0,
            "wall_s": 12.0,
            "calls": 4,
            "cost": 0.01,
            "reading_window_status": None,
            "restitution_acts_degraded": None,
        }
        state = {
            "act1_framing": "Cadrage sobre.",
            "act2_narrative": "Récit sobre.",
            "act3_conclusion": "Conclusion sobre.",
            "narrative_synthesis": None,
            "interpretive_question": None,
        }
        out = render_fiche(facts, state, None, "abc1234", "gpt-x", "run")
        assert "spectacular" not in out
        assert WORKFLOW_LABELS_FR["spectacular"] in out
        assert "#3123" not in out


# ============================================================================
# Item 9 — the stamp names the ROUTE the run takes, and labels its probes
# ============================================================================


class TestStampNamesTheRouteNotTheProbe:
    def _env(self) -> dict:
        return {
            "jvm": {
                "jvm_started": True,
                "jvm_started_note": "test",
                "jar_count_in_libs_tweety": 74,
                "tweety_version_target": "1.28",
            },
            "llm_endpoints": {
                "openai_configured": True,
                "self_hosted_configured": True,
                "self_hosted_endpoint": "http://localhost:5001/v1",
            },
            "llm_route": {
                "probe": "resolved",
                "provider": "openai",
                "endpoint": "https://api.openai.com/v1",
                "model": "gpt-5.6-luna",
            },
            "torch": {"torch_available": False, "torch_note": "test"},
            "overrides": {},
        }

    def test_the_route_line_precedes_and_differs_from_the_probe_census(self):
        """On main the stamp printed ``endpoint=`` from a self-hosted
        PROBE while the run answered through OpenAI — a probe read as the
        route."""
        out = render_environment_stamp(self._env())
        assert (
            "llm: route=openai endpoint=https://api.openai.com/v1 "
            "model=gpt-5.6-luna" in out
        )
        # The census stays, labelled as what it is.
        assert "llm probes: configured=[openai, self_hosted]" in out
        assert "probe: self_hosted endpoint=http://localhost:5001/v1" in out

    def test_a_refused_resolution_says_refused(self):
        env = self._env()
        env["llm_route"] = {"probe": "refused", "note": "divergence gardée"}
        out = render_environment_stamp(env)
        assert "llm: route=REFUSED — divergence gardée" in out

    def test_the_route_comes_from_the_canonical_resolver(self):
        """The route is what ``resolve_chat_endpoint`` (#2352) would hand
        the run — one route source, not a re-derivation."""
        from argumentation_analysis.evaluation.env_manifest import _probe_llm_route

        route = _probe_llm_route()
        assert route["probe"] in ("resolved", "refused", "unavailable"), route
        if route["probe"] == "resolved":
            assert route["provider"] in ("openai", "openrouter", "anthropic", "none")
