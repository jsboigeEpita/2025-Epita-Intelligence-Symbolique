"""#3434 — the JTMS lens survives a fallacy whose confidence the descent
declares unmeasured.

On the v1 panel's cycle 2, the phase failed outright on one document: a
``hierarchical_fallacy`` record carried ``confidence: None`` — the #3029/#3034
contract, a confidence the model did not give is None and its reason travels
in ``confidence_note`` — and the fallacy-belief loop coerced it with
``float(...)``. The whole lens was lost on that document: no beliefs, no
retraction chain.

The repair is the honest absence, not a number: the unmeasured fallacy does
NOT become a belief (a confidence nobody measured would read as measured in
every reader downstream — ``ExtendedBelief`` coerces to float and max()-merges
on update), it is excluded and NAMED in the phase output. Anti-pendulum,
both ways: no 0.7 default (that is exactly what #3029 removed), and no
silent drop either (the phase says what it did with the record).

Offline: synthetic opaque records, no LLM, no network, no corpus content.
"""

from __future__ import annotations


def _subject():
    """The module under test, imported late on purpose (born-red discipline)."""
    from argumentation_analysis.orchestration.unified_pipeline import _invoke_jtms

    return _invoke_jtms


def _context(fallacies: list[dict]) -> dict:
    return {
        "phase_extract_output": {
            "arguments": [
                {"text": "Premise one supports the thesis"},
                {"text": "Premise two supports the thesis"},
            ],
            "claims": [],
        },
        "phase_hierarchical_fallacy_output": {"fallacies": fallacies},
    }


_UNMEASURED = {
    "fallacy_type": "appel_a_la_tradition",
    "explanation": "the move leans on age alone",
    # The #3029/#3034 contract: present and None, with the reason beside it.
    "confidence": None,
    "confidence_note": "confidence absente (argument omis par le modele)",
    "detection_paths": ["fallacy_descent"],
}

_MEASURED = {
    "fallacy_type": "homme_de_paille",
    "explanation": "the move refutes a position nobody held",
    "confidence": 0.9,
    "target_argument": "arg_2",
}


class TestTheUnmeasuredFallacyIsNamedNotDropped:
    async def test_the_phase_completes_and_names_the_record(self) -> None:
        """Born red on the frozen tree: ``float(None)`` raised TypeError and
        the WHOLE phase was lost. After: the phase completes, the record is
        excluded from the belief set and named with its note."""
        invoke_jtms = _subject()
        result = await invoke_jtms("text", _context([_UNMEASURED]))
        # The phase completed — the lens is no longer lost on the document.
        assert result["belief_count"] == 2  # the two premises, nothing else
        assert result["fallacy_count"] == 0
        assert result["fallacies_considered"] == 1
        # The record is accounted for, by name and with its reason.
        assert result["unmeasured_confidence_fallacies"] == [
            {
                "fallacy_type": "appel_a_la_tradition",
                "confidence_note": "confidence absente (argument omis par le modele)",
            }
        ]

    async def test_no_fabricated_number_becomes_a_belief(self) -> None:
        """Anti-pendulum: nothing measured stands in for the unmeasured
        confidence. The fallacy belief does not exist at all — no 0.7, no
        0.0, no belief whose confidence would read as measured."""
        invoke_jtms = _subject()
        result = await invoke_jtms("text", _context([_UNMEASURED]))
        fallacy_beliefs = [
            name for name in result["beliefs"] if name.startswith("FALLACY:")
        ]
        assert fallacy_beliefs == []
        for entry in result["beliefs"].values():
            assert entry["agent_source"] != "fallacy_detector"


class TestTheMeasuredPathIsUntouched:
    async def test_a_measured_fallacy_still_becomes_a_belief(self) -> None:
        """The post-#3029 measured shape (key present, numeric) keeps its
        belief, its confidence and its retraction — the repair touches only
        the unmeasured standing."""
        invoke_jtms = _subject()
        result = await invoke_jtms("text", _context([_MEASURED]))
        assert result["fallacy_count"] == 1
        assert "unmeasured_confidence_fallacies" not in result
        fallacy_entry = result["beliefs"]["FALLACY:homme_de_paille"]
        assert fallacy_entry["confidence"] == 0.9
        assert fallacy_entry["valid"] is True
        # The measured fallacy still retracts its named target.
        assert result["undermined_count"] == 1
        assert (
            result["beliefs"]["arg_2:Premise two supports the thesis"]["valid"] is False
        )

    async def test_a_key_absent_confidence_keeps_the_pre_existing_default(
        self,
    ) -> None:
        """The absent-key path is not this issue's: a producer that stamps
        no confidence key keeps the pre-existing severity/0.7 default,
        unchanged by the repair."""
        invoke_jtms = _subject()
        no_key = {
            "fallacy_type": "pente_glissante",
            "explanation": "the move slides from one step to a cliff",
        }
        result = await invoke_jtms("text", _context([no_key]))
        assert result["fallacy_count"] == 1
        assert result["beliefs"]["FALLACY:pente_glissante"]["confidence"] == 0.7


class TestTheMixedDocumentKeepsBothBooksHonest:
    async def test_one_of_each_is_counted_on_its_own_side(self) -> None:
        """A real document mixes standings. The arithmetic is honest: two
        considered, one belief, one named exclusion — the gap between
        ``fallacies_considered`` and ``fallacy_count`` is explained."""
        invoke_jtms = _subject()
        result = await invoke_jtms("text", _context([_UNMEASURED, _MEASURED]))
        assert result["fallacies_considered"] == 2
        assert result["fallacy_count"] == 1
        assert [
            e["fallacy_type"] for e in result["unmeasured_confidence_fallacies"]
        ] == ["appel_a_la_tradition"]
        # And the measured one still retracted its target.
        assert result["undermined_count"] == 1
