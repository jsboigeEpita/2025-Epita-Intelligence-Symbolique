# -*- coding: utf-8 -*-
"""
Sous-script de démonstration pour les fonctionnalités notables du projet.

Ce script utilise des mocks pour illustrer rapidement les concepts suivants :
1.  Analyse de la cohérence d'un texte.
2.  Calcul du score de clarté.
3.  Extraction d'arguments (prémisses et conclusions).
4.  Génération de visualisations de performance.
"""
import logging
import sys
import os
from pathlib import Path
import time
from unittest.mock import MagicMock, patch

# Configuration de l'environnement
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Configuration du logger
logger = logging.getLogger("demo_notable_features")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Mocks pour simuler les modules sans les importer réellement
sys.modules['pandas'] = MagicMock()
sys.modules['matplotlib'] = MagicMock()
sys.modules['matplotlib.pyplot'] = MagicMock()
sys.modules['seaborn'] = MagicMock()

# Imports du projet (après les mocks)
try:
    from argumentation_analysis.mocks.coherence_analysis import CoherenceAnalyser
    from argumentation_analysis.mocks.clarity_scoring import ClarityScorer
    from argumentation_analysis.mocks.argument_mining import ArgumentMiner
    from argumentation_analysis.utils.visualization_generator import VisualizationGenerator
    logger.info("Modules de démonstration (mocks) importés avec succès.")
except ImportError as e:
    logger.critical(f"Impossible d'importer les modules de mock nécessaires : {e}")
    sys.exit(1)


def demonstrate_coherence_analysis():
    """Démontre l'analyse de cohérence sur un texte d'exemple."""
    logger.info("\n--- Démonstration : Analyse de la Cohérence ---")
    analyser = CoherenceAnalyser()
    text = "Le soleil brille. Les oiseaux chantent. Le ciel est bleu."
    incoherent_text = "Le soleil brille. Les bananes sont jaunes. J'aime le football."
    
    score1 = analyser.analyse(text)
    score2 = analyser.analyse(incoherent_text)
    
    logger.info(f"Texte cohérent : \"{text}\"")
    logger.info(f"Score de cohérence obtenu : {score1:.2f} (attendu: élevé)")
    
    logger.info(f"Texte incohérent : \"{incoherent_text}\"")
    logger.info(f"Score de cohérence obtenu : {score2:.2f} (attendu: faible)")


def demonstrate_clarity_scoring():
    """Démontre le calcul du score de clarté."""
    logger.info("\n--- Démonstration : Score de Clarté ---")
    scorer = ClarityScorer()
    clear_text = "Ceci est une phrase simple et facile à comprendre."
    unclear_text = "L'implémentation paradigmatique de l'interface synergise une sérendipité ontologique."
    
    score1 = scorer.score(clear_text)
    score2 = scorer.score(unclear_text)
    
    logger.info(f"Texte clair : \"{clear_text}\"")
    logger.info(f"Score de clarté obtenu : {score1:.2f} (attendu: élevé)")
    
    logger.info(f"Texte peu clair : \"{unclear_text}\"")
    logger.info(f"Score de clarté obtenu : {score2:.2f} (attendu: faible)")


def demonstrate_argument_mining():
    """Démontre l'extraction d'arguments d'un texte."""
    logger.info("\n--- Démonstration : Extraction d'Arguments ---")
    miner = ArgumentMiner()
    text = "Il pleut dehors, donc le sol doit être mouillé. De plus, le ciel est gris."
    
    result = miner.mine(text)
    
    logger.info(f"Texte analysé : \"{text}\"")
    logger.info("Arguments extraits (simulation) :")
    for arg in result['arguments']:
        logger.info(f"  - Prémisse : '{arg['premise']}'")
        logger.info(f"  - Conclusion : '{arg['conclusion']}'")


def demonstrate_visualization_generation():
    """Démontre la génération (simulée) de graphiques de performance."""
    logger.info("\n--- Démonstration : Génération de Visualisations ---")
    
    # Utilisation d'un patch pour s'assurer que les fonctions de matplotlib ne sont pas réellement appelées
    with patch('matplotlib.pyplot.show'), patch('matplotlib.pyplot.savefig'):
        generator = VisualizationGenerator()
        data = {'coherence': 0.85, 'clarity': 0.92, 'fallacies': 3}
        
        logger.info("Génération d'un graphique à barres (simulée)...")
        generator.plot_bar_chart(data, "Scores d'Analyse", "Métrique", "Score")
        
        logger.info("Génération d'un graphique circulaire (simulée)...")
        generator.plot_pie_chart([10, 3, 1], ["Valide", "Sophisme", "Inclassable"], "Répartition des Arguments")
        
    logger.info("Les appels à la génération de graphiques ont été effectués.")
    logger.info("Dans une exécution réelle, des fichiers image seraient sauvegardés et/ou affichés.")


if __name__ == "__main__":
    logger.info("=== Début du sous-script de démonstration des fonctionnalités notables ===")
    
    start_time = time.time()
    
    demonstrate_coherence_analysis()
    demonstrate_clarity_scoring()
    demonstrate_argument_mining()
    demonstrate_visualization_generation()
    
    duration = time.time() - start_time
    logger.info(f"\nDurée d'exécution du script : {duration:.2f} secondes.")
    logger.info("=== Fin du sous-script de démonstration des fonctionnalités notables ===")