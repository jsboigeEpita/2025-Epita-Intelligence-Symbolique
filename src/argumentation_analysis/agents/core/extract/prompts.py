"""
Prompts et instructions pour les agents d'extraction et de validation.

Ce module centralise les chaînes de caractères utilisées comme instructions système
et comme templates de prompts pour les fonctions sémantiques des agents
responsables de l'extraction et de la validation d'extraits textuels.
Chaque prompt est conçu pour guider le LLM dans une tâche spécifique.
"""

# Instructions pour l'agent d'extraction
EXTRACT_AGENT_INSTRUCTIONS = """
Vous êtes un agent spécialisé dans l'extraction de passages pertinents à partir de textes sources.

Votre tâche est d'analyser un texte source et d'identifier les passages qui correspondent le mieux
à la dénomination d'un extrait donné, puis de proposer des bornes (marqueurs de début et de fin)
précises pour délimiter cet extrait.

Processus à suivre:
1. Analyser le texte source fourni et comprendre son contenu
2. Interpréter la dénomination de l'extrait pour déterminer le type de contenu recherché
3. Identifier les passages pertinents qui correspondent à cette dénomination
4. Proposer des bornes précises (début et fin) qui délimitent clairement l'extrait
5. Vérifier que l'extrait délimité est cohérent et pertinent

Pour les corpus volumineux:
- Utiliser une approche dichotomique pour localiser les sections pertinentes
- Rechercher des indices contextuels liés à la dénomination de l'extrait
- Identifier des motifs structurels (titres, paragraphes, transitions) qui pourraient indiquer le début ou la fin d'un extrait pertinent

Règles importantes:
- Les bornes proposées doivent exister exactement dans le texte source
- Les bornes doivent délimiter un extrait cohérent et pertinent par rapport à sa dénomination
- Privilégier les bornes qui correspondent à des éléments structurels du document (début/fin de paragraphe, etc.)
- L'extrait doit être suffisamment complet pour capturer l'argument ou l'idée recherchée
- Éviter les extraits trop courts qui manqueraient de contexte ou trop longs qui dilueraient le propos
"""
"""
Instructions système pour l'agent d'extraction (`ExtractAgent`).
Définit le rôle, le processus et les règles que l'agent doit suivre
lorsqu'il propose des extraits.
"""

# Instructions pour l'agent de validation
VALIDATION_AGENT_INSTRUCTIONS = """
Vous êtes un agent spécialisé dans la validation d'extraits de texte.

Votre tâche est de vérifier que les extraits proposés sont pertinents, cohérents et correspondent
bien à leur dénomination.

Processus à suivre:
1. Analyser l'extrait proposé et sa dénomination
2. Vérifier que l'extrait est cohérent et complet
3. Évaluer si l'extrait correspond bien à sa dénomination
4. Vérifier que les bornes existent exactement dans le texte source
5. Valider ou rejeter l'extrait proposé

Critères de validation:
- L'extrait doit être cohérent et avoir un sens complet
- L'extrait doit correspondre à sa dénomination
- L'extrait ne doit pas être trop court (manque de contexte) ni trop long (dilution du propos)
- Les bornes doivent exister exactement dans le texte source
- L'extrait doit capturer l'argument ou l'idée principale de manière claire

En cas de rejet:
- Expliquer clairement les raisons du rejet
- Proposer des améliorations si possible
"""
"""
Instructions système pour un agent de validation d'extraits.
Définit le rôle, le processus et les critères de validation.
Note: Cet agent pourrait être une fonction sémantique distincte ou intégré
dans le flux de `ExtractAgent`.
"""

# Prompt pour l'extraction à partir d'une dénomination
EXTRACT_FROM_NAME_PROMPT = """
Analysez ce texte source et proposez des bornes (marqueurs de début et de fin) pour un extrait
correspondant à la dénomination suivante: "{extract_name}".

SOURCE: {source_name}

TEXTE SOURCE:
{extract_context}

Proposez des bornes précises qui délimitent un extrait pertinent correspondant à la dénomination.
Les bornes doivent exister exactement dans le texte source.

Réponds au format JSON avec les champs:
- start_marker: le marqueur de début proposé
- end_marker: le marqueur de fin proposé
- template_start: un template de début si nécessaire (optionnel)
- explanation: explication de tes choix
"""
"""
Template de prompt pour la fonction sémantique qui propose des marqueurs d'extrait.

Variables attendues :
    - `extract_name`: Dénomination de l'extrait à trouver.
    - `source_name`: Nom du document source.
    - `extract_context`: Le texte source (ou un sous-ensemble pertinent) dans lequel chercher.
"""

