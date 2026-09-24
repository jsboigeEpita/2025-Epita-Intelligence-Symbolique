"""#2344: the UI's fetch and cache functions were a parallel copy of the services.

``ui/utils.py`` (and, for the cache, ``ui/cache_utils.py``) carried their own
copy of ``services/fetch_service`` and ``services/cache_service``, on the same
``_temp/text_cache`` directory and the same file names. #2581 repaired the
services; the copies kept both defects. Measured on ``main`` ``e4d451251``:

- ``fetch_direct_text`` and an uploaded ``.txt`` decoded with
  ``errors="ignore"``: a Latin-1 text lost its accents, and the cache kept
  the loss.
- The text cache and the raw download cache wrote in place. A write that
  failed midway left an empty or truncated file, which the next call served
  as the document.

The copies now delegate to the services. The network is replaced at
``requests``; the fetch and cache code under test is real.
"""

from __future__ import annotations

import io
import pathlib

import pytest
import requests

from argumentation_analysis.services.cache_service import CacheService
from argumentation_analysis.services.fetch_service import FetchService
from argumentation_analysis.ui import cache_utils
from argumentation_analysis.ui import config as ui_config
from argumentation_analysis.ui import utils as ui_utils

TEXT = "Liberté, égalité, fraternité : un texte accentué."
URL = "https://example.test/source_2344.txt"
PDF_URL = "https://example.test/source_2344.pdf"
RAW = b"%PDF-1.4 " + b"binary " * 64
# Both UI modules expose the cache functions; both must be the service's.
UI_CACHES = [
    pytest.param(ui_utils, id="ui.utils"),
    pytest.param(cache_utils, id="ui.cache_utils"),
]


def _response(content: bytes, content_type: str) -> requests.Response:
    """A real ``requests.Response``, with the encoding requests derives from the header."""
    response = requests.Response()
    response.status_code = 200
    response._content = content
    response.headers["Content-Type"] = content_type
    response.encoding = requests.utils.get_encoding_from_headers(response.headers)
    return response


@pytest.fixture
def ui_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    monkeypatch.setattr(ui_config, "CACHE_DIR", cache_dir)
    return cache_dir


@pytest.fixture
def network(monkeypatch):
    """``requests.get`` answers from ``gets``; ``requests.put`` (Tika) with ``put``."""
    answers = {"gets": {}, "put": None, "calls": []}

    def get(url, *args, **kwargs):
        answers["calls"].append(("GET", url))
        return answers["gets"][url]

    def put(url, *args, **kwargs):
        answers["calls"].append(("PUT", url))
        return answers["put"]

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setattr(requests, "put", put)
    return answers


