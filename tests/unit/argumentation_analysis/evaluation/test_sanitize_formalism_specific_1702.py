"""#1702 — direct contract test for the ``formalism_specific`` sidecar scrub.

The coverage guard (``test_sanitize_coverage_guard_1702``) pins the RELATION
between what producers write and what the scrubber covers (canary planted in
every NL slot, survivors must match a frozen baseline). This file pins the
CONTRACT of pass 4d directly: every nominative leaf of the Wave-2
``formalism_specific`` sidecar is opacified, the closed-vocabulary / numeric
leaves survive untouched, and the topology (list arity, mapping key count) is
preserved — so the downstream quantitative aggregates (joint-attack arity,
weight distribution, extension sizes) are unaffected.

The leaf shapes mirror the real ``_write_*_to_state`` sites exactly (measured at
each producer — the anti-pendule of #1702): ABA ``contraries`` (Dict[atom,atom]),
SetAF ``set_attacks`` (List[{attackers,target}]), Weighted ``attack_weights``
(List[{source,target,weight}]) + ``weight_statistics``, EAF ``epistemic_beliefs``
(Dict[agent,List[atom]]), DeLP ``delp_arguments`` + ``program_size`` +
``criterion``. Opaque synthetic atoms only (privacy HARD — no corpus text).
"""

from __future__ import annotations

from argumentation_analysis.evaluation.sanitize_state import sanitize_state
import pytest


@pytest.fixture(autouse=True)
def _synthetic_opaque_salt(monkeypatch):
    """#1973: ``opaque_id`` has no default salt any more and raises without one.

    Every source this module feeds the scrubber is fabricated (see the module
    docstring), so a salt protects nothing here — it is pinned at the perimeter
    of the synthetic fixtures rather than provisioned as a CI secret. Two
    reasons, in that order: a repository secret makes the dependency invisible
    (green in CI, red on a fresh clone), and a root-scope ``autouse`` would
    disarm the #1973 fail-loud guard for the whole test environment, letting a
    future production path that forgets the salt pass green. Scoped to this
    module, the guard keeps its teeth everywhere else and
    ``test_opaque_id.py`` keeps asserting the raise.
    """
    monkeypatch.setenv("OPAQUE_ID_SALT", "synthetic-test-salt-1973")


def _entry(sidecar: dict) -> dict:
    """Wrap a formalism_specific sidecar in a single dung_frameworks entry."""
    return {
        "dung_frameworks": {
            "dung_1": {"name": "setaf_grounded", "formalism_specific": sidecar}
        }
    }


