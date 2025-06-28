"""
Prompts pour l'interaction avec les LLMs.

Ce module contient les templates de prompts utilisés pour
interagir avec les grands modèles de langage (LLMs).
"""

# Prompt pour l'analyse d'un argument
ARGUMENT_ANALYSIS_PROMPT = """
Analysez la structure de l'argument suivant. Identifiez les prémisses, la conclusion, et le type d'argument.

Argument: "{argument_text}"

Fournissez votre analyse sous la forme suivante:
- Prémisses: [Liste des prémisses]
- Conclusion: [La conclusion de l'argument]
- Type d'argument: [déductif/inductif/abductif]
- Explication: [Courte explication sur la structure et la logique de l'argument]
"""

# Prompt pour l'identification des vulnérabilités
VULNERABILITY_IDENTIFICATION_PROMPT = """
Identifiez les vulnérabilités dans l'argument suivant.

Argument: "{argument_text}"

Prémisses:
{premises}

Conclusion: {conclusion}

Type d'argument: {argument_type}

Analysez cet argument et identifiez ses vulnérabilités potentielles. Pour chaque vulnérabilité, spécifiez:
1. Le type de vulnérabilité
2. La partie de l'argument concernée (prémisse spécifique, conclusion, ou structure globale)
3. Une brève description du problème
4. Un score de vulnérabilité de 0 à 1, où 1 représente une vulnérabilité critique
5. Le type de contre-argument recommandé (réfutation directe, contre-exemple, remise en question des prémisses, explication alternative, réduction à l'absurde)

Fournissez votre réponse au format JSON:
{{
  "vulnerabilities": [
    {{
      "type": "type_de_vulnerabilite",
      "target": "cible",
      "description": "description",
      "score": 0.8,
      "suggested_counter_type": "direct_refutation"
    }},
    ...
  ]
}}

Les types de contre-arguments possibles sont: "direct_refutation", "counter_example", "premise_challenge", "alternative_explanation", "reductio_ad_absurdum".
"""

# Prompt pour la génération de contre-arguments
COUNTER_ARGUMENT_GENERATION_PROMPT = """
Générez un contre-argument pour l'argument suivant.

Argument original: "{argument_text}"

Prémisses:
{premises}

Conclusion: {conclusion}

Type d'argument: {argument_type}

Vulnérabilités identifiées:
{vulnerabilities}

Type de contre-argument à générer: {counter_type}
Stratégie rhétorique à utiliser: {rhetorical_strategy}

Générez un contre-argument pertinent et convaincant qui exploite les vulnérabilités identifiées. Utilisez la stratégie rhétorique spécifiée.

Fournissez votre réponse au format JSON:
{{
  "counter_argument": "Texte du contre-argument",
  "target_component": "La partie de l'argument ciblée (prémisse, conclusion, structure)",
  "strength": "decisive|strong|moderate|weak",
  "confidence": 0.8,
  "supporting_evidence": ["Preuve 1", "Preuve 2", ...],
  "rhetorical_strategy": "La stratégie rhétorique que vous avez utilisée",
  "explanation": "Explication de la stratégie utilisée"
}}

Les valeurs possibles pour "strength" sont: "weak", "moderate", "strong", "decisive".
Les stratégies rhétoriques possibles sont: "socratic_questioning", "reductio_ad_absurdum", "analogical_counter", "authority_appeal", "statistical_evidence".
"""

# Prompt pour l'évaluation de contre-arguments
COUNTER_ARGUMENT_EVALUATION_PROMPT = """
Évaluez la qualité du contre-argument suivant.

Argument original: "{original_argument}"

Contre-argument: "{counter_argument}"

Type de contre-argument: {counter_type}
Stratégie rhétorique utilisée: {rhetorical_strategy}

Évaluez ce contre-argument selon les critères suivants (score de 0 à 1):
1. Pertinence: À quel point le contre-argument cible-t-il l'argument original?
2. Force logique: La structure logique est-elle solide?
3. Persuasion: Le contre-argument est-il convaincant?
4. Originalité: Le contre-argument propose-t-il un angle intéressant ou inattendu?
5. Clarté: Le contre-argument est-il clairement exprimé et facile à comprendre?

Fournissez également des recommandations pour améliorer ce contre-argument.

Répondez au format JSON:
{{
  "scores": {{
    "relevance": 0.8,
    "logical_strength": 0.7,
    "persuasiveness": 0.75,
    "originality": 0.6,
    "clarity": 0.9
  }},
  "overall_score": 0.75,
  "recommendations": [
    "Recommandation 1",
    "Recommandation 2",
    ...
  ],
  "explanation": "Explication détaillée de l'évaluation"
}}
"""


def format_prompt(template: str, **kwargs) -> str:
    """
    Formate un template de prompt avec les valeurs fournies.
    
    Args:
        template: Le template de prompt à formater
        **kwargs: Les valeurs à insérer dans le template
        
    Returns:
        Le prompt formaté
    """
    return template.format(**kwargs) 