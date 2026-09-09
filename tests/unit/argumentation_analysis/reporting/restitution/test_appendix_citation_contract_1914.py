"""#1914 (résidu b) — stable opaque appendix references, cited and resolvable.

Qualification (R961, dispatch R964): 0/49 real renders cite the appendix.
Refs ``Annexe Dung[label]`` ARE produced (``dung_reader.appendix_ref``) and
ride the anchor lines of TENUE FORMELLE, but (i) no consigne authorizes the
conductor to cite one — the anti-recopy rule dominates and kills the
citation in the egg, (ii) Acte III carries its Dung weak points without the
ref, and (iii) nothing pins that a cited ref resolves to an exact textual
target in the folded appendix.

This pins the full contract end to end, deterministically:
builder → prompt → contract-following stub conductor → renderer/annexe.
The stub follows the prompt exactly as a conductor would: it cites a
reference IFF the citation directive is present AND the verified block
carries one — never otherwise (anti-invention guard).
"""

from __future__ import annotations

import re
from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act2_narrative_plugin import (
    build_act2_evidence,
    build_act2_prompt,
)
from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)
from argumentation_analysis.reporting.restitution.appendix import render_appendix

_DIRECTIVE_MARKER = "RÉFÉRENCES D'ANNEXE"
_REF_RE = re.compile(r"Annexe Dung\[[^\]\n]+\]")


def _refs_in(text: str) -> list:
    """Every appendix ref literally present in ``text`` (test-side twin of
    ``dung_reader.appendix_refs_in`` — the accord between the two is itself
    pinned below)."""
    return _REF_RE.findall(text or "")


# --- synthetic state reproducing the measured native shapes (privacy HARD:
# synthetic opaque IDs, no corpus text) ----------------------------------------


def _state(*, with_dung: bool = True) -> SimpleNamespace:
    fw = {
        "name": "verification_preferred",
        "arguments": ["arg_1", "arg_2", "arg_3"],
        "attacks": [["arg_1", "arg_3"]],
        "extensions": {"all_members": ["arg_1", "arg_2"]},
    }
    return SimpleNamespace(
        dung_frameworks={"fw1": fw} if with_dung else {},
        identified_arguments={
            "arg_1": "L'orateur écarte l'opposant par une attaque personnelle.",
            "arg_2": "Une revendication étayée par un raisonnement causal.",
            "arg_3": "Un procès d'intention sur les motifs de l'opposant.",
        },
        identified_fallacies={},
        argument_quality_scores={},
        counter_arguments=[],
        fol_analysis_results=[],
        propositional_analysis_results=[],
        modal_analysis_results=[],
        governance_decisions=[],
        debate_transcripts=[],
    )


def _appendix_of(state: SimpleNamespace) -> str:
    """The appendix exactly as the renderer would fold it from this state."""
    return render_appendix({"dung_frameworks": state.dung_frameworks})


def _stub_conductor(prompt: str, beat: str) -> str:
    """Contract-following conductor stub (#1941 pattern): cites an appendix
    reference on the mobilized beat IFF the prompt's citation directive is
    present and the verified block carries one. Copies it verbatim."""
    if _DIRECTIVE_MARKER in prompt:
        refs = _refs_in(prompt)
        if refs:
            return f"{beat} (voir {refs[0]})."
    return f"{beat}."


# --- the shared detector -------------------------------------------------------


class TestSharedRefDetector:
    def test_dung_reader_exposes_the_shared_detector(self):
        from argumentation_analysis.reporting.restitution.dung_reader import (
            appendix_refs_in,
        )

        assert appendix_refs_in("texte sans ref") == []
        found = appendix_refs_in(
            "ancrage : Annexe Dung[preferred] — composition exacte ; puis rien"
        )
        assert found == ["Annexe Dung[preferred]"]


# --- Acte II: the citation contract --------------------------------------------


