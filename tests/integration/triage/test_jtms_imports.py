#!/usr/bin/env python3
"""Script de test pour vérifier tous les imports de l'AXE B JTMS"""

import pytest


def test_axe_b_jtms_imports():
    """Vérifie tous les imports critiques de l'axe B (JTMS)."""
    errors = []

    try:
        from argumentation_analysis.services.jtms_service import JTMSService

        assert JTMSService is not None
    except ImportError as e:
        errors.append(f"Erreur import JTMSService: {e}")

    try:
        from argumentation_analysis.services.jtms_session_manager import (
            JTMSSessionManager,
        )

        assert JTMSSessionManager is not None
    except ImportError as e:
        errors.append(f"Erreur import JTMSSessionManager: {e}")

    try:
        from argumentation_analysis.plugins.semantic_kernel.jtms_plugin import (
            JTMSSemanticKernelPlugin,
        )

        assert JTMSSemanticKernelPlugin is not None
    except ImportError as e:
        errors.append(f"Erreur import JTMSSemanticKernelPlugin: {e}")

    try:
        from argumentation_analysis.api import jtms_models

        assert jtms_models is not None
    except ImportError as e:
        errors.append(f"Erreur import jtms_models: {e}")

    # integrations/semantic_kernel_integration (residual SK montage, 0 production
    # importer) was withdrawn in #2116 — the SK JTMS surface that production
    # actually mounts is already covered by the jtms_plugin block above.

    assert not errors, "Des erreurs d'import ont été trouvées:\\n" + "\\n".join(errors)
