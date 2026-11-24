"""Synthetic domain-public deliberation propositions (BO-2 #1472 demo).

Bundle of 5 citizen-deliberation propositions for the ``democratech`` demo. All
are **synthetic, domain-public, generic** participatory-budget scenarios — no
real names, no corpus, no politically sensitive content (privacy HARD, #1472).

Each proposition frames 3 divergent options so the governance phase has ≥2
choices to aggregate (governance needs ≥2 to render a genuine verdict — BO-2
#1472). The option wording is deliberately varied across propositions so the
LLM produces distinct extractions → distinct cache keys (also used by the BO-3
#1473 replay-cache batch test).

**A proposition that only enumerates is not argumentative (#3679 item 40d).**
The fact-extraction phase returns zero arguments on a text that names possible
uses without defending any; the #1909 gate then classifies the document as
``non_argumentative`` and the remaining phases are skipped, so the demo cannot
render the firsthand verdict its DoD asks for. prop_B was measured that way
(record run 45351057154, Haiku route: 0 argument, 5 claims, 8 phases skipped)
and now gives the reason of each of its three options. prop_A extracted 3
arguments on the same route with the wording below and is kept as measured.
prop_C to prop_E are not selected by the demo's test (``limit=2``) and were not
measured on that route: they enumerate their options the way prop_B used to.

IDs are opaque (prop_A..prop_E) for any GitHub-indexed surface.
"""

from typing import Dict

# (opaque_id, human_label_for_display_only, proposition_text)
SYNTHETIC_PROPOSITIONS = (
    (
        "prop_A",
        "Chess club — annual budget",
        "Le club d'echecs dispose d'un budget participatif annuel de 2000 euros. "
        "Trois options divergentes s'affrontent. "
        "Option A : organiser un tournoi inter-villes avec buffet et prix pour 2000 "
        "euros, augmentant la visibilite du club. "
        "Option B : investir les 2000 euros en materiel pedagogique et echiquiers neufs. "
        "Option C : un format hybride, 1000 euros tournoi reduit et 1000 euros materiel.",
    ),
    (
        "prop_B",
        "Neighborhood library — exceptional grant",
        "La bibliotheque de quartier beneficie d'une subvention exceptionnelle de "
        "3000 euros. Trois usages sont en concurrence. "
        # #3679 item 40d — each option carries its reason. Without one the
        # text names three possible uses and defends none, so a faithful
        # extraction returns zero arguments and the #1909 gate reads the
        # document as non-argumentative (record run 45351057154: 0 argument,
        # 5 claims, 8 of 10 phases skipped). A correct reading of a fixture
        # that did not argue, hence a fixture change and not a prompt one.
        "Option A : elargir le fonds de livres jeunesse, car le fonds actuel "
        "vieillit et les plus jeunes lecteurs sont les plus nombreux. "
        "Option B : creer un espace numerique avec des ordinateurs en libre "
        "acces, pour reduire la fracture numerique du quartier. "
        "Option C : repartir la somme, moitie fonds livre, moitie espace "
        "numerique, afin de servir les deux publics sans en favoriser un.",
    ),
    (
        "prop_C",
        "Sports association — subsidy allocation",
        "L'association sportive municipale dispose de 1500 euros de subvention a "
        "allouer. Trois pistes sont proposees. "
        "Option A : acheter des equipements collectifs (ballons, filets, vestiaires). "
        "Option B : financer des stages de formation pour les entraineurs benevoles. "
        "Option C : repartir equitablement entre equipement et formation.",
    ),
    (
        "prop_D",
        "District park — improvement budget",
        "Le comite de quartier a 2500 euros pour amenager un parc local. "
        "Trois options sont debattues. "
        "Option A : installer des jeux pour enfants et des bancs. "
        "Option B : planter une voie verdoyante et un potager partage. "
        "Option C : moitie jeux, moitie verdurisation.",
    ),
    (
        "prop_E",
        "Music school — equipment fund",
        "L'ecole de musique associative a leve 1800 euros. Trois projets "
        "concurrents emergent. "
        "Option A : renouveler les instruments d'etude (pianos, guitares). "
        "Option B : financer des bourses pour les eleves en difficulte. "
        "Option C : repartir entre instruments et bourses.",
    ),
)


def get_propositions() -> Dict[str, Dict[str, str]]:
    """Return the bundle as ``{opaque_id: {label, text}}`` for the demo driver."""
    return {
        pid: {"label": label, "text": text}
        for pid, label, text in SYNTHETIC_PROPOSITIONS
    }
