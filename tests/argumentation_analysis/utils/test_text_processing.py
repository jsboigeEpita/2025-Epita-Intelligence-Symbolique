#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour les utilitaires de traitement de texte.
"""

import unittest
from argumentation_analysis.utils.text_processing import split_text_into_arguments, generate_sample_text

class TestTextProcessing(unittest.TestCase):
    """Classe de test pour les fonctions de text_processing."""

    def test_split_text_into_arguments_simple(self):
        """Teste la division simple avec des points."""
        text = "Premier argument. Deuxième argument assez long pour être compté. Troisième argument également."
        expected = [
            "Premier argument",
            "Deuxième argument assez long pour être compté",
            "Troisième argument également"
        ]
        self.assertEqual(split_text_into_arguments(text), expected)

    def test_split_text_into_arguments_various_delimiters(self):
        """Teste la division avec divers délimiteurs."""
        text = "Argument un! Argument deux? Argument trois.\nArgument quatre. \nArgument cinq! \nArgument six?"
        expected = [
            "Argument un",
            "Argument deux",
            "Argument trois",
            "Argument quatre",
            "Argument cinq",
            "Argument six"
        ]
        # La fonction filtre les arguments courts, donc ceux-ci ne passeront pas
        # s'ils ne sont pas assez longs. Ajustons les attentes ou le texte.
        # Pour l'instant, on s'attend à ce que les arguments soient assez longs.
        # Si la logique de filtrage par longueur est stricte, il faut des exemples plus longs.
        # Modifions le texte pour que les arguments soient plus longs.
        text_long = "Argument un est suffisamment long! Argument deux l'est aussi? Argument trois avec un point.\nArgument quatre est aussi long. \nArgument cinq est très très long! \nArgument six est le dernier ici?"
        expected_long = [
            "Argument un est suffisamment long",
            "Argument deux l'est aussi",
            "Argument trois avec un point",
            "Argument quatre est aussi long",
            "Argument cinq est très très long",
            "Argument six est le dernier ici"
        ]
        self.assertEqual(split_text_into_arguments(text_long), expected_long)

    def test_split_text_into_arguments_empty_and_short(self):
        """Teste avec du texte vide et des arguments courts."""
        self.assertEqual(split_text_into_arguments(""), [])
        self.assertEqual(split_text_into_arguments("Court."), [])
        self.assertEqual(split_text_into_arguments("Un. Deux. Trois arguments ici."), ["Trois arguments ici"]) # Seul le dernier est assez long

    def test_split_text_into_arguments_no_delimiter(self):
        """Teste un texte sans délimiteur clair (devrait retourner le texte si assez long)."""
        text = "Ceci est un seul long argument sans délimiteur standard"
        self.assertEqual(split_text_into_arguments(text), [text])
        text_court = "Court"
        self.assertEqual(split_text_into_arguments(text_court), [])

    def test_generate_sample_text_lincoln(self):
        """Teste la génération de texte pour Lincoln."""
        text = generate_sample_text("Discours de Lincoln", "Gettysburg Address")
        self.assertIn("Nous sommes engagés dans une grande guerre civile", text)
        text2 = generate_sample_text("Quelque chose sur Lincoln", "Autre source")
        self.assertIn("Nous sommes engagés dans une grande guerre civile", text2)

    def test_generate_sample_text_debat(self):
        """Teste la génération de texte pour un débat/discours."""
        text = generate_sample_text("Débat important", "Source politique")
        self.assertIn("Mesdames et messieurs", text)
        text2 = generate_sample_text("Discours inaugural", "Événement")
        self.assertIn("Mesdames et messieurs", text2)

    def test_generate_sample_text_default(self):
        """Teste la génération de texte par défaut."""
        text = generate_sample_text("Extrait inconnu", "Source X")
        self.assertIn("L'argumentation est l'art de convaincre", text)

if __name__ == '__main__':
    unittest.main()