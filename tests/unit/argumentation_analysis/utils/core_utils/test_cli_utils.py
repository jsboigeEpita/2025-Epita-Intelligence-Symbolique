# -*- coding: utf-8 -*-
"""Tests pour les utilitaires CLI."""

import pytest
import argparse
from unittest.mock import patch

from argumentation_analysis.core.utils.cli_utils import (
    parse_advanced_analysis_arguments,
    parse_summary_generation_arguments,
    parse_extract_verification_arguments,
    parse_extract_repair_arguments,  # Ajout de l'import
)


def test_parse_advanced_analysis_arguments_defaults():
    """Teste les valeurs par défaut lorsque aucun argument n'est fourni."""
    with patch("sys.argv", ["script_name"]):  # Simule l'appel sans arguments
        args = parse_advanced_analysis_arguments()

    assert args.extracts is None
    assert args.base_results is None
    assert args.output is None
    assert args.verbose is False


def test_parse_advanced_analysis_arguments_extracts_provided():
    """Teste la fourniture de l'argument --extracts."""
    test_path = "/path/to/extracts.json"
    with patch("sys.argv", ["script_name", "--extracts", test_path]):
        args = parse_advanced_analysis_arguments()
    assert args.extracts == test_path


def test_parse_advanced_analysis_arguments_base_results_provided():
    """Teste la fourniture de l'argument --base-results."""
    test_path = "results/base.json"
    with patch("sys.argv", ["script_name", "--base-results", test_path]):
        args = parse_advanced_analysis_arguments()
    assert args.base_results == test_path


def test_parse_advanced_analysis_arguments_output_provided():
    """Teste la fourniture de l'argument --output."""
    test_path = "output/advanced.json"
    with patch("sys.argv", ["script_name", "-o", test_path]):  # Test avec l'alias court
        args = parse_advanced_analysis_arguments()
    assert args.output == test_path


def test_parse_advanced_analysis_arguments_verbose_true():
    """Teste la fourniture de l'argument --verbose."""
    with patch("sys.argv", ["script_name", "--verbose"]):
        args = parse_advanced_analysis_arguments()
    assert args.verbose is True

    with patch("sys.argv", ["script_name", "-v"]):  # Test avec l'alias court
        args_v = parse_advanced_analysis_arguments()
    assert args_v.verbose is True


def test_parse_advanced_analysis_arguments_all_provided():
    """Teste la fourniture de tous les arguments."""
    extracts_p = "data/extracts.enc"
    base_p = "data/base_res.json"
    output_p = "out/final_adv.json"

    cli_args = [
        "script_name",
        "--extracts",
        extracts_p,
        "-b",
        base_p,  # Utilisation de l'alias
        "--output",
        output_p,
        "-v",
    ]
    with patch("sys.argv", cli_args):
        args = parse_advanced_analysis_arguments()

    assert args.extracts == extracts_p
    assert args.base_results == base_p
    assert args.output == output_p
    assert args.verbose is True


# Il n'est généralement pas nécessaire de tester si argparse lève des erreurs pour des types incorrects
# car c'est le comportement intégré d'argparse. On teste que nos définitions sont correctes.
# On a défini type=str pour les chemins, la conversion en Path se fait dans le script appelant.
# --- Tests for parse_summary_generation_arguments ---


def test_parse_summary_generation_arguments_defaults():
    """Teste les valeurs par défaut pour la génération de synthèses."""
    with patch("sys.argv", ["script_name"]):
        args = parse_summary_generation_arguments()
    assert args.output_dir == "results"  # Valeur par défaut définie dans la fonction
    assert args.verbose is False


def test_parse_summary_generation_arguments_output_dir_provided():
    """Teste la fourniture de l'argument --output-dir."""
    test_dir = "my_custom_reports"
    with patch("sys.argv", ["script_name", "--output-dir", test_dir]):
        args = parse_summary_generation_arguments()
    assert args.output_dir == test_dir

    with patch(
        "sys.argv", ["script_name", "-o", "other_dir"]
    ):  # Test avec l'alias court
        args_o = parse_summary_generation_arguments()
    assert args_o.output_dir == "other_dir"


def test_parse_summary_generation_arguments_verbose_true():
    """Teste la fourniture de l'argument --verbose pour la génération de synthèses."""
    with patch("sys.argv", ["script_name", "--verbose"]):
        args = parse_summary_generation_arguments()
    assert args.verbose is True

    with patch("sys.argv", ["script_name", "-v"]):  # Test avec l'alias court
        args_v = parse_summary_generation_arguments()
    assert args_v.verbose is True


def test_parse_summary_generation_arguments_all_provided():
    """Teste la fourniture de tous les arguments pour la génération de synthèses."""
    output_d = "final_summaries"

    cli_args = ["script_name", "--output-dir", output_d, "-v"]
    with patch("sys.argv", cli_args):
        args = parse_summary_generation_arguments()

    assert args.output_dir == output_d
    assert args.verbose is True


# --- Tests for parse_extract_verification_arguments ---


def test_parse_extract_verification_arguments_defaults():
    """Teste les valeurs par défaut pour la vérification des extraits."""
    with patch("sys.argv", ["script_name"]):
        args = parse_extract_verification_arguments()
    assert args.output == "verify_report.html"  # Valeur par défaut
    assert args.verbose is False
    assert args.input is None  # Valeur par défaut
    assert args.hitler_only is False  # Valeur par défaut


