import project_core.core_from_scripts.auto_env
#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour visualiser l'évolution de la couverture des tests au fil du temps.

Ce script génère des graphiques montrant l'évolution de la couverture des tests
pour différents modules du projet d'analyse argumentative.
"""

import os
import sys
import json
import argparse
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Définir les couleurs pour les différents modules
COLORS = {
    'Communication': '#1f77b4',
    'Gestion d\'État': '#ff7f0e',
    'Agents d\'Extraction': '#2ca02c',
    'Agents d\'Analyse Informelle': '#d62728',
    'Outils d\'Analyse': '#9467bd',
    'Global': '#8c564b'
}

# def parse_coverage_xml(xml_path): # Fonction déplacée
#     """
#     Parse un fichier coverage.xml et extrait les informations de couverture.
#     ... (contenu de la fonction supprimé)
#     """
#     pass # La fonction est maintenant importée

def save_coverage_history(coverage_data, history_file):
    """
    Sauvegarde les données de couverture dans un fichier d'historique.
    
    Args:
        coverage_data (dict): Données de couverture
        history_file (str): Chemin vers le fichier d'historique
    """
    history = []
    
    # Charger l'historique existant s'il existe
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
        except Exception as e:
            print(f"Erreur lors de la lecture du fichier d'historique: {e}")
    
    # Ajouter les nouvelles données
    history.append(coverage_data)
    
    # Sauvegarder l'historique mis à jour
    try:
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
        print(f"Historique de couverture sauvegardé dans {history_file}")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier d'historique: {e}")

# def map_package_to_module(package_name): # Fonction déplacée
#     """
#     Mappe un nom de package à un nom de module.
#     ... (contenu de la fonction supprimé)
#     """
#     pass # La fonction est maintenant importée

def generate_coverage_trend_chart(history_file, output_dir):
    """
    Génère un graphique montrant l'évolution de la couverture des tests au fil du temps.
    
    Args:
        history_file (str): Chemin vers le fichier d'historique
        output_dir (str): Répertoire de sortie pour les graphiques
    """
    if not os.path.exists(history_file):
        print(f"Le fichier d'historique {history_file} n'existe pas.")
        return
    
    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier d'historique: {e}")
        return
    
    if not history:
        print("L'historique est vide.")
        return
    
    # Préparer les données pour le graphique
    dates = [entry.get('timestamp', '') for entry in history]
    global_coverage = [entry.get('global', 0) for entry in history]
    
    # Créer un DataFrame pour les modules
    module_data = {}
    for entry in history:
        packages = entry.get('packages', {})
        for package, coverage in packages.items():
            module = map_package_to_module(package)
            if module not in module_data:
                module_data[module] = []
            module_data[module].append(coverage)
    
    # Créer le graphique
    plt.figure(figsize=(12, 8))
    
    # Tracer la ligne de couverture globale
    plt.plot(dates, global_coverage, marker='o', linewidth=3, color=COLORS['Global'], label='Couverture Globale')
    
    # Tracer les lignes pour chaque module
    for module, coverage in module_data.items():
        if module in COLORS and len(coverage) == len(dates):
            plt.plot(dates, coverage, marker='s', linewidth=2, color=COLORS[module], label=module)
    
    # Ajouter la ligne d'objectif
    plt.axhline(y=80, color='r', linestyle='--', label='Objectif (80%)')
    
    # Configurer le graphique
    plt.title('Évolution de la Couverture des Tests au Fil du Temps', fontsize=16)
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Couverture (%)', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='lower right')
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Sauvegarder le graphique
    output_path = os.path.join(output_dir, 'coverage_trend.png')
    plt.savefig(output_path, dpi=300)
    print(f"Graphique d'évolution de la couverture sauvegardé dans {output_path}")
    
    # Fermer la figure pour libérer la mémoire
    plt.close()

def generate_module_comparison_chart(history_file, output_dir):
    """
    Génère un graphique comparant la couverture des différents modules.
    
    Args:
        history_file (str): Chemin vers le fichier d'historique
        output_dir (str): Répertoire de sortie pour les graphiques
    """
    if not os.path.exists(history_file):
        print(f"Le fichier d'historique {history_file} n'existe pas.")
        return
    
    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier d'historique: {e}")
        return
    
    if not history:
        print("L'historique est vide.")
        return
    
    # Utiliser la dernière entrée pour la comparaison des modules
    latest_entry = history[-1]
    packages = latest_entry.get('packages', {})
    
    # Regrouper par module
    module_coverage = {}
    for package, coverage in packages.items():
        module = map_package_to_module(package)
        if module not in module_coverage:
            module_coverage[module] = []
        module_coverage[module].append(coverage)
    
    # Calculer la moyenne pour chaque module
    module_avg_coverage = {module: sum(coverages) / len(coverages) for module, coverages in module_coverage.items()}
    
    # Créer le graphique
    plt.figure(figsize=(10, 8))
    
    modules = list(module_avg_coverage.keys())
    coverages = list(module_avg_coverage.values())
    
    # Trier par couverture
    sorted_indices = np.argsort(coverages)
    modules = [modules[i] for i in sorted_indices]
    coverages = [coverages[i] for i in sorted_indices]
    
    # Définir les couleurs
    colors = [COLORS.get(module, '#333333') for module in modules]
    
    # Créer le graphique à barres
    bars = plt.barh(modules, coverages, color=colors)
    
    # Ajouter les valeurs sur les barres
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 1, bar.get_y() + bar.get_height()/2, f'{width:.1f}%',
                 ha='left', va='center', fontsize=10)
    
    # Ajouter la ligne d'objectif
    plt.axvline(x=80, color='r', linestyle='--', label='Objectif (80%)')
    
    # Configurer le graphique
    plt.title('Comparaison de la Couverture des Tests par Module', fontsize=16)
    plt.xlabel('Couverture (%)', fontsize=12)
    plt.ylabel('Module', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7, axis='x')
    plt.legend()
    plt.tight_layout()
    
    # Sauvegarder le graphique
    output_path = os.path.join(output_dir, 'module_comparison.png')
    plt.savefig(output_path, dpi=300)
    print(f"Graphique de comparaison des modules sauvegardé dans {output_path}")
    
    # Fermer la figure pour libérer la mémoire
    plt.close()

