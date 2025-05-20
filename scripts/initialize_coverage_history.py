#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour initialiser l'historique de couverture des tests.

Ce script crée un fichier d'historique initial avec les données de couverture actuelles
et une entrée fictive antérieure pour permettre la visualisation de l'évolution.
"""

import os
import sys
import json
import datetime
import xml.etree.ElementTree as ET
from pathlib import Path

def parse_coverage_xml(xml_path):
    """
    Parse un fichier coverage.xml et extrait les informations de couverture.
    
    Args:
        xml_path (str): Chemin vers le fichier coverage.xml
        
    Returns:
        dict: Dictionnaire contenant les informations de couverture
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Extraire la couverture globale
        line_rate = float(root.attrib.get('line-rate', '0')) * 100
        lines_valid = int(root.attrib.get('lines-valid', '0'))
        lines_covered = int(root.attrib.get('lines-covered', '0'))
        
        # Extraire la couverture par package
        packages = {}
        for package in root.findall('.//package'):
            name = package.attrib.get('name', '')
            package_line_rate = float(package.attrib.get('line-rate', '0')) * 100
            packages[name] = package_line_rate
        
        return {
            'global': line_rate,
            'lines_valid': lines_valid,
            'lines_covered': lines_covered,
            'packages': packages,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d')
        }
    except Exception as e:
        print(f"Erreur lors de l'analyse du fichier XML: {e}")
        return None

def create_initial_history(coverage_data, history_file):
    """
    Crée un fichier d'historique initial avec les données de couverture actuelles
    et une entrée fictive antérieure.
    
    Args:
        coverage_data (dict): Données de couverture actuelles
        history_file (str): Chemin vers le fichier d'historique à créer
    """
    # Créer une entrée fictive antérieure avec une couverture légèrement inférieure
    previous_date = (datetime.datetime.now() - datetime.timedelta(days=30)).strftime('%Y-%m-%d')
    previous_coverage = coverage_data.copy()
    previous_coverage['timestamp'] = previous_date
    
    # Réduire légèrement la couverture pour simuler une amélioration
    previous_coverage['global'] = max(0, previous_coverage['global'] - 5)
    previous_coverage['lines_covered'] = int(previous_coverage['lines_covered'] * 0.9)
    
    # Réduire la couverture de chaque package
    previous_packages = {}
    for package, coverage in previous_coverage['packages'].items():
        previous_packages[package] = max(0, coverage - 5)
    previous_coverage['packages'] = previous_packages
    
    # Créer l'historique avec les deux entrées
    history = [previous_coverage, coverage_data]
    
    # Sauvegarder l'historique
    try:
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
        print(f"Historique de couverture initialisé dans {history_file}")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde du fichier d'historique: {e}")

def main():
    """Fonction principale."""
    # Définir les chemins
    xml_path = 'argumentation_analysis/tests/coverage.xml'
    history_file = 'results/coverage_history.json'
    
    # Vérifier si le fichier d'historique existe déjà
    if os.path.exists(history_file):
        print(f"Le fichier d'historique {history_file} existe déjà.")
        overwrite = input("Voulez-vous l'écraser ? (o/n): ").lower()
        if overwrite != 'o':
            print("Opération annulée.")
            return
    
    # Analyser le fichier coverage.xml
    coverage_data = parse_coverage_xml(xml_path)
    if coverage_data:
        # Créer l'historique initial
        create_initial_history(coverage_data, history_file)
        print("Historique de couverture initialisé avec succès.")
        print("Vous pouvez maintenant exécuter le script visualize_test_coverage.py pour générer les graphiques.")
    else:
        print(f"Impossible d'analyser le fichier {xml_path}")

if __name__ == "__main__":
    main()