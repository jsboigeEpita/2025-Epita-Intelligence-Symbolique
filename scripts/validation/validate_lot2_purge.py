#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VALIDATION FINALE LOT 2 - PURGE PHASE 3A
========================================
Validation complète de la purge des 5 fichiers du Lot 2
"""

import argumentation_analysis.core.environment
import os
import re
from pathlib import Path


def check_file_for_mocks(filepath):
    """Vérifie si un fichier contient des patterns de mock"""
    dangerous_mock_patterns = [
        r"from\s+unittest\.mock\s+import",
        r"import\s+unittest\.mock",
        r"@patch\(",
        r"@mock\.",
        r"Mock\(\)",
        r"MagicMock\(\)",
        r"AsyncMock\(\)",
        r"return_value\s*=",
        r"side_effect\s*=",
        r"\.assert_called",
        r"mock_.*\.",
        r"patch\(",
        r"Mock.*=",
        r"mock.*=",
    ]

    # Patterns safe: commentaires anti-simulation
    safe_patterns = [
        r"pas un mock",
        r"aucun mock",
        r"NO MOCKS",
        r"TOUS MOCKS ÉLIMINÉS",
        r"100% AUTHENTIQUES",
        r"PURGE",
    ]

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Vérifier s'il y a des commentaires anti-simulation
        has_anti_simulation = any(
            re.search(pattern, content, re.IGNORECASE) for pattern in safe_patterns
        )

        infected_patterns = []
        for pattern in dangerous_mock_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            if matches:
                infected_patterns.append(pattern)

        # Si le fichier a des commentaires anti-simulation et pas de vrais patterns dangereux
        if has_anti_simulation and len(infected_patterns) == 0:
            return True, []

        # Vérifier seulement les patterns vraiment dangereux (pas dans commentaires)
        lines = content.split("\n")
        real_infected = []
        for pattern in dangerous_mock_patterns:
            for line_num, line in enumerate(lines, 1):
                # Ignorer les lignes de commentaires
                if (
                    line.strip().startswith("#")
                    or line.strip().startswith('"""')
                    or line.strip().startswith("'''")
                ):
                    continue

                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    real_infected.append(f"{pattern} (line {line_num})")

        return len(real_infected) == 0, real_infected

    except Exception as e:
        return False, [f"Error reading file: {e}"]


def main():
    print("VALIDATION FINALE LOT 2 - PURGE PHASE 3A")
    print("=" * 50)

    files_lot2 = [
        "tests/orchestration/tactical/test_tactical_coordinator_advanced.py",
        "tests/orchestration/tactical/test_tactical_coordinator_coverage.py",
        "tests/finaux/validation_complete_sans_mocks.py",
        "tests/integration/test_cluedo_oracle_integration.py",
        "tests/integration/test_cluedo_orchestration_integration.py",
    ]

    all_clean = True
    total_files = len(files_lot2)
    clean_files = 0

    for i, filepath in enumerate(files_lot2, 1):
        if os.path.exists(filepath):
            is_clean, patterns = check_file_for_mocks(filepath)
            status = "PURGE" if is_clean else "INFECTE"
            print(f"{i}. {filepath}")
            print(f"   Status: {status}")

            if is_clean:
                clean_files += 1
            else:
                all_clean = False
                print(
                    f"   Patterns détectés: {patterns[:3]}..."
                )  # Show first 3 patterns
            print()
        else:
            print(f"{i}. {filepath}")
            print(f"   Status: FICHIER INTROUVABLE")
            all_clean = False
            print()

    print("=" * 50)
    print(f"RESULTAT FINAL LOT 2:")
    print(f"   Fichiers traités: {clean_files}/{total_files}")
    print(f"   Taux de purge: {(clean_files/total_files)*100:.1f}%")

    if all_clean:
        print("SUCCES! TOUS LES FICHIERS DU LOT 2 SONT 100% PURGES!")
        print("   + Aucun mock detecte")
        print("   + Transformation authentique complete")
        print("   + PHASE 3A LOT 2 TERMINEE")
    else:
        print("ATTENTION: PURGE INCOMPLETE - Actions requises")

    print("=" * 50)


if __name__ == "__main__":
    main()
