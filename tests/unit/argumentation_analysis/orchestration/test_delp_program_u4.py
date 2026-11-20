"""#3546 — U4 of #1644: the DeLP chain, from the unavailable filing to the
producer that derives a program from the run's own units.

Measured on the recorded cycle-6 panel states (coordinator seat): phase
``delp_reasoning`` status ``completed`` on 9 of 10 documents, 0 of 10 in
``degraded_phases``. Yet ``_invoke_delp`` returned ``status: "unavailable"``
(no ``program`` in context — see #1215: prose is never parsed as DeLP).

Ask 1 — filing: the unavailable payload carried ``status: "unavailable"``
but NO ``degraded: True`` flag, so the rollup at
``workflow_dsl.py:_compute_workflow_degraded`` (which reads
``r.output.get("degraded") is True`` on COMPLETED phases) did not see it.
The phase read as healthy. ``TestDelpUnavailableIsDegraded`` witnesses the
flag and the reason.

Asks 2-7 — producer: ``TestTranslatedProgramProducesVerdict`` (real JVM)
runs the planted permit text through the wiring with a fake translator:
the validated program reaches the handler, the query is decided NO under
generalized specificity (the heritage-zone rule, more specific, defeats
the city-funded rule), and the state writer → ``_delp_verdicts_finding``
→ ``build_act3_prompt`` chain carries the Act III line.
``TestMostSpecificRuleMutation`` is the issue's DoD mutation: removing the
more specific rule flips the verdict to YES.
``TestWiringWithoutJvm`` proves the wiring without a JVM (fake handler
receives the translated program; prose never reaches the handler when no
program was derived). ``TestDelpProgramValidator`` holds the validator
(whole DeLP syntax only; prose, malformed literals and dangling source
ids dropped) and ``TestAssembledProgramParses`` round-trips the ASSEMBLED
program through the real Tweety parser.
``TestStrongNegationQuerySurvives`` / ``TestHandlerAnswerVocabulary``
witness the two handler repairs: the re-parse reads the SOURCE text
(``str(program)`` prints strong negation as ``!``, a lexical rejection),
and the answer is the bare token (Tweety's long form "The answer is: NO"
fell through the reader's comparisons).

Witnesses were born red on the #3641 head (7 of the 9 here), then green;
each repair reddens again under its mutation.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ask 1 — Filing: a DeLP phase returning ``unavailable`` carries degraded=True
# ---------------------------------------------------------------------------


def _run(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestDelpUnavailableIsDegraded:
    """The unavailable payload (no program in context) must carry the
    degraded signal — otherwise the workflow rollup files the phase as
    completed and the absence ledger never names it (#3546)."""

    def test_unavailable_payload_is_flagged_degraded(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_delp,
        )

        result = _run(_invoke_delp("ignored text", {}))

        assert result.get("status") == "unavailable"
        assert (
            result.get("degraded") is True
        ), "unavailable DeLP payload must carry degraded=True so the rollup files it"
        assert result.get("degradation_reason"), (
            "unavailable DeLP payload must carry a degradation_reason "
            "(the absence ledger names the phase by it)"
        )

    def test_unavailable_payload_reason_names_the_missing_program(self):
        from argumentation_analysis.orchestration.invoke_callables import (
            _invoke_delp,
        )

        result = _run(_invoke_delp("ignored text", {}))
        reason = str(result.get("degradation_reason", "")).lower()
        assert (
            "program" in reason
        ), "the degradation_reason must name the missing 'program' so the ledger says why"


# ---------------------------------------------------------------------------
# Handler fix — a strongly negated rule must not kill the query (re-parse
# from the SOURCE text, never from str(program)'s '!' representation)
# ---------------------------------------------------------------------------

#: The planted permit program (#3546 ask 2). Invented content, tests only:
#: a note on a building permit whose second rule (heritage zone) is the
#: more specific one — under generalized specificity it defeats the
#: city-funded rule, so the contested conclusion is NOT warranted.
PLANTED_PROGRAM_WITH_SPECIFIC = "\n".join(
    [
        "city_funded(annex).",
        "heritage_zone(annex).",
        "city_funded(X) <- heritage_zone(X).",
        "gets_permit_within_month(X) -< city_funded(X).",
        "~gets_permit_within_month(X) -< heritage_zone(X).",
    ]
)

#: Mutation (#3546 DoD): the most specific rule removed — the verdict must
#: change (NO -> YES), which reddens the verdict witness below.
PLANTED_PROGRAM_WITHOUT_SPECIFIC = "\n".join(
    [
        "city_funded(annex).",
        "heritage_zone(annex).",
        "city_funded(X) <- heritage_zone(X).",
        "gets_permit_within_month(X) -< city_funded(X).",
    ]
)

PLANTED_QUERY = "gets_permit_within_month(annex)"


def _handler():
    from argumentation_analysis.agents.core.logic.delp_handler import DeLPHandler
    from argumentation_analysis.agents.core.logic.tweety_initializer import (
        ready_initializer,
    )

    return DeLPHandler(ready_initializer())


def _answer_of(program_text: str) -> str:
    handler = _handler()
    result = handler.analyze_delp(program_text, [PLANTED_QUERY])
    answers = [
        r.get("answer", "")
        for r in result.get("query_results", [])
        if r.get("query") == PLANTED_QUERY
    ]
    assert answers, f"no query result for {PLANTED_QUERY}: {result}"
    return answers[0]


@pytest.mark.jpype
class TestStrongNegationQuerySurvives:
    """query() re-parses str(program) whose strong negation prints as '!' —
    a token the parser rejects. On main every strongly negated rule turns
    its query into UNKNOWN (lexical error). The fix re-parses the SOURCE
    text, whose '~' parses fine."""

    def test_strong_negation_rule_yields_a_real_verdict(self):
        answer = _answer_of(PLANTED_PROGRAM_WITH_SPECIFIC)
        assert answer != "UNKNOWN", (
            "a strongly negated rule must not kill the query with a lexical "
            "error — the re-parse must read the source text, not str(program)"
        )


@pytest.mark.jpype
class TestHandlerAnswerVocabulary:
    """The handler's answer must speak the writer/reader vocabulary
    (YES/NO/UNDECIDED/UNKNOWN) — analyze_delp returned Tweety's long form
    ("The answer is: NO"), which the Act III reader compares against the
    bare token, so every real verdict read as undecided-nothing."""

    def test_answer_is_the_bare_token(self):
        handler = _handler()
        result = handler.analyze_delp(PLANTED_PROGRAM_WITHOUT_SPECIFIC, [PLANTED_QUERY])
        answers = [r["answer"] for r in result["query_results"]]
        assert answers == [
            "YES"
        ], f"analyze_delp must return the bare token, got {answers!r}"


# ---------------------------------------------------------------------------
# Asks 2-7 — the producer: translator → handler → state → Act III prompt
# ---------------------------------------------------------------------------

#: Invented content, tests only (#3546 ask 2): the note on a building permit.
#: The second rule (heritage zone) is the more specific one.
PLANTED_TEXT = (
    "Note on the building permit: city-funded projects usually get their "
    "permit within a month. Projects in the heritage zone usually do not. "
    "The library annex is city-funded and in the heritage zone."
)

_PLANTED_UNITS = [
    "City-funded projects usually get their permit within a month.",
    "Projects in the heritage zone usually do not.",
    "The library annex is city-funded and in the heritage zone.",
]

_TRANSLATOR_SRC = (
    "argumentation_analysis.orchestration.structured_arg_translator"
    ".translate_to_delp_program"
)


def _fake_translator_outcome(program_text: str, queries):
    outcome = MagicMock()
    outcome.relations = {
        "program_text": program_text,
        "queries": list(queries),
        "defeasible_count": 2,
    }
    outcome.cause = "evaluated"
    outcome.error = ""
    return outcome


def _delp_invoke(input_text, context):
    from argumentation_analysis.orchestration.invoke_callables import _invoke_delp

    return _invoke_delp(input_text, context)


@pytest.mark.jpype
class TestTranslatedProgramProducesVerdict:
    """Test 2 of the issue's witness: with fake translator replies for the
    planted text, delp_query_results holds one decided query and the Act III
    prompt carries the DeLP line. Red on main (no producer existed: the
    phase returned unavailable, 0 results)."""

    def _invoke(self, program_text):
        with patch(
            _TRANSLATOR_SRC,
            new=AsyncMock(
                return_value=_fake_translator_outcome(program_text, [PLANTED_QUERY])
            ),
        ):
            return _run(_delp_invoke(PLANTED_TEXT, {"arguments": list(_PLANTED_UNITS)}))

    def test_the_translated_program_reaches_the_solver_and_is_decided(self):
        result = self._invoke(PLANTED_PROGRAM_WITH_SPECIFIC)
        assert result.get("program_origin") == "translator"
        answers = [r["answer"] for r in result["query_results"]]
        # Under generalized specificity the heritage-zone rule (more
        # specific) defeats the city-funded rule: the contested conclusion
        # is NOT warranted.
        assert answers == ["NO"], (
            f"the planted program's contested query must be decided NO, "
            f"got {answers!r}"
        )

    def test_the_verdict_reaches_the_act3_prompt(self):
        result = self._invoke(PLANTED_PROGRAM_WITH_SPECIFIC)
        from types import SimpleNamespace

        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_delp_to_state,
        )
        from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
            build_act3_evidence,
            build_act3_prompt,
        )

        real = UnifiedAnalysisState("3546 planted permit probe")
        _write_delp_to_state(result, real, {})
        stub = SimpleNamespace(
            identified_arguments={},
            identified_fallacies={},
            argument_quality_scores={},
            counter_arguments=[],
            dung_frameworks=real.dung_frameworks,
            fol_analysis_results=[],
            propositional_analysis_results=[],
            modal_analysis_results=[],
            narrative_synthesis="",
            governance_decisions=[],
            debate_transcripts=[],
        )
        evidence = build_act3_evidence(stub)
        capabilities = [f.capability for f in evidence.structured_findings]
        assert (
            "delp_reasoning" in capabilities
        ), "the DeLP verdict finding must be part of the Act III evidence"
        prompt = build_act3_prompt(evidence)
        assert (
            "défaisable" in prompt and "renversée" in prompt
        ), "the Act III prompt must carry the DeLP line (a decided query)"


