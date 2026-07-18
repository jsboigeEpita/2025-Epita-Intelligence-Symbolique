"""Synthetic domain-public deliberation propositions (BO-2 #1472 demo).

Bundle of 5 citizen-deliberation propositions for the ``democratech`` demo. All
are **synthetic, domain-public, generic** participatory-budget scenarios — no
real names, no corpus, no politically sensitive content (privacy HARD, #1472).

Each proposition frames 3 divergent options so the governance phase has ≥2
choices to aggregate (governance needs ≥2 to render a genuine verdict — BO-2
#1472). The option wording is deliberately varied across propositions so the
LLM produces distinct extractions → distinct cache keys (also used by the BO-3
#1473 replay-cache batch test).

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
        "Option A : elargir le fonds de livres jeunesse. "
        "Option B : creer un espace numerique avec des ordinateurs en libre acces. "
        "Option C : repartir la somme, moitie fonds livre, moitie espace numerique.",
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
