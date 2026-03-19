"""
Model registry for multi-model benchmarking.

Manages OpenAI-compatible endpoints and switches the active model
at runtime by reconfiguring environment variables.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

logger = logging.getLogger("evaluation.model_registry")


@dataclass
class ModelConfig:
    """Configuration for a single model endpoint."""

    model_id: str
    base_url: str
    api_key: str
    display_name: str = ""
    cost_per_1k_tokens: float = 0.0
    is_thinking_model: bool = False
    max_tokens: Optional[int] = None

    def __post_init__(self):
        if not self.display_name:
            self.display_name = self.model_id


class ModelRegistry:
    """Registry of available LLM models for benchmarking."""

    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}
        self._active: Optional[str] = None

    def register(self, name: str, config: ModelConfig) -> None:
        self._models[name] = config
        logger.info(f"Registered model: {name} ({config.display_name})")

    def get(self, name: str) -> ModelConfig:
        if name not in self._models:
            raise KeyError(
                f"Model '{name}' not registered. Available: {list(self._models.keys())}"
            )
        return self._models[name]

    def list_models(self) -> Dict[str, ModelConfig]:
        return dict(self._models)

    @property
    def active(self) -> Optional[str]:
        return self._active

    def activate(self, name: str) -> ModelConfig:
        """Set model as active by updating environment variables."""
        config = self.get(name)
        os.environ["OPENAI_API_KEY"] = config.api_key
        os.environ["OPENAI_BASE_URL"] = config.base_url
        os.environ["OPENAI_CHAT_MODEL_ID"] = config.model_id
        self._active = name
        logger.info(f"Activated model: {name} → {config.base_url}")
        return config

    def restore_env(self, saved: Dict[str, str]) -> None:
        """Restore environment variables from a saved snapshot."""
        for key, val in saved.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val

    def save_env(self) -> Dict[str, Optional[str]]:
        """Snapshot current model-related environment variables."""
        keys = ["OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_CHAT_MODEL_ID"]
        return {k: os.environ.get(k) for k in keys}

    @classmethod
    def from_env(cls) -> "ModelRegistry":
        """Build a registry from .env variables (numbered endpoints)."""
        registry = cls()

        # Primary endpoint
        api_key = os.environ.get("OPENAI_API_KEY", "")
        model_id = os.environ.get("OPENAI_CHAT_MODEL_ID", "gpt-5-mini")
        base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        if api_key:
            registry.register(
                "default",
                ModelConfig(
                    model_id=model_id,
                    base_url=base_url,
                    api_key=api_key,
                    display_name=f"Default ({model_id})",
                ),
            )

        # Numbered endpoints (2, 3, 4, ...)
        for i in range(2, 10):
            key = os.environ.get(f"OPENAI_API_KEY_{i}", "")
            url = os.environ.get(f"OPENAI_BASE_URL_{i}", "")
            name = os.environ.get(f"OPENAI_ENDPOINT_NAME_{i}", f"endpoint-{i}")
            if key and url:
                registry.register(
                    f"endpoint-{i}",
                    ModelConfig(
                        model_id=name,
                        base_url=url,
                        api_key=key,
                        display_name=name,
                    ),
                )

        # OpenRouter
        or_key = os.environ.get("OPENROUTER_API_KEY", "")
        or_url = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        if or_key:
            registry.register(
                "openrouter",
                ModelConfig(
                    model_id="anthropic/claude-sonnet-4-6",
                    base_url=or_url,
                    api_key=or_key,
                    display_name="OpenRouter (Claude Sonnet)",
                ),
            )

        return registry
