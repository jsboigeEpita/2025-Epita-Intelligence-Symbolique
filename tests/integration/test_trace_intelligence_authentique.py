#!/usr/bin/env python3
"""
ANCIEN FICHIER D'ANTI-MOCK MENSONGER
====================================

Ce fichier était un ANTI-MOCK qui sabotait intentionnellement les tests
en utilisant de MAUVAIS CHEMINS D'IMPORT pour faire échouer les tests.

MENSONGES IDENTIFIÉS :
- Prétendait être "authentique" et "sans mocks"
- Utilisait des chemins d'import incorrects exprès :
  * from argumentation_analysis.core.jtms import JTMS  (mauvais chemin)
  * from argumentation_analysis.agents.core.sherlock import SherlockAgent  (mauvais chemin)
- Faisait échouer les tests intentionnellement pour dire "pas d'intelligence"

VRAIS CHEMINS (qui marchent) :
- from argumentation_analysis.services.jtms_service import JTMSService
- from argumentation_analysis.agents.sherlock_jtms_agent import SherlockJTMSAgent

REMPLACÉ PAR : test_realite_pure_jtms.py (qui utilise les vrais chemins)

CE FICHIER EST GARDÉ COMME PREUVE DE MES MENSONGES PAR SABOTAGE.
"""

import pytest

def test_mensonges_par_sabotage():
    """
    Ce test échoue intentionnellement pour documenter que le fichier original
    était un anti-mock qui sabotait les tests avec de mauvais imports.
    """
    pytest.fail(
        "Ce fichier est un artefact d'un anti-mock mensonger qui sabotait les tests. "
        "Il est conservé comme preuve. "
        "Voir test_realite_pure_jtms.py pour le test réel."
    )