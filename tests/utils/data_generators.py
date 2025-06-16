#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Générateurs de données de test.

Ce module fournit des fonctions pour générer des données de test
pour les tests d'intégration et fonctionnels.
"""

import os
import json
import random
from datetime import datetime
import uuid


def generate_fallacy_text(fallacy_type):
    """
    Génère un texte contenant un sophisme du type spécifié.
    
    Args:
        fallacy_type (str): Type de sophisme à générer.
        
    Returns:
        str: Texte contenant le sophisme.
    """
    fallacy_templates = {
        "ad_hominem": [
            "Pierre est incompétent, donc son argument sur l'économie est invalide.",
            "Marie est riche, donc son opinion sur la pauvreté n'est pas valable.",
            "Cet expert est payé par l'industrie, donc ses recherches sont biaisées."
        ],
        "faux_dilemme": [
            "Soit nous augmentons les impôts, soit l'économie s'effondrera.",
            "Vous êtes soit avec nous, soit contre nous.",
            "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans."
        ],
        "pente_glissante": [
            "Si nous légalisons la marijuana, bientôt toutes les drogues seront légales.",
            "Si nous autorisons le mariage homosexuel, bientôt les gens voudront épouser leurs animaux de compagnie.",
            "Si nous interdisons les armes à feu, bientôt le gouvernement confisquera tous nos droits."
        ],
        "généralisation_hâtive": [
            "J'ai rencontré deux Français impolis, donc tous les Français sont impolis.",
            "Le réchauffement climatique est un mythe car il a neigé cet hiver.",
            "Mon voisin a gagné à la loterie, donc c'est facile de gagner à la loterie."
        ],
        "homme_de_paille": [
            "Les défenseurs du contrôle des armes à feu veulent confisquer toutes les armes et laisser les citoyens sans défense.",
            "Les écologistes veulent que nous retournions à l'âge de pierre sans électricité ni voitures.",
            "Les féministes détestent tous les hommes et veulent les dominer."
        ],
        "appel_à_l'autorité": [
            "Einstein ne croyait pas à la mécanique quantique, donc la mécanique quantique est fausse.",
            "Ce célèbre acteur utilise ce produit, donc il doit être bon.",
            "Mon médecin fume, donc fumer n'est pas si mauvais pour la santé."
        ],
        "appel_à_l'émotion": [
            "Pensez aux enfants qui souffriront si vous ne soutenez pas cette loi.",
            "Comment pouvez-vous être si insensible face à cette tragédie ?",
            "Nous devons agir maintenant, avant qu'il ne soit trop tard !"
        ],
        "corrélation_causation": [
            "Les ventes de crème glacée augmentent en même temps que les noyades, donc la crème glacée cause des noyades.",
            "Les vaccins contre la COVID-19 ont été développés rapidement, donc ils sont dangereux.",
            "Depuis l'introduction de cette politique, le crime a augmenté, donc la politique a causé l'augmentation du crime."
        ]
    }
    
    if fallacy_type in fallacy_templates:
        return random.choice(fallacy_templates[fallacy_type])
    else:
        return f"Ceci est un exemple de sophisme de type {fallacy_type}."


def generate_text_with_fallacies(fallacy_types=None, num_fallacies=3):
    """
    Génère un texte contenant plusieurs sophismes.
    
    Args:
        fallacy_types (list): Liste des types de sophismes à inclure.
        num_fallacies (int): Nombre de sophismes à inclure.
        
    Returns:
        str: Texte contenant les sophismes.
    """
    if fallacy_types is None:
        fallacy_types = [
            "ad_hominem", "faux_dilemme", "pente_glissante", 
            "généralisation_hâtive", "homme_de_paille", "appel_à_l'autorité",
            "appel_à_l'émotion", "corrélation_causation"
        ]
    
    selected_types = random.sample(fallacy_types, min(num_fallacies, len(fallacy_types)))
    
    paragraphs = []
    for fallacy_type in selected_types:
        paragraphs.append(generate_fallacy_text(fallacy_type))
    
    # Ajouter quelques phrases neutres
    neutral_sentences = [
        "Le débat sur ce sujet est complexe et mérite une analyse approfondie.",
        "Il est important de considérer différentes perspectives sur cette question.",
        "Les données scientifiques doivent être examinées avec rigueur.",
        "Une approche équilibrée permettrait de mieux comprendre les enjeux.",
        "La recherche continue d'apporter de nouvelles informations sur ce sujet."
    ]
    
    for _ in range(2):
        paragraphs.append(random.choice(neutral_sentences))
    
    # Mélanger les paragraphes
    random.shuffle(paragraphs)
    
    return "\n\n".join(paragraphs)


def generate_test_file(content, file_path):
    """
    Génère un fichier de test avec le contenu spécifié.
    
    Args:
        content (str): Contenu du fichier.
        file_path (str): Chemin du fichier à créer.
        
    Returns:
        str: Chemin du fichier créé.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return file_path


