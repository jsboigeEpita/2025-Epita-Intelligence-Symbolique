# -*- coding: utf-8 -*-
"""#3342 — the mypy gate sees missing stubs again; one named exception.

``pyproject.toml`` used to set ``ignore_missing_imports = true`` GLOBALLY, so
``mypy --strict`` read 0 with or without the stubs installed (#3325 measured
the blindness; the census on #3342, negative control included, measured what
the flag was hiding: exactly one untyped import, ``jpype``, in the 8 strict
modules + the 32 restitution files). A gate that cannot redden proves
nothing — the same rule as any instrument.

The coordinator ruling (#3342, option a) removes the global flag and names
the one exception at module granularity:
``[[tool.mypy.overrides]] module = ["jpype", "jpype.*"]`` — ``types-jpype``
does not exist on PyPI, and the import is deliberate (the clingo bridge in
``orchestration/invoke_callables.py``). These witnesses pin that shape:

- the global flag is gone — putting it back (or reaching for the same
  blank cheque a second time) reddens here, not at the next blind pass;
- exactly ONE override carries ``ignore_missing_imports``, and it names
  ``jpype`` — a second quiet exception added next year cannot hide behind
  the first.

Parsing ``pyproject.toml`` as data (``tomli``, pytest's own dependency on
py3.10; ``tomllib`` on 3.11+) — no mypy run, no network.
"""

from __future__ import annotations

from pathlib import Path

try:  # py>=3.11
    import tomllib  # type: ignore[import-not-found]
except ModuleNotFoundError:  # py3.10 — pytest's own config dependency
    import tomli as tomllib  # type: ignore[import-not-found]

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"


def _mypy_tables() -> dict:
    with PYPROJECT.open("rb") as fh:
        data = tomllib.load(fh)
    return data["tool"]["mypy"]


class TestGlobalBlankChequeIsGone:
    def test_no_global_ignore_missing_imports(self):
        """Born red on main: the global flag is the blindness itself."""
        tables = _mypy_tables()
        assert "ignore_missing_imports" not in tables, (
            "ignore_missing_imports must not be set globally (#3342): it "
            "hides every missing stub from the gate. Name exceptions per "
            "module in [[tool.mypy.overrides]] instead."
        )


class TestTheOneNamedException:
    def test_exactly_one_override_carries_it_and_it_names_jpype(self):
        """One exception, spelled out — not a growing family of silences."""
        tables = _mypy_tables()
        flagged = [
            o for o in tables.get("overrides", []) if "ignore_missing_imports" in o
        ]
        assert len(flagged) == 1, (
            f"expected exactly one override with ignore_missing_imports, "
            f"found {len(flagged)}: {[o.get('module') for o in flagged]}"
        )
        assert flagged[0]["ignore_missing_imports"] is True
        assert flagged[0]["module"] == ["jpype", "jpype.*"], (
            "the only tolerated untyped import is jpype (no stubs on PyPI, "
            "lazy clingo-bridge import) — anything else must redden."
        )
