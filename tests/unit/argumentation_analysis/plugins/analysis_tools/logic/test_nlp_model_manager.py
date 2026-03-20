# -*- coding: utf-8 -*-
"""
Tests for argumentation_analysis.plugins.analysis_tools.logic.nlp_model_manager
Covers NLPModelManager: singleton pattern, load_models_sync, get_model,
are_models_loaded, graceful degradation without transformers.
"""

import sys
import pytest
from unittest.mock import MagicMock


def _get_module():
    """Get the actual nlp_model_manager MODULE (not the instance exported by __init__.py)."""
    return sys.modules[
        "argumentation_analysis.plugins.analysis_tools.logic.nlp_model_manager"
    ]


# Force import so the module is in sys.modules
from argumentation_analysis.plugins.analysis_tools.logic.nlp_model_manager import (
    NLPModelManager,
    nlp_model_manager as _nlp_instance,
    TEXT_CLASSIFICATION_MODEL,
    NER_MODEL,
    TEXT_GENERATION_MODEL,
    HAS_TRANSFORMERS,
)

# ============================================================
# Singleton pattern
# ============================================================


class TestSingleton:
    def test_singleton_returns_same_instance(self):
        a = NLPModelManager()
        b = NLPModelManager()
        assert a is b

    def test_module_level_instance_exists(self):
        assert isinstance(_nlp_instance, NLPModelManager)


# ============================================================
# Constants
# ============================================================


class TestConstants:
    def test_model_constants_defined(self):
        assert isinstance(TEXT_CLASSIFICATION_MODEL, str)
        assert isinstance(NER_MODEL, str)
        assert isinstance(TEXT_GENERATION_MODEL, str)

    def test_has_transformers_flag(self):
        assert isinstance(HAS_TRANSFORMERS, bool)


# ============================================================
# get_model / are_models_loaded (without loading)
# ============================================================


class TestGetModelWithoutLoad:
    def test_get_model_returns_none_when_not_loaded(self):
        manager = NLPModelManager()
        original_loaded = NLPModelManager._models_loaded
        original_models = NLPModelManager._models.copy()
        try:
            NLPModelManager._models_loaded = False
            NLPModelManager._models = {}
            result = manager.get_model("sentiment")
            assert result is None
        finally:
            NLPModelManager._models_loaded = original_loaded
            NLPModelManager._models = original_models

    def test_are_models_loaded_false_initially(self):
        manager = NLPModelManager()
        original_loaded = NLPModelManager._models_loaded
        try:
            NLPModelManager._models_loaded = False
            assert manager.are_models_loaded() is False
        finally:
            NLPModelManager._models_loaded = original_loaded


# ============================================================
# load_models_sync (mocked)
# ============================================================


class TestLoadModelsSync:
    def test_load_without_transformers_does_nothing(self):
        mod = _get_module()
        manager = NLPModelManager()
        original_loaded = NLPModelManager._models_loaded
        original_has = mod.HAS_TRANSFORMERS
        original_models = NLPModelManager._models.copy()
        try:
            NLPModelManager._models_loaded = False
            NLPModelManager._models = {}
            mod.HAS_TRANSFORMERS = False
            manager.load_models_sync()
            assert manager.are_models_loaded() is False
        finally:
            NLPModelManager._models_loaded = original_loaded
            mod.HAS_TRANSFORMERS = original_has
            NLPModelManager._models = original_models

    def test_load_already_loaded_does_nothing(self):
        manager = NLPModelManager()
        original_loaded = NLPModelManager._models_loaded
        original_models = NLPModelManager._models.copy()
        try:
            NLPModelManager._models_loaded = True
            NLPModelManager._models = {"sentiment": "fake"}
            manager.load_models_sync()
            assert manager.are_models_loaded() is True
            assert NLPModelManager._models["sentiment"] == "fake"
        finally:
            NLPModelManager._models_loaded = original_loaded
            NLPModelManager._models = original_models

    def test_load_with_mock_transformers(self):
        mod = _get_module()
        manager = NLPModelManager()
        original_loaded = NLPModelManager._models_loaded
        original_has = mod.HAS_TRANSFORMERS
        original_models = NLPModelManager._models.copy()
        original_pipeline = mod.pipeline
        # Save instance-level attr if it exists
        had_instance_attr = "_models_loaded" in manager.__dict__
        try:
            NLPModelManager._models_loaded = False
            # Clear instance-level shadow if present
            manager.__dict__.pop("_models_loaded", None)
            NLPModelManager._models = {}
            mod.HAS_TRANSFORMERS = True
            mock_pipeline = MagicMock(side_effect=lambda task, model: f"mock_{task}")
            mod.pipeline = mock_pipeline
            manager.load_models_sync()
            assert manager.are_models_loaded() is True
            assert "sentiment" in NLPModelManager._models
            assert "ner" in NLPModelManager._models
        finally:
            # Remove instance-level shadow set by load_models_sync
            manager.__dict__.pop("_models_loaded", None)
            NLPModelManager._models_loaded = original_loaded
            mod.HAS_TRANSFORMERS = original_has
            NLPModelManager._models = original_models
            mod.pipeline = original_pipeline

    def test_load_error_sets_loaded_false(self):
        mod = _get_module()
        manager = NLPModelManager()
        original_loaded = NLPModelManager._models_loaded
        original_has = mod.HAS_TRANSFORMERS
        original_models = NLPModelManager._models.copy()
        original_pipeline = mod.pipeline
        try:
            NLPModelManager._models_loaded = False
            # Clear instance-level shadow if present from previous tests
            manager.__dict__.pop("_models_loaded", None)
            NLPModelManager._models = {}
            mod.HAS_TRANSFORMERS = True
            mod.pipeline = MagicMock(side_effect=RuntimeError("download fail"))
            manager.load_models_sync()
            assert manager.are_models_loaded() is False
        finally:
            manager.__dict__.pop("_models_loaded", None)
            NLPModelManager._models_loaded = original_loaded
            mod.HAS_TRANSFORMERS = original_has
            NLPModelManager._models = original_models
            mod.pipeline = original_pipeline


# ============================================================
# get_model after successful load
# ============================================================


class TestGetModelAfterLoad:
    def test_returns_model_when_loaded(self):
        manager = NLPModelManager()
        original_loaded = NLPModelManager._models_loaded
        original_models = NLPModelManager._models.copy()
        try:
            NLPModelManager._models_loaded = True
            NLPModelManager._models = {"sentiment": "mock_sentiment", "ner": "mock_ner"}
            assert manager.get_model("sentiment") == "mock_sentiment"
            assert manager.get_model("ner") == "mock_ner"
        finally:
            NLPModelManager._models_loaded = original_loaded
            NLPModelManager._models = original_models

    def test_returns_none_for_unknown_model(self):
        manager = NLPModelManager()
        original_loaded = NLPModelManager._models_loaded
        original_models = NLPModelManager._models.copy()
        try:
            NLPModelManager._models_loaded = True
            NLPModelManager._models = {"sentiment": "mock"}
            assert manager.get_model("nonexistent") is None
        finally:
            NLPModelManager._models_loaded = original_loaded
            NLPModelManager._models = original_models
