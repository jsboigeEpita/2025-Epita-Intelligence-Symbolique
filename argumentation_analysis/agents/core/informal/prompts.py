"""
Prompts pour l'agent d'analyse informelle des arguments.

Ce module centralise les templates de prompts utilisés par `InformalAnalysisAgent`
pour interagir avec les modèles de langage (LLM). Ces prompts sont conçus pour
des tâches spécifiques telles que :
    - L'identification d'arguments distincts dans un texte.
    - L'analyse d'un argument pour y détecter des sophismes potentiels.
    - La justification détaillée de l'attribution d'un type de sophisme spécifique
      à un argument donné.

Chaque prompt spécifie le format d'entrée attendu (via des variables comme `{{$input}}`)
et le format de sortie souhaité.
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
"""
Prompt pour l'identification d'arguments (Version 8).

Demande au LLM d'analyser un texte (`$input`) et d'extraire les arguments
ou affirmations distincts, en respectant des critères de clarté, concision,
et neutralité. La sortie attendue est une liste d'arguments, un par ligne.
"""

# --- Fonction Sémantique (Prompt) pour Analyse de Sophismes (Nouveau) ---
prompt_analyze_fallacies_v2 = """
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
"""
Prompt pour l'analyse des sophismes dans un argument donné (Version 2).

Demande au LLM d'identifier les sophismes dans un argument (`$input`) et de retourner
le résultat sous forme d'un objet JSON structuré. Si aucun sophisme n'est trouvé,
il doit retourner une liste vide.
"""
# Renommer l'ancien prompt pour référence, mais utiliser le nouveau
prompt_analyze_fallacies_v1 = prompt_analyze_fallacies_v2

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
"""
Prompt pour la justification de l'attribution d'un sophisme (Version 1).

Demande au LLM de fournir une justification détaillée expliquant pourquoi
un argument (`$argument`) spécifique contient un type de sophisme donné
(`$fallacy_type`), en s'appuyant sur la définition du sophisme
(`$fallacy_definition`). La justification doit inclure une explication
du mécanisme, des citations, un exemple et l'impact du sophisme.
"""

# Log de chargement
logging.getLogger(__name__).debug("Module agents.core.informal.prompts chargé (V8 - Amélioré, AnalyzeFallacies V1).")