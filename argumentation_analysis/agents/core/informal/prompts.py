"""
Prompts pour l'agent d'analyse informelle.

Ce module définit les chaînes de caractères multilignes utilisées comme prompts
pour guider le modèle de langage (LLM) dans ses tâches d'analyse informelle,
telles que l'identification d'arguments, l'analyse de sophismes, et la
justification de l'attribution de sophismes.
"""
# agents/core/informal/prompts.py
import logging

# --- Fonction Sémantique (Prompt) pour Identification Arguments (V8 - Amélioré) ---
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

# --- Fonction Sémantique (Prompt) pour Analyse de Sophismes (Nouveau) ---
prompt_analyze_fallacies_v1 = """
[Instructions]
Analysez l'argument fourni ($input) et identifiez les sophismes potentiels qu'il contient.

Pour chaque sophisme identifié, vous devez:
1. Nommer précisément le type de sophisme selon la taxonomie standard
2. Expliquer pourquoi cet argument constitue ce type de sophisme
3. Citer la partie spécifique du texte qui illustre le sophisme
4. Proposer une reformulation non fallacieuse de l'argument (si possible)

Concentrez-vous sur les sophismes les plus évidents et significatifs. Soyez précis dans votre analyse.

[Argument à Analyser]
{{$input}}
+++++
[Sophismes Identifiés]
"""

# --- Fonction Sémantique (Prompt) pour Justification d'Attribution (Nouveau) ---
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
logging.getLogger(__name__).debug("Module agents.core.informal.prompts chargé (V8 - Amélioré).")