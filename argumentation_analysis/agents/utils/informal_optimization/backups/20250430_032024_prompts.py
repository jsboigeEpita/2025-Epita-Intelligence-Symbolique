# agents/informal/prompts.py
import logging

# --- Fonction Sémantique (Prompt) pour Identification Arguments ---
prompt_identify_args_v7 = """
[Instructions]
Analysez le texte argumentatif fourni ($input) et identifiez les principaux arguments ou affirmations distincts.
Listez chaque argument de manière concise, un par ligne. Retournez UNIQUEMENT la liste, sans numérotation ou préambule.
Focalisez-vous sur les affirmations principales défendues ou attaquées.

[Texte à Analyser]
{{$input}}
+++++
[Arguments Identifiés (un par ligne)]
"""

# Log de chargement
logging.getLogger(__name__).debug("Module agents.informal.prompts chargé.")