def generate_test_corpus(num_files=5, output_dir="examples/test_data"):
    """
    Génère un corpus de fichiers de test contenant des sophismes.
    
    Args:
        num_files (int): Nombre de fichiers à générer.
        output_dir (str): Répertoire de sortie.
        
    Returns:
        list: Liste des chemins des fichiers générés.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    file_paths = []
    for i in range(num_files):
        content = generate_text_with_fallacies()
        file_path = os.path.join(output_dir, f"test_sophismes_{i+1}.txt")
        generate_test_file(content, file_path)
        file_paths.append(file_path)
    
    return file_paths


def generate_task(task_type="extraction", objective_id=None):
    """
    Génère une tâche pour les tests.
    
    Args:
        task_type (str): Type de tâche (extraction, analysis, report).
        objective_id (str): ID de l'objectif associé.
        
    Returns:
        dict: Tâche générée.
    """
    if objective_id is None:
        objective_id = f"objective-{uuid.uuid4()}"
    
    task_id = f"task-{uuid.uuid4()}"
    
    task_templates = {
        "extraction": {
            "id": task_id,
            "description": "Extraire le texte du document",
            "objective_id": objective_id,
            "estimated_duration": 3600,
            "required_capabilities": ["text_extraction"],
            "parameters": {
                "document_path": "examples/exemple_sophisme.txt",
                "output_format": "text"
            }
        },
        "analysis": {
            "id": task_id,
            "description": "Analyser les sophismes dans le texte",
            "objective_id": objective_id,
            "estimated_duration": 7200,
            "required_capabilities": ["fallacy_detection"],
            "parameters": {
                "analysis_type": "fallacy",
                "output_format": "json"
            }
        },
        "report": {
            "id": task_id,
            "description": "Générer un rapport d'analyse",
            "objective_id": objective_id,
            "estimated_duration": 1800,
            "required_capabilities": ["result_presentation"],
            "parameters": {
                "report_type": "summary",
                "output_format": "json"
            }
        }
    }
    
    if task_type in task_templates:
        return task_templates[task_type]
    else:
        return {
            "id": task_id,
            "description": f"Tâche de type {task_type}",
            "objective_id": objective_id,
            "estimated_duration": 3600,
            "required_capabilities": [task_type],
            "parameters": {}
        }


def generate_objective(objective_type="fallacy_analysis"):
    """
    Génère un objectif pour les tests.
    
    Args:
        objective_type (str): Type d'objectif.
        
    Returns:
        dict: Objectif généré.
    """
    objective_id = f"objective-{uuid.uuid4()}"
    
    objective_templates = {
        "fallacy_analysis": {
            "id": objective_id,
            "description": "Analyser le texte pour identifier les sophismes",
            "priority": "high",
            "text": generate_text_with_fallacies(),
            "type": "fallacy_analysis"
        },
        "rhetorical_analysis": {
            "id": objective_id,
            "description": "Analyser la rhétorique du texte",
            "priority": "medium",
            "text": generate_text_with_fallacies(),
            "type": "rhetorical_analysis"
        },
        "document_extraction": {
            "id": objective_id,
            "description": "Extraire le texte du document",
            "priority": "low",
            "document_path": "examples/exemple_sophisme.txt",
            "type": "document_extraction"
        }
    }
    
    if objective_type in objective_templates:
        return objective_templates[objective_type]
    else:
        return {
            "id": objective_id,
            "description": f"Objectif de type {objective_type}",
            "priority": "medium",
            "type": objective_type
        }


def generate_analysis_result(fallacy_types=None, num_fallacies=3):
    """
    Génère un résultat d'analyse pour les tests.
    
    Args:
        fallacy_types (list): Liste des types de sophismes à inclure.
        num_fallacies (int): Nombre de sophismes à inclure.
        
    Returns:
        dict: Résultat d'analyse généré.
    """
    if fallacy_types is None:
        fallacy_types = [
            "ad_hominem", "faux_dilemme", "pente_glissante", 
            "généralisation_hâtive", "homme_de_paille", "appel_à_l'autorité",
            "appel_à_l'émotion", "corrélation_causation"
        ]
    
    selected_types = random.sample(fallacy_types, min(num_fallacies, len(fallacy_types)))
    
    fallacies = []
    for fallacy_type in selected_types:
        text = generate_fallacy_text(fallacy_type)
        confidence = round(random.uniform(0.7, 0.95), 2)
        fallacies.append({
            "type": fallacy_type,
            "text": text,
            "confidence": confidence
        })
    
    return {
        "fallacies": fallacies,
        "analysis_metadata": {
            "timestamp": datetime.now().isoformat(),
            "agent_id": "test_agent",
            "version": "1.0"
        }
    }


def generate_enhanced_analysis_result(fallacy_types=None, num_fallacies=3):
    """
    Génère un résultat d'analyse améliorée pour les tests.
    
    Args:
        fallacy_types (list): Liste des types de sophismes à inclure.
        num_fallacies (int): Nombre de sophismes à inclure.
        
    Returns:
        dict: Résultat d'analyse améliorée généré.
    """
    # Générer les sophismes
    result = generate_analysis_result(fallacy_types, num_fallacies)
    fallacies = result["fallacies"]
    
    # Générer l'analyse contextuelle
    context_analysis = {}
    for fallacy in fallacies:
        fallacy_type = fallacy["type"]
        context_relevance = round(random.uniform(0.6, 0.9), 1)
        
        cultural_factors_options = {
            "ad_hominem": ["politique", "débat", "crédibilité"],
            "faux_dilemme": ["politique", "économie", "environnement"],
            "pente_glissante": ["législation", "morale", "société"],
            "généralisation_hâtive": ["science", "statistiques", "climat"],
            "homme_de_paille": ["politique", "débat", "idéologie"],
            "appel_à_l'autorité": ["science", "expertise", "célébrité"],
            "appel_à_l'émotion": ["politique", "publicité", "activisme"],
            "corrélation_causation": ["science", "statistiques", "santé"]
        }
        
        if fallacy_type in cultural_factors_options:
            factors = cultural_factors_options[fallacy_type]
        else:
            factors = ["politique", "science", "société"]
        
        cultural_factors = random.sample(factors, 2)
        
        context_analysis[fallacy_type] = {
            "context_relevance": context_relevance,
            "cultural_factors": cultural_factors
        }
    
    # Générer l'évaluation de la sévérité
    severity_evaluation = []
    for fallacy in fallacies:
        fallacy_type = fallacy["type"]
        severity = round(random.uniform(0.5, 0.9), 1)
        
        if severity < 0.7:
            impact = "low"
        elif severity < 0.8:
            impact = "medium"
        else:
            impact = "high"
        
        severity_evaluation.append({
            "type": fallacy_type,
            "severity": severity,
            "impact": impact
        })
    
    # Générer l'analyse rhétorique
    rhetorical_analysis = {
        "tone": random.choice(["persuasif", "informatif", "émotionnel", "agressif", "défensif"]),
        "style": random.choice(["formel", "informel", "académique", "journalistique", "polémique"]),
        "techniques": random.sample([
            "appel à l'émotion", "question rhétorique", "polarisation",
            "répétition", "métaphore", "ironie", "hyperbole"
        ], 3),
        "effectiveness": round(random.uniform(0.5, 0.9), 2)
    }
    
    # Assembler le résultat final
    return {
        "fallacies": fallacies,
        "context_analysis": context_analysis,
        "severity_evaluation": severity_evaluation,
        "rhetorical_analysis": rhetorical_analysis,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "agent_id": "test_agent",
            "version": "1.0"
        }
    }


def save_analysis_result(result, file_path):
    """
    Sauvegarde un résultat d'analyse dans un fichier JSON.
    
    Args:
        result (dict): Résultat d'analyse.
        file_path (str): Chemin du fichier de sortie.
        
    Returns:
        str: Chemin du fichier créé.
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    return file_path


if __name__ == "__main__":
    # Exemple d'utilisation
    text = generate_text_with_fallacies()
    print("Texte généré avec sophismes :")
    print(text)
    print("\n")
    
    result = generate_enhanced_analysis_result()
    print("Résultat d'analyse généré :")
    print(json.dumps(result, ensure_ascii=False, indent=2))