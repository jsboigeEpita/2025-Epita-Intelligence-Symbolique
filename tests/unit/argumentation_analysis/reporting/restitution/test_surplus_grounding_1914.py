"""#1914 criterion 8 — the reader-chair fixture that rejects ungrounded
surplus claims.

The issue's most discriminant acceptance criterion:

    *A reader-chair fixture rejects a report whose only multi-agent surplus
    is counters/labels without a changed interpretive conclusion.*

The producer side is honest (``TestReaderChair`` in
``test_conclusion_salience_1914.py`` pins that the prompt carries the
refusal when ``established == []``), but until this tranche nothing checked
the **rendered** text: the coordinator's probe (R1029, measured against
``3da03329``) — an Acte III claiming « un surplus interprétatif décisif …
la conclusion interprétative s'en trouve modifiée » on a state whose
re-derived surplus is EMPTY — rendered ``band=PASS``, zero remarks.

These tests pin the consumer side, wired into ``renderer.render`` beside
``check_factual_consistency``:

* **the negative is the test that counts** — the probe report reddens;
* the positive — the SAME claim on a state whose re-derived surplus is
  established passes untouched (anti-pendulum: the fixture rejects the
  unsupported claim, never the mention of multi-agent work);
* the honest refusal and the bare counters/labels inventory pass;
* the discriminator is the STATE (re-derived), never what the act claims —
  pinned by the ± pair (identical body, differing state).

Privacy HARD — opaque ids only (doc_B, arg_1). No JVM, no LLM, no network.
"""

from __future__ import annotations

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution import (
    RestitutionActs,
    RestitutionReportRenderer,
)
from argumentation_analysis.reporting.restitution.state_adapter import (
    state_to_appendix_mapping,
)
from argumentation_analysis.reporting.restitution.surplus_grounding_check import (
    check_surplus_grounding,
)


def _thin_ns() -> SimpleNamespace:
    """Labels + counters only (the TestReaderChair corpus shape): localized
    fallacy, generated counter, no formal verdict, no Dung exclusion, no
    structural relation. The re-derived surplus is EMPTY — measured thin,
    fixture-guaranteed."""
    return SimpleNamespace(
        identified_arguments={"arg_1": "these A", "arg_7": "these B"},
        identified_fallacies={
            "f1": {"target_argument_id": "arg_1", "type": "ad_hominem"},
        },
        argument_quality_scores={},
        counter_arguments=[{"target_arg_id": "arg_1", "counter_content": "contre"}],
        dung_frameworks={},
        propositional_analysis_results=[],
        fol_analysis_results=[],
        modal_analysis_results=[],
    )


def _grounded_ns() -> SimpleNamespace:
    """Same corpus plus discriminating signals (a FOL refutation and a Dung
    exclusion): the re-derived surplus carries established items — the state
    a surplus claim is ALLOWED on."""
    d = _thin_ns().__dict__
    d["fol_analysis_results"] = [
        {"consistent": False, "message": "incoherent", "formulas": ["p(a)"]},
    ]
    d["dung_frameworks"] = {
        "d1": {
            "name": "verification_grounded",
            "arguments": ["arg_1", "arg_7"],
            "attacks": [["arg_7", "arg_1"]],
            "extensions": {"all_members": ["arg_1"]},
        }
    }
    return SimpleNamespace(**d)


_ACT1 = (
    "Le discours analysé (source doc_B) défend une décision controversée "
    "devant un auditoire sceptique. Le locuteur empile des garanties "
    "d'autorité et des appels à la solidarité ; l'enjeu est l'adhésion, pas "
    "la démonstration. Un lecteur attentif doit démêler ce qui persuade de "
    "ce qui prouve."
)

_ACT2 = (
    "Le premier mouvement appuie la thèse centrale sur une autorité "
    "invérifiable, le second déplace la charge de la preuve vers "
    "l'adversaire. Chaque mouvement gagne en efficacité ce qu'il perd en "
    "rigueur : les procédés accomplissent leur office pendant que la trame "
    "argumentative se fragilise mouvement après mouvement."
)

# The coordinator's probe report (R1029) — the exact shape criterion 8
# exists to reject: a decisive-surplus claim + a changed-conclusion claim,
# on matter (counters/labels) the split files as procedural.
_PROBE_ACT3 = (
    "L'analyse conclut à un propos persuasif mais fragile. L'outillage "
    "multi-agents apporte ici un surplus interprétatif décisif : sept "
    "sophismes localisés et douze contre-arguments générés — la conclusion "
    "interprétative s'en trouve modifiée."
)

