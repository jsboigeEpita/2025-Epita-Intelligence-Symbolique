"""Shared reader-facing interpretation of Dung results (#1908).

Act II and Act III must not diverge on what « accepté » and « rejeté » mean
when they talk about the Dung graph — that divergence was the #1167 family,
and the digestion work (#1908) reopens the surface: both acts now render
Dung consequences, so both read their caveat and their interpretation
glossary HERE. One module, one meaning.

The digested consequence replaces the raw machinery in the body: which
support survives, what loses its footing, how much confidence to place in a
graph result. The machinery itself (extension membership, attack edges,
protocol) moves to the appendix, referenced from the prose.
"""

from __future__ import annotations

import re

# The epistemic caveat, stated at the FIRST reader-facing mention of the
# graph (Act II) — not deferred to Act III. Acceptance and rejection are
# verdicts internal to the constructed graph.
EPISTEMIC_CAVEAT = (
    "accepter ou rejeter ici est un verdict interne au graphe construit sur "
    "les arguments extraits : l'acceptation n'établit pas une vérité "
    "factuelle, et le rejet n'est pas une réfutation historique du propos"
)

# What the reader may conclude from each verdict — the interpretation
# glossary both acts share.
ACCEPTED_MEANS = (
    "un argument accepté garde son assise dans le graphe face aux attaques " "reçues"
)
REJECTED_MEANS = (
    "un argument rejeté perd cette assise dans le graphe, rien de plus : "
    "ses soutiens n'y survivent pas aux attaques"
)
# #3153: « rejeté » covers only the arguments the graph settles AGAINST.
# An argument the graph does not settle is a third verdict, and it needs its
# own gloss — reading non-membership as rejection turned a mutual attack into
# a defeat of both poles (doc_B).
UNDECIDED_MEANS = (
    "un argument en suspens n'est ni retenu ni écarté : le graphe ne tranche "
    "pas le désaccord qui le concerne, ce qui est un constat sur le graphe et "
    "non un verdict sur l'argument"
)
CREDULOUS_MEANS = (
    "parmi les arguments en suspens, ceux qu'une extension acceptée contient "
    "sont dits « acceptés par crédulité » : ils survivent dans au moins une "
    "lecture cohérente du graphe, sans que le graphe impose ce choix"
)


def reader_consequence(
    n_arguments: int,
    n_attacks: int,
    n_rejected: int,
    semantics_label: str,
    n_identified: int | None = None,
    *,
    n_undecided: int = 0,
) -> str:
    """The digested Dung consequence for the body — no extension list, no
    serialized edges, no raw counts dump.

    Frames the graph as a reorganisation of the extracted arguments (#1280)
    and says what changed for the reader's judgment, not what the solver
    printed.

    #2037: the graph's node count and the Acte I inventory (``N arguments
    extraits``) are two DIFFERENT populations — the graph is built from a
    subset produced by a different phase. When the inventory total is known
    and the graph covers less than it, the frame NAMES the reduction
    (retained-for-the-graph, out of identified units) instead of reusing the
    inventory's syntagme with a second number. Never align the numbers —
    the bridge is the fix, not the convergence.

    #3153: ``n_undecided`` counts the arguments the graph does NOT settle.
    They are neither accepted nor rejected, so the two pre-#3153 sentences
    were both false whenever it was non-zero: « sans fragiliser aucun
    argument » and « en fragilisant N » both describe a graph that decided.
    The stand-off gets its own wording, and it never hides the conflict —
    dropping it is the pendulum the issue forbids.
    """
    if n_identified is not None and 0 < n_arguments < n_identified:
        frame = (
            f"le graphe d'attaque construit sur les {n_arguments} arguments "
            f"retenus pour le graphe, sur {n_identified} unités "
            f"argumentatives identifiées ({n_attacks} relations d'attaque, "
            f"sémantique {semantics_label}) réorganise le matériau"
        )
        node_syntagme = "retenus"
    else:
        frame = (
            f"le graphe d'attaque construit sur les {n_arguments} arguments "
            f"extraits ({n_attacks} relations d'attaque, sémantique "
            f"{semantics_label}) réorganise le matériau"
        )
        node_syntagme = "extraits"
    if n_rejected == 0 and n_undecided == 0:
        consequence = (
            f"{frame} sans fragiliser aucun argument : chaque position "
            "conserve son assise face aux attaques reçues"
        )
    elif n_rejected == 0:
        # Nothing is settled against anyone, but the graph does not settle
        # the dispute either — the stand-off is the finding.
        consequence = (
            f"{frame} sans écarter aucun argument, mais sans départager "
            f"{n_undecided} des {n_arguments} arguments {node_syntagme} : la "
            f"sémantique {semantics_label} les laisse en suspens, le désaccord "
            "qui les concerne n'étant pas tranché par les attaques du graphe"
        )
    elif n_undecided == 0:
        # Morphology-free French: the « (s) » alternation is a solver-output
        # marker the readability gate now tracks (#1908) — the digested
        # consequence must read as prose, not as machine output. The node
        # population keeps the SAME syntagme as the frame — « extraits » is
        # the inventory's word (#2037), never the graph's when bridged.
        consequence = (
            f"{frame} en fragilisant {n_rejected} des {n_arguments} arguments "
            f"{node_syntagme}, qui perdent l'assise que l'extension "
            f"{semantics_label} garantit aux autres"
        )
    else:
        consequence = (
            f"{frame} en fragilisant {n_rejected} des {n_arguments} arguments "
            f"{node_syntagme}, qui perdent l'assise que l'extension "
            f"{semantics_label} garantit aux autres, et en laissant "
            f"{n_undecided} en suspens : le désaccord qui les concerne n'est "
            "pas tranché par les attaques du graphe"
        )
    return consequence


#: Native status that rides the semantics-label slot when the pipeline files
#: a framework whose extensions were never computed (``verification_unavailable``
#: in compare mode, or a ``degraded: True`` entry): the label parsed back from
#: the name is a STATUS, not a semantics (#3050). Nothing was computed, so
#: there is nothing to cite.
UNAVAILABLE_STATUS = "unavailable"


def appendix_ref(semantics_label: str) -> str:
    """Stable opaque appendix reference, citable from Act II and Act III.

    Returns ``""`` when the label is the native *unavailable* status (#3050):
    no semantics was computed, so no appendix holds machinery to cite — the
    prose names the status itself (see Act II's non-concluable branch), never
    a phantom anchor ``Annexe Dung[unavailable]``.
    """
    label = (semantics_label or "dung").strip().lower().replace(" ", "-")
    if label == UNAVAILABLE_STATUS:
        return ""
    return f"Annexe Dung[{label}]"


# #1914 résidu b — same format knowledge as the producer above, one module.
_REF_RE = re.compile(r"Annexe Dung\[[^\]\n]+\]")


def appendix_refs_in(text: str) -> list[str]:
    """Every appendix ref literally present in ``text``, in order of appearance.

    Lets a conductor (or a guard test) find the refs a prompt carries without
    re-deriving the format — ``appendix_ref`` stays the single producer.
    """
    return _REF_RE.findall(text or "")


def backend_provenance() -> str:
    """Honest backend line for the appendix — the state carries no solver
    tag on verification_* entries (state_writers), so the protocol names the
    writer and says the solver is unlabelled rather than guessing one."""
    return (
        "protocole : cadre natif verification_* écrit par les state writers ; "
        "solveur non étiqueté dans l'état"
    )
