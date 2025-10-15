# Authentic gpt-4o-mini imports (replacing mocks)
import openai
from semantic_kernel.contents import ChatHistory
from semantic_kernel.core_plugins import ConversationSummaryPlugin
from config.unified_config import UnifiedConfig

# -*- coding: utf-8 -*-
"""
Tests pour les utilitaires de vérification des extraits.
"""

import unittest

from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import patch, mock_open

# Fonctions à tester
from argumentation_analysis.utils.dev_tools.verification_utils import (
    verify_extract,
    verify_all_extracts,
    generate_verification_report,
)


class TestVerificationUtils(unittest.TestCase):
    async def _create_authentic_gpt4o_mini_instance(self):
        """Crée une instance authentique de gpt-4o-mini au lieu d'un mock."""
        config = UnifiedConfig()
        return config.get_kernel_with_gpt4o_mini()

    async def _make_authentic_llm_call(self, prompt: str) -> str:
        """Fait un appel authentique à gpt-4o-mini."""
        try:
            kernel = await self._create_authentic_gpt4o_mini_instance()
            result = await kernel.invoke("chat", input=prompt)
            return str(result)
        except Exception as e:
            logger.warning(f"Appel LLM authentique échoué: {e}")
            return "Authentic LLM call failed"

    """
    Suite de tests pour les fonctions dans verification_utils.py.
    """

    @patch(
        "argumentation_analysis.utils.dev_tools.verification_utils.extract_text_with_markers"
    )
    @patch("argumentation_analysis.utils.dev_tools.verification_utils.load_source_text")
    def test_verify_extract_valid(
        self, mock_load_source_text, mock_extract_text_with_markers
    ):
        """Teste verify_extract avec un cas valide."""
        mock_load_source_text.return_value = (
            "Texte source complet",
            "http://example.com/source",
        )
        mock_extract_text_with_markers.return_value = (
            "Texte extrait",
            "status_ok",
            True,
            True,
        )

        source_info = {"source_name": "Test Source", "url": "http://example.com/source"}
        extract_info = {
            "extract_name": "Test Extract",
            "start_marker": "Template START",
            "end_marker": "END",
            "template_start": "Template {0}",
        }

        result = verify_extract(source_info, extract_info)

        self.assertEqual(result["status"], "valid")
        self.assertEqual(
            result["message"], "Extrait valide. Les deux marqueurs ont été trouvés."
        )
        self.assertTrue(result["start_found"])
        self.assertTrue(result["end_found"])
        self.assertEqual(result["extracted_length"], len("Texte extrait"))
        mock_load_source_text.assert_called_once()
        mock_extract_text_with_markers.assert_called_once_with(
            "Texte source complet", "Template START", "END", "Template {0}"
        )

    @patch(
        "argumentation_analysis.utils.dev_tools.verification_utils.extract_text_with_markers"
    )
    @patch("argumentation_analysis.utils.dev_tools.verification_utils.load_source_text")
    def test_verify_extract_invalid_markers(
        self, mock_load_source_text, mock_extract_text_with_markers
    ):
        """Teste verify_extract quand les marqueurs ne sont pas trouvés."""
        mock_load_source_text.return_value = ("Texte source", "url")
        mock_extract_text_with_markers.return_value = ("", "status_fail", False, False)

        source_info = {"source_name": "S1"}
        extract_info = {
            "extract_name": "E1",
            "start_marker": "S",
            "end_marker": "E",
            "template_start": "T",
        }

        result = verify_extract(source_info, extract_info)
        self.assertEqual(result["status"], "invalid")
        self.assertIn("Les deux marqueurs sont introuvables", result["message"])
        self.assertFalse(result["start_found"])
        self.assertFalse(result["end_found"])

    @patch("argumentation_analysis.utils.dev_tools.verification_utils.load_source_text")
    def test_verify_extract_source_load_fail(self, mock_load_source_text):
        """Teste verify_extract quand le chargement de la source échoue."""
        mock_load_source_text.return_value = (None, "http://example.com/failed")

        source_info = {
            "source_name": "Failed Source",
            "url": "http://example.com/failed",
        }
        extract_info = {"extract_name": "Extract Fail"}

        result = verify_extract(source_info, extract_info)
        self.assertEqual(result["status"], "error")
        self.assertIn("Impossible de charger le texte source", result["message"])

    @patch(
        "argumentation_analysis.utils.dev_tools.verification_utils.extract_text_with_markers"
    )
    @patch("argumentation_analysis.utils.dev_tools.verification_utils.load_source_text")
    def test_verify_extract_warning_short_text(
        self, mock_load_source_text, mock_extract_text_with_markers
    ):
        """Teste verify_extract avec un texte extrait valide mais court."""
        mock_load_source_text.return_value = ("Texte source", "url")
        mock_extract_text_with_markers.return_value = (
            "Court",
            "status_ok",
            True,
            True,
        )  # "Court" a 5 caractères

        source_info = {"source_name": "S1"}
        extract_info = {
            "extract_name": "E1",
            "start_marker": "S",
            "end_marker": "E",
            "template_start": "T",
        }

        result = verify_extract(source_info, extract_info)
        self.assertEqual(result["status"], "warning")
        self.assertIn("Extrait valide mais très court", result["message"])
        self.assertEqual(result["extracted_length"], 5)

    @patch(
        "argumentation_analysis.utils.dev_tools.verification_utils.extract_text_with_markers"
    )
    @patch("argumentation_analysis.utils.dev_tools.verification_utils.load_source_text")
    def test_verify_extract_warning_template_issue(
        self, mock_load_source_text, mock_extract_text_with_markers
    ):
        """Teste verify_extract avec un problème de template potentiel."""
        mock_load_source_text.return_value = ("Texte source", "url")
        # Simuler un start_marker qui ne commence PAS par le template (sans {0})
        mock_extract_text_with_markers.return_value = (
            "Texte assez long",
            "status_ok",
            True,
            True,
        )

        source_info = {"source_name": "S1"}
        extract_info = {
            "extract_name": "E1",
            "start_marker": "XSTART",  # Ne correspond pas à "Template "
            "end_marker": "END",
            "template_start": "Template {0}",  # template_start.replace("{0}", "") == "Template "
        }

        result = verify_extract(source_info, extract_info)
        self.assertEqual(result["status"], "warning")
        self.assertIn("ne commence pas par le template attendu", result["message"])
        self.assertTrue(result.get("template_issue"))

    @patch("argumentation_analysis.utils.dev_tools.verification_utils.verify_extract")
    def test_verify_all_extracts(self, mock_verify_extract):
        """Teste verify_all_extracts."""
        mock_verify_extract.side_effect = [
            {"status": "valid", "source_name": "S1", "extract_name": "E1.1"},
            {"status": "invalid", "source_name": "S1", "extract_name": "E1.2"},
            {"status": "valid", "source_name": "S2", "extract_name": "E2.1"},
        ]

        extract_definitions_list = [
            {
                "source_name": "S1",
                "extracts": [{"extract_name": "E1.1"}, {"extract_name": "E1.2"}],
            },
            {"source_name": "S2", "extracts": [{"extract_name": "E2.1"}]},
        ]

        results = verify_all_extracts(extract_definitions_list)

        self.assertEqual(len(results), 3)
        self.assertEqual(mock_verify_extract.call_count, 3)
        mock_verify_extract.assert_any_call(
            extract_definitions_list[0], extract_definitions_list[0]["extracts"][0]
        )
        mock_verify_extract.assert_any_call(
            extract_definitions_list[0], extract_definitions_list[0]["extracts"][1]
        )
        mock_verify_extract.assert_any_call(
            extract_definitions_list[1], extract_definitions_list[1]["extracts"][0]
        )

    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_generate_verification_report(self, mock_file_open, mock_mkdir):
        """Teste la génération du rapport de vérification."""
        results_data: List[Dict[str, Any]] = [
            {
                "source_name": "Source A",
                "extract_name": "Extrait 1",
                "status": "valid",
                "message": "OK",
                "extracted_length": 100,
                "start_found": True,
                "end_found": True,
            },
            {
                "source_name": "Source B",
                "extract_name": "Extrait 2",
                "status": "invalid",
                "message": "Marqueur début manquant",
                "start_found": False,
                "end_found": True,
            },
            {
                "source_name": "Source C",
                "extract_name": "Extrait 3",
                "status": "warning",
                "message": "Trop court",
                "extracted_length": 5,
                "start_found": True,
                "end_found": True,
                "template_issue": False,
                "encoding_issues": False,
            },
            {
                "source_name": "Source D",
                "extract_name": "Extrait 4",
                "status": "error",
                "message": "Chargement source impossible",
            },
        ]
        output_file_path = "test_report.html"

        generate_verification_report(results_data, output_file_path)

        mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)
        mock_file_open.assert_called_once_with(
            Path(output_file_path), "w", encoding="utf-8"
        )

        # Vérifier que le contenu HTML contient des éléments clés
        html_content = mock_file_open().write.call_args[0][0]
        self.assertIn("<h1>Rapport de vérification des extraits</h1>", html_content)
        self.assertIn("Total des extraits vérifiés: <strong>4</strong>", html_content)
        self.assertIn(
            'Extraits valides: <strong class="valid">1</strong>', html_content
        )
        self.assertIn(
            'Extraits avec avertissements: <strong class="warning">1</strong>',
            html_content,
        )
        self.assertIn(
            'Extraits invalides: <strong class="invalid">1</strong>', html_content
        )
        self.assertIn('Erreurs: <strong class="error">1</strong>', html_content)
        self.assertIn("<td>Source A</td><td>Extrait 1</td><td>valid</td>", html_content)
        self.assertIn(
            "<td>Source B</td><td>Extrait 2</td><td>invalid</td>", html_content
        )


if __name__ == "__main__":
    unittest.main(argv=["first-arg-is-ignored"], exit=False)