class TestFormalismSpecificNominativeLeavesOpacified:
    """Each source-derived leaf is opacified; its content no longer survives."""

    def test_contraries_keys_and_values_opacified(self) -> None:
        # ABA: Dict[assumption_atom, contrary_atom] — BOTH nominative.
        out = sanitize_state(
            _entry(
                {
                    "contraries": {
                        "claim_alpha": "claim_beta",
                        "claim_gamma": "claim_delta",
                    }
                }
            )
        )
        contra = out["dung_frameworks"]["dung_1"]["formalism_specific"]["contraries"]
        assert len(contra) == 2  # topology preserved (key count)
        # Neither the original atoms nor their keys survive verbatim.
        flat = set(contra.keys()) | set(str(v) for v in contra.values())
        assert all("claim_" not in s for s in flat)

    def test_set_attacks_attackers_and_target_opacified(self) -> None:
        # SetAF: List[{attackers: [atom], target: atom}].
        out = sanitize_state(
            _entry(
                {
                    "set_attacks": [
                        {
                            "attackers": ["claim_alpha", "claim_beta"],
                            "target": "claim_gamma",
                        }
                    ]
                }
            )
        )
        sa = out["dung_frameworks"]["dung_1"]["formalism_specific"]["set_attacks"]
        assert len(sa) == 1  # attack count preserved
        assert len(sa[0]["attackers"]) == 2  # joint-attack arity preserved
        assert all("claim_" not in a for a in sa[0]["attackers"])
        assert "claim_" not in sa[0]["target"]

    def test_attack_weights_source_target_opacified_weight_kept(self) -> None:
        # Weighted: List[{source, target, weight}] — source/target opacified,
        # weight (numeric) KEPT.
        out = sanitize_state(
            _entry(
                {
                    "attack_weights": [
                        {
                            "source": "claim_alpha",
                            "target": "claim_beta",
                            "weight": 0.75,
                        }
                    ]
                }
            )
        )
        aw = out["dung_frameworks"]["dung_1"]["formalism_specific"]["attack_weights"]
        assert len(aw) == 1
        assert aw[0]["weight"] == 0.75  # numeric survives
        assert "claim_" not in aw[0]["source"]
        assert "claim_" not in aw[0]["target"]

    def test_epistemic_beliefs_keys_and_values_opacified(self) -> None:
        # EAF: Dict[agent, List[atom]] — agent names + belief atoms both nominative.
        out = sanitize_state(
            _entry({"epistemic_beliefs": {"agent_one": ["claim_alpha", "claim_beta"]}})
        )
        eb = out["dung_frameworks"]["dung_1"]["formalism_specific"]["epistemic_beliefs"]
        assert len(eb) == 1  # agent count preserved
        only_args = next(iter(eb.values()))
        assert len(only_args) == 2  # belief arity preserved
        assert all("claim_" not in a for a in only_args)
        assert all("agent_" not in k for k in eb.keys())

    def test_delp_arguments_opacified_as_atom_list(self) -> None:
        # DeLP: the defeasible program — a source-derived string OR list of them.
        out = sanitize_state(_entry({"delp_arguments": ["claim_alpha <- claim_beta"]}))
        da = out["dung_frameworks"]["dung_1"]["formalism_specific"]["delp_arguments"]
        assert isinstance(da, list) and len(da) == 1  # topology preserved
        assert "claim_" not in da[0]

    def test_delp_arguments_opacified_as_bare_string(self) -> None:
        # The DeLP handler may emit the program as a single rule string.
        out = sanitize_state(_entry({"delp_arguments": "claim_alpha <- claim_beta"}))
        da = out["dung_frameworks"]["dung_1"]["formalism_specific"]["delp_arguments"]
        assert isinstance(da, str)
        assert "claim_" not in da


class TestFormalismSpecificClosedVocabAndNumericSurvive:
    """The anti-pendule: leaves the #1702 contract promises to preserve are
    NOT opacified (the symmetrical guarantee to the nominative-leaf tests)."""

    def test_weight_statistics_survive(self) -> None:
        out = sanitize_state(
            _entry(
                {
                    "attack_weights": [{"source": "a", "target": "b", "weight": 0.5}],
                    "weight_statistics": {
                        "min_weight": 0.1,
                        "max_weight": 0.9,
                        "avg_weight": 0.5,
                    },
                }
            )
        )
        stats = out["dung_frameworks"]["dung_1"]["formalism_specific"][
            "weight_statistics"
        ]
        assert stats == {"min_weight": 0.1, "max_weight": 0.9, "avg_weight": 0.5}

    def test_program_size_and_criterion_survive(self) -> None:
        out = sanitize_state(
            _entry(
                {
                    "delp_arguments": ["x <- y"],
                    "program_size": 7,
                    "criterion": "generalized_specificity",
                }
            )
        )
        side = out["dung_frameworks"]["dung_1"]["formalism_specific"]
        assert side["program_size"] == 7  # int untouched
        assert side["criterion"] == "generalized_specificity"  # closed vocab untouched


class TestFormalismSpecificAbsentOrNonDictIsSafe:
    """Defensive: an entry without the sidecar, or a non-dict sidecar, is left
    alone (no crash, no synthesis). Honest-absent stays honest-absent (#1019)."""

    def test_entry_without_sidecar_unchanged(self) -> None:
        out = sanitize_state(
            {
                "dung_frameworks": {
                    "dung_1": {"name": "dung_arbitration", "arguments": []}
                }
            }
        )
        assert "formalism_specific" not in out["dung_frameworks"]["dung_1"]

    def test_non_dict_sidecar_passes_through(self) -> None:
        # A malformed sidecar (producer bug) must not crash the export boundary.
        out = sanitize_state(
            {"dung_frameworks": {"dung_1": {"formalism_specific": "not-a-dict"}}}
        )
        # _scrub_formalism_specific returns non-dict input unchanged.
        assert out["dung_frameworks"]["dung_1"]["formalism_specific"] == "not-a-dict"

    def test_empty_sidecar_dict_survives(self) -> None:
        out = sanitize_state(
            {"dung_frameworks": {"dung_1": {"formalism_specific": {}}}}
        )
        assert out["dung_frameworks"]["dung_1"]["formalism_specific"] == {}
