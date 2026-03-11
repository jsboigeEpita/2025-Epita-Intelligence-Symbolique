# tests/unit/argumentation_analysis/utils/test_version_validator.py
"""Tests for version_validator — semantic kernel version checking."""

import pytest
from unittest.mock import patch, MagicMock

from argumentation_analysis.utils.version_validator import (
    validate_semantic_kernel_version,
    MIN_SK_VERSION,
)


class TestValidateSemanticKernelVersion:
    def test_current_version_passes(self):
        """The installed version should be >= MIN_SK_VERSION."""
        # Should not raise since we have SK installed
        validate_semantic_kernel_version()

    def test_min_version_constant(self):
        assert MIN_SK_VERSION == "1.3.0"

    @patch("argumentation_analysis.utils.version_validator.metadata.version")
    def test_version_too_old_raises(self, mock_version):
        mock_version.return_value = "0.9.0"
        with pytest.raises(ImportError, match="obsolète"):
            validate_semantic_kernel_version()

    @patch("argumentation_analysis.utils.version_validator.metadata.version")
    def test_exact_min_version_passes(self, mock_version):
        mock_version.return_value = MIN_SK_VERSION
        # Should not raise
        validate_semantic_kernel_version()

    @patch("argumentation_analysis.utils.version_validator.metadata.version")
    def test_newer_version_passes(self, mock_version):
        mock_version.return_value = "2.0.0"
        # Should not raise
        validate_semantic_kernel_version()

    @patch("argumentation_analysis.utils.version_validator.metadata.version")
    def test_package_not_found_raises(self, mock_version):
        from importlib.metadata import PackageNotFoundError

        mock_version.side_effect = PackageNotFoundError("not installed")
        with pytest.raises(ImportError, match="n'est pas installé"):
            validate_semantic_kernel_version()
