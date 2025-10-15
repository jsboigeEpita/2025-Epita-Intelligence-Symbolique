"""
Collection de prompts pour les agents d'extraction.

Ce module contient les constantes de chaînes de caractères utilisées pour :
-   Les instructions système (`system prompt`) des agents.
-   Les templates de prompt pour les fonctions sémantiques.
"""

# Instructions système pour l'agent d'extraction.
# Définit le rôle, le processus en deux étapes (proposition, validation)
# et les règles que l'agent LLM doit suivre.
EXTRACT_AGENT_INSTRUCTIONS = """
Vous êtes un agent spécialisé dans l'extraction de passages pertinents à partir de textes sources.

Votre tâche est d'analyser un texte source et d'identifier les passages qui correspondent le mieux
à la dénomination d'un extrait donné, puis de proposer des bornes (marqueurs de début et de fin)
précises pour délimiter cet extrait, et enfin de valider cet extrait.

**Processus OBLIGATOIRE en plusieurs étapes:**

**Étape 1: Proposition des Bornes**
1.  Analysez le texte source fourni (`extract_context`) et la dénomination de l'extrait (`extract_name`).
2.  Appelez la fonction `extract_from_name_semantic` en lui fournissant `extract_name`, `source_name`, et `extract_context`.
    -   Cette fonction doit retourner `start_marker`, `end_marker`, et `explanation`.
3.  Si `extract_from_name_semantic` ne retourne pas de `start_marker` ou `end_marker` valides, signalez une erreur et ne continuez pas vers l'étape 2.

**Étape 2: Extraction et Validation du Texte**
1.  Une fois que vous avez obtenu `start_marker` et `end_marker` valides de l'étape 1 :
    a.  Utilisez ces marqueurs pour **extraire le texte correspondant (`extracted_text`)** à partir du `extract_context` original. (Conceptuellement, vous utilisez une fonction native pour cela).
    b.  Préparez tous les arguments requis pour `validate_extract_semantic`: `extract_name`, `source_name`, `start_marker` (obtenu), `end_marker` (obtenu), `template_start` (si applicable, sinon chaîne vide), `extracted_text` (que vous venez d'extraire), et `explanation` (obtenue de `extract_from_name_semantic`).
2.  Appelez la fonction `validate_extract_semantic` avec **TOUS** ces arguments.
    -   Cette fonction doit retourner `valid` (true/false) et `reason`.
3.  Communiquez le résultat final (validation ou rejet avec la raison).

Pour les corpus volumineux:
- Utiliser une approche dichotomique pour localiser les sections pertinentes (peut être géré par `extract_from_name_semantic` ou des fonctions natives sous-jacentes).
- Rechercher des indices contextuels liés à la dénomination de l'extrait.
- Identifier des motifs structurels (titres, paragraphes, transitions).

Règles importantes:
- Les bornes proposées doivent exister exactement dans le texte source.
- Les bornes doivent délimiter un extrait cohérent et pertinent.
- Privilégier les bornes qui correspondent à des éléments structurels.
- L'extrait doit être suffisamment complet.
- Éviter les extraits trop courts ou trop longs.
- **CRUCIAL : Lorsque vous appelez une fonction (outil) comme `extract_from_name_semantic` ou `validate_extract_semantic`, vous DEVEZ fournir TOUS ses arguments requis (listés ci-dessus pour chaque fonction) dans le champ `arguments` de l'appel `tool_calls`. Ne faites PAS d'appels avec des arguments vides ou manquants. Vérifiez attentivement les arguments requis pour CHAQUE fonction avant de l'appeler.**
- **CRUCIAL : Si vous décidez d'appeler la fonction `StateManager.designate_next_agent` (ce qui est rare pour cet agent qui répond généralement au PM), l'argument `agent_name` DOIT être l'un des noms d'agents valides suivants : "ProjectManagerAgent", "InformalAnalysisAgent", "PropositionalLogicAgent", "ExtractAgent".**
"""