def test_parse_extract_verification_arguments_output_provided():
    """Teste la fourniture de l'argument --output."""
    test_file = "custom_report.html"
    with patch("sys.argv", ["script_name", "--output", test_file]):
        args = parse_extract_verification_arguments()
    assert args.output == test_file

    with patch(
        "sys.argv", ["script_name", "-o", "other_report.xml"]
    ):  # Test avec l'alias court
        args_o = parse_extract_verification_arguments()
    assert args_o.output == "other_report.xml"


def test_parse_extract_verification_arguments_verbose_true():
    """Teste la fourniture de l'argument --verbose."""
    with patch("sys.argv", ["script_name", "--verbose"]):
        args = parse_extract_verification_arguments()
    assert args.verbose is True

    with patch("sys.argv", ["script_name", "-v"]):  # Test avec l'alias court
        args_v = parse_extract_verification_arguments()
    assert args_v.verbose is True


def test_parse_extract_verification_arguments_input_provided():
    """Teste la fourniture de l'argument --input."""
    test_input_file = "my_definitions.json"
    with patch("sys.argv", ["script_name", "--input", test_input_file]):
        args = parse_extract_verification_arguments()
    assert args.input == test_input_file

    with patch(
        "sys.argv", ["script_name", "-i", "another_def.yaml"]
    ):  # Test avec l'alias court
        args_i = parse_extract_verification_arguments()
    assert args_i.input == "another_def.yaml"


def test_parse_extract_verification_arguments_hitler_only_true():
    """Teste la fourniture de l'argument --hitler-only."""
    with patch("sys.argv", ["script_name", "--hitler-only"]):
        args = parse_extract_verification_arguments()
    assert args.hitler_only is True
    # Pas d'alias court pour cet argument


def test_parse_extract_verification_arguments_all_provided():
    """Teste la fourniture de tous les arguments pour la vérification des extraits."""
    output_f = "final_verification.html"
    input_f = "specific_set.json"

    cli_args = [
        "script_name",
        "--output",
        output_f,
        "-v",  # verbose
        "-i",
        input_f,
        "--hitler-only",
    ]
    with patch("sys.argv", cli_args):
        args = parse_extract_verification_arguments()

    assert args.output == output_f
    assert args.verbose is True
    assert args.input == input_f
    assert args.hitler_only is True


# --- Tests for parse_extract_repair_arguments ---


def test_parse_extract_repair_arguments_defaults():
    """Teste les valeurs par défaut pour la réparation des extraits."""
    with patch("sys.argv", ["script_name"]):
        args = parse_extract_repair_arguments()
    assert args.output == "repair_report.html"
    assert args.save is False
    assert args.hitler_only is False
    assert args.verbose is False
    assert args.input is None
    assert args.output_json == "extract_sources_updated.json"


def test_parse_extract_repair_arguments_output_provided():
    """Teste la fourniture de l'argument --output."""
    test_file = "custom_repair.html"
    with patch("sys.argv", ["script_name", "--output", test_file]):
        args = parse_extract_repair_arguments()
    assert args.output == test_file

    with patch("sys.argv", ["script_name", "-o", "other_repair.xml"]):
        args_o = parse_extract_repair_arguments()
    assert args_o.output == "other_repair.xml"


def test_parse_extract_repair_arguments_save_true():
    """Teste la fourniture de l'argument --save."""
    with patch("sys.argv", ["script_name", "--save"]):
        args = parse_extract_repair_arguments()
    assert args.save is True
    with patch("sys.argv", ["script_name", "-s"]):
        args_s = parse_extract_repair_arguments()
    assert args_s.save is True


def test_parse_extract_repair_arguments_hitler_only_true():
    """Teste la fourniture de l'argument --hitler-only."""
    with patch("sys.argv", ["script_name", "--hitler-only"]):
        args = parse_extract_repair_arguments()
    assert args.hitler_only is True


def test_parse_extract_repair_arguments_verbose_true():
    """Teste la fourniture de l'argument --verbose."""
    with patch("sys.argv", ["script_name", "--verbose"]):
        args = parse_extract_repair_arguments()
    assert args.verbose is True
    with patch("sys.argv", ["script_name", "-v"]):
        args_v = parse_extract_repair_arguments()
    assert args_v.verbose is True


def test_parse_extract_repair_arguments_input_provided():
    """Teste la fourniture de l'argument --input."""
    test_input_file = "repair_defs.json"
    with patch("sys.argv", ["script_name", "--input", test_input_file]):
        args = parse_extract_repair_arguments()
    assert args.input == test_input_file
    with patch("sys.argv", ["script_name", "-i", "repair_another.yaml"]):
        args_i = parse_extract_repair_arguments()
    assert args_i.input == "repair_another.yaml"


def test_parse_extract_repair_arguments_output_json_provided():
    """Teste la fourniture de l'argument --output-json."""
    test_json_file = "my_repaired_extracts.json"
    with patch("sys.argv", ["script_name", "--output-json", test_json_file]):
        args = parse_extract_repair_arguments()
    assert args.output_json == test_json_file
    # Pas d'alias court pour cet argument


def test_parse_extract_repair_arguments_all_provided():
    """Teste la fourniture de tous les arguments pour la réparation des extraits."""
    output_f = "final_repair.html"
    input_f = "specific_repair_set.json"
    output_j = "repaired_data_final.json"

    cli_args = [
        "script_name",
        "--output",
        output_f,
        "-s",  # save
        "--hitler-only",
        "-v",  # verbose
        "-i",
        input_f,
        "--output-json",
        output_j,
    ]
    with patch("sys.argv", cli_args):
        args = parse_extract_repair_arguments()

    assert args.output == output_f
    assert args.save is True
    assert args.hitler_only is True
    assert args.verbose is True
    assert args.input == input_f
    assert args.output_json == output_j
