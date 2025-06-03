#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script de test pour évaluer les messages d'erreur de validation des extraits.
"""

import sys
import os
import json

# Ajouter le répertoire racine au chemin Python pour pouvoir importer les modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# L'installation du package via `pip install -e .` devrait gérer l'accessibilité,
# mais cette modification assure le fonctionnement même sans installation en mode édition.

# Définir une classe de validation simplifiée pour les tests
class ExtractValidator:
    def __init__(self):
        self.errors = []
    
    def validate_source(self, source):
        """Valide une source d'extraits."""
        self.errors = []
        
        # Vérifier les champs obligatoires
        if 'source_name' not in source:
            self.errors.append("Erreur de validation: Champ 'source_name' manquant.")
        
        if 'source_type' not in source:
            self.errors.append("Erreur de validation: Champ 'source_type' manquant.")
        
        # Vérifier le type de source
        if 'source_type' in source:
            if source['source_type'] not in ['url', 'file', 'text']:
                self.errors.append(f"Erreur de validation: Type de source '{source['source_type']}' invalide. Valeurs acceptées: 'url', 'file', 'text'.")
        
        # Vérifier les champs spécifiques au type de source
        if 'source_type' in source and source['source_type'] == 'url':
            if 'schema' not in source:
                self.errors.append("Erreur de validation: Champ 'schema' manquant pour une source de type 'url'.")
            elif source['schema'] not in ['http', 'https']:
                self.errors.append(f"Erreur de validation: Schéma '{source['schema']}' invalide. Valeurs acceptées: 'http', 'https'.")
            
            if 'host_parts' not in source:
                self.errors.append("Erreur de validation: Champ 'host_parts' manquant pour une source de type 'url'.")
            elif not isinstance(source['host_parts'], list):
                self.errors.append("Erreur de validation: Le champ 'host_parts' doit être une liste.")
            elif any(not part for part in source['host_parts']):
                self.errors.append("Erreur de validation: Les parties d'hôte ne doivent pas contenir de chaînes vides.")
            
            if 'path' not in source:
                self.errors.append("Erreur de validation: Champ 'path' manquant pour une source de type 'url'.")
            elif not source['path'].startswith('/'):
                self.errors.append("Erreur de validation: Le chemin doit commencer par '/'.")
        
        # Vérifier les extraits
        if 'extracts' not in source:
            self.errors.append("Erreur de validation: Champ 'extracts' manquant.")
        elif not isinstance(source['extracts'], list):
            self.errors.append("Erreur de validation: Le champ 'extracts' doit être une liste.")
        else:
            extract_names = set()
            for i, extract in enumerate(source['extracts']):
                # Vérifier les champs obligatoires
                if 'extract_name' not in extract:
                    self.errors.append(f"Erreur de validation: Champ 'extract_name' manquant pour l'extrait #{i+1}.")
                elif not isinstance(extract['extract_name'], str):
                    self.errors.append(f"Erreur de validation: Le champ 'extract_name' doit être une chaîne de caractères pour l'extrait #{i+1}.")
                else:
                    if extract['extract_name'] in extract_names:
                        self.errors.append(f"Erreur de validation: Nom d'extrait '{extract['extract_name']}' dupliqué.")
                    extract_names.add(extract['extract_name'])
                
                if 'start_marker' not in extract:
                    self.errors.append(f"Erreur de validation: Champ 'start_marker' manquant pour l'extrait '{extract.get('extract_name', f'#{i+1}')}.")
                
                if 'end_marker' not in extract:
                    self.errors.append(f"Erreur de validation: Champ 'end_marker' manquant pour l'extrait '{extract.get('extract_name', f'#{i+1}')}.")
                elif not extract['end_marker']:
                    self.errors.append(f"Erreur de validation: Marqueur de fin vide pour l'extrait '{extract.get('extract_name', f'#{i+1}')}.")
        
        return len(self.errors) == 0
    
    def get_errors(self):
        """Retourne les erreurs de validation."""
        return self.errors

def test_missing_fields():
    print("\n=== Test avec champs manquants ===")
    validator = ExtractValidator()
    source = {
        "source_name": "Source incomplète",
        "extracts": [
            {
                "extract_name": "Extrait incomplet",
                "start_marker": "Début"
            }
        ]
    }
    is_valid = validator.validate_source(source)
    print(f"Source valide: {is_valid}")
    if not is_valid:
        for error in validator.get_errors():
            print(f"  - {error}")

def test_invalid_types():
    print("\n=== Test avec types invalides ===")
    validator = ExtractValidator()
    source = {
        "source_name": "Source avec types invalides",
        "source_type": "url",
        "schema": "https",
        "host_parts": "example.com",  # Devrait être une liste
        "path": "/page",
        "extracts": [
            {
                "extract_name": 42,  # Devrait être une chaîne
                "start_marker": "Début",
                "end_marker": "Fin"
            }
        ]
    }
    is_valid = validator.validate_source(source)
    print(f"Source valide: {is_valid}")
    if not is_valid:
        for error in validator.get_errors():
            print(f"  - {error}")

def test_invalid_url_components():
    print("\n=== Test avec composants d'URL invalides ===")
    validator = ExtractValidator()
    source = {
        "source_name": "Source avec URL invalide",
        "source_type": "url",
        "schema": "ftp",  # Invalide
        "host_parts": ["example", ""],  # Contient une chaîne vide
        "path": "page-sans-slash",  # Ne commence pas par /
        "extracts": []
    }
    is_valid = validator.validate_source(source)
    print(f"Source valide: {is_valid}")
    if not is_valid:
        for error in validator.get_errors():
            print(f"  - {error}")

def test_duplicate_extract_names():
    print("\n=== Test avec noms d'extraits dupliqués ===")
    validator = ExtractValidator()
    source = {
        "source_name": "Source avec extraits dupliqués",
        "source_type": "url",
        "schema": "https",
        "host_parts": ["example", "com"],
        "path": "/page",
        "extracts": [
            {
                "extract_name": "Extrait dupliqué",
                "start_marker": "Début 1",
                "end_marker": "Fin 1"
            },
            {
                "extract_name": "Extrait dupliqué",  # Nom dupliqué
                "start_marker": "Début 2",
                "end_marker": "Fin 2"
            }
        ]
    }
    is_valid = validator.validate_source(source)
    print(f"Source valide: {is_valid}")
    if not is_valid:
        for error in validator.get_errors():
            print(f"  - {error}")

def test_valid_source():
    print("\n=== Test avec source valide ===")
    validator = ExtractValidator()
    source = {
        "source_name": "Source valide",
        "source_type": "url",
        "schema": "https",
        "host_parts": ["example", "com"],
        "path": "/page",
        "extracts": [
            {
                "extract_name": "Extrait 1",
                "start_marker": "Début 1",
                "end_marker": "Fin 1"
            },
            {
                "extract_name": "Extrait 2",
                "start_marker": "Début 2",
                "end_marker": "Fin 2"
            }
        ]
    }
    is_valid = validator.validate_source(source)
    print(f"Source valide: {is_valid}")
    if not is_valid:
        for error in validator.get_errors():
            print(f"  - {error}")

if __name__ == "__main__":
    print("=== Tests des messages d'erreur de validation des extraits ===")
    test_missing_fields()
    test_invalid_types()
    test_invalid_url_components()
    test_duplicate_extract_names()
    test_valid_source()