@pytest.mark.jpype
class TestMostSpecificRuleMutation:
    """DoD mutation control: with the more specific rule removed from the
    program, the verdict changes (NO -> YES) and the witness is red again."""

    def test_without_the_specific_rule_the_verdict_flips(self):
        with patch(
            _TRANSLATOR_SRC,
            new=AsyncMock(
                return_value=_fake_translator_outcome(
                    PLANTED_PROGRAM_WITHOUT_SPECIFIC, [PLANTED_QUERY]
                )
            ),
        ):
            result = _run(
                _delp_invoke(PLANTED_TEXT, {"arguments": list(_PLANTED_UNITS)})
            )
        answers = [r["answer"] for r in result["query_results"]]
        assert answers == ["YES"], (
            f"without the heritage-zone rule the query must be warranted "
            f"(YES), got {answers!r} — if this equals NO the mutation no "
            "longer discriminates"
        )


class TestWiringWithoutJvm:
    """The wiring alone, no JVM: a fake handler records the program it was
    handed — the translated program, whole, never the document's prose."""

    def test_the_handler_receives_the_translated_program(self):
        received = {}

        class _FakeHandler:
            def __init__(self, initializer):
                received["initializer"] = initializer

            def analyze_delp(self, program_text, queries, criterion):
                received["program"] = program_text
                received["queries"] = queries
                received["criterion"] = criterion
                return {"query_results": [], "program": program_text}

        with patch(
            _TRANSLATOR_SRC,
            new=AsyncMock(
                return_value=_fake_translator_outcome(
                    PLANTED_PROGRAM_WITH_SPECIFIC, [PLANTED_QUERY]
                )
            ),
        ), patch(
            "argumentation_analysis.agents.core.logic.delp_handler.DeLPHandler",
            _FakeHandler,
        ), patch(
            "argumentation_analysis.agents.core.logic.tweety_initializer"
            ".ready_initializer",
            return_value=object(),
        ):
            result = _run(
                _delp_invoke(PLANTED_TEXT, {"arguments": list(_PLANTED_UNITS)})
            )

        assert (
            received["program"] == PLANTED_PROGRAM_WITH_SPECIFIC
        ), "the handler must receive the translator's validated program"
        assert received["queries"] == [PLANTED_QUERY]
        assert result.get("program_origin") == "translator"

    def test_prose_never_reaches_the_handler(self):
        """#1215: without a translator reply, the handler is never built —
        the unavailable payload returns before any DeLP parsing."""

        built = []

        class _LoudHandler:
            def __init__(self, initializer):
                built.append("constructed")

            def analyze_delp(self, *a, **k):  # pragma: no cover — must not run
                raise AssertionError("handler must not run without a program")

        empty_outcome = MagicMock()
        empty_outcome.relations = {}
        empty_outcome.cause = "no_genuine_relations"
        empty_outcome.error = ""

        with patch(_TRANSLATOR_SRC, new=AsyncMock(return_value=empty_outcome)), patch(
            "argumentation_analysis.agents.core.logic.delp_handler.DeLPHandler",
            _LoudHandler,
        ), patch(
            "argumentation_analysis.agents.core.logic.tweety_initializer"
            ".ready_initializer",
            return_value=object(),
        ):
            result = _run(
                _delp_invoke(PLANTED_TEXT, {"arguments": list(_PLANTED_UNITS)})
            )

        assert built == [], "no handler may be constructed without a program"
        assert result.get("status") == "unavailable"
        assert result.get("degraded") is True


