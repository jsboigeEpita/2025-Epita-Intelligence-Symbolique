"""
Local LLM service adapter — integration of student project 2.3.6.

Provides a service wrapper for local GGUF models served via llama-cpp-python.
Designed to register as a provider in ServiceDiscovery, enabling transparent
LLM provider switching between local/remote models.

This adapter does NOT import llama-cpp-python directly. Instead, it connects
to a locally running OpenAI-compatible server (the student project's FastAPI
or any vLLM/Ollama endpoint).

Dependencies:
    - httpx (async HTTP client, already in project deps)
    Graceful degradation if endpoint is unreachable.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("LocalLLMService")


class LocalLLMService:
    """
    Adapter for local LLM inference via OpenAI-compatible endpoints.

    Supports:
    - Student 2.3.6 FastAPI server (llama-cpp GGUF models)
    - vLLM endpoints (Qwen, GLM, etc.)
    - Ollama endpoints
    - Any OpenAI-compatible local server

    Usage:
        service = LocalLLMService(endpoint="http://localhost:5001/v1")
        result = await service.chat_completion(messages=[...])
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:5001/v1",
        model: Optional[str] = None,
        api_key: str = "not-needed",
        timeout: float = 60.0,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.timeout = timeout
        self._available = None

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Send chat completion request to local endpoint."""
        try:
            import httpx
        except ImportError:
            logger.error("httpx not installed, cannot call local LLM")
            return {"error": "httpx not installed"}

        payload: Dict[str, Any] = {
            "model": model or self.model or "default",
            "messages": messages,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        url = f"{self.endpoint}/chat/completions"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.warning("Local LLM call failed: %s", e)
            return {"error": str(e)}

    async def is_available(self) -> bool:
        """Check if the local LLM endpoint is reachable."""
        if self._available is not None:
            return self._available
        try:
            import httpx

            url = f"{self.endpoint}/models"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                self._available = response.status_code == 200
        except Exception:
            self._available = False
        return self._available

    def get_status_details(self) -> Dict[str, Any]:
        """Return service status for diagnostics."""
        return {
            "service": "local_llm",
            "endpoint": self.endpoint,
            "model": self.model,
            "available": self._available,
        }

    def __repr__(self) -> str:
        return f"LocalLLMService(endpoint={self.endpoint!r}, model={self.model!r})"
