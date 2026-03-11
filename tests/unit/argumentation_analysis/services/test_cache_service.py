# tests/unit/argumentation_analysis/services/test_cache_service.py
"""Tests for CacheService — file-based URL content cache."""

import pytest
from pathlib import Path

from argumentation_analysis.services.cache_service import CacheService


@pytest.fixture
def cache_dir(tmp_path):
    return tmp_path / "cache"


@pytest.fixture
def service(cache_dir):
    return CacheService(cache_dir)


# ── Init ──

class TestInit:
    def test_creates_dir(self, cache_dir):
        assert not cache_dir.exists()
        CacheService(cache_dir)
        assert cache_dir.exists()

    def test_existing_dir_ok(self, cache_dir):
        cache_dir.mkdir(parents=True)
        svc = CacheService(cache_dir)
        assert svc.cache_dir == cache_dir


# ── get_cache_filepath ──

class TestGetCacheFilepath:
    def test_returns_path(self, service):
        path = service.get_cache_filepath("https://example.com")
        assert isinstance(path, Path)
        assert path.suffix == ".txt"
        assert path.parent == service.cache_dir

    def test_deterministic(self, service):
        p1 = service.get_cache_filepath("https://example.com")
        p2 = service.get_cache_filepath("https://example.com")
        assert p1 == p2

    def test_different_urls_different_paths(self, service):
        p1 = service.get_cache_filepath("https://a.com")
        p2 = service.get_cache_filepath("https://b.com")
        assert p1 != p2

    def test_sha256_based(self, service):
        import hashlib
        url = "https://example.com"
        expected = hashlib.sha256(url.encode()).hexdigest() + ".txt"
        assert service.get_cache_filepath(url).name == expected


# ── save_to_cache / load_from_cache ──

class TestSaveAndLoad:
    def test_roundtrip(self, service):
        url = "https://example.com/page"
        text = "Hello, world!"
        assert service.save_to_cache(url, text) is True
        assert service.load_from_cache(url) == text

    def test_empty_text_not_saved(self, service):
        assert service.save_to_cache("https://a.com", "") is False

    def test_none_text_not_saved(self, service):
        assert service.save_to_cache("https://a.com", None) is False

    def test_load_cache_miss(self, service):
        assert service.load_from_cache("https://nonexistent.com") is None

    def test_overwrite(self, service):
        url = "https://example.com"
        service.save_to_cache(url, "v1")
        service.save_to_cache(url, "v2")
        assert service.load_from_cache(url) == "v2"

    def test_unicode_content(self, service):
        url = "https://example.com/fr"
        text = "Les élèves étudient la théorie de l'argumentation."
        service.save_to_cache(url, text)
        assert service.load_from_cache(url) == text

    def test_large_content(self, service):
        url = "https://example.com/large"
        text = "x" * 100_000
        service.save_to_cache(url, text)
        assert service.load_from_cache(url) == text


# ── clear_cache ──

class TestClearCache:
    def test_clear_specific_url(self, service):
        url = "https://example.com"
        service.save_to_cache(url, "data")
        deleted, errors = service.clear_cache(url)
        assert deleted == 1
        assert errors == 0
        assert service.load_from_cache(url) is None

    def test_clear_nonexistent_url(self, service):
        deleted, errors = service.clear_cache("https://nope.com")
        assert deleted == 0
        assert errors == 0

    def test_clear_all(self, service):
        service.save_to_cache("https://a.com", "a")
        service.save_to_cache("https://b.com", "b")
        service.save_to_cache("https://c.com", "c")
        deleted, errors = service.clear_cache()
        assert deleted == 3
        assert errors == 0

    def test_clear_empty_cache(self, service):
        deleted, errors = service.clear_cache()
        assert deleted == 0
        assert errors == 0


# ── get_cache_size ──

class TestGetCacheSize:
    def test_empty_cache(self, service):
        count, size = service.get_cache_size()
        assert count == 0
        assert size == 0

    def test_after_save(self, service):
        service.save_to_cache("https://a.com", "hello")
        count, size = service.get_cache_size()
        assert count == 1
        assert size > 0

    def test_multiple_files(self, service):
        service.save_to_cache("https://a.com", "a")
        service.save_to_cache("https://b.com", "bb")
        count, size = service.get_cache_size()
        assert count == 2


# ── get_cache_info ──

class TestGetCacheInfo:
    def test_empty_info(self, service):
        info = service.get_cache_info()
        assert "0 fichiers" in info

    def test_with_files(self, service):
        service.save_to_cache("https://a.com", "data")
        info = service.get_cache_info()
        assert "1 fichiers" in info


# ── _format_size ──

class TestFormatSize:
    def test_bytes(self, service):
        assert "B" in service._format_size(500)

    def test_kilobytes(self, service):
        assert "KB" in service._format_size(1500)

    def test_megabytes(self, service):
        assert "MB" in service._format_size(2_000_000)

    def test_gigabytes(self, service):
        assert "GB" in service._format_size(5_000_000_000)

    def test_zero(self, service):
        result = service._format_size(0)
        assert "0.00" in result
