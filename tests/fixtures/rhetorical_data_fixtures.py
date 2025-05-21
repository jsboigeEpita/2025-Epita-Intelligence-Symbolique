#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fixtures pour les données rhétoriques utilisées dans les tests.

Ce module fournit des fixtures réutilisables pour les tests d'analyse rhétorique
et de détection des sophismes.
"""

import pytest
import os
import json
from pathlib import Path


@pytest.fixture
def example_text():
    """Fixture fournissant un texte d'exemple contenant des sophismes."""
    return """
    Le réchauffement climatique est un mythe car il a neigé cet hiver.
    Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.
    Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées.
    """


@pytest.fixture
def example_text_file(tmp_path):
    """Fixture créant un fichier temporaire contenant un texte d'exemple."""
    text = """
    Le réchauffement climatique est un mythe car il a neigé cet hiver.
    Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.
    Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées.
    """
    file_path = tmp_path / "exemple_sophisme.txt"
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(text)
    return file_path


@pytest.fixture
def example_fallacies():
    """Fixture fournissant des exemples de sophismes détectés."""
    return [
        {"type": "généralisation_hâtive", "text": "Le réchauffement climatique est un mythe car il a neigé cet hiver", "confidence": 0.92},
        {"type": "faux_dilemme", "text": "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans", "confidence": 0.85},
        {"type": "ad_hominem", "text": "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées", "confidence": 0.88}
    ]


@pytest.fixture
def example_context_analysis():
    """Fixture fournissant un exemple d'analyse contextuelle des sophismes."""
    return {
        "généralisation_hâtive": {"context_relevance": 0.7, "cultural_factors": ["climat", "science"]},
        "faux_dilemme": {"context_relevance": 0.8, "cultural_factors": ["environnement", "politique"]},
        "ad_hominem": {"context_relevance": 0.9, "cultural_factors": ["science", "financement"]}
    }


@pytest.fixture
def example_severity_evaluation():
    """Fixture fournissant un exemple d'évaluation de la sévérité des sophismes."""
    return [
        {"type": "généralisation_hâtive", "severity": 0.7, "impact": "medium"},
        {"type": "faux_dilemme", "severity": 0.8, "impact": "high"},
        {"type": "ad_hominem", "severity": 0.9, "impact": "high"}
    ]


@pytest.fixture
def example_rhetorical_analysis():
    """Fixture fournissant un exemple d'analyse rhétorique."""
    return {
        "tone": "persuasif",
        "style": "émotionnel",
        "techniques": ["appel à l'émotion", "question rhétorique", "polarisation"],
        "effectiveness": 0.82
    }


@pytest.fixture
def example_analysis_result():
    """Fixture fournissant un exemple de résultat d'analyse complet."""
    return {
        "fallacies": [
            {"type": "généralisation_hâtive", "text": "Le réchauffement climatique est un mythe car il a neigé cet hiver", "confidence": 0.92},
            {"type": "faux_dilemme", "text": "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans", "confidence": 0.85},
            {"type": "ad_hominem", "text": "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées", "confidence": 0.88}
        ],
        "context_analysis": {
            "généralisation_hâtive": {"context_relevance": 0.7, "cultural_factors": ["climat", "science"]},
            "faux_dilemme": {"context_relevance": 0.8, "cultural_factors": ["environnement", "politique"]},
            "ad_hominem": {"context_relevance": 0.9, "cultural_factors": ["science", "financement"]}
        },
        "severity_evaluation": [
            {"type": "généralisation_hâtive", "severity": 0.7, "impact": "medium"},
            {"type": "faux_dilemme", "severity": 0.8, "impact": "high"},
            {"type": "ad_hominem", "severity": 0.9, "impact": "high"}
        ],
        "rhetorical_analysis": {
            "tone": "persuasif",
            "style": "émotionnel",
            "techniques": ["appel à l'émotion", "question rhétorique", "polarisation"],
            "effectiveness": 0.82
        },
        "metadata": {
            "timestamp": "2025-05-21T23:30:00",
            "agent_id": "informal_agent",
            "version": "1.0"
        }
    }