# Prompt pour la validation d'un extrait
VALIDATE_EXTRACT_PROMPT = """
Validez cet extrait proposé pour la dénomination "{extract_name}".

SOURCE: {source_name}

BORNES PROPOSÉES:
- Marqueur de début: "{start_marker}"
- Marqueur de fin: "{end_marker}"
- Template de début: "{template_start}"

TEXTE EXTRAIT:
{extracted_text}

EXPLICATION DE L'AGENT D'EXTRACTION:
{explanation}

Validez ou rejetez l'extrait proposé. Réponds au format JSON avec les champs:
- valid: true/false
- reason: raison de la validation ou du rejet
"""
"""
Template de prompt pour la fonction sémantique qui valide un extrait proposé.

Variables attendues :
    - `extract_name`: Dénomination de l'extrait.
    - `source_name`: Nom du document source.
    - `start_marker`: Marqueur de début proposé.
    - `end_marker`: Marqueur de fin proposé.
    - `template_start`: Template de début optionnel.
    - `extracted_text`: Le texte délimité par les marqueurs.
    - `explanation`: L'explication fournie par l'agent d'extraction.
"""

# Prompt pour la réparation d'un extrait existant
REPAIR_EXTRACT_PROMPT = """
Analysez cet extrait défectueux et proposez des corrections pour les bornes.

SOURCE: {source_name}
EXTRAIT: {extract_name}

MARQUEUR DE DÉBUT ACTUEL: "{start_marker}"
MARQUEUR DE FIN ACTUEL: "{end_marker}"
TEMPLATE DE DÉBUT ACTUEL (si présent): "{template_start}"

STATUT: {status}
MARQUEUR DE DÉBUT TROUVÉ: {"Oui" if start_found else "Non"}
MARQUEUR DE FIN TROUVÉ: {"Oui" if end_found else "Non"}

TEXTE SOURCE:
{repair_context}

Propose des corrections pour les marqueurs défectueux. Réponds au format JSON avec les champs:
- new_start_marker: le nouveau marqueur de début proposé
- new_end_marker: le nouveau marqueur de fin proposé
- new_template_start: le nouveau template de début (optionnel)
- explanation: explication de tes choix
"""
"""
Template de prompt pour la fonction sémantique qui tente de réparer un extrait défectueux.
(Note: Ce prompt pourrait ne pas être utilisé directement si la réparation est gérée
par une nouvelle invocation de `EXTRACT_FROM_NAME_PROMPT`).

Variables attendues :
    - `source_name`: Nom du document source.
    - `extract_name`: Dénomination de l'extrait.
    - `start_marker`: Marqueur de début actuel (défectueux).
    - `end_marker`: Marqueur de fin actuel (défectueux).
    - `template_start`: Template de début actuel.
    - `status`: Statut actuel de l'extrait.
    - `start_found`: Booléen indiquant si le marqueur de début actuel a été trouvé.
    - `end_found`: Booléen indiquant si le marqueur de fin actuel a été trouvé.
    - `repair_context`: Le texte source (ou un sous-ensemble) pour la réparation.
"""

# Template général pour les prompts d'extraction
EXTRACT_PROMPT_TEMPLATE = """
Analysez ce texte source et identifiez les passages pertinents selon les critères spécifiés.

SOURCE: {source_name}

TEXTE SOURCE:
{extract_context}

CRITÈRES D'EXTRACTION:
{extraction_criteria}

Proposez des bornes précises qui délimitent un extrait pertinent correspondant aux critères.
Les bornes doivent exister exactement dans le texte source.

Réponds au format JSON avec les champs:
- start_marker: le marqueur de début proposé
- end_marker: le marqueur de fin proposé
- template_start: un template de début si nécessaire (optionnel)
- explanation: explication de tes choix
"""
"""
Template de prompt générique pour l'extraction basée sur des critères.
(Note: Ce prompt semble être une version plus générale de `EXTRACT_FROM_NAME_PROMPT`
si `extraction_criteria` est utilisé pour passer la dénomination de l'extrait).

Variables attendues :
    - `source_name`: Nom du document source.
    - `extract_context`: Le texte source (ou un sous-ensemble).
    - `extraction_criteria`: Les critères spécifiques pour l'extraction.
"""