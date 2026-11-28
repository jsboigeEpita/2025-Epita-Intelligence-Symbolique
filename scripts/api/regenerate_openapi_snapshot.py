#!/usr/bin/env python3
"""Regenerate the OpenAPI snapshot used by contract tests.

Usage:
    python scripts/api/regenerate_openapi_snapshot.py

Outputs api/openapi.snapshot.json from api.main:app. The OpenAPI schema
can be read without starting the app or initializing a JVM. Run this when
intentionally adding/removing/changing endpoints, then commit the snapshot.
"""

import json
import os
import sys
from typing import Any, Dict

# Project root = two levels up from this script
_PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def write_snapshot(spec: Dict[str, Any], output_path: str) -> None:
    """Write the snapshot with LF bytes, whatever the seat (#3714 item 50).

    The snapshot is a TRACKED file, and in text mode ``"\\n"`` becomes the
    platform's line ending: a seat with ``core.autocrlf=false`` would commit
    the CRLF and the whole file would differ from ``main`` where the patch
    touches a handful of lines. The writer owns its bytes.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(spec, f, indent=2, ensure_ascii=False)


def main():
    # Imported here, not at module level: the writer above is exercised by a
    # unit test that must not build the FastAPI app to write a file.
    from api.main import _JTMS_AVAILABLE, app

    if not _JTMS_AVAILABLE:
        raise RuntimeError("Cannot regenerate OpenAPI snapshot without JTMS routes")
    spec = app.openapi()

    # Normalize: sort paths and schemas for deterministic diffs
    if "paths" in spec:
        spec["paths"] = dict(sorted(spec["paths"].items()))
    if "components" in spec and "schemas" in spec["components"]:
        spec["components"]["schemas"] = dict(
            sorted(spec["components"]["schemas"].items())
        )

    output_path = os.path.join(_PROJECT_ROOT, "api", "openapi.snapshot.json")
    write_snapshot(spec, output_path)

    n_paths = len(spec.get("paths", {}))
    n_schemas = len(spec.get("components", {}).get("schemas", {}))
    print(f"Snapshot written to {output_path}")
    print(f"  Paths: {n_paths}")
    print(f"  Schemas: {n_schemas}")


if __name__ == "__main__":
    main()
