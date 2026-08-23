#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests non relocalisés de la couche services (web_api) — #1859.

Ces 8 tests RESTENT hors gate (emplacement jamais collecté) parce qu'ils
ne peuvent pas passer contre le code vivant, pour deux raisons mesurées :

- TestFrameworkService (4 tests) : l'interface testée (`is_healthy`,
  `build_framework`) n'existe plus. La surface vivante est
  `analyze_dung_framework` (framework_service.py:36), consommée par le
  serveur MCP. Réécrire ces tests contre la surface vivante est un
  authoring nouveau, décision séparée.
- test_validate_formal_argument_valid/invalid (2 tests) : la branche
  formelle de `validate_argument` est désactivée en production
  (validation_service.py:83-87 — la condition exige `request.logic_type`,
  champ que le modèle ne définit plus ; le commentaire du code documente
  la désactivation). Recalibrer ces tests sur le chemin heuristique
  dupliquerait test_validate_deductive_argument.

Les 24 autres tests (porteuses) tournent désormais dans le gate :
tests/unit/services/web_api/test_services.py.
"""

import pytest
from unittest.mock import Mock, patch

from argumentation_analysis.services.web_api.models.request_models import (
    ValidationRequest,
)


class TestValidationServiceFormalBranch:
    """Branche formelle désactivée — conservée pour la future décision."""

    @pytest.mark.asyncio
    async def test_validate_formal_argument_valid(self, validation_service):
        """Test de validation d'un argument formel valide via le LogicService mocké."""
        request = ValidationRequest(
            premises=["Si A alors B", "A"], conclusion="B", logic_type="propositional"
        )

        response = await validation_service.validate_argument(request)

        assert response.success is True
        assert response.result.is_valid is True
        assert response.result.validity_score == 1.0
        assert validation_service.logic_service.validate_argument_from_components.called

    @pytest.mark.asyncio
    async def test_validate_formal_argument_invalid(self, validation_service):
        """Test de validation d'un argument formel invalide via le LogicService mocké."""
        request = ValidationRequest(
            premises=["Si A alors B", "B"],
            conclusion="A",  # Fallacy: Affirming the consequent
            logic_type="propositional",
        )

        response = await validation_service.validate_argument(request)

        assert response.success is True
        assert response.result.is_valid is False
        assert response.result.validity_score == 0.0
        assert "L'argument n'est pas logiquement valide" in response.result.issues[0]
        assert validation_service.logic_service.validate_argument_from_components.called


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
