"""#2402 — xdist serialises reports as UTF-8; a lone surrogate crashes the worker.

Measured: a test whose failure message holds a lone surrogate (U+D800..U+DFFF —
half an emoji, a truncated decode) makes execnet refuse the report
(``DumpError: strings must be utf-8 encodable``). The worker dies, xdist raises
INTERNALERROR, and the session ends WITHOUT its failures section: a failure
elsewhere in the same session was reported as a bare count, traceback lost.

The repair: ``tests/conftest.py`` wraps ``pytest_report_to_serializable`` — the
hook xdist calls in the worker to build the wire form of a report — and
re-encodes, recursively, every string that is not UTF-8 encodable, naming the
cause so the escaped text stays traceable.

Import-light (stdlib only): conftest loads this on every pytest bootstrap.
"""

from __future__ import annotations

NOTE = (
    "[#2402: escaped a lone surrogate (not UTF-8 encodable) in a report "
    "string, which execnet cannot serialise]"
)


def escape_lone_surrogates(value: str) -> str:
    """``\\ud800`` and friends become their ``\\ud800`` backslash spelling."""
    return value.encode("utf-8", "backslashreplace").decode("utf-8")


def sanitize_report_data(data):
    """``(data, escaped)``: every non-UTF-8-encodable string in ``data`` is
    re-encoded (see ``NOTE``); ``escaped`` counts them.

    Walks the report's containers (dicts, lists, tuples) where execnet's
    serialiser would find the strings. Anything else is returned as-is.
    """
    escaped = 0

    def walk(node):
        nonlocal escaped
        if isinstance(node, str):
            try:
                node.encode("utf-8")
            except UnicodeEncodeError:
                escaped += 1
                return f"{escape_lone_surrogates(node)}\n{NOTE}"
            return node
        if isinstance(node, dict):
            return {walk(key): walk(value) for key, value in node.items()}
        if isinstance(node, tuple):
            return tuple(walk(item) for item in node)
        if isinstance(node, list):
            return [walk(item) for item in node]
        return node

    return walk(data), escaped
