#!/usr/bin/env python3
"""
Script Monitoring Budget API Tests LLM Réels - Mission D3.2
Affiche estimation coûts tokens temps réel pendant exécution pytest

Usage:
    python -m pytest tests/ -m "llm_light" -v | python scripts/monitoring/monitor_llm_tests_budget.py

Note: Estimations basées sur moyennes observées par marker.
Pour monitoring réel tokens, intégration OpenAI API callbacks requise.
"""

import sys
import re
from datetime import datetime
from typing import Dict, Tuple


class LLMTestBudgetMonitor:
    """Monitore et estime les coûts des tests LLM en temps réel"""

    # Estimations coûts par marker (tokens, cost_usd)
    COST_ESTIMATES = {
        "llm_light": (50, 0.01),  # Tests légers
        "llm_integration": (500, 0.10),  # Tests intégration
        "llm_critical": (1500, 0.25),  # Tests critiques
    }

    def __init__(self):
        self.total_cost = 0.0
        self.total_tokens = 0
        self.tests_passed = 0
        self.tests_failed = 0
        self.start_time = datetime.now()

    def estimate_cost_tokens(self, test_name: str, marker: str) -> Tuple[int, float]:
        """Estime coût et tokens pour un test donné"""
        return self.COST_ESTIMATES.get(marker, (100, 0.05))

    def detect_marker(self, line: str) -> str:
        """Détecte marker du test depuis ligne pytest"""
        # Priorité ordre décroissant complexité
        if "llm_critical" in line or "[llm_critical]" in line:
            return "llm_critical"
        elif "llm_integration" in line or "[llm_integration]" in line:
            return "llm_integration"
        elif "llm_light" in line or "[llm_light]" in line:
            return "llm_light"

        # Détection via chemin fichier (fallback)
        if "test_" in line:
            # Heuristique: tests critiques contiennent "complex", "advanced"
            if any(kw in line.lower() for kw in ["complex", "advanced", "critical"]):
                return "llm_critical"
            # Tests légers contiennent "simple", "basic", "quick"
            elif any(
                kw in line.lower() for kw in ["simple", "basic", "quick", "light"]
            ):
                return "llm_light"

        return "llm_integration"  # Par défaut

    def parse_test_result(self, line: str) -> Dict:
        """Parse ligne résultat test pytest"""
        result = {
            "is_test": False,
            "passed": False,
            "failed": False,
            "test_name": None,
            "marker": None,
        }

        # Détection format: tests/path/test_file.py::test_name PASSED
        test_match = re.search(r"(tests/.+?\.py)::(test_\w+)\s+(PASSED|FAILED)", line)
        if test_match:
            result["is_test"] = True
            result["test_name"] = f"{test_match.group(1)}::{test_match.group(2)}"
            result["passed"] = test_match.group(3) == "PASSED"
            result["failed"] = test_match.group(3) == "FAILED"
            result["marker"] = self.detect_marker(line)

        return result

    def update_stats(self, test_info: Dict):
        """Met à jour statistiques monitoring"""
        if not test_info["is_test"]:
            return

        marker = test_info["marker"]
        tokens, cost = self.estimate_cost_tokens(test_info["test_name"], marker)

        self.total_tokens += tokens
        self.total_cost += cost

        if test_info["passed"]:
            self.tests_passed += 1
        elif test_info["failed"]:
            self.tests_failed += 1

    def format_budget_line(self, test_info: Dict) -> str:
        """Formate ligne affichage budget après test"""
        if not test_info["is_test"]:
            return ""

        marker = test_info["marker"]
        tokens, cost = self.estimate_cost_tokens(test_info["test_name"], marker)

        status_icon = "✅" if test_info["passed"] else "❌"

        return (
            f"  💰 {status_icon} Budget: +${cost:.3f} "
            f"(total: ${self.total_cost:.2f}, ~{self.total_tokens} tokens) "
            f"[{marker}]"
        )

    def format_summary(self) -> str:
        """Formate synthèse finale monitoring"""
        duration = (datetime.now() - self.start_time).total_seconds()
        total_tests = self.tests_passed + self.tests_failed

        summary = [
            "",
            "=" * 70,
            "📊 SYNTHESE MONITORING BUDGET LLM - Mission D3.2",
            "=" * 70,
            f"⏱️  Durée exécution       : {duration:.1f}s ({duration/60:.1f}min)",
            f"📝 Tests exécutés        : {total_tests}",
            f"✅ Tests PASSED          : {self.tests_passed}",
            f"❌ Tests FAILED          : {self.tests_failed}",
            "",
            f"💰 Budget Total Estimé   : ${self.total_cost:.2f} USD",
            f"🔢 Tokens Estimés        : ~{self.total_tokens} tokens",
            "",
        ]

        # Alertes budget
        if self.total_cost > 15.0:
            summary.append("⚠️  ALERTE: Budget dépassement seuil $15 USD !")
        elif self.total_cost > 10.0:
            summary.append("⚡ INFO: Budget approche seuil estimé ($10-15 USD)")

        # Taux succès
        if total_tests > 0:
            success_rate = (self.tests_passed / total_tests) * 100
            summary.append(f"📈 Taux succès           : {success_rate:.1f}%")

            if success_rate >= 80:
                summary.append("✅ Objectif atteint (≥80% succès)")
            elif success_rate >= 50:
                summary.append("⚠️  Succès partiel (50-79% succès)")
            else:
                summary.append("❌ Échec (<50% succès)")

        summary.extend(
            [
                "",
                "=" * 70,
                "ℹ️  Note: Estimations basées sur moyennes markers observées.",
                "   Pour coûts réels, consulter dashboard OpenAI après exécution.",
                "=" * 70,
                "",
            ]
        )

        return "\n".join(summary)

    def monitor_pytest_output(self):
        """Parse sortie pytest stdin et affiche monitoring temps réel"""
        print("=" * 70)
        print("🔍 Monitoring Budget Tests LLM D3.2 - Démarré")
        print("=" * 70)
        print("")

        for line in sys.stdin:
            # Afficher sortie pytest normale
            print(line, end="")

            # Parser résultat test
            test_info = self.parse_test_result(line)

            # Mettre à jour stats et afficher budget si test détecté
            if test_info["is_test"]:
                self.update_stats(test_info)
                budget_line = self.format_budget_line(test_info)
                if budget_line:
                    print(budget_line)

        # Afficher synthèse finale
        print(self.format_summary())


def main():
    """Point d'entrée script"""
    monitor = LLMTestBudgetMonitor()

    try:
        monitor.monitor_pytest_output()
    except KeyboardInterrupt:
        print("\n\n⚠️  Monitoring interrompu par utilisateur (Ctrl+C)")
        print(monitor.format_summary())
    except Exception as e:
        print(f"\n\n❌ Erreur monitoring: {e}")
        print(monitor.format_summary())


if __name__ == "__main__":
    main()
