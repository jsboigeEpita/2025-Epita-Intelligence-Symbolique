"""#3547 — the counterfactual axis is READ from the render, not labelled.

The counting rule that declared « 1 of 9 rendered » read labels and markers
the render structurally cannot carry (the Act III prompt forbids echoing
them). The State of 18/11 re-read the 6 recorded Act III renders by hand and
found the fact itself — what supports what, and what falls if the support
goes — present in every render that has an entry, in paraphrased forms. That
table was ONE reader's judgment; this instrument makes it reproducible.

What is witnessed here, with no key, no network and no corpus (fixtures are
synthetic French carrying the same grammatical forms):

- the three dependence forms fire: the support verb (``A soutient B``), the
  reflexive rests-on (``s'appuie sur``), and the plain rests-on — including
  the comma-interrupted variant (``repose, dit-il, sur``);
- the thesis verb (``il soutient que …``) does NOT fire — a thesis is not a
  support relation — and neither does the past participle (``soutenue par``);
- run-metadata sentences (``le socle du run repose sur``) are excluded: the
  run's base is not a document-internal support relation;
- the sole-support markers (``à lui seul``, ``seule justification``) raise
  their own flag;
- the consequence fires only on a counterfactual operator: the withdrawal
  conditional (``si … disparaît, … perd …``) or the conditional-weakening
  form (``fragilisation … aurait des effets``). The present-tense
  ``fragilise``/``affaiblit`` and the bare noun ``fragilité`` do NOT fire —
  a present vulnerability is not the withdrawal chain;
- prose after the run-metadata markers (``**Verdict sur les vertus``) is out
  of scope: the axis lives in the analysis sections;
- the state side is censused too: the counterfactual entries the writer had
  (``jtms_counterfactual_withdrawals``) count beside the render reading, so
  one row shows what there was to render and what the render carries.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from panel.read_counterfactual_render_3547 import (  # noqa: E402
    read_counterfactual_state,
    read_render,
)


class TestDependenceForms:
    def test_support_verb_between_two_discourse_objects_fires(self):
        reading = read_render(
            "Le second axe soutient la conclusion du premier paragraphe."
        )
        assert reading.dependence is True
        assert "support_verb" in reading.dep_forms
        assert reading.dep_relations == 1

    def test_support_verb_plural_fires(self):
        reading = read_render(
            "Ces deux passages soutiennent la même lecture d'ensemble."
        )
        assert reading.dependence is True

    def test_two_relations_in_one_sentence_count_two(self):
        reading = read_render(
            "L'axe A soutient la thèse B, tandis que l'axe C soutient celle de D."
        )
        assert reading.dep_relations == 2

    def test_thesis_verb_que_does_not_fire(self):
        reading = read_render(
            "Dans ce texte, il soutient que la conclusion n'est pas définitive."
        )
        assert reading.dependence is False

    def test_past_participle_does_not_fire(self):
        reading = read_render(
            "C'est une préférence, soutenue par une large majorité des voies consultées."
        )
        assert reading.dependence is False

    def test_rests_on_reflexive_fires_both_apostrophes(self):
        straight = read_render(
            "Cette lecture s'appuie sur deux passages distincts du chapitre."
        )
        curly = read_render(
            "Cette lecture s’appuie sur deux passages distincts du chapitre."
        )
        assert straight.dependence is True
        assert "rests_on_reflexive" in straight.dep_forms
        assert curly.dependence is True

    def test_rests_on_plain_and_comma_interrupted_fire(self):
        plain = read_render("Cette lecture repose sur des exemples précis.")
        interrupted = read_render(
            "Cette lecture repose, dit-il, sur des exemples précis du même ordre."
        )
        assert plain.dependence is True
        assert interrupted.dependence is True
        assert "rests_on" in interrupted.dep_forms


class TestScoping:
    def test_run_metadata_sentence_is_excluded(self):
        reading = read_render(
            "Le socle du run repose sur des segments du texte entier."
        )
        assert reading.dependence is False

    def test_same_sentence_without_the_run_word_fires(self):
        reading = read_render(
            "Le socle du raisonnement repose sur des segments du texte entier."
        )
        assert reading.dependence is True

    def test_prose_after_the_verdict_marker_is_out_of_scope(self):
        render = (
            "### Ce qui tient\nUn paragraphe d'analyse sans forme de soutien.\n\n"
            "**Verdict sur les vertus (chiffres du pipeline)**\n"
            "L'axe A soutient la thèse B ici, mais dans la section des chiffres.\n"
        )
        reading = read_render(render)
        assert reading.dependence is False

    def test_prose_after_the_reading_bounds_marker_is_out_of_scope(self):
        render = (
            "Analyse liminaire.\n\n**Bornes de lecture du run**\n"
            "Le passage A soutient la conclusion B."
        )
        reading = read_render(render)
        assert reading.dependence is False

    def test_section_title_carrying_the_verb_does_not_fire(self):
        render = (
            "### Ce que le texte soutient réellement\n"
            "Le locuteur pose sa thèse liminaire sans relation interne."
        )
        reading = read_render(render)
        assert reading.dependence is False


class TestSoleSupport:
    def test_a_lui_seul_raises_the_sole_flag(self):
        reading = read_render(
            "L'argument des halles couvertes soutient à lui seul l'idée d'une relocalisation."
        )
        assert reading.sole_support is True
        assert reading.dependence is True

    def test_seule_justification_raises_the_sole_flag(self):
        reading = read_render(
            "Si cette prémisse est retirée, la conclusion perd sa seule justification."
        )
        assert reading.sole_support is True

    def test_sufficiency_idiom_does_not_raise_the_sole_flag(self):
        reading = read_render(
            "La thèse ne suffit pas, à elle seule, à établir la conclusion."
        )
        assert reading.sole_support is False

    def test_plain_support_does_not_raise_the_sole_flag(self):
        reading = read_render("L'axe A soutient la thèse B.")
        assert reading.sole_support is False


class TestConsequenceForms:
    def test_withdrawal_conditional_fires(self):
        reading = read_render(
            "Si le passage fondateur disparaît, la thèse voisine perd son appui direct."
        )
        assert reading.consequence is True
        assert "withdrawal_conditional" in reading.cons_forms

    def test_conditional_weakening_fires(self):
        reading = read_render(
            "Leur fragilisation engendrerait des glissements successifs sur l'ensemble."
        )
        assert reading.consequence is True
        assert "conditional_weakening" in reading.cons_forms

    def test_present_tense_fragilise_does_not_fire(self):
        reading = read_render(
            "Le cadre ne retient pas cette position : cela fragilise la thèse citée."
        )
        assert reading.consequence is False

    def test_present_tense_affaiblit_does_not_fire(self):
        reading = read_render(
            "cela affaiblit la position citée ou combattue dans le texte."
        )
        assert reading.consequence is False

    def test_bare_noun_fragilite_does_not_fire(self):
        reading = read_render(
            "C'est une fragilité de la charpente, pas une invalidation complète."
        )
        assert reading.consequence is False

    def test_withdrawal_without_fall_effect_does_not_fire(self):
        reading = read_render("Si le passage disparaît, le reste demeure lisible.")
        assert reading.consequence is False


class TestStateCensus:
    def _state_file(self, tmp_path: Path, entries: list) -> Path:
        state = {"jtms_counterfactual_withdrawals": entries}
        path = tmp_path / "state_full_example.json"
        path.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        return path

    def test_entries_are_censused_beside_the_reading(self, tmp_path):
        entries = [
            {"text": "prémisse A", "falls": [{"text": "chute 1"}]},
            {"text": "prémisse B", "falls": [{"text": "chute 2"}]},
        ]
        path = self._state_file(tmp_path, entries)
        reading = read_counterfactual_state(path, render="Prose sans forme.")
        assert reading.entries == 2
        assert reading.dependence is False

    def test_missing_key_reads_zero_entries(self, tmp_path):
        path = self._state_file(tmp_path, [])
        reading = read_counterfactual_state(path, render="Prose sans forme.")
        assert reading.entries == 0


class TestEndToEndSynthetic:
    def test_full_synthetic_render_reads_both_halves(self):
        render = (
            "### Ce que le texte soutient\n"
            "Le locuteur pose sa thèse liminaire.\n\n"
            "### Ce qui tient, et ce qui dérape\n"
            "L'axe des relevés soutient la conclusion liminaire, tandis que "
            "l'axe des notations soutient celui du prolongement.\n\n"
            "### Comment se faire son avis\n"
            "L'analyse éclaire les dépendances : l'axe des relevés "
            "soutient à lui seul l'idée du prolongement, et l'axe des "
            "notations soutient celui de la conclusion ; leur "
            "fragilisation engendrerait des glissements successifs.\n\n"
            "**Verdict sur les vertus (chiffres du pipeline)**\n"
            "Le texte tient sur pertinence."
        )
        reading = read_render(render)
        assert reading.dependence is True
        assert reading.sole_support is True
        assert reading.consequence is True
        assert reading.dep_relations == 4

    def test_render_without_any_form_reads_all_false(self):
        render = (
            "### Ce qui tient\nLe texte est cohérent comme récit d'apprentissage.\n"
        )
        reading = read_render(render)
        assert reading.dependence is False
        assert reading.sole_support is False
        assert reading.consequence is False
        assert reading.dep_relations == 0
        assert reading.dep_forms == ()
        assert reading.cons_forms == ()
