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
from typing import Any, Dict, List, Optional, cast

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


# ──── Cache monitoring (BO-3 #1473 PR3 — profiling/batch/monitoring) ────
#
# Thread-safe counters shared by BOTH cache layers (CachedChatCompletion for the
# SK-native path, cached_raw_chat_completion for the direct path). Exposes a
# single truthful view of how many calls were served from cache vs. hit the API,
# so a replay batch can be proven to make ZERO live calls (anti-théâtre #1019:
# a silent live fallback on a cache miss is exactly the theater this measures).
# PR3 measures the cache wired in PR1/PR2 — it does NOT add caching logic.

import threading


class CacheStats:
    """Counters for cache hit/miss/live across both layers (BO-3 #1473 PR3).

    - ``hit``: served from cache (record or replay mode)
    - ``miss_record``: record-mode miss → API call + store
    - ``miss_replay``: replay-mode miss → ``LLMCacheMiss`` raised (never live)
    - ``live``: actual API round-trip made (off passthrough OR record miss)

    ``live`` is the anti-theatre metric: at replay it MUST stay 0 — any non-zero
    value means a cache miss silently fell through to the API.
    """

    __slots__ = ("_lock", "hit", "miss_record", "miss_replay", "live")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.hit = 0
        self.miss_record = 0
        self.miss_replay = 0
        self.live = 0

    def as_dict(self) -> Dict[str, int]:
        with self._lock:
            return {
                "hit": self.hit,
                "miss_record": self.miss_record,
                "miss_replay": self.miss_replay,
                "live": self.live,
            }

    def reset(self) -> None:
        with self._lock:
            self.hit = 0
            self.miss_record = 0
            self.miss_replay = 0
            self.live = 0


_cache_stats = CacheStats()


def get_cache_stats() -> Dict[str, int]:
    """Snapshot of the shared cache counters (both layers, BO-3 #1473 PR3)."""
    return _cache_stats.as_dict()


def reset_cache_stats() -> None:
    """Zero the shared cache counters (test isolation / per-batch measurement)."""
    _cache_stats.reset()


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
            _cache_stats.live += 1
            return await self._inner.get_chat_message_contents(
                chat_history=chat_history, settings=settings, **kwargs
            )

        key = compute_cache_key(chat_history, settings)

        if self._mode == REPLAY:
            cached = self._cache.get(key)
            if cached is None:
                _cache_stats.miss_replay += 1
                raise LLMCacheMiss(
                    f"Cache miss in replay mode for key {key[:16]}... "
                    f"Record fixtures first with LLM_CACHE_MODE=record"
                )
            _cache_stats.hit += 1
            logger.debug("Cache HIT (replay): %s...", key[:16])
            return _deserialize_response(cached)

        # RECORD mode: check cache, fall back to API
        cached = self._cache.get(key)
        if cached is not None:
            _cache_stats.hit += 1
            logger.debug("Cache HIT (record): %s...", key[:16])
            return _deserialize_response(cached)

        logger.debug("Cache MISS (record): %s..., calling API", key[:16])
        _cache_stats.miss_record += 1
        response = await self._inner.get_chat_message_contents(
            chat_history=chat_history, settings=settings, **kwargs
        )
        _cache_stats.live += 1
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


# ──── Raw-path cache (direct OpenAI calls via _guarded_chat_completion) ────
#
# CachedChatCompletion above wraps the SK service (kernel/agents path). But the
# direct path — ``_guarded_chat_completion`` → ``client.chat.completions.create``
# (extract/governance/quality/fallacy/counter-arg) — never touches an SK service,
# so it needs its own cache at the raw OpenAI-kwargs level. Both share the same
# diskcache backend + CACHE_DIR so a single record run seeds every call site,
# and a single replay run replays every call site (BO-3 #1473, determinism DoD).

_RAW_CACHE_KEY_FIELDS = (
    "temperature",
    "max_tokens",
    "top_p",
    "presence_penalty",
    "frequency_penalty",
    "response_format",
    "tool_choice",
    "tools",
)


