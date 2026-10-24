# -*- coding: utf-8 -*-
"""#3214 — the units Act II weighs reach Act III when a map edge joins them.

On the R1109 doc_A state, Act II weighs 91 units while Act III's evidence
carries 22 of them: Act III selects the governance winner, the salience
anchors, the global-findings cites and ``cited_unit_ids`` (fallacy targets,
counter targets, winner) — a reply that is none of those never reaches the
conclusion writer, even though Act II weighed it a page earlier. Act III then
concluded « le texte ne montre pas de réponse » on the very reply Act II had
weighed (#3198 treated what the writer may ASSERT; this is the cause
underneath).

The fix is a JOIN, not a widening: the units Act II weighs reach Act III as a
citation population of their own, limited to those a ``verification_*``
attack edge joins to a unit Act III already cites. Sidecar frameworks
(ABA/ADF/SetAF/…) stay skipped (#1912 — their extensions are not native
evidence, and neither are their edges). The joined block renders AFTER the
claims block, so the order of what Act III cites first does not change, and
each text travels under the existing excerpt budget with a drop notice
(#1622/#2850 idiom: fires from the gap, never from the cap alone).

Support relations are deliberately NOT read: they are not wired into the
state (the extraction's support-relations channel is unwritten), so the
argument map's only unit-to-unit edges today are the ``verification_*``
attacks. A reply the speaker makes IS an attack edge in the built graph
(the reply attacks the charge).

* witness — a unit joined to a citation by an attack edge reaches Act III's
  evidence with its text and the cited neighbor on its line.
* controls — no edge to a citation ⇒ no join; already-cited ⇒ no duplicate;
  sidecar edges ⇒ ignored; the existing citations keep their order.
* mutation — dropping the join call reddens every join witness.

Synthetic vocabulary only (cloche du port, marées — no corpus content,
privacy HARD): the *shape* is doc_A's, the words are not.
"""

from types import SimpleNamespace

from argumentation_analysis.reporting.restitution.act3_conclusion_plugin import (
    build_act3_evidence,
    build_act3_prompt,
)

_CHARGE = "La cloche du port annonce la poussée des marées."
_REPLY = "La poussée des marées suit la lune, pas la cloche du port."
_ATTACKED = "Le registre du port note chaque marée depuis un siècle."
_FAR = "Le phare ne sert plus rien depuis l'électrification de la jetée."


def _framework(attacks, name="verification_grounded"):
    # Real producer shape: the pipeline files one ``verification_{semantics}``
    # entry per semantics, ``attacks`` as ``[attacker, target]`` string pairs.
    return {
        "name": name,
        "arguments": [],
        "attacks": [list(p) for p in attacks],
        "extensions": {"extensions": [[]]},
    }


def _joined_state(
    attacks=(("arg_2", "arg_1"),),
    *,
    name="verification_grounded",
    extra_args=None,
    fallacy_targets=("arg_1",),
):
    """doc_A's shape in synthetic words: a charge the analysis cites (a
    fallacy targets it) and a reply only the argument map knows."""
    args = {
        "arg_1": _CHARGE,
        "arg_2": _REPLY,
        "arg_3": _ATTACKED,
        "arg_far": _FAR,
    }
    if extra_args:
        args.update(extra_args)
    fallacies = {
        f"fallacy_{i}": {
            "id": f"fallacy_{i}",
            "type": "appel à l'autorité",
            "justification": "Aucune source n'étaye la régularité alléguée.",
            "target_argument_id": target,
        }
        for i, target in enumerate(fallacy_targets, start=1)
    }
    return SimpleNamespace(
        propositional_analysis_results=None,
        fol_analysis_results=None,
        modal_analysis_results=None,
        identified_arguments=args,
        identified_fallacies=fallacies,
        counter_arguments=[],
        argument_quality_scores=None,
        dung_frameworks={"fw_1": _framework(attacks, name=name)},
    )


class TestTheJoinReachesTheEvidence:
    def test_a_unit_joined_by_an_attack_edge_reaches_act3(self):
        """Born red on main: the selection took winner / salience / findings /
        ``cited_unit_ids`` — a reply attacking a cited charge reached none of
        them, and arg_87's absence let Act III deny the reply existed."""
        evidence = build_act3_evidence(_joined_state())
        joined = {unit_id for unit_id, _rel, _text in evidence.joined_excerpts}
        assert "arg_2" in joined

    def test_the_joined_unit_travels_with_its_text(self):
        """A bare id is what let the writer rebind a cite to whichever unit it
        could describe (#2965's lesson): the text travels on the line."""
        evidence = build_act3_evidence(_joined_state())
        text = next(t for u, _r, t in evidence.joined_excerpts if u == "arg_2")
        assert "suit la lune" in text

    def test_the_cited_neighbor_travels_on_the_line(self):
        """The join is the information: without the neighbor, the excerpt is
        orphan text the writer cannot place against the citation it answers."""
        evidence = build_act3_evidence(_joined_state())
        rel = next(r for u, r, _t in evidence.joined_excerpts if u == "arg_2")
        assert rel == "attaque arg_1"

    def test_the_attacked_direction_is_named_too(self):
        """The map edge may run the other way: a unit the CITATION attacks is
        joined as attacked, not as attacking."""
        evidence = build_act3_evidence(_joined_state((("arg_1", "arg_3"),)))
        pair = next((r, t) for u, r, t in evidence.joined_excerpts if u == "arg_3")
        assert pair[0] == "attaqué par arg_1"
        assert "registre du port" in pair[1]

    def test_the_prompt_carries_the_block_after_the_claims(self):
        """#3214 requested: after Act III's own citations, so the order of
        what it cites first does not change."""
        prompt = build_act3_prompt(build_act3_evidence(_joined_state()))
        claims_at = prompt.index("[CE QUI A ÉTÉ DIT")
        joined_at = prompt.index("[REVENDICATIONS PESÉES PAR L'ACTE II")
        assert claims_at < joined_at
        # the joined line itself — arg_2 also sits in the claims dict tail, so
        # the search is scoped to the joined section, where the relation rides
        section = prompt.split("[REVENDICATIONS PESÉES PAR L'ACTE II", 1)[1]
        line = next(
            ln for ln in section.splitlines() if "arg_2" in ln and "suit la lune" in ln
        )
        assert "attaque arg_1" in line


