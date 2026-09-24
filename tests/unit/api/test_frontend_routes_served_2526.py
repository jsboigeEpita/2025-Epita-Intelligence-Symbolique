# -*- coding: utf-8 -*-
"""#2526: every route the React frontend calls is a route ``api.main:app`` serves.

The frontend was written against the Flask app of ``services/web_api_from_libs``,
archived in ``df031b34`` (#34). ``api.main:app`` did not take its routes over, so
seven calls answered 404, and nothing said so until a live e2e run reached them.

The census, with its root stated: every tracked ``.js`` file under
``services/web_api/interface-web-argumentative/src/``, test files excepted. A call
is a string or template literal whose path starts with ``/api/``, after an
optional ``${API_BASE_URL}``. Its method is the ``method:`` of the options object
that follows the literal, and GET when there is none (``fetch``'s default, and
what a link does). A ``${...}`` segment matches any OpenAPI path parameter.

The served routes are read from ``app.openapi()["paths"]``, in a fresh
interpreter. ``app.routes`` does not list what ``include_router`` adds since
FastAPI 0.138 (#1853), and the test session's ``sys.modules`` may hold mocks
(#2529).

A call the backend does not serve yet is named in ``UNSERVED``, with the issue
that owns it. The map only shrinks: an entry whose route is served reddens.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
FRONTEND = "services/web_api/interface-web-argumentative/src"

# (method, path) -> why it is not served yet, and the issue that owns it. Empty
# since #2526 PR B served POST /api/fallacies with the pipeline's detector.
UNSERVED = {}

_LITERAL = re.compile(
    r"""(['"`])(?:\$\{API_BASE_URL\})?(/api/[^'"`?\s]*)(?:\?[^'"`]*)?\1"""
)
_OPTIONS = re.compile(r"\s*,\s*\{([^}]*)")
_METHOD = re.compile(r"""method:\s*['"](\w+)['"]""")
_PARAM = re.compile(r"\$\{[^}]*\}|\{[^}]*\}")

_SERVED = r"""
import json
from api.main import app
print("SERVED " + json.dumps({p: sorted(m.upper() for m in ops) for p, ops in app.openapi()["paths"].items()}))
"""


def calls(text):
    """``[(line, method, path), ...]``: the ``/api/`` calls in a JS source."""
    found = []
    for match in _LITERAL.finditer(text):
        options = _OPTIONS.match(text, match.end())
        method = options and _METHOD.search(options.group(1))
        found.append(
            (
                text.count("\n", 0, match.start()) + 1,
                method.group(1).upper() if method else "GET",
                match.group(2),
            )
        )
    return found


def shape(path):
    """A path with every parameter written ``{}``, so both sides compare."""
    return _PARAM.sub("{}", path)


def served_routes():
    """``{(method, shaped path)}`` that ``api.main:app`` publishes."""
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join([str(ROOT), env.get("PYTHONPATH", "")])
    done = subprocess.run(
        [sys.executable, "-c", _SERVED],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    lines = [line for line in done.stdout.splitlines() if line.startswith("SERVED ")]
    assert done.returncode == 0 and lines, done.stdout[-2000:] + done.stderr[-2000:]
    paths = json.loads(lines[-1][len("SERVED ") :])
    return {
        (method, shape(path)) for path, methods in paths.items() for method in methods
    }


def _sources():
    listed = subprocess.run(
        ["git", "ls-files", "--", f"{FRONTEND}/*.js"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    return [ROOT / name for name in listed if not name.endswith(".test.js")]


SOURCES = _sources()
CALLS = [
    (path.relative_to(ROOT).as_posix(), line, method, url)
    for path in SOURCES
    for line, method, url in calls(path.read_text(encoding="utf-8-sig"))
]


@pytest.fixture(scope="module")
def served():
    return served_routes()


def test_the_census_sees_the_calls_it_names():
    files = {name for name, *_ in CALLS}
    assert f"{FRONTEND}/services/api.js" in files, files
    assert f"{FRONTEND}/services/proposalApi.js" in files, files
    assert len(CALLS) >= 15, CALLS


def test_the_census_reads_methods_and_parameters():
    """Control: the parser on the shapes the frontend uses."""
    text = (
        "const a = () => fetchJSON(`${API_BASE_URL}/api/proposals/${id}`);\n"
        "const b = () => fetchWithTimeout(`${API_BASE_URL}/api/validate`, {\n"
        "    method: 'POST',\n"
        "    body: JSON.stringify({ premises })\n"
        "  });\n"
        "const c = () => fetchJSON(`${API_BASE_URL}/api/proposals?${params}`);\n"
        '<a href="/api/health">x</a>\n'
    )

    assert calls(text) == [
        (1, "GET", "/api/proposals/${id}"),
        (2, "POST", "/api/validate"),
        (6, "GET", "/api/proposals"),
        (7, "GET", "/api/health"),
    ]
    assert shape("/api/proposals/${id}") == shape("/api/proposals/{proposal_id}")


@pytest.mark.parametrize(
    "call",
    [call for call in CALLS if (call[2], call[3]) not in UNSERVED],
    ids=lambda call: f"{call[0].rsplit('/', 1)[-1]}:{call[1]} {call[2]} {call[3]}",
)
def test_every_frontend_call_is_served(call, served):
    name, line, method, url = call
    assert (method, shape(url)) in served, f"{name}:{line} calls {method} {url}"


def test_an_unserved_entry_is_still_unserved_and_still_called(served):
    """The map only shrinks: a served or no longer called route leaves it.

    A loop, not a parametrization: an empty map is the goal, and pytest skips a
    test whose parameter set is empty.
    """
    for method, url in UNSERVED:
        assert (method, shape(url)) not in served, f"{method} {url} is served now"
        assert any(
            (m, u) == (method, url) for _, _, m, u in CALLS
        ), f"{method} {url} is not called"
