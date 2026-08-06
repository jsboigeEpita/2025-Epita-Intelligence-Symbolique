"""#1617 — a missing act must not have its precise degradation motif thrown away.

When an act is missing (empty narrative), the renderer used to print a
hard-coded wording and ``continue`` past the degraded branch — so the *precise*
reason the act is missing (filed in ``acts.degraded``) never reached the reader.

For Acte III the hard-coded wording named a cause — *« portes G1–G4 non
évaluées »* — that is **false on all three real paths** that produce a missing
act (verified firsthand in ``act3_conclusion_plugin.build_act3_conclusion``):

* ``empty_state`` (l.1509) — G1 WAS evaluated (and failed); the real cause is
  *« Aucun argument extrait »*.
* no LLM injected (l.1521) — the gates passed; the real cause is
  *« aucun LLM injecté »*.
* LLM produced nothing (l.1547) — gates passed, LLM called; the real cause is
  *« le LLM n'a rien produit »*.

The fix: the hard-coded wording *cedes the floor* to the precise motif when one
exists, and is itself made honest-generic (no false cause named). The
``continue`` stays in place — a missing act must not also pass through the
"thin act" check (``min_act_chars``), which would count 0 chars and add
misleading noise.

The same mechanism covers Acte I and Acte II — verified firsthand: both have
missing-with-degraded return paths in their generators
(``act1_framing_plugin`` l.570/583, ``act2_narrative_plugin`` l.1294/1306/1318),
so the defect is NOT specific to Acte III (contrary to the issue body's guess
that act1/act2 were "sains"). The fix is generic in the renderer's per-act
loop. This contradicts the parallel drawn with #1615: #1615 was about motif
flattening at ``_read_act_degraded``; #1617 is about the renderer's ``continue``
short-circuit — a different mechanism that hits all three acts.

Falsifiability — ``test_three_missing_paths_produce_distinct_renders`` asserts
the three renders DIFFER. On the pre-fix code they are identical (the motif is
dropped, the same hard-coded wording is printed for all three), so the
inequalities fail. Degenerate substitution: delete the
``acts.degraded.get(key)`` lookup in the renderer's missing-act branch → all
three renders collapse to the generic wording again → the test fails.

Anti-pendule: ``_MISSING_ACT_WORDING`` is NOT removed — it stays as the generic
fallback when no motif was recorded (an act never invoked produces none).
"""

from __future__ import annotations

from argumentation_analysis.reporting.restitution.acts import RestitutionActs
from argumentation_analysis.reporting.restitution.renderer import (
    RestitutionReportRenderer,
)

# The exact motifs ``build_act3_conclusion`` records on the three missing-act
# paths (act3_conclusion_plugin.py:1509/1521/1547). Using the real strings, not
# paraphrases — the test must break if the plugin rewording drifts.
_ACT3_MISSING_MOTIFS = {
    "empty_state": (
        "Aucun argument extrait — l'Acte III n'a pas de substrat à conclure "
        "(G1 échoué : identified_arguments vide)."
    ),
    "llm_absent": (
        "Conclusion non conduite — aucun LLM injecté pour l'Acte III "
        "(fail-loud, #1108)."
    ),
    "llm_mute": (
        "Conclusion indisponible — le LLM n'a rien produit (fail-loud, #1108)."
    ),
}

# The hard-coded cause the renderer used to print unconditionally for a missing
# Acte III — false on all three paths above (G1 is evaluated, not "non évaluée").
_FALSE_ACT3_CAUSE = "portes G1–G4 non évaluées"


def _acts_with_missing_act3(motif: str) -> RestitutionActs:
    """Three-act bundle with Acte III missing and a precise motif recorded."""
    return RestitutionActs(
        act1_framing="Cadre woven suffisamment long pour éviter le seuil min_act_chars.",
        act2_narrative="Récit dialectique woven suffisamment long pour le seuil.",
        act3_conclusion="",
        source_id="doc_A",
        degraded={"act3_conclusion": motif},
    )


