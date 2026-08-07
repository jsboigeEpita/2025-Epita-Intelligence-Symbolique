"""#1648 — Regression tests pinning the flattening contract for state writers.

Each test stubs the corresponding handler (to avoid JVM/Tweety dependency) and
drives the real ``_write_*_to_state`` writer. The assertion reads back through
the canonical ``state.<container>`` — so the test fails today precisely where
the writer drops distinctive information.

Anti-#1019 discipline (R761 #1643, R764 #1636, R765 #1662): the writer is
real, the handler is stubbed. A mocked writer would just agree with itself.

Privacy: synthetic atoms only (no corpus tokens).
"""

from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import patch

import pytest

from argumentation_analysis.core.shared_state import UnifiedAnalysisState
from argumentation_analysis.orchestration.state_writers import (
    _write_aba_to_state,
    _write_adf_to_state,
    _write_cl_to_state,
    _write_delp_to_state,
    _write_dl_to_state,
    _write_eaf_to_state,
    _write_qbf_to_state,
    _write_setaf_to_state,
    _write_social_to_state,
    _write_weighted_to_state,
)


def _new_state() -> UnifiedAnalysisState:
    """A fresh state for a single writer probe."""
    return UnifiedAnalysisState("flattening-1648 synthetic probe")


# ─────────────────────────────────────────────────────────────────────────────
# ABA — handler drops contraries, writer drops attacks (Section 2.1)
# ─────────────────────────────────────────────────────────────────────────────


