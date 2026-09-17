"""Guards for #2282 — environment manifest must be probed and honest."""
import os
import pytest
from pathlib import Path
from unittest.mock import patch


class TestEnvironmentManifest:
    """The manifest must measure the real environment, never assume it."""

    def test_manifest_structure(self):
        """Manifest must have jvm, llm_endpoints, torch, and overrides axes."""
        from argumentation_analysis.evaluation.env_manifest import environment_manifest

        manifest = environment_manifest()
        assert "jvm" in manifest
        assert "llm_endpoints" in manifest
        assert "torch" in manifest
        assert "overrides" in manifest

    def test_jvm_probe_reports_jar_count(self):
        """JVM probe must report the real jar count, not assume."""
        from argumentation_analysis.evaluation.env_manifest import _probe_jvm

        result = _probe_jvm()
        assert "jar_count_in_libs_tweety" in result
        assert "jars_resolvable" in result
        assert "tweety_version_target" in result
        # In the main repo, libs/tweety/ has 76 jars — the probe must see them
        libs_dir = Path("libs/tweety")
        if libs_dir.exists():
            expected = len(list(libs_dir.glob("*.jar")))
            assert result["jar_count_in_libs_tweety"] == expected
            if expected > 0:
                assert result["jars_resolvable"] is True

    def test_jvm_probe_detects_missing_jars(self, tmp_path):
        """With an empty libs/tweety and no Maven, jars_resolvable must be False."""
        from argumentation_analysis.evaluation.env_manifest import _probe_jvm

        empty_dir = tmp_path / "empty_tweety"
        empty_dir.mkdir()
        with patch(
            "argumentation_analysis.evaluation.env_manifest.settings"
        ) as mock_settings:
            mock_settings.jvm.tweety_libs_dir = empty_dir
            mock_settings.jvm.tweety_version = "1.31"
            with patch(
                "argumentation_analysis.evaluation.env_manifest.shutil.which",
                return_value=None,
            ):
                result = _probe_jvm()
        assert result["jar_count_in_libs_tweety"] == 0
        assert result["jars_resolvable"] is False
        assert "provisioning impossible" in result["jars_note"]

    def test_jvm_probe_detects_maven_fallback(self, tmp_path):
        """With no jars but Maven available, jars_resolvable must be True."""
        from argumentation_analysis.evaluation.env_manifest import _probe_jvm

        empty_dir = tmp_path / "empty_tweety"
        empty_dir.mkdir()
        with patch(
            "argumentation_analysis.evaluation.env_manifest.settings"
        ) as mock_settings:
            mock_settings.jvm.tweety_libs_dir = empty_dir
            mock_settings.jvm.tweety_version = "1.31"
            with patch(
                "argumentation_analysis.evaluation.env_manifest.shutil.which",
                return_value="/usr/bin/mvn",
            ):
                result = _probe_jvm()
        assert result["jars_resolvable"] is True
        assert result["maven_available"] is True

    def test_llm_probe_reports_configured_endpoints(self):
        """LLM probe must report which endpoints are configured."""
        from argumentation_analysis.evaluation.env_manifest import _probe_llm_endpoints

        env = {
            "OPENAI_API_KEY": "test-key",
            "OPENROUTER_API_KEY": "test-or-key",
            "OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1",
            "SELF_HOSTED_LLM_API_KEY": "",
            "SELF_HOSTED_LLM_ENDPOINT": "",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _probe_llm_endpoints()
        assert result["openai_configured"] is True
        assert result["openrouter_configured"] is True
        assert result["openrouter_base_url"] == "https://openrouter.ai/api/v1"
        # Empty strings → not configured (empty ≠ present, #2281)
        assert result["self_hosted_configured"] is False

    def test_overrides_probe_surfaces_pins(self):
        """Pinned overrides must be loud — visible in the manifest."""
        from argumentation_analysis.evaluation.env_manifest import _probe_overrides

        env = {
            "JVM_TWEETY_VERSION": "1.28",
            "OPENAI_CHAT_MODEL_ID": "gpt-5.6-luna",
        }
        with patch.dict(os.environ, env, clear=True):
            result = _probe_overrides()
        assert result["pinned_overrides"]["JVM_TWEETY_VERSION"] == "1.28"
        assert result["pinned_overrides"]["OPENAI_CHAT_MODEL_ID"] == "gpt-5.6-luna"


class TestProvenanceBlockWithManifest:
    """The provenance block must carry the environment manifest."""

    def test_provenance_includes_environment(self):
        """provenance_block() must stamp the environment manifest."""
        from argumentation_analysis.evaluation.run_provenance import provenance_block

        block = provenance_block()
        assert "environment" in block
        env = block["environment"]
        assert "jvm" in env
        assert "llm_endpoints" in env
        assert "torch" in env
        assert "overrides" in env

    def test_provenance_environment_is_probed(self):
        """The environment in provenance must be probed, not mocked."""
        from argumentation_analysis.evaluation.run_provenance import provenance_block

        block = provenance_block()
        jvm = block["environment"]["jvm"]
        # Real probe: jar_count must be a real integer, not a placeholder
        assert isinstance(jvm["jar_count_in_libs_tweety"], int)
        assert jvm["jar_count_in_libs_tweety"] >= 0
        assert isinstance(jvm["jars_resolvable"], bool)
