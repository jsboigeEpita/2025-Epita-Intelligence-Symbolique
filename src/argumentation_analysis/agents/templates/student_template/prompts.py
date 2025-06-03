"""
Prompts utilisés par l'agent étudiant pour les interactions avec les modèles de langage.
"""

# Prompt système qui définit le rôle et les capacités du modèle
SYSTEM_PROMPT = """
Tu es un assistant spécialisé dans l'analyse d'argumentation. Ta tâche est d'analyser 
le texte fourni et d'identifier les éléments clés de l'argumentation selon les instructions.

Voici comment tu dois procéder:
1. Identifie la thèse principale défendue dans le texte
2. Repère les arguments utilisés pour soutenir cette thèse
3. Identifie les prémisses et les conclusions de chaque argument
4. Évalue la qualité logique de chaque argument
5. Identifie les éventuelles faiblesses ou sophismes dans l'argumentation

Réponds de manière structurée en utilisant le format demandé dans les instructions.
"""

# Template de prompt utilisateur qui sera complété avec les données spécifiques
USER_PROMPT_TEMPLATE = """
Analyse le texte suivant et identifie les éléments clés de l'argumentation:

TEXTE:
{text}

CONTEXTE (si disponible):
{context}

Réponds en utilisant le format suivant:
1. Thèse principale: [La thèse défendue dans le texte]
2. Arguments:
   - Argument 1:
     * Prémisses: [Liste des prémisses]
     * Conclusion: [Conclusion de l'argument]
     * Évaluation: [Évaluation de la qualité logique]
   - Argument 2:
     * [...]
3. Faiblesses/Sophismes:
   - [Liste des faiblesses ou sophismes identifiés]
4. Évaluation globale: [Évaluation de la qualité globale de l'argumentation]
"""

# Vous pouvez définir d'autres prompts spécifiques à votre agent ici

# Prompt pour l'analyse détaillée d'un argument spécifique
ARGUMENT_ANALYSIS_PROMPT = """
Analyse en détail l'argument suivant:

ARGUMENT:
{argument}

Réponds en utilisant le format suivant:
1. Structure logique: [Forme logique de l'argument]
2. Validité: [L'argument est-il valide logiquement?]
3. Solidité: [L'argument est-il solide (prémisses vraies)?]
4. Forces: [Points forts de l'argument]
5. Faiblesses: [Points faibles de l'argument]
6. Suggestions d'amélioration: [Comment l'argument pourrait être renforcé]
"""

# Prompt pour l'identification des sophismes
FALLACY_IDENTIFICATION_PROMPT = """
Identifie les sophismes présents dans le texte suivant:

TEXTE:
{text}

Pour chaque sophisme identifié, fournis:
1. Type de sophisme
2. Citation exacte du texte où le sophisme apparaît
3. Explication de pourquoi il s'agit d'un sophisme
4. Suggestion pour corriger ou éviter ce sophisme
"""