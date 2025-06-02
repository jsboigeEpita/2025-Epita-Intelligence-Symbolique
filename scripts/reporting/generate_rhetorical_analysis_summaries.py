#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour générer des synthèses des analyses rhétoriques avec des extraits concrets.

Ce script:
1. Simule le chargement des extraits déchiffrés (discours d'Hitler, débats Lincoln Douglas)
2. Génère des analyses rhétoriques synthétiques mais réalistes pour ces extraits
3. Produit des synthèses au format Markdown avec:
   - Un résumé de l'analyse pour chaque extrait
   - Des extraits concrets du texte analysé
   - Des exemples de sophismes détectés avec leur contexte
   - Des métriques d'analyse (scores de cohérence, nombre de sophismes, etc.)
   - Des liens vers des analyses plus détaillées
4. Crée un rapport de synthèse global comparant les différents agents
5. Sauvegarde ces synthèses dans le répertoire results/

Auteur: Roo
Date: 15/05/2025
"""

import os
import sys
import json
import random
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("RhetoricalAnalysisSummaries")

# Définition des sources et extraits simulés
SIMULATED_SOURCES = [
    {
        "source_name": "Discours d'Hitler",
        "extracts": [
            {"extract_name": "Discours du Reichstag (1939)", "type": "discours_politique"},
            {"extract_name": "Discours de Nuremberg (1934)", "type": "discours_politique"},
            {"extract_name": "Discours à Munich (1923)", "type": "discours_politique"},
            {"extract_name": "Discours sur l'annexion de l'Autriche (1938)", "type": "discours_politique"},
            {"extract_name": "Discours sur le pacte germano-soviétique (1939)", "type": "discours_politique"}
        ]
    },
    {
        "source_name": "Débats Lincoln-Douglas",
        "extracts": [
            {"extract_name": "Débat d'Ottawa (1858)", "type": "debat_politique"},
            {"extract_name": "Débat de Freeport (1858)", "type": "debat_politique"},
            {"extract_name": "Débat de Jonesboro (1858)", "type": "debat_politique"},
            {"extract_name": "Débat de Charleston (1858)", "type": "debat_politique"},
            {"extract_name": "Débat d'Alton (1858)", "type": "debat_politique"}
        ]
    }
]
# Définition des agents d'analyse rhétorique
RHETORICAL_AGENTS = [
    {
        "name": "Agent de base",
        "tools": [
            "ContextualFallacyDetector",
            "ArgumentCoherenceEvaluator",
            "SemanticArgumentAnalyzer"
        ],
        "strengths": [
            "Détection des sophismes de base",
            "Évaluation simple de la cohérence",
            "Analyse sémantique basique"
        ],
        "weaknesses": [
            "Analyse contextuelle limitée",
            "Pas de détection des sophismes complexes",
            "Pas d'évaluation de la gravité des sophismes"
        ]
    },
    {
        "name": "Agent avancé",
        "tools": [
            "EnhancedComplexFallacyAnalyzer",
            "EnhancedContextualFallacyAnalyzer",
            "EnhancedFallacySeverityEvaluator",
            "EnhancedRhetoricalResultAnalyzer"
        ],
        "strengths": [
            "Détection des sophismes complexes",
            "Analyse contextuelle approfondie",
            "Évaluation de la gravité des sophismes",
            "Recommandations détaillées"
        ],
        "weaknesses": [
            "Temps d'analyse plus long",
            "Complexité d'interprétation des résultats",
            "Sensibilité aux nuances contextuelles"
        ]
    }
]

# Définition des sophismes courants
COMMON_FALLACIES = [
    {
        "name": "Ad hominem",
        "description": "Attaque personnelle plutôt que l'argument",
        "severity": "Élevée",
        "examples": [
            "Son argument est invalide car il a un casier judiciaire.",
            "Comment peut-on faire confiance à quelqu'un qui a menti dans le passé?"
        ]
    },
    {
        "name": "Appel à l'autorité",
        "description": "Utilisation inappropriée d'une figure d'autorité pour soutenir un argument",
        "severity": "Modérée",
        "examples": [
            "Le Dr. Smith, qui est un physicien renommé, affirme que ce régime fonctionne.",
            "Selon un expert, cette théorie est correcte."
        ]
    },
    {
        "name": "Faux dilemme",
        "description": "Présentation de deux options comme les seules possibles alors qu'il en existe d'autres",
        "severity": "Modérée",
        "examples": [
            "Soit vous êtes avec nous, soit vous êtes contre nous.",
            "Nous devons choisir entre la liberté et la sécurité."
        ]
    },
    {
        "name": "Pente glissante",
        "description": "Suggestion qu'une action mènera inévitablement à une série d'événements négatifs",
        "severity": "Modérée",
        "examples": [
            "Si nous autorisons cela, bientôt tout sera permis.",
            "Si nous cédons sur ce point, nous devrons céder sur tous les autres."
        ]
    },
    {
        "name": "Appel à la peur",
        "description": "Utilisation de la peur pour influencer l'opinion",
        "severity": "Élevée",
        "examples": [
            "Si nous ne prenons pas ces mesures, notre nation sera détruite.",
            "Sans cette loi, le chaos règnera dans nos rues."
        ]
    },
    {
        "name": "Homme de paille",
        "description": "Déformation de l'argument de l'adversaire pour le rendre plus facile à attaquer",
        "severity": "Élevée",
        "examples": [
            "Vous voulez réduire le budget militaire, donc vous voulez laisser notre pays sans défense.",
            "Vous êtes en faveur de la régulation, donc vous êtes contre la liberté d'entreprise."
        ]
    }
]

def generate_sample_text(extract_type: str) -> str:
    """
    Génère un texte d'exemple pour un type d'extrait donné.
    
    Args:
        extract_type (str): Type d'extrait (discours_politique, debat_politique, etc.)
        
    Returns:
        str: Texte d'exemple généré
    """
    if extract_type == "discours_politique" and "Hitler" in extract_type:
        return """
        Le peuple allemand a été trahi par les forces qui cherchent à détruire notre nation. 
        Nous ne pouvons pas rester les bras croisés pendant que nos ennemis complotent contre nous.
        L'Allemagne doit se lever et prendre sa place légitime dans le monde.
        Ceux qui s'opposent à notre vision seront balayés par la force de notre détermination.
        Notre peuple mérite un espace vital, et nous ne reculerons devant rien pour l'obtenir.
        L'histoire jugera nos actions comme nécessaires pour la survie de notre race.
        """
    elif extract_type == "discours_politique":
        return """
        Le peuple allemand a été trahi par les forces qui cherchent à détruire notre nation. 
        Nous ne pouvons pas rester les bras croisés pendant que nos ennemis complotent contre nous.
        L'Allemagne doit se lever et prendre sa place légitime dans le monde.
        Ceux qui s'opposent à notre vision seront balayés par la force de notre détermination.
        Notre peuple mérite un espace vital, et nous ne reculerons devant rien pour l'obtenir.
        L'histoire jugera nos actions comme nécessaires pour la survie de notre race.
        """
    elif extract_type == "debat_politique":
        return """
        Nous sommes engagés dans une grande guerre civile, mettant à l'épreuve si cette nation, ou toute nation ainsi conçue et ainsi dédiée, peut perdurer.
        Je ne crois pas que notre gouvernement puisse endurer de façon permanente mi-esclave, mi-libre.
        Une maison divisée contre elle-même ne peut pas tenir debout.
        Je ne m'attends pas à ce que l'Union soit dissoute; je ne m'attends pas à ce que la maison s'effondre; mais je m'attends à ce qu'elle cesse d'être divisée.
        Elle deviendra tout l'un ou tout l'autre.
        Soit les opposants de l'esclavage arrêteront son expansion et le placeront là où l'esprit public pourra se reposer dans la croyance qu'il est sur la voie de l'extinction ultime, soit ses défenseurs le pousseront en avant jusqu'à ce qu'il devienne légal dans tous les États, anciens comme nouveaux, du Nord comme du Sud.
        """
    else:
        return """
        L'argumentation est l'art de convaincre par le raisonnement logique et la présentation d'évidences.
        Un bon argument repose sur des prémisses solides et des inférences valides.
        Cependant, il faut être vigilant face aux sophismes qui peuvent miner la qualité d'un raisonnement.
        La cohérence argumentative est essentielle pour maintenir la crédibilité d'un discours.
        En conclusion, l'analyse rhétorique nous permet d'évaluer la qualité et l'efficacité des arguments présentés.
        """

def split_text_into_arguments(text: str) -> List[str]:
    """
    Divise un texte en arguments individuels.
    
    Args:
        text (str): Texte à diviser en arguments
        
    Returns:
        List[str]: Liste des arguments extraits
    """
    # Liste des délimiteurs d'arguments
    delimiters = [
        ". ", "! ", "? ", 
        ". \n", "! \n", "? \n",
        ".\n", "!\n", "?\n"
    ]
    
    # Remplacer les délimiteurs par un marqueur spécial
    for delimiter in delimiters:
        text = text.replace(delimiter, "|||")
    
    # Diviser le texte en utilisant le marqueur
    raw_arguments = text.split("|||")
    
    # Nettoyer les arguments
    arguments = []
    for arg in raw_arguments:
        arg = arg.strip()
        if arg and len(arg) > 10:  # Ignorer les arguments trop courts
            arguments.append(arg)
    
    return arguments

def generate_fallacy_detection(argument: str) -> List[Dict[str, Any]]:
    """
    Génère une détection de sophismes simulée pour un argument.
    
    Args:
        argument (str): Argument à analyser
        
    Returns:
        List[Dict[str, Any]]: Liste des sophismes détectés
    """
    # Probabilité de détecter un sophisme (50%)
    if random.random() < 0.5:
        return []
    
    # Sélectionner un sophisme aléatoire
    fallacy = random.choice(COMMON_FALLACIES)
    
    # Générer une détection simulée
    return [{
        "fallacy_type": fallacy["name"].lower().replace(" ", "_"),
        "description": fallacy["description"],
        "severity": fallacy["severity"],
        "context_text": argument[:50] + "...",
        "confidence": round(random.uniform(0.6, 0.95), 2)
    }]

def generate_coherence_evaluation() -> Dict[str, Any]:
    """
    Génère une évaluation de cohérence simulée.
    
    Returns:
        Dict[str, Any]: Évaluation de cohérence simulée
    """
    # Générer un score de cohérence aléatoire
    coherence_score = round(random.uniform(0.4, 0.9), 2)
    
    # Déterminer le niveau de cohérence
    if coherence_score < 0.5:
        coherence_level = "Faible"
    elif coherence_score < 0.7:
        coherence_level = "Modéré"
    else:
        coherence_level = "Élevé"
    
    # Générer des recommandations aléatoires
    recommendations = [
        "Améliorer la transition entre les arguments",
        "Renforcer la cohérence thématique",
        "Clarifier les liens logiques entre les idées",
        "Éviter les digressions qui affaiblissent l'argumentation"
    ]
    
    # Sélectionner un sous-ensemble aléatoire de recommandations
    selected_recommendations = random.sample(recommendations, k=random.randint(1, 3))
    
    return {
        "overall_coherence": {
            "score": coherence_score,
            "level": coherence_level
        },
        "thematic_coherence": round(random.uniform(0.4, 0.9), 2),
        "logical_coherence": round(random.uniform(0.4, 0.9), 2),
        "recommendations": selected_recommendations
    }

def generate_rhetorical_analysis(extract: Dict[str, Any], source_name: str, agent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Génère une analyse rhétorique simulée pour un extrait.
    
    Args:
        extract (Dict[str, Any]): Extrait à analyser
        source_name (str): Nom de la source
        agent (Dict[str, Any]): Agent d'analyse rhétorique
        
    Returns:
        Dict[str, Any]: Résultats de l'analyse
    """
    extract_name = extract["extract_name"]
    extract_type = extract.get("type", "general")
    
    # Générer un texte d'exemple
    extract_text = generate_sample_text(extract_type)
    
    # Diviser l'extrait en arguments
    arguments = split_text_into_arguments(extract_text)
    
    # Initialiser les résultats
    results = {
        "extract_name": extract_name,
        "source_name": source_name,
        "agent_name": agent["name"],
        "argument_count": len(arguments),
        "timestamp": datetime.now().isoformat(),
        "extract_text": extract_text,
        "analyses": {}
    }
    
    # Analyse des sophismes
    fallacy_results = {
        "argument_count": len(arguments),
        "context_description": f"Extrait '{extract_name}' de la source '{source_name}'",
        "contextual_factors": {
            "domain": "politique" if "politique" in extract_type else "général",
            "audience": "public" if "discours" in extract_type else "spécialistes",
            "medium": "oral" if "discours" in extract_type else "écrit",
            "purpose": "persuader" if "politique" in extract_type else "informer"
        },
        "argument_results": []
    }
    
    # Analyser chaque argument
    total_fallacies = 0
    for i, argument in enumerate(arguments):
        # Générer des détections de sophismes
        detected_fallacies = generate_fallacy_detection(argument)
        total_fallacies += len(detected_fallacies)
        
        # Ajouter les résultats pour cet argument
        fallacy_results["argument_results"].append({
            "argument_index": i,
            "argument": argument,
            "detected_fallacies": detected_fallacies
        })
    
    results["analyses"]["fallacy_detection"] = fallacy_results
    results["analyses"]["fallacy_count"] = total_fallacies
    
    # Analyse de la cohérence
    results["analyses"]["coherence_evaluation"] = generate_coherence_evaluation()
    
    # Métriques globales
    results["analyses"]["metrics"] = {
        "fallacy_density": round(total_fallacies / len(arguments), 2) if arguments else 0,
        "persuasiveness_score": round(random.uniform(0.3, 0.9), 2),
        "clarity_score": round(random.uniform(0.4, 0.9), 2),
        "overall_quality": round(random.uniform(0.4, 0.9), 2)
    }
    
    # Recommandations
    results["analyses"]["recommendations"] = [
        "Réduire l'utilisation des sophismes identifiés",
        "Améliorer la cohérence entre les arguments",
        "Renforcer les preuves factuelles",
        "Clarifier les liens logiques entre les idées"
    ]
    
    return results
def generate_markdown_summary(analysis_result: Dict[str, Any], output_dir: Path) -> Path:
    """
    Génère une synthèse au format Markdown pour un résultat d'analyse.
    
    Args:
        analysis_result (Dict[str, Any]): Résultat d'analyse
        output_dir (Path): Répertoire de sortie
        
    Returns:
        Path: Chemin du fichier Markdown généré
    """
    extract_name = analysis_result["extract_name"]
    source_name = analysis_result["source_name"]
    agent_name = analysis_result["agent_name"]
    
    # Créer un nom de fichier valide
    filename = f"{source_name.replace(' ', '_')}_{extract_name.replace(' ', '_')}_{agent_name.replace(' ', '_')}.md"
    output_path = output_dir / filename
    
    # Extraire les informations nécessaires
    extract_text = analysis_result["extract_text"]
    argument_count = analysis_result["argument_count"]
    fallacy_count = analysis_result["analyses"]["fallacy_count"]
    coherence_evaluation = analysis_result["analyses"]["coherence_evaluation"]
    metrics = analysis_result["analyses"]["metrics"]
    
    # Créer le contenu Markdown
    content = f"""# Analyse rhétorique: {extract_name}

## Informations générales

- **Source**: {source_name}
- **Extrait**: {extract_name}
- **Agent d'analyse**: {agent_name}
- **Date d'analyse**: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

## Résumé de l'analyse

L'analyse rhétorique de cet extrait a identifié **{fallacy_count} sophismes** sur un total de **{argument_count} arguments**. 
La cohérence argumentative globale est évaluée comme **{coherence_evaluation["overall_coherence"]["level"]}** 
(score: {coherence_evaluation["overall_coherence"]["score"]}).

## Extrait analysé

```
{extract_text}
```

## Sophismes détectés

"""
    
    # Ajouter les sophismes détectés
    fallacy_results = analysis_result["analyses"]["fallacy_detection"]["argument_results"]
    fallacies_found = False
    
    for arg_result in fallacy_results:
        if arg_result["detected_fallacies"]:
            fallacies_found = True
            argument = arg_result["argument"]
            
            for fallacy in arg_result["detected_fallacies"]:
                fallacy_type = fallacy["fallacy_type"].replace("_", " ").title()
                description = fallacy["description"]
                severity = fallacy.get("severity", "Non spécifiée")
                confidence = fallacy.get("confidence", 0.0)
                
                content += f"""### {fallacy_type}

- **Description**: {description}
- **Sévérité**: {severity}
- **Confiance**: {confidence:.2f}
- **Contexte**: 
  > {argument}

"""
    
    if not fallacies_found:
        content += "Aucun sophisme n'a été détecté dans cet extrait.\n\n"
    
    # Ajouter les métriques d'analyse
    content += """## Métriques d'analyse

| Métrique | Valeur | Interprétation |
|----------|--------|----------------|
"""
    
    for metric_name, metric_value in metrics.items():
        # Déterminer l'interprétation
        if metric_name == "fallacy_density":
            if metric_value < 0.2:
                interpretation = "Faible présence de sophismes"
            elif metric_value < 0.5:
                interpretation = "Présence modérée de sophismes"
            else:
                interpretation = "Forte présence de sophismes"
        elif metric_name == "persuasiveness_score":
            if metric_value < 0.4:
                interpretation = "Peu persuasif"
            elif metric_value < 0.7:
                interpretation = "Modérément persuasif"
            else:
                interpretation = "Très persuasif"
        elif metric_name == "clarity_score":
            if metric_value < 0.4:
                interpretation = "Peu clair"
            elif metric_value < 0.7:
                interpretation = "Modérément clair"
            else:
                interpretation = "Très clair"
        elif metric_name == "overall_quality":
            if metric_value < 0.4:
                interpretation = "Qualité faible"
            elif metric_value < 0.7:
                interpretation = "Qualité moyenne"
            else:
                interpretation = "Qualité élevée"
        else:
            interpretation = "Non spécifiée"
        
        # Formater le nom de la métrique
        formatted_name = metric_name.replace("_", " ").title()
        
        content += f"| {formatted_name} | {metric_value:.2f} | {interpretation} |\n"
    
    # Ajouter les recommandations
    content += "\n## Recommandations\n\n"
    
    for recommendation in analysis_result["analyses"]["recommendations"]:
        content += f"- {recommendation}\n"
    
    # Ajouter les liens vers des analyses plus détaillées
    content += f"""
## Analyses détaillées

Pour une analyse plus détaillée, consultez les ressources suivantes:

- [Analyse complète au format JSON](../rhetorical_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json)
- [Rapport de performance comparatif](../performance_comparison/rapport_performance.md)
- [Rapport d'analyse complet](../comprehensive_report/rapport_analyse_complet.md)

"""
    
    # Écrire le contenu dans le fichier
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"✅ Synthèse Markdown générée: {output_path}")
    
    return output_path