class TestAct2CitationContract:
    def test_prompt_carries_the_citation_directive_when_refs_exist(self):
        prompt = build_act2_prompt(build_act2_evidence(_state()))
        assert _DIRECTIVE_MARKER in prompt, (
            "the conductor is never told it may cite the appendix ref — "
            "the anti-recopy rule dominates (measured 0/49)"
        )

    def test_stub_conductor_cites_and_the_annexe_resolves(self):
        state = _state()
        prompt = build_act2_prompt(build_act2_evidence(state))
        act = _stub_conductor(
            prompt, "Le mouvement fragilisé par le graphe perd son assise"
        )
        cited = _refs_in(act)
        assert cited, "a contract-following conductor must cite the ref it mobilizes"
        appendix = _appendix_of(state)
        for ref in cited:
            assert (
                f"#### {ref}" in appendix
            ), f"cited ref {ref} has no exact textual target in the appendix"

    def test_no_directive_and_no_citation_without_dung(self):
        # Perimeter guard — must stay green before AND after the fix: absence
        # of evidence produces no ref to cite, and none is invented.
        state = _state(with_dung=False)
        prompt = build_act2_prompt(build_act2_evidence(state))
        assert _DIRECTIVE_MARKER not in prompt
        assert not _refs_in(prompt)
        act = _stub_conductor(prompt, "Le mouvement tient")
        assert not _refs_in(act)


# --- Acte III: same finding, same ref -------------------------------------------


class TestAct3CitationContract:
    def test_dung_weak_point_carries_the_same_stable_ref(self):
        weak_points = build_act3_evidence(_state()).weak_points
        dung_wps = [wp for wp in weak_points if wp.source == "dung"]
        assert dung_wps, "a decodable graph with a rejected arg must yield a wp"
        assert "Annexe Dung[preferred]" in dung_wps[0].detail, (
            "Acte III carries its Dung weak point without the shared ref — "
            "the same graph finding must bear the same ref in both acts"
        )

    def test_prompt_directive_and_resolution(self):
        state = _state()
        prompt = build_act3_prompt(build_act3_evidence(state))
        assert _DIRECTIVE_MARKER in prompt
        act = _stub_conductor(
            prompt, "Le cadre d'argumentation isole cette revendication comme rejetée"
        )
        cited = _refs_in(act)
        assert cited
        appendix = _appendix_of(state)
        for ref in cited:
            assert f"#### {ref}" in appendix

    def test_no_ref_without_dung(self):
        state = _state(with_dung=False)
        evidence = build_act3_evidence(state)
        assert not any(_refs_in(wp.detail or "") for wp in evidence.weak_points)
        prompt = build_act3_prompt(evidence)
        assert _DIRECTIVE_MARKER not in prompt


# --- a ref never upgrades mobilisation ------------------------------------------


class TestRefDoesNotUpgradeMobilisation:
    def test_roles_hierarchy_block_never_carries_a_ref(self):
        prompt = build_act2_prompt(build_act2_evidence(_state()))
        roles = prompt.split("RÔLES DES RÉSULTATS")[1].split("CONVERGENCES")[0]
        assert not _refs_in(roles), (
            "the proof hierarchy must stay ref-free: a ref opens the folded "
            "proof, it never promotes a result to decisive/corroborating"
        )

    def test_salience_module_never_reads_weak_points(self):
        # The ranking (P1→P2→P3, #1941) computes from roles/evidence fields
        # that carry no refs; weak-point details are where refs live on the
        # Acte III side. Pin the disjointness: if someone wires weak-point
        # text into the ranking, refs would start influencing mobilisation.
        import inspect

        from argumentation_analysis.reporting.restitution import (
            conclusion_salience,
        )

        source = inspect.getsource(conclusion_salience)
        assert "weak_points" not in source


# --- the appendix target contract ------------------------------------------------


class TestAppendixExactTarget:
    def test_every_ref_in_either_prompt_resolves_in_the_appendix(self):
        state = _state()
        appendix = _appendix_of(state)
        for prompt in (
            build_act2_prompt(build_act2_evidence(state)),
            build_act3_prompt(build_act3_evidence(state)),
        ):
            for ref in set(_refs_in(prompt)):
                assert f"#### {ref}" in appendix

    def test_sidecar_frameworks_produce_no_ref(self):
        # A non-native entry (sidecar formalism) is not citable material:
        # reading its extension as native acceptance is the #1912 fabrication.
        state = _state()
        state.dung_frameworks = {
            "fw_sidecar": {
                "name": "setaf_analysis",
                "arguments": ["arg_1"],
                "attacks": [],
                "extensions": {"all_members": ["arg_1"]},
            }
        }
        assert not _refs_in(build_act2_prompt(build_act2_evidence(state)))
