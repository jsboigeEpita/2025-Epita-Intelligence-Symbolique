# -*- coding: utf-8 -*-
# tests/integration/test_sherlock_watson_moriarty_real_gpt.py
"""
Lanceur pour les tests d'intégration de Sherlock/Watson/Moriarty avec GPT-4o-mini réel.
Exécute les tests dans un sous-processus pour isoler la JVM.
"""

import pytest
from pathlib import Path
import os

# Importer la fixture depuis son emplacement partagé
from tests.fixtures.jvm_subprocess_fixture import run_in_jvm_subprocess

# Le chemin vers le script worker qui contient les vrais tests.
WORKER_SCRIPT_PATH = Path(__file__).parent / "workers" / "worker_sherlock_watson_moriarty.py"

# Configuration pour tests réels GPT-4o-mini
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
REAL_GPT_AVAILABLE = OPENAI_API_KEY is not None and len(OPENAI_API_KEY) > 10

# Skip si pas d'API key
pytestmark = pytest.mark.skipif(
    not REAL_GPT_AVAILABLE,
    reason="Tests réels GPT-4o-mini nécessitent OPENAI_API_KEY"
)

@pytest.mark.integration
def test_sherlock_watson_moriarty_real_gpt_in_subprocess(run_in_jvm_subprocess):
    """
    Exécute l'ensemble des tests d'intégration de Sherlock/Watson/Moriarty
    dans un sous-processus isolé pour éviter les conflits JVM.
    """
    assert WORKER_SCRIPT_PATH.exists(), f"Le script worker n'a pas été trouvé à {WORKER_SCRIPT_PATH}"
    
    # La fixture 'run_in_jvm_subprocess' exécute le script worker.
    run_in_jvm_subprocess(WORKER_SCRIPT_PATH)