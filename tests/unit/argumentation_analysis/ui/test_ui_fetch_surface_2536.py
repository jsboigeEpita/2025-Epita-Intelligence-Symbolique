"""#2536: the notebook UI could neither build its FetchService nor call it.

Three layers, each hidden by the one above it:

- ``initialize_text_cache`` read two names it never bound: ``fetch_service``,
  a local of ``configure_analysis_task``, and ``get_cache_filepath``, never
  imported. Every source raised a NameError that the loop's ``except`` counted
  as one more cache error.
- Both entry points built the service as
  ``FetchService(CacheService(settings), settings)``, which raises before any
  source: CacheService takes a directory, not the settings object.
- The UI called ``fetch_website_content`` and ``fetch_document_content``, two
  methods FetchService has never had (``git log -S`` finds no definition), on
  9 sites: 7 in ``app.py``, 2 in ``verification_utils.py``. The service's
  methods are ``fetch_with_jina`` and ``fetch_with_tika``.

The service is really constructed here and only its network methods are
replaced, at the class, so a call to a method the class lacks fails the patch
instead of being answered by a double. The two display modules ``ui/app.py``
imports at module level (``ipywidgets``, ``jupyter_ui_poll``) are declared
nowhere (#2076) and are stubbed; the cache path never touches them. Sources
are synthetic.
"""

import importlib
import sys
import types
from unittest.mock import MagicMock

import pytest

from argumentation_analysis.services.cache_service import CacheService
from argumentation_analysis.services.fetch_service import FetchService
from argumentation_analysis.ui import config as ui_config
from argumentation_analysis.ui.utils import reconstruct_url
from argumentation_analysis.ui.verification_utils import verify_extract_definitions

APP = "argumentation_analysis.ui.app"
SOURCE = {
    "source_name": "Source_A",
    "schema": "https",
    "host_parts": ["example", "org"],
    "path": "/texts/source_a_2536.txt",
}
URL = reconstruct_url(SOURCE["schema"], SOURCE["host_parts"], SOURCE["path"])
BY_TYPE = [
    ("jina", "fetch_with_jina", (URL,), {}),
    ("direct_download", "fetch_direct_text", (URL,), {}),
    ("tika", "fetch_with_tika", (), {"url": URL}),
]


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setitem(sys.modules, "ipywidgets", types.ModuleType("ipywidgets"))
    poll = types.ModuleType("jupyter_ui_poll")
    poll.ui_events = lambda: None
    monkeypatch.setitem(sys.modules, "jupyter_ui_poll", poll)
    sys.modules.pop(APP, None)
    yield importlib.import_module(APP)
    sys.modules.pop(APP, None)


@pytest.mark.parametrize("source_type, method, args, kwargs", BY_TYPE)
def test_the_cache_init_fetches_a_source_it_lacks(
    app, monkeypatch, source_type, method, args, kwargs
):
    fetch = MagicMock()
    monkeypatch.setattr(FetchService, method, fetch)
    monkeypatch.setattr(
        app.ui_config, "EXTRACT_SOURCES", [{**SOURCE, "source_type": source_type}]
    )

    app.initialize_text_cache()

    fetch.assert_called_once_with(*args, **kwargs)


@pytest.mark.parametrize("source_type, method, args, kwargs", BY_TYPE)
def test_the_marker_check_fetches_through_the_real_methods(
    monkeypatch, tmp_path, source_type, method, args, kwargs
):
    fetch = MagicMock(return_value="debut du texte ... fin du texte")
    monkeypatch.setattr(FetchService, method, fetch)
    source = {
        **SOURCE,
        "source_type": source_type,
        "extracts": [
            {
                "extract_name": "Extract_A",
                "start_marker": "debut",
                "end_marker": "fin",
            }
        ],
    }

    summary = verify_extract_definitions([source], FetchService(CacheService(tmp_path)))

    fetch.assert_called_once_with(*args, **kwargs)
    assert "1 extraits vérifiés" in summary
    assert "0 erreur(s)" in summary


def test_the_service_caches_where_the_ui_looks_up(app):
    service = app._build_fetch_service()

    assert service.cache_service.cache_dir == ui_config.CACHE_DIR
    assert service.jina_reader_prefix == ui_config.JINA_READER_PREFIX