class TestMissingActMotifCeded:
    """A missing act with a recorded motif prints the motif, not a false cause."""

    def test_three_missing_paths_produce_distinct_renders(self) -> None:
        """The three real missing-act paths render to DISTINCT markdown.

        The assertion is on the DIFFERENCE between renders, not on the presence
        of any particular word. On the pre-fix code the three renders are
        identical (the motif is dropped, the same hard-coded wording is printed),
        so these inequalities fail — that is the defect.
        """
        renders = {
            path: RestitutionReportRenderer()
            .render(_acts_with_missing_act3(motif))
            .markdown
            for path, motif in _ACT3_MISSING_MOTIFS.items()
        }
        assert renders["empty_state"] != renders["llm_absent"]
        assert renders["empty_state"] != renders["llm_mute"]
        assert renders["llm_absent"] != renders["llm_mute"]

    def test_missing_act_with_motif_prints_the_motif(self) -> None:
        """The precise motif reaches the reader (here: the empty_state path)."""
        acts = _acts_with_missing_act3(_ACT3_MISSING_MOTIFS["empty_state"])
        md = RestitutionReportRenderer().render(acts).markdown
        assert "Aucun argument extrait" in md

    def test_missing_act_with_motif_does_not_name_false_cause(self) -> None:
        """The hard-coded false cause is gone when a real motif exists."""
        acts = _acts_with_missing_act3(_ACT3_MISSING_MOTIFS["empty_state"])
        md = RestitutionReportRenderer().render(acts).markdown
        assert _FALSE_ACT3_CAUSE not in md

    def test_missing_act_without_motif_uses_generic_fallback(self) -> None:
        """No motif recorded → generic honest wording (an act never invoked).

        ``_MISSING_ACT_WORDING`` stays — but honest: it names the missing act
        without naming a cause it did not observe.
        """
        acts = RestitutionActs(
            act1_framing="Cadre woven suffisamment long pour le seuil.",
            act2_narrative="Récit dialectique woven suffisamment long pour le seuil.",
            act3_conclusion="",
            source_id="doc_A",
            degraded={},
        )
        md = RestitutionReportRenderer().render(acts).markdown
        assert "Acte III indisponible" in md
        assert _FALSE_ACT3_CAUSE not in md


class TestMissingActTwinsAct1Act2:
    """The same mechanism covers Acte I and Acte II (verified firsthand).

    Both have missing-with-degraded return paths in their generators, so the
    renderer's ``continue`` short-circuit dropped their motifs too. The fix is
    generic in the per-act loop, so it covers them without per-act code.
    """

    def test_missing_act1_cedes_to_its_motif(self) -> None:
        acts = RestitutionActs(
            act1_framing="",
            act2_narrative="Récit dialectique woven suffisamment long pour le seuil.",
            act3_conclusion="Conclusion woven suffisamment long pour le seuil.",
            source_id="doc_A",
            degraded={
                "act1_framing": (
                    "Cadrage non conduit — aucun LLM injecté pour l'Acte I "
                    "(fail-loud, #1108)."
                )
            },
        )
        md = RestitutionReportRenderer().render(acts).markdown
        assert "Cadrage non conduit" in md
        # the disjunctive hard-coded wording ("non câblé ou en échec") cedes
        assert "non câblé ou en échec" not in md

    def test_missing_act2_cedes_to_its_motif(self) -> None:
        acts = RestitutionActs(
            act1_framing="Cadre woven suffisamment long pour le seuil.",
            act2_narrative="",
            act3_conclusion="Conclusion woven suffisamment long pour le seuil.",
            source_id="doc_A",
            degraded={
                "act2_narrative": (
                    "Aucun argument extrait — l'Acte II n'a pas de substrat "
                    "argumentatif à narrer (identified_arguments vide)."
                )
            },
        )
        md = RestitutionReportRenderer().render(acts).markdown
        assert "Aucun argument extrait" in md
        # the hard-coded wording ("cœur narratif absent") cedes
        assert "cœur narratif absent" not in md
