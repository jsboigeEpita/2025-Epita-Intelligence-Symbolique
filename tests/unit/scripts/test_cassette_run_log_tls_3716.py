"""#3716 item 49b — the run's logs are verified against the bundle, not the OS store.

The symptom (#3716): on ``myia-ai-01`` step 1 with ``--verify-run`` refused with
``<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed:
unable to get issuer certificate>`` while every other client on the same seat
succeeded. The root, bisected by the coordinator over the 23 certificates of the
user store: ``ssl.create_default_context()`` with no ``cafile`` also loads the
platform store, and on Windows that includes the user's INTERMEDIATE store
(``Cert:\\CurrentUser\\CA``); with a cached Let's Encrypt intermediate
(``YR1``/``YR2``) the chain stops at its issuer ``ISRG Root YR``, which no store
carries. Removing those two certificates by thumbprint held until Windows
re-cached them — measured twice, 09/11 and 27/11 — so the seat repair is not a
repair.

The witness is the mechanical one: the context handed to ``urlopen`` is built
on the certifi bundle, and a context built with a ``cafile`` does not read the
platform store at all. Verification stays on, and a refusal is not retried
against a default context.

Seat free: the transport is a double, no network, no key.
"""

from __future__ import annotations

import importlib
import io
import ssl
import urllib.error
import zipfile
from pathlib import Path
from typing import Any, Dict, List

import pytest

# ``import`` is a keyword: the module is reached by name, as the #2326 suite does.
cassette_import = importlib.import_module("scripts.cassettes.import")

LOG = "Exported cassettes: 587\n"


def _zip_response(log_text: str) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("record job/4_Export cassettes/4_export.txt", log_text)
    buf.seek(0)
    return buf


class _CapturingUrlopen:
    """Records how the call was made, and answers with a shaped archive."""

    def __init__(self, payload: bytes = b"", error: Exception | None = None) -> None:
        self.calls: List[Dict[str, Any]] = []
        self._payload = payload
        self._error = error

    def __call__(self, req: Any, **kwargs: Any) -> io.BytesIO:
        self.calls.append(kwargs)
        if self._error is not None:
            raise self._error
        return _zip_response(LOG)


def _count(urlopen: Any) -> int:
    return cassette_import._run_export_count(
        "https://api.github.com",
        "owner/repo",
        "token",
        "45513278355",
        urlopen=urlopen,
    )


def test_the_run_log_call_carries_a_context_built_on_the_bundle(
    monkeypatch: pytest.MonkeyPatch,
):
    """The one mechanical claim: ``create_default_context`` is given the
    certifi bundle as ``cafile``. With a ``cafile`` CPython does NOT call
    ``load_default_certs`` — the Windows user store, and its cached
    ``YR1``/``YR2`` intermediates, are never read."""
    import certifi

    seen: Dict[str, Any] = {}
    real = ssl.create_default_context

    def spy(*args: Any, **kwargs: Any) -> ssl.SSLContext:
        seen.update(kwargs)
        seen["args"] = args
        return real(*args, **kwargs)

    monkeypatch.setattr(cassette_import.ssl, "create_default_context", spy)
    urlopen = _CapturingUrlopen()

    assert _count(urlopen) == 587  # the answer is unchanged: this is the seam only
    assert seen.get("cafile") == certifi.where(), (
        "the context is not anchored on the certifi bundle: without a cafile "
        "it also loads the platform store, which is the #3716 refusal"
    )
    assert seen.get("args") == (), seen


def test_verification_stays_on():
    """Narrowing the store must not weaken the check: the context handed over
    is a verifying one, hostname included."""
    urlopen = _CapturingUrlopen()

    _count(urlopen)

    context = urlopen.calls[0]["context"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_a_tls_refusal_stays_a_named_run_log_error_and_is_not_retried():
    """No fallback: a refusal is a provenance verdict, not a reason to try a
    weaker context. The transport is called exactly once, and the error line
    is the one the gate reports."""
    refusal = urllib.error.URLError(
        ssl.SSLCertVerificationError("unable to get issuer certificate")
    )
    urlopen = _CapturingUrlopen(error=refusal)

    with pytest.raises(cassette_import.RunLogError) as caught:
        _count(urlopen)

    assert "logs unreachable" in str(caught.value)
    assert "unable to get issuer certificate" in str(caught.value)
    assert len(urlopen.calls) == 1, urlopen.calls


def test_the_context_is_rebuilt_per_call_and_is_not_shared_state():
    """A module-level context would freeze whatever the first caller had (and
    would carry its session store into the next run). Each call builds its
    own, from the bundle, with nothing cached between them."""
    first = _CapturingUrlopen()
    second = _CapturingUrlopen()

    _count(first)
    _count(second)

    assert first.calls[0]["context"] is not second.calls[0]["context"]


def test_the_bundle_exists_on_this_seat():
    """Control: the repair leans on ``certifi`` because it is in
    ``conda-lock.yml``. If it were absent the import would fail at call time
    and the gate would redden for the wrong reason — so it is asserted here."""
    import certifi

    bundle = Path(certifi.where())
    assert bundle.is_file(), bundle
    assert bundle.stat().st_size > 0
