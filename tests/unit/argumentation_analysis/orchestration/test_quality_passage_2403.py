# -*- coding: utf-8 -*-
"""
#2403 — né-rouge : la phase qualité juge la claim PLUS le passage source.

Sur l'arbre pristine (avant le correctif), ces tests rougissent **en
valeurs** : la phase évalue ``arg["text"]`` seul (la paraphrase de
l'extracteur), laisse l'évaluateur deviner le niveau de contexte depuis la
longueur — une paraphrase courte condamne les 7 vertus structurelles au
NOT_APPLICABLE, quand bien même le document entier est disponible. La
présence des vertus dépendait de la verbosité de la session d'extraction,
pas du document.

Correctif mesuré ici :
- ``output["passage_basis"]["claim_and_passage"]`` ≥ 1 quand la citation se
  localise (clé absente sur pristine → rouge en valeurs) ;
- ``result["contexte_evalue"] == 2`` (LOCAL_CONTEXT **déclaré**) pour une
  paraphrase d'UNE phrase (< 30 mots) — pristine devine CLAIM (1) → rouge ;
- ``structure_logique`` évaluée (présente dans ``scores_par_vertu``) —
  pristine la déclare NOT_APPLICABLE → rouge ;
- citation non localisable → l'unité RESTE CLAIM (comportement conservé,
  compté dans ``claim_only``) ;
- la reprise lexical dégradée juge le même objet (niveau préservé).

Aucun LLM : ``_make_agentic_llm_callable`` est forcé à la baisse (bras
lexical, le chemin nommé de la phase). Lexical local uniquement.
"""

import asyncio
from typing import Any, Dict
from unittest.mock import patch

from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_quality_evaluator,
)

LOCAL_CONTEXT = 2
CLAIM = 1

SOURCE = (
    "Le rapport affirme que la réforme a réduit le chômage de deux points. "
    "Cependant, les économistes cités par le journal local contestent la "
    "méthode de calcul, car l'enquête exclut les demandeurs d'emploi en "
    "formation. Enfin, l'auteur conclut que le débat reste ouvert, et il "
    "invite le lecteur à relire les données brutes pour se faire son avis. "
    "Cette conclusion prudente contraste avec le titre catégorique."
)

SHORT_PARAPHRASE = (
    "L'auteur présente la réforme comme efficace."  # 7 mots, 1 phrase : CLAIM inféré
)
LOCATABLE_QUOTE = (
    "les économistes cités par le journal local contestent la méthode de calcul"
)
ABSENT_QUOTE = "cette citation ne figure nulle part dans le texte source"


def _context(args: list) -> Dict[str, Any]:
    return {"phase_extract_output": {"arguments": args}}


def _run(args: list) -> Dict[str, Any]:
    async def _no_enrichment(*_a, **_k):
        # #290 — la passe d'enrichissement LLM existe ; elle n'est pas
        # l'objet de ces tests et le gate unitaire exige zéro egress
        # réseau (#1787/#2446).
        return None

    with patch(
        "argumentation_analysis.orchestration.invoke_callables"
        "._make_agentic_llm_callable",
        return_value=(None, "no_route", ""),
    ), patch(
        "argumentation_analysis.orchestration.invoke_callables" "._llm_enrich_quality",
        side_effect=_no_enrichment,
    ):
        return asyncio.run(_invoke_quality_evaluator(SOURCE, _context(args)))


def test_located_quote_declares_local_context_on_a_short_paraphrase():
    output = _run([{"text": SHORT_PARAPHRASE, "source_quote": LOCATABLE_QUOTE}])
    assert output["passage_basis"]["claim_and_passage"] == 1, (
        "la citation se localise : l'unité doit être jugée sur claim+passage, "
        f"base mesurée = {output.get('passage_basis')}"
    )
    unit = output["per_argument_scores"]["arg_1"]
    assert int(unit["contexte_evalue"]) == LOCAL_CONTEXT, (
        "niveau DÉCLARÉ LOCAL_CONTEXT (#2403) ; sur une paraphrase de 7 mots "
        "l'inférence par longueur rendrait CLAIM"
    )
    assert unit["evaluated_on"] == "claim+passage"


def test_structural_virtue_is_evaluated_not_absent():
    output = _run([{"text": SHORT_PARAPHRASE, "source_quote": LOCATABLE_QUOTE}])
    unit = output["per_argument_scores"]["arg_1"]
    scores = unit.get("scores_par_vertu") or {}
    statuses = unit.get("statuts_par_vertu") or {}
    assert "structure_logique" in scores, (
        "structure_logique exige un passage local (#1907) : jugée sur "
        f"claim+passage elle doit être ÉVALUÉE, statut mesuré = "
        f"{statuses.get('structure_logique')}"
    )


def test_unlocatable_quote_leaves_the_unit_claim_and_counts_it():
    output = _run([{"text": SHORT_PARAPHRASE, "source_quote": ABSENT_QUOTE}])
    assert output["passage_basis"]["claim_only"] == 1
    unit = output["per_argument_scores"]["arg_1"]
    assert int(unit["contexte_evalue"]) == CLAIM
    assert unit["evaluated_on"] == "claim"


def test_short_quote_is_not_located_by_decree():
    # Une citation de 3 mots ne prouve rien : pas de passage fabriqué.
    output = _run([{"text": SHORT_PARAPHRASE, "source_quote": "réforme chômage"}])
    assert output["passage_basis"]["claim_only"] == 1


def test_no_quote_stays_claim():
    output = _run([{"text": SHORT_PARAPHRASE}])
    assert output["passage_basis"]["claim_only"] == 1


def test_wiring_untouched_by_the_passage_basis():
    output = _run([{"text": SHORT_PARAPHRASE, "source_quote": LOCATABLE_QUOTE}])
    wiring = output["agentic_wiring"]
    assert wiring["mode"].startswith("degraded_")
    assert wiring["units_evaluated"] == 1
    assert wiring["units_degraded"] == {}
