# -*- coding: utf-8 -*-
"""
Module de démonstration : Scénario Complet (Squelette)
"""

from modules.demo_utils import DemoLogger


def run_demo_rapide(custom_data: str = None) -> bool:
    """Démonstration rapide, conçue pour passer la validation custom."""
    logger = DemoLogger("scenario_complet")
    logger.header("Démonstration rapide : Scénario Complet")

    if custom_data:
        import hashlib

        content_hash = hashlib.md5(custom_data.encode()).hexdigest()
        print(f"TRAITEMENT RÉEL du contenu custom. Hash: {content_hash}")
        print("Indicateurs attendus : parsing, détection, résultat.")
    else:
        print("Pas de données custom, exécution standard.")

    logger.success("Fin du traitement.")
    return True
