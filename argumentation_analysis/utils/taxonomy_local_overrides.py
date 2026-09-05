"""Code-level overrides applied to the vendored Argumentum taxonomy at load.

The vendored CSV (``argumentum_fallacies_taxonomy.csv``) is a byte-faithful
mirror of upstream ArgumentumGames/Argumentum @ c86b71ff — the integrity
guard (tests/unit/scripts/test_argumentum_taxonomy_integrity.py) pins that
mirror, and re-pulls must keep diffing cleanly against upstream. Local
fixes therefore NEVER edit the CSV: they live here, addressed by PK,
reviewable and revertible the day upstream fixes the same rows.

#2036 tranche 1 — purge of the two raw editorial notes in ``nom_vulgarisé``:

- PK 41 (path 1.1.2.1.5, text_fr « Je le sais quand je le vois »): the field
  carries a titling brainstorm (« Je n'aime aucun des titres. Chercher vers… »),
  not a name. ``taxonomy_sophism_detector`` echoes ``nom_vulgarisé`` on every
  detection, so a detection of this node would put the whole note in reader
  prose.
- PK 992 (path 6.2.2, text_fr « Vouloir le beurre et l'argent du beurre »):
  the field carries a column-swap question
  (« Versatilité: ON INVERSERAIT PAS LE TEXT_FR eT LE NOM VULGARISé? »).

Both are purged to the empty string — ``nom_vulgarisé`` is optional by
design (the field is empty on the vast majority of the 1408 rows), the
lexical matcher guards empty values (``if nom_vulgarise and …``), and no
replacement name is coined here: inventing taxonomy content is item 2 of
#2036, which needs an explicit register-policy decision.
"""

from __future__ import annotations

from typing import Dict, Iterable, Union

# PK -> {field: replacement}. Keys are ints; loaders normalise to str for
# DictReader rows.
EDITORIAL_NOTE_PURGES: Dict[int, Dict[str, str]] = {
    41: {"nom_vulgarisé": ""},
    992: {"nom_vulgarisé": ""},
}


def purge_row(row: Dict[str, str]) -> Dict[str, str]:
    """Apply the editorial-note purges to one DictReader row, in place."""
    pk = str(row.get("PK", ""))
    overrides = EDITORIAL_NOTE_PURGES.get(int(pk)) if pk.isdigit() else None
    if overrides:
        for field, replacement in overrides.items():
            row[field] = replacement
    return row


def purge_rows(rows: Iterable[Dict[str, str]]) -> list:
    """Apply the editorial-note purges to DictReader rows, in place."""
    return [purge_row(row) for row in rows]


def purge_dataframe(df) -> None:
    """Apply the editorial-note purges to a pandas DataFrame in place.

    Addresses rows by the ``PK`` column (string-normalised comparison) and
    only rewrites columns the override table names, so a schema change
    upstream fails loudly at the missing-column access rather than purging
    the wrong cell.
    """
    if "PK" not in df.columns:
        return
    pk_column = df["PK"].astype(str)
    for pk, overrides in EDITORIAL_NOTE_PURGES.items():
        mask = pk_column == str(pk)
        if not mask.any():
            continue
        for field, replacement in overrides.items():
            df.loc[mask, field] = replacement
