# -*- coding: utf-8 -*-
"""
Textes calibrés pour tester la détection de sophismes.

Issue #259: Calibration du workflow hiérarchique
Chaque texte contient des sophismes délibérément plantés avec leur famille taxonomique.
"""

# Texte calibré avec 8 sophismes de familles différentes
CALIBRATED_TEXT_8_FALLACIES = """
Le ministre de la Santé a déclaré que ce vaccin est sûr. Comment pouvez-vous douter d'un expert
avec 30 ans de carrière ? D'ailleurs, mon voisin l'a pris et il n'a eu aucun effet secondaire.
Si on commence à douter de la science, bientôt plus personne ne se fera soigner et on retournera
au Moyen Âge avec ses épidémies mortelles. Ceux qui critiquent les vaccins sont soit des ignorants,
soit des complotistes paranoïaques qui croient que la Terre est plate. En plus, 90% des Français
font confiance à la médecine moderne, donc c'est forcément la bonne décision. Écoutez, ce vaccin
existe depuis des générations dans sa forme traditionnelle en Asie, nos ancêtres avaient raison
de faire confiance à la nature. Ceux qui disent qu'il y a des risques cachés veulent juste nous
effrayer pour vendre leurs produits alternatifs miracle. De toute façon, soit vous êtes pour la science,
soit vous êtes contre le progrès - il faut choisir votre camp.
"""

# Mapping des sophismes attendus avec leur chemin taxonomique
EXPECTED_FALLACIES_8 = [
    {
        "name": "Appel à l'autorité",
        "family": "Appel à l'autorité",
        "citation": "Le ministre de la Santé a déclaré que ce vaccin est sûr",
        "path": "Pertinence > Appel à l'autorité",
    },
    {
        "name": "Témoignage anonyme / Anecdote",
        "family": "Appel à l'autorité",
        "citation": "mon voisin l'a pris et il n'a eu aucun effet secondaire",
        "path": "Pertinence > Appel à l'autorité > Témoignage",
    },
    {
        "name": "Pente glissante",
        "family": "Pente glissante",
        "citation": "Si on commence à douter de la science, bientôt plus personne ne se fera soigner",
        "path": "Pertinence > Pente glissante",
    },
    {
        "name": "Attaque ad hominem",
        "family": "Ad hominem",
        "citation": "Ceux qui critiquent les vaccins sont soit des ignorants, soit des complotistes paranoïaques",
        "path": "Attaque > Ad hominem",
    },
    {
        "name": "Appel à la popularité",
        "family": "Appel à la popularité",
        "citation": "90% des Français font confiance à la médecine moderne",
        "path": "Pertinence > Appel à la popularité",
    },
    {
        "name": "Appel à la tradition",
        "family": "Appel à la tradition",
        "citation": "nos ancêtres avaient raison de faire confiance à la nature",
        "path": "Pertinence > Appel à la tradition",
    },
    {
        "name": "Homme de paille",
        "family": "Homme de paille",
        "citation": "Ceux qui disent qu'il y a des risques cachés veulent juste nous effrayer",
        "path": "Attaque > Homme de paille",
    },
    {
        "name": "Faux dilemme",
        "family": "Faux dilemme",
        "citation": "soit vous êtes pour la science, soit vous êtes contre le progrès",
        "path": "Pertinence > Faux dilemme",
    },
]

# Texte EPITA réel (du contexte du projet)
EPITA_TEXT = """
EPITA est une excellente école d'informatique. Le directeur lui-même a affirmé que 98% des
diplômés trouvent un emploi en moins de 3 mois. Ceux qui critiquent l'école sont juste des
jaloux qui n'ont pas réussi à y entrer. D'ailleurs, tous mes amis qui y vont sont très satisfaits.
Si tu ne vas pas à EPITA, tu n'auras jamais de carrière dans l'informatique en France.
"""

EXPECTED_FALLACIES_EPITA = [
    {
        "name": "Appel à l'autorité",
        "family": "Appel à l'autorité",
        "citation": "Le directeur lui-même a affirmé que 98% des diplômés trouvent un emploi",
        "path": "Pertinence > Appel à l'autorité",
    },
    {
        "name": "Attaque ad hominem",
        "family": "Ad hominem",
        "citation": "Ceux qui critiquent l'école sont juste des jaloux qui n'ont pas réussi à y entrer",
        "path": "Attaque > Ad hominem",
    },
]

# Texte neutre (sans sophisme) pour tester les faux positifs
NEUTRAL_TEXT = """
La photosynthèse est le processus par lequel les plantes convertissent l'énergie lumineuse
en énergie chimique. Ce processus se déroule dans les chloroplastes et utilise la chlorophylle
comme pigment principal. Les scientifiques ont découvert que ce processus produit environ
70% de l'oxygène atmosphérique de la Terre. Les recherches continues dans ce domaine
permettent de mieux comprendre comment optimiser la croissance des plantes.
"""

EXPECTED_FALLACIES_NEUTRAL = []  # Aucun sophisme attendu
