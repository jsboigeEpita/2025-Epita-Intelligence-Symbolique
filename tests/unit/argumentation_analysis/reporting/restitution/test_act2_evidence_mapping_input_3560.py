# -*- coding: utf-8 -*-
"""#3560 item 25b — ``build_act2_evidence`` reads the mapping form of a state.

The coordinator's c12 probe measured it: replaying an archived state as the
decoded JSON ``dict`` yields **0 movements, no error** — the builder reads
its input by attribute, so a mapping is silently read as an empty state,
and a scalar is read as one too. An instrument that silently measures
nothing is worse than one that fails (the replay fidelity witness of #3650
relied on the caller remembering to wrap the dict).

The fix: the mapping form is READ (attribute access over the keys), and an
input that is neither a state nor a mapping RAISES ``TypeError`` — the two
forms the replay tooling actually produces, named in the error.

Synthetic only — same document family as the item-23b witness, no key, no
network, no corpus.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from argumentation_analysis.agents.core.reading.coverage_review import LENS_BY_CLASS
from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
)

OPENING = "Speaker_A ouvre le débat sur une thèse simple."
FILLER = " ".join(
    f"Phrase de contexte numéro {index} pour installer le débat."
    for index in range(1, 31)
)
DOCUMENT = f"{OPENING} {FILLER}"
UNITS = {
    "arg_1": "Un cas unique est monté en règle pour justifier la mesure.",
    "arg_5": "Une réserve tardive n'entre jamais dans le débat principal.",
}
FALLACIES = {
    "f_1": {
        "target_argument_id": "arg_1",
        "family": "Erreur de raisonnement",
        "type": "Généralisation hâtive",
        "justification": "Un cas unique ne fonde pas une règle générale.",
    },
}


def _coverage_review() -> dict:
    return {
        "status": "ok",
        "items": [],
        "examined": 0,
        "examined_by_class": {},
        "document_chars": len(DOCUMENT),
        "dropped": {},
        "reason": "",
        "basis": "coverage_review",
    }


def _dict_state() -> dict:
    """The mapping form of an archived state — what ``json.loads`` returns."""
    return {
        "raw_text": DOCUMENT,
        "identified_arguments": {
            k: dict(v) if isinstance(v, dict) else v for k, v in UNITS.items()
        },
        "identified_fallacies": {k: dict(v) for k, v in FALLACIES.items()},
        "argument_quality_scores": {},
        "counter_arguments": [],
        "analysis_coverage": {"fallacy_per_argument": {"unit_ids": ["arg_1"]}},
        "coverage_review": _coverage_review(),
    }


def _attr_state() -> SimpleNamespace:
    """The same state, attribute form — what the pipeline passes live."""
    return SimpleNamespace(**_dict_state())


def _themes(evidence) -> list:
    return [m.theme for m in evidence.movements]


class TestTheMappingFormIsRead:
    def test_the_dict_yields_the_same_movements_as_the_attribute_form(self) -> None:
        """RED on the pre-25b head: the dict form yields 0 movements, the
        attribute form its own — the replay tooling had to remember to wrap
        the dict or silently measure nothing."""
        attr = build_act2_evidence(_attr_state())
        as_dict = build_act2_evidence(_dict_state())
        assert _themes(as_dict) == _themes(attr)
        assert len(as_dict.movements) == len(attr.movements)
        assert len(as_dict.movements) > 0  # the dict read something, not nothing

    def test_the_dict_form_feeds_the_fallacy_thread(self) -> None:
        """The fallacy-built movement survives the mapping read — the same
        thread the c12 probe compared movement by movement."""
        evidence = build_act2_evidence(_dict_state())
        themes = _themes(evidence)
        assert any("raisonnement" in (t or "").lower() for t in themes)


class TestNeitherStateNorMappingRaises:
    def test_a_scalar_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            build_act2_evidence("not a state")

    def test_none_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            build_act2_evidence(None)

    def test_a_list_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            build_act2_evidence([_dict_state()])

    def test_the_error_names_the_two_accepted_forms(self) -> None:
        with pytest.raises(TypeError, match="mapping|état"):
            build_act2_evidence(42)


class TestTheAttributeFormIsUnchanged:
    def test_the_attribute_state_still_builds(self) -> None:
        """Positive control: the live pipeline's form needs no wrap and no
        change — the coercion is additive at the entry, never a detour."""
        evidence = build_act2_evidence(_attr_state())
        assert len(evidence.movements) > 0