@pytest.fixture
def example_analysis_result_file(tmp_path):
    """Fixture créant un fichier temporaire contenant un résultat d'analyse."""
    result = {
        "fallacies": [
            {"type": "généralisation_hâtive", "text": "Le réchauffement climatique est un mythe car il a neigé cet hiver", "confidence": 0.92},
            {"type": "faux_dilemme", "text": "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans", "confidence": 0.85},
            {"type": "ad_hominem", "text": "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées", "confidence": 0.88}
        ],
        "metadata": {
            "timestamp": "2025-05-21T23:30:00",
            "agent_id": "informal_agent",
            "version": "1.0"
        }
    }
    file_path = tmp_path / "analysis_result.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return file_path


@pytest.fixture
def example_corpus():
    """Fixture fournissant un exemple de corpus de textes."""
    return [
        "Le réchauffement climatique est un mythe car il a neigé cet hiver.",
        "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.",
        "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées.",
        "Si nous autorisons le mariage homosexuel, bientôt les gens voudront épouser leurs animaux de compagnie.",
        "Einstein ne croyait pas à la mécanique quantique, donc la mécanique quantique est fausse."
    ]


@pytest.fixture
def example_corpus_files(tmp_path):
    """Fixture créant des fichiers temporaires contenant un corpus de textes."""
    corpus = [
        "Le réchauffement climatique est un mythe car il a neigé cet hiver.",
        "Soit nous réduisons drastiquement les émissions de CO2, soit la planète sera inhabitable dans 10 ans.",
        "Les scientifiques qui soutiennent le réchauffement climatique sont payés pour dire cela, donc leurs recherches sont biaisées.",
        "Si nous autorisons le mariage homosexuel, bientôt les gens voudront épouser leurs animaux de compagnie.",
        "Einstein ne croyait pas à la mécanique quantique, donc la mécanique quantique est fausse."
    ]
    
    corpus_dir = tmp_path / "corpus"
    corpus_dir.mkdir()
    
    file_paths = []
    for i, text in enumerate(corpus):
        file_path = corpus_dir / f"text_{i+1}.txt"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)
        file_paths.append(file_path)
    
    return file_paths


@pytest.fixture
def example_fallacy_definitions():
    """Fixture fournissant des exemples de définitions de sophismes."""
    return [
        {
            "name": "ad_hominem",
            "category": "relevance",
            "description": "Attaque la personne plutôt que l'argument",
            "examples": ["Il est stupide, donc son argument est invalide"],
            "detection_patterns": ["stupide", "idiot", "incompétent"]
        },
        {
            "name": "faux_dilemme",
            "category": "structure",
            "description": "Présente seulement deux options alors qu'il en existe d'autres",
            "examples": ["Soit vous êtes avec nous, soit vous êtes contre nous"],
            "detection_patterns": ["soit...soit", "ou bien...ou bien", "deux options"]
        },
        {
            "name": "pente_glissante",
            "category": "causalite",
            "description": "Suggère qu'une action mènera inévitablement à une chaîne d'événements indésirables",
            "examples": ["Si nous autorisons cela, bientôt tout sera permis"],
            "detection_patterns": ["bientôt", "mènera à", "conduira à", "inévitablement"]
        }
    ]


@pytest.fixture
def example_fallacy_categories():
    """Fixture fournissant des exemples de catégories de sophismes."""
    return {
        "relevance": ["ad_hominem", "appel_a_l_autorite", "homme_de_paille"],
        "structure": ["faux_dilemme", "affirmation_du_consequent", "negation_de_l_antecedent"],
        "causalite": ["pente_glissante", "post_hoc_ergo_propter_hoc", "correlation_causation"],
        "ambiguite": ["equivocation", "amphibologie", "accent"],
        "induction": ["generalisation_hative", "echantillon_biaise", "anecdote"]
    }