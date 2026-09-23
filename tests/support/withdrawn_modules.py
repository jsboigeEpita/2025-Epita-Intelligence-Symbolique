"""Is a withdrawn module still importable? (#2436)

``importlib.util.find_spec(name) is None`` is the natural withdrawal guard, and
it goes red on any checkout that ran the code before the withdrawal. Git
deletes the sources but not their untracked ``__pycache__/`` directories, and a
directory left holding only caches is enough for Python to resolve its name as
an empty namespace package. Nothing can be imported from it, since Python
ignores ``__pycache__`` bytecode whose source is gone. Measured on ai-01: the
guards of #2111, #2116 and #2122 went red on such leftovers while every
checkout made by a fresh clone, CI included, stayed green.

A withdrawal guard asks :func:`still_importable` instead: a module file or a
regular package counts; a namespace counts only when a file outside any
``__pycache__`` directory lives under it.
"""

import importlib.util
from pathlib import Path
from typing import Iterable, List


def importable_files(search_locations: Iterable[str]) -> List[str]:
    """Files under ``search_locations`` that are not inside a ``__pycache__``."""
    found = []
    for location in search_locations:
        root = Path(location)
        for path in root.rglob("*"):
            relative = path.relative_to(root)
            if path.is_file() and "__pycache__" not in relative.parts:
                found.append(relative.as_posix())
    return sorted(found)


def still_importable(name: str) -> bool:
    try:
        spec = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        return False  # the parent package is gone, so this name is too
    if spec is None:
        return False
    if spec.submodule_search_locations is None or spec.origin not in (
        None,
        "namespace",
    ):
        return True  # a module file, or a package with an __init__
    return bool(importable_files(spec.submodule_search_locations))