# ---------------------------------------------------------------------------
# The validator — whole programs only, every line DeLP, every source real
# ---------------------------------------------------------------------------


class TestDelpProgramValidator:
    """_validate_delp_program filters the LLM reply down to a whole,
    syntactically valid program — prose, malformed literals and dangling
    source ids are dropped, never repaired (#1215)."""

    def _validate(self, data):
        from argumentation_analysis.orchestration.structured_arg_translator import (
            _build_inventory,
            _validate_delp_program,
        )

        arg_by_id, _ = _build_inventory(_PLANTED_UNITS)
        return _validate_delp_program(data, arg_by_id)

    def test_a_well_formed_reply_assembles_the_program(self):
        data = {
            "facts": [
                {
                    "predicate": "city_funded",
                    "args": ["annex"],
                    "source": ["arg3"],
                    "rationale": "stated",
                }
            ],
            "strict_rules": [
                {
                    "head": "city_funded(X)",
                    "body": ["heritage_zone(X)"],
                    "source": ["arg3"],
                    "rationale": "every heritage project is city-funded",
                }
            ],
            "defeasible_rules": [
                {
                    "head": "gets_permit(X)",
                    "body": ["city_funded(X)"],
                    "source": ["arg1"],
                    "rationale": "usually",
                },
                {
                    "head": "~gets_permit(X)",
                    "body": ["heritage_zone(X)"],
                    "source": ["arg2"],
                    "rationale": "usually not",
                },
            ],
            "queries": ["gets_permit(annex)"],
        }
        program = self._validate(data)
        assert program["defeasible_count"] == 2
        assert program["queries"] == ["gets_permit(annex)"]
        lines = program["program_text"].splitlines()
        assert lines[0] == "city_funded(annex)."
        assert "city_funded(X) <- heritage_zone(X)." in lines
        assert "~gets_permit(X) -< heritage_zone(X)." in lines

    def test_prose_and_malformed_entries_are_dropped(self):
        data = {
            "facts": [
                {
                    "predicate": "The annex",
                    "args": ["is city funded"],
                    "source": ["arg3"],
                    "rationale": "prose is not a fact",
                },
                {
                    "predicate": "valid_fact",
                    "args": ["annex"],
                    "source": ["arg3"],
                    "rationale": "kept",
                },
            ],
            "strict_rules": [
                {
                    "head": "head with spaces(X)",
                    "body": ["body(X)"],
                    "source": ["arg1"],
                    "rationale": "dropped",
                }
            ],
            "defeasible_rules": [
                {
                    "head": "q(X)",
                    "body": ["p(X)"],
                    "source": ["arg1"],
                    "rationale": "kept",
                }
            ],
            "queries": ["not a literal", "q(annex)"],
        }
        program = self._validate(data)
        assert program["program_text"] == "valid_fact(annex).\nq(X) -< p(X)."
        assert program["queries"] == ["q(annex)"]

    def test_a_dangling_source_id_drops_the_entry(self):
        data = {
            "facts": [
                {
                    "predicate": "p",
                    "args": ["a"],
                    "source": ["arg99"],
                    "rationale": "not in the inventory",
                }
            ],
            "defeasible_rules": [
                {
                    "head": "q(X)",
                    "body": ["p(X)"],
                    "source": ["arg1"],
                    "rationale": "kept",
                }
            ],
            "queries": ["q(a)"],
        }
        program = self._validate(data)
        assert "p(a)." not in program["program_text"]
        assert "q(X) -< p(X)." in program["program_text"]


