# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.config.settings
Covers all Pydantic settings classes: defaults, types, computed fields, nesting.
"""

import pytest
from pathlib import Path
from pydantic import SecretStr, HttpUrl


from argumentation_analysis.config.settings import (
    OpenAISettings,
    AzureOpenAISettings,
    TikaSettings,
    JinaSettings,
    NetworkSettings,
    UISettings,
    ServiceManagerSettings,
    JVMSettings,
    AppSettings,
    settings,
)

# ============================================================
# Module-level singleton
# ============================================================


class TestModuleSingleton:
    def test_settings_is_app_settings_instance(self):
        assert isinstance(settings, AppSettings)

    def test_settings_has_openai_child(self):
        assert hasattr(settings, "openai")
        assert isinstance(settings.openai, OpenAISettings)

    def test_settings_has_tika_child(self):
        assert isinstance(settings.tika, TikaSettings)

    def test_settings_has_network_child(self):
        assert isinstance(settings.network, NetworkSettings)


# ============================================================
# OpenAISettings
# ============================================================


class TestOpenAISettings:
    def test_default_chat_model(self):
        s = OpenAISettings()
        # May be overridden by env, but should be a string
        assert isinstance(s.chat_model_id, str)

    def test_api_key_type(self):
        s = OpenAISettings()
        # api_key is always present (either from .env or default dummy)
        assert s.api_key is not None
        assert isinstance(s.api_key, SecretStr)

    def test_api_key_get_secret_value(self):
        s = OpenAISettings()
        val = s.api_key.get_secret_value()
        assert isinstance(val, str)
        assert len(val) > 0

    def test_base_url_optional(self):
        s = OpenAISettings()
        assert s.base_url is None or isinstance(s.base_url, HttpUrl)


# ============================================================
# AzureOpenAISettings
# ============================================================


class TestAzureOpenAISettings:
    def test_api_key_optional(self):
        s = AzureOpenAISettings()
        # May be None or set from env
        assert s.api_key is None or isinstance(s.api_key, SecretStr)

    def test_endpoint_optional(self):
        s = AzureOpenAISettings()
        assert s.endpoint is None or isinstance(s.endpoint, HttpUrl)

    def test_deployment_name_optional(self):
        s = AzureOpenAISettings()
        assert s.deployment_name is None or isinstance(s.deployment_name, str)

    def test_chat_model_id_is_string(self):
        s = AzureOpenAISettings()
        assert isinstance(s.chat_model_id, str)


# ============================================================
# TikaSettings
# ============================================================


class TestTikaSettings:
    def test_timeout_is_int(self):
        s = TikaSettings()
        assert isinstance(s.server_timeout, int)
        assert s.server_timeout > 0

    def test_server_endpoint_is_url(self):
        s = TikaSettings()
        # Should be a valid URL containing 'tika'
        endpoint_str = str(s.server_endpoint)
        assert "tika" in endpoint_str or "http" in endpoint_str


# ============================================================
# JinaSettings
# ============================================================


class TestJinaSettings:
    def test_reader_prefix_default(self):
        s = JinaSettings()
        assert "jina.ai" in str(s.reader_prefix)


# ============================================================
# NetworkSettings
# ============================================================


class TestNetworkSettings:
    def test_breaker_defaults(self):
        s = NetworkSettings()
        assert s.breaker_fail_max == 5
        assert s.breaker_reset_timeout == 60

    def test_retry_defaults(self):
        s = NetworkSettings()
        assert s.retry_stop_after_attempt == 3
        assert s.retry_wait_multiplier == 1
        assert s.retry_wait_min == 2
        assert s.retry_wait_max == 10

    def test_default_timeout(self):
        s = NetworkSettings()
        assert s.default_timeout == 90.0


# ============================================================
# UISettings
# ============================================================


class TestUISettings:
    def test_temp_download_dir_default(self):
        s = UISettings()
        assert s.temp_download_dir == Path("temp_downloads")

    def test_plaintext_extensions_is_list(self):
        s = UISettings()
        assert isinstance(s.plaintext_extensions, list)
        assert ".txt" in s.plaintext_extensions
        assert ".md" in s.plaintext_extensions

    def test_plaintext_extensions_has_common_types(self):
        s = UISettings()
        for ext in [".txt", ".json", ".xml", ".html"]:
            assert ext in s.plaintext_extensions


# ============================================================
# ServiceManagerSettings
# ============================================================


class TestServiceManagerSettings:
    def test_defaults(self):
        s = ServiceManagerSettings()
        assert s.enable_hierarchical is True
        assert s.enable_specialized_orchestrators is True
        assert s.enable_communication_middleware is True

    def test_concurrency_defaults(self):
        s = ServiceManagerSettings()
        assert s.max_concurrent_analyses == 10
        assert s.analysis_timeout == 300

    def test_auto_cleanup_default(self):
        s = ServiceManagerSettings()
        assert s.auto_cleanup is True

    def test_save_results_default(self):
        s = ServiceManagerSettings()
        assert s.save_results is True

    def test_results_dir_is_path(self):
        s = ServiceManagerSettings()
        assert isinstance(s.results_dir, Path)

    def test_default_llm_service_id(self):
        s = ServiceManagerSettings()
        assert s.default_llm_service_id == "openai"

    def test_default_model_id(self):
        s = ServiceManagerSettings()
        assert s.default_model_id == "gpt-5-mini"


# ============================================================
# JVMSettings
# ============================================================


class TestJVMSettings:
    def test_java_version_defaults(self):
        s = JVMSettings()
        assert s.min_java_version == 11
        assert s.jdk_version == "17.0.12"
        assert s.jdk_build == "7"

    def test_heap_defaults(self):
        s = JVMSettings()
        assert s.min_heap_size == "256m"
        assert s.max_heap_size == "2048m"

    def test_tweety_settings(self):
        s = JVMSettings()
        assert s.tweety_version == "1.29"
        assert isinstance(s.tweety_libs_dir, Path)
        assert isinstance(s.native_libs_dir, Path)

    def test_has_azure_openai_nested(self):
        s = JVMSettings()
        assert isinstance(s.azure_openai, AzureOpenAISettings)


# ============================================================
# AppSettings — structure and defaults
# ============================================================


class TestAppSettings:
    def test_debug_mode_default(self):
        s = AppSettings()
        assert s.debug_mode is False

    def test_environment_default(self):
        s = AppSettings()
        assert s.environment == "development"

    def test_enable_jvm_default(self):
        s = AppSettings()
        assert s.enable_jvm is True

    def test_use_mock_llm_default(self):
        s = AppSettings()
        assert s.use_mock_llm is False

    def test_project_root_is_path(self):
        s = AppSettings()
        assert isinstance(s.project_root, Path)
        assert s.project_root.is_absolute()

    def test_computed_config_dir(self):
        s = AppSettings()
        assert isinstance(s.config_dir, Path)
        assert "argumentation_analysis" in str(s.config_dir)
        assert str(s.config_dir).endswith("data")

    def test_computed_config_file_json(self):
        s = AppSettings()
        assert str(s.config_file_json).endswith("extract_sources.json")

    def test_computed_config_file_enc(self):
        s = AppSettings()
        assert str(s.config_file_enc).endswith(".json.gz.enc")

    def test_computed_config_file_is_enc(self):
        s = AppSettings()
        # config_file == config_file_enc for legacy compat
        assert s.config_file == s.config_file_enc

    def test_all_child_settings_initialized(self):
        s = AppSettings()
        assert isinstance(s.openai, OpenAISettings)
        assert isinstance(s.tika, TikaSettings)
        assert isinstance(s.jina, JinaSettings)
        assert isinstance(s.network, NetworkSettings)
        assert isinstance(s.ui, UISettings)
        assert isinstance(s.service_manager, ServiceManagerSettings)
        assert isinstance(s.jvm, JVMSettings)

    def test_passphrase_default_none(self):
        s = AppSettings()
        # May have a value from .env, or None if not set
        assert s.passphrase is None or isinstance(s.passphrase, SecretStr)

    def test_encryption_key_default_none(self):
        s = AppSettings()
        assert s.encryption_key is None or isinstance(s.encryption_key, SecretStr)
