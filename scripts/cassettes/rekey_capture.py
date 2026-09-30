"""Pytest plugin: capture the key material of every replay-mode miss.

Loaded by ``rekey_settings_class.py`` (its docstring says why) through
``-p scripts.cassettes.rekey_capture``. Wraps both cache-key derivations of
``argumentation_analysis.services.llm_cache`` — ``compute_cache_key`` (SK
path) and ``compute_raw_cache_key`` (raw path) — and stashes, per computed
key, the serialized ``messages`` + ``settings`` block the derivation saw. At
session finish it writes, for every key the run MISSED in replay mode, that
key material to ``$REKEY_CAPTURE_OUT`` so the driver can rebuild the
pre-#2853 key from the same inputs the live derivation consumed.

The wrapper must not change any key: it computes the original first and
returns it untouched. Payload serialization failures are stashed as a
``<unserializable: ...>`` note — the driver then treats that miss as
unrebuildable and names it, never silently.
"""

from __future__ import annotations

import json
import os
import traceback
from pathlib import Path

_STASH: dict[str, dict] = {}


def _caller_stack() -> list[str]:
    frames = []
    for f in traceback.extract_stack()[:-1]:
        frames.append(f"{Path(f.filename).name}:{f.lineno}:{f.name}")
    return frames[-8:]


def pytest_configure(config):
    import argumentation_analysis.services.llm_cache as llm

    orig_sk = llm.compute_cache_key

    def spy_sk(chat_history, settings=None):
        key = orig_sk(chat_history, settings)
        try:
            payload = json.dumps(
                {
                    "messages": llm._serialize_messages(chat_history),
                    "settings": llm._serialize_settings(settings),
                },
                sort_keys=True,
                ensure_ascii=False,
            )
        except Exception as exc:  # probe must not break the run
            payload = f"<unserializable: {exc!r}>"
        _STASH[key[:16]] = {
            "key": key,
            "path": "sk",
            "payload": payload,
            "settings_class": type(settings).__name__ if settings is not None else None,
            "stack": _caller_stack(),
        }
        return key

    llm.compute_cache_key = spy_sk

    orig_raw = llm.compute_raw_cache_key

    def spy_raw(**kwargs):
        key = orig_raw(**kwargs)
        try:
            payload = json.dumps(
                kwargs, sort_keys=True, ensure_ascii=False, default=str
            )
        except Exception as exc:  # probe must not break the run
            payload = f"<unserializable: {exc!r}>"
        _STASH[key[:16]] = {
            "key": key,
            "path": "raw",
            "payload": payload,
            "settings_class": None,
            "stack": _caller_stack(),
        }
        return key

    llm.compute_raw_cache_key = spy_raw


def pytest_sessionfinish(session, exitstatus):
    import argumentation_analysis.services.llm_cache as llm

    misses = llm.get_cache_miss_keys()
    records = []
    for m in misses:
        rec = _STASH.get(m)
        records.append(rec if rec else {"prefix": m, "note": "no payload stashed"})
    out = Path(os.environ["REKEY_CAPTURE_OUT"])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {"misses": misses, "records": records}, indent=2, ensure_ascii=False
        ),
        encoding="utf-8",
    )
    print(
        f"\n[rekey-capture] miss_replay={len(misses)} "
        f"attributed={sum(1 for r in records if 'payload' in r)}"
    )