class TestTheControlsStayGreen:
    def test_a_unit_with_no_edge_to_a_citation_is_not_joined(self):
        """arg_far attacks nothing cited (its edge, if any, reaches another
        uncited unit) — widening to every weighed unit is NOT the fix."""
        evidence = build_act3_evidence(
            _joined_state((("arg_far", "arg_3"),), fallacy_targets=("arg_1",))
        )
        joined = {u for u, _r, _t in evidence.joined_excerpts}
        assert "arg_far" not in joined
        assert "arg_3" not in joined

    def test_an_already_cited_unit_is_not_duplicated(self):
        """A unit both counter-targeted (cited) and map-adjacent stays a
        citation: the join adds a population, it does not double one."""
        state = _joined_state()
        state.counter_arguments = [
            {
                "id": "ca_1",
                "target_arg_id": "arg_2",
                "strategy": "direct refutation",
                "counter_content": "La lune ne suffit pas à expliquer la marée.",
                "score": 0.5,
            }
        ]
        evidence = build_act3_evidence(state)
        joined = {u for u, _r, _t in evidence.joined_excerpts}
        assert "arg_2" not in joined
        # and it IS in the evidence as a citation (its counter targets it)
        assert "arg_2" in {u for u, _t in evidence.claim_excerpts}

    def test_a_sidecar_framework_joins_nothing(self):
        """#1912: sidecar entries (ABA/ADF/SetAF/…) are not native evidence;
        reading their edges would join on fabricated relations."""
        evidence = build_act3_evidence(
            _joined_state((("arg_2", "arg_1"),), name="dung_1")
        )
        assert evidence.joined_excerpts == []

    def test_an_edge_to_an_untracked_id_is_ignored(self):
        """An attack whose other end is not a weighed unit (a method name, a
        gate id, an id the dict lost) joins nothing."""
        evidence = build_act3_evidence(
            _joined_state((("arg_2", "arg_1"), ("arg_1", "arg_999")))
        )
        joined = {u for u, _r, _t in evidence.joined_excerpts}
        assert "arg_999" not in joined
        assert joined == {"arg_2"}

    def test_no_join_says_so(self):
        """#1667's rule: an empty section and a missing section read the same
        to the writer — the block renders its honest absence."""
        prompt = build_act3_prompt(build_act3_evidence(_joined_state(attacks=())))
        assert "[REVENDICATIONS PESÉES PAR L'ACTE II" in prompt
        assert "aucune unité pesée par l'Acte II ne rejoint les citations" in prompt

    def test_existing_citation_order_is_unchanged(self):
        """DoD box 3: the claims list names the same units, in the same
        order, whether or not the map joins new ones."""
        without = build_act3_evidence(_joined_state(attacks=()))
        with_join = build_act3_evidence(_joined_state())
        assert [u for u, _t in without.claim_excerpts] == [
            u for u, _t in with_join.claim_excerpts
        ]
        assert without.claim_excerpts_total == with_join.claim_excerpts_total


class TestTheBudget:
    def test_the_cap_counts_its_drops(self):
        """The #1622/#2850 idiom: the notice fires from the gap between what
        is listed and what the join found, never from the cap alone."""
        extra = {
            f"arg_j{i}": f"La jetée {i} change tout, quoi qu'on en dise."
            for i in range(10)
        }
        attacks = (("arg_2", "arg_1"),) + tuple(
            (f"arg_j{i}", "arg_1") for i in range(10)
        )
        evidence = build_act3_evidence(_joined_state(attacks, extra_args=extra))
        assert evidence.joined_excerpts_total == 11
        assert len(evidence.joined_excerpts) < 11
        prompt = build_act3_prompt(evidence)
        block = prompt.split("[REVENDICATIONS PESÉES PAR L'ACTE II")[1]
        assert f"{len(evidence.joined_excerpts)} unités jointes listées sur 11" in block
        assert "N'écris pas, et ne laisse pas entendre" in block

    def test_the_join_follows_the_citations(self):
        """A unit joined to an EARLY citation comes before one joined to a
        late citation, and ties break by id — deterministic order."""
        extra = {
            "arg_5": "La bonde océane explique seule les grandes marées.",
            "arg_zz": "Le registre du port est contresigné par le harbour-master.",
        }
        # citations: fallacy targets sorted → arg_1 then arg_5
        attacks = (
            ("arg_zz", "arg_5"),  # joined to the LATE citation
            ("arg_2", "arg_1"),  # joined to the EARLY citation
        )
        evidence = build_act3_evidence(
            _joined_state(attacks, extra_args=extra, fallacy_targets=("arg_1", "arg_5"))
        )
        order = [u for u, _r, _t in evidence.joined_excerpts]
        assert order.index("arg_2") < order.index("arg_zz")
