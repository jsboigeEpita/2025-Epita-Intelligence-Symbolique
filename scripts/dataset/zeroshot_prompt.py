"""Single source of the zero-shot analyst prompt (#2841 retouche).

Moved verbatim from ``scripts/run_capstone_c1.py`` so importers do not
inherit that script's import-time side effects (``sys.path`` insertion,
``os.chdir`` to the repo root, ``load_dotenv``). The capstone script and
the corpus-campaign arm producer both import the prompt from here — a
copy would drift.
"""

ZEROSHOT_PROMPT = """Tu es un analyste rhétorique expert. Analyse le texte suivant de manière exhaustive.

Pour chaque argument identifié, fournis :
1. La thèse de l'argument
2. Les prémisses explicites et implicites
3. Le type de raisonnement (déductif, inductif, analogique, causal, etc.)
4. Tout sophisme ou erreur de raisonnement détecté (avec la famille : appel à l'autorité, homme de paille, faux dilemme, pente glissante, etc.)
5. La force persuasive de l'argument (1-10)

Ensuite, fournis une évaluation globale :
6. La structure argumentative du texte (nombre et types d'arguments)
7. Les stratégies rhétoriques employées
8. Les points forts et les faiblesses de l'argumentation
9. Une conclusion sur la qualité globale de l'argumentation

Texte :
---
{text}
---"""
