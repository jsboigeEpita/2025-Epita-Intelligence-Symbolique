#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests non relocalisés de la couche services (web_api) — #1859.

Ces 6 tests RESTENT hors gate (emplacement jamais collecté). Mesuré #2536 :
4 passent, 2 échouent.

- Les 2 tests `build_framework` échouent : cette interface n'existe plus. La
  surface vivante est `analyze_dung_framework`, consommée par le serveur MCP.
  Réécrire ces tests contre la surface vivante est un authoring nouveau,
  décision séparée.
- Les 4 autres passent et sont tenus dans le gate : `is_healthy` (rétabli
  par #1864) par tests/unit/argumentation_analysis/services/test_mcp_server.py,
  la validation des modèles par TestFrameworkRequestModel dans
  tests/unit/argumentation_analysis/services/test_web_api_models_and_services.py.

(Les 2 tests fossiles de la branche formelle de `validate_argument` ont été
supprimés avec la branche elle-même — #2097-5 : la condition testait
`request.logic_type`, un champ que ValidationRequest n'a jamais défini,
donc la branche ne s'exécutait jamais. Les tests porteuses tournent dans
le gate : tests/unit/services/web_api/test_services.py.)
"""

import pytest

# #2536: #1863 moved this import to the relocated suite with the tests that
# left, but the four tests below still build these models.
from argumentation_analysis.services.web_api.models.request_models import (
    Argument,
    FrameworkOptions,
    FrameworkRequest,
)


class TestFrameworkService:
    """Tests pour le service de framework."""

    @pytest.fixture
    def framework_service(self):
        """Instance du service de framework."""
        from argumentation_analysis.services.web_api.services.framework_service import (
            FrameworkService,
        )

        return FrameworkService()

    def test_service_initialization(self, framework_service):
        """Test de l'initialisation du service."""
        assert framework_service is not None
        assert hasattr(framework_service, "is_healthy")

    def test_is_healthy(self, framework_service):
        """Test de la vérification de santé."""
        health_status = framework_service.is_healthy()
        assert isinstance(health_status, bool)

    def test_build_simple_framework(self, framework_service):
        """Test de construction d'un framework simple."""
        arguments = [
            Argument(id="arg1", content="Argument 1"),
            Argument(id="arg2", content="Argument 2", attacks=["arg1"]),
        ]
        request = FrameworkRequest(arguments=arguments)

        response = framework_service.build_framework(request)

        assert response is not None
        assert hasattr(response, "success")
        assert hasattr(response, "arguments")
        assert hasattr(response, "extensions")
        assert response.argument_count == len(arguments)

    def test_build_framework_with_options(self, framework_service):
        """Test de construction avec options."""
        arguments = [Argument(id="arg1", content="Argument 1")]
        options = FrameworkOptions(
            compute_extensions=True, semantics="preferred", include_visualization=True
        )
        request = FrameworkRequest(arguments=arguments, options=options)

        response = framework_service.build_framework(request)

        assert response is not None
        assert response.framework_options == options.dict()
        assert response.semantics_used == "preferred"

    def test_framework_argument_validation(self):
        """Test de validation des arguments du framework."""
        with pytest.raises(ValueError):
            arguments = [
                Argument(id="arg1", content="Argument 1"),
                Argument(id="arg1", content="Argument 2"),
            ]
            FrameworkRequest(arguments=arguments)

        with pytest.raises(ValueError):
            arguments = [
                Argument(id="arg1", content="Argument 1", attacks=["nonexistent"])
            ]
            FrameworkRequest(arguments=arguments)

    def test_framework_options_validation(self):
        """Test de validation des options du framework."""
        with pytest.raises(ValueError):
            FrameworkOptions(semantics="invalid_semantics")

        with pytest.raises(ValueError):
            FrameworkOptions(max_arguments=0)

        with pytest.raises(ValueError):
            FrameworkOptions(max_arguments=2000)