class TestAbaFlattening1648:
    """ABA writer must surface contraries (or contrary-derived attacks) somewhere.

    Section 2.1: ``handler.analyze_aba_framework`` consumes ``contraries`` at
    ``invoke_callables.py:3610,3640`` but does NOT return them. The writer then
    hard-codes ``attacks=[]`` (state_writers.py:843). A reader aggregating
    attacks sees zero — and ABA cannot refute anything via this projection.

    #1648 Wave-2 site 1 (this PR): the handler now echoes ``contraries`` in its
    return dict and the writer attaches a strictly-additive
    ``formalism_specific`` sidecar. The 12 readers of ``dung_frameworks`` see
    the same ``attacks=[]`` and ``extensions={"aba_extensions": [...]}`` as
    before — only readers that look for ``formalism_specific["contraries"]``
    pick up the new signal. ABA still cannot refute anything via the Dung
    projection, but it can be refuted via its own contraries.

    Pin: today's expected behaviour on the test stub is that the contraries
    that the *real* handler would echo now reach the state via the sidecar.
    The xfail markers were removed when the fix landed (the strict=True
    contract I posed in #1672 R767 would otherwise flip the test to a
    strict failure as soon as it passed).
    """

    def _stub_handler_output(self) -> Dict[str, Any]:
        """Mimic the post-fix handler output.

        Pre-fix the handler returned ``{semantics, extensions, assumptions,
        rules_count, statistics}`` only — the test then proved the loss.
        Post-fix the handler echoes ``contraries`` and the writer must carry
        it forward unchanged.
        """
        return {
            "semantics": "preferred",
            "extensions": [["a", "b"], ["a", "c"]],
            "assumptions": ["a", "b", "c"],
            "rules_count": 2,
            "contraries": {"a": "b", "b": "a", "c": "a"},
            "statistics": {
                "assumptions_count": 3,
                "rules_count": 2,
                "extensions_count": 2,
            },
        }

    def test_aba_writer_preserves_contraries_or_derived_attacks(self) -> None:
        state = _new_state()
        output = self._stub_handler_output()
        ctx = {"contraries": {"a": "b", "b": "a", "c": "a"}}

        _write_aba_to_state(output, state, ctx)

        # The frame is keyed by a generated id (df_001), not by the 'name' field.
        # Fetch the entry the same way the rest of the inventory does.
        entry = next(iter(state.dung_frameworks.values()))
        # The diagnostic: writer stored no attacks despite contraries being
        # genuine structured input. Wave-2 keeps ``attacks=[]`` (the Dung
        # projection still has no slot for contrary-derived attacks — that is
        # a separate, harder problem); but the contraries themselves must
        # reach the state so a downstream reader can derive attacks.
        attacks: List[List[str]] = entry.get("attacks", [])
        assert attacks == [], (
            "ABA writer must keep ``attacks=[]`` for the Dung projection — "
            "the sidecar carries the contraries. Got non-empty: "
            f"{attacks!r}"
        )

    def test_aba_writer_or_sidecar_carries_contraries(self) -> None:
        """Stretch assertion: even if `attacks` stays empty, the contraries
        themselves must reach the state (via extensions or a sidecar)."""
        state = _new_state()
        output = self._stub_handler_output()
        ctx = {"contraries": {"a": "b", "b": "a", "c": "a"}}

        _write_aba_to_state(output, state, ctx)

        entry = next(iter(state.dung_frameworks.values()))
        # Look for contraries anywhere the state carries them today or
        # in the new formalism-specific sidecar.
        extensions = entry.get("extensions", {})
        formalism_specific = entry.get("formalism_specific", {})
        has_contraries = (
            "contraries" in extensions
            or "contraries" in formalism_specific
            or extensions.get("aba_extensions") == ctx["contraries"]
        )
        assert has_contraries, (
            "ABA writer dropped contraries from extensions/sidecar: "
            f"extensions={extensions!r}, formalism_specific={formalism_specific!r}"
        )
        # Sidecar shape is locked — a reader that wants the contraries
        # reads ``entry["formalism_specific"]["contraries"]``.
        assert formalism_specific.get("contraries") == ctx["contraries"], (
            "ABA writer did not mirror the handler's ``contraries`` mapping "
            f"into ``formalism_specific``: got {formalism_specific!r}, "
            f"expected {ctx['contraries']!r}"
        )

    def test_aba_real_handler_round_trip_preserves_contraries(self) -> None:
        """Differential test: real handler (JVM-backed) → writer → state.

        This test exercises the **real** ``ABAHandler.analyze_aba_framework``
        — not a stub — so it proves the whole round trip on a real Tweety
        AbaTheory. It is the strongest form of anti-#1019 for this site:
        a mocked handler would just agree with itself, a real handler
        cannot.

        Pre-fix this test **fails** because the handler returns
        ``{semantics, extensions, assumptions, rules_count, statistics}``
        only — there is no ``contraries`` key in the output, the writer
        finds no ``contraries`` to mirror, and the sidecar stays absent.

        Post-fix the handler echoes ``contraries`` in its return dict and
        the writer mirrors it into ``formalism_specific``. The test passes.

        Skipped when the JVM is not initialised (CI environment without
        Java, or ``--disable-jvm-session`` flag). Marked ``jpype`` so the
        fail-loud guard #1385 still scans it (skip = expected, not a
        silent skip storm).
        """
        try:
            from argumentation_analysis.core.jvm_setup import initialize_jvm
            from argumentation_analysis.agents.core.logic.aba_handler import (
                ABAHandler,
            )
        except ImportError:
            pytest.skip("JVM/Tweety unavailable in this environment")

        if not initialize_jvm():
            pytest.skip("JVM not initialised — handler requires Tweety")

        handler = ABAHandler()
        contraries_in = {"a": "b", "b": "a", "c": "a"}
        output = handler.analyze_aba_framework(
            assumptions=["a", "b", "c"],
            rules=[
                {"head": "p", "body": ["a"]},
                {"head": "q", "body": ["b"]},
            ],
            contraries=contraries_in,
            semantics="preferred",
        )

        # Pre-fix this assertion fails — ``contraries`` is absent.
        assert output.get("contraries") == contraries_in, (
            "ABAHandler must echo the supplied ``contraries`` mapping in "
            f"its return dict (got {output.get('contraries')!r})"
        )

        state = UnifiedAnalysisState("ABA sidecar round-trip probe")
        _write_aba_to_state(output, state, {})
        entry = next(iter(state.dung_frameworks.values()))
        # Pre-fix the sidecar is absent; the assertion fires on main.
        assert entry.get("formalism_specific", {}).get("contraries") == contraries_in, (
            "ABA writer did not mirror the handler's ``contraries`` mapping "
            f"into ``formalism_specific``: got {entry.get('formalism_specific')!r}, "
            f"expected {contraries_in!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# SetAF — writer drops joint attacks that the handler returns (Section 2.3)
# ─────────────────────────────────────────────────────────────────────────────


class TestSetafFlattening1648:
    """SetAF handler returns joint attacks; writer hardcodes ``attacks=[]``.

    Section 2.3: ``handler.analyze_setaf`` returns ``attacks`` at
    ``setaf_handler.py:123`` as ``List[{attackers: List[str], target: str}]``.
    Writer at ``state_writers.py:1303-1341`` attaches them to a strictly
    additive ``formalism_specific`` sidecar (joint attacks don't fit the
    binary ``attacks`` projection).

    #1648 Wave-2 site 2 (this PR): the writer now mirrors the joint
    attacks into ``entry["formalism_specific"]["set_attacks"]``. The 12
    readers of ``dung_frameworks`` see the same ``attacks=[]`` and
    ``extensions={"setaf_extensions": [...]}`` as before — only readers
    that look for ``formalism_specific["set_attacks"]`` pick up the
    joint attacks. SetAF still cannot refute anything via the binary Dung
    projection, but it can be refuted via its own joint attacks in the
    sidecar.

    Pin: today's expected behaviour on the test stub is that the joint
    attacks that the *real* handler returns now reach the state via the
    sidecar. The xfail marker from #1672 R767 is removed (the
    strict=True contract would flip the test to a strict failure as
    soon as it passed).
    """

    def _stub_handler_output(self) -> Dict[str, Any]:
        """Mimic the post-#1679 handler output (returns ``attacks`` already)."""
        return {
            "semantics": "grounded",
            "arguments": ["a", "b", "c"],
            "attacks": [
                {"attackers": ["a", "b"], "target": "c"},
                {"attackers": ["a"], "target": "b"},
            ],
            "extensions": [["a"]],
            "extensions_count": 1,
            "statistics": {"arguments_count": 3, "attacks_count": 2},
        }

    def test_setaf_writer_attaches_set_attacks_sidecar(self) -> None:
        """Joint attacks survive in ``formalism_specific``.

        Pre-fix the writer dropped ``output["attacks"]`` on the floor:
        ``entry["attacks"]`` was ``[]`` (binary field — joint attacks
        don't fit) and the joint list was lost. Post-fix the writer
        attaches ``entry["formalism_specific"]["set_attacks"]`` mirroring
        the handler's output verbatim.
        """
        state = _new_state()
        output = self._stub_handler_output()

        _write_setaf_to_state(output, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        # Binary projection stays untouched — the Dung projection has
        # no slot for joint attacks, and the readers expect it empty.
        assert entry["attacks"] == [], (
            "SetAF writer must keep ``attacks=[]`` for the binary Dung "
            f"projection — the sidecar carries the joint attacks. "
            f"Got non-empty: {entry['attacks']!r}"
        )
        # The sidecar is present and carries the joint attacks verbatim.
        formalism_specific = entry.get("formalism_specific", {})
        assert formalism_specific.get("set_attacks") == output["attacks"], (
            "SetAF writer did not mirror the handler's joint attacks into "
            f"``formalism_specific.set_attacks``: got {formalism_specific!r}, "
            f"expected set_attacks={output['attacks']!r}"
        )

    def test_setaf_writer_omits_sidecar_when_handler_returns_empty_attacks(
        self,
    ) -> None:
        """An empty ``attacks`` list ⇒ no ``formalism_specific`` key.

        We don't synthesize a sidecar for empty input: an empty handler
        output is indistinguishable from a handler that never ran, and
        downstream readers should not see a phantom key.
        """
        state = _new_state()
        output = self._stub_handler_output()
        output["attacks"] = []
        output["statistics"]["attacks_count"] = 0

        _write_setaf_to_state(output, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        assert "formalism_specific" not in entry, (
            "SetAF writer must NOT attach ``formalism_specific`` when the "
            "handler returned no joint attacks — synthesising a sidecar "
            f"for empty input would mislead downstream readers. Got: {entry!r}"
        )

    def test_setaf_writer_drops_malformed_set_attack_entries(self) -> None:
        """Defensive: a malformed joint-attack entry (no ``attackers`` key
        or non-list ``attackers``) is dropped rather than crashing the
        writer boundary. Valid entries still pass through."""
        state = _new_state()
        output = self._stub_handler_output()
        output["attacks"] = [
            {"attackers": ["a", "b"], "target": "c"},     # valid
            {"target": "b"},                              # missing attackers
            {"attackers": "not-a-list", "target": "d"},   # wrong shape
            {"attackers": [], "target": "e"},             # empty set (valid)
        ]

        _write_setaf_to_state(output, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        formalism_specific = entry.get("formalism_specific", {})
        sanitised = formalism_specific.get("set_attacks", [])
        # Only the well-formed entries survive (the valid + the empty set).
        assert sanitised == [
            {"attackers": ["a", "b"], "target": "c"},
            {"attackers": [], "target": "e"},
        ], (
            "SetAF writer must drop malformed joint-attack entries "
            f"instead of crashing — got {sanitised!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# ADF — writer is correct (no binary attacks), but acceptance conditions
# are lost upstream of the writer (Section 2.2). This test pins the
# *current correct* behaviour on the writer and documents the upstream gap.
# ─────────────────────────────────────────────────────────────────────────────


class TestAdfFlattening1648:
    """ADF has no binary attacks — ``attacks=[]`` is the correct projection.

    Section 2.2: the writer's ``attacks=[]`` is formally correct. The
    distinctive ADF data (acceptance conditions, interpretations) is lost
    upstream of the writer. This test pins the writer-side contract so a
    future refactor that tries to "fix" ADF attacks breaks it visibly.
    """

    def test_adf_attacks_stay_empty_and_acceptance_conditions_acknowledged(self) -> None:
        state = _new_state()
        output = {
            "semantics": "grounded",
            "statements": ["p", "q"],
            "interpretations": ["{p=T,q=F}", "{p=F,q=F}"],
            "statistics": {"statements_count": 2, "interpretations_count": 2},
        }

        _write_adf_to_state(output, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        # Writer-side contract: attacks stay empty (ADF has none).
        assert entry["attacks"] == [], (
            f"ADF writer unexpectedly produced attacks={entry['attacks']!r}"
        )
        # Distinct ADF data (interpretations) IS preserved via extensions.
        # If a future refactor drops them, this assertion fires.
        assert "adf_models" in entry["extensions"], (
            f"ADF writer dropped interpretations: extensions={entry['extensions']!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Weighted — handler returns weights, writer drops them (Section 1.1 #4)
# ─────────────────────────────────────────────────────────────────────────────


class TestWeightedFlattening1648:
    """Weighted writer extracts only ``[src, tgt]`` from each attack dict.

    The handler returns ``output["attacks"]`` as ``List[{source, target, weight}]``
    but the writer at ``state_writers.py:1212-1226`` projects to ``[src, tgt]``
    pairs only. The weight is invisible to readers.
    """

    @pytest.mark.xfail(
        strict=True,
        reason="Pinning #1648 Wave-1 known loss (Weighted). Handler returns "
        "weights, writer projects to [src, tgt] only. Wave-2 fix.",
    )
    def test_weighted_writer_preserves_attack_weights(self) -> None:
        state = _new_state()
        output = {
            "semantics": "grounded",
            "arguments": ["a", "b", "c"],
            "attacks": [
                {"source": "a", "target": "b", "weight": 0.9},
                {"source": "b", "target": "c", "weight": 0.5},
            ],
            "extensions": [["a", "c"]],
        }

        _write_weighted_to_state(output, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        extensions = entry.get("extensions", {})
        formalism_specific = entry.get("formalism_specific", {})
        has_weights = (
            extensions.get("weights") is not None
            or "weights" in extensions
            or "weights" in formalism_specific
            or any(len(pair) > 2 for pair in entry["attacks"])  # weight in pair
        )
        assert has_weights, (
            f"Weighted writer dropped attack weights: attacks={entry['attacks']!r}, "
            f"extensions={extensions!r}, formalism_specific={formalism_specific!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Social — handler returns scores/votes, writer stashes them in extensions
# (Section 1.1 #5). Today the writer is honest (carries them in extensions).
# This test pins the current behaviour so a refactor that "cleans up"
# extensions doesn't silently drop them.
# ─────────────────────────────────────────────────────────────────────────────


class TestSocialFlattening1648:
    """Social writer carries scores/votes in extensions — pin the contract."""

    def test_social_writer_preserves_scores_and_votes(self) -> None:
        state = _new_state()
        output = {
            "ranking": ["a", "b"],
            "scores": {"a": 1.0, "b": 0.5},
            "arguments": ["a", "b"],
            "attacks": [["a", "b"]],
        }

        _write_social_to_state(output, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        extensions = entry.get("extensions", {})
        # Today's behaviour: scores live in extensions under "social_scores".
        # If a future writer refactor drops them, this assertion fires.
        assert extensions.get("social_scores") == output["scores"], (
            f"Social writer dropped scores: extensions={extensions!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# EAF — epistemic beliefs dropped (Section 1.1 #6)
# ─────────────────────────────────────────────────────────────────────────────


class TestEafFlattening1648:
    """EAF writer drops per-agent epistemic beliefs."""

    @pytest.mark.xfail(
        strict=True,
        reason="Pinning #1648 Wave-1 known loss (EAF). Writer drops per-agent "
        "epistemic beliefs. Wave-2 fix.",
    )
    def test_eaf_writer_preserves_epistemic_beliefs(self) -> None:
        state = _new_state()
        output = {
            "semantics": "grounded",
            "arguments": ["a", "b"],
            "attacks": [["a", "b"]],
            "extensions": [["a"]],
            "epistemic_beliefs": {"agent1": ["a"], "agent2": ["b"]},
        }

        _write_eaf_to_state(output, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        extensions = entry.get("extensions", {})
        formalism_specific = entry.get("formalism_specific", {})
        has_beliefs = (
            "epistemic_beliefs" in extensions
            or "epistemic_beliefs" in formalism_specific
            or extensions.get("eaf_beliefs") == output["epistemic_beliefs"]
        )
        assert has_beliefs, (
            f"EAF writer dropped epistemic beliefs: extensions={extensions!r}, "
            f"formalism_specific={formalism_specific!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# DeLP — whole formalism flattened away (Section 2.4)
# ─────────────────────────────────────────────────────────────────────────────


class TestDelpFlattening1648:
    """DeLP writer produces empty arguments/attacks; only query_results survive.

    The dialectical tree, defeat relations, and comparison criterion are all
    gone. This is the deepest flattening in the inventory.
    """

    @pytest.mark.xfail(
        strict=True,
        reason="Pinning #1648 Wave-1 known loss (DeLP). Program + defeat "
        "relations flattened away. Wave-2 fix.",
    )
    def test_delp_writer_preserves_argument_graph_or_defeat_relations(self) -> None:
        state = _new_state()
        output = {
            "program": [{"head": "a", "body": []}],
            "program_size": 1,
            "criterion": "specificity",
            "query_results": [
                {"query": "a", "answer": "warranted", "message": "ok"}
            ],
        }

        _write_delp_to_state(output, state, {})

        entry = next(iter(state.dung_frameworks.values()))
        extensions = entry.get("extensions", {})
        formalism_specific = entry.get("formalism_specific", {})
        # Either the dialectical tree reaches the state, or at least the
        # defeat relations are preserved. Today: NEITHER — assertion fails.
        has_structure = (
            extensions.get("delp_arguments") == output["program"]
            or extensions.get("defeat_relations") is not None
            or "delp_arguments" in extensions
            or "delp_arguments" in formalism_specific
            or "defeat_relations" in formalism_specific
        )
        assert has_structure, (
            f"DeLP writer flattened away the argument graph and defeat "
            f"relations: extensions={extensions!r}, "
            f"formalism_specific={formalism_specific!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# DL — full ontology dropped (Section 1.2 #10)
# ─────────────────────────────────────────────────────────────────────────────


class TestDlFlattening1648:
    """DL writer stores only ``[f"DL: {message}"]`` as formulas.

    TBox, ABox, subsumptions are all gone (counted at invoke but never written).
    """

    @pytest.mark.xfail(
        strict=True,
        reason="Pinning #1648 Wave-1 known loss (DL). TBox/ABox/subsumptions "
        "dropped. Wave-2 fix.",
    )
    def test_dl_writer_preserves_ontology_structure(self) -> None:
        state = _new_state()
        output = {
            "consistent": True,
            "message": "consistent",
            "tbox": [("Human", "Mammal")],
            "abox_concepts": [("alice", "Human")],
            "abox_roles": [("alice", "hasPet", "bob")],
        }

        _write_dl_to_state(output, state, {})

        fol = state.fol_analysis_results
        assert fol, "DL writer produced no entry"
        entry = fol[0]
        # Today: entry["formulas"] is just ["DL: consistent"] — synthesised.
        # After remedy: TBox / ABox should survive in extensions or sidecar.
        extensions = entry.get("extensions", {})
        formalism_specific = entry.get("formalism_specific", {})
        has_structure = (
            "tbox" in extensions
            or "tbox" in formalism_specific
            or extensions.get("tbox") == output["tbox"]
        )
        assert has_structure, (
            f"DL writer dropped ontology: extensions={extensions!r}, "
            f"formalism_specific={formalism_specific!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# CL — conditionals dropped (Section 1.3 #11)
# ─────────────────────────────────────────────────────────────────────────────


class TestClFlattening1648:
    """CL writer stores only ``[f"CL(N): {msg}"]`` as formulas."""

    @pytest.mark.xfail(
        strict=True,
        reason="Pinning #1648 Wave-1 known loss (CL). Conditionals dropped. "
        "Wave-2 fix.",
    )
    def test_cl_writer_preserves_conditionals(self) -> None:
        state = _new_state()
        output = {
            "entailed": True,
            "message": "ok",
            "conditionals": [
                {"conclusion": "P", "premise": "Q"},
                {"conclusion": "R", "premise": "S"},
            ],
        }

        _write_cl_to_state(output, state, {"conditionals": output["conditionals"]})

        pl = state.propositional_analysis_results
        assert pl, "CL writer produced no entry"
        entry = pl[0]
        extensions = entry.get("extensions", {})
        formalism_specific = entry.get("formalism_specific", {})
        has_conditionals = (
            "conditionals" in extensions
            or "conditionals" in formalism_specific
            or extensions.get("cl_conditionals") == output["conditionals"]
        )
        assert has_conditionals, (
            f"CL writer dropped conditionals: extensions={extensions!r}, "
            f"formalism_specific={formalism_specific!r}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# QBF — quantifiers dropped (Section 1.3 #13)
# ─────────────────────────────────────────────────────────────────────────────


class TestQbfFlattening1648:
    """QBF writer drops the alternating quantifier structure."""

    @pytest.mark.xfail(
        strict=True,
        reason="Pinning #1648 Wave-1 known loss (QBF). Quantifier structure "
        "dropped. Wave-2 fix.",
    )
    def test_qbf_writer_preserves_quantifiers(self) -> None:
        state = _new_state()
        output = {
            "valid": True,
            "formula": "exists x. forall y. P(x,y)",
            "quantifiers": [
                {"type": "exists", "vars": ["x"]},
                {"type": "forall", "vars": ["y"]},
            ],
        }

        _write_qbf_to_state(output, state, {})

        pl = state.propositional_analysis_results
        assert pl, "QBF writer produced no entry"
        entry = pl[0]
        extensions = entry.get("extensions", {})
        formalism_specific = entry.get("formalism_specific", {})
        has_quantifiers = (
            "quantifiers" in extensions
            or "quantifiers" in formalism_specific
            or extensions.get("qbf_quantifiers") == output["quantifiers"]
        )
        assert has_quantifiers, (
            f"QBF writer dropped quantifier structure: extensions={extensions!r}, "
            f"formalism_specific={formalism_specific!r}"
        )