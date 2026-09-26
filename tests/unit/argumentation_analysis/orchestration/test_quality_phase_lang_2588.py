# -*- coding: utf-8 -*-
"""#2588 review-2 — la langue se décide sur le DOCUMENT, pas sur l'unité jugée.

Sur l'arbre d'avant ce correctif, ``_invoke_quality_evaluator`` évalue chaque
argument extrait sans ``lang``. L'unité qu'elle juge est une claim courte : sous
le seuil du détecteur, sa clarté tombe sur l'heuristique « mots courts » au lieu
de la formule Flesch — alors que le document est dans la main de la phase, c'est
``input_text``. Un vrai run perd donc la mesure sur les arguments courts, ceux
qui sont précisément le sujet de #2588.

Témoins mesurés ici :
- une claim anglaise courte (5 mots, détecteur muet) dans un document anglais →
  ``Lisibilité (Flesch en, langue du document)``, jamais l'heuristique ;
- contre-pendule : sans langue décidable (document ET unité muets), l'heuristique
  NOMMÉE reste — on n'invente pas une langue pour remplir la case.

Aucun LLM : le bras agentic et l'enrichissement sont ramenés au chemin lexical
nommé (même montage que #2403) — zéro egress réseau.
"""

import asyncio
from typing import Any, Dict
from unittest.mock import patch

from argumentation_analysis.orchestration.invoke_callables import (
    _invoke_quality_evaluator,
)

EN_DOCUMENT = (
    "The report states that the reform cut unemployment by two points. "
    "However, the economists quoted by the local newspaper dispute the "
    "calculation method, because the survey leaves out job seekers in "
    "training. Finally, the author concludes that the debate remains open "
    "and invites the reader to review the raw data to form an opinion."
)

# 5 mots : mesuré « unknown » par le détecteur (le seuil est de 3 mots-outils),
# et Flesch en 100.24 sous les règles anglaises contre l'heuristique « mots
# courts » quand aucune langue n'est décidée.
SHORT_EN_ARGUMENT = "Taxes must be cut now."

# Citation absente du document → l'unité jugée est la claim seule (la
# localisation échoue), donc courte : c'est exactement le cas du défaut.
NOT_IN_DOCUMENT = "a sentence that appears nowhere in the source document"


def _run(input_text: str, args: list) -> Dict[str, Any]:
    async def _no_enrichment(*_a, **_k):
        # #290 — la passe d'enrichissement LLM existe ; elle n'est pas l'objet
        # de ces témoins et le gate unitaire exige zéro egress réseau.
        return None

    with patch(
        "argumentation_analysis.orchestration.invoke_callables"
        "._make_agentic_llm_callable",
        return_value=(None, "no_route", ""),
    ), patch(
        "argumentation_analysis.orchestration.invoke_callables" "._llm_enrich_quality",
        side_effect=_no_enrichment,
    ):
        return asyncio.run(
            _invoke_quality_evaluator(
                input_text, {"phase_extract_output": {"arguments": args}}
            )
        )


def _clarte_comment(output: Dict[str, Any], arg_id: str = "arg_1") -> str:
    return output["per_argument_scores"][arg_id]["rapport_detaille"]["clarte"]


def test_short_argument_inherits_the_document_flesch_scale():
    """Le témoin demandé au 2ᵉ tour : la formule du document, pas l'heuristique."""
    output = _run(
        EN_DOCUMENT, [{"text": SHORT_EN_ARGUMENT, "source_quote": NOT_IN_DOCUMENT}]
    )
    comment = _clarte_comment(output)
    assert "Flesch en" in comment, comment
    assert "langue du document" in comment, comment
    assert "heuristique" not in comment, comment


def test_no_decidable_language_keeps_the_named_heuristic():
    """Contre-pendule : document muet → l'heuristique nommée, jamais une langue inventée."""
    output = _run(
        "zzqq xxvv. kkww jjff.",
        [{"text": SHORT_EN_ARGUMENT, "source_quote": NOT_IN_DOCUMENT}],
    )
    comment = _clarte_comment(output)
    assert "heuristique" in comment, comment
    assert "langue du document" not in comment, comment
