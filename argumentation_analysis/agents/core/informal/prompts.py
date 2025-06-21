"""
Collection de prompts pour les fonctions sémantiques de l'analyse informelle.

Ce module contient les chaînes de caractères formatées (templates) utilisées
comme prompts pour les fonctions sémantiques du `InformalAnalysisAgent`.
Chaque prompt est une constante de module conçue pour une tâche LLM spécifique.
"""
# agents/core/informal/prompts.py
import logging

# --- Prompt pour l'Identification d'Arguments ---
# Ce prompt demande au LLM d'extraire les arguments ou affirmations distincts
# d'un texte.
#
# Variables:
#   - {{$input}}: Le texte brut à analyser.
#
# Sortie attendue:
#   Une liste d'arguments, formatée avec un argument par ligne.
prompt_identify_args_v8 = """
[Instructions]
Analysez le texte argumentatif fourni ($input) et identifiez tous les arguments ou affirmations distincts.

Un bon argument doit:
1. Exprimer une position claire ou une affirmation défendable
2. Être concis (idéalement 10-20 mots)
3. Capturer une idée complète sans détails superflus
4. Être formulé de manière neutre et précise

Pour chaque argument identifié:
- Formulez-le comme une affirmation simple et directe
- Concentrez-vous sur les affirmations principales défendues ou attaquées
- Évitez les formulations trop longues ou trop complexes
- Assurez-vous de capturer tous les arguments importants, même secondaires

Retournez UNIQUEMENT la liste des arguments, un par ligne, sans numérotation, préambule ou commentaire.

[Texte à Analyser]
{{$input}}
+++++
[Arguments Identifiés (un par ligne)]
"""

# --- Prompt pour l'Analyse de Sophismes ---
# Ce prompt demande au LLM d'analyser un argument et d'identifier les
# sophismes potentiels.
#
# Variables:
#   - {{$input}}: L'argument à analyser.
#
# Sortie attendue:
#   Un objet JSON unique avec une clé "sophismes", contenant une liste
#   d'objets. Chaque objet représente un sophisme et doit contenir les clés
#   "nom", "explication", "citation", et "reformulation".
prompt_analyze_fallacies_v1 = """
[Instructions]
Analysez l'argument fourni ($input) et identifiez les sophismes potentiels qu'il contient.
Votre réponse doit être un objet JSON valide contenant une seule clé "sophismes", qui est une liste d'objets.
Chaque objet doit représenter un sophisme identifié et contenir les clés suivantes : "nom", "explication", "citation", "reformulation".
Si aucun sophisme n'est identifié, retournez un objet JSON avec une liste vide : {"sophismes": []}.
Ne retournez aucun texte ou explication en dehors de l'objet JSON.

[Argument à Analyser]
{{$input}}
+++++
[Sophismes Identifiés (JSON)]
"""

# --- Prompt pour la Justification d'Attribution de Sophisme ---
# Ce prompt guide le LLM pour qu'il rédige une justification détaillée
# expliquant pourquoi un argument donné correspond à un type de sophisme
# spécifique.
#
# Variables:
#   - {{$argument}}: L'argument analysé.
#   - {{$fallacy_type}}: Le nom du sophisme à justifier.
#   - {{$fallacy_definition}}: La définition du sophisme pour contextualiser.
#
# Sortie attendue:
#   Un texte de justification structuré et détaillé.
prompt_justify_fallacy_attribution_v1 = """
[Instructions]
Vous devez justifier pourquoi l'argument fourni contient le sophisme spécifié.

Votre justification doit:
1. Expliquer clairement le mécanisme du sophisme indiqué
2. Montrer précisément comment l'argument correspond à ce type de sophisme
3. Citer des parties spécifiques de l'argument qui illustrent le sophisme
4. Fournir un exemple similaire pour clarifier (si pertinent)
5. Expliquer l'impact de ce sophisme sur la validité de l'argument

[Argument]
{{$argument}}

[Sophisme à Justifier]
{{$fallacy_type}}

[Définition du Sophisme]
{{$fallacy_definition}}
+++++
[Justification Détaillée]
"""

# Log de chargement
logging.getLogger(__name__).debug("Module agents.core.informal.prompts chargé (V8 - Amélioré, AnalyzeFallacies V1).")