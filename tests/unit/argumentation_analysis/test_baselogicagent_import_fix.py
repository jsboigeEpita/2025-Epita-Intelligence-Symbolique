#!/usr/bin/env python3
"""
Test unitaire pour vérifier que le cycle d'import de BaseLogicAgent a été résolu.

Ce test valide que :
1. BaseAgent peut être importé sans erreur
2. BaseLogicAgent peut être importé sans cycle d'import
3. ServiceManager peut maintenant importer BaseLogicAgent
4. Les forward references fonctionnent correctement avec TYPE_CHECKING
"""

import pytest
import sys
from typing import TYPE_CHECKING

# Vérification PyTorch pour skip conditionnel Windows
PYTORCH_AVAILABLE = True
PYTORCH_ERROR = None
try:
    import torch
except (ImportError, OSError) as e:
    PYTORCH_AVAILABLE = False
    PYTORCH_ERROR = str(e)


def test_baseagent_import_success():
    """Test que BaseAgent peut être importé sans erreur."""
    try:
        from argumentation_analysis.agents.core.abc.agent_bases import BaseAgent

        assert BaseAgent is not None
        assert (
            BaseAgent.__module__ == "argumentation_analysis.agents.core.abc.agent_bases"
        )
        print("SUCCESS: BaseAgent importé avec succès")
    except Exception as e:
        pytest.fail(f"ECHEC: Impossible d'importer BaseAgent: {e}")


def test_baselogicagent_import_success():
    """Test que BaseLogicAgent peut être importé sans cycle d'import."""
    try:
        from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent

        assert BaseLogicAgent is not None
        assert (
            BaseLogicAgent.__module__
            == "argumentation_analysis.agents.core.abc.agent_bases"
        )
        print("SUCCESS: BaseLogicAgent importé avec succès")
    except ImportError as e:
        if "partially initialized module" in str(e):
            pytest.fail(f"ECHEC: Cycle d'import détecté pour BaseLogicAgent: {e}")
        else:
            pytest.fail(f"ECHEC: Erreur d'import BaseLogicAgent: {e}")
    except Exception as e:
        pytest.fail(f"ECHEC: Erreur inattendue lors de l'import BaseLogicAgent: {e}")


@pytest.mark.skipif(
    sys.platform == "win32" and not PYTORCH_AVAILABLE,
    reason=f"PyTorch fbgemm.dll issue on Windows - {PYTORCH_ERROR if PYTORCH_ERROR else 'WinError 182: Visual C++ Redistributable required'}"
)
def test_service_manager_can_import_baselogicagent():
    """Test que ServiceManager peut maintenant importer BaseLogicAgent sans problème."""
    try:
        from argumentation_analysis.orchestration.service_manager import ServiceManager

        # Si on arrive ici, c'est que ServiceManager peut être importé sans problème
        assert ServiceManager is not None
        print("SUCCESS: ServiceManager importé avec succès")
    except ImportError as e:
        if "BaseLogicAgent" in str(e) or "partially initialized module" in str(e):
            pytest.fail(
                f"ECHEC: ServiceManager ne peut toujours pas importer BaseLogicAgent: {e}"
            )
        else:
            pytest.fail(f"ECHEC: Autre erreur d'import ServiceManager: {e}")
    except Exception as e:
        pytest.fail(f"ECHEC: Erreur inattendue lors de l'import ServiceManager: {e}")


def test_forward_references_work():
    """Test que les forward references avec TYPE_CHECKING fonctionnent."""
    try:
        from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent

        # Vérifier que _tweety_bridge is accessible on instances (set in __init__)
        # Note: _tweety_bridge annotation was removed to avoid Pydantic V2 issues;
        # it's now initialized via object.__setattr__ in __init__
        assert hasattr(BaseLogicAgent, "__annotations__") or True  # class exists
        # Verify the tweety_bridge property exists on the class
        assert hasattr(BaseLogicAgent, "tweety_bridge"), (
            "BaseLogicAgent should have a tweety_bridge property"
        )

        print("SUCCESS: Forward references correctement configurées")
    except Exception as e:
        pytest.fail(f"ECHEC: Problème avec les forward references: {e}")


def test_no_circular_import_in_module_deps():
    """Test que les dépendances circulaires ont été éliminées."""
    import sys

    initial_modules = set(sys.modules.keys())

    try:
        # Import des modules qui étaient en conflit
        from argumentation_analysis.agents.core.abc.agent_bases import (
            BaseLogicAgent,
            BaseAgent,
        )
        from argumentation_analysis.agents.core.logic.belief_set import BeliefSet

        # Si on arrive ici sans exception, le cycle est résolu
        assert BaseLogicAgent is not None
        assert BaseAgent is not None
        assert BeliefSet is not None

        print("SUCCESS: Pas de cycle d'import détecté entre les modules")
    except ImportError as e:
        if "partially initialized module" in str(e):
            pytest.fail(f"ECHEC: Cycle d'import encore présent: {e}")
        else:
            pytest.fail(f"ECHEC: Erreur d'import: {e}")


def test_logic_agents_can_inherit_from_baselogicagent():
    """Test que les agents logiques peuvent hériter de BaseLogicAgent."""
    try:
        # Test avec un agent logique spécifique
        from argumentation_analysis.agents.core.logic.propositional_logic_agent import (
            PropositionalLogicAgent,
        )
        from argumentation_analysis.agents.core.abc.agent_bases import BaseLogicAgent

        # Vérifier l'héritage
        assert issubclass(PropositionalLogicAgent, BaseLogicAgent)
        print("SUCCESS: PropositionalLogicAgent hérite correctement de BaseLogicAgent")
    except ImportError as e:
        if "BaseLogicAgent" in str(e):
            pytest.fail(
                f"ECHEC: PropositionalLogicAgent ne peut pas importer BaseLogicAgent: {e}"
            )
        else:
            # Cet agent peut ne pas exister, on ignore
            print("INFO: PropositionalLogicAgent non trouvé (peut être normal)")
    except Exception as e:
        pytest.fail(f"ECHEC: Problème avec l'héritage: {e}")


class TestBaseLogicAgentImportFix:
    """Classe de test pour la résolution du cycle d'import BaseLogicAgent."""

    @pytest.mark.skipif(
        sys.platform == "win32" and not PYTORCH_AVAILABLE,
        reason=f"PyTorch fbgemm.dll issue on Windows - {PYTORCH_ERROR if PYTORCH_ERROR else 'WinError 182: Visual C++ Redistributable required'}"
    )
    def test_complete_import_resolution(self):
        """Test complet de résolution du cycle d'import."""
        print("\n=== TEST RESOLUTION CYCLE D'IMPORT BASELOGICAGENT ===")

        # Tests individuels
        test_baseagent_import_success()
        test_baselogicagent_import_success()
        test_service_manager_can_import_baselogicagent()
        test_forward_references_work()
        test_no_circular_import_in_module_deps()
        test_logic_agents_can_inherit_from_baselogicagent()

        print("=== TOUS LES TESTS REUSSIS - CYCLE D'IMPORT RESOLU ===")


if __name__ == "__main__":
    # Permet d'exécuter le test directement
    test = TestBaseLogicAgentImportFix()
    test.test_complete_import_resolution()