@pytest.mark.jpype
class TestAssembledProgramParses:
    """The validator's ASSEMBLED program must survive the real parser — the
    end-to-end witnesses hand the handler a pre-formed program_text, so this
    is the one place where _validate_delp_program's own output meets Tweety."""

    def test_the_assembled_program_parses_and_decides(self):
        from argumentation_analysis.orchestration.structured_arg_translator import (
            _build_inventory,
            _validate_delp_program,
        )

        data = {
            "facts": [
                {
                    "predicate": "city_funded",
                    "args": ["annex"],
                    "source": ["arg3"],
                    "rationale": "stated",
                },
                {
                    "predicate": "heritage_zone",
                    "args": ["annex"],
                    "source": ["arg3"],
                    "rationale": "stated",
                },
            ],
            "strict_rules": [
                {
                    "head": "city_funded(X)",
                    "body": ["heritage_zone(X)"],
                    "source": ["arg3"],
                    "rationale": "every heritage project is city-funded",
                }
            ],
            "defeasible_rules": [
                {
                    "head": "gets_permit_within_month(X)",
                    "body": ["city_funded(X)"],
                    "source": ["arg1"],
                    "rationale": "usually",
                },
                {
                    "head": "~gets_permit_within_month(X)",
                    "body": ["heritage_zone(X)"],
                    "source": ["arg2"],
                    "rationale": "usually not",
                },
            ],
            "queries": ["gets_permit_within_month(annex)"],
        }
        arg_by_id, _ = _build_inventory(_PLANTED_UNITS)
        program = _validate_delp_program(data, arg_by_id)
        assert program["defeasible_count"] == 2

        result = _handler().analyze_delp(program["program_text"], program["queries"])
        answers = [r["answer"] for r in result["query_results"]]
        assert answers == [
            "NO"
        ], f"the assembled program must parse and decide NO, got {answers!r}"
