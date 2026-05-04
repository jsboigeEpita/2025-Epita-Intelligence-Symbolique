"""LLM response caching layer for deterministic tests and CI cost reduction.

Wraps Semantic Kernel's ChatCompletionClientBase to cache responses on disk.
Supports three modes controlled by LLM_CACHE_MODE env var:
- record: cache miss → API call → store response (default for live runs)
- replay: cache miss → raise LLMCacheMiss (CI determinism)
- off: pass-through, no caching

Cache key: sha256(model_id + messages_json + temperature + tools_json)
Cache backend: diskcache (mature, cross-platform)
Cache location: .cache/llm_responses/ (gitignored)
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from semantic_kernel.contents.chat_history import ChatHistory
from semantic_kernel.contents.chat_message_content import ChatMessageContent
from semantic_kernel.connectors.ai.chat_completion_client_base import (
    ChatCompletionClientBase,
)

logger = logging.getLogger("LLMCache")

CACHE_DIR = Path(os.getenv("LLM_CACHE_DIR", ".cache/llm_responses"))
REPLAY = "replay"
RECORD = "record"
OFF = "off"


class LLMCacheMiss(Exception):
    """Raised in replay mode when a cache key is not found."""

    pass


def get_cache_mode() -> str:
    """Read LLM_CACHE_MODE env var. Defaults to 'off'."""
    mode = os.getenv("LLM_CACHE_MODE", OFF).lower()
    if mode not in (REPLAY, RECORD, OFF):
        raise ValueError(
            f"Invalid LLM_CACHE_MODE={mode!r}. Must be one of: replay, record, off"
        )
    return mode


def _serialize_messages(chat_history: ChatHistory) -> list:
    """Extract serializable message dicts from ChatHistory."""
    messages = []
    for msg in chat_history.messages:
        role = getattr(msg, "role", None)
        role_str = getattr(role, "value", str(role)) if role is not None else "unknown"
        entry = {"role": role_str}
        content = getattr(msg, "content", None)
        if content is not None:
            entry["content"] = str(content)
        # Include tool calls if present
        items = getattr(msg, "items", None)
        if items:
            serialized_items = []
            for item in items:
                item_data = {"type": type(item).__name__}
                if hasattr(item, "function_name"):
                    item_data["function_name"] = item.function_name
                if hasattr(item, "plugin_name"):
                    item_data["plugin_name"] = item.plugin_name
                if hasattr(item, "arguments"):
                    item_data["arguments"] = str(item.arguments)
                # Serialize tool call results for FunctionResultContent items
                if hasattr(item, "result"):
                    try:
                        item_data["result"] = json.dumps(item.result, default=str)
                    except (TypeError, ValueError):
                        item_data["result"] = str(item.result)
                serialized_items.append(item_data)
            entry["items"] = serialized_items
        messages.append(entry)
    return messages


def _serialize_settings(settings) -> dict:
    """Extract deterministic fields from PromptExecutionSettings."""
    result = {}
    if settings is None:
        return result
    for attr in (
        "ai_model_id",
        "temperature",
        "max_tokens",
        "top_p",
        "presence_penalty",
        "frequency_penalty",
        "service_id",
    ):
        val = getattr(settings, attr, None)
        if val is not None:
            result[attr] = val
    # Include tool_choice if present
    tool_choice = getattr(settings, "tool_choice", None)
    if tool_choice is not None:
        result["tool_choice"] = str(tool_choice)
    # Include tool definitions (function schemas) — critical for agentic workflows
    # where different tool configs with same tool_choice would collide
    tools = getattr(settings, "tools", None)
    if tools is not None:
        try:
            result["tools"] = json.dumps(tools, sort_keys=True, default=str)
        except (TypeError, ValueError):
            result["tools"] = str(tools)
    return result


def compute_cache_key(chat_history: ChatHistory, settings=None) -> str:
    """Generate a stable SHA-256 cache key from messages + settings."""
    key_data = {
        "messages": _serialize_messages(chat_history),
        "settings": _serialize_settings(settings),
    }
    raw = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _serialize_response(response: List[ChatMessageContent]) -> list:
    """Serialize a list of ChatMessageContent to JSON-compatible structure."""
    serialized = []
    for msg in response:
        role = getattr(msg, "role", "assistant")
        role_str = getattr(role, "value", str(role))
        entry = {"role": role_str}
        content = getattr(msg, "content", None)
        entry["content"] = str(content) if content is not None else ""
        # Metadata (usage stats, model, etc.)
        metadata = getattr(msg, "metadata", None)
        if metadata:
            safe_meta = {}
            for k, v in metadata.items():
                try:
                    json.dumps(v)
                    safe_meta[k] = v
                except (TypeError, ValueError):
                    safe_meta[k] = str(v)
            entry["metadata"] = safe_meta
        serialized.append(entry)
    return serialized


def _deserialize_response(serialized: list) -> List[ChatMessageContent]:
    """Reconstruct ChatMessageContent list from cached JSON."""
    results = []
    for entry in serialized:
        msg = ChatMessageContent(
            role=entry.get("role", "assistant"),
            content=entry.get("content", ""),
        )
        if "metadata" in entry:
            msg.metadata = entry["metadata"]
        results.append(msg)
    return results


class CachedChatCompletion(ChatCompletionClientBase):
    """Wraps a ChatCompletionClientBase with disk-backed response caching.

    In 'record' mode, passes calls through to the inner service and caches results.
    In 'replay' mode, reads from cache only — raises LLMCacheMiss on unknown keys.
    In 'off' mode, passes through without caching.
    """

    def __init__(
        self,
        inner: ChatCompletionClientBase,
        cache_dir: Optional[Path] = None,
        mode: Optional[str] = None,
    ):
        self._inner = inner
        self._mode = mode or get_cache_mode()
        self._cache_dir = cache_dir or CACHE_DIR
        self._cache = None
        if self._mode in (RECORD, REPLAY):
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            try:
                import diskcache

                self._cache = diskcache.Cache(str(self._cache_dir))
            except ImportError:
                logger.warning("diskcache not installed, caching disabled")
                self._mode = OFF

    @property
    def mode(self) -> str:
        return self._mode

    async def get_chat_message_contents(
        self,
        chat_history: ChatHistory,
        settings=None,
        **kwargs,
    ) -> List[ChatMessageContent]:
        """Intercept LLM calls with caching logic."""
        if self._mode == OFF or self._cache is None:
            return await self._inner.get_chat_message_contents(
                chat_history=chat_history, settings=settings, **kwargs
            )

        key = compute_cache_key(chat_history, settings)

        if self._mode == REPLAY:
            cached = self._cache.get(key)
            if cached is None:
                raise LLMCacheMiss(
                    f"Cache miss in replay mode for key {key[:16]}... "
                    f"Record fixtures first with LLM_CACHE_MODE=record"
                )
            logger.debug("Cache HIT (replay): %s...", key[:16])
            return _deserialize_response(cached)

        # RECORD mode: check cache, fall back to API
        cached = self._cache.get(key)
        if cached is not None:
            logger.debug("Cache HIT (record): %s...", key[:16])
            return _deserialize_response(cached)

        logger.debug("Cache MISS (record): %s..., calling API", key[:16])
        response = await self._inner.get_chat_message_contents(
            chat_history=chat_history, settings=settings, **kwargs
        )
        self._cache.set(key, _serialize_response(response))
        return response

    # Delegate attribute access to inner service
    def __getattr__(self, name):
        return getattr(self._inner, name)

    def close(self):
        """Close the diskcache and release resources."""
        if self._cache is not None:
            self._cache.close()
            self._cache = None
