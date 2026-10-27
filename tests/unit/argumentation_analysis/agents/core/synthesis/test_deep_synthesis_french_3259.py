"""#3259 — the grounded transversal block reads in the report's French.

The « Synthèse narrative » block is appended to a French report (the acts
read in French); until #3259 the producer prompt taught four English
headings and VG-3 enforced exactly those, so every rendered block came out
in English. The witness pins the repaired behaviour: the SAME gate that
accepts the French vocabulary rejects the English one — not a test that
re-asserts the prompt constant.

Synthetic stubs only: opaque ids, synthetic citation keys, no corpus text.
"""

from __future__ import annotations

from argumentation_analysis.agents.core.synthesis.deep_synthesis_agent import (
    DeepSynthesisAgent,
)

_FRENCH_STUB = """## Motifs transversaux
Le même geste d'esquive revient sur plusieurs cibles [artifact:identified_arguments.arg_1] et franchit les familles de sophismes [artifact:identified_fallacies.f1].

## Évaluation de la stratégie rhétorique
La pression tient lieu de preuve : le locuteur déplace l'enjeu [artifact:counter_arguments.c1] et l'extension admise ne le soutient pas [artifact:dung_frameworks.dung_1].

## Vulnérabilités structurelles
Les croyances rétractées affaiblissent la chaîne [artifact:jtms_beliefs.b1] ; la convergence formelle fait défaut [artifact:propositional_analysis_results.p1].

## Synthèse interprétative
Sous l'examen multi-méthodes, le discours tient par l'autorité, non par la preuve [artifact:identified_arguments.arg_2] [artifact:identified_fallacies.f2]."""

#: What the pre-#3259 prompt taught the model to write (measured on the
#: R1109-R1115 renders): same structure, same citation discipline, English
#: headings and prose.
_ENGLISH_STUB = """## Transversal Patterns
The same evasive move recurs at several targets [artifact:identified_arguments.arg_1] and crosses fallacy families [artifact:identified_fallacies.f1].

## Rhetorical Strategy Assessment
Pressure stands in for proof: the speaker shifts the stakes [artifact:counter_arguments.c1] and the grounded extension does not carry it [artifact:dung_frameworks.dung_1].

## Structural Vulnerabilities
Retracted beliefs weaken the chain [artifact:jtms_beliefs.b1]; the formal convergence is missing [artifact:propositional_analysis_results.p1].

## Interpretive Synthesis
Under multi-method scrutiny the discourse holds by authority, not proof [artifact:identified_arguments.arg_2] [artifact:identified_fallacies.f2]."""

_PLANTED_KEYS = [
    "identified_arguments.arg_1",
    "identified_fallacies.f1",
    "counter_arguments.c1",
    "dung_frameworks.dung_1",
    "jtms_beliefs.b1",
    "propositional_analysis_results.p1",
    "identified_arguments.arg_2",
    "identified_fallacies.f2",
]


def _vg3(synthesis_md: str) -> bool:
    gates = DeepSynthesisAgent.validate_value_gates(synthesis_md, 4)
    return bool(gates["vg3_no_boilerplate"]["pass"])


class TestTheGateSpeaksFrench:
    def test_the_french_vocabulary_passes_vg3(self) -> None:
        """Born red on main: the French block was the rejected one."""
        assert _vg3(_FRENCH_STUB)

    def test_the_english_vocabulary_is_rejected_vg3(self) -> None:
        """The same gate now treats the old English scaffold as boilerplate.

        On main this passes VG-3 (the four English headings were the
        required ones) — that is precisely the defect the issue measured
        on the R1109-R1115 renders.
        """
        assert not _vg3(_ENGLISH_STUB)

    def test_a_missing_section_still_fails_in_the_new_vocabulary(self) -> None:
        """Mutation: drop one section -> the completeness check stays red.

        The heading swap must not weaken VG-3: a French response that
        omits a section is still boilerplate-incomplete.
        """
        for heading in DeepSynthesisAgent.REQUIRED_GROUNDED_SECTIONS:
            mutilated = _FRENCH_STUB.replace(f"{heading}\n", "", 1)
            assert heading not in mutilated  # the mutation is real
            assert not _vg3(mutilated), f"VG-3 accepted a block missing {heading!r}"

    def test_citation_keys_survive_the_gate_verbatim(self) -> None:
        """VG-3 never rewrites prose: the keys in are the keys counted."""
        found = sorted(
            "".join(parts)
            for parts in DeepSynthesisAgent.CITATION_RE.findall(_FRENCH_STUB)
        )
        assert found == sorted(_PLANTED_KEYS)

    def test_the_prompt_teaches_exactly_what_the_check_enforces(self) -> None:
        """One vocabulary: every enforced heading appears in the prompt.

        The #3123 shape — the producer and the check read the same
        constant, so they cannot disagree. (A consistency guarantee on
        top of the behavioural witness above, not a substitute for it.)
        """
        prompt = DeepSynthesisAgent.GROUNDED_SYNTHESIS_PROMPT
        for heading in DeepSynthesisAgent.REQUIRED_GROUNDED_SECTIONS:
            assert heading in prompt
        # And the retired English headings teach nothing anymore.
        for retired in (
            "## Transversal Patterns",
            "## Rhetorical Strategy Assessment",
            "## Structural Vulnerabilities",
            "## Interpretive Synthesis",
        ):
            assert retired not in prompt


class TestSectionVocabulary:
    def test_required_sections_are_the_french_four(self) -> None:
        assert DeepSynthesisAgent.REQUIRED_GROUNDED_SECTIONS == [
            "## Motifs transversaux",
            "## Évaluation de la stratégie rhétorique",
            "## Vulnérabilités structurelles",
            "## Synthèse interprétative",
        ]
