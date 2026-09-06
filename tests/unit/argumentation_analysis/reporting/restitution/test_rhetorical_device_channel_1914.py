# -*- coding: utf-8 -*-
"""#1914 (constat 4, tranche Acte II) — the rhetorical-device channel.

« Rhetorical devices reduced to fallacy labels » : anaphora, slogans, jokes
and genuine faults all exited the Acte II evidence under the same attack
word (« Dérapage : … »), and nothing told the conductor to say WHAT the
device accomplishes. The measured fact this slice builds on: the state's
``justification`` fields already carry the discursive function (« visant
à… », « pour légitimer… ») — including for devices that are not faults
(a joke, a slogan). These tests pin that the evidence line no longer
pre-judges, that the consigne carries the two-sided contract (function
first, verdict kept when deserved, no invented function), and that the
existing honest channels survive.

Synthetic devices only — no corpus content (privacy HARD, same discipline
as test_formal_derivation_channel_1914).
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)

_DEVICE_JUSTIFICATION = (
    "La formule concise et rythmée vise à créer une adhésion par "
    "l'effet de répétition plutôt que par la preuve."
)
_FAULT_JUSTIFICATION = (
    "Le propos attribue un effet à une cause sans lien établi entre " "les deux."
)


def _state():
    return SimpleNamespace(
        identified_arguments={
            "arg_A": "L'orateur martèle une formule-choc pour emporter l'adhésion.",
            "arg_B": "L'orateur attribue un résultat à son action seule.",
        },
        identified_fallacies={
            "f1": {
                "type": "Appel au slogan",
                "family": "Influence",
                "justification": _DEVICE_JUSTIFICATION,
                "target_argument_id": "arg_A",
            },
            "f2": {
                "type": "Confusion entre corrélation et causalité",
                "family": "Erreur de raisonnement",
                "justification": _FAULT_JUSTIFICATION,
                "target_argument_id": "arg_B",
            },
        },
    )


def _prompt(state=None):
    return build_act2_prompt(build_act2_evidence(state or _state()))


class TestProcureLineShape:
    """The evidence line states the device, not the verdict."""

    def test_device_line_names_type_and_family_without_attack_word(self):
        prompt = _prompt()
        assert "Procédé : « Appel au slogan » (famille Influence)." in prompt

    def test_attack_word_gone_from_the_whole_prompt(self):
        assert "Dérapage :" not in _prompt()

    def test_fault_device_keeps_its_full_identity(self):
        prompt = _prompt()
        assert "Procédé : « Confusion entre corrélation et causalité »" in prompt
        assert "(famille Erreur de raisonnement)." in prompt

    def test_justification_carried_verbatim_for_both_natures(self):
        prompt = _prompt()
        assert _DEVICE_JUSTIFICATION in prompt
        assert _FAULT_JUSTIFICATION in prompt


class TestConsigneContract:
    """The conductor is told: function first, verdict kept, no invention."""

    def test_accomplishment_contract_present(self):
        prompt = _prompt()
        assert "CE QU'IL ACCOMPLIT" in prompt
        assert "pas un défaut par nature" in prompt

    def test_deserved_verdict_kept(self):
        assert "GARDE son verdict de sophisme" in _prompt()

    def test_no_invented_function(self):
        assert "N'invente JAMAIS une fonction" in _prompt()

    def test_weaving_bullet_names_the_new_channel(self):
        assert (
            "ses procédés relevés (procédé + descente + contre-argument)" in _prompt()
        )


class TestHonestChannelsIntact:
    """The neighboring honest-absence channels survive the slice."""

    def test_unattributed_fallacy_still_counted_apart(self):
        state = _state()
        state.identified_fallacies["f3"] = {
            "type": "Procédé orphelin",
            "justification": "Cible non résolue.",
        }
        evidence = build_act2_evidence(state)
        assert evidence.unattributed_fallacies == 1
        assert evidence.fallacies_total == 2