def generate_global_summary(all_analyses: List[Dict[str, Any]], output_dir: Path) -> Path:
    """
    Génère un rapport de synthèse global comparant les différents agents.
    
    Args:
        all_analyses (List[Dict[str, Any]]): Liste de toutes les analyses
        output_dir (Path): Répertoire de sortie
        
    Returns:
        Path: Chemin du fichier Markdown généré
    """
    # Créer le chemin du fichier
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"rapport_synthese_global_{timestamp}.md"
    
    # Regrouper les analyses par agent et par source
    analyses_by_agent = {}
    sources = set()
    
    for analysis in all_analyses:
        agent_name = analysis["agent_name"]
        source_name = analysis["source_name"]
        
        if agent_name not in analyses_by_agent:
            analyses_by_agent[agent_name] = {}
        
        if source_name not in analyses_by_agent[agent_name]:
            analyses_by_agent[agent_name][source_name] = []
        
        analyses_by_agent[agent_name][source_name].append(analysis)
        sources.add(source_name)
    
    # Créer le contenu Markdown
    content = f"""# Rapport de synthèse global des analyses rhétoriques

## Informations générales

- **Date de génération**: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
- **Nombre d'agents**: {len(analyses_by_agent)}
- **Nombre de sources**: {len(sources)}
- **Nombre total d'analyses**: {len(all_analyses)}

## Comparaison des agents

"""
    
    # Tableau comparatif des agents
    content += """| Agent | Nombre d'analyses | Sophismes détectés | Cohérence moyenne | Forces | Faiblesses |
|-------|-------------------|-------------------|-------------------|---------|------------|
"""
    
    for agent_name, agent_analyses in analyses_by_agent.items():
        # Calculer les statistiques
        total_analyses = sum(len(analyses) for analyses in agent_analyses.values())
        total_fallacies = sum(sum(analysis["analyses"]["fallacy_count"] for analysis in analyses) for analyses in agent_analyses.values())
        
        # Calculer la cohérence moyenne
        coherence_scores = []
        for source_analyses in agent_analyses.values():
            for analysis in source_analyses:
                coherence_scores.append(analysis["analyses"]["coherence_evaluation"]["overall_coherence"]["score"])
        
        avg_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0
        
        # Trouver l'agent dans la liste des agents
        agent_info = next((agent for agent in RHETORICAL_AGENTS if agent["name"] == agent_name), None)
        
        if agent_info:
            strengths = ", ".join(agent_info["strengths"][:2])  # Limiter à 2 forces
            weaknesses = ", ".join(agent_info["weaknesses"][:2])  # Limiter à 2 faiblesses
        else:
            strengths = "Non spécifiées"
            weaknesses = "Non spécifiées"
        
        content += f"| {agent_name} | {total_analyses} | {total_fallacies} | {avg_coherence:.2f} | {strengths} | {weaknesses} |\n"
    
    # Analyse par source
    content += "\n## Analyse par source\n\n"
    
    for source_name in sorted(sources):
        content += f"### {source_name}\n\n"
        
        content += """| Agent | Extraits analysés | Sophismes détectés | Cohérence moyenne | Qualité globale |
|-------|------------------|-------------------|-------------------|----------------|
"""
        
        for agent_name, agent_analyses in analyses_by_agent.items():
            if source_name in agent_analyses:
                source_analyses = agent_analyses[source_name]
                
                # Calculer les statistiques
                total_extracts = len(source_analyses)
                total_fallacies = sum(analysis["analyses"]["fallacy_count"] for analysis in source_analyses)
                
                # Calculer la cohérence moyenne
                coherence_scores = [analysis["analyses"]["coherence_evaluation"]["overall_coherence"]["score"] for analysis in source_analyses]
                avg_coherence = sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0
                
                # Calculer la qualité globale moyenne
                quality_scores = [analysis["analyses"]["metrics"]["overall_quality"] for analysis in source_analyses]
                avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
                
                content += f"| {agent_name} | {total_extracts} | {total_fallacies} | {avg_coherence:.2f} | {avg_quality:.2f} |\n"
        
        content += "\n"
    
    # Exemples de sophismes notables
    content += "## Exemples de sophismes notables\n\n"
    
    # Collecter tous les sophismes détectés
    all_fallacies = []
    
    for analysis in all_analyses:
        fallacy_results = analysis["analyses"]["fallacy_detection"]["argument_results"]
        
        for arg_result in fallacy_results:
            if arg_result["detected_fallacies"]:
                for fallacy in arg_result["detected_fallacies"]:
                    all_fallacies.append({
                        "type": fallacy["fallacy_type"].replace("_", " ").title(),
                        "description": fallacy["description"],
                        "severity": fallacy.get("severity", "Non spécifiée"),
                        "confidence": fallacy.get("confidence", 0.0),
                        "context": arg_result["argument"],
                        "source": analysis["source_name"],
                        "extract": analysis["extract_name"],
                        "agent": analysis["agent_name"]
                    })
    
    # Trier les sophismes par sévérité et confiance
    all_fallacies.sort(key=lambda x: (0 if x["severity"] == "Élevée" else (1 if x["severity"] == "Modérée" else 2), -x["confidence"]))
    
    # Sélectionner les 5 premiers sophismes
    for i, fallacy in enumerate(all_fallacies[:5]):
        content += f"""### {i+1}. {fallacy["type"]} ({fallacy["severity"]})

- **Source**: {fallacy["source"]} - {fallacy["extract"]}
- **Agent**: {fallacy["agent"]}
- **Description**: {fallacy["description"]}
- **Confiance**: {fallacy["confidence"]:.2f}
- **Contexte**: 
  > {fallacy["context"]}

"""
    
    # Recommandations générales
    content += """## Recommandations générales

Sur la base des analyses effectuées, voici quelques recommandations générales:

1. **Utilisation des agents**: Utiliser l'agent avancé pour les analyses approfondies et l'agent de base pour les analyses rapides.
2. **Amélioration des analyses**: Combiner les résultats des différents agents pour obtenir une analyse plus complète.
3. **Détection des sophismes**: Porter une attention particulière aux sophismes de type "Appel à la peur" et "Ad hominem" qui sont les plus fréquents et les plus graves.
4. **Cohérence argumentative**: Renforcer la cohérence thématique et logique des arguments pour améliorer la qualité globale des discours.
5. **Analyse contextuelle**: Prendre en compte le contexte historique et politique pour une meilleure compréhension des arguments.
"""
    
    # Écrire le contenu dans le fichier
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    logger.info(f"✅ Rapport de synthèse global généré: {output_path}")
    
    return output_path
