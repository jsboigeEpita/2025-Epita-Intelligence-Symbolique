"""The panel's document ids, parsed once for both arms (#3375).

Moved verbatim from ``scripts/dataset/run_corpus_batch.py`` (#3700) so that an
importer which must stay keyless and model-clientless does not inherit that
module's imports: the pipeline runtime, and the checkout's ``.env`` written
into the process environment on the way. Measured 2026-11-26 on one seat,
working environment, one import per process (counts only): this module adds
7 modules and writes no environment variable, where the batch runner adds
2964 modules and writes 34, ten of them credential-bearing by name.

``parse_doc_ids`` lives here and nowhere else; the batch runner imports it
from here under its own name, because three call sites still read it from
there — a copy would drift, which is the very failure #3375 exists against.
``tests/unit/scripts/test_panel_ids_import_3700.py`` keeps both properties:
this module's import stays free of the runtime and of ``.env``, and the
runner's name is the same function object.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional


def parse_doc_ids(
    doc_ids: Optional[str] = None, panel_file: Optional[str] = None
) -> Optional[List[str]]:
    """#3375 — the panel's document ids, parsed once for BOTH arms.

    The v1 panel runs the pipeline and the same-model zero-shot on the same
    ten documents; a re-implementation per arm is how two populations drift
    apart (#2841's rule 4, which the panel inherits). One parser, one list.

    ``--doc-ids`` is a comma (or whitespace) separated list; a panel file
    holds one id per line, ``#`` opening a comment, blank lines ignored.
    Given both, the ids are concatenated in reading order and de-duplicated
    first-wins, so a document is run at most once.

    ``None`` means "no selection" — the whole corpus, exactly as before.
    A selection that was ASKED FOR but came out empty raises: running the
    whole corpus under a panel flag is the silent-difference shape, and a
    panel of zero documents would report every arm as trivially equal.
    """
    ids: List[str] = []
    if doc_ids:
        ids.extend(part for part in re.split(r"[,\s]+", doc_ids) if part)
    if panel_file is not None:
        path = Path(panel_file)
        if not path.is_file():
            raise ValueError(f"--panel-file: {path} is not a file")
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.split("#", 1)[0].strip()
            if line:
                ids.append(line)
    if not ids:
        if doc_ids is not None or panel_file is not None:
            raise ValueError(
                "the panel selection is empty — an empty panel would silently "
                "run the whole corpus"
            )
        return None
    ordered: List[str] = []
    seen = set()
    for item in ids:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered
