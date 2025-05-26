#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import csv

# Créer le répertoire de test
test_data_dir = os.path.join('tests', 'test_data')
os.makedirs(test_data_dir, exist_ok=True)

# Créer le fichier CSV de test
test_taxonomy_path = os.path.join(test_data_dir, 'test_taxonomy.csv')
with open(test_taxonomy_path, 'w', encoding='utf-8') as f:
    f.write("PK,Name,Category,Description,Example,Counter_Example\n")
    f.write("1,Appel à l'autorité,Fallacy,Invoquer une autorité non pertinente,\"Einstein a dit que Dieu ne joue pas aux dés, donc la mécanique quantique est fausse.\",\"Selon le consensus scientifique, le réchauffement climatique est réel.\"\n")
    f.write("2,Pente glissante,Fallacy,Suggérer qu'une action mènera inévitablement à une chaîne d'événements indésirables,\"Si nous légalisons la marijuana, bientôt toutes les drogues seront légales.\",\"Si nous augmentons le salaire minimum, certaines entreprises pourraient réduire leurs effectifs.\"\n")
    f.write("3,Ad hominem,Fallacy,Attaquer la personne plutôt que ses idées,\"Vous êtes trop jeune pour comprendre la politique.\",\"Votre argument est basé sur des données obsolètes.\"\n")

print(f"Fichier créé: {test_taxonomy_path}")

# Lire le fichier avec le module csv standard
with open(test_taxonomy_path, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)
    print(f"Header lu par csv.reader: {header}")
    print(f"Nombre de colonnes: {len(header)}")
    
    rows = list(reader)
    print(f"Nombre de lignes de données: {len(rows)}")
    for i, row in enumerate(rows):
        print(f"Ligne {i+1}: {len(row)} colonnes - {row}")

# Tester avec notre mock pandas
import sys
sys.path.append('tests/mocks')
from pandas_mock import read_csv

print("\n--- Test avec mock pandas ---")
df = read_csv(test_taxonomy_path)
print(f"Colonnes du DataFrame: {df.columns}")
print(f"Nombre de colonnes: {len(df.columns)}")
print(f"Données: {df._data}")