def main():
    """Fonction principale du script."""
    # Analyser les arguments
    args = parse_arguments()
    
    # Configurer le niveau de logging
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug("Mode verbeux activé")
    
    logger.info("Démarrage de la génération des synthèses d'analyses rhétoriques...")
    
    # Créer les répertoires de sortie
    output_dir = Path(args.output_dir)
    summaries_dir = output_dir / "summaries"
    summaries_dir.mkdir(parents=True, exist_ok=True)
    
    # Générer les analyses pour chaque source et extrait
    all_analyses = []
    
    for agent in RHETORICAL_AGENTS:
        logger.info(f"Génération des analyses avec l'agent '{agent['name']}'...")
        
        for source in SIMULATED_SOURCES:
            source_name = source["source_name"]
            extracts = source["extracts"]
            
            for extract in extracts:
                # Générer l'analyse rhétorique
                analysis_result = generate_rhetorical_analysis(extract, source_name, agent)
                all_analyses.append(analysis_result)
                
                # Générer la synthèse Markdown
                generate_markdown_summary(analysis_result, summaries_dir)
    
    # Générer le rapport de synthèse global
    global_summary_path = generate_global_summary(all_analyses, output_dir)
    
    # Sauvegarder toutes les analyses au format JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"rhetorical_analyses_{timestamp}.json"
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_analyses, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ Analyses sauvegardées au format JSON: {json_path}")
    logger.info(f"✅ Rapport de synthèse global généré: {global_summary_path}")
    logger.info(f"✅ {len(all_analyses)} analyses générées avec succès")
    logger.info("Génération des synthèses d'analyses rhétoriques terminée avec succès.")

def parse_arguments():
    """
    Parse les arguments de ligne de commande.
    
    Returns:
        argparse.Namespace: Les arguments parsés
    """
    parser = argparse.ArgumentParser(description="Génération de synthèses d'analyses rhétoriques")
    
    parser.add_argument(
        "--output-dir", "-o",
        help="Répertoire de sortie pour les synthèses",
        default="results"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Affiche des informations de débogage supplémentaires"
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    main()