def compute_raw_cache_key(**kwargs: Any) -> str:
    """SHA-256 over the deterministic part of a raw chat.completions.create call.

    The cache key captures the fields that affect the LLM output: model,
    messages, and the deterministic sampling/tooling kwargs. Non-deterministic
    kwargs (e.g. ``user``, ``seed`` if unset) are ignored. The ``client`` is
    NOT part of the key (two clients with the same provider → same answer).
    Takes the full ``client.chat.completions.create`` kwargs and extracts the
    relevant fields itself, so callers never risk a double-arg collision.
    """
    key_data: Dict[str, Any] = {
        "model": kwargs.get("model"),
        "messages": kwargs.get("messages", []),
    }
    for field in _RAW_CACHE_KEY_FIELDS:
        if field in kwargs and kwargs[field] is not None:
            key_data[field] = kwargs[field]
    raw = json.dumps(key_data, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _serialize_chat_completion(response: Any) -> Dict[str, Any]:
    """Serialize an OpenAI ChatCompletion to a JSON-safe dict (diskcache-storable).

    Uses pydantic ``model_dump`` (OpenAI v1+ SDK). The dict round-trips via
    ``ChatCompletion.model_validate`` (probed firsthand: content + tool_calls +
    JSON-string all survive).
    """
    if hasattr(response, "model_dump"):
        return cast(Dict[str, Any], response.model_dump())
    # Fallback: already a dict-like.
    return {"_fallback": str(response)}


def _deserialize_chat_completion(data: Any) -> Any:
    """Reconstruct an OpenAI ChatCompletion from a cached dict."""
    if isinstance(data, dict) and "_fallback" in data:
        return data["_fallback"]
    from openai.types.chat import ChatCompletion

    return ChatCompletion.model_validate(data)


# Module-level singleton diskcache for the raw path (shared with CACHE_DIR).
_raw_cache: Any = None
_raw_cache_dir: Optional[str] = None


def get_raw_cache(cache_dir: Optional[Path] = None) -> Any:
    """Return the shared raw-path diskcache, or None when caching is off.

    Lazily initialized so importing the module never opens a cache. Reuses one
    diskcache across calls within a process; a different ``cache_dir`` re-opens.
    """
    mode = get_cache_mode()
    if mode == OFF:
        return None
    env_cache_dir: Optional[str] = os.getenv("LLM_CACHE_DIR")
    target = str(cache_dir or env_cache_dir or CACHE_DIR)
    global _raw_cache, _raw_cache_dir
    if _raw_cache is None or _raw_cache_dir != target:
        Path(target).mkdir(parents=True, exist_ok=True)
        try:
            import diskcache

            _raw_cache = diskcache.Cache(target)
            _raw_cache_dir = target
        except ImportError:
            logger.warning("diskcache not installed, raw cache disabled")
            return None
    return _raw_cache


def reset_raw_cache() -> None:
    """Close + drop the module-level raw cache singleton (test isolation)."""
    global _raw_cache, _raw_cache_dir
    if _raw_cache is not None:
        try:
            _raw_cache.close()
        except Exception:  # noqa: BLE001 — best-effort teardown
            pass
    _raw_cache = None
    _raw_cache_dir = None


async def cached_raw_chat_completion(client: Any, **kwargs: Any) -> Any:
    """Cache-aware wrapper for ``client.chat.completions.create(**kwargs)``.

    Mirrors ``CachedChatCompletion`` but for the direct (non-SK) path. In replay
    mode a miss raises ``LLMCacheMiss`` (fail-loud — never a silent live call,
    BO-3 #1473 anti-theatre); in record mode a miss calls the API and caches the
    response; in off mode it passes through. The cache key is computed from the
    deterministic kwargs only (see ``compute_raw_cache_key``).
    """
    mode = get_cache_mode()
    if mode == OFF:
        _cache_stats.live += 1
        return await client.chat.completions.create(**kwargs)
    cache = get_raw_cache()
    if cache is None:  # diskcache unavailable
        _cache_stats.live += 1
        return await client.chat.completions.create(**kwargs)
    key = compute_raw_cache_key(**kwargs)
    if mode == REPLAY:
        cached = cache.get(key)
        if cached is None:
            _cache_stats.miss_replay += 1
            raise LLMCacheMiss(
                f"Raw cache miss in replay mode for key {key[:16]}... "
                f"Record fixtures first with LLM_CACHE_MODE=record"
            )
        _cache_stats.hit += 1
        logger.debug("Raw cache HIT (replay): %s...", key[:16])
        return _deserialize_chat_completion(cached)
    # RECORD mode
    cached = cache.get(key)
    if cached is not None:
        _cache_stats.hit += 1
        logger.debug("Raw cache HIT (record): %s...", key[:16])
        return _deserialize_chat_completion(cached)
    logger.debug("Raw cache MISS (record): %s..., calling API", key[:16])
    _cache_stats.miss_record += 1
    response = await client.chat.completions.create(**kwargs)
    _cache_stats.live += 1
    cache.set(key, _serialize_chat_completion(response))
    return response
