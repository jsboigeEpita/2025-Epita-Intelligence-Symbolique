"""#3154 — Act I's stakeholder reader reads the keys its producer writes.

The stakes extractor (``stakes_extractor.EXTRACTION_PROMPT``) writes
``{name, role, stance, evidence_indices}`` and nothing else. The Act I reader
used to take ``role or name`` for the label and ``interest or description or
stake`` for the detail — so the name never reached the writer, the stance never
reached it, and every party collapsed onto a bare role (measured on R1107:
nine named parties arrived as ``opponent`` ×5 / ``audience`` ×2, no name, no
stance, and the report then said the adversaries' "lists count up to four
identical entries" — it could name none of them).

Family #1019: a reader reading keys its producer does not write.

Deterministic — no JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act1_framing_plugin import (
    build_act1_evidence,
    build_act1_prompt,
)


def _state(stakeholders, **fields):
    base = dict(
        source_metadata={},
        stakes_and_stakeholders={
            "stakes": [],
            "stakeholders": stakeholders,
            "rhetorical_register": "",
            "discursive_arena": "",
        },
        identified_arguments={},
    )
    base.update(fields)
    return SimpleNamespace(**base)


# Shaped exactly as the producer writes them: name / role / stance /
# evidence_indices — no ``interest``, no ``description``, no ``stake``, no ``id``.
_PRODUCED = [
    {
        "name": "Parti_Nord",
        "role": "opponent",
        "stance": "against",
        "evidence_indices": [0, 1],
    },
    {
        "name": "Assemblee_Civile",
        "role": "audience",
        "stance": "uncommitted",
        "evidence_indices": [2],
    },
    {
        "name": "Coalition_Centre",
        "role": "opponent",
        "stance": "against",
        "evidence_indices": [],
    },
]


class TestEveryNameAndStanceReachesThePrompt:
    def test_the_prompt_carries_every_name_and_every_stance(self):
        prompt = build_act1_prompt(build_act1_evidence(_state(_PRODUCED)))
        for sh in _PRODUCED:
            assert sh["name"] in prompt, f"name {sh['name']!r} never reached the writer"
            assert (
                sh["stance"] in prompt
            ), f"stance {sh['stance']!r} never reached the writer"

    def test_a_party_is_not_a_bare_role(self):
        # The defect's signature: several parties rendered as the same word.
        prompt = build_act1_prompt(build_act1_evidence(_state(_PRODUCED)))
        assert "- opponent" not in prompt
        assert "- audience" not in prompt

    def test_each_line_pairs_name_role_and_stance(self):
        prompt = build_act1_prompt(build_act1_evidence(_state(_PRODUCED)))
        assert "- Parti_Nord (opponent, against)" in prompt
        assert "- Assemblee_Civile (audience, uncommitted)" in prompt


class TestTheReaderStaysHonest:
    def test_an_older_record_carrying_interest_keeps_it_as_the_detail(self):
        prompt = build_act1_prompt(
            build_act1_evidence(
                _state([{"role": "locuteur", "interest": "Faire adopter la decision."}])
            )
        )
        assert "- locuteur : Faire adopter la decision." in prompt

    def test_a_name_without_qualifiers_prints_no_empty_parentheses(self):
        prompt = build_act1_prompt(build_act1_evidence(_state([{"name": "Parti_Sud"}])))
        assert "- Parti_Sud" in prompt
        assert "- Parti_Sud (" not in prompt

    def test_a_detail_only_record_keeps_its_sentence(self):
        prompt = build_act1_prompt(
            build_act1_evidence(_state([{"interest": "Defendre la reforme."}]))
        )
        assert "- Defendre la reforme." in prompt
