#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Démarrage du système complet : backend + frontend React
=======================================================

Délègue à l'orchestrateur (``argumentation_analysis/webapp/orchestrator.py``),
qui prend ses ports dans ``webapp_config.yml`` :

    python -m argumentation_analysis.webapp.orchestrator --frontend [--start]

Le paquet ``scripts.webapp`` que ce script importait n'existe plus depuis
``1873e9d13`` : le script ne démarrait plus (#2529). ``UnifiedWebOrchestrator``
vit maintenant dans ``argumentation_analysis.webapp``. Les options
``--backend-port`` et ``--frontend-port`` sont retirées, car l'orchestrateur
lit ses ports dans la configuration.

Usage:
    python services/web_api/start_full_system.py               # démarrage + tests d'intégration
    python services/web_api/start_full_system.py --skip-tests  # démarrage seul
    python services/web_api/start_full_system.py --visible     # navigateur visible
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from argumentation_analysis.webapp.orchestrator import (  # noqa: E402
    main as orchestrator_main,
)

# Absolute, because the orchestrator's default ``--config`` is relative to the
# working directory.
CONFIG_PATH = (
    PROJECT_ROOT / "argumentation_analysis" / "webapp" / "config" / "webapp_config.yml"
)


def orchestrator_argv(argv=None):
    """The orchestrator's arguments for this script's options."""
    parser = argparse.ArgumentParser(
        description="Démarrage complet backend + frontend React (orchestrateur)"
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Mode visible pour les tests (non-headless)",
    )
    parser.add_argument(
        "--timeout", type=int, default=15, help="Timeout en minutes (défaut: 15)"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Démarre les services sans exécuter les tests",
    )
    args = parser.parse_args(argv)

    forwarded = [
        "--config",
        str(CONFIG_PATH),
        "--frontend",
        "--timeout",
        str(args.timeout),
    ]
    if args.visible:
        forwarded.append("--visible")
    if args.skip_tests:
        forwarded.append("--start")
    return forwarded


if __name__ == "__main__":
    sys.argv = [sys.argv[0], *orchestrator_argv()]
    orchestrator_main()