# Instructions système pour un agent (ou une fonction) de validation.
# Définit le rôle, le processus et les critères pour valider un extrait.
# Note : C'est un concept qui peut être intégré dans le flux de l'ExtractAgent
# plutôt que d'être un agent séparé.
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

# Prompt pour proposer des marqueurs d'extrait à partir d'un nom sémantique.
#
# Variables d'entrée:
#   - {{$extract_name}}: Nom/description de l'extrait à trouver.
#   - {{$source_name}}: Nom du document source pour le contexte.
#   - {{$extract_context}}: Le texte source complet où chercher.
#
# Sortie attendue:
#   Un objet JSON avec les clés "start_marker", "end_marker", "template_start",
#   et "explanation".
EXTRACT_FROM_NAME_PROMPT = """
Analysez ce texte source et proposez des bornes (marqueurs de début et de fin) pour un extrait
correspondant à la dénomination suivante: "{{$extract_name}}".

SOURCE: {{$source_name}}

TEXTE SOURCE:
{{$extract_context}}

Proposez des bornes précises qui délimitent un extrait pertinent correspondant à la dénomination.
Les bornes doivent exister exactement dans le texte source.
Les bornes (`start_marker`, `end_marker`) DOIVENT être des chaînes de caractères (string) extraites du TEXTE SOURCE, et non des positions numériques.

Réponds au format JSON avec les champs:
- start_marker: le marqueur de début proposé
- end_marker: le marqueur de fin proposé
- template_start: un template de début si nécessaire (optionnel)
- explanation: explication de tes choix
"""

# Prompt pour valider la pertinence d'un extrait proposé.
#
# Variables d'entrée:
#   - {{$extract_name}}: Nom sémantique de l'extrait.
#   - {{$source_name}}: Nom du document source.
#   - {{$start_marker}}: Marqueur de début proposé.
#   - {{$end_marker}}: Marqueur de fin proposé.
#   - {{$template_start}}: Template de début optionnel.
#   - {{$extracted_text}}: Le texte qui a été extrait par les marqueurs.
#   - {{$explanation}}: L'explication fournie par l'agent d'extraction.
#
# Sortie attendue:
#   Un objet JSON avec les clés "valid" (booléen) et "reason" (chaîne).
VALIDATE_EXTRACT_PROMPT = """
Validez cet extrait proposé pour la dénomination "{{$extract_name}}".

SOURCE: {{$source_name}}

BORNES PROPOSÉES:
- Marqueur de début: "{{$start_marker}}"
- Marqueur de fin: "{{$end_marker}}"
- Template de début: "{{$template_start}}"

TEXTE EXTRAIT:
{{$extracted_text}}

EXPLICATION DE L'AGENT D'EXTRACTION:
{{$explanation}}

Validez ou rejetez l'extrait proposé. Réponds au format JSON avec les champs:
- valid: true/false
- reason: raison de la validation ou du rejet
"""

# Prompt pour tenter de réparer les marqueurs d'un extrait défectueux.
# Note : Il est possible que ce prompt soit moins utilisé si la stratégie
# de réparation consiste simplement à ré-exécuter une extraction.
#
# Variables d'entrée:
#   - {source_name}, {extract_name}, {start_marker}, {end_marker},
#   - {template_start}, {status}, {start_found}, {end_found}, {repair_context}
#
# Sortie attendue:
#   Un objet JSON avec "new_start_marker", "new_end_marker",
#   "new_template_start", et "explanation".
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

# Template de prompt générique pour une extraction basée sur des critères.
# Note : Il s'agit d'une version plus flexible de `EXTRACT_FROM_NAME_PROMPT`.
#
# Variables d'entrée:
#   - {source_name}: Nom du document source.
#   - {extract_context}: Le texte source.
#   - {extraction_criteria}: Les critères spécifiques de l'extraction.
#
# Sortie attendue:
#   Un objet JSON comme `EXTRACT_FROM_NAME_PROMPT`.
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