class _DiskFullOn:
    """A file whose write of ``payload`` stops halfway, as on a full disk."""

    def __init__(self, f, payload: bytes):
        self._f = f
        self._payload = payload

    def write(self, data):
        if bytes(data) == self._payload:
            self._f.write(self._payload[: len(self._payload) // 2])
            self._f.flush()
            raise OSError(28, "No space left on device")
        return self._f.write(data)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._f.close()

    def __getattr__(self, name):
        return getattr(self._f, name)


@pytest.fixture
def disk_full_on_raw(monkeypatch):
    """Any binary write of ``RAW`` to disk stops halfway.

    Python 3.10's ``Path.open`` is bound to ``io.open`` when pathlib is
    imported, so both are patched: an in-place ``Path.write_bytes`` goes
    through the first, an atomic ``os.fdopen`` write through the second.
    """
    real_io_open = io.open
    real_path_open = pathlib.Path.open

    def io_open(file, mode="r", *args, **kwargs):
        f = real_io_open(file, mode, *args, **kwargs)
        return _DiskFullOn(f, RAW) if "w" in mode and "b" in mode else f

    def path_open(self, mode="r", *args, **kwargs):
        f = real_path_open(self, mode, *args, **kwargs)
        return _DiskFullOn(f, RAW) if "w" in mode and "b" in mode else f

    monkeypatch.setattr(io, "open", io_open)
    monkeypatch.setattr(pathlib.Path, "open", path_open)


class TestTheUiDecodesWithoutLoss:
    def test_latin1_page_keeps_its_accents_and_so_does_the_cache(
        self, ui_cache, network
    ):
        network["gets"][URL] = _response(
            TEXT.encode("latin-1"), "text/plain; charset=ISO-8859-1"
        )
        assert ui_utils.fetch_direct_text(URL) == TEXT
        assert ui_utils.load_from_cache(URL) == TEXT

    def test_latin1_upload_goes_to_tika_instead_of_losing_its_accents(
        self, ui_cache, network
    ):
        network["put"] = _response(TEXT.encode("utf-8"), "text/plain; charset=utf-8")
        text = ui_utils.fetch_with_tika(
            file_content=TEXT.encode("latin-1"), file_name="doc.txt"
        )
        assert text == TEXT
        assert [method for method, _ in network["calls"]] == ["PUT"]


class TestTheUiCacheNeverServesAPartialWrite:
    @pytest.mark.parametrize("module", UI_CACHES)
    def test_failed_save_leaves_no_entry(self, ui_cache, module):
        # A lone surrogate cannot be encoded, so the save fails midway.
        module.save_to_cache(URL, "début \ud800 fin")
        assert not module.get_cache_filepath(URL).exists()
        assert module.load_from_cache(URL) is None

    @pytest.mark.parametrize("module", UI_CACHES)
    def test_empty_cache_file_is_a_miss(self, ui_cache, module):
        # An empty file is what an interrupted in-place write left behind.
        module.get_cache_filepath(URL).write_bytes(b"")
        assert module.load_from_cache(URL) is None

    def test_empty_cache_file_is_fetched_again(self, ui_cache, network):
        ui_utils.get_cache_filepath(URL).write_bytes(b"")
        network["gets"][URL] = _response(
            "contenu frais".encode("utf-8"), "text/plain; charset=utf-8"
        )
        assert ui_utils.fetch_direct_text(URL) == "contenu frais"
        assert network["calls"] == [("GET", URL)]

    def test_interrupted_raw_download_leaves_no_raw_cache(
        self, ui_cache, network, disk_full_on_raw, tmp_path
    ):
        # The next call must not find a truncated raw file to send to Tika.
        raw_dir = tmp_path / "downloads"
        network["gets"][PDF_URL] = _response(RAW, "application/pdf")
        network["put"] = _response(TEXT.encode("utf-8"), "text/plain; charset=utf-8")
        text = ui_utils.fetch_with_tika(
            source_url=PDF_URL, temp_download_dir_override=raw_dir
        )
        assert text == TEXT
        assert list(raw_dir.iterdir()) == []


class TestTheUiContractHolds:
    """Controls: what the UI's callers rely on is unchanged by the delegation."""

    def test_a_completed_save_is_the_services_entry(self, ui_cache):
        ui_utils.save_to_cache(URL, TEXT)
        assert CacheService(ui_cache).load_from_cache(URL) == TEXT
        assert cache_utils.load_from_cache(URL) == TEXT

    def test_jina_strips_its_header(self, ui_cache, network):
        prefix = "https://jina.test/"
        network["gets"][prefix + URL] = _response(
            "Title: x\nMarkdown Content:\n  corps du texte  ".encode("utf-8"),
            "text/markdown; charset=utf-8",
        )
        text = ui_utils.fetch_with_jina(URL, jina_reader_prefix_override=prefix)
        assert text == "corps du texte"

    def test_a_failed_fetch_is_a_connection_error(self, ui_cache, monkeypatch):
        def down(*args, **kwargs):
            raise requests.exceptions.ConnectionError("down")

        # The service is stubbed at its method, so its retries and its shared
        # circuit breaker are not exercised; requests too, for the old copy.
        monkeypatch.setattr(requests, "get", down)
        monkeypatch.setattr(FetchService, "fetch_direct_text", down)
        with pytest.raises(ConnectionError, match="down"):
            ui_utils.fetch_direct_text(URL)

    def test_tika_without_input_is_refused(self, ui_cache):
        with pytest.raises(ValueError, match="source_url soit file_content"):
            ui_utils.fetch_with_tika()