def generate_coverage_improvement_chart(history_file, output_dir):
    """
    Génère un graphique montrant l'amélioration de la couverture des tests.
    
    Args:
        history_file (str): Chemin vers le fichier d'historique
        output_dir (str): Répertoire de sortie pour les graphiques
    """
    if not os.path.exists(history_file):
        print(f"Le fichier d'historique {history_file} n'existe pas.")
        return
    
    try:
        with open(history_file, 'r') as f:
            history = json.load(f)
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier d'historique: {e}")
        return
    
    if len(history) < 2:
        print("L'historique doit contenir au moins deux entrées pour calculer l'amélioration.")
        return
    
    # Prendre la première et la dernière entrée
    first_entry = history[0]
    last_entry = history[-1]
    
    # Calculer l'amélioration pour la couverture globale
    initial_global = first_entry.get('global', 0)
    current_global = last_entry.get('global', 0)
    global_improvement = current_global - initial_global
    
    # Calculer l'amélioration pour chaque module
    module_improvements = {}
    first_packages = first_entry.get('packages', {})
    last_packages = last_entry.get('packages', {})
    
    all_packages = set(first_packages.keys()) | set(last_packages.keys())
    for package in all_packages:
        initial = first_packages.get(package, 0)
        current = last_packages.get(package, 0)
        module = map_package_to_module(package)
        
        if module not in module_improvements:
            module_improvements[module] = []
        
        module_improvements[module].append(current - initial)
    
    # Calculer la moyenne d'amélioration pour chaque module
    avg_improvements = {module: sum(improvements) / len(improvements) for module, improvements in module_improvements.items()}
    
    # Créer le graphique
    plt.figure(figsize=(10, 8))
    
    modules = list(avg_improvements.keys())
    improvements = list(avg_improvements.values())
    
    # Trier par amélioration
    sorted_indices = np.argsort(improvements)
    modules = [modules[i] for i in sorted_indices]
    improvements = [improvements[i] for i in sorted_indices]
    
    # Définir les couleurs
    colors = [COLORS.get(module, '#333333') for module in modules]
    
    # Créer le graphique à barres
    bars = plt.barh(modules, improvements, color=colors)
    
    # Ajouter les valeurs sur les barres
    for bar in bars:
        width = bar.get_width()
        plt.text(width + 0.5, bar.get_y() + bar.get_height()/2, f'{width:+.1f}%',
                 ha='left' if width >= 0 else 'right', va='center', fontsize=10)
    
    # Configurer le graphique
    plt.title('Amélioration de la Couverture des Tests par Module', fontsize=16)
    plt.xlabel('Amélioration (%)', fontsize=12)
    plt.ylabel('Module', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7, axis='x')
    plt.axvline(x=0, color='k', linestyle='-', linewidth=0.5)
    plt.tight_layout()
    
    # Sauvegarder le graphique
    output_path = os.path.join(output_dir, 'coverage_improvement.png')
    plt.savefig(output_path, dpi=300)
    print(f"Graphique d'amélioration de la couverture sauvegardé dans {output_path}")
    
    # Fermer la figure pour libérer la mémoire
    plt.close()

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description='Visualiser l\'évolution de la couverture des tests.')
    parser.add_argument('--xml', type=str, default='argumentation_analysis/tests/coverage.xml',
                        help='Chemin vers le fichier coverage.xml')
    parser.add_argument('--history', type=str, default='results/coverage_history.json',
                        help='Chemin vers le fichier d\'historique')
    parser.add_argument('--output', type=str, default='results/visualizations',
                        help='Répertoire de sortie pour les graphiques')
    parser.add_argument('--update-only', action='store_true',
                        help='Mettre à jour l\'historique sans générer de graphiques')
    
    args = parser.parse_args()
    
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(args.output, exist_ok=True)
    
    # Analyser le fichier coverage.xml
    coverage_data = parse_coverage_xml(Path(args.xml)) # Utiliser Path pour la fonction importée
    if coverage_data:
        # Sauvegarder les données dans l'historique
        history_file_path = Path(args.history) # Convertir en Path
        save_coverage_history(coverage_data, history_file_path) # Utiliser la fonction importée
        
        if not args.update_only:
            # Générer les graphiques en utilisant les fonctions importées
            # S'assurer que les arguments sont des Path pour les fonctions utilitaires
            history_file_path = Path(args.history)
            output_dir_path = Path(args.output)
            
            generate_coverage_trend_chart(history_file_path, output_dir_path, module_colors=COLORS)
            generate_module_comparison_chart(history_file_path, output_dir_path, module_colors=COLORS)
            generate_coverage_improvement_chart(history_file_path, output_dir_path, module_colors=COLORS)
    else:
        print(f"Impossible d'analyser le fichier {args.xml}")

if __name__ == "__main__":
    main()