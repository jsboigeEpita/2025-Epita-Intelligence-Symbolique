"""Reproducible README inventory of ``argumentation_analysis/`` (#2088 lot 0).

First-party is decided by GIT TRACKING, not disk presence: vendored trees,
local caches and the dead-tree leftovers of past cleanups (#2055) all sit on
disk and must not enter the inventory. The instrument therefore enumerates
``git ls-files`` under ``argumentation_analysis/`` only.

Emits a dated markdown report to stdout. Positive controls (exit 1 on any
failure) pin the instrument itself — an inventory that cannot find the known
documented dir, the known undocumented ones, the known vendored exclusion and
the known deleted trees measures nothing.

Usage:
    python scripts/docs/inventory_argumentation_readmes.py > report.md
"""

from __future__ import annotations

import datetime as _dt
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SUBTREE = "argumentation_analysis"
VENDORED_ROOTS = ("libs", "portable_jdk")
# A directory is *substantial* when it carries at least this many tracked
# files, or any tracked Python source. Printed in the report — the threshold
# is a declared rule, not a hidden judgement.
SUBSTANTIAL_MIN_FILES = 3
_SOURCE_EXTS = {".py", ".md", ".yaml", ".yml", ".json", ".toml", ".ps1", ".sh", ".cfg", ".ini"}
_LINK_RE = re.compile(r"\]\(([^)#\s]+)[)#\s]")


def _git(*args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True
    )
    return out.stdout


def _last_commit_date(path: str) -> str:
    out = _git("log", "-1", "--format=%as", "--", path)
    return out.strip() or "untracked"


def _tracked_files() -> dict[str, set[str]]:
    files = _git("ls-files", "--", SUBTREE).splitlines()
    dirs: dict[str, set[str]] = defaultdict(set)
    for f in files:
        parent = str(Path(f).parent).replace("\\", "/")
        if parent == SUBTREE:
            continue
        dirs[parent].add(f)
    return dirs


def _on_disk_only(tracked_dirs: set[str]) -> list[str]:
    disk = {
        str(p.relative_to(REPO)).replace("\\", "/")
        for p in (REPO / SUBTREE).rglob("*")
        if p.is_dir() and "__pycache__" not in p.parts
    }
    return sorted(d for d in disk if d != SUBTREE and d not in tracked_dirs)


def _gitignored(rel_dir: str) -> bool:
    """True when a VERSIONED .gitignore rule covers this directory.

    The probe is a fictional FILE under the directory, not the directory
    itself: directory-only patterns (``libs/``) cannot match a non-existent
    path because git would have to stat() it to learn it is a directory —
    from a clean worktree/clone the roots are absent and the directory probe
    silently fails. A descendant path is under a directory by construction,
    so the rules evaluate everywhere (#2091 review). No disk content is
    required: check-ignore only evaluates the path against tracked rules.
    """
    out = subprocess.run(
        ["git", "-C", str(REPO), "check-ignore", f"{rel_dir}/__probe__"],
        capture_output=True,
        text=True,
    )
    return out.returncode == 0 and bool(out.stdout.strip())


def _ignore_status(rel_dir: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(REPO), "check-ignore", rel_dir],
        capture_output=True,
        text=True,
    )
    if out.returncode == 0 and out.stdout.strip():
        return "gitignored"
    tracked = _git("ls-files", "--", rel_dir).strip()
    return "untracked non-ignoré" if not tracked else "suivi (résiduel)"


def _broken_paths(readme: Path) -> list[str]:
    """Relative links/targets inside a README that resolve to nothing."""
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


