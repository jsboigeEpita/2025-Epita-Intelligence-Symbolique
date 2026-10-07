"""Classify every existing README under argumentation_analysis/ (#2088, DoD item 3).

The Lot 0 inventory (INVENTORY_READMEs_ARG_ANALYSIS_2088_LOT0_2026-09-09.md)
enumerated directories and README presence; the waves then wrote the missing
leaf READMEs. What the Epic still owes (DoD item 3) is a CLASS per existing
README: courant, à réécrire, spécialisé seulement, ou hors périmètre — each
backed by a measurement, never inferred from the file name alone.

Classes and their measured rule (see the report header for the judgment
overlay):

- hors périmètre     — no tracked README lives under a versioned-ignore root;
                       the instrument proves the count is 0 (Lot 0 control 3).
- spécialisé seulement — filename README_*.md: a companion document, not the
                       directory's README (the two must not be conflated).
- à réécrire         — dir README with >=1 broken relative link (markdown
                       target resolves to nothing on disk), or under 5 prose
                       lines (a stub), or explicitly flagged by the dated
                       judgment overlay carried in this script's OUTPUT
                       (single-family README on a multi-family dir, etc.).
- courant            — dir README that passes every measured check.

Reproduction (the report cites exactly this):
    python scripts/docs/classify_argumentation_readmes.py > rapport.md

Self-test (non-vacuity, born-red): --selftest builds synthetic fixtures in a
temp dir and asserts the classifier fires on each class it must detect —
a broken link reddens, a README_*.md is specialized, an empty stub reddens.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUBTREE = "argumentation_analysis"

# Same family as inventory_argumentation_readmes._LINK_RE: markdown link /
# image targets. Bare backticked paths are NOT links and are not counted.
_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")

# Minimum prose for a dir README to count as non-stub. The waves' leaf
# contract produces multi-section documents; a near-empty file is a counter
# satisfaction, not documentation (Epic anti-pendicle: "Ne pas créer un
# README vide ... pour satisfaire un compteur").
_MIN_PROSE_LINES = 5

# Judgment overlay — entries the measurements cannot see, each with the dated
# evidence that motivated it. Keys are repo-relative POSIX paths. This is the
# ONLY hand-written input; everything else is measured. Empty until a human
# reading finds a case (see report §3 for the rows that were read in full).
_JUDGMENT: dict[str, tuple[str, str]] = {}  # path -> (classe, motif)


def _git(*args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True
    )
    return out.stdout


def _broken_paths(readme: Path) -> list[str]:
    """Relative markdown targets inside a README that resolve to nothing."""
    try:
        text = readme.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    broken = []
    for target in _LINK_RE.findall(text):
        if target.startswith(("http://", "https://", "mailto:")):
            continue
        rel = re.split(r"[:#]", target.split("#")[0])[0]
        # `fichier.py:24` is a line-anchored link, not a broken path.
        if rel and not (readme.parent / rel).exists():
            broken.append(target)
    return broken


def _prose_lines(readme: Path) -> int:
    """Non-blank, non-heading, non-table lines — the prose the reader gets."""
    try:
        text = readme.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0
    return sum(
        1
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", "|", "---", "<"))
    )


def _last_commit_date(path: str) -> str:
    out = _git("log", "-1", "--format=%as", "--", path)
    return out.strip() or "untracked"


def _gitignored_probe(rel_dir: str) -> bool:
    """Versioned .gitignore coverage, proven via a fictional descendant file
    (Lot 0 control 3: directory-only patterns cannot match a missing path)."""
    out = subprocess.run(
        ["git", "-C", str(REPO), "check-ignore", f"{rel_dir}/__probe__"],
        capture_output=True,
        text=True,
    )
    return out.returncode == 0 and bool(out.stdout.strip())


def _decide(
    rel: str, name: str, broken: list[str], prose: int, ignored: bool
) -> tuple[str, str]:
    """The class, from the MEASURED inputs — one place holds every literal.

    Kept apart from :func:`classify_one` so the self-test can drive the real
    decision on synthetic inputs: a control that re-implements the branches
    (as the first version did for the judgment overlay) can never fail, and
    a mutation of a threshold would go unnoticed (measured by the
    coordinator on #2992, mutation-style). Every branch below is exercised
    by ``--selftest``.
    """
    if re.fullmatch(r"README_[^/]*\.md", name):
        classe = "spécialisé seulement"
        motif = "README_*.md : document compagnon, pas le README du répertoire"
    elif ignored:
        # Unreachable for tracked files (Lot 0 proved 0 tracked vendored) —
        # kept as a measured branch so the class is earned, not asserted.
        classe = "hors périmètre"
        motif = "sous une racine couverte par un .gitignore versionné"
    elif broken:
        classe = "à réécrire"
        motif = f"{len(broken)} lien(s) relatif(s) cassé(s) : {', '.join(broken[:4])}"
    elif prose < _MIN_PROSE_LINES:
        classe = "à réécrire"
        motif = f"stock ({prose} lignes de prose) — satisfaction de compteur"
    else:
        classe = "courant"
        motif = "0 lien cassé, prose suffisante"
    if rel in _JUDGMENT:
        classe, motif = _JUDGMENT[rel]
        motif = f"jugement daté : {motif}"
    return classe, motif


def classify_one(readme: Path) -> dict[str, object]:
    rel = readme.relative_to(REPO).as_posix()
    parent_rel = readme.parent.relative_to(REPO).as_posix()
    name = readme.name
    broken = _broken_paths(readme)
    prose = _prose_lines(readme)
    classe, motif = _decide(rel, name, broken, prose, _gitignored_probe(parent_rel))
    return {
        "path": rel,
        "lines": prose,
        "touched": _last_commit_date(rel),
        "broken": broken,
        "classe": classe,
        "motif": motif,
    }


def _selftest() -> int:
    """Born-red: the REAL decider is exercised on every branch it claims.

    Two layers: the measurement primitives on disk fixtures (a broken link is
    really a broken link; a stub really falls under the floor), then
    :func:`_decide` itself on synthetic inputs — one assertion per branch, so
    a mutated threshold or a dropped overlay reddens here.
    """
    failures = []

    def expect(desc: str, got: object, want: object) -> None:
        if got != want:
            failures.append(f"{desc}: got {got!r}, want {want!r}")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "README.md").write_text(
            "# d\n\nsee [gone](missing.py) and [ok](./README.md)\n", encoding="utf-8"
        )
        (root / "stub").mkdir()
        (root / "stub" / "README.md").write_text("# st\n\n", encoding="utf-8")
        expect(
            "broken-link detector",
            _broken_paths(root / "README.md"),
            ["missing.py"],
        )
        if _prose_lines(root / "README.md") < 1:
            failures.append("prose counter returned 0 on real prose")
        if _prose_lines(root / "stub" / "README.md") >= _MIN_PROSE_LINES:
            failures.append("stub passed the prose floor")

    # The real decision function, one assertion per branch.
    rel = "argumentation_analysis/fake/README.md"
    expect(
        "specialized branch",
        _decide(rel, "README_solver.md", [], 50, False)[0],
        "spécialisé seulement",
    )
    expect(
        "out-of-scope branch",
        _decide(rel, "README.md", [], 50, True)[0],
        "hors périmètre",
    )
    expect(
        "broken-link branch",
        _decide(rel, "README.md", ["missing.py"], 50, False)[0],
        "à réécrire",
    )
    expect(
        "stub branch",
        _decide(rel, "README.md", [], _MIN_PROSE_LINES - 1, False)[0],
        "à réécrire",
    )
    expect("current branch", _decide(rel, "README.md", [], 50, False)[0], "courant")
    # The judgment overlay wins over the measured class and marks its origin.
    global _JUDGMENT
    saved = dict(_JUDGMENT)
    try:
        _JUDGMENT = {rel: ("à réécrire", "selftest overlay")}
        classe, motif = _decide(rel, "README.md", [], 50, False)
        expect("overlay class", classe, "à réécrire")
        if "selftest overlay" not in motif:
            failures.append(f"overlay motif not carried: {motif!r}")
    finally:
        _JUDGMENT = saved
    readmes = _tracked_readmes()
    if len(readmes) < 90:
        failures.append(f"enumeration saw only {len(readmes)} READMEs (>= 90 expected)")
    specialized_readmes = [
        p for p in readmes if re.fullmatch(r"README_[^/]*\.md", p.name)
    ]
    if not specialized_readmes:
        failures.append("no specialized README detected (Lot 0 measured 3)")
    if failures:
        for f in failures:
            print(f"SELFTEST FAIL: {f}", file=sys.stderr)
        return 1
    print(
        f"SELFTEST PASS — every branch of _decide fires (specialized / "
        f"out-of-scope / broken link / stub / current / overlay), the "
        f"measurement primitives bite, enumeration sees {len(readmes)} READMEs "
        f"({len(specialized_readmes)} specialized)"
    )
    return 0


def _tracked_readmes() -> list[Path]:
    files = _git("ls-files", "--", SUBTREE).splitlines()
    return sorted(
        REPO / f for f in files if re.fullmatch(r"README[^/]*\.md", Path(f).name)
    )


def main() -> int:
    if "--selftest" in sys.argv:
        return _selftest()
    rows = [classify_one(p) for p in _tracked_readmes()]
    order = {
        "courant": 0,
        "à réécrire": 1,
        "spécialisé seulement": 2,
        "hors périmètre": 3,
    }
    rows.sort(key=lambda r: (order[str(r["classe"])], str(r["path"])))
    counts: dict[str, int] = {}
    for r in rows:
        counts[str(r["classe"])] = counts.get(str(r["classe"]), 0) + 1
    print(f"# Classement des README existants — argumentation_analysis/ (#2088 n°3)")
    print()
    print(f"**Total README suivis** : {len(rows)}")
    for classe in order:
        print(f"- **{classe}** : {counts.get(classe, 0)}")
    print()
    print("| README | Prose | Dernier toucher | Classe | Motif (mesuré) |")
    print("|---|---:|---|---|---|")
    for r in rows:
        print(
            f"| `{r['path']}` | {r['lines']} | {r['touched']} | "
            f"{r['classe']} | {r['motif']} |"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
