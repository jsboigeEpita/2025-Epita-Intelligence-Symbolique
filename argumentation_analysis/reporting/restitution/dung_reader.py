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
    "un argument accepté garde son assise dans le graphe face aux attaques "
    "reçues"
)
REJECTED_MEANS = (
    "un argument rejeté perd cette assise dans le graphe, rien de plus : "
    "ses soutiens n'y survivent pas aux attaques"
)


def reader_consequence(
    n_arguments: int,
    n_attacks: int,
    n_rejected: int,
    semantics_label: str,
) -> str:
    """The digested Dung consequence for the body — no extension list, no
    serialized edges, no raw counts dump.

    Frames the graph as a reorganisation of the extracted arguments (#1280)
    and says what changed for the reader's judgment, not what the solver
    printed.
    """
    frame = (
        f"le graphe d'attaque construit sur les {n_arguments} arguments "
        f"extraits ({n_attacks} relations d'attaque, sémantique "
        f"{semantics_label}) réorganise le matériau"
    )
    if n_rejected == 0:
        consequence = (
            f"{frame} sans fragiliser aucun argument : chaque position "
            "conserve son assise face aux attaques reçues"
        )
    else:
        # Morphology-free French: the « (s) » alternation is a solver-output
        # marker the readability gate now tracks (#1908) — the digested
        # consequence must read as prose, not as machine output.
        consequence = (
            f"{frame} en fragilisant {n_rejected} des {n_arguments} arguments "
            f"extraits, qui perdent l'assise que l'extension {semantics_label} "
            "garantit aux autres"
        )
    return consequence


def appendix_ref(semantics_label: str) -> str:
    """Stable opaque appendix reference, citable from Act II and Act III."""
    label = (semantics_label or "dung").strip().lower().replace(" ", "-")
    return f"Annexe Dung[{label}]"


def backend_provenance() -> str:
    """Honest backend line for the appendix — the state carries no solver
    tag on verification_* entries (state_writers), so the protocol names the
    writer and says the solver is unlabelled rather than guessing one."""
    return (
        "protocole : cadre natif verification_* écrit par les state writers ; "
        "solveur non étiqueté dans l'état"
    )
