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

    def test_the_formal_axis_families_resolve_too(self):
        """#1914 criterion 6 — the acceptance the map names: the exact-target
        contract extended to the formal-axis families. Non-vacuous by
        construction: the three refs are required (a missing section reddens),
        and each is produced by the shared producer, not spelled here."""
        from argumentation_analysis.reporting.restitution.formal_derivation import (
            formal_axis_ref,
        )

        appendix = _appendix_of_formal(_formal_state())
        refs = [formal_axis_ref(f) for f in ("FOL", "PL", "modale")]
        assert len(set(refs)) == 3, "one ref per family, no collision"
        for ref in refs:
            assert f"#### {ref}" in appendix, f"cited ref {ref} has no target"


# --- #1914 criterion 6 — the formal-axis derivation subsections -------------------


def _formal_state(**overrides) -> SimpleNamespace:
    """A state whose three formal axes all RAN and decided — synthetic opaque
    atoms only (privacy HARD), plus one prose-shaped entry that exercises the
    default/full split."""
    fields = dict(
        fol_analysis_results=[
            {
                "consistent": False,
                "message": "incoherent",
                "formulas": ["pred_alpha(cst_x)"],
            }
        ],
        propositional_analysis_results=[
            {"consistent": False, "message": "unsat", "formulas": ["a -> b"]}
        ],
        modal_analysis_results=[
            {"valid": True, "message": "ok", "formulas": ["box(p)"]}
        ],
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _appendix_of_formal(state: SimpleNamespace, *, full: bool = False) -> str:
    return render_appendix(
        {
            "fol_analysis_results": state.fol_analysis_results,
            "propositional_analysis_results": state.propositional_analysis_results,
            "modal_analysis_results": state.modal_analysis_results,
        },
        include_full_state_json=full,
    )


def _axis_slice(appendix: str, ref: str) -> str:
    """The text of one axis subsection — from its anchor to the next ``####``
    (or the end). Scoping matters: the opt-in full mode ALSO dumps the state
    JSON, so an unscoped ``in appendix`` would pass on the JSON dump and
    witness nothing about the section."""
    start = appendix.find(f"#### {ref}")
    if start == -1:
        return ""
    nxt = appendix.find("\n#### ", start + 1)
    return appendix[start : nxt if nxt != -1 else len(appendix)]


class TestFormalDerivationAppendix1914:
    """#1914 criterion 6 — « move exact solver formulas/derivations here ».

    Measured on ``main`` (2026-09-29): the folded appendix carried NO formal
    axis section and no citable anchor but Dung's; none of the three axes'
    tested formulas appeared anywhere in it, while the state carried them.
    """

    def test_one_citable_subsection_per_axis_that_ran(self):
        appendix = _appendix_of_formal(_formal_state())
        for ref in (
            "Annexe FOL[dérivations]",
            "Annexe PL[dérivations]",
            "Annexe modale[dérivations]",
        ):
            assert f"#### {ref}" in appendix

    def test_the_axis_that_did_not_run_gets_no_section(self):
        """Perimeter guard — green before and after: an axis with no records
        is not announced, so the anchors mean what they say."""
        appendix = _appendix_of_formal(
            _formal_state(fol_analysis_results=[], modal_analysis_results=[])
        )
        assert "Annexe PL[dérivations]" in appendix
        assert "Annexe FOL[dérivations]" not in appendix
        assert "Annexe modale[dérivations]" not in appendix

    def test_the_default_mode_counts_and_never_prints_corpus_prose(self):
        """The measured population (90 real dumps): ~93 % of the stored
        « formulas » are transcriptions, so the default folded mode — the one
        every render uses — must not list them."""
        state = _formal_state(
            fol_analysis_results=[
                {
                    "consistent": False,
                    "message": "incoherent",
                    "formulas": [
                        "une longue transcription de position reprise du corpus, "
                        "avec des virgules, des propositions entières et un point."
                    ],
                }
            ]
        )
        appendix = _appendix_of_formal(state)
        section = _axis_slice(appendix, "Annexe FOL[dérivations]")
        assert section, "the axis that ran must have its citable subsection"
        assert "transcription de position reprise du corpus" not in appendix
        assert "formules testées" in section

    def test_the_opt_in_full_mode_carries_the_verbatim_formulas(self):
        appendix = _appendix_of_formal(_formal_state(), full=True)
        assert "pred_alpha(cst_x)" in _axis_slice(appendix, "Annexe FOL[dérivations]")
        assert "a -> b" in _axis_slice(appendix, "Annexe PL[dérivations]")
        assert "box(p)" in _axis_slice(appendix, "Annexe modale[dérivations]")

    def test_placeholders_are_counted_but_never_listed(self):
        """A writer status message is not a derivation — the same guard the
        readable path applies, so the two surfaces cannot diverge."""
        state = _formal_state(
            fol_analysis_results=[
                {
                    "consistent": True,
                    "message": "ok",
                    "formulas": ["DL: Knowledge base is consistent."],
                }
            ]
        )
        appendix = _appendix_of_formal(state, full=True)
        section = _axis_slice(appendix, "Annexe FOL[dérivations]")
        assert "DL: Knowledge base" not in section
        assert "entrée non formulaire" in section

    def test_an_undecided_axis_contributes_no_tested_content(self):
        """#1019 — ``consistent: None`` (degraded) is not a decision, so its
        formulas are not counted as tested; the axis still gets its section
        and its honest tri-state verdict."""
        state = _formal_state(
            fol_analysis_results=[
                {"consistent": None, "message": "degraded", "formulas": ["p(a)"]}
            ]
        )
        appendix = _appendix_of_formal(state)
        assert "Annexe FOL[dérivations]" in appendix
        assert "0 formule" in appendix
        assert "p(a)" not in appendix


# --- #2882 — the machine-shaped subset, citable by default -----------------------


class TestDefaultAdmission2882:
    """#2882 — admit a machine-shaped subset of the tested formulas in the
    folded (default) annex, under the axis anchors.

    Rule chosen by confrontation, not supposition (the issue's DoD): R1 as
    issued (« 1 token, ≤ 40 car. ») could not be adopted bare — measured on
    the 90 real campaign dumps, 454 of its 519 unique admissions are
    underscore-joined sentence transcriptions (the FOL/PL atom naming swaps
    spaces for underscores), and the DoD's own criterion is « une chaîne qui
    est un fragment de phrase ne doit pas passer ». The retained rule is the
    R1 bound completed by a transcribed-sentence guard (≥ 3 word-runs of
    ≥ 3 letters without any logic symbol), shared with the Dung canonical
    line — where R1 bare was invisible only because Dung atoms keep their
    spaces (0/717 real atoms passed it). The next-more-permissive candidate
    (R4) measured +688 admissions beyond R1, of which 322 prose-shaped: the
    fold keeps those for the opt-in full mode.
    """

    def test_machine_formulas_are_listed_by_default(self):
        """Born red on main: the default mode listed nothing (R0) — a
        decided record's machine formulas must now appear under the anchor."""
        state = _formal_state(
            fol_analysis_results=[
                {
                    "consistent": False,
                    "message": "incoherent",
                    "formulas": ["p(a)", "!q|r"],
                }
            ]
        )
        section = _axis_slice(_appendix_of_formal(state), "Annexe FOL[dérivations]")
        assert "p(a)" in section, "a machine formula must be citable by default"
        assert "!q|r" in section

    def test_an_underscore_joined_sentence_stays_out(self):
        """DoD witness, green before AND after: a sentence transcribed with
        underscores — one token, no punctuation, the exact shape R1 bare
        admits — is corpus prose and must never be listed by default. The
        listing and the excluded count are the NEW behaviour (born red in
        the tests below); this one pins only the exclusion itself."""
        transcription = "the_harbour_ledger_has_tripled"
        assert len(transcription) <= 40 and " " not in transcription
        state = _formal_state(
            fol_analysis_results=[
                {
                    "consistent": False,
                    "message": "incoherent",
                    "formulas": [transcription, "p(a)"],
                }
            ]
        )
        appendix = _appendix_of_formal(state)
        assert transcription not in appendix

    def test_the_listing_is_bounded_and_deduplicated(self):
        """The default listing reuses the full mode's cap and de-duplicates
        (``scan_tested_content`` keeps duplicates by contract — a repeated
        formula is listed once, the transcription is the excluded count)."""
        transcription = "the_harbour_ledger_has_tripled"
        formulas = [f"w{i}" for i in range(13)] + ["w0", transcription]
        state = _formal_state(
            fol_analysis_results=[
                {"consistent": True, "message": "ok", "formulas": formulas}
            ]
        )
        section = _axis_slice(_appendix_of_formal(state), "Annexe FOL[dérivations]")
        assert section.count("w0") == 1, "a repeated formula is listed once"
        assert "+1 autre formule" in section, "the 13th unique formula is capped"
        assert "1 formule écartée" in section, "the transcription is counted out"

    def test_the_full_mode_keeps_the_verbatim_listing(self):
        """Anti-pendulum: opting in keeps the integral verbatim behaviour —
        the default admission never narrows the full mode."""
        transcription = "the_harbour_ledger_has_tripled"
        state = _formal_state(
            fol_analysis_results=[
                {
                    "consistent": False,
                    "message": "incoherent",
                    "formulas": [transcription, "p(a)"],
                }
            ]
        )
        section = _axis_slice(
            _appendix_of_formal(state, full=True), "Annexe FOL[dérivations]"
        )
        assert transcription in section, "the full mode lists the verbatim string"
        assert (
            "formules machine citables" not in section
        ), "the default-mode line does not duplicate the verbatim listing"

    def test_the_dung_canonical_line_shares_the_admission_rule(self):
        """Born red on the Dung side: under R1 bare the underscore-joined
        sentence was canonical and PRINTED — one rule for both sections
        means the transcription falls to the counted raw class there too."""
        transcription = "the_harbour_ledger_has_tripled"
        appendix = render_appendix(
            {
                "dung_frameworks": {
                    "fw1": {
                        "name": "verification_preferred",
                        "arguments": [transcription, "atom_x", "in_ext"],
                        "attacks": [],
                        "extensions": {"all_members": ["in_ext"]},
                    }
                }
            }
        )
        assert "atom_x" in appendix, "the machine atom stays canonical"
        assert transcription not in appendix
        assert "1 entrée non canonique" in appendix

    def test_one_admission_definition_not_respelled_inline(self):
        """The DoD's single-definition clause: the predicate lives once in
        ``formal_derivation`` — an inline re-spelling in the appendix would
        be a second way to misread the same matter."""
        import inspect

        from argumentation_analysis.reporting.restitution import appendix as ax

        source = inspect.getsource(ax)
        assert '" " not in' not in source, (
            "the canonical bound is re-spelled inline instead of importing "
            "is_machine_shaped"
        )