def main() -> int:
    tracked = _tracked_files()
    tracked_dirs = set(tracked)
    rows = []
    readme_rows = []
    substantial_without_readme = []
    for d in sorted(tracked):
        files = tracked[d]
        n_files = len(files)
        py = [f for f in files if f.endswith(".py")]
        readme = f"{d}/README.md"
        has_readme = readme in files
        specialized = sorted(
            f.rsplit("/", 1)[1]
            for f in files
            if re.fullmatch(r"README_[^/]*\.md", f.rsplit("/", 1)[1])
        )
        vendored = d.replace(SUBTREE + "/", "").split("/")[0] in VENDORED_ROOTS
        substantial = (not vendored) and (n_files >= SUBSTANTIAL_MIN_FILES or bool(py))
        depth = len(d.split("/")) - 1
        rows.append(
            (d, depth, n_files, len(py), has_readme, specialized, vendored, substantial)
        )
        if substantial and not has_readme:
            substantial_without_readme.append(d)
        if has_readme:
            p = REPO / readme
            readme_rows.append(
                (
                    readme,
                    len(p.read_text(encoding="utf-8", errors="replace").splitlines()),
                    _last_commit_date(readme),
                    _last_commit_date(d),
                    _broken_paths(p),
                )
            )

    today = _dt.date.today().isoformat()
    vendored_dirs = [r for r in rows if r[6]]
    disk_only = _on_disk_only(tracked_dirs)

    print(f"# Inventaire README `argumentation_analysis/` — {today} (#2088 lot 0)")
    print()
    print(
        "Base : contenu **suivi par git** (`git ls-files`), pas le disque — les arbres\n"
        "vendorisés, caches locaux et résidus de cleanups passés ne sont pas first-party.\n"
        f"Règle « substantiel » : ≥{SUBSTANTIAL_MIN_FILES} fichiers suivis OU au moins un `.py`.\n"
        f"Reproduction : `python scripts/docs/inventory_argumentation_readmes.py`"
    )
    print()
    print(f"- répertoires suivis (hors racine) : **{len(rows)}**")
    print(f"- dont vendorisés (exclus, preuve ci-dessous) : **{len(vendored_dirs)}**")
    print(f"- first-party substantiels : **{sum(1 for r in rows if r[7])}**")
    print(f"- substantiels SANS `README.md` : **{len(substantial_without_readme)}**")
    print(f"- avec `README.md` : **{len(readme_rows)}**")
    print()

    print("## Répertoires first-party substantiels (profondeur, README, spécialisés)")
    print()
    print("| Répertoire | Prof. | Fichiers | `.py` | README.md | README_*.md |")
    print("|---|---|---|---|---|---|")
    for d, depth, n, npy, has, spec, _v, subst in rows:
        if not subst:
            continue
        print(
            f"| `{d}` | {depth} | {n} | {npy} | "
            f"{'oui' if has else '**NON**'} | {', '.join(spec) or '—'} |"
        )
    print()

    print("## First-party NON substantiels (classpath léger — pas de README exigé)")
    print()
    light = [(d, n) for d, _dep, n, _py, _r, _s, _v, subst in rows if not subst and not _v]
    for d, n in light:
        print(f"- `{d}` ({n} fichier(s) suivi(s))")
    print()

    print("## Exclusions vendorées (preuve par contenu)")
    print()
    for d, _dep, n, _py, _r, _s, _v, _subst in vendored_dirs:
        marker = _git("ls-files", "--", d)
        jars = sum(1 for f in marker.splitlines() if f.endswith((".jar", ".exe", ".dll", ".bat")))
        print(f"- `{d}` — {n} fichiers vendorisés suivis, dont {jars} binaire(s) jar/exe/dll/bat")
    print()

    disk_roots = {d.replace(SUBTREE + "/", "").split("/")[0] for d in disk_only}
    print("## Présents sur disque mais NON suivis (signal machine local — hors base de preuve)")
    print()
    for d in disk_only:
        vend = " — **vendorisé**" if d.replace(SUBTREE + "/", "").split("/")[0] in VENDORED_ROOTS else ""
        print(f"- `{d}` ({_ignore_status(d)}{vend})")
    print()

    print("## README existants — signaux objectifs")
    print()
    print(
        "Âge = dernier commit touchant le README ; « activité rép. » = dernier commit\ntouchant "
        "n'importe quel fichier du répertoire. Un README plus vieux que son\nrépertoire est un "
        "candidat « partiel/périmé » à vérifier à la lecture."
    )
    print()
    print("| README | Lignes | Dernier commit README | Dernier activité rép. | Liens cassés |")
    print("|---|---|---|---|---|")
    for path, lines, age, dir_age, broken in readme_rows:
        drift = " ← dérive" if age < dir_age else ""
        print(
            f"| `{path}` | {lines} | {age}{drift} | {dir_age} | "
            f"{len(broken)}{' : ' + ', '.join(broken[:4]) if broken else ''} |"
        )
    print()

    print("## Contrôles positifs de l'instrument")
    print()
    checks = []
    ok, msg = any(r[0] == f"{SUBTREE}/orchestration" and r[4] for r in rows), (
        "répertoire documenté connu (`orchestration/` porte un README.md)"
    )
    checks.append((ok, msg))
    ok2, msg2 = len(substantial_without_readme) >= 5, (
        f"{len(substantial_without_readme)} substantiels sans README (attendu ≥26 selon "
        "l'issue — l'instrument en voit au moins 5)"
    )
    checks.append((ok2, msg2))
    disk_roots = {d.replace(SUBTREE + "/", "").split("/")[0] for d in disk_only}
    tracked_vendored = {d.replace(SUBTREE + "/", "").split("/")[0] for d in vendored_dirs}
    vendored_rel = [f"{SUBTREE}/{r}" for r in VENDORED_ROOTS]
    tracked_under_roots = [f for f in _git("ls-files", "--", *vendored_rel).splitlines() if f.strip()]
    ignored_roots = [rel for rel in vendored_rel if _gitignored(rel)]
    ok3 = (not tracked_under_roots) and len(ignored_roots) == len(vendored_rel)
    checks.append(
        (
            ok3,
            "exclusions vendorisées prouvées DEPUIS GIT UNIQUEMENT : "
            f"{len(tracked_under_roots)} fichier suivi sous {vendored_rel} (attendu 0), "
            f"règles .gitignore versionnées matchées par check-ignore pour "
            f"{len(ignored_roots)}/{len(vendored_rel)} — aucune exigence sur le disque "
            "local (reproductible depuis un worktree/clone propre)",
        )
    )
    ok4 = not any(
        d.startswith(f"{SUBTREE}/orchestration/engine")
        or d.startswith(f"{SUBTREE}/orchestration/cluedo_components")
        for d in tracked
    )
    checks.append(
        (
            ok4,
            "arbres morts #2055 (`orchestration/engine/`, `cluedo_components/`) absents "
            "de l'inventaire suivi — la base git ls-files résiste aux résidus disque",
        )
    )
    failures = 0
    for ok_i, m in checks:
        print(f"- {'PASS' if ok_i else 'FAIL'} — {m}")
        failures += 0 if ok_i else 1
    if failures:
        print(f"\n{failures} contrôle(s) positif(s) ÉCHOUÉ(S) — inventaire non fiable.")
        return 1
    print("\nTous les contrôles positifs passent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
