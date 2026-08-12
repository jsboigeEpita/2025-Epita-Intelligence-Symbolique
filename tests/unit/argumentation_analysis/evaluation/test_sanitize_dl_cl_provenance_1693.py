"""#1693 — DL/CL input provenance carried through, then scrubbed on export.

Two layers, both tested here:

1. **Producer** (``_invoke_dl``/``_invoke_cl``): the input ontology /
   conditionals the reasoner worked over are returned in the output dict
   (named ``input_ontology``/``input_conditionals`` — provenance, not result).
2. **Export** (``sanitize_state`` pass 5f): the ``formalism_specific`` sidecar
   on ``fol_analysis_results`` (DL) and ``propositional_analysis_results`` (CL)
   is opacified — the axiom text is source-derived (NL→DL/CL translation of
   claim text), so it must not survive an export. Topology (list arity)
   survives, so downstream counts are unaffected.

Privacy: opaque synthetic atoms only (no corpus text).
"""

from __future__ import annotations

from unittest.mock import patch

from argumentation_analysis.evaluation.sanitize_state import sanitize_state

# ─────────────────────────────────────────────────────────────────────────────
# Producer — the invoke now carries the input ontology / conditionals.
# ─────────────────────────────────────────────────────────────────────────────


class TestInvokeDlCarriesOntology1693:
    """_invoke_dl returns the input ontology (provenance), not just counts."""

    async def test_invoke_dl_carries_input_ontology(self) -> None:
        from argumentation_analysis.orchestration import invoke_callables

        with (
            patch(
                "argumentation_analysis.agents.core.logic.dl_handler.DLHandler"
            ) as DLH,
            patch(
                "argumentation_analysis.agents.core.logic.tweety_initializer."
                "TweetyInitializer"
            ),
        ):
            handler = DLH.return_value
            handler.create_knowledge_base.return_value = object()
            # is_consistent is called via asyncio.to_thread (sync); return the
            # (verdict, message) tuple directly.
            handler.is_consistent.return_value = (True, "consistent")

            result = await invoke_callables._invoke_dl(
                "unused",
                {
                    "tbox": ["synthetic_axiom_1"],
                    "abox_concepts": ["synthetic_concept_a"],
                    "abox_roles": ["synthetic_role_r"],
                },
            )

        assert result["consistent"] is True
        ontology = result["input_ontology"]
        assert ontology["tbox"] == ["synthetic_axiom_1"], ontology
        assert ontology["abox_concepts"] == ["synthetic_concept_a"], ontology
        assert ontology["abox_roles"] == ["synthetic_role_r"], ontology
        # The counts the writer still carries ride alongside (unchanged).
        assert result["tbox_size"] == 1 and result["abox_size"] == 2


class TestInvokeClCarriesConditionals1693:
    """_invoke_cl returns the input conditionals (provenance), not just a count."""

    async def test_invoke_cl_carries_input_conditionals(self) -> None:
        from argumentation_analysis.orchestration import invoke_callables

        with (
            patch(
                "argumentation_analysis.agents.core.logic.cl_handler.CLHandler"
            ) as CLH,
            patch(
                "argumentation_analysis.agents.core.logic.tweety_initializer."
                "TweetyInitializer"
            ),
        ):
            handler = CLH.return_value
            handler.create_knowledge_base.return_value = object()
            handler.query.return_value = (False, "not entailed")

            result = await invoke_callables._invoke_cl(
                "unused",
                {
                    "conditionals": ["synthetic_cond_1 => synthetic_cond_2"],
                    "query_conclusion": "synthetic_conclusion",
                    "query_premise": None,
                },
            )

        assert result["entailed"] is False
        assert result["input_conditionals"] == [
            "synthetic_cond_1 => synthetic_cond_2"
        ], result
        assert result["num_conditionals"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# Export — pass 5f opacifies the DL/CL provenance sidecar on FOL/PL containers.
# ─────────────────────────────────────────────────────────────────────────────


class TestSanitizeDlClProvenanceSidecar1693:
    """The fol/pl ``formalism_specific`` sidecar leaves are opacified (pass 5f)."""

    def test_dl_tbox_abox_opacified_topology_preserved(self) -> None:
        out = sanitize_state(
            {
                "fol_analysis_results": [
                    {
                        "id": "fol_1",
                        "formulas": ["DL: msg"],
                        "consistent": True,
                        "formalism_specific": {
                            "tbox": ["synthetic_axiom_alpha", "synthetic_axiom_beta"],
                            "abox_concepts": ["synthetic_concept_gamma"],
                            "abox_roles": ["synthetic_role_delta"],
                        },
                    }
                ]
            }
        )
        side = out["fol_analysis_results"][0]["formalism_specific"]
        # Topology preserved: list arity survives.
        assert len(side["tbox"]) == 2, side
        assert len(side["abox_concepts"]) == 1, side
        assert len(side["abox_roles"]) == 1, side
        # Content opacified: no synthetic- atom survives verbatim.
        flat = side["tbox"] + side["abox_concepts"] + side["abox_roles"]
        assert all("synthetic_" not in str(a) for a in flat), flat

    def test_cl_conditionals_opacified_topology_preserved(self) -> None:
        out = sanitize_state(
            {
                "propositional_analysis_results": [
                    {
                        "id": "pl_1",
                        "formulas": ["CL(2 conditionals): ok"],
                        "satisfiable": True,
                        "formalism_specific": {
                            "conditionals": [
                                "synthetic_cond_1 => synthetic_cond_2",
                                "synthetic_cond_3",
                            ]
                        },
                    }
                ]
            }
        )
        side = out["propositional_analysis_results"][0]["formalism_specific"]
        assert len(side["conditionals"]) == 2, side  # arity preserved
        assert all("synthetic_" not in str(c) for c in side["conditionals"]), side[
            "conditionals"
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Substitution control on the real input — empty vs non-empty TBox.
# ─────────────────────────────────────────────────────────────────────────────


class TestDlClProvenanceDistinguishableDownstream1693:
    """DoD item 4: an empty and a non-empty TBox produce two distinguishable
    states downstream. If the figure does not move, say so in the PR."""

    def test_empty_vs_nonempty_ontology_produce_distinguishable_sidecars(self) -> None:
        from argumentation_analysis.core.shared_state import UnifiedAnalysisState
        from argumentation_analysis.orchestration.state_writers import (
            _write_dl_to_state,
        )

        def _build(ontology_present: bool) -> dict:
            state = UnifiedAnalysisState("dl-1693 probe")
            output = {
                "consistent": True,
                "message": "m",
                "tbox_size": 1 if ontology_present else 0,
                "abox_size": 0,
            }
            if ontology_present:
                output["input_ontology"] = {
                    "tbox": ["synthetic_axiom"],
                    "abox_concepts": [],
                    "abox_roles": [],
                }
            _write_dl_to_state(output, state, {})
            entry = state.fol_analysis_results[-1]
            return entry.get("formalism_specific", {})

        empty_sidecar = _build(ontology_present=False)
        full_sidecar = _build(ontology_present=True)

        # The two states ARE distinguishable downstream: the empty-TBox run has
        # no sidecar, the non-empty one carries the axiom. (Reverting the writer
        # to always-attach would collapse the two — the theatre guard #1019.)
        assert empty_sidecar == {}, empty_sidecar
        assert full_sidecar.get("tbox") == ["synthetic_axiom"], full_sidecar
