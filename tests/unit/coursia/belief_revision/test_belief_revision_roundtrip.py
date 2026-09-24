# -*- coding: utf-8 -*-
"""Round-trip guard for the #1961 Phase 4 CoursIA asset on belief revision.

Replays every case of docs/coursia_contrib/belief_revision_examples.json
against the real engines (JTMS, ATMS, ConflictResolver, DungFramework,
qbf_native) and pins the structural claims the notebook teaches. Corpus-free,
zero LLM, zero JVM — all five modules are pure Python.
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
EXAMPLES_PATH = REPO / "docs" / "coursia_contrib" / "belief_revision_examples.json"
NOTEBOOK_PATH = REPO / "docs" / "coursia_contrib" / "belief_revision.ipynb"

from argumentation_analysis.services.jtms.jtms_core import JTMS
from argumentation_analysis.services.jtms.atms_core import ATMS, CONTRADICTION_SYMBOL
from argumentation_analysis.services.jtms.conflict_resolution import ConflictResolver
from argumentation_analysis.agents.core.logic.dung_native import DungFramework
from argumentation_analysis.agents.core.logic import qbf_native as qbf

SOURCE_FILES = [
    "argumentation_analysis/services/jtms/jtms_core.py",
    "argumentation_analysis/services/jtms/atms_core.py",
    "argumentation_analysis/services/jtms/conflict_resolution.py",
    "argumentation_analysis/agents/core/logic/dung_native.py",
    "argumentation_analysis/agents/core/logic/qbf_native.py",
]


@pytest.fixture(scope="module")
def examples():
    data = json.loads(EXAMPLES_PATH.read_text(encoding="utf-8"))
    assert data["asset"] == "belief_revision"
    assert data["phase"] == 4
    return data


def case(section, name):
    match = [c for c in section if c["name"] == name]
    assert len(match) == 1, f"case {name!r} not found exactly once"
    return match[0]


# ---------------------------------------------------------------- inventory


def test_inventory_matches_head(examples):
    inv = examples["inventory"]
    assert set(inv) == set(SOURCE_FILES)
    for rel in SOURCE_FILES:
        lines = len((REPO / rel).read_text(encoding="utf-8").splitlines())
        assert lines == inv[rel], f"line count drifted for {rel}"


def test_notebook_ships_executed_outputs():
    nb = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    code_cells = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert len(code_cells) >= 15
    counts = []
    for cell in code_cells:
        assert cell.get("execution_count"), "code cell without execution_count"
        assert cell.get("outputs"), "code cell without committed outputs"
        counts.append(cell["execution_count"])
    assert counts == sorted(counts), "execution_count must be sequential"


# ---------------------------------------------------------------- JTMS


def test_jtms_propagation_and_retraction(examples):
    stored = case(examples["jtms_cases"], "propagation_and_retraction")
    j = JTMS()
    j.add_belief("A")
    j.add_belief("B")
    j.add_justification(["A"], [], "B")
    j.set_belief_validity("A", True)
    assert str(j.beliefs["B"]) == stored["b_after_a_true"] == "B -> VALID"
    j.set_belief_validity("A", False)
    # Retracting the premise falls back to UNKNOWN, never INVALID (#2094)
    assert str(j.beliefs["B"]) == stored["b_after_a_false"] == "B -> UNKNOWN"


def test_jtms_strict_vs_autocreate(examples):
    stored = case(examples["jtms_cases"], "strict_mode_and_autocreate")
    j = JTMS(strict=True)
    with pytest.raises(KeyError):
        j.set_belief_validity("X", True)
    with pytest.raises(KeyError) as exc:
        j.add_justification(["A"], [], "C")
    assert f"KeyError: {exc.value}" == stored["strict_add_justification"]

    nonstrict = JTMS(strict=False)  # default
    nonstrict.add_justification(["P"], [], "Q")
    assert (
        sorted(nonstrict.beliefs)
        == stored["nonstrict_autocreated_beliefs"]
        == ["P", "Q"]
    )


def test_jtms_out_list_semantics(examples):
    stored = case(examples["jtms_cases"], "out_list_blocks_when_premise_valid")
    j = JTMS()
    j.add_justification(["A"], ["B"], "C")
    j.set_belief_validity("A", True)
    assert str(j.beliefs["C"]) == stored["c_when_b_unknown"] == "C -> VALID"
    j.set_belief_validity("B", True)
    assert str(j.beliefs["C"]) == stored["c_when_b_valid"] == "C -> UNKNOWN"


def test_jtms_scc_marks_non_monotonic(examples):
    stored = case(
        examples["jtms_cases"], "scc_cycle_marks_non_monotonic_and_locks_unknown"
    )
    j = JTMS()
    j.add_justification(["A"], [], "B")
    j.add_justification(["B"], [], "A")
    nonmono = sorted(n for n, b in j.beliefs.items() if b.non_monotonic)
    assert nonmono == stored["cycle_members"] == ["A", "B"]


def test_jtms_explain_tri_state(examples):
    stored = case(examples["jtms_cases"], "explain_belief_tri_state_verdicts")
    j = JTMS()
    j.add_justification(["A"], ["B"], "C")
    j.set_belief_validity("A", True)
    verdict = lambda: j.explain_belief("C").strip().splitlines()[-1]
    assert verdict() == stored["unknown_premise"] == "  Result: Valid"
    j.set_belief_validity("B", True)
    assert verdict() == stored["refuted_by_out_premise"] == "  Result: Invalid"
    j.set_belief_validity("B", False)
    assert verdict() == stored["valid_when_out_falsy"] == "  Result: Valid"


def test_jtms_retraction_trace_and_teardown(examples):
    stored_trace = case(examples["jtms_cases"], "retraction_trace_cascade")
    j = JTMS()
    j.enable_tracing()
    j.add_justification(["A"], [], "B")
    j.add_justification(["B"], [], "C")
    j.set_belief_validity("A", True)
    j.set_belief_validity("A", None)
    assert j.get_retraction_chain() == stored_trace["trace"]
    assert set(j.get_retraction_chain()[0]["cascaded"]) == {"B", "C"}

    stored_rm = case(examples["jtms_cases"], "remove_belief_tears_down_justifications")
    j2 = JTMS()
    j2.add_justification(["A"], [], "B")
    j2.set_belief_validity("A", True)
    j2.remove_belief("A")
    assert sorted(j2.beliefs) == stored_rm["beliefs_after"] == ["B"]
    assert (
        len(j2.beliefs["B"].justifications) == stored_rm["b_justifications_after"] == 0
    )


# ---------------------------------------------------------------- ATMS


def test_atms_assumption_label_and_product(examples):
    stored = case(examples["atms_cases"], "assumption_label_and_product_environment")
    a = ATMS()
    a.add_assumption("p")
    a.add_assumption("q")
    a.add_node("r")
    a.add_justification(["p", "q"], [], "r")
    envs = lambda n: [sorted(e) for e in a.get_environments(n)]
    assert envs("p") == stored["p_envs"] == [["p"]]
    assert envs("r") == stored["r_envs"] == [["p", "q"]]


def test_atms_invalidation_never_repropagates(examples):
    stored = case(examples["atms_cases"], "invalidation_strips_and_never_repropagates")
    a = ATMS()
    a.add_assumption("x")
    a.add_node("t")
    a.add_justification(["x"], [], "t")
    assert [sorted(e) for e in a.get_environments("t")] == stored["t_envs_before"]
    a.invalidate_environment(frozenset({"x"}))
    assert (
        [sorted(e) for e in a.get_environments("t")]
        == stored["t_envs_after_invalidation"]
        == []
    )
    assert (
        [sorted(e) for e in a.get_environments("x")]
        == stored["assumption_x_envs_after"]
        == []
    )
    # The derivation still exists; nothing re-fires it (#2094 label contract)
    assert len(a.nodes["t"].justifications) == 1


def test_atms_nogood_not_durable_double_invalidation(examples):
    stored = case(examples["atms_cases"], "contradiction_nogood_not_durable")
    a = ATMS()
    a.add_assumption("m")
    a.add_assumption("n")
    a.add_justification(["m"], [], "n")  # n's label is {{n},{m}} — non-minimal
    assert (
        a.is_consistent(frozenset({"m", "n"})) is stored["consistent_mn_before_nogood"]
    )
    a.add_justification(["m", "n"], [], CONTRADICTION_SYMBOL)
    assert (
        a.is_consistent(frozenset({"m", "n"}))
        is stored["consistent_mn_after_nogood"]
        is True
    )
    assert (
        [sorted(e) for e in a.get_environments(CONTRADICTION_SYMBOL)]
        == stored["contradiction_node_label_after"]
        == []
    )
    assert (
        [sorted(e) for e in a.get_environments("n")]
        == stored["n_envs_after"]
        == [["n"]]
    )
    # The LAST auto-invalidation ({m}) strips the assumption's own label too
    assert [sorted(e) for e in a.get_environments("m")] == stored["m_envs_after"] == []


def test_atms_out_node_blocking_and_errors(examples):
    stored_block = case(examples["atms_cases"], "out_node_blocks_superset_environments")
    a = ATMS()
    a.add_assumption("s")
    a.add_assumption("u")
    a.add_node("v")
    a.add_node("w")
    a.add_node("blocked")
    a.add_justification(["s"], [], "v")
    a.add_justification(["u"], [], "w")
    a.add_justification(["v"], ["w"], "blocked")
    assert (
        [sorted(e) for e in a.get_environments("blocked")]
        == stored_block["blocked_envs"]
        == [["s"]]
    )

    stored_err = case(examples["atms_cases"], "unknown_node_raises")
    with pytest.raises(KeyError) as exc:
        a.get_environments("zz")
    assert f"KeyError: {exc.value}" == stored_err["result"]

    stored_expl = case(examples["atms_cases"], "explain_node_shape")
    a2 = ATMS()
    a2.add_assumption("d")
    a2.add_node("e")
    a2.add_justification(["d"], [], "e")
    assert a2.explain_node("e") == stored_expl["explain"]


# ---------------------------------------------------------------- conflicts


CONFLICT = {
    "belief_name": "hypothesis_X",
    "beliefs": {
        "agent_1": {"belief_name": "hypothesis_X", "confidence": 0.8, "valid": True},
        "agent_2": {"belief_name": "hypothesis_X", "confidence": 0.3, "valid": False},
    },
    "context": {"type": "hypothesis"},
}


def test_conflict_confidence_evidence_and_unknown_strategy(examples):
    stored_c = case(examples["conflict_cases"], "confidence_based")
    stored_e = case(examples["conflict_cases"], "evidence_based_score_beats_confidence")
    stored_u = case(examples["conflict_cases"], "unknown_strategy_raises")
    r = ConflictResolver()

    res = r.resolve(CONFLICT, strategy="confidence_based")
    assert res["resolved"] is stored_c["resolved"] is True
    assert res["chosen_agent"] == stored_c["chosen_agent"] == "agent_1"

    ev = {
        "belief_name": "claim_Y",
        "beliefs": {
            "agent_1": {
                "belief_name": "claim_Y",
                "confidence": 0.5,
                "justification_count": 4,
            },
            "agent_2": {
                "belief_name": "claim_Y",
                "confidence": 0.9,
                "justification_count": 1,
            },
        },
    }
    res_ev = r.resolve(ev, strategy="evidence_based")
    assert res_ev["chosen_agent"] == stored_e["chosen_agent"] == "agent_1"
    assert res_ev["reasoning"] == stored_e["reasoning"]  # 4×0.5 beats 1×0.9

    # #2344: an unknown strategy raises; it used to fall back silently.
    assert stored_u["raises"] == "ValueError"
    with pytest.raises(ValueError, match=stored_u["message_contains"]):
        r.resolve(CONFLICT, strategy="made_up_strategy")


def test_conflict_consensus_quorum_and_tie(examples):
    stored = case(examples["conflict_cases"], "consensus_quorum_and_tie")
    r = ConflictResolver()

    two = r.resolve(CONFLICT, strategy="consensus")
    assert two["resolved"] is stored["two_agents_resolved"] is False
    assert (
        two["reasoning"]
        == stored["two_agents_reasoning"]
        == "Consensus requires 3+ agents"
    )

    three = r.resolve(
        {
            "belief_name": "hyp_Z",
            "beliefs": {
                "a1": {"belief_name": "hyp_Z", "confidence": 0.9, "valid": True},
                "a2": {"belief_name": "hyp_Z", "confidence": 0.5, "valid": True},
                "a3": {"belief_name": "hyp_Z", "confidence": 0.1, "valid": False},
            },
        },
        strategy="consensus",
    )
    assert (
        three["reasoning"]
        == stored["three_agents_reasoning"]
        == "Consensus: 2 for vs 1 against"
    )

    tie = r.resolve(
        {
            "belief_name": "hyp_T",
            "beliefs": {
                f"a{i}": {"belief_name": "hyp_T", "valid": i % 2 == 0}
                for i in range(1, 5)
            },
        },
        strategy="consensus",
    )
    assert tie["resolved"] is stored["tie_resolved"] is False
    assert tie["reasoning"] == stored["tie_reasoning"] == "Consensus tie"


def test_conflict_expertise_and_temporal(examples):
    stored_exp = case(
        examples["conflict_cases"], "agent_expertise_substring_and_fallback"
    )
    stored_time = case(examples["conflict_cases"], "temporal_iso_string_comparison")
    r = ConflictResolver()

    exp = r.resolve(
        {
            "belief_name": "ev_W",
            "beliefs": {
                "watson_agent": {"belief_name": "ev_W", "confidence": 0.2},
                "sherlock_agent": {"belief_name": "ev_W", "confidence": 0.9},
            },
            "context": {"type": "evidence"},
        },
        strategy="agent_expertise",
    )
    assert exp["chosen_agent"] == stored_exp["expert_chosen"] == "sherlock_agent"
    assert exp["reasoning"] == stored_exp["expert_reasoning"]

    noexp = r.resolve(
        {
            "belief_name": "ev_N",
            "beliefs": {
                "agent_x": {"belief_name": "ev_N", "confidence": 0.4},
                "agent_y": {"belief_name": "ev_N", "confidence": 0.7},
            },
            "context": {"type": "evidence"},
        },
        strategy="agent_expertise",
    )
    assert noexp["chosen_agent"] == stored_exp["no_expert_fallback_agent"] == "agent_y"
    assert noexp["reasoning"] == stored_exp["no_expert_fallback_reasoning"]
    # #2344: the fallback is named, not booked under the strategy asked for.
    assert noexp["strategy_used"] == stored_exp["no_expert_strategy_used"]
    assert noexp["fallback_from"] == stored_exp["no_expert_fallback_from"]

    late = r.resolve(
        {
            "belief_name": "fact_T",
            "beliefs": {
                "old": {"belief_name": "fact_T", "timestamp": "2026-01-01T10:00:00"},
                "new": {"belief_name": "fact_T", "timestamp": "2026-06-01T10:00:00"},
            },
        },
        strategy="temporal",
    )
    assert late["chosen_agent"] == stored_time["latest_chosen"] == "new"

    undated = r.resolve(
        {
            "belief_name": "fact_U",
            "beliefs": {
                "a": {"belief_name": "fact_U", "confidence": 0.3},
                "b": {"belief_name": "fact_U", "confidence": 0.6},
            },
        },
        strategy="temporal",
    )
    assert undated["chosen_agent"] == stored_time["no_timestamp_fallback_agent"]
    assert undated["strategy_used"] == stored_time["no_timestamp_strategy_used"]
    assert undated["fallback_from"] == stored_time["no_timestamp_fallback_from"]


def test_conflict_history_stats_consistent(examples):
    stored = case(examples["conflict_cases"], "history_stats")["stats"]
    assert stored["total_conflicts"] == stored["resolved"] + stored["unresolved"]
    assert sum(stored["by_strategy"].values()) == stored["total_conflicts"]
    # The named fallbacks (no expert, no timestamp) are booked under the
    # strategy that actually decided; the unknown strategy raises (#2344).
    assert stored["by_strategy"]["confidence_based"] == 3


# ---------------------------------------------------------------- Dung


def test_dung_triangle_odd_cycle(examples):
    stored = case(examples["dung_cases"], "triangle_odd_cycle_nothing_accepted")
    tri = DungFramework.triangle()
    assert sorted(tri.grounded_extension()) == stored["grounded"] == []
    assert (
        [sorted(e) for e in tri.preferred_extensions()] == stored["preferred"] == [[]]
    )
    assert [sorted(e) for e in tri.stable_extensions()] == stored["stable"] == []


def test_dung_reinstatement_and_characteristic_function(examples):
    stored = case(examples["dung_cases"], "reinstatement_a_defends_c")
    stored_f = case(examples["dung_cases"], "characteristic_function")
    rei = DungFramework.reinstatement()
    assert sorted(rei.grounded_extension()) == stored["grounded"] == ["a", "c"]
    assert [sorted(e) for e in rei.preferred_extensions()] == stored["preferred"]
    assert [sorted(e) for e in rei.stable_extensions()] == stored["stable"]
    assert (
        sorted(rei.characteristic_function(frozenset()))
        == stored_f["reinstatement_F_empty"]
        == ["a"]
    )
    assert (
        sorted(rei.characteristic_function(frozenset({"a"})))
        == stored_f["reinstatement_F_a"]
        == ["a", "c"]
    )


def test_dung_nixon_diamond_variant(examples):
    # The preset was renamed mutual_destruction (#2252): the stored case is the
    # measured 4-arg variant, unchanged in semantics — only the name moved.
    stored = case(examples["dung_cases"], "nixon_diamond_measured")
    nix = DungFramework.mutual_destruction()
    assert nix.get_all_extensions() == stored["all_extensions"]
    assert nix.get_argument_status("hawk") == stored["status_hawk"]
    assert nix.get_argument_status("pacifist") == stored["status_pacifist"]
    # Every semantics rejects hawk and pacifist (unlike the classic diamond)
    assert stored["status_hawk"]["skeptically_accepted"] is False
    assert stored["status_pacifist"]["skeptically_accepted"] is False


def test_dung_framework_properties(examples):
    stored = case(examples["dung_cases"], "framework_properties")
    assert DungFramework.triangle().framework_properties() == stored["triangle"]
    self_atk = DungFramework()
    self_atk.add_attack("s", "s")
    assert self_atk.framework_properties() == stored["self_attacking"]
    assert stored["self_attacking"]["self_attacking"] == ["s"]


def test_dung_enumeration_cap_970(examples):
    stored = case(examples["dung_cases"], "enumeration_cap_970")
    big = DungFramework()
    for i in range(16):
        big.add_argument(f"x{i}")
    for i in range(15):
        big.add_attack(f"x{i}", f"x{i+1}")
    grounded = sorted(big.grounded_extension())
    assert grounded == stored["grounded_still_works"]
    assert all(name in (f"x{i}" for i in range(0, 16, 2)) for name in grounded)
    with pytest.raises(RuntimeError) as exc:
        big.stable_extensions()
    assert str(exc.value) == stored["stable_raises"]
    assert "#970" in str(exc.value)


# ---------------------------------------------------------------- QBF


def test_qbf_example_analyses(examples):
    assert (
        qbf.example_simple_validity()
        == case(examples["qbf_cases"], "tautology")["analysis"]
    )
    assert (
        qbf.example_simple_satisfiability()
        == case(examples["qbf_cases"], "contradiction")["analysis"]
    )
    assert (
        qbf.example_mixed_quantifiers()
        == case(examples["qbf_cases"], "mixed_quantifiers_valid")["analysis"]
    )


def test_qbf_parser_traps(examples):
    no_parens = case(examples["qbf_cases"], "parser_no_parentheses_support")
    assert (
        repr(qbf.parse_formula("a & (b | c)")) == no_parens["repr_of_a_and_paren_expr"]
    )
    # Parens become part of variable names — the '|' never groups
    assert repr(qbf.parse_formula("a & (b | c)")) == "((a & (b) | c))"

    right = case(examples["qbf_cases"], "parser_implication_right_associative")
    assert repr(qbf.parse_formula("a => b => c")) == right["repr"] == "(a => (b => c))"

    fold = case(examples["qbf_cases"], "parser_or_left_fold")
    assert repr(qbf.parse_formula("a | b | c")) == fold["repr"] == "((a | b) | c)"


def test_qbf_unassigned_variable_defaults_false(examples):
    stored = case(examples["qbf_cases"], "unassigned_variable_defaults_false")
    assert qbf.Var("zz").evaluate({}) is stored["eval_empty_assignment"] is False


def test_qbf_acceptance_replays(examples):
    assert (
        qbf.example_argumentation_acceptance()
        == case(examples["qbf_cases"], "credulous_witness")["result"]
    )

    sk = qbf.skeptical_acceptance_qbf(
        arguments=["a", "b", "c"], attacks=[["a", "b"], ["b", "a"]], target="a"
    )
    assert sk == case(examples["qbf_cases"], "skeptical_via_preferred")["result"]
    assert sk["accepted"] is False and sk["preferred_extensions"] == [
        ["a", "c"],
        ["b", "c"],
    ]

    assert (
        qbf.skeptical_acceptance_qbf(["a"], [], "nope")
        == case(examples["qbf_cases"], "absent_target")["result"]
    )

    big_args = [f"y{i}" for i in range(16)]
    assert (
        qbf.credulous_acceptance_qbf(big_args, [], "y0")
        == case(examples["qbf_cases"], "too_large_returns_none")["result"]
    )
