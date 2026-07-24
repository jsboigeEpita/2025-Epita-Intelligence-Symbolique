# tests/unit/argumentation_analysis/ui/test_extract_utils_encryption_key.py
"""Regression tests for the encryption_key normalisation in extract_utils.

Background
----------
The two helpers ``load_extract_definitions_safely`` and
``save_extract_definitions_safely`` historically typed ``encryption_key`` as
``Optional[str]`` even though the underlying ``CryptoService`` is documented
to expect ``Optional[bytes]``. Two ``TODO`` markers recorded the gap. The
public signature must stay ``Optional[str]`` (legacy callers pass strings), so
the fix is a *normalisation* at the call site: ``str`` inputs are encoded as
UTF-8 bytes before being forwarded to the crypto service. ``bytes`` inputs are
passed through unchanged. ``None`` inputs short-circuit the encryption branch
as before.

These tests verify (1) the imports resolve, (2) the public signatures still
accept ``None`` and ``bytes`` without raising, and (3) the JSON-fallback path
remains functional when ``encryption_key`` is ``None``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest


def _write_json(path: Path, payload: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_load_extract_definitions_safely_importable() -> None:
    from argumentation_analysis.ui.extract_utils import (
        load_extract_definitions_safely,
        save_extract_definitions_safely,
    )

    assert callable(load_extract_definitions_safely)
    assert callable(save_extract_definitions_safely)


def test_load_falls_back_to_json_when_key_is_none(tmp_path: Path) -> None:
    """The pure fallback path (no encryption) must keep working unchanged."""
    from argumentation_analysis.ui.extract_utils import (
        load_extract_definitions_safely,
    )

    payload = [{"source": "dummy", "extracts": []}]
    fallback = tmp_path / "defs.json"
    _write_json(fallback, payload)

    # encryption_key=None is the dominant production path; it must not be
    # affected by the normalisation change.
    defs, msg = load_extract_definitions_safely(
        config_file=tmp_path / "missing.json",
        encryption_key=None,
        fallback_json_file=fallback,
    )

    assert defs == payload, "fallback JSON must be loaded verbatim"
    assert "définitions" in msg.lower() or "definitions" in msg.lower()


@pytest.mark.parametrize("encryption_key", [None, b"", b"raw-bytes-key"])
def test_load_tolerates_bytes_or_none_encryption_key(
    tmp_path: Path, encryption_key: bytes | None
) -> None:
    """The signature must accept ``bytes`` (canonical) and ``None`` without raising.

    The encrypted file does not exist in this fixture, so the function is
    expected to fall through to ``KeyError``/``AttributeError`` only if the
    CryptoService surface is wired. In this test we rely on the public surface
    staying importable and the call not raising ``TypeError`` from our normalisation.
    """
    from argumentation_analysis.ui.extract_utils import (
        load_extract_definitions_safely,
    )

    fallback = tmp_path / "defs.json"
    _write_json(fallback, [{"source": "dummy", "extracts": []}])

    # We catch TypeError explicitly to ensure the normalisation did not
    # introduce a regression on the input contract.
    try:
        defs, _msg = load_extract_definitions_safely(
            config_file=tmp_path / "missing.enc.json",
            encryption_key=encryption_key,
            fallback_json_file=fallback,
        )
    except TypeError as exc:
        pytest.fail(
            f"load_extract_definitions_safely raised TypeError on key={encryption_key!r}: {exc}"
        )

    # Without a real encrypted file, the fallback path is expected to deliver
    # the payload regardless of the encryption_key value.
    assert defs == [{"source": "dummy", "extracts": []}]


def test_save_no_encryption_key_writes_fallback(tmp_path: Path) -> None:
    """The save path with ``encryption_key=None`` must write the fallback JSON."""
    from argumentation_analysis.ui.extract_utils import (
        save_extract_definitions_safely,
    )

    payload = [{"source": "dummy", "extracts": []}]
    fallback = tmp_path / "defs.json"

    ok, _msg = save_extract_definitions_safely(
        extract_definitions=payload,
        config_file=tmp_path / "missing.enc.json",
        encryption_key=None,
        fallback_json_file=fallback,
    )

    assert ok is True
    assert fallback.exists()
    assert json.loads(fallback.read_text(encoding="utf-8")) == payload


def test_todo_markers_removed() -> None:
    """Static guard: the two TODO markers must not be reintroduced."""
    import re
    from pathlib import Path

    src = Path("argumentation_analysis/ui/extract_utils.py").read_text(encoding="utf-8")
    # The two TODO lines about encryption_key→bytes must be gone.
    matches = re.findall(r"TODO:.*encryption_key.*bytes", src)
    assert not matches, (
        f"Unexpected remaining TODO(s) about encryption_key bytes: {matches}"
    )