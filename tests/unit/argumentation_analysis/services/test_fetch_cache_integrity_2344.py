"""#2344: the fetch caches never keep a mangled or half-written text.

Measured on ``main`` ``328df1af0``:
- ``fetch_direct_text`` decoded with ``errors="ignore"``, so a Latin-1 page
  lost every accent ("Liberté" became "Libert"), and the cache kept the loss.
- An uploaded Latin-1 ``.txt`` lost its accents the same way. The Tika branch
  meant for undecodable files was unreachable: ``errors="ignore"`` never raises.
- Both caches wrote in place. A failed write left an empty file, which
  ``load_from_cache`` served as the cached text of the source: ``""``, forever.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
import requests

from argumentation_analysis.services import fetch_service as fetch_module
from argumentation_analysis.services.cache_service import CacheService
from argumentation_analysis.services.fetch_service import FetchService

GET = "argumentation_analysis.services.fetch_service.requests.get"
TEXT = "Liberté, égalité, fraternité : un texte accentué."


def _response(content: bytes, content_type: str) -> requests.Response:
    """A real ``requests.Response``, with the encoding requests derives from the header."""
    response = requests.Response()
    response.status_code = 200
    response._content = content
    response.headers["Content-Type"] = content_type
    response.encoding = requests.utils.get_encoding_from_headers(response.headers)
    return response


@pytest.fixture
def cache_service(tmp_path) -> CacheService:
    return CacheService(cache_dir=tmp_path / "cache")


@pytest.fixture
def fetch_service(cache_service, tmp_path) -> FetchService:
    return FetchService(
        cache_service=cache_service, temp_download_dir=tmp_path / "downloads"
    )


class TestDecodingKeepsEveryCharacter:
    def test_latin1_page_keeps_its_accents_and_so_does_the_cache(self, fetch_service):
        url = "https://example.test/latin1.txt"
        latin1 = _response(TEXT.encode("latin-1"), "text/plain; charset=ISO-8859-1")
        with patch(GET, return_value=latin1):
            text = fetch_service.fetch_direct_text(url)
        assert text == TEXT
        assert fetch_service.cache_service.load_from_cache(url) == TEXT

    def test_utf8_page_is_unchanged(self, fetch_service):
        # Control: no charset on text/plain makes requests guess ISO-8859-1,
        # but valid UTF-8 is still read as UTF-8.
        url = "https://example.test/utf8.txt"
        with patch(GET, return_value=_response(TEXT.encode("utf-8"), "text/plain")):
            assert fetch_service.fetch_direct_text(url) == TEXT

    def test_undecodable_bytes_stay_visible(self):
        text, encoding = fetch_module.decode_fetched_text(b"caf\xe9 noir", ())
        assert text == "caf\ufffd noir"
        assert encoding == "utf-8+replace"

    def test_latin1_upload_goes_to_tika_instead_of_losing_its_accents(
        self, fetch_service
    ):
        tika = _response(TEXT.encode("utf-8"), "text/plain; charset=utf-8")
        with patch.object(
            fetch_service, "_robust_put_request", return_value=tika
        ) as put:
            text = fetch_service.fetch_with_tika(
                file_content=TEXT.encode("latin-1"), file_name="doc.txt"
            )
        assert text == TEXT
        put.assert_called_once()


class TestCacheNeverServesAPartialWrite:
    def test_failed_save_leaves_no_entry(self, cache_service):
        url = "https://example.test/doc"
        # A lone surrogate cannot be encoded, so the save fails.
        assert cache_service.save_to_cache(url, "début \ud800 fin") is False
        assert not cache_service.get_cache_filepath(url).exists()
        assert cache_service.load_from_cache(url) is None
        assert list(cache_service.cache_dir.iterdir()) == []

    def test_empty_cache_file_is_a_miss_and_the_source_is_fetched_again(
        self, fetch_service
    ):
        # An empty file is what an interrupted in-place write left behind.
        source = {
            "schema": "https:",
            "host_parts": ["example", "test"],
            "path": "/doc",
            "source_type": "direct_download",
        }
        url = fetch_service.reconstruct_url(
            source["schema"], source["host_parts"], source["path"]
        )
        fetch_service.cache_service.get_cache_filepath(url).write_bytes(b"")

        fresh = _response("contenu frais".encode("utf-8"), "text/plain; charset=utf-8")
        with patch(GET, return_value=fresh) as get:
            text, fetched_url = fetch_service.fetch_text(source)
        assert (text, fetched_url) == ("contenu frais", url)
        get.assert_called_once()

    def test_interrupted_raw_download_leaves_no_raw_cache(self, fetch_service):
        # The write is interrupted before it lands: the next call must not find
        # a partial raw file to send to Tika.
        url = "https://example.test/doc.pdf"
        download = _response(b"%PDF-1.4 binary", "application/pdf")
        tika = _response("texte extrait".encode("utf-8"), "text/plain; charset=utf-8")
        with patch(GET, return_value=download), patch.object(
            fetch_service, "_robust_put_request", return_value=tika
        ), patch(
            "argumentation_analysis.services.cache_service.os.replace",
            side_effect=OSError("disk full"),
        ):
            text = fetch_service.fetch_with_tika(url=url)
        assert text == "texte extrait"
        assert list(fetch_service.temp_download_dir.iterdir()) == []
        assert list(fetch_service.cache_service.cache_dir.iterdir()) == []

    def test_completed_save_round_trips(self, cache_service):
        # Control: the atomic path still writes what it was given.
        url = "https://example.test/doc"
        assert cache_service.save_to_cache(url, TEXT) is True
        assert cache_service.load_from_cache(url) == TEXT
        assert [p.name for p in cache_service.cache_dir.iterdir()] == [
            cache_service.get_cache_filepath(url).name
        ]
