#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le service d'extraction

Ce module contient les tests unitaires pour le service d'extraction (ExtractService)
qui est responsable de l'extraction de texte à partir de sources en utilisant des marqueurs.
"""

import pytest
import re
import os
import sys
from unittest.mock import patch, MagicMock

# Ajouter le répertoire parent au chemin de recherche des modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer les modules à tester
from argumentation_analysis.services.extract_service import ExtractService


@pytest.fixture
def extract_service():
    """Fixture pour le service d'extraction."""
    return ExtractService()


@pytest.fixture
def sample_text():
    """Fixture pour un texte source d'exemple."""
    return """
    Ceci est un exemple de texte source.
    Il contient plusieurs paragraphes.
    
    Voici un marqueur de début: DEBUT_EXTRAIT
    Ceci est le contenu de l'extrait.
    Il peut contenir plusieurs lignes.
    Voici un marqueur de fin: FIN_EXTRAIT
    
    Et voici la suite du texte après l'extrait.
    """


class TestExtractService:
    """Tests pour le service d'extraction."""

    def test_extract_text_with_markers_valid(self, extract_service, sample_text):
        """Test d'extraction avec des marqueurs valides."""
        start_marker = "DEBUT_EXTRAIT"
        end_marker = "FIN_EXTRAIT"
        
        extracted_text, status, start_found, end_found = extract_service.extract_text_with_markers(
            sample_text, start_marker, end_marker
        )
        
        # Vérifier que l'extraction a réussi
        assert start_found is True
        assert end_found is True
        assert "✅ Extraction réussie" in status
        
        # Vérifier le contenu extrait
        expected_text = "Ceci est le contenu de l'extrait.\n    Il peut contenir plusieurs lignes.\n    " # Ajusté pour l'indentation et pour exclure le marqueur de fin implicitement
        assert extracted_text.strip() == expected_text.strip() # Comparaison après strip pour gérer les variations d'espaces

    def test_extract_text_with_markers_invalid_start(self, extract_service, sample_text):
        """Test d'extraction avec un marqueur de début invalide."""
        invalid_start_marker = "MARQUEUR_INEXISTANT"
        end_marker = "FIN_EXTRAIT"
        
        extracted_text, status, start_found, end_found = extract_service.extract_text_with_markers(
            sample_text, invalid_start_marker, end_marker
        )
        
        # Vérifier que l'extraction a échoué
        assert start_found is False
        assert end_found is True
        assert "⚠️ Marqueur début non trouvé" in status

    def test_extract_text_with_markers_invalid_end(self, extract_service, sample_text):
        """Test d'extraction avec un marqueur de fin invalide."""
        start_marker = "DEBUT_EXTRAIT"
        invalid_end_marker = "MARQUEUR_INEXISTANT"
        
        extracted_text, status, start_found, end_found = extract_service.extract_text_with_markers(
            sample_text, start_marker, invalid_end_marker
        )
        
        # Vérifier que l'extraction a échoué
        assert start_found is True
        assert end_found is False
        assert "⚠️ Marqueur fin non trouvé" in status

    def test_extract_text_with_template(self, extract_service):
        """Test d'extraction avec un template pour le marqueur de début."""
        # Texte avec une première lettre manquante
        text_with_missing_letter = """
        Ceci est un exemple de texte source.
        Il contient plusieurs paragraphes.
        
        Voici un marqueur de début: EBUT_EXTRAIT
        Ceci est le contenu de l'extrait.
        Il peut contenir plusieurs lignes.
        Voici un marqueur de fin: FIN_EXTRAIT
        
        Et voici la suite du texte après l'extrait.
        """
        
        # Template qui ajoute la lettre 'D' au début
        template_start = "D{0}"
        start_marker = "EBUT_EXTRAIT"
        end_marker = "FIN_EXTRAIT"
        
        extracted_text, status, start_found, end_found = extract_service.extract_text_with_markers(
            text_with_missing_letter, start_marker, end_marker, template_start
        )
        
        # Vérifier que l'extraction a réussi
        assert start_found is True
        assert end_found is True
        assert "✅ Extraction réussie" in status
        
        # Vérifier le contenu extrait
        expected_text = "Ceci est le contenu de l'extrait.\n        Il peut contenir plusieurs lignes.\n        " # Ajusté pour l'indentation et pour exclure le marqueur de fin implicitement
        assert extracted_text.strip() == expected_text.strip() # Comparaison après strip

    def test_extract_text_empty_text(self, extract_service):
        """Test d'extraction avec un texte vide."""
        start_marker = "DEBUT_EXTRAIT"
        end_marker = "FIN_EXTRAIT"
        
        extracted_text, status, start_found, end_found = extract_service.extract_text_with_markers(
            "", start_marker, end_marker
        )
        
        assert extracted_text is None
        assert "Texte source vide" in status
        assert start_found is False
        assert end_found is False

    def test_find_similar_text(self, extract_service):
        """Test de recherche de texte similaire."""
        text = "Ceci est un exemple de texte. Il contient des mots similaires comme exemple et texte."
        search_text = "exemple de texte"
        
        results = extract_service.find_similar_text(text, search_text)
        
        # Vérifier qu'au moins un résultat a été trouvé
        assert len(results) > 0
        
        # Vérifier que le premier résultat contient le texte recherché
        context, position, found_text = results[0]
        assert search_text in found_text
        assert position >= 0
        assert search_text in context

    def test_find_similar_text_empty(self, extract_service):
        """Test de recherche de texte similaire avec des entrées vides."""
        # Cas 1: Texte vide
        results = extract_service.find_similar_text("", "exemple")
        assert len(results) == 0
        
        # Cas 2: Marqueur vide
        results = extract_service.find_similar_text("Ceci est un exemple", "")
        assert len(results) == 0

    def test_find_similar_text_long_marker(self, extract_service):
        """Test de recherche de texte similaire avec un marqueur long."""
        text = "Ceci est un exemple de texte long pour tester la recherche de similarité."
        search_text = "exemple de texte long pour tester la recherche"
        
        results = extract_service.find_similar_text(text, search_text)
        
        assert len(results) > 0
        context, position, found_text = results[0]
        assert position >= 0
        assert len(context) > 0

    def test_highlight_text(self, extract_service, sample_text):
        """Test de mise en évidence des marqueurs dans le texte."""
        start_marker = "DEBUT_EXTRAIT"
        end_marker = "FIN_EXTRAIT"
        
        html_text, start_found, end_found = extract_service.highlight_text(
            sample_text, start_marker, end_marker
        )
        
        assert start_found is True
        assert end_found is True
        assert "<span style='background-color: #FFFF00; font-weight: bold;'>DEBUT_EXTRAIT</span>" in html_text
        assert "<span style='background-color: #FFFF00; font-weight: bold;'>FIN_EXTRAIT</span>" in html_text

    def test_highlight_text_empty(self, extract_service):
        """Test de mise en évidence avec un texte vide."""
        html_text, start_found, end_found = extract_service.highlight_text(
            "", "DEBUT", "FIN"
        )
        
        assert start_found is False
        assert end_found is False
        assert "<p>Texte vide</p>" in html_text

    def test_search_in_text(self, extract_service, sample_text):
        """Test de recherche dans le texte."""
        search_term = "exemple"
        
        matches = extract_service.search_in_text(sample_text, search_term)
        
        assert len(matches) > 0
        assert isinstance(matches[0], re.Match)
        assert matches[0].group() == search_term

    def test_search_in_text_case_sensitive(self, extract_service):
        """Test de recherche sensible à la casse."""
        text = "Exemple et exemple sont différents en casse."
        
        # Recherche insensible à la casse
        matches_insensitive = extract_service.search_in_text(text, "exemple", case_sensitive=False)
        assert len(matches_insensitive) == 2
        
        # Recherche sensible à la casse
        matches_sensitive = extract_service.search_in_text(text, "exemple", case_sensitive=True)
        assert len(matches_sensitive) == 1
        assert matches_sensitive[0].group() == "exemple"

    def test_highlight_search_results(self, extract_service, sample_text):
        """Test de mise en évidence des résultats de recherche."""
        search_term = "exemple"
        
        html_results, count = extract_service.highlight_search_results(sample_text, search_term)
        
        assert count > 0
        assert "<span style='background-color: #4CAF50; color: white; font-weight: bold;'>exemple</span>" in html_results

    def test_highlight_search_results_empty(self, extract_service):
        """Test de mise en évidence des résultats avec des entrées vides."""
        # Cas 1: Texte vide
        html_results, count = extract_service.highlight_search_results("", "exemple")
        assert count == 0
        assert "Texte vide ou terme de recherche manquant" in html_results
        
        # Cas 2: Terme de recherche vide
        html_results, count = extract_service.highlight_search_results("Ceci est un exemple", "")
        assert count == 0
        assert "Texte vide ou terme de recherche manquant" in html_results

    def test_extract_blocks(self, extract_service):
        """Test d'extraction de blocs de texte."""
        text = "A" * 1000  # Texte de 1000 caractères
        block_size = 300
        overlap = 50
        
        blocks = extract_service.extract_blocks(text, block_size, overlap)
        
        assert len(blocks) > 0
        assert blocks[0]["start_pos"] == 0
        assert blocks[0]["end_pos"] == 300
        assert len(blocks[0]["block"]) == 300
        
        # Vérifier le chevauchement
        assert blocks[1]["start_pos"] == 250  # 300 - 50
        assert blocks[1]["end_pos"] == 550

    def test_extract_blocks_empty(self, extract_service):
        """Test d'extraction de blocs avec un texte vide."""
        blocks = extract_service.extract_blocks("")
        assert len(blocks) == 0

    def test_search_text_dichotomically(self, extract_service):
        """Test de recherche dichotomique dans le texte."""
        text = "Ceci est un exemple. " * 100  # Répéter pour avoir un texte long
        search_term = "exemple"
        
        results = extract_service.search_text_dichotomically(text, search_term)
        
        assert len(results) > 0
        assert results[0]["match"] == search_term
        assert "context" in results[0]
        assert "position" in results[0]

    def test_search_text_dichotomically_empty(self, extract_service):
        """Test de recherche dichotomique avec des entrées vides."""
        # Cas 1: Texte vide
        results = extract_service.search_text_dichotomically("", "exemple")
        assert len(results) == 0
        
        # Cas 2: Terme de recherche vide
        results = extract_service.search_text_dichotomically("Ceci est un exemple", "")
        assert len(results) == 0