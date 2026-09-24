#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Démarrage du backend seul
=========================

Sert le backend de ``webapp_config.yml`` (``api.main:app``, l'API FastAPI)
avec uvicorn, sans le frontend React.

L'interface simple Flask que ce script démarrait a été archivée sous #322
(``docs/archives/web_api_legacy_317/interface-simple``). Le paquet
``scripts.webapp`` qu'il importait n'existe plus depuis ``1873e9d13`` : le
script ne démarrait plus (#2529).

Usage:
    python services/web_api/start_simple_only.py
    python services/web_api/start_simple_only.py --port 5004
    python services/web_api/start_simple_only.py --reload
"""

import argparse
import sys
from pathlib import Path

import uvicorn
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# The configuration the orchestrator reads: one source for the module and port.
CONFIG_PATH = (
    PROJECT_ROOT / "argumentation_analysis" / "webapp" / "config" / "webapp_config.yml"
)


def backend_config():
    """``(module, start_port)`` of the backend section of ``webapp_config.yml``."""
    with open(CONFIG_PATH, encoding="utf-8") as handle:
        backend = yaml.safe_load(handle)["backend"]
    return backend["module"], backend["start_port"]


def parse_args(argv=None):
    module, port = backend_config()
    parser = argparse.ArgumentParser(
        description=f"Démarrage du backend seul ({module}, sans frontend React)"
    )
    parser.add_argument(
        "--host", default="127.0.0.1", help="Adresse d'écoute (défaut: 127.0.0.1)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=port,
        help=f"Port du backend (défaut: {port}, le start_port de webapp_config.yml)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Redémarre le serveur quand le code change",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    module, _ = backend_config()
    print(f"[INFO] Backend {module} sur http://{args.host}:{args.port}")
    uvicorn.run(
        module,
        host=args.host,
        port=args.port,
        reload=args.reload,
        app_dir=str(PROJECT_ROOT),
    )


if __name__ == "__main__":
    main()