# The compliant mirror: same corpus, same counts — the honest refusal the
# prompt itself carries when the derived surplus is empty.
_HONEST_ACT3 = (
    "L'analyse conclut à un propos persuasif mais fragile. Rien au-delà "
    "d'une lecture attentive n'a été établi ici : les compteurs et labels "
    "disponibles ne sont pas un surplus interprétatif, et la conclusion "
    "reste celle qu'une lecture soignée aurait formée."
)


def _acts(act3: str) -> RestitutionActs:
    return RestitutionActs(
        act1_framing=_ACT1,
        act2_narrative=_ACT2,
        act3_conclusion=act3,
        source_id="doc_B",
    )


class TestTheNegativeIsTheTestThatCounts:
    """Unit level: the check itself reddens the probe."""

    def test_probe_report_reddens_on_thin_state(self):
        verdict = check_surplus_grounding(
            _PROBE_ACT3, state_to_appendix_mapping(_thin_ns())
        )
        assert verdict.band == "FAIL", (
            "the probe report is the exact shape criterion 8 exists to "
            "reject — it must not pass"
        )
        assert any("Surplus non étayé" in r for r in verdict.reasons)
        assert any("procédurale" in r for r in verdict.reasons)

    def test_discriminator_is_the_state_not_the_claim(self):
        """The ± pair: ONE body (the probe), two states. The verdict follows
        the re-derived state, never what the act claims — the fixture
        re-derives, it does not trust the act."""
        thin = check_surplus_grounding(
            _PROBE_ACT3, state_to_appendix_mapping(_thin_ns())
        )
        grounded = check_surplus_grounding(
            _PROBE_ACT3, state_to_appendix_mapping(_grounded_ns())
        )
        assert thin.band == "FAIL"
        assert grounded.band == "PASS", (
            "a claim grounded in an established surplus must pass — "
            "anti-pendulum: the fixture rejects the unsupported claim, "
            "not the mention of multi-agent work"
        )


class TestTheHonestHalfPasses:
    """Anti-pendulum guards: the check must not mute an honest Acte III."""

    def test_honest_refusal_passes(self):
        verdict = check_surplus_grounding(
            _HONEST_ACT3, state_to_appendix_mapping(_thin_ns())
        )
        assert verdict.band == "PASS"

    def test_counters_inventory_mention_passes(self):
        """Counting the work is legitimate — only SELLING it as surplus is
        not. The bare inventory line carries no claim."""
        inventory = (
            "L'analyse multi-agents a produit sept sophismes localisés et "
            "douze contre-arguments générés, présentés en annexe."
        )
        verdict = check_surplus_grounding(
            inventory, state_to_appendix_mapping(_thin_ns())
        )
        assert verdict.band == "PASS"

    def test_none_state_skips_honestly(self):
        verdict = check_surplus_grounding(_PROBE_ACT3, None)
        assert verdict.band == "PASS"


class TestRendererWiring:
    """Integration level: the fixture is wired into ``renderer.render``,
    beside ``check_factual_consistency`` — the render path itself rejects
    the probe (this is the class that was born red before the wiring)."""

    def test_render_rejects_the_probe_report(self):
        report = RestitutionReportRenderer().render(
            _acts(_PROBE_ACT3), state=state_to_appendix_mapping(_thin_ns())
        )
        assert report.verdict.band == "FAIL"
        assert any("Surplus non étayé" in r for r in report.verdict.reasons)
        # auditability intact: the reason rides the folded gate block, not
        # the reader surface (#2086 contract)
        md = report.markdown
        fold = md.find("<details>")
        assert fold != -1
        assert "Surplus non étayé" not in md[:fold]
        assert "Surplus non étayé" in md[fold:]

    def test_render_passes_the_honest_conclusion(self):
        report = RestitutionReportRenderer().render(
            _acts(_HONEST_ACT3), state=state_to_appendix_mapping(_thin_ns())
        )
        assert report.verdict.band == "PASS", (
            "the wiring must not break honest reports: with the refusal "
            "wording and no other defect, the render stays green"
        )

    def test_render_passes_the_grounded_claim(self):
        report = RestitutionReportRenderer().render(
            _acts(_PROBE_ACT3), state=state_to_appendix_mapping(_grounded_ns())
        )
        assert (
            report.verdict.band == "PASS"
        ), "the same claim on a state whose surplus IS established